# Agent Controller

## Purpose

The `agent_controller` module is the **engine room** of OpenHands. It is the piece that
takes an agent (an LLM-driven decision maker) and actually *runs* it: it feeds the agent
events, asks it for the next action, publishes that action, waits for the result, and
decides when to stop.

Everything else in the system either produces events for the controller or consumes the
events it produces. The controller itself does not talk to an LLM, does not run shell
commands, and does not read files. It only decides **when** the agent may act, **whether**
that action is allowed, and **what** the agent is allowed to remember.

In one sentence: *the agent controller turns a stateless `step(state) -> action` function
into a long-running, resumable, safe, budget-limited conversation.*

### Responsibilities at a glance

| Responsibility | Meaning |
| --- | --- |
| Event loop | Subscribe to the event stream, react to each event, call the agent when it is the agent's turn |
| State machine | Own the `AgentState` transitions (`LOADING` → `RUNNING` → `FINISHED` / `ERROR` / …) |
| Limits | Stop the agent when it runs out of iterations or money |
| Loop safety | Detect a stuck agent that repeats itself forever |
| Confirmation | Hold risky actions until a human (or a policy) approves them |
| Delegation | Spawn a child controller so one agent can hand a subtask to another agent |
| Persistence | Save and restore the whole run so a conversation survives a restart |
| Replay | Re-run a recorded trajectory step by step |
| Error handling | Turn LLM/provider failures into user-readable statuses instead of crashes |

---

## Where it sits in the system

The controller is the middle of a three-way sandwich. Above it is the session/server
layer that creates it; beside it is the agent that decides; below it is the runtime that
executes.

```mermaid
graph TB
    subgraph Clients["Clients"]
        CLI["CLI / Frontend"]
    end

    subgraph Service["Conversation Service Tier"]
        AS["AgentSession / WebSession"]
        CS["ConversationStats"]
    end

    subgraph Reasoning["Agent Reasoning Core"]
        AC["<b>AgentController</b><br/>(this module)"]
        AG["Agent implementations<br/>CodeAct, Browsing, ReadOnly, Loc, Dummy"]
        MEM["Memory + Condensers"]
        LLM["LLM layer<br/>registry, routing, metrics"]
        SEC["Security analyzers"]
    end

    subgraph Foundation["Shared Platform Foundation"]
        ES["EventStream"]
        FS["FileStore"]
    end

    subgraph Runtime["Sandboxed Execution Layer"]
        RT["Runtime<br/>bash, jupyter, browser, files"]
    end

    CLI --> AS
    AS -->|creates + owns| AC
    AS --> CS
    CS -.->|cost + token totals| AC

    AC -->|"step(state)"| AG
    AG --> LLM
    AC -->|analyze action| SEC
    MEM -.->|recall + condense| ES

    AC <-->|publish / subscribe| ES
    ES <--> RT
    ES <--> MEM
    AC -->|save_state| FS
```

Key point: **the controller and the runtime never call each other directly.** They only
meet through the [event stream](event_system.md). The controller adds an `Action`; the
runtime notices it, executes it, and adds an `Observation`; the controller notices that and
lets the agent take another step.

---

## Architecture of the module

The module is small in file count but dense in behaviour. It splits cleanly into three
concerns: **orchestration**, **state**, and **execution safeguards**.

```mermaid
graph TB
    subgraph Orchestration["Orchestration — agent_controller_core.md"]
        AC["AgentController<br/><i>event loop, state machine,<br/>delegation, confirmation</i>"]
    end

    subgraph StateMgmt["State — agent_controller_state.md"]
        ST["StateTracker<br/><i>persistence + history</i>"]
        S["State<br/><i>the run's data</i>"]
        CF["ControlFlag<br/>IterationControlFlag<br/>BudgetControlFlag"]
        TCS["TrafficControlState<br/><i>(deprecated)</i>"]
    end

    subgraph Safeguards["Safeguards — agent_controller_safeguards.md"]
        SD["StuckDetector<br/><i>loop detection</i>"]
        RM["ReplayManager<br/><i>trajectory replay</i>"]
    end

    AC -->|owns one| ST
    AC -->|owns one| SD
    AC -->|owns one| RM
    ST -->|owns the| S
    S -->|holds| CF
    S -.->|legacy field| TCS
    SD -->|reads history from| S
    AC -.->|"self.state (alias)"| S

    style AC fill:#e1f0ff
    style ST fill:#fff4e1
    style SD fill:#ffe8e8
```

### Component roles

| Component | File | Role |
| --- | --- | --- |
| `AgentController` | `controller/agent_controller.py` | The orchestrator. Subscribes to events, drives the agent step, manages state transitions, delegation, confirmation, and error mapping. |
| `StateTracker` | `controller/state/state_tracker.py` | Owns the `State` object. Rebuilds history from the event stream, saves/loads it, steps the control flags, and syncs budget with real spend. |
| `State` / `TrafficControlState` | `controller/state/state.py` | The serializable record of a run: history, iteration/budget flags, metrics, delegate level, outputs, last error. `TrafficControlState` is a deprecated leftover. |
| `ControlFlag` | `controller/state/control_flags.py` | Generic limit guard. `IterationControlFlag` counts steps; `BudgetControlFlag` watches accumulated cost. Both raise when the ceiling is hit. |
| `StuckDetector` | `controller/stuck.py` | Pattern-matches recent history for five kinds of infinite loop. |
| `ReplayManager` | `controller/replay.py` | Replaces the agent's decision with a pre-recorded action while replaying a trajectory. |

---

## The core loop

This is the single most important flow in the module. Every turn of the agent goes through it.

```mermaid
sequenceDiagram
    participant U as User
    participant ES as EventStream
    participant AC as AgentController
    participant STK as StateTracker
    participant SD as StuckDetector
    participant AG as Agent
    participant RT as Runtime

    U->>ES: MessageAction (user)
    ES->>AC: on_event(event)
    AC->>STK: add_history(event)
    AC->>ES: RecallAction (fetch microagent context)
    AC->>AC: set_agent_state_to(RUNNING)

    Note over AC: should_step(event) == true

    AC->>STK: sync_budget_flag_with_metrics()
    AC->>SD: is_stuck()?
    SD-->>AC: false
    AC->>STK: run_control_flags()
    Note right of STK: raises if out of<br/>iterations or budget

    AC->>AG: step(state)
    AG-->>AC: Action

    alt runnable + confirmation mode
        AC->>AC: _handle_security_analyzer(action)
        AC->>AC: state = AWAITING_USER_CONFIRMATION
    end

    AC->>AC: _pending_action = action
    AC->>ES: add_event(action)
    ES->>RT: execute
    RT->>ES: Observation
    ES->>AC: on_event(observation)
    AC->>AC: clear _pending_action
    Note over AC: loop repeats
```

### The three gates before every step

`_step()` refuses to run unless all three gates are open:

1. **State gate** — the agent state must be `RUNNING`.
2. **Pending-action gate** — no action may be in flight (`_pending_action is None`).
   This is what makes the loop turn-based: one action out, one observation back.
3. **Limit gate** — the iteration and budget flags must not be at their ceiling, and the
   stuck detector must say the agent is making progress.

---

## Agent state machine

The controller owns `AgentState` transitions. Every transition emits an
`AgentStateChangedObservation` and triggers a state save, so the UI and the disk are
always in sync with reality.

```mermaid
stateDiagram-v2
    [*] --> LOADING

    LOADING --> RUNNING: user message

    RUNNING --> AWAITING_USER_INPUT: agent asks a question
    AWAITING_USER_INPUT --> RUNNING: user replies

    RUNNING --> AWAITING_USER_CONFIRMATION: risky action + confirmation mode
    AWAITING_USER_CONFIRMATION --> USER_CONFIRMED: approve
    AWAITING_USER_CONFIRMATION --> USER_REJECTED: reject
    USER_CONFIRMED --> RUNNING: action re-published
    USER_REJECTED --> AWAITING_USER_INPUT

    RUNNING --> RATE_LIMITED: provider 429, retries left
    RATE_LIMITED --> RUNNING: retry succeeds

    RUNNING --> FINISHED: AgentFinishAction
    RUNNING --> REJECTED: AgentRejectAction
    RUNNING --> ERROR: exception / limit hit / stuck
    RUNNING --> STOPPED: user stop
    RUNNING --> PAUSED: user pause
    PAUSED --> RUNNING: resume

    ERROR --> RUNNING: resume (limits may be raised)

    FINISHED --> [*]
    REJECTED --> [*]
    STOPPED --> [*]
```

Two transitions deserve attention:

* **`STOPPED` / `ERROR` triggers `_reset()`.** If an action was in flight and it carried
  tool-call metadata, the controller synthesizes an `ErrorObservation` for it. Without
  this, the conversation history would contain a tool call with no result — which most LLM
  APIs reject outright.
* **`ERROR` → `RUNNING` may raise the limits.** In interactive (non-headless) mode,
  resuming from an error calls `maybe_increase_control_flags_limits`, so clicking "resume"
  grants the agent another batch of iterations or budget.

---

## Delegation: controllers inside controllers

OpenHands is multi-agent. When an agent emits an `AgentDelegateAction`, the parent
controller builds a **child controller** with a different agent class, and forwards every
event to it until it finishes.

```mermaid
graph TB
    subgraph Parent["Parent AgentController"]
        P["state.delegate_level = 0<br/>subscribed to EventStream"]
    end

    subgraph Child["Delegate AgentController"]
        C["state.delegate_level = 1<br/>is_delegate = True<br/>NOT subscribed"]
    end

    ES["EventStream"]

    ES -->|"on_event"| P
    P -->|"forwards while delegate alive"| C
    C -->|"adds actions"| ES
    P -->|"AgentDelegateObservation on finish"| ES

    style P fill:#e1f0ff
    style C fill:#f0e1ff
```

Rules that make this work:

* **Only the root controller subscribes** to the event stream. Delegates get events
  hand-delivered by their parent (`is_delegate=True` skips the subscription). This avoids
  double processing.
* **Shared counters, separate accounting.** The child reuses the parent's
  `iteration_flag`, `budget_flag`, and `Metrics` object, so global limits apply across the
  whole tree. It also stores a `parent_metrics_snapshot` and `parent_iteration`, which let
  `get_local_metrics()` / `get_local_step()` report *only* the delegate's own share.
* **The child starts on top of the stream** (`start_id = latest_event_id + 1`), so it
  never sees the parent's earlier history.
* **On finish the parent emits an `AgentDelegateObservation`** carrying the child's
  outputs, and copies the delegate action's `tool_call_metadata` onto it so the parent's
  LLM sees a proper tool result.

---

## Data flow: what the agent is allowed to see

The controller does not hand the agent the raw event stream. There are three filtering
layers between the stream and the LLM prompt.

```mermaid
graph LR
    ES["EventStream<br/>all events"]
    HF["EventFilter<br/><i>drop Null*, ChangeAgentState,<br/>AgentStateChanged, hidden</i>"]
    H["state.history"]
    V["state.view<br/><i>apply condensation events</i>"]
    AG["Agent.step()"]
    LLM["LLM prompt"]

    ES --> HF --> H --> V --> AG --> LLM

    style HF fill:#fff4e1
    style V fill:#e1ffe1
```

1. **`EventFilter`** (in `StateTracker`) removes bookkeeping noise. Delegate *internals*
   are also collapsed away — only the delegate action and its observation survive, so the
   parent never re-reads its child's work.
2. **`State.view`** applies condensation semantics: events marked forgotten by a
   `CondensationAction` are dropped and a summary is spliced in at the recorded offset.
   The view is cached against a cheap `len(history)` checksum. Condensation strategies
   themselves live in [memory_and_condensers](memory_and_condensers.md).
3. **`truncate_content`** caps individual observation text at
   `llm.config.max_message_chars` for logging.

### Context-window overflow is a feedback loop, not a crash

When the LLM rejects a prompt as too long, the controller does not fail the run. It emits
a `CondensationRequestAction` back into the stream. The condenser reacts, produces a
`CondensationAction`, the view shrinks, and the agent steps again with a smaller prompt.

```mermaid
graph LR
    A["Agent.step()"] -->|ContextWindowExceeded| B["CondensationRequestAction"]
    B --> C["Condenser"]
    C --> D["CondensationAction"]
    D --> E["state.view shrinks"]
    E --> A

    style B fill:#ffe8e8
    style D fill:#e1ffe1
```

This only happens if `agent.config.enable_history_truncation` is on; otherwise the
controller raises `LLMContextWindowExceedError`. If the loop itself starts spinning, the
`StuckDetector`'s context-window scenario catches it.

---

## Safety layers

Three independent mechanisms keep a run from going wrong in three different ways.

```mermaid
graph TB
    A["Agent proposes an Action"]

    A --> B{"Runnable and<br/>confirmation mode?"}
    B -->|no| F["Publish to EventStream"]
    B -->|yes| C["SecurityAnalyzer.security_risk(action)"]

    C --> D{"HIGH risk, or<br/>no analyzer at all?"}
    D -->|no| F
    D -->|yes| E["AWAITING_USER_CONFIRMATION"]
    E -->|human approves| F
    E -->|human rejects| G["Action dropped"]

    style C fill:#fff4e1
    style E fill:#ffe8e8
```

| Layer | Guards against | Failure mode |
| --- | --- | --- |
| `ControlFlag` | Runaway cost and endless iteration | `RuntimeError` → `ERROR` state, resumable with raised limits |
| `StuckDetector` | Semantic loops (same action forever) | `AgentStuckInLoopError` → `ERROR` state |
| Security analyzer + confirmation | Dangerous side effects | Action parked in `AWAITING_USER_CONFIRMATION` |

The confirmation path is deliberately **fail-safe**: with no analyzer configured, every
runnable action is labelled `UNKNOWN` risk, which in confirmation mode means *ask the
human*. Analyzer implementations live in [security_analyzers](security_analyzers.md).

---

## Error handling

`_step_with_exception_handling` wraps every step. Known provider errors are passed through
so `_react_to_exception` can map them to a specific `RuntimeStatus`; unknown ones are
wrapped in a generic, user-friendly `RuntimeError`.

```mermaid
graph TB
    E["Exception during step"]

    E --> P{"Parse phase errors?<br/>LLMMalformedAction,<br/>LLMNoAction, FunctionCall*"}
    P -->|yes| PE["ErrorObservation to stream<br/><b>agent keeps going</b>"]

    E --> C{"Context window<br/>exceeded?"}
    C -->|yes| CE["CondensationRequestAction<br/><b>agent keeps going</b>"]

    E --> R{"RateLimitError?"}
    R -->|retries left| RL["RATE_LIMITED"]
    R -->|exhausted| ERR

    E --> M{"Auth / ServiceUnavailable /<br/>InternalServer / ContentPolicy /<br/>ExceededBudget?"}
    M -->|yes| MS["Specific RuntimeStatus<br/>via status_callback"]
    MS --> ERR

    E --> U["Anything else"]
    U --> ERR["ERROR state<br/>state.last_error set"]

    style PE fill:#e1ffe1
    style CE fill:#e1ffe1
    style ERR fill:#ffe8e8
```

Note the split: **parse errors and context overflow are recoverable** — they go back into
the stream as events and the agent tries again. Everything else ends the run in `ERROR`,
from which the user can resume.

---

## Persistence and resume

A conversation must survive a process restart. The controller saves on **every** state
transition, not just at the end.

```mermaid
sequenceDiagram
    participant AC as AgentController
    participant STK as StateTracker
    participant FS as FileStore
    participant ES as EventStream

    Note over AC: --- shutdown ---
    AC->>STK: save_state()
    STK->>FS: pickle + base64 State (history stripped)
    STK->>FS: conversation_stats.save_metrics()

    Note over AC: --- restart ---
    AC->>STK: set_initial_state(restored State)
    Note right of STK: agent_state = LOADING<br/>resume_state = previous, if resumable
    AC->>STK: _init_history(event_stream)
    STK->>ES: search_events(start_id..end_id, filter)
    ES-->>STK: events
    STK->>STK: collapse delegate ranges
    Note over STK: history rebuilt
```

The important design choice: **history is never pickled.** `State.__getstate__` blanks it
out, along with cached views and deprecated fields. The event stream is the single source
of truth, and history is always reconstructed from it. This keeps saved state small and
prevents the two from drifting apart.

---

## Sub-modules

The module's detail is documented in three focused pages.

```mermaid
graph LR
    M["agent_controller.md<br/><i>this page</i>"]
    A["agent_controller_core.md"]
    B["agent_controller_state.md"]
    C["agent_controller_safeguards.md"]
    C1["agent_controller_safeguards_<br/>stuck_detection.md"]
    C2["agent_controller_safeguards_<br/>replay.md"]

    M --> A
    M --> B
    M --> C
    C --> C1
    C --> C2
    A -.->|drives| B
    A -.->|consults| C
    C -.->|reads history from| B
```

### [agent_controller_core](agent_controller_core.md)

The `AgentController` itself — the event loop, the `AgentState` machine, delegation,
confirmation flow, pending-action tracking, and the error-to-status mapping. Read this
first if you want to know *when* and *why* the agent acts.

*Covers:* `AgentController`

### [agent_controller_state](agent_controller_state.md)

Everything about the run's data: the `State` dataclass, its pickle/base64 session format
and backward-compatibility shims, the `StateTracker` that owns it and rebuilds history
from the event stream, and the `ControlFlag` family that enforces iteration and budget
ceilings.

*Covers:* `StateTracker`, `State`, `TrafficControlState`, `ControlFlag`,
`IterationControlFlag`, `BudgetControlFlag`

### [agent_controller_safeguards](agent_controller_safeguards.md)

The two helpers that watch the agent rather than drive it: `StuckDetector` (five loop
patterns, from identical action/observation pairs to context-window thrash) and
`ReplayManager` (deterministic re-execution of a recorded trajectory).

*Covers:* `StuckDetector`, `ReplayManager`

---

## Related modules

| Module | Relationship |
| --- | --- |
| [agents](agents.md) | Supplies the `Agent` implementations the controller drives, plus the `AgentFinishedCritic`. |
| [event_system](event_system.md) | The `EventStream` the controller subscribes to and publishes on — the only channel between the controller and the runtime. |
| [memory_and_condensers](memory_and_condensers.md) | Answers `RecallAction`s and produces the `CondensationAction`s that shape `State.view`. |
| [llm_layer](llm_layer.md) | The `LLMRegistry` the controller passes to delegate agents, and the `Metrics` objects the budget flag reads. |
| [security_analyzers](security_analyzers.md) | Implements the `SecurityAnalyzer` interface the controller calls before risky actions. |
| [server_sessions](server_sessions.md) | `AgentSession` builds and owns the controller; `ConversationStats` supplies combined cost/token totals. |
| [core_schema_and_runtime_support](core_schema_and_runtime_support.md) | Defines `AgentState`, `ActionType`, `ObservationType`, and `RuntimeStatus`. |
| [storage_backends](storage_backends.md) | The `FileStore` implementations the state is pickled into. |
| [runtime_implementations](runtime_implementations.md) | Executes the actions the controller publishes and returns observations. |
| [core_configuration](core_configuration.md) | `AgentConfig`, `LLMConfig`, and `SecurityConfig` shape controller behaviour. |
