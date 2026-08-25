# agent_controller_state

## Introduction

`agent_controller_state` is the memory of one running conversation. It answers three questions that the rest of the reasoning stack keeps asking:

1. **What has happened so far?** — the ordered list of events the agent is allowed to see.
2. **Where are we in the run?** — agent state (`LOADING`, `RUNNING`, `FINISHED`, …), iteration count, spend, delegate depth.
3. **Are we allowed to keep going?** — iteration and budget limits, and what happens when they are hit.

The module has three files and three ideas:

| File | Component | Idea |
| --- | --- | --- |
| `openhands/controller/state/state.py` | `State` (+ deprecated `TrafficControlState`) | The **data**. A pickled, resumable snapshot of a conversation. |
| `openhands/controller/state/state_tracker.py` | `StateTracker` | The **manager**. Builds, updates, and persists that data. |
| `openhands/controller/state/control_flags.py` | `ControlFlag`, `IterationControlFlag`, `BudgetControlFlag` | The **limits**. Small objects that count and raise when a ceiling is crossed. |

[`AgentController`](agent_controller_core.md) owns a `StateTracker` and never touches the file store or the event stream for state purposes itself. Agents ([agents](agents.md)) and condensers ([memory_and_condensers](memory_and_condensers.md)) receive the `State` object read-only and read `state.view` from it.

---

## Where it sits in the system

```mermaid
graph TB
    subgraph clients["Entry points"]
        AS["AgentSession<br/>server_sessions"]
        SETUP["core/setup.create_controller<br/>headless / CLI"]
    end

    subgraph ctrl["agent_controller_core"]
        AC["AgentController"]
    end

    subgraph state["agent_controller_state (this module)"]
        STK["StateTracker"]
        ST["State"]
        CF["IterationControlFlag<br/>BudgetControlFlag"]
    end

    subgraph readers["Read-only consumers of State"]
        AG["Agent.step(state)<br/>agents"]
        CD["Condenser.condensed_history(state)<br/>memory_and_condensers"]
        SD["StuckDetector(state)<br/>agent_controller_safeguards"]
    end

    ES["EventStream<br/>event_system"]
    FS["FileStore<br/>storage_backends"]
    CS["ConversationStats<br/>server_sessions"]
    MET["Metrics<br/>llm_layer"]

    AS -->|"State.restore_from_session()"| ST
    SETUP -->|"State.restore_from_session()"| ST
    AS -->|"initial_state="| AC
    SETUP -->|"initial_state="| AC

    AC -->|owns| STK
    STK -->|owns| ST
    ST -->|holds| CF

    STK -->|"search_events() to rebuild history"| ES
    STK -->|"save_to_session() / pickle"| FS
    STK -->|"accumulated_cost"| CS
    CS --> MET
    ST -->|"metrics"| MET

    AC -->|"state (shared ref)"| AG
    AG --> CD
    AC --> SD
    SD --> ST
```

Two things are worth noticing in that picture:

- **History is never persisted.** `State.__getstate__` blanks `history` before pickling. On restore, `StateTracker._init_history()` replays the event stream between `start_id` and `end_id`. The event stream is the single source of truth; `State` only stores the *pointers* into it.
- **Cost is never owned here.** `BudgetControlFlag.current_value` is copied from `ConversationStats.get_combined_metrics().accumulated_cost` on every step. The flag is a *watcher*, not an accountant.

---

## `State` — the conversation snapshot

`State` is a plain `@dataclass`. Its fields fall into six groups.

```mermaid
classDiagram
    class State {
        +str session_id
        +str~None~ user_id
        --- identity ---
        +AgentState agent_state
        +AgentState~None~ resume_state
        +bool confirmation_mode
        +str last_error
        --- history pointers ---
        +list~Event~ history
        +int start_id = -1
        +int end_id = -1
        +View view (cached property)
        --- limits ---
        +IterationControlFlag iteration_flag
        +BudgetControlFlag~None~ budget_flag
        --- delegation ---
        +int delegate_level = 0
        +int parent_iteration = 100
        +Metrics~None~ parent_metrics_snapshot
        +dict inputs
        +dict outputs
        --- metrics / extras ---
        +Metrics metrics
        +ConversationStats~None~ conversation_stats
        +dict extra_data
        --- methods ---
        +save_to_session(sid, file_store, user_id)
        +restore_from_session(sid, file_store, user_id) State
        +get_current_user_intent() tuple
        +get_last_user_message() MessageAction
        +get_last_agent_message() MessageAction
        +get_local_step() int
        +get_local_metrics() Metrics
        +to_llm_metadata(model, agent) dict
    }

    class TrafficControlState {
        <<deprecated enum>>
        NORMAL
        THROTTLING
        PAUSED
    }

    State ..> TrafficControlState : legacy field only
```

### The `view` property

`state.history` is the *raw* filtered event list. `state.view` is what an LLM should actually see. The property builds a [`View`](memory_and_condensers.md) via `View.from_events(self.history)`, which drops events that a `CondensationAction` marked as forgotten and splices in the summary.

The result is cached against a cheap checksum — `len(self.history)`:

```mermaid
flowchart LR
    A["state.view accessed"] --> B{"len(history) ==<br/>_history_checksum?"}
    B -- yes --> C["return cached _view"]
    B -- no --> D["_view = View.from_events(history)"]
    D --> E["_history_checksum = len(history)"]
    E --> C
```

Because history is append-only during a run, length is a sufficient checksum. Both cache attributes (`_history_checksum`, `_view`) are stripped in `__getstate__` so they are rebuilt after a restore.

Every agent and condenser reads `state.view`, not `state.history` — for example `BrowsingAgent` iterates `state.view` and `VisualBrowsingAgent` checks `len(state.view) == 1` to detect the first step. `get_current_user_intent()`, `get_last_user_message()`, and `get_last_agent_message()` all scan `reversed(self.view)`.

### Persistence

```mermaid
sequenceDiagram
    participant STK as StateTracker
    participant S as State
    participant FS as FileStore
    participant CS as ConversationStats

    Note over STK,CS: save_state()
    STK->>S: save_to_session(sid, file_store, user_id)
    S->>S: detach conversation_stats (saves itself)
    S->>S: __getstate__ → drop history,<br/>view cache, deprecated fields
    S->>S: pickle.dumps → base64
    S->>FS: write(sessions/<sid>/agent_state.pkl)
    opt user_id set
        S->>FS: delete legacy path without user_id
    end
    S->>S: reattach conversation_stats
    STK->>CS: save_metrics()

    Note over STK,CS: restore (called by AgentSession / core.setup)
    STK->>FS: read(agent_state.pkl)
    FS-->>S: base64 → pickle.loads → __setstate__
    S->>S: migrate old `iteration` field → IterationControlFlag
    S->>S: resume_state = agent_state if resumable else None
    S->>S: agent_state = LOADING
```

Notes on the restore path:

- The read falls back to the **legacy path without `user_id`** when the new path is missing, which keeps hosted (SaaS) conversations readable after the path change. See [enterprise_storage](enterprise_storage.md) for the hosted storage layout.
- `RESUMABLE_STATES = [RUNNING, PAUSED, AWAITING_USER_INPUT, FINISHED]`. If the saved `agent_state` is one of these it is copied to `resume_state`; the controller uses that to decide whether to resume automatically. Everything else (`ERROR`, `STOPPED`, `REJECTED`, …) resumes as a fresh idle conversation.
- `__setstate__` performs a **schema migration**: if the pickle has the old `iteration` / `max_iterations` fields, it synthesizes an `IterationControlFlag` from them. It also fills in defaults for `iteration_flag`, `budget_flag`, and `history` when absent, so old pickles never crash on load.
- `__getstate__` **drops** the deprecated fields (`iteration`, `local_iteration`, `max_iterations`, `traffic_control_state`, `local_metrics`, `delegates`), so each save/load cycle cleans the record a little.

`TrafficControlState` is one of those deprecated leftovers. It once described rate limiting (`NORMAL` / `THROTTLING` / `PAUSED`); that job now belongs to the control flags, and the enum survives only so old pickles deserialize.

### Delegation fields

When an agent delegates a subtask, [`AgentController.start_delegate`](agent_controller_core.md) builds a child `State` that **shares** the parent's control flags and `Metrics` object, but records where the parent left off:

| Field | Meaning |
| --- | --- |
| `delegate_level` | Parent + 1. Root is 0. |
| `iteration_flag`, `budget_flag` | **Same objects** as the parent — limits are global across the whole delegate tree. |
| `metrics` | **Same object** as the parent — cost accumulates globally. |
| `parent_iteration` | Parent's `iteration_flag.current_value` at delegation time. |
| `parent_metrics_snapshot` | Deep copy of the parent's `Metrics` at delegation time (`StateTracker.get_metrics_snapshot()`). |
| `start_id` | `event_stream.get_latest_event_id() + 1` — the delegate's history starts on top of the stream. |
| `inputs` / `outputs` | The subtask arguments in, and the subtask result out (read back by `end_delegate`). |

Because the counters are global, "how much did *this* delegate use?" needs subtraction. That is exactly what the two helpers do:

```
get_local_step()    = iteration_flag.current_value - parent_iteration
get_local_metrics() = metrics.diff(parent_metrics_snapshot)
```

---

## `ControlFlag` — limits as objects

`ControlFlag[T]` is a generic dataclass with three abstract methods and four fields: `limit_increase_amount`, `current_value`, `max_value`, plus a private `_hit_limit` latch (and a `headless_mode` field kept for compatibility — the real mode is passed in per call).

```mermaid
classDiagram
    class ControlFlag~T~ {
        <<abstract>>
        +T limit_increase_amount
        +T current_value
        +T max_value
        +bool headless_mode
        +bool _hit_limit
        +reached_limit() bool
        +increase_limit(headless_mode)
        +step()
    }
    class IterationControlFlag {
        step() increments current_value
        increase_limit() only when NOT headless
    }
    class BudgetControlFlag {
        step() does NOT increment
        increase_limit() rebases on current_value
    }
    ControlFlag~T~ <|-- IterationControlFlag : T = int
    ControlFlag~T~ <|-- BudgetControlFlag : T = float
```

The two subclasses share the shape but differ in three meaningful ways:

| | `IterationControlFlag` (int) | `BudgetControlFlag` (float) |
| --- | --- | --- |
| Who moves `current_value` | `step()` itself, `+= 1` | External — synced from `ConversationStats` |
| New ceiling on extension | `max_value += limit_increase_amount` | `max_value = current_value + limit_increase_amount` |
| Extension in headless mode | **Blocked** — a script must not silently run forever | **Allowed** |
| On limit | `RuntimeError('Agent reached maximum iteration…')` | `RuntimeError('Agent reached maximum budget…')` |

The budget flag rebases on `current_value` rather than adding to `max_value` because spend can overshoot the ceiling between checks (a single LLM call may cost more than the remaining headroom); adding to `max_value` could leave the flag already over the new limit.

### The check → error → extend cycle

`step()` raises **before** doing work, and only a user action clears the latch. This is how "the agent stopped, click continue" works:

```mermaid
stateDiagram-v2
    [*] --> UnderLimit
    UnderLimit --> UnderLimit : step() → current_value += 1
    UnderLimit --> HitLimit : reached_limit() is True<br/>_hit_limit = True<br/>raise RuntimeError
    HitLimit --> AgentError : AgentController._react_to_exception()<br/>→ AgentState.ERROR
    AgentError --> UnderLimit : user sets state RUNNING again<br/>maybe_increase_control_flags_limits()<br/>max_value grows, _hit_limit = False
    AgentError --> [*] : user gives up / session closes
    note right of HitLimit
        headless_mode blocks the
        iteration extension, so a
        script terminates instead
        of looping forever.
    end note
```

`increase_limit()` is a no-op unless `_hit_limit` is set, so repeatedly toggling the agent back to `RUNNING` cannot inflate the ceiling.

---

## `StateTracker` — the manager

`StateTracker` is constructed with only `(sid, file_store, user_id)`. Everything else arrives through method arguments, which keeps it free of a reference to the controller.

Its one piece of configuration is the history filter:

```python
self.agent_history_filter = EventFilter(
    exclude_types=(NullAction, NullObservation,
                   ChangeAgentStateAction, AgentStateChangedObservation),
    exclude_hidden=True,
)
```

Those four types are bookkeeping noise: they are how the controller talks to itself and to the UI, and they carry nothing an LLM should reason about. See [event_system](event_system.md) for `EventFilter` and the event taxonomy.

### Responsibilities

```mermaid
graph LR
    subgraph tracker["StateTracker"]
        A["set_initial_state()"]
        B["_init_history()"]
        C["add_history()"]
        D["close()"]
        E["get_trajectory()"]
        F["run_control_flags()"]
        G["sync_budget_flag_with_metrics()"]
        H["maybe_increase_control_flags_limits()"]
        I["get_metrics_snapshot()"]
        J["save_state()"]
    end

    A -->|"lifecycle"| L1["create or adopt State"]
    B -->|"history"| L1
    C -->|"history"| L1
    D -->|"history"| L1
    E -->|"export"| L2["evals / tests"]
    F -->|"limits"| L3["ControlFlags"]
    G -->|"limits"| L3
    H -->|"limits"| L3
    I -->|"delegation"| L4["parent snapshot"]
    J -->|"persistence"| L5["FileStore + ConversationStats"]
```

### `set_initial_state` — three sources of state

```mermaid
flowchart TD
    START["AgentController.__init__<br/>set_initial_state(state=…)"] --> Q{"state is None?"}
    Q -- yes --> NEW["Build fresh State:<br/>session_id = id minus '-delegate'<br/>iteration_flag from max_iterations<br/>budget_flag only if max_budget set<br/>start_id = 0"]
    Q -- no --> ADOPT["Adopt the given State<br/>(previous session, or parent's delegate state)"]
    ADOPT --> FIX{"start_id <= -1?"}
    FIX -- yes --> Z["start_id = 0"]
    FIX -- no --> K["keep start_id"]
    NEW --> ATTACH
    Z --> ATTACH
    K --> ATTACH
    ATTACH["state.conversation_stats = conversation_stats"] --> HIST["_init_history(event_stream)<br/>— always runs, even for a fresh state"]
```

Two details matter here:

- `budget_flag` is `None` when no budget was configured. Every read site therefore guards with `if self.state.budget_flag:` — an unlimited conversation has no flag at all rather than an infinite one.
- `_init_history()` is called unconditionally by the controller, *including* for brand-new states. A "new" state may still sit on top of an event stream that already has events (a reconnect where the pickle was lost), so history is always rebuilt from the stream.

### `_init_history` — rebuilding history, collapsing delegates

This is the most intricate method in the module. It fetches events in `[start_id, end_id]` through the filter, then **collapses delegate subtrees**: everything a child agent did is replaced by the `AgentDelegateAction` that started it and the `AgentDelegateObservation` that summarized it.

```mermaid
flowchart TD
    A["start_id = state.start_id (or 0)<br/>end_id = state.end_id or stream latest"] --> B{"start_id > end_id + 1?"}
    B -- yes --> B2["warn, history = [], return"]
    B -- no --> C["events = event_stream.search_events(<br/>start_id, end_id, filter=agent_history_filter)"]
    C --> D["Walk events, maintain a stack<br/>of unmatched AgentDelegateAction ids"]
    D --> E{"AgentDelegateObservation<br/>with a match on the stack?"}
    E -- yes --> F["pop → delegate_ranges += (action_id, obs_id)"]
    E -- no --> G["warn: observation without action, skip"]
    F --> H{"any delegate_ranges?"}
    G --> H
    H -- no --> I["history = events"]
    H -- yes --> J["For each sorted range:<br/>keep events before start_id,<br/>keep the action + observation,<br/>skip everything in between"]
    J --> K["append the tail after the last range"]
    K --> I
    I --> L["state.start_id = start_id"]
```

Why collapse? A delegate's internal reasoning is not the parent's business — including it would blow up the parent's context and confuse the parent agent about which actions were its own. A stack is used rather than a simple pair-match so nested delegations resolve to the outermost pair.

### `add_history` vs `close` — two views of the same run

The two methods differ on purpose:

| | `add_history(event)` (during the run) | `close(event_stream)` (at shutdown) |
| --- | --- | --- |
| Trigger | Every event the controller observes | `AgentController.close()` |
| Delegates | **Collapsed** (delegate internals were never appended to this controller's history) | **Expanded** — a full re-read of `[start_id, end_id]` through the filter |
| Purpose | The agent's working context | The complete record for evals, tests, and trajectory export |

So `close()` deliberately *rewrites* history to be wider than what the agent saw. `get_trajectory()` then serializes it via `event_to_trajectory`; `AgentController.get_trajectory()` asserts the controller is closed first, precisely because the pre-close history is the narrow, delegate-collapsed one.

### Per-step limit handling

```mermaid
sequenceDiagram
    participant AC as AgentController._step()
    participant STK as StateTracker
    participant CS as ConversationStats
    participant BF as BudgetControlFlag
    participant IF as IterationControlFlag
    participant AG as Agent

    AC->>STK: sync_budget_flag_with_metrics()
    STK->>CS: get_combined_metrics().accumulated_cost
    CS-->>STK: total cost across all LLM services
    STK->>BF: current_value = cost

    AC->>AC: _is_stuck()?  (StuckDetector)
    AC->>STK: run_control_flags()
    STK->>IF: step()  → raise if at max, else += 1
    STK->>BF: step()  → raise if at max (no increment)

    alt RuntimeError raised
        STK-->>AC: exception
        AC->>AC: _react_to_exception() → AgentState.ERROR
        Note over AC: user may resume → maybe_increase_control_flags_limits()
    else within limits
        AC->>AG: agent.step(state)
    end
```

`sync_budget_flag_with_metrics()` pulls from `ConversationStats`, not from `state.metrics`, because a conversation can run several LLM services at once — the agent's model, a condenser's model, a router's models (see [llm_layer](llm_layer.md) and [memory_and_condensers](memory_and_condensers.md)). `ConversationStats` is the only place that sums them all.

### `save_state`

```python
if self.sid and self.file_store:
    self.state.save_to_session(self.sid, self.file_store, self.user_id)
if self.state.conversation_stats:
    self.state.conversation_stats.save_metrics()
```

Two independent stores: the pickled `State` and the pickled per-service `Metrics` map. `State.save_to_session` detaches `conversation_stats` before pickling exactly so the two do not duplicate each other. `AgentController` calls `save_state()` on every `set_agent_state_to()` transition, so a crash loses at most one step.

---

## Lifecycle end to end

```mermaid
sequenceDiagram
    participant U as User / Client
    participant AS as AgentSession
    participant AC as AgentController
    participant STK as StateTracker
    participant S as State
    participant ES as EventStream
    participant FS as FileStore

    U->>AS: open / resume conversation
    AS->>FS: State.restore_from_session(sid, user_id)
    alt pickle found
        FS-->>AS: State (history empty, resume_state set, agent_state=LOADING)
    else nothing saved
        FS-->>AS: raises → initial_state = None
    end

    AS->>AC: AgentController(initial_state=…, conversation_stats=…)
    AC->>STK: StateTracker(sid, file_store, user_id)
    AC->>STK: set_initial_state(...)
    STK->>S: adopt or create
    AC->>STK: _init_history(event_stream)
    STK->>ES: search_events(start_id..end_id, filter)
    ES-->>STK: filtered events
    STK->>S: history = delegate-collapsed events

    loop each step while RUNNING
        ES-->>AC: new Event
        AC->>STK: add_history(event)
        STK->>S: append if filter includes it
        AC->>STK: sync_budget_flag_with_metrics()
        AC->>STK: run_control_flags()
        AC->>AC: agent.step(state) → reads state.view
        AC->>STK: save_state() on each state change
        STK->>FS: agent_state.pkl + conversation_stats.pkl
    end

    U->>AC: close
    AC->>STK: close(event_stream)
    STK->>S: history = full range (delegates expanded)
    AC->>STK: save_state()
```

---

## Design notes and gotchas

- **The event stream is the source of truth; `State` is an index into it.** Any bug where history looks wrong is usually a `start_id` / `end_id` bug, not a lost-data bug.
- **`AgentController.state` is the same object as `StateTracker.state`.** The controller keeps a direct alias (with a `TODO` acknowledging it) so older code paths keep working. Mutating either mutates both.
- **Limits are shared down the delegate tree, metrics are shared globally, and only the *snapshots* are per-delegate.** Read `get_local_step()` / `get_local_metrics()` for per-subtask numbers; read the flags for the whole task.
- **Pickle is the persistence format.** That makes `State` sensitive to class renames and field removals, which is why `__getstate__` / `__setstate__` carry explicit migration logic. Adding a field is safe (`__setstate__` fills defaults); renaming or removing one needs a migration branch.
- **`headless_mode` changes the meaning of a hit limit.** Interactively, hitting the iteration cap is a pause the user can extend. In headless/eval runs, it is a hard stop. The budget flag intentionally does *not* make this distinction.
- **`TrafficControlState`, `iteration`, `local_iteration`, `max_iterations`, `local_metrics`, `delegates`** are all deprecated. Do not read them; they are stripped on the next save.

## Related modules

- [agent_controller_core](agent_controller_core.md) — `AgentController`, the only writer of this state.
- [agent_controller_safeguards](agent_controller_safeguards.md) — `StuckDetector` (reads `state.view`) and `ReplayManager`.
- [agent_controller](agent_controller.md) — parent module overview.
- [event_system](event_system.md) — `EventStream`, `EventFilter`, event types.
- [memory_and_condensers](memory_and_condensers.md) — `View`, condensers, and `state.extra_data` metadata.
- [llm_layer](llm_layer.md) — `Metrics`, `LLMRegistry`.
- [server_sessions](server_sessions.md) — `AgentSession`, `ConversationStats`.
- [storage_backends](storage_backends.md) — `FileStore` implementations behind `save_to_session`.
- [core_schema_and_runtime_support](core_schema_and_runtime_support.md) — the `AgentState` enum.
- [agents](agents.md) — consumers of `State` inside `agent.step()`.
