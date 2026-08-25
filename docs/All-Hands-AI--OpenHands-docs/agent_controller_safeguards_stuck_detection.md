# Agent Controller Safeguards — Stuck Detection

## Introduction

An LLM agent can get trapped. It runs the same command again and again, retries a broken
edit forever, or talks to itself in circles. Nothing crashes, so no error stops it. It just
burns iterations, tokens, and money until a hard limit kicks in.

The **stuck detection** module is the guard against that. It holds one class,
`StuckDetector` (`openhands/controller/stuck.py`), which looks at the agent's event history
and answers a single question: *is this agent repeating itself instead of making progress?*

It is a **pure, read-only predicate**. It never sends events, never changes state, never
calls an LLM. It just reads the history list and returns `True` or `False`. The
[`AgentController`](agent_controller_core.md) decides what to do with that answer — it raises
`AgentStuckInLoopError` and moves the agent into the `ERROR` state.

Together with its sibling [`ReplayManager`](agent_controller_safeguards_replay.md), this
module makes up the [safeguards layer](agent_controller.md) of the controller.

---

## Where this module sits

`StuckDetector` is a small leaf. It is owned by one object (`AgentController`), reads one
piece of data (`State.history`), and is consulted at one point (the start of every step).

```mermaid
graph TB
    subgraph AC["agent_controller (parent module)"]
        subgraph CORE["agent_controller_core"]
            Ctrl["AgentController<br/><i>_step() / _is_stuck()</i>"]
        end
        subgraph ST["agent_controller_state"]
            State["State<br/><i>history: list[Event]</i>"]
            Tracker["StateTracker"]
        end
        subgraph SG["agent_controller_safeguards"]
            SD["StuckDetector<br/><b>(this module)</b>"]
            RM["ReplayManager"]
        end
    end

    subgraph FOUND["shared_platform_foundation"]
        ES["EventStream"]
        EV["Action / Observation<br/>event classes"]
        LOG["openhands_logger"]
    end

    ES -->|"events appended"| Tracker
    Tracker -->|"maintains"| State
    Ctrl -->|"owns one instance"| SD
    Ctrl -->|"owns one instance"| RM
    SD -->|"reads (never writes)"| State
    SD -->|"isinstance checks against"| EV
    SD -->|"logger.warning on detection"| LOG
    SD -.->|"bool verdict"| Ctrl

    style SD fill:#ffe6b3,stroke:#d68910,stroke-width:3px
```

Related module docs:

| Module | Why it matters here |
| --- | --- |
| [agent_controller_core](agent_controller_core.md) | The only caller. Owns the detector and reacts to its verdict. |
| [agent_controller_state](agent_controller_state.md) | Owns `State.history`, the sole input. Also owns the iteration/budget `ControlFlag`s, the *other* kind of limit. |
| [agent_controller_safeguards_replay](agent_controller_safeguards_replay.md) | Sibling safeguard in the same layer. |
| [event_system](event_system.md) | Defines `Event`, `EventSource`, `Action`, `Observation`, `CmdOutputObservation`. |
| [memory_and_condensers](memory_and_condensers.md) | Produces the `AgentCondensationObservation` events that scenario 5 watches. |
| [core_schema_and_runtime_support](core_schema_and_runtime_support.md) | `AgentState`, `ActionType`, `ObservationType`. |
| [logging](logging.md) | The logger used to announce every detection. |

---

## Component structure

`StuckDetector` has one public method and a set of private scenario checkers. Each checker
owns exactly one loop pattern, so patterns can be added or tuned in isolation.

```mermaid
classDiagram
    class StuckDetector {
        +SYNTAX_ERROR_MESSAGES: list[str]
        +state: State
        +__init__(state: State)
        +is_stuck(headless_mode: bool) bool
        -_is_stuck_repeating_action_observation(actions, observations) bool
        -_is_stuck_repeating_action_error(actions, observations) bool
        -_is_stuck_monologue(filtered_history) bool
        -_is_stuck_action_observation_pattern(filtered_history) bool
        -_is_stuck_context_window_error(filtered_history) bool
        -_check_for_consistent_line_error(observations, msg) bool
        -_check_for_consistent_invalid_syntax(observations, msg) bool
        -_eq_no_pid(obj1: Event, obj2: Event) bool
    }

    class State {
        +history: list[Event]
    }

    class AgentController {
        -_stuck_detector: StuckDetector
        -delegate: AgentController
        +headless_mode: bool
        -_is_stuck() bool
        -_step()
    }

    AgentController --> StuckDetector : owns
    AgentController --> State : owns
    StuckDetector --> State : reads history
    StuckDetector ..> AgentController : returns bool
```

Only three names cross the module boundary:

- **In:** a `State` object at construction time; a `headless_mode` flag per call.
- **Out:** a `bool`, plus warning log lines.

That narrow surface is deliberate. The detector can be unit-tested by handing it a fake
`State` with a hand-built list of events — no runtime, no LLM, no event stream needed.

---

## The one integration point

`AgentController._step()` asks the question **before every agent step**, right after budget
sync and right before the iteration/budget control flags are run.

```mermaid
flowchart TD
    S1["AgentController._step() is called"] --> S2{"agent state == RUNNING<br/>and no pending action?"}
    S2 -->|no| Skip["return early, no step"]
    S2 -->|yes| S3["state_tracker.sync_budget_flag_with_metrics()"]
    S3 --> S4["_is_stuck()"]

    S4 --> D1{"a delegate exists<br/>and delegate._is_stuck()?"}
    D1 -->|yes| Verdict["stuck"]
    D1 -->|no| SD["StuckDetector.is_stuck(headless_mode)"]

    SD --> R1["read State.history"]
    R1 --> R2["select window, filter noise,<br/>run the 5 scenario checks"]
    R2 --> R3{"a pattern matched?"}
    R3 -->|yes| Warn["logger.warning(...)"] --> Verdict
    R3 -->|no| OK["not stuck"]

    Verdict --> E1["_react_to_exception(AgentStuckInLoopError)"]
    E1 --> E2["state.last_error set<br/>agent state → ERROR<br/>step aborted"]

    OK --> C1["state_tracker.run_control_flags()<br/>(iteration and budget limits)"]
    C1 --> C2["agent.step(state) → next Action"]

    style Verdict fill:#f8b4b4,stroke:#c0392b
    style OK fill:#c6e5b3,stroke:#27ae60
    style SD fill:#ffe6b3,stroke:#d68910,stroke-width:2px
```

Read top to bottom, the controller checks its own preconditions, then the delegate, then
this module, and only reaches the agent if every check passes.

Two details are worth remembering:

- **Delegates are checked first, and recursively.** `AgentController._is_stuck()` calls
  `self.delegate._is_stuck()` before checking itself. A child agent spinning in a loop
  stops the whole chain, because the parent is blocked while the delegate runs.
- **A stuck verdict is terminal, not corrective.** The module does not nudge the agent or
  inject a hint. It hands the controller an exception, and the conversation stops with an
  error. The user (or an outer harness) decides what happens next.

---

## How a verdict is reached

`is_stuck()` runs a fixed pipeline: pick a window of history, clean it, bail out if it is
too short, build the last-N action/observation lists, then try each scenario in order. The
first scenario that matches wins and short-circuits.

```mermaid
flowchart TD
    Start(["is_stuck(headless_mode)"]) --> Mode{headless_mode?}

    Mode -->|"False<br/>(interactive)"| Slice["find last MessageAction<br/>with source == USER<br/>→ keep only events after it"]
    Mode -->|"True<br/>(headless / tests)"| All["use the whole history"]

    Slice --> Filter
    All --> Filter

    Filter["drop USER MessageActions<br/>drop NullAction / NullObservation"]
    Filter --> Len{"len(filtered) >= 3 ?"}
    Len -->|no| FalseOut(["return False"])

    Len -->|yes| Window["walk history backwards:<br/>collect last 4 Actions<br/>and last 4 Observations"]

    Window --> S1{"Scenario 1<br/>4 identical action+observation pairs?"}
    S1 -->|yes| TrueOut(["return True"])
    S1 -->|no| S2{"Scenario 2<br/>3 identical actions, all erroring?"}
    S2 -->|yes| TrueOut
    S2 -->|no| S3{"Scenario 3<br/>3 identical agent messages,<br/>no observation between?"}
    S3 -->|yes| TrueOut
    S3 -->|no| S4{"len >= 6 and<br/>Scenario 4: A,B,A,B,A,B pattern?"}
    S4 -->|yes| TrueOut
    S4 -->|no| S5{"len >= 10 and<br/>Scenario 5: condensation-only run?"}
    S5 -->|yes| TrueOut
    S5 -->|no| FalseOut

    style TrueOut fill:#f8b4b4,stroke:#c0392b
    style FalseOut fill:#c6e5b3,stroke:#27ae60
```

### Step 1 — choosing the window (headless vs interactive)

`headless_mode` mirrors the same flag on `AgentController`.

| Mode | Window | Reasoning |
| --- | --- | --- |
| `headless_mode=True` (scripted runs, benchmarks, tests) | The entire history | Nobody is watching. Any repetition anywhere is worth catching. |
| `headless_mode=False` (interactive chat / UI) | Only events **after the last user message** | A new user message means new intent. Repetition from before it should not count against the agent now. |

This matters in practice: a user often asks the agent to redo something similar. In
interactive mode, that fresh instruction resets the detector's view of the world.

### Step 2 — cleaning the window

Two kinds of noise are removed:

- **User `MessageAction`s** — the human is not the one looping.
- **`NullAction` / `NullObservation`** — placeholder events that would break the
  action/observation alternation the later scenarios rely on.

The filter is written to be correct in both modes. In headless mode it actively strips user
messages out of the full history; in interactive mode it is a no-op for user messages,
because the slice already cut them away.

If fewer than **3** events survive, the answer is `False`. Three steps is the floor for
saying anything about a loop.

### Step 3 — building the comparison windows

The detector walks the cleaned history **backwards** and collects up to 4 `Action`s and up
to 4 `Observation`s into two separate lists. Because of the reverse walk, **index 0 is the
most recent event**. The two lists are independent — the detector does not require actions
and observations to strictly alternate, and it does not care how far apart they are in the
raw history.

```mermaid
flowchart LR
    subgraph H["filtered_history (oldest → newest)"]
        direction LR
        E1["Act A"] --> E2["Obs X"] --> E3["Act A"] --> E4["Obs X"] --> E5["Act A"] --> E6["Obs X"] --> E7["Act A"] --> E8["Obs X"]
    end

    H --> LA["last_actions<br/>[A, A, A, A]<br/>index 0 = newest"]
    H --> LO["last_observations<br/>[X, X, X, X]<br/>index 0 = newest"]

    LA --> Check["scenario checks"]
    LO --> Check
```

---

## The five loop patterns

| # | Name | Needs | Window | What it catches | Log line |
| --- | --- | --- | --- | --- | --- |
| 1 | Repeating action + observation | 4 actions **and** 4 observations | last 4 | Perfect standstill: same action, same result, four times | `Action, Observation loop detected` |
| 2 | Repeating action + error | 3 actions and 3 observations | last 3 | Same action failing repeatedly (`ErrorObservation`, or Jupyter `SyntaxError`) | `Action, ErrorObservation loop detected` / `Action, IPythonRunCellObservation loop detected` |
| 3 | Monologue | 3 agent messages | all filtered | Agent repeating the same message to itself with no observation in between | `Repeated MessageAction with source=AGENT detected` |
| 4 | Alternating pattern | 6 actions **and** 6 observations, ≥6 filtered events | last 6 | A→B→A→B→A→B ping-pong (e.g. edit, test, edit, test, unchanged) | `Action, Observation pattern detected` |
| 5 | Context-window error loop | ≥10 condensation observations, ≥10 filtered events | all filtered | Condenser firing over and over without the agent doing anything in between | `Context window error loop detected - repeated condensation events` |

The order is cheapest-and-most-obvious first. Every check is a pure comparison over a small
list, so running all five on every step is inexpensive relative to an LLM call.

### Scenario 1 — dead standstill

All four recent actions equal each other, **and** all four recent observations equal each
other. This is the clearest signal: the agent tried the identical thing four times and got
the identical answer four times. Comparison uses `_eq_no_pid` (see below), so cosmetic
differences like process IDs do not save the agent.

### Scenario 2 — same action, repeated failure

Three identical recent actions plus three failing observations. "Failing" means one of:

- All three observations are `ErrorObservation`, **or**
- All three are `IPythonRunCellObservation` carrying the *same* Python syntax error.

The syntax-error branch exists because a broken code cell does not produce an
`ErrorObservation` — it produces normal Jupyter output that happens to contain a traceback.
The detector therefore parses the observation text. Three specific messages are tracked in
`SYNTAX_ERROR_MESSAGES`, and they are checked by two different helpers:

```mermaid
flowchart TD
    S2["3 identical actions +<br/>3 IPythonRunCellObservations"] --> Loop["for each message in SYNTAX_ERROR_MESSAGES"]

    Loop --> M1{"'unterminated string literal<br/>(detected at line' ?"}
    Loop --> M2{"'invalid syntax. Perhaps you<br/>forgot a comma?' or<br/>'incomplete input' ?"}

    M1 --> C1["_check_for_consistent_line_error"]
    M2 --> C2["_check_for_consistent_invalid_syntax"]

    C1 --> C1a["each obs: >= 3 lines"]
    C1a --> C1b["last 2 lines are our own Jupyter markers:<br/>'[Jupyter current working directory:'<br/>'[Jupyter Python interpreter:'"]
    C1b --> C1c["error message appears in the<br/>3rd-to-last line"]
    C1c --> C1d["all 3 error lines found AND<br/>textually identical"]

    C2 --> C2a["each obs: >= 6 lines<br/>(a real syntax error is at least 6)"]
    C2a --> C2b["first line starts with 'Cell In[1], line'"]
    C2b --> C2c["last 2 lines are Jupyter markers<br/>and error msg is in 3rd-to-last"]
    C2c --> C2d["all first lines identical AND<br/>exactly 3 valid observations AND<br/>error lines identical"]

    C1d --> Stuck(["stuck"])
    C2d --> Stuck

    style Stuck fill:#f8b4b4,stroke:#c0392b
```

Both helpers insist that the *same* error appears at the *same* place. That is the point:
an agent that keeps hitting `SyntaxError` on **different** lines is at least moving. One
that hits the identical error at the identical line three times is not.

The structural checks (Jupyter marker lines, the `Cell In[1], line` prefix, the minimum
line counts) tie this scenario to the exact output format of the
[Jupyter plugin](runtime_plugins.md). If that format changes, these two helpers go quiet —
they fail closed, reporting "not stuck" rather than a false positive.

### Scenario 3 — monologue

Collect every `MessageAction` whose source is `AGENT`, keeping its index. If the last three
are all equal, look at the raw slice between the first and last of them. If **no
`Observation` appears in that gap**, the agent is talking to itself with no new input, and
it is declared stuck.

The observation check is the escape hatch. If something happened between the repeated
messages, the agent still has new information and might recover, so no verdict is issued.

```mermaid
flowchart LR
    subgraph A["Stuck: no observation between"]
        M1["msg 'Let me check'"] --> M2["msg 'Let me check'"] --> M3["msg 'Let me check'"]
    end
    subgraph B["Not stuck: observation between"]
        N1["msg 'Let me check'"] --> O1["Observation"] --> N2["msg 'Let me check'"] --> O2["Observation"] --> N3["msg 'Let me check'"]
    end
    style A fill:#f8b4b4,stroke:#c0392b
    style B fill:#c6e5b3,stroke:#27ae60
```

Note that this scenario compares messages with plain `==`, not `_eq_no_pid` — messages have
no process IDs to ignore.

### Scenario 4 — alternating ping-pong

Guarded by `len(filtered_history) >= 6`. It rebuilds a larger window (last 6 actions, last
6 observations) and looks for a two-step cycle:

- actions: `a[0] == a[2] == a[4]` and `a[1] == a[3] == a[5]`
- observations: `o[0] == o[2] == o[4]` and `o[1] == o[3] == o[5]`

Both conditions must hold. This is the "alternating between two useless moves" case — for
example: run tests, edit the same line back, run tests, edit it back. Scenario 1 misses this
because no single action repeats consecutively.

### Scenario 5 — condensation loop

Guarded by `len(filtered_history) >= 10`. It collects all `AgentCondensationObservation`
events (with indices) and needs at least **10** of them. It then walks the last 10 pairwise
and asks whether any two adjacent condensation events have **nothing but condensation
events** between them.

This catches a specific failure in the [condenser pipeline](memory_and_condensers.md): the
prompt exceeds the context window, the condenser trims history, the trimmed history is
*still* too large, so it trims again — forever, with the agent never getting to act. Because
no real agent step happens, none of the other four scenarios see anything to compare.

---

## Noise-tolerant equality: `_eq_no_pid`

Raw `==` on events is too strict for loop detection. Two runs of the same shell command
produce observations that differ only by process ID; two attempts at the same file edit
produce actions that differ only by the agent's thought text. `_eq_no_pid` normalises that
away.

```mermaid
flowchart TD
    Cmp(["_eq_no_pid(obj1, obj2)"]) --> T1{"both IPythonRunCellAction?"}

    T1 -->|yes| T1a{"both contain<br/>'edit_file_by_replace(' ?"}
    T1a -->|yes| T1b["compare first 3 lines of code only<br/>AND require code > 2 lines<br/><i>(thought ignored; one-liners never match)</i>"]
    T1a -->|no| Def1["obj1 == obj2"]

    T1 -->|no| T2{"both CmdOutputObservation?"}
    T2 -->|yes| T2a["compare command + exit_code only<br/><i>(command_id / pid ignored)</i>"]
    T2 -->|no| Def2["obj1 == obj2"]
```

| Event pair | Compared on | Ignored |
| --- | --- | --- |
| Two `IPythonRunCellAction`s that both call `edit_file_by_replace(` | First 3 lines of `code`, and only if the code has more than 2 lines | The agent's `thought`, and anything past line 3 |
| Two `CmdOutputObservation`s | `command` and `exit_code` | `command_id` (the PID) |
| Anything else | Full `==` | — |

The `len(code.split('\n')) > 2` guard is there so short one-line edits are never treated as
equal. Trivial one-liners repeat legitimately far too often to use as loop evidence.

---

## Data flow end to end

```mermaid
flowchart LR
    subgraph Sources["event producers"]
        AG["Agent<br/>(actions)"]
        RT["Runtime<br/>(observations)"]
        CD["Condenser<br/>(AgentCondensationObservation)"]
        US["User<br/>(MessageAction)"]
    end

    AG --> ES["EventStream"]
    RT --> ES
    CD --> ES
    US --> ES

    ES --> STK["StateTracker"]
    STK --> HIST["State.history<br/>list[Event]"]

    HIST --> W["window select<br/>(headless vs interactive)"]
    W --> F["filter noise<br/>(user msgs, nulls)"]
    F --> G{"len >= 3?"}
    G -->|no| NO["False"]
    G -->|yes| B["build last-4 / last-6 lists"]
    B --> SC["scenario 1..5<br/>with _eq_no_pid"]
    SC --> V["bool verdict"]
    V --> CTL["AgentController"]
    CTL --> ERR["AgentStuckInLoopError<br/>→ AgentState.ERROR"]

    style SC fill:#ffe6b3,stroke:#d68910,stroke-width:2px
```

Note that `State.history` is not pickled when a conversation is saved — it is rebuilt from
the [`EventStream`](event_system.md) on restore. The detector therefore has no persistence
concerns of its own; it always reads whatever history the
[state layer](agent_controller_state.md) currently holds.

---

## Design notes

**Heuristic, not a proof.** Every threshold (3, 4, 6, 10) is a tuned guess balancing two
costs: stopping an agent that was about to succeed, versus letting one burn budget on
nothing. The code leans toward *not* firing — many checks return `False` the moment
something does not line up exactly.

**Stateless between calls.** `StuckDetector` keeps only a reference to `State`. There are no
counters, no memory of past verdicts, no cached windows. Each call recomputes from scratch,
which makes behaviour easy to reason about and easy to test.

**Complementary to control flags.** This module answers "is the agent going in circles?"
The `ControlFlag`s in [agent_controller_state](agent_controller_state.md) answer "has the
agent used too many iterations or too much money?" Both are checked in `_step()`, one right
after the other. Loop detection usually trips first, because a loop wastes the budget that
a flag would otherwise have to wait for.

**Detect, do not repair.** The module deliberately stops short of intervention. It does not
inject hints, force a different action, or ask the condenser to try harder. Escalation
policy lives in the controller, so a stuck verdict means the same thing everywhere while
different front ends ([CLI](cli.md), [server sessions](server_sessions.md)) can present it
however they like.

**Where the blind spots are.** Semantic loops slip through — an agent making cosmetically
different but equally useless moves (different file names, different phrasing, slightly
different commands) will not match any scenario. Detection is structural, based on event
equality, not on understanding intent.

## Extending the module

Adding a new pattern is a contained change:

1. Write a `_is_stuck_<pattern>(self, ...) -> bool` method. Read only from the arguments it
   is given; call `logger.warning(...)` with a distinct message when it fires.
2. Add the call to the scenario chain in `is_stuck()`, behind a `len(filtered_history) >= N`
   guard if it needs a long window. Put cheap and high-confidence checks earlier.
3. If the pattern needs a tolerant comparison, extend `_eq_no_pid` rather than comparing
   inline — that keeps "what counts as the same event" in one place.
4. Cover it with a unit test that builds a fake `State` with a hand-written event list. No
   runtime or LLM is required, which is the main practical benefit of keeping this module
   pure.
