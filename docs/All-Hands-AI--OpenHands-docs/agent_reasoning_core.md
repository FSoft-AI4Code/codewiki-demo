# Agent Reasoning Core

## 1. Purpose

The `agent_reasoning_core` is the **brain** of OpenHands. It is the part of the system that
decides *what to do next*.

Everything in this group answers one question, over and over:

> Given everything that has happened so far, what is the next single action?

It does **not** execute anything. It does not open a shell, write a file, or click a
button. Those jobs belong to the [sandboxed execution layer](sandboxed_execution_layer.md).
This group only reasons, and it hands its decision to the event stream.

The whole group is one loop with six supporting parts:

| Sub-module | Path | Job in one line |
|---|---|---|
| [Agent Controller](agent_controller.md) | `openhands/controller` | Runs the loop: when may the agent act, and is it allowed to? |
| [Agents](agents.md) | `openhands/agenthub` | The policies: `State` in, one `Action` out |
| [LLM Layer](llm_layer.md) | `openhands/llm` | The single door to every model provider; also cost and token accounting |
| [Memory and Condensers](memory_and_condensers.md) | `openhands/memory` | Decides what the agent remembers, and shrinks it when it stops fitting |
| [Microagents](microagents.md) | `openhands/microagent` | Extra instructions loaded from Markdown files |
| [Security Analyzers](security_analyzers.md) | `openhands/security` | Scores how dangerous a proposed action is |

### The one-line summary

The controller turns a stateless `step(state) -> action` function into a long-running,
resumable, budget-limited, safety-gated conversation. Everything else in the group feeds
that function or guards it.

---

## 2. Where the group sits

```mermaid
graph TB
    subgraph Clients["User-facing clients"]
        UI["Frontend / CLI"]
    end

    subgraph Service["Conversation service tier"]
        AS["AgentSession<br/>builds + owns the controller"]
        CS["ConversationStats<br/>cost + token totals"]
    end

    subgraph Core["Agent Reasoning Core (this group)"]
        AC["AgentController"]
        AG["Agents"]
        MEM["Memory + Condensers"]
        MA["Microagents"]
        LLM["LLM Layer"]
        SEC["Security Analyzers"]
    end

    subgraph Foundation["Shared platform foundation"]
        ES["EventStream"]
        FS["FileStore"]
        CFG["Config + schema"]
    end

    subgraph Exec["Sandboxed execution layer"]
        RT["Runtime<br/>bash, jupyter, browser, files"]
    end

    UI --> AS
    AS -->|creates| AC
    AS --> CS
    CS -.->|metrics| AC

    AC -->|"step(state)"| AG
    AG --> LLM
    AG --> MEM
    MEM --> MA
    MEM --> LLM
    AC -->|"security_risk(action)"| SEC

    AC <-->|publish / subscribe| ES
    MEM <-->|recall / condense| ES
    ES <--> RT
    AC -->|save_state| FS
    CFG --> Core
```

The important boundary: **the controller and the runtime never call each other.** They
only meet through the [event stream](event_system.md). The controller adds an `Action`,
the runtime notices it and adds an `Observation`, and the controller lets the agent step
again. That indirection is what makes the whole group testable without a sandbox.

---

## 3. Internal architecture

```mermaid
graph TB
    subgraph Loop["The loop"]
        AC["<b>AgentController</b><br/>event loop, AgentState machine,<br/>delegation, confirmation"]
        ST["StateTracker + State<br/>history, iteration flag, budget flag"]
        SD["StuckDetector"]
        RM["ReplayManager"]
    end

    subgraph Policy["The policies"]
        BASE["Agent (abstract base)<br/>step(state) -> Action"]
        CA["CodeActAgent + variants<br/>ReadOnlyAgent, LocAgent"]
        BR["BrowsingAgent<br/>VisualBrowsingAgent"]
        DUM["DummyAgent · AgentFinishedCritic"]
    end

    subgraph Context["What the agent sees"]
        VIEW["View<br/>condensed history"]
        CM["ConversationMemory<br/>events -> Messages"]
        COND["Condenser family<br/>structural · masking · LLM"]
        RECALL["Memory<br/>answers RecallAction"]
        MAG["Microagents<br/>repo · knowledge · task"]
    end

    subgraph Model["The model door"]
        REG["LLMRegistry<br/>one client per service id"]
        CLI2["LLM / AsyncLLM / StreamingLLM"]
        ROUTE["RouterLLM · MultimodalRouter"]
        MET["Metrics<br/>cost, tokens, latency"]
    end

    subgraph Guard["The guards"]
        SA["SecurityAnalyzer<br/>LLMRiskAnalyzer · InvariantAnalyzer"]
    end

    AC --> ST
    AC --> SD
    AC --> RM
    AC -->|"step()"| BASE
    BASE --> CA
    BASE --> BR
    BASE --> DUM

    ST --> VIEW
    VIEW --> COND
    COND --> CM
    RECALL --> MAG
    RECALL -.->|RecallObservation| VIEW
    CA --> CM
    CM --> CLI2

    BASE --> REG
    COND --> REG
    SA --> REG
    REG --> CLI2
    ROUTE --> CLI2
    CLI2 --> MET
    MET -.->|budget flag reads| ST

    AC --> SA

    style AC fill:#e1f0ff
    style COND fill:#e1ffe1
    style SA fill:#ffe8e8
```

### Three layers of responsibility

1. **Orchestration** — only `AgentController` has authority. It owns the `AgentState`
   machine, the pending-action gate, delegation, and the mapping from provider errors to
   user-readable statuses.
2. **Decision** — agents are deliberately passive. They receive a read-only `State` and
   return one `Action`. They never touch the event stream or start anything.
3. **Support** — memory, microagents, the LLM layer, and the analyzers are all called
   *into*. None of them drives the loop.

---

## 4. One turn, end to end

This is the single most important flow in the repository.

```mermaid
sequenceDiagram
    participant U as User
    participant ES as EventStream
    participant AC as AgentController
    participant MEM as Memory
    participant CND as Condenser
    participant AG as Agent
    participant L as LLM
    participant SA as SecurityAnalyzer
    participant RT as Runtime

    U->>ES: MessageAction
    ES->>AC: on_event
    AC->>ES: RecallAction
    ES->>MEM: on_event
    MEM->>MEM: match microagent triggers,<br/>gather repo + runtime info
    MEM->>ES: RecallObservation

    Note over AC: three gates: state RUNNING,<br/>no pending action, limits not hit

    AC->>AG: step(state)
    AG->>CND: condensed_history(state)
    CND-->>AG: View (trimmed / masked / summarized)
    AG->>L: completion(messages, tools)
    L-->>AG: response (+ cost & tokens recorded)
    AG-->>AC: Action

    opt runnable and confirmation mode
        AC->>SA: security_risk(action)
        SA-->>AC: LOW | MEDIUM | HIGH | UNKNOWN
        AC->>AC: park in AWAITING_USER_CONFIRMATION if HIGH
    end

    AC->>ES: add_event(action)
    ES->>RT: execute
    RT->>ES: Observation
    ES->>AC: on_event -> clear pending, loop again
```

### The three gates before any step

`_step()` refuses to run unless all three are open:

1. **State gate** — the agent state must be `RUNNING`.
2. **Pending-action gate** — no action may be in flight. One action out, one observation
   back. This is what makes the loop strictly turn-based.
3. **Limit gate** — iteration and budget flags below their ceiling, and the stuck detector
   reporting progress.

---

## 5. The safety net

Four independent mechanisms fail in four different ways, on purpose.

```mermaid
flowchart TD
    A["Agent proposes an Action"]

    A --> B{"Iteration / budget<br/>ceiling reached?"}
    B -->|yes| B1["ERROR state<br/>resumable with raised limits"]

    B -->|no| C{"StuckDetector:<br/>same pattern looping?"}
    C -->|yes| C1["AgentStuckInLoopError<br/>-> ERROR"]

    C -->|no| D{"Confirmation mode<br/>and gated action type?"}
    D -->|no| Z["Publish to EventStream"]
    D -->|yes| E["SecurityAnalyzer scores it"]

    E --> F{"HIGH risk, or UNKNOWN<br/>with no analyzer?"}
    F -->|no| Z
    F -->|yes| G["AWAITING_USER_CONFIRMATION"]
    G -->|approved| Z
    G -->|rejected| H["Action dropped"]

    style B1 fill:#ffe8e8
    style C1 fill:#ffe8e8
    style G fill:#fff4e1
```

| Guard | Stops | Lives in |
|---|---|---|
| `IterationControlFlag` / `BudgetControlFlag` | Runaway cost and endless stepping | [agent_controller](agent_controller.md) |
| `StuckDetector` | Semantic loops — the same action forever | [agent_controller](agent_controller.md) |
| Security analyzer + confirmation mode | Dangerous side effects | [security_analyzers](security_analyzers.md) |
| Condensers | Prompts that outgrow the context window | [memory_and_condensers](memory_and_condensers.md) |

The confirmation path is **fail-safe**: with no analyzer configured every runnable action
scores `UNKNOWN`, and in confirmation mode `UNKNOWN` means *ask the human*.

### Context overflow is a feedback loop, not a crash

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

The controller does not fail the run when a prompt is too long. It puts a request back
into the stream, the condenser answers with a `CondensationAction`, the view shrinks, and
the agent steps again. If that loop itself starts spinning, the stuck detector catches it.

---

## 6. Two design ideas that repeat everywhere

### 6.1 Append-only history, derived views

Nothing in this group ever deletes an event. History is rebuilt from the event stream on
every restart, and `State.__getstate__` deliberately blanks history out before pickling so
the two can never drift apart. Condensers add a `CondensationAction` saying what *should*
be forgotten; the `View` is recomputed from that. Result: condensation is replayable and
auditable.

```mermaid
graph LR
    ES["EventStream<br/>all events"] --> HF["EventFilter<br/>drop bookkeeping noise,<br/>collapse delegate internals"]
    HF --> H["state.history"]
    H --> V["state.view<br/>apply condensations"]
    V --> AG["Agent.step()"]
    AG --> MSG["ConversationMemory<br/>-> list[Message]"]
    MSG --> LLM["LLM prompt"]

    style HF fill:#fff4e1
    style V fill:#e1ffe1
```

### 6.2 Registries instead of switch statements

Every extension point in this group is a registry, so adding a piece never means editing a
dispatcher:

| Thing you add | How it is registered | Selected by |
|---|---|---|
| A new agent | `Agent.register(name, cls)` | `AgentConfig.agent` name |
| A new condenser | `register_config(SomeCondenserConfig)` | the config object's type |
| A new router | `ROUTER_LLM_REGISTRY` | `model_routing.router_name` |
| A new analyzer | `SecurityAnalyzers['name']` | `[security] security_analyzer` |
| A new microagent | drop a `.md` file in a microagents directory | trigger word or `/name` |

---

## 7. Multi-agent delegation

OpenHands agents can hand a subtask to another agent. The parent controller builds a
**child controller** with a different agent class and forwards events to it.

```mermaid
graph TB
    ES["EventStream"]
    P["Parent AgentController<br/>delegate_level = 0<br/><b>subscribed</b>"]
    C["Delegate AgentController<br/>delegate_level = 1<br/>is_delegate = True<br/><b>not subscribed</b>"]

    ES -->|on_event| P
    P -->|forwards while alive| C
    C -->|adds actions| ES
    P -->|AgentDelegateObservation on finish| ES

    style P fill:#e1f0ff
    style C fill:#f0e1ff
```

Three rules make this work: only the root subscribes to the stream (delegates get events
hand-delivered, so nothing is processed twice); iteration, budget, and `Metrics` objects
are **shared** so global limits apply across the whole tree, while snapshots let each
delegate report its own share; and the child starts above the parent's history so it never
re-reads it.

---

## 8. Sub-module reference

```mermaid
graph TB
    ROOT["agent_reasoning_core<br/><i>this page</i>"]

    ROOT --> AC["agent_controller.md"]
    ROOT --> AG["agents.md"]
    ROOT --> LL["llm_layer.md"]
    ROOT --> MC["memory_and_condensers.md"]
    ROOT --> MA["microagents.md"]
    ROOT --> SA["security_analyzers.md"]

    AC --> AC1["agent_controller_core.md"]
    AC --> AC2["agent_controller_state.md"]
    AC --> AC3["agent_controller_safeguards.md"]

    AG --> AG1["agents_browsing.md"]
    AG --> AG2["agents_codeact_variants.md"]
    AG --> AG3["agents_testing_and_critics.md"]

    LL --> LL1["llm_layer_registry.md"]
    LL --> LL2["llm_layer_clients.md"]
    LL --> LL3["llm_layer_routing.md"]
    LL --> LL4["llm_layer_metrics.md"]

    MC --> MC1["memory_and_condensers_recall.md"]
    MC --> MC2["..._conversation_memory.md"]
    MC --> MC3["..._condenser_framework.md"]
    MC --> MC4["..._structural_condensers.md"]
    MC --> MC5["..._masking_condensers.md"]
    MC --> MC6["..._llm_condensers.md"]
```

### [Agent Controller](agent_controller.md) — `openhands/controller`

The engine room. The event loop, the `AgentState` machine, delegation, the confirmation
flow, error-to-status mapping, and persistence.

- [agent_controller_core](agent_controller_core.md) — `AgentController`: *when* and *why*
  the agent acts.
- [agent_controller_state](agent_controller_state.md) — `State`, `StateTracker`,
  `ControlFlag` / `IterationControlFlag` / `BudgetControlFlag`, and the pickle session
  format.
- [agent_controller_safeguards](agent_controller_safeguards.md) — `StuckDetector` (five
  loop patterns) and `ReplayManager` (deterministic trajectory re-runs).

### [Agents](agents.md) — `openhands/agenthub`

The agent zoo, plus the `openhands/critic/` run scorers. Two families, split by how an LLM
reply becomes an `Action`: **text parsing** (browsing agents, BrowserGym's Python-code
DSL) and **native function calling** (CodeAct variants). A third family makes no LLM call
at all.

- [agents_browsing](agents_browsing.md) — `BrowsingAgent`, `VisualBrowsingAgent`,
  `BrowsingResponseParser`.
- [agents_codeact_variants](agents_codeact_variants.md) — `ReadOnlyAgent`, `LocAgent`:
  inherit the loop, narrow the tool list.
- [agents_testing_and_critics](agents_testing_and_critics.md) — `DummyAgent`,
  `AgentFinishedCritic`.

### [LLM Layer](llm_layer.md) — `openhands/llm`

The single door to every provider, built on LiteLLM. One client per *service id*, so cost
counters stay coherent.

- [llm_layer_registry](llm_layer_registry.md) — `LLMRegistry`: create, cache, announce.
- [llm_layer_clients](llm_layer_clients.md) — `LLM` / `AsyncLLM` / `StreamingLLM`,
  retries, logging, every provider quirk, non-native tool-call emulation.
- [llm_layer_routing](llm_layer_routing.md) — `RouterLLM`, `MultimodalRouter`: several
  models pretending to be one.
- [llm_layer_metrics](llm_layer_metrics.md) — `Metrics`, `Cost`, `TokenUsage`,
  `ResponseLatency`; the numbers the budget flag reads.

### [Memory and Condensers](memory_and_condensers.md) — `openhands/memory`

Everything between "raw events" and "what the LLM actually sees."

- [memory_and_condensers_recall](memory_and_condensers_recall.md) — `Memory`, the
  `RecallAction` responder.
- [memory_and_condensers_conversation_memory](memory_and_condensers_conversation_memory.md) —
  `ConversationMemory`: events to `Message`s, tool-call pairing, prompt caching.
- [memory_and_condensers_condenser_framework](memory_and_condensers_condenser_framework.md) —
  the `Condenser` contract, `View`, `CondenserPipeline`.
- [memory_and_condensers_structural_condensers](memory_and_condensers_structural_condensers.md) —
  trimming by size and position, no LLM call.
- [memory_and_condensers_masking_condensers](memory_and_condensers_masking_condensers.md) —
  redacting bulky content outside a recent window.
- [memory_and_condensers_llm_condensers](memory_and_condensers_llm_condensers.md) —
  summarizing and importance ranking.

### [Microagents](microagents.md) — `openhands/microagent`

The prompt extension system: a Markdown file with YAML frontmatter becomes a
`RepoMicroagent` (always active), `KnowledgeMicroagent` (keyword triggered), or
`TaskMicroagent` (`/slash` command with inputs). Type is inferred from *shape*, not from
the declared `type:` field. A leaf module — it parses and describes, nothing else.

### [Security Analyzers](security_analyzers.md) — `openhands/security`

Pull-based risk scoring. `LLMRiskAnalyzer` (the default) reads the risk tag the agent's own
LLM already produced — free, but self-assessment. `InvariantAnalyzer` sends the trace to an
independent policy engine in Docker — semgrep and secret detection the agent cannot talk
its way past. Both only *score*; the controller decides what to do with the score.

---

## 9. Boundaries with the rest of the system

| Module | Direction | What crosses |
|---|---|---|
| [event_system](event_system.md) | both | `Action`, `Observation`, `EventStream` — the only channel to the runtime |
| [core_configuration](core_configuration.md) | in | `AgentConfig`, `LLMConfig`, `SecurityConfig`, condenser configs |
| [core_schema_and_runtime_support](core_schema_and_runtime_support.md) | in | `AgentState`, `ActionType`, `RuntimeStatus`, `PromptManager` |
| [storage_backends](storage_backends.md) | out | `FileStore` the state is pickled into |
| [server_sessions](server_sessions.md) | in | `AgentSession` builds the controller; `ConversationStats` restores metrics |
| [sandboxed_execution_layer](sandboxed_execution_layer.md) | via stream | executes actions, owns the security analyzer instance, supplies microagent files |
| [cli](cli.md) / [frontend_state](frontend_state.md) | out | agent state, cost, and risk levels shown to users |

---

## 10. Reading order

1. [agent_controller](agent_controller.md) — the loop that drives everything.
2. [agents](agents.md) — what `step()` actually does.
3. [llm_layer](llm_layer.md) — how a model call is made and paid for.
4. [memory_and_condensers](memory_and_condensers.md) — how the prompt stays in budget.
5. [microagents](microagents.md) — where extra instructions come from.
6. [security_analyzers](security_analyzers.md) — the last gate before an action runs.