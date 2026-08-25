# Condenser Framework

## Introduction

An OpenHands agent works by reading its whole conversation history and deciding what to do next. That history grows with every action and observation, and LLMs have a limited context window. The **condenser framework** is the layer that shrinks the history before it reaches the LLM.

This module holds the three pieces that every condensation strategy builds on:

| Component | File | Role |
| --- | --- | --- |
| `View` | `openhands/memory/view.py` | A linear, LLM-ready list of events, rebuilt from raw history. |
| `Condensation` | `openhands/memory/condenser/condenser.py` | A wrapper around a `CondensationAction` — the "I shrank the history" event. |
| `Condenser` | `openhands/memory/condenser/condenser.py` | Abstract base class + config registry + metadata plumbing. |
| `RollingCondenser` | `openhands/memory/condenser/condenser.py` | Base class for strategies that condense a *rolling* window. |
| `CondenserPipeline` | `openhands/memory/condenser/impl/pipeline.py` | Chains several condensers into one. |

The concrete strategies live in sibling modules and are documented separately:

- [Structural condensers](memory_and_condensers_structural_condensers.md) — drop events by position/count.
- [Masking condensers](memory_and_condensers_masking_condensers.md) — blank out old observation bodies.
- [LLM condensers](memory_and_condensers_llm_condensers.md) — summarize or re-rank with an LLM.

---

## The Central Idea: History vs. View

The key design choice is that **condensation is itself an event**. A condenser never mutates the event stream. Instead it emits a `CondensationAction` that says "forget events 12–48, and here is a summary to put at offset 4". That action is appended to history like any other event.

`View.from_events` then *replays* history and applies those instructions to produce the list the LLM actually sees.

```mermaid
graph LR
    subgraph Durable["Durable Event Stream (append-only)"]
        E1["Event 1<br/>SystemMessage"]
        E2["Event 2..48<br/>actions + observations"]
        E3["CondensationAction<br/>forget 12-48<br/>summary at offset 4"]
        E4["Event 50..<br/>new events"]
    end

    E1 --> VF
    E2 --> VF
    E3 --> VF
    E4 --> VF

    VF["View.from_events()"] --> V["View<br/>kept events +<br/>AgentCondensationObservation(summary)"]
    V --> LLM["Messages sent to the LLM"]

    style Durable fill:#eef4fb
    style VF fill:#fff3cd
```

Why this matters:

- **Nothing is lost.** The raw stream is intact, so replay, debugging, and the UI still see everything.
- **Condensation is reproducible.** Restore a session from disk, rebuild the view, get the same result.
- **Condensers stay stateless.** All the state they need is encoded in the events themselves.

---

## Architecture

```mermaid
classDiagram
    class View {
        +list~Event~ events
        +bool unhandled_condensation_request
        +from_events(events) View$
        +__len__()
        +__iter__()
        +__getitem__(int|slice)
    }

    class Condensation {
        +CondensationAction action
    }

    class Condenser {
        <<abstract>>
        -dict _metadata_batch
        -dict _llm_metadata
        +condense(view)* View|Condensation
        +condensed_history(state) View|Condensation
        +add_metadata(key, value)
        +write_metadata(state)
        +metadata_batch(state)
        +llm_metadata
        +register_config(cfg_type)$
        +from_config(cfg, llm_registry)$ Condenser
    }

    class RollingCondenser {
        <<abstract>>
        +should_condense(view)* bool
        +get_condensation(view)* Condensation
        +condense(view) View|Condensation
    }

    class CondenserPipeline {
        +list~Condenser~ condensers
        +condense(view) View|Condensation
        +metadata_batch(state)
    }

    class NoOpCondenser
    class ObservationMaskingCondenser
    class AmortizedForgettingCondenser
    class LLMSummarizingCondenser
    class ConversationWindowCondenser

    Condenser <|-- RollingCondenser
    Condenser <|-- CondenserPipeline
    Condenser <|-- NoOpCondenser
    Condenser <|-- ObservationMaskingCondenser
    RollingCondenser <|-- AmortizedForgettingCondenser
    RollingCondenser <|-- LLMSummarizingCondenser
    RollingCondenser <|-- ConversationWindowCondenser

    CondenserPipeline o-- Condenser : chains
    Condenser ..> View : consumes
    Condenser ..> Condensation : may produce
```

### Two return types, two meanings

`Condenser.condense` returns either a `View` or a `Condensation`. The agent must handle both:

- **`View`** — "here are the events, go ahead and think." The agent builds messages and calls the LLM.
- **`Condensation`** — "stop; I need to shrink the history first." The agent returns `Condensation.action` as its action for this step. The controller writes it to the stream, which triggers another agent step, and this time `View.from_events` produces the smaller view.

This is what makes an expensive condensation (like an LLM summarization) visible to the user and recorded in the event log, instead of happening invisibly inside a single step.

---

## `View` in Detail

`View` is a Pydantic model that behaves like a list — it supports `len()`, iteration, integer indexing, and slicing (via `@overload`-typed `__getitem__`), so condenser code can write `view[:keep_first]` and `view[-n:]` naturally.

### `View.from_events` algorithm

```mermaid
flowchart TD
    Start["events: list[Event]"] --> S1

    S1["Pass 1 — collect forgotten IDs<br/>• CondensationAction → its .forgotten + its own id<br/>• CondensationRequestAction → its own id"]
    S1 --> S2["Filter: kept_events = events not in forgotten set"]

    S2 --> S3["Pass 2 — scan backwards for the<br/>most recent CondensationAction<br/>that carries a summary"]
    S3 --> Q1{"summary and<br/>summary_offset<br/>present?"}
    Q1 -->|yes| S4["Insert AgentCondensationObservation(summary)<br/>into kept_events at summary_offset"]
    Q1 -->|no| S5
    S4 --> S5

    S5["Pass 3 — scan backwards:<br/>a CondensationRequestAction seen<br/>before any CondensationAction<br/>→ unhandled_condensation_request = True"]
    S5 --> Out["View(events, unhandled_condensation_request)"]

    style Start fill:#e8f5e9
    style Out fill:#e3f2fd
```

Three behaviors worth calling out:

1. **Condensation bookkeeping erases itself.** A `CondensationAction` adds its *own* id to the forgotten set, so the agent never sees the plumbing events — only their effect.
2. **Only the newest summary survives.** Summaries are cumulative by construction: each new summarizing condensation writes a summary that already covers the previous one, so `from_events` keeps just the last.
3. **`unhandled_condensation_request` is a flag, not a queue.** It is `True` only when a request came *after* the last condensation — i.e. somebody asked for a condensation and nobody has done one yet.

### `CondensationAction` shape

The action (defined in the [event system](event_system.md), `openhands/events/action/agent.py`) can specify forgotten events two ways, and validates that exactly one is used:

| Field set | Meaning |
| --- | --- |
| `forgotten_event_ids: [3, 7, 9]` | Forget exactly these ids (sparse). |
| `forgotten_events_start_id` + `forgotten_events_end_id` | Forget the whole inclusive range (dense). |
| `summary` + `summary_offset` | Optional, must be supplied together. |

The `forgotten` property normalizes both forms into a plain list of ids.

---

## `Condenser`: The Base Class

`Condenser` gives every strategy four things.

### 1. The `condense` contract

Subclasses implement one method:

```python
@abstractmethod
def condense(self, view: View) -> View | Condensation: ...
```

### 2. The entry point used by agents

`condensed_history(state)` is what agents actually call. It wires up LLM tracing metadata and guarantees diagnostic metadata gets flushed:

```mermaid
sequenceDiagram
    participant A as Agent
    participant C as Condenser
    participant S as State

    A->>C: condensed_history(state)
    C->>C: model_name = self.llm.config.model if present else "unknown"
    C->>S: to_llm_metadata(model_name, agent_name="condenser")
    S-->>C: llm_metadata (session_id, trace tags, user_id)
    C->>C: enter metadata_batch(state) context
    C->>S: read state.view (cached View.from_events)
    C->>C: condense(view)
    Note over C: implementation may call add_metadata(...)
    C->>S: write_metadata(state) — on exit, even on error
    C-->>A: View or Condensation
```

`state.view` is itself cached on the `State` object, keyed by a cheap `len(history)` checksum, so repeated access in a step does not re-run `from_events`. See [agent controller state](agent_controller_state.md).

### 3. Per-condensation metadata

Condensers record diagnostics without knowing anything about persistence:

- `add_metadata(key, value)` puts a key into the current batch.
- `write_metadata(state)` appends the batch to `state.extra_data['condenser_meta']` and clears it.
- `metadata_batch(state)` is a `@contextmanager` wrapping the two, so the write happens in a `finally`.
- The free function `get_condensation_metadata(state)` reads the accumulated list back out.

LLM-backed condensers use this to log the raw response and token metrics per condensation, e.g. `LLMSummarizingCondenser` calls `add_metadata('response', ...)` and `add_metadata('metrics', ...)`.

The `llm_metadata` property exposes the trace metadata that condensers pass to their LLM call as `extra_body={'metadata': self.llm_metadata}`, which tags the request as coming from `agent:condenser` rather than the main agent. It logs a warning if it is read before `condensed_history` populated it.

### 4. Config-driven construction (the registry)

Condensers are never constructed directly by callers. A module-level dict maps config classes to condenser classes:

```mermaid
flowchart LR
    subgraph Import["import openhands.memory.condenser.impl"]
        M1["amortized_forgetting_condenser.py"] -->|"register_config(AmortizedForgettingCondenserConfig)"| REG
        M2["llm_summarizing_condenser.py"] -->|"register_config(LLMSummarizingCondenserConfig)"| REG
        M3["pipeline.py"] -->|"register_config(CondenserPipelineConfig)"| REG
        M4["... every impl module"] -->|"register_config(...)"| REG
    end

    REG[("CONDENSER_REGISTRY<br/>type[CondenserConfig] → type[Condenser]")]

    CFG["CondenserConfig instance<br/>(from TOML / settings / defaults)"] --> FC
    FC["Condenser.from_config(config, llm_registry)"] --> REG
    REG --> RES["registry[type(config)].from_config(...)"]
    RES --> INST["Concrete condenser instance"]

    style REG fill:#fff3cd
```

Each impl module calls `<Class>.register_config(<ConfigClass>)` at import time, and `openhands/memory/condenser/impl/__init__.py` imports every module so the registry is fully populated. `register_config` raises `ValueError` on a duplicate registration; `from_config` raises `ValueError` for an unknown config type.

Note the double dispatch in the base `from_config`: it looks up the concrete class, then calls *that class's* `from_config`, which knows how to unpack its own config fields (usually `config.model_dump(exclude={'type'})`) and pull an LLM from the `LLMRegistry`. See [LLM registry](llm_layer_registry.md) and [core configuration](core_configuration.md) for the `CondenserConfig` union.

---

## `RollingCondenser`: The Common Strategy Shape

Most useful condensers follow the same pattern: watch a growing view, and when it crosses a threshold, emit a condensation. `RollingCondenser` factors that out into two hooks.

```python
def condense(self, view: View) -> View | Condensation:
    if self.should_condense(view):
        return self.get_condensation(view)
    return view
```

```mermaid
stateDiagram-v2
    [*] --> Passthrough
    Passthrough --> Passthrough: should_condense(view) == False<br/>→ return view unchanged
    Passthrough --> Condensing: should_condense(view) == True
    Condensing --> Emitted: get_condensation(view)<br/>→ Condensation(CondensationAction)
    Emitted --> Passthrough: action lands in event stream,<br/>next View.from_events is smaller
```

Subclasses only decide *when* and *what*:

| Condenser | `should_condense` trigger | `get_condensation` output |
| --- | --- | --- |
| `AmortizedForgettingCondenser` | `len(view) > max_size` | Forget the middle; keep `keep_first` head + tail down to `max_size // 2`. |
| `LLMSummarizingCondenser` | `len(view) > max_size` | LLM-written summary + forget range, summary at `keep_first`. |
| `ConversationWindowCondenser` | `view.unhandled_condensation_request` | Keep system msg, first user msg, recall pair, and ~half the tail. |

Not every condenser is rolling. `ObservationMaskingCondenser` and `NoOpCondenser` subclass `Condenser` directly and always return a `View` — masking rewrites observation bodies to `<MASKED>` in-place for the view only, which never needs an event.

---

## `CondenserPipeline`: Composition

Real deployments rarely want a single strategy. `CondenserPipeline` chains condensers, feeding each one the previous one's `View`:

```mermaid
flowchart LR
    IN["View from State"] --> C1

    C1["ConversationWindowCondenser<br/>(emergency truncation)"]
    C1 -->|View| C2["BrowserOutputCondenser<br/>(attention_window=2)"]
    C2 -->|View| C3["LLMSummarizingCondenser<br/>(keep_first=4, max_size=120)"]
    C3 -->|View| OUT["Final View → LLM"]

    C1 -.->|Condensation| SHORT["short-circuit:<br/>return immediately"]
    C2 -.->|Condensation| SHORT
    C3 -.->|Condensation| SHORT

    style SHORT fill:#ffe0e0
    style OUT fill:#e3f2fd
```

Two rules govern the loop:

1. **Views flow forward.** Each condenser's output view is the next one's input.
2. **A `Condensation` breaks the chain.** The moment any stage returns a `Condensation`, the pipeline stops and returns it — later stages never run on this step. They will run on the next step, against the freshly shrunk view.

Ordering therefore matters. The default server pipeline (`openhands/server/session/session.py`) puts browser-output masking *before* LLM summarizing so the summarizer only ever sees the two most recent browser dumps, which keeps summarization cheap.

### Metadata override

The pipeline overrides `metadata_batch` for a subtle reason: `Condenser.condense` receives only a `View`, not a `State`, so the pipeline cannot hand a `State` to its children. Instead, after the pipeline's own condensation finishes, it walks its child list and calls `child.write_metadata(state)` on each — collecting metadata that the children accumulated in their own batches.

```mermaid
sequenceDiagram
    participant A as Agent
    participant P as CondenserPipeline
    participant C1 as Child A
    participant C2 as Child B
    participant S as State

    A->>P: condensed_history(state)
    activate P
    P->>P: enter metadata_batch(state) [overridden]
    P->>C1: condense(view)
    C1->>C1: add_metadata(...) into own batch
    C1-->>P: View'
    P->>C2: condense(View')
    C2->>C2: add_metadata(...) into own batch
    C2-->>P: View''
    P->>C1: write_metadata(state)
    P->>C2: write_metadata(state)
    C1->>S: append batch to extra_data['condenser_meta']
    C2->>S: append batch to extra_data['condenser_meta']
    deactivate P
    P-->>A: View''
```

---

## End-to-End Flow

Here is a full agent step showing both the fast path and the condensation path. The agent side is documented in [agents](agents.md) / [agent controller core](agent_controller_core.md).

```mermaid
sequenceDiagram
    participant EC as AgentController
    participant AG as CodeActAgent
    participant CO as Condenser
    participant ST as State
    participant ES as EventStream
    participant LLM as LLM

    EC->>AG: step(state)
    AG->>CO: condensed_history(state)
    CO->>ST: state.view → View.from_events(history)

    alt View returned (fast path)
        CO-->>AG: View(events)
        AG->>AG: _get_messages(condensed_history)
        AG->>LLM: completion(messages, tools)
        LLM-->>AG: response
        AG-->>EC: Action (e.g. CmdRunAction)
        EC->>ES: add_event(action)
    else Condensation returned
        CO-->>AG: Condensation(action)
        AG-->>EC: CondensationAction
        EC->>ES: add_event(CondensationAction)
        Note over ES,EC: should_step(CondensationAction) == True
        ES->>EC: re-trigger step
        EC->>AG: step(state)  [view is now smaller]
    end
```

### The context-window overflow path

The framework also handles the case where the LLM call itself fails because the prompt is too long. This closes the loop between the runtime error and the `unhandled_condensation_request` flag:

```mermaid
flowchart TD
    A["Agent calls LLM"] --> B{"ContextWindowExceededError<br/>(or a matching provider error string)"}
    B -->|no| Z["Normal action"]
    B -->|yes| C{"agent.config.<br/>enable_history_truncation?"}
    C -->|no| E["raise LLMContextWindowExceedError"]
    C -->|yes| D["EventStream.add_event(<br/>CondensationRequestAction())"]
    D --> F["View.from_events sets<br/>unhandled_condensation_request = True"]
    F --> G["ConversationWindowCondenser.<br/>should_condense() → True"]
    G --> H["get_condensation():<br/>keep system msg, first user msg,<br/>recall pair, ~half the tail"]
    H --> I["CondensationAction into stream"]
    I --> J["Next step sees a much smaller View"]

    style B fill:#ffe0e0
    style E fill:#ffcccc
    style J fill:#e8f5e9
```

The agent can also raise a `CondensationRequestAction` itself via the `CondensationRequestTool` when `enable_condensation_request` is on — the same flag and the same condenser handle it.

---

## Dependencies

```mermaid
graph TD
    subgraph CF["condenser_framework (this module)"]
        CD["condenser.py<br/>Condenser · RollingCondenser · Condensation"]
        VW["view.py<br/>View"]
        PL["impl/pipeline.py<br/>CondenserPipeline"]
    end

    subgraph Upstream["Depends on"]
        EV["events.action.agent<br/>CondensationAction<br/>CondensationRequestAction"]
        OB["events.observation.agent<br/>AgentCondensationObservation"]
        CFG["core.config.condenser_config<br/>CondenserConfig union"]
        STA["controller.state.state<br/>State"]
        REG["llm.llm_registry<br/>LLMRegistry"]
        LOG["core.logger"]
    end

    subgraph Downstream["Depended on by"]
        SC["structural condensers"]
        MC["masking condensers"]
        LC["LLM condensers"]
        AGT["agents (CodeActAgent etc.)"]
        CM["conversation_memory"]
    end

    CD --> EV
    CD --> CFG
    CD --> STA
    CD --> REG
    CD --> LOG
    CD --> VW
    VW --> EV
    VW --> OB
    VW --> LOG
    PL --> CD
    PL --> VW
    PL --> CFG
    PL --> STA
    PL --> REG

    CD --> SC
    CD --> MC
    CD --> LC
    VW --> AGT
    CD --> AGT
    AGT --> CM

    style CF fill:#e3f2fd
    style Upstream fill:#fff8e1
    style Downstream fill:#f1f8e9
```

| Dependency | Why |
| --- | --- |
| [event system](event_system.md) | `CondensationAction`, `CondensationRequestAction`, `AgentCondensationObservation`, `Event`. |
| [agent controller state](agent_controller_state.md) | `State.view` (cached), `State.extra_data`, `State.to_llm_metadata`. |
| [core configuration](core_configuration.md) | The `CondenserConfig` union and TOML parsing. |
| [LLM registry](llm_layer_registry.md) | Handed to `from_config` so LLM-backed condensers can obtain a client. |
| [conversation memory](memory_and_condensers_conversation_memory.md) | Turns the resulting `View` events into LLM `Message` objects. |

There is a notable **circular-ish** relationship worth understanding: the condenser framework imports `State`, and `State` imports `View`. Python handles this because `state.py` imports only `openhands.memory.view` (which has no controller dependency), while `condenser.py` imports `State` — the cycle is broken by keeping `View` in its own leaf module. This is a real constraint: do not add controller imports to `view.py`.

---

## Extending the Framework

To add a new strategy:

1. **Define a config** in `openhands/core/config/condenser_config.py` as a Pydantic model with a unique `type: Literal[...]`, add it to the `CondenserConfig` union and to the `condenser_classes` map in `create_condenser_config`.
2. **Pick a base class.** Subclass `RollingCondenser` if you drop/summarize events past a threshold; subclass `Condenser` directly if you always return a rewritten `View`.
3. **Implement the hooks** — `should_condense` + `get_condensation`, or `condense`.
4. **Implement `from_config`** as a classmethod taking `(config, llm_registry)`.
5. **Register at module scope**: `MyCondenser.register_config(MyCondenserConfig)`.
6. **Export it** from `openhands/memory/condenser/impl/__init__.py`, otherwise the registration never runs.

Guidelines that fall out of the design:

- **Never mutate `view.events` in place.** Build a new list; other code holds the same `Event` objects.
- **Emit ranges, not sparse lists, when you can.** `forgotten_events_start_id`/`end_id` keeps the action small; `ConversationWindowCondenser` checks for contiguity and picks the compact form.
- **Keep `should_condense` cheap.** It runs on every single agent step.
- **Do expensive work only in `get_condensation`.** That is the step the agent surfaces as a real action, so the cost is visible and recorded.
- **Always pair `summary` with `summary_offset`.** `CondensationAction.__post_init__` rejects one without the other.
- **Use `add_metadata` for anything you would otherwise log.** It lands in `state.extra_data['condenser_meta']` and is readable afterwards via `get_condensation_metadata`, which evaluation harnesses rely on.
