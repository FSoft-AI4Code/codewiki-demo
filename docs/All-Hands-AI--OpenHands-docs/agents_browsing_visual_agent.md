# Visual Browsing Agent

## Introduction

The `agents_browsing_visual_agent` module holds a single class: `VisualBrowsingAgent`. It is an agent that browses the web the way a person does — by **looking at the page**.

Most agents in OpenHands read a web page as text. This one reads text *and* pictures. Each turn it sends the LLM two things:

1. A text view of the page (the accessibility tree, or "AXTree").
2. A screenshot with numbered boxes drawn on top of every element (a "Set-of-Marks" image).

The LLM then replies with one browser command, such as `click('324')` or `goto('https://example.com')`. The agent runs it, gets a new page, and repeats.

Because it can see the page, this agent handles tasks that pure-text agents struggle with: reading charts, finding a button by its color or position, or answering a question about an image on the page. It is the agent used for the **VisualWebArena** benchmark.

- **Source file:** `openhands/agenthub/visualbrowsing_agent/visualbrowsing_agent.py`
- **Core class:** `VisualBrowsingAgent`
- **Sibling agent:** [Text Browsing Agent](agents_browsing_text_agent.md)
- **Parent module:** [Browsing Agents](agents_browsing.md)

---

## Where This Module Sits

The agent itself is small and stateless. It is one replaceable part inside a much bigger loop. It never touches the browser directly — it only returns an `Action` object and waits to be handed an `Observation` back.

```mermaid
graph TB
    subgraph Control["Control Layer"]
        AC["AgentController<br/><i>drives the step loop</i>"]
        ST["StateTracker / State<br/><i>holds state.view</i>"]
    end

    subgraph ThisModule["agents_browsing_visual_agent"]
        VBA["VisualBrowsingAgent<br/><b>step(state) -> Action</b>"]
        Helpers["Prompt builders<br/>get_tabs, get_axtree,<br/>get_action_prompt,<br/>get_history_prompt,<br/>create_goal_prompt,<br/>create_observation_prompt,<br/>get_error_prefix"]
    end

    subgraph Support["Supporting Modules"]
        RP["BrowsingResponseParser<br/><i>text -> Action</i>"]
        LLMR["LLMRegistry -> LLM<br/><i>multimodal completion</i>"]
        BG["BrowserGym<br/>HighLevelActionSet<br/>flatten_axtree_to_str"]
    end

    subgraph Runtime["Execution Layer"]
        BE["BrowserEnv<br/><i>Playwright + SoM overlay</i>"]
    end

    AC -->|"step(state)"| VBA
    ST -.->|"reads history"| VBA
    VBA --> Helpers
    VBA -->|"completion(messages)"| LLMR
    VBA -->|"parse(response)"| RP
    VBA -->|"action space + AXTree flatten"| BG
    RP -->|"BrowseInteractiveAction"| AC
    AC -->|"executes"| BE
    BE -->|"BrowserOutputObservation<br/>(axtree + set_of_marks)"| AC

    style ThisModule fill:#e8f0fe,stroke:#3367d6
    style VBA fill:#c5d9f7,stroke:#3367d6,stroke-width:2px
```

Related module docs:

| Concern | Module |
|---|---|
| The loop that calls `step()` | [agent_controller_core](agent_controller_core.md) |
| `State`, `state.view`, control flags | [agent_controller_state](agent_controller_state.md) |
| Turning LLM text into an `Action` | [agents_browsing_response_parsing](agents_browsing_response_parsing.md) |
| The text-only counterpart | [agents_browsing_text_agent](agents_browsing_text_agent.md) |
| Real browser process, screenshots, SoM overlay | [browser_environment](browser_environment.md) |
| LLM selection, multimodal routing, metrics | [llm_layer](llm_layer.md) |
| Trimming old screenshots from history | [memory_and_condensers](memory_and_condensers.md) |
| `Action` / `Observation` event types | [event_system](event_system.md) |
| `Message`, `TextContent`, `ImageContent` | [core_schema_and_runtime_support](core_schema_and_runtime_support.md) |

---

## Core Functionality

### The class contract

```python
class VisualBrowsingAgent(Agent):
    VERSION = '1.0'
    sandbox_plugins: list[PluginRequirement] = []
    response_parser = BrowsingResponseParser()
```

| Member | Meaning |
|---|---|
| `VERSION` | Prompt/behaviour version, used in eval reporting. |
| `sandbox_plugins` | Empty — this agent needs no Jupyter, no AgentSkills, no VSCode. Only a browser. |
| `response_parser` | Shared with the text browsing agent. Converts the raw LLM reply into an `Action`. |
| `action_space` | A BrowserGym `HighLevelActionSet`. Defines which commands are legal. |
| `error_accumulator` | Counts consecutive browser errors. Aborts the task past 5. |

### Action space

Set up once in `__init__`:

```python
action_subsets = ['chat', 'bid', 'nav', 'tab', 'infeas']
self.action_space = HighLevelActionSet(
    subsets=action_subsets,
    strict=False,        # tolerant parsing
    multiaction=False,   # exactly one action per turn
)
```

| Subset | What it unlocks |
|---|---|
| `chat` | `send_msg_to_user(...)` — talk to the user, report an answer |
| `bid` | `click`, `fill`, `select_option`, `hover`, ... on elements addressed by `bid` |
| `nav` | `goto`, `go_back`, `go_forward` |
| `tab` | `new_tab`, `tab_close`, `tab_focus` |
| `infeas` | `report_infeasible(...)` — declare the task impossible |

**Contrast with the text agent** ([agents_browsing_text_agent](agents_browsing_text_agent.md)), which uses only `['chat', 'bid']` plus optional `nav`, and sets `multiaction=True`:

| | `VisualBrowsingAgent` | `BrowsingAgent` |
|---|---|---|
| Screenshots | Yes (Set-of-Marks) | No |
| Goal images | Yes | No |
| Action subsets | chat, bid, nav, tab, infeas | chat, bid, (nav) |
| Actions per turn | 1 | many |
| AXTree filtering | Full tree, `visible`/`clickable` tags kept | Visible-only |
| History in prompt | Thought **and** action, per step | Action strings only |
| System prompt | Short, generic | Contains the goal |
| Temperature | `0.0` (pinned) | LLM default |
| Bootstrap `noop` | Always, with `return_axtree=True` | Only in eval mode |

The wider action space plus single-action-per-turn is a deliberate trade: more ways to move around, but one careful move at a time, since a screenshot only tells you about the state *before* the action.

### Static prompt blocks

Three text blocks are built once in `__init__` and reused every turn, so they cost nothing per step:

- **`action_prompt`** — from `get_action_prompt(action_space)`. Lists every legal command using `action_set.describe(with_long_description=False, with_examples=False)`. Short descriptions keep the prompt small, since the screenshot already eats many tokens.
- **`abstract_example`** — the required answer shape, ending with `` ```<action>``` ``.
- **`concrete_example`** — a worked example (a dropdown that needed `click` instead of `select_option`).
- **`hints`** — two reminders: always address elements by `bid`; comboboxes and autocompletes are fiddly.

---

## The Step Cycle

`step(state)` is the whole agent. It is pure: read `state`, build a prompt, call the LLM, parse, return.

```mermaid
flowchart TD
    Start(["step(state)"]) --> Boot{"len(state.view) == 1?"}
    Boot -->|Yes| Noop["return BrowseInteractiveAction<br/>noop(1000), return_axtree=True"]
    Boot -->|No| Scan["Scan state.view"]

    Scan --> Classify{"event type?"}
    Classify -->|BrowseInteractiveAction| Collect["append to prev_actions<br/>set last_action"]
    Classify -->|"MessageAction from AGENT"| Finish["return AgentFinishAction<br/>outputs={content}"]
    Classify -->|BrowserOutputObservation| Keep["last_obs = event"]
    Classify -->|other Observation| Skip["skip"]

    Collect --> Done
    Keep --> Done
    Skip --> Done
    Done["scan complete"] --> Trim["drop prev_actions[0]<br/><i>the bootstrap noop</i>"]

    Trim --> SendMsg{"last_action had<br/>browsergym_send_msg_to_user?"}
    SendMsg -->|Yes| Msg["return MessageAction(msg)"]
    SendMsg -->|No| Hist["history_prompt = get_history_prompt(prev_actions)"]

    Hist --> HasObs{"last_obs is a<br/>BrowserOutputObservation?"}
    HasObs -->|No| Goal
    HasObs -->|Yes| Err{"last_obs.error?"}

    Err -->|Yes| Count["error_prefix = get_error_prefix()<br/>error_accumulator += 1"]
    Err -->|No| Focus
    Count --> Over{"error_accumulator > 5?"}
    Over -->|Yes| Fail["return MessageAction<br/>'Too many errors. Task failed.'"]
    Over -->|No| Focus

    Focus["focused_element, tabs = get_tabs()"] --> Flat["flatten_axtree_to_str(...)"]
    Flat -->|raises| AxErr["return MessageAction<br/>'Error encountered when browsing.'"]
    Flat -->|ok| SoM["set_of_marks = last_obs.set_of_marks"]

    SoM --> Goal["goal, image_urls = state.get_current_user_intent()<br/>fallback: state.inputs['task']"]
    Goal --> Build["Assemble multimodal user message"]
    Build --> Call["llm.completion(temperature=0.0,<br/>stop=[')```', ')\\n```'])"]
    Call --> Parse["response_parser.parse(response)"]
    Parse --> Out(["Action"])

    style Noop fill:#fff4e0,stroke:#e8a33d
    style Finish fill:#e6f4ea,stroke:#34a853
    style Msg fill:#e6f4ea,stroke:#34a853
    style Fail fill:#fce8e6,stroke:#d93025
    style AxErr fill:#fce8e6,stroke:#d93025
    style Out fill:#e8f0fe,stroke:#3367d6
```

### The bootstrap `noop`

```python
if len(state.view) == 1:
    return BrowseInteractiveAction(browser_actions='noop(1000)', return_axtree=True)
```

On the very first call the history holds only the user's task. The agent has no page to look at. Rather than guess, it issues a do-nothing action that waits 1000 ms and asks for the AXTree back.

Two reasons this matters:

- **Benchmarks.** In VisualWebArena, WebArena and MiniWoB++, `BrowserEnv` already sits on the task's starting page. The `noop` is how the agent *fetches* that page without changing it.
- **`return_axtree=True`.** In `openhands/runtime/browser/utils.py::browse`, the AXTree, DOM and element properties are **stripped from the observation unless `return_axtree` is set**. This agent needs the full tree, so it must always ask.

The bootstrap action is later removed from the prompt history (`prev_actions = prev_actions[1:]`) so the LLM never sees a pointless `noop` as step 1.

Note the difference from the text agent, which gates its `noop` behind an `EVAL_MODE` flag. The visual agent always does it — a screenshot-driven agent is useless without a first screenshot.

### Reading history

The scan over `state.view` is a small state machine with three exits:

| Event seen | Effect |
|---|---|
| `BrowseInteractiveAction` | Recorded in `prev_actions`; tracked as `last_action` |
| `MessageAction` with `source == EventSource.AGENT` | **Terminate.** The agent already answered; return `AgentFinishAction` |
| `BrowserOutputObservation` | Overwrite `last_obs` — only the newest page matters |
| Any other `Observation` | Skipped explicitly |

That last row is a defensive guard. In a delegation setup, or when microagents inject `RecallObservation`s, unrelated observations land in the view. Skipping them (instead of assigning them to `last_obs`, which the text agent does) stops the agent from mistaking a non-browser event for the current page.

Only `last_obs` is used for the page snapshot — the agent shows the LLM **one** screenshot and **one** AXTree, never a stack of them. Old screenshots survive only as text in the history block. This is what keeps token use bounded without a condenser, though [BrowserOutputCondenser](memory_and_condensers.md) can trim further.

### Early exit via `send_msg_to_user`

```python
if isinstance(last_action, BrowseInteractiveAction) and last_action.browsergym_send_msg_to_user:
    return MessageAction(last_action.browsergym_send_msg_to_user)
```

BrowserGym's `send_msg_to_user` is a *browser* command, so its message would otherwise be trapped inside the browser layer. `BrowsingResponseParser` extracts it into `browsergym_send_msg_to_user` when parsing; here the agent lifts it into a real OpenHands `MessageAction` so the user actually sees it.

On the following turn, that `MessageAction` (source `AGENT`) is what triggers `AgentFinishAction`. So finishing takes two hops:

```mermaid
sequenceDiagram
    participant LLM
    participant VBA as VisualBrowsingAgent
    participant RP as BrowsingResponseParser
    participant AC as AgentController

    LLM->>RP: "...```send_msg_to_user('The price is $42')```"
    RP->>VBA: BrowseInteractiveAction(browsergym_send_msg_to_user="The price is $42")
    VBA->>AC: (that action)
    AC->>VBA: step(state)  %% turn N+1
    Note over VBA: last_action has send_msg_to_user
    VBA->>AC: MessageAction("The price is $42")
    AC->>VBA: step(state)  %% turn N+2
    Note over VBA: sees MessageAction from AGENT
    VBA->>AC: AgentFinishAction(outputs={'content': ...})
```

### Error handling

Two independent guards:

**1. Browser errors — counted, with an exception.**

```python
def get_error_prefix(obs):
    if 'timeout' in obs.last_browser_action_error:
        return ''                      # swallowed on purpose
    return f'## Error from previous action:\n{obs.last_browser_action_error}\n'
```

Timeouts return an empty prefix. Since `error_accumulator` only increments when `len(error_prefix) > 0`, **timeouts are not counted at all** — a documented workaround for the OneStopMarket site in WebArena, which times out routinely while still rendering a usable page. Real errors are surfaced to the LLM and counted; past 5 the agent gives up with a `MessageAction`.

**2. AXTree parse failure — fatal immediately.**

`flatten_axtree_to_str` is wrapped in `try/except`. If the tree cannot be flattened there is no observation to reason about, so the agent bails with `MessageAction('Error encountered when browsing.')` rather than prompting on an empty page.

---

## Prompt Construction

This is the heart of the module. The user message is a **list** of alternating text and image parts, which is what makes the agent multimodal.

```mermaid
graph LR
    subgraph Sources["From state / observation"]
        G["goal + image_urls<br/><i>get_current_user_intent()</i>"]
        O["last_obs<br/>axtree_object,<br/>extra_element_properties,<br/>open_pages_urls,<br/>focused_element_bid,<br/>set_of_marks"]
        H["prev_actions"]
    end

    subgraph Builders["Helper functions"]
        B1["create_goal_prompt"]
        B2["get_tabs"]
        B3["get_axtree"]
        B4["get_error_prefix"]
        B5["create_observation_prompt"]
        B6["get_history_prompt"]
    end

    subgraph Msg["Message(role='user')"]
        P1["1. TextContent<br/>goal_txt"]
        P2["2. ImageContent<br/>goal images <i>(if any)</i>"]
        P3["3. TextContent<br/>tabs + AXTree +<br/>focused + error"]
        P4["4. ImageContent<br/>SoM screenshot <i>(if any)</i>"]
        P5["5. TextContent<br/>history + action space +<br/>hints + examples"]
    end

    G --> B1 --> P1
    G --> P2
    O --> B2 --> B5
    O --> B3 --> B5
    O --> B4 --> B5
    B5 --> P3
    O -->|set_of_marks| P4
    H --> B6 --> P5

    style Msg fill:#e8f0fe,stroke:#3367d6
```

### Part 1 — Goal (`create_goal_prompt`)

Instructions plus the user's task. If the user attached images, a line `Images: Goal input image (N)` is appended per image so the LLM can tell which picture is which. The URLs are returned separately and become part 2.

This is how a task like *"find the product in this photo"* works: the photo rides along as `image_urls` on the user's `MessageAction`, is surfaced by `state.get_current_user_intent()`, and is placed right next to its label.

### Part 3 — Observation (`create_observation_prompt`)

Concatenates, in order: tabs, AXTree, focused element, error prefix. Then, if a Set-of-Marks screenshot exists, appends a caption that includes a critical warning:

> *only visible portion of webpage is present in the screenshot. You may need to scroll to view the remaining portion*

Without this, the LLM tends to assume the screenshot is the whole page and declares items missing when they are merely below the fold.

If `set_of_marks` is empty, the function logs `SOM Screenshot not present in observation!` and returns `None` — the agent then runs **text-only** for that turn instead of failing. Graceful degradation.

**Tabs** (`get_tabs`) lists every open page with its URL and marks the active one — needed because the `tab` action subset is enabled.

**AXTree** (`get_axtree`) prefixes the tree with two notes: `bid` is the element handle, and only elements tagged `visible` can be interacted with. The flatten call is deliberately permissive:

```python
flatten_axtree_to_str(
    last_obs.axtree_object,
    extra_properties=last_obs.extra_element_properties,
    with_visible=True,          # tag visibility
    with_clickable=True,        # tag clickability
    with_center_coords=False,   # screenshot carries position
    with_bounding_box_coords=False,
    filter_visible_only=False,  # keep the WHOLE page
    filter_with_bid_only=False,
    filter_som_only=False,
)
```

The design here is the key insight of the module. The **full** tree is kept (nothing filtered out) so the agent knows what exists off-screen, while `with_visible` tags tell it what it can act on *right now*. Coordinates are dropped because the screenshot conveys layout better than numbers. The text agent does the opposite — `filter_visible_only=True` — because with no screenshot, off-screen nodes are just noise it can never act on.

### Part 5 — History and guidance (`get_history_prompt`)

Every prior step is rendered as:

```
## step N

Ouput thought and action: <thought> ```<browser_actions>```
```

Including the **thought**, not just the action, is another visual-agent-specific choice. Since the old screenshots are gone from the context, the recorded reasoning is the only surviving trace of *why* a step was taken and what the agent believed it saw.

Appended after the history: the action space, hints, and the two examples.

### System message

Short and fixed:

> *You are an agent trying to solve a web task based on the content of the page and user instructions. You can interact with the page and explore, and send messages to the user when you finish the task. Each time you submit an action it will be sent to the browser and you will receive a new page.*

The goal deliberately lives in the **user** message, not here — so a changing goal (multi-turn conversation) never invalidates the cacheable system prefix. The text agent bakes the goal into its system message instead.

### LLM call

```python
response = self.llm.completion(
    messages=messages,
    temperature=0.0,
    stop=[')```', ')\n```'],
)
```

- `temperature=0.0` — pinned for reproducible benchmark runs.
- `stop=[')```', ')\n```']` — cuts generation the moment the action's closing fence appears, so the model cannot ramble past its own action. Note this **strips the terminator**, which is exactly why `BrowsingResponseParser.parse_response` re-appends `)``` ` before parsing.

The `self.llm` handle comes from `LLMRegistry.get_llm_from_agent_config` in the base `Agent`. Because this agent sends images, a vision-capable model is required; see [llm_layer](llm_layer.md) for `MultimodalRouter`, which routes multimodal turns to a capable model.

---

## Component Interaction

```mermaid
sequenceDiagram
    autonumber
    participant AC as AgentController
    participant VBA as VisualBrowsingAgent
    participant BGym as BrowserGym helpers
    participant LLM as LLM (vision)
    participant RP as BrowsingResponseParser
    participant BE as BrowserEnv

    AC->>VBA: step(state)
    Note over VBA: first call: history has 1 event
    VBA-->>AC: BrowseInteractiveAction('noop(1000)', return_axtree=True)
    AC->>BE: browse(action)
    BE-->>AC: BrowserOutputObservation<br/>(axtree_object, set_of_marks, tabs, ...)

    AC->>VBA: step(state)
    VBA->>VBA: scan view -> prev_actions, last_obs
    VBA->>BGym: flatten_axtree_to_str(axtree_object, ...)
    BGym-->>VBA: AXTree text with bids
    VBA->>VBA: build goal / observation / history parts
    VBA->>LLM: completion(system + [text, img, text, img, text])
    LLM-->>VBA: "Let's think... ```click('324')"
    VBA->>RP: parse(response)
    RP->>RP: re-append ')```', split on fences,<br/>extract thought + action
    RP-->>VBA: BrowseInteractiveAction(browser_actions="click('324')", thought=...)
    VBA-->>AC: action
    AC->>BE: browse(action)
    BE-->>AC: new BrowserOutputObservation
    Note over AC,BE: loop until send_msg_to_user,<br/>error limit, or iteration cap
```

### Data dependencies

```mermaid
graph TD
    subgraph Obs["BrowserOutputObservation fields consumed"]
        F1["axtree_object"]
        F2["extra_element_properties"]
        F3["set_of_marks"]
        F4["open_pages_urls"]
        F5["active_page_index"]
        F6["focused_element_bid"]
        F7["last_browser_action_error"]
        F8["error"]
    end

    subgraph Prompt["Prompt slot"]
        S1["AXTree block"]
        S2["Screenshot image"]
        S3["Tabs block"]
        S4["Focused element"]
        S5["Error prefix"]
    end

    F1 --> S1
    F2 --> S1
    F3 --> S2
    F4 --> S3
    F5 --> S3
    F6 --> S4
    F7 --> S5
    F8 --> S5

    style Obs fill:#f1f3f4,stroke:#5f6368
    style Prompt fill:#e8f0fe,stroke:#3367d6
```

Note what is **not** used: `content` (the html2text rendering), `screenshot` (the raw, unannotated image), `screenshot_path`, and `dom_object`. The agent prefers the AXTree over flattened HTML, and the marked-up `set_of_marks` image over the plain screenshot — because the marks are what let the LLM name an element by `bid`.

`set_of_marks` is produced in `BrowserEnv.browser_process` by `overlay_som(...)` over the raw Playwright screenshot, then base64-encoded as a data URL. See [browser_environment](browser_environment.md).

---

## Design Notes

**Stateless by design.** The only mutable field is `error_accumulator`, and `reset()` clears it while leaving LLM metrics alone (metrics live in [llm_layer](llm_layer.md) and must survive across a delegation). Everything else is recomputed from `state.view` each turn, which makes the agent safe to replay — see [agent_controller_safeguards_replay](agent_controller_safeguards_replay.md).

**No prompt templates.** Unlike CodeAct-family agents, this agent builds prompts with plain Python f-strings, not `PromptManager` Jinja templates. It also does not define `_prompt_manager`, so `get_system_message()` from the base `Agent` would raise; the system message is inlined in `step()` instead.

**No tool calling.** The agent uses free-text output with fenced actions plus a regex/AST parser, not the LLM function-calling API. This keeps it compatible with BrowserGym's action grammar and with the shared parser used by the text agent.

**Single screenshot per turn.** The most important cost control in the module. Screenshots are large; keeping only the latest one bounds context growth. When even that is too much, wire in a condenser from [memory_and_condensers](memory_and_condensers.md).

**Known rough edges.**

- `state.inputs['task']` is used as the goal fallback and will `KeyError` if no user message and no `task` input exist.
- `'timeout' in obs.last_browser_action_error` is a substring match — any error text containing "timeout" bypasses the error counter.
- A typo, `Ouput thought and action`, appears in every history entry; harmless, but it is part of the prompt the model sees.
- `prev_actions[1:]` assumes the first recorded action was the bootstrap `noop`. In a resumed or delegated conversation whose view starts mid-task, this drops a real action.

---

## Registration and Selection

The agent registers itself with the `Agent` class registry (`Agent.register`) at import of `openhands/agenthub`, and is chosen by name through `AgentConfig`. Set the agent to `VisualBrowsingAgent` — for example in `config.toml`:

```toml
[core]
default_agent = "VisualBrowsingAgent"
```

Because `sandbox_plugins` is empty, no runtime plugins are installed; the runtime only needs a working `BrowserEnv`. See [runtime_plugins](runtime_plugins.md) and [runtime_implementations](runtime_implementations.md).

---

## Summary

| Aspect | Detail |
|---|---|
| Purpose | Web browsing driven by screenshots plus accessibility tree |
| Public surface | `VisualBrowsingAgent.__init__`, `.reset()`, `.step(state)` |
| Inputs | `State` (history) and `BrowserOutputObservation` (page snapshot) |
| Outputs | `BrowseInteractiveAction`, `MessageAction`, or `AgentFinishAction` |
| Key dependency | BrowserGym `HighLevelActionSet` + `flatten_axtree_to_str` |
| Multimodal parts | Goal images, and one Set-of-Marks screenshot per turn |
| Termination | `send_msg_to_user` → `MessageAction` → `AgentFinishAction`; or 5 errors; or AXTree failure |
| Best suited for | VisualWebArena, image-grounded tasks, visually complex pages |
