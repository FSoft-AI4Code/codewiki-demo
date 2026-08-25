# llm_layer_sync_core: The Synchronous LLM Client

## Introduction

This module holds one class: `LLM` in `openhands/llm/llm.py`. It is the single door through which every part of OpenHands talks to a language model.

The job sounds simple — "send messages, get a reply" — but the class does much more. Model providers do not behave the same way. Some support native tool calling, some do not. Some accept `max_completion_tokens`, others want `max_tokens`. Some charge for cache writes, others do not. Some crash if you send both `temperature` and `top_p`. `LLM` hides all of that. Callers get one stable method, `llm.completion(messages=..., tools=...)`, and always get back a normal LiteLLM `ModelResponse` with tool calls in it — even when the model behind it has no idea what a tool call is.

Everything else in the LLM layer builds on this class. [`AsyncLLM` and `StreamingLLM`](llm_layer_clients_async_streaming.md) subclass it, [`RouterLLM`](llm_layer_routing.md) wraps it, and [`LLMRegistry`](llm_layer_registry.md) creates and hands out instances of it.

---

## 1. What the module is responsible for

| Responsibility | Where it happens |
| --- | --- |
| Build a pre-bound completion function for one model | `__init__` (the `partial(litellm_completion, ...)`) |
| Discover model limits and capabilities | `init_model_info()` |
| Normalize provider quirks into working kwargs | `__init__` (the long chain of `if` blocks) |
| Emulate tool calling for models that lack it | the `wrapper` closure + `fn_call_converter` |
| Retry failed calls with backoff | [`RetryMixin`](llm_layer_clients_mixins.md) |
| Log prompts and responses | [`DebugMixin`](llm_layer_clients_mixins.md) |
| Measure cost, tokens, and latency | `_post_completion()`, `_completion_cost()` → [`Metrics`](llm_layer_metrics.md) |
| Count tokens for condensers and budget checks | `get_token_count()` |
| Serialize `Message` objects with the right flags | `format_messages_for_llm()` |
| Write raw completion logs for evaluation runs | the `wrapper` closure |

What it does **not** do: it does not decide *what* to send (that is the [agent controller](agent_controller_core.md) and [memory/condensers](memory_and_condensers.md)), it does not pick *which* model to use (that is [routing](llm_layer_routing.md)), and it does not own the lifecycle of instances (that is the [registry](llm_layer_registry.md)).

---

## 2. Where it sits in the system

```mermaid
graph TB
    subgraph callers["Callers"]
        AC["AgentController<br/>agent_controller_core"]
        AG["Agents<br/>agents"]
        COND["LLM condensers<br/>memory_and_condensers"]
        SEC["LLMRiskAnalyzer<br/>security_analyzers"]
        SOLV["Solvability classifier<br/>enterprise_solvability"]
    end

    subgraph layer["LLM layer"]
        REG["LLMRegistry<br/>llm_layer_registry"]
        ROUTER["RouterLLM<br/>llm_layer_routing"]
        LLM["LLM<br/>(this module)"]
        ASYNC["AsyncLLM / StreamingLLM<br/>llm_layer_clients_async_streaming"]
    end

    subgraph support["Support"]
        MIX["RetryMixin + DebugMixin<br/>llm_layer_clients_mixins"]
        FEAT["get_features<br/>llm_layer_clients_model_features"]
        MET["Metrics<br/>llm_layer_metrics"]
        CFG["LLMConfig<br/>core_configuration"]
        MSG["Message<br/>core_schema_and_runtime_support"]
    end

    LITE["litellm"]
    PROV["Model providers<br/>OpenAI / Anthropic / Bedrock / proxy / local"]

    AC --> REG
    AG --> REG
    COND --> LLM
    SEC --> LLM
    SOLV --> LLM
    REG --> LLM
    REG --> ROUTER
    ROUTER --> LLM
    ASYNC -.->|"subclass of"| LLM

    LLM -.->|"mixes in"| MIX
    LLM --> FEAT
    LLM --> MET
    CFG --> LLM
    MSG --> LLM
    LLM --> LITE --> PROV
```

The key point: almost nobody constructs `LLM` directly. They ask the [registry](llm_layer_registry.md) for one by `service_id`, so the same model instance (and the same `Metrics` object) is shared across a conversation.

---

## 3. Internal structure

```mermaid
classDiagram
    class RetryMixin {
        +retry_decorator(**kwargs) Callable
        +log_retry_attempt(retry_state)
    }
    class DebugMixin {
        +log_prompt(messages)
        +log_response(resp)
        +vision_is_active() bool
    }
    class LLM {
        +config: LLMConfig
        +service_id: str
        +metrics: Metrics
        +model_info: ModelInfo
        +tokenizer
        +retry_listener
        +cost_metric_supported: bool
        -_completion: Callable
        -_completion_unwrapped: Callable
        -_function_calling_active: bool
        -_tried_model_info: bool
        +completion : property
        +init_model_info()
        +vision_is_active() bool
        +is_caching_prompt_active() bool
        +is_function_calling_active() bool
        +get_token_count(messages) int
        +format_messages_for_llm(messages) list
        -_supports_vision() bool
        -_post_completion(response) float
        -_completion_cost(response) float
        -_is_local() bool
    }
    class AsyncLLM {
        +async_completion : property
    }
    class StreamingLLM {
        +async_streaming_completion : property
    }

    RetryMixin <|-- LLM
    DebugMixin <|-- LLM
    LLM <|-- AsyncLLM
    AsyncLLM <|-- StreamingLLM

    LLM --> Metrics : records into
    LLM --> LLMConfig : reads
    LLM ..> ModelFeatures : asks get_features()
```

`LLM` is deliberately not abstract. It is a concrete, ready-to-use client, and the async and streaming variants extend it rather than replace it. That is why `DebugMixin.vision_is_active()` raises `NotImplementedError` — the mixin expects its host class to answer that question, and `LLM` does.

---

## 4. Construction: turning config into a callable

`__init__` is the most important method in the file. It runs once per instance and does five things in order.

```mermaid
flowchart TD
    START(["LLM(config, service_id, metrics, retry_listener)"]) --> COPY["deepcopy config<br/>attach or create Metrics"]
    COPY --> LOGDIR{"log_completions<br/>enabled?"}
    LOGDIR -->|"yes, no folder"| ERR["raise RuntimeError"]
    LOGDIR -->|"otherwise"| INFO["init_model_info()"]

    INFO --> TOK{"custom_tokenizer set?"}
    TOK -->|yes| PRE["create_pretrained_tokenizer()"]
    TOK -->|no| NOTOK["tokenizer = None"]

    PRE --> KW
    NOTOK --> KW

    KW["base kwargs:<br/>temperature, max_completion_tokens,<br/>optional top_k / top_p"] --> QUIRKS

    subgraph QUIRKS["Provider normalization"]
        direction TB
        Q1["openhands/* → litellm_proxy/* +<br/>all-hands proxy base_url"]
        Q2["reasoning models: set reasoning_effort<br/>(Gemini 2.5 Pro low/none → thinking budget 128)<br/>drop temperature and top_p"]
        Q3["azure*: max_completion_tokens → max_tokens"]
        Q4["mistral / gemini: pass safety_settings"]
        Q5["always pass AWS region + keys for Bedrock"]
        Q6["claude-opus-4-1: thinking disabled,<br/>drop top_p when temperature present"]
        Q1 --> Q2 --> Q3 --> Q4 --> Q5 --> Q6
    end

    QUIRKS --> PARTIAL["_completion = partial(litellm_completion,<br/>model, api_key, base_url, api_version,<br/>custom_llm_provider, timeout,<br/>drop_params, seed, **kwargs)"]
    PARTIAL --> UNWRAP["_completion_unwrapped = _completion"]
    UNWRAP --> WRAP["define wrapper(), decorate with<br/>retry_decorator(...)"]
    WRAP --> DONE(["_completion = wrapper"])
```

Two details worth remembering:

- **`_completion` vs `_completion_unwrapped`.** The unwrapped one is the raw `partial` that calls LiteLLM. The wrapped one is the retrying, logging, tool-converting closure exposed through the `completion` property. Tests and subclasses patch `_completion_unwrapped` to intercept the real network call without losing the surrounding behavior.
- **Config is deep-copied and then mutated.** Rewriting `openhands/foo` to `litellm_proxy/foo`, filling in `max_input_tokens`, and forcing `top_p = 0.9` on Hugging Face all write back into `self.config`. The caller's config object is never touched, but `self.config` after construction is *not* the same as what was passed in. The [registry](llm_layer_registry.md) compares configs by equality when deciding whether to reuse a service, so this matters.

### The provider quirk table

| Condition | What changes |
| --- | --- |
| `model` starts with `openhands/` | rewritten to `litellm_proxy/<name>`, `base_url` set to the All-Hands LLM proxy |
| `get_features(model).supports_reasoning_effort` | `reasoning_effort` added; `temperature` and `top_p` removed |
| `gemini-2.5-pro` with effort in `{None, low, none}` | swapped for `thinking = {budget_tokens: 128}` plus `allowed_openai_params` |
| `model` starts with `azure` | `max_completion_tokens` replaced by `max_tokens` |
| `mistral` or `gemini` in name, and `safety_settings` set | `safety_settings` forwarded |
| always | `aws_region_name`, and AWS keys if present, forwarded for Bedrock |
| `claude-opus-4-1` | `thinking = {type: disabled}`; `top_p` dropped when `temperature` is present |
| `huggingface*` (in `init_model_info`) | `top_p` of 1 lowered to 0.9 |

The capability checks come from [`get_features`](llm_layer_clients_model_features.md) rather than from string matching scattered here, so adding a new model family is mostly a change in that module — the string checks left in `llm.py` are the per-model exceptions that do not generalize.

---

## 5. Model discovery: `init_model_info()`

Before `LLM` can build kwargs it needs to know the model's limits. `init_model_info` guards itself with `_tried_model_info` so it only ever runs once, and it tries several sources in order until something answers.

```mermaid
flowchart TD
    A(["init_model_info()"]) --> GUARD{"_tried_model_info?"}
    GUARD -->|yes| RET(["return"])
    GUARD -->|no| MARK["set _tried_model_info = True"]

    MARK --> S1{"openrouter/*?"}
    S1 -->|yes| L1["litellm.get_model_info(full name)"]
    S1 -->|no| S2
    L1 --> S2

    S2{"litellm_proxy/*?"} -->|yes| HTTP["httpx GET {base_url}/v1/model/info<br/>match on model_name"]
    S2 -->|no| S3
    HTTP --> S3

    S3{"model_info still empty?"} -->|yes| L2["litellm.get_model_info(name.split(':')[0])"]
    S3 -->|no| APPLY
    L2 --> S4{"still empty?"}
    S4 -->|yes| L3["litellm.get_model_info(name.split('/')[-1])"]
    S4 -->|no| APPLY
    L3 --> APPLY

    APPLY["apply findings"] --> A1["huggingface: clamp top_p to 0.9"]
    A1 --> A2["max_input_tokens ← model_info<br/>(only if unset)"]
    A2 --> A3["max_output_tokens ← 64000 for claude-3-7-sonnet,<br/>else model_info max_output_tokens or max_tokens"]
    A3 --> A4["_function_calling_active ←<br/>config.native_tool_calling ?? features.supports_function_calling"]
    A4 --> END(["done"])
```

Every lookup is wrapped in a bare `except` — an unknown model must not stop the client from working. It just means `model_info` stays `None`, cost calculation may fall back or give up, and context-window reporting is 0.

Note that the LiteLLM-proxy branch makes a **blocking HTTP request inside `__init__`**. Constructing an `LLM` against a proxy is not free, which is another reason instances are cached in the registry.

---

## 6. The completion path

This is what happens on every `llm.completion(...)` call.

```mermaid
sequenceDiagram
    participant C as Caller (agent / condenser)
    participant W as wrapper (retry-decorated)
    participant F as fn_call_converter
    participant U as _completion_unwrapped
    participant P as Provider (via litellm)
    participant M as Metrics

    C->>W: completion(messages=[Message|dict], tools=[...])
    W->>W: normalize args → kwargs['messages']
    alt messages are Message objects
        W->>W: format_messages_for_llm()<br/>set cache / vision / fncall flags
    end
    W->>W: keep deepcopy as original_fncall_messages

    alt native tool calling OFF and tools given
        W->>F: convert_fncall_messages_to_non_fncall_messages()
        F-->>W: prompt-style messages
        W->>W: add STOP_WORDS if supported<br/>pop 'tools'<br/>tool_choice = 'none' (openhands-lm) or removed
    end

    W->>W: raise if messages empty
    W->>W: log_prompt() [DebugMixin]
    W->>W: litellm.modify_params = config.modify_params<br/>drop extra_body unless proxy
    W->>U: call with final kwargs
    U->>P: HTTP request

    alt transient failure (429, timeout, 5xx, no-response)
        P--xU: error
        U--xW: raises
        W->>W: RetryMixin backoff, notify retry_listener,<br/>bump temperature to 1.0 on LLMNoResponseError
        W->>U: retry
        U->>P: HTTP request
    end

    P-->>U: ModelResponse
    U-->>W: resp
    W->>M: add_response_latency(elapsed, response_id)

    alt tool calling was mocked
        W->>W: raise LLMNoResponseError if no choices
        W->>F: convert_non_fncall_messages_to_fncall_messages()
        F-->>W: message with real tool_calls
        W->>W: splice into resp.choices[0].message
    end

    W->>W: raise LLMNoResponseError if still no choices
    W->>W: log_response() [DebugMixin]
    W->>W: _post_completion(resp)
    W->>M: add_cost(), add_token_usage()

    opt config.log_completions
        W->>W: write JSON to log_completions_folder
    end

    W-->>C: ModelResponse (always with tool_calls when tools were sent)
```

### Argument normalization

Callers are inconsistent, so the wrapper accepts several shapes:

- `completion(messages=[...])` — the normal case.
- `completion(model, messages, ...)` positionally — the first positional argument is **deliberately ignored**, because the model is already bound in the `partial`. Callers cannot override the configured model here.
- A single `Message` instead of a list — wrapped into a list.

If the first list item is a `Message`, the whole list goes through `format_messages_for_llm()`; otherwise it is assumed to already be dicts.

### Function-call emulation

This is the module's most valuable trick. When `is_function_calling_active()` is `False` but the caller passed `tools`, the wrapper:

1. Converts tool definitions into a system-prompt suffix and rewrites the conversation into plain text (`tool` messages become `user` messages prefixed with `EXECUTION RESULT of [name]:`).
2. Optionally prepends an in-context learning example — skipped for `openhands-lm` and `devstral`, which are already trained on the format.
3. Adds `STOP_WORDS` so the model stops after emitting one call, unless the model does not support stop words or `disable_stop_word` is set.
4. Removes `tools` from the request entirely.
5. After the response comes back, parses the `<function=...>` block out of the text and rebuilds a real `tool_calls` structure on `resp.choices[0].message`.

The caller never sees the difference. Only one tool call per message is supported by this path.

```mermaid
flowchart LR
    subgraph in["Request"]
        A["messages + tools<br/>(native format)"] -->|"mock path"| B["messages with tool<br/>docs in system prompt"]
    end
    subgraph out["Response"]
        C["assistant text with<br/>&lt;function=...&gt; block"] -->|"reverse convert"| D["assistant message with<br/>tool_calls[0]"]
    end
    B --> P["provider"] --> C
    A -.->|"native path"| P
    P -.->|"native path"| D
```

### Failure handling

`LLM_RETRY_EXCEPTIONS` is the retry set: `APIConnectionError`, `RateLimitError`, `ServiceUnavailableError`, `litellm.Timeout`, `litellm.InternalServerError`, and OpenHands' own `LLMNoResponseError`. Everything else propagates straight to the caller.

`LLMNoResponseError` is raised by `LLM` itself in two places — after mock-fncall conversion, and again on the final `choices` check — for the case where a provider (mostly Gemini) returns a response with no choices. Because it is in the retry set, [`RetryMixin`](llm_layer_clients_mixins.md) catches it and, if `temperature` was 0, nudges it to 1.0 before retrying. A deterministic empty response often becomes a real one with a little randomness.

The `retry_listener` callback, passed in by the [registry](llm_layer_registry.md), is how retry attempts surface to the UI as status updates.

---

## 7. Accounting: cost, tokens, latency

Every successful call ends in `_post_completion()`, which is the only place metrics are written.

```mermaid
flowchart TD
    R(["_post_completion(response)"]) --> COST["_completion_cost(response)"]

    subgraph CH["_completion_cost cascade"]
        direction TB
        C0{"cost_metric_supported?"} -->|no| CZERO["return 0.0"]
        C0 -->|yes| C1["build custom CostPerToken<br/>if configured in LLMConfig"]
        C1 --> C2{"response._hidden_params has<br/>llm_provider-x-litellm-response-cost?"}
        C2 -->|yes| CUSE["use it"]
        C2 -->|no| C3["litellm_completion_cost(response)"]
        C3 --> C4{"still None?"}
        C4 -->|yes| C5["retry with model name<br/>stripped of first path segment"]
        C4 -->|no| CUSE
        C5 --> CUSE
        CUSE --> CADD["metrics.add_cost(cost)"]
        C3 -.->|"raises"| CFLAG["cost_metric_supported = False<br/>return 0.0 forever after"]
    end

    COST --> STATS["build stats string:<br/>cost, accumulated cost, latest latency"]
    STATS --> U{"response has usage?"}
    U -->|no| LOG
    U -->|yes| TOK["read prompt_tokens, completion_tokens,<br/>prompt_tokens_details.cached_tokens,<br/>model_extra.cache_creation_input_tokens"]
    TOK --> CW["context_window from model_info.max_input_tokens"]
    CW --> ADD["metrics.add_token_usage(...)"]
    ADD --> LOG["logger.debug(stats)"]
    LOG --> RET(["return cost"])
```

Points to know:

- **Cache reads and cache writes are tracked separately.** Anthropic charges differently for writing to the prompt cache than for reading from it, but LiteLLM does not split them in `usage`. `LLM` reads `cached_tokens` from `prompt_tokens_details` and digs `cache_creation_input_tokens` out of the provider-specific `model_extra` to get both numbers.
- **`cost_metric_supported` is a one-way latch.** The first time cost calculation throws, it flips to `False` and no further cost work is attempted for this instance. Local and unknown models silently report zero cost instead of spamming errors.
- **Latency is measured around the unwrapped call only**, so it excludes conversion and logging overhead but includes the whole retry-free network round trip. It is recorded even for calls that later fail the `choices` check.
- The `Metrics` object may be **shared**. The registry passes a conversation-wide instance so cost across agent, condenser, and delegate calls accumulates in one place — see [llm_layer_metrics](llm_layer_metrics.md) and [server_sessions](server_sessions.md) (`ConversationStats`).

`_is_local()` exists to identify locally-served models (a `localhost`/`127.0.0.1`/`0.0.0.0` base URL, or an `ollama` model) so they can be treated as free.

---

## 8. Capability flags and message serialization

Four small predicates drive most conditional behavior:

| Method | Answer comes from | Cached? |
| --- | --- | --- |
| `vision_is_active()` | `not config.disable_vision and _supports_vision()` | no |
| `_supports_vision()` | `OPENHANDS_FORCE_VISION` env var, or `litellm.supports_vision` on the full name **or** the suffix after the last `/`, or `model_info['supports_vision']` | no |
| `is_caching_prompt_active()` | `config.caching_prompt and get_features(model).supports_prompt_cache` | no |
| `is_function_calling_active()` | `_function_calling_active`, set once in `init_model_info` | yes |

The double vision check exists because LiteLLM returns `False` for prefixed names like `openai/gpt-4o` even when the model does support images.

`format_messages_for_llm()` is where these flags reach the [`Message`](core_schema_and_runtime_support.md) model. It stamps `cache_enabled`, `vision_enabled`, and `function_calling_enabled` on every message, then lets Pydantic serialize. Those flags decide whether a message becomes a single string or a list of content blocks. A few models need the string form even though they support other features, so `force_string_serializer` is set for `deepseek`, `kimi-k2-instruct` on `groq`, and `openrouter/anthropic/claude-sonnet-4`.

```mermaid
flowchart LR
    MSGS["list[Message]"] --> FLAGS["format_messages_for_llm()"]
    FLAGS -->|"cache_enabled"| S["Message.serialize_model()"]
    FLAGS -->|"vision_enabled"| S
    FLAGS -->|"function_calling_enabled"| S
    FLAGS -->|"force_string_serializer<br/>(deepseek, groq kimi, some openrouter)"| S
    S --> LIST["list-of-content-blocks form"]
    S --> STR["single-string form"]
    LIST --> OUT["list[dict] for litellm"]
    STR --> OUT
```

`get_token_count()` reuses the same serialization, then calls `litellm.token_counter` with the custom tokenizer if one was loaded. On any error it logs and returns `0` — a deliberate choice, since a token-count failure should not break a condenser or a budget check. Callers should treat `0` as "unknown", not "empty". This method is the main entry point used by [condensers](memory_and_condensers.md) to decide when history must be shrunk.

---

## 9. Lifecycle summary

```mermaid
stateDiagram-v2
    [*] --> Constructing: LLM(config, service_id, ...)
    Constructing --> Probing: init_model_info()
    Probing --> Probing: try openrouter / proxy HTTP / name fallbacks
    Probing --> Configured: limits + capability flags fixed
    Configured --> Ready: partial + retry-wrapped wrapper built
    Ready --> Calling: completion(messages, tools)
    Calling --> Retrying: retryable exception
    Retrying --> Calling: backoff elapsed
    Retrying --> Failed: retries exhausted (reraise)
    Calling --> Accounting: ModelResponse received
    Accounting --> Ready: metrics updated, response returned
    Failed --> Ready: caller handles the exception
    Ready --> [*]: instance discarded with the conversation
```

After construction the instance is effectively immutable in configuration: model, kwargs, capability flags, and the bound completion function are all fixed. This is exactly why [`LLMRegistry.get_llm`](llm_layer_registry.md) refuses to hand back an existing `service_id` under a different `LLMConfig` — it would have to rebuild everything, so it makes you use a new service ID instead.

---

## 10. Extending it

If you are adding a new model or provider, work through this order:

1. **Is it a capability?** (function calling, reasoning effort, prompt cache, stop words) → add a pattern in [`model_features`](llm_layer_clients_model_features.md). Nothing in `llm.py` changes.
2. **Is it a parameter rename or an incompatible combination?** → add a narrow `if` in `__init__`, scoped as tightly as possible. The existing blocks all name a specific model family on purpose, to avoid changing behavior for siblings.
3. **Is it a serialization shape?** → set `force_string_serializer` in `format_messages_for_llm()`.
4. **Is it a new transient error worth retrying?** → add it to `LLM_RETRY_EXCEPTIONS`.
5. **Does it need async or streaming?** → the subclasses in [llm_layer_clients_async_streaming](llm_layer_clients_async_streaming.md) rebuild their own `partial`, so provider quirks added only to `__init__`'s kwargs may need mirroring there.

That last point is the sharpest edge in the module. `AsyncLLM` builds its own completion partial with a much shorter parameter list (`max_tokens`, `temperature`, `top_p`, and so on) and re-derives `reasoning_effort` itself. The careful quirk normalization in `LLM.__init__` applies to the **synchronous path only**.

---

## Related modules

| Module | Relationship |
| --- | --- |
| [llm_layer_clients_mixins](llm_layer_clients_mixins.md) | `RetryMixin` and `DebugMixin` — the retry and logging behavior mixed into `LLM` |
| [llm_layer_clients_model_features](llm_layer_clients_model_features.md) | `get_features` — the capability table `LLM` consults |
| [llm_layer_clients_async_streaming](llm_layer_clients_async_streaming.md) | `AsyncLLM` and `StreamingLLM` subclasses |
| [llm_layer_registry](llm_layer_registry.md) | Creates, caches, and shares `LLM` instances by `service_id` |
| [llm_layer_routing](llm_layer_routing.md) | `RouterLLM` / `MultimodalRouter` — picks among several `LLM` instances |
| [llm_layer_metrics](llm_layer_metrics.md) | `Metrics` — where cost, tokens, and latency land |
| [core_configuration](core_configuration.md) | `LLMConfig` and the wider config system |
| [core_schema_and_runtime_support](core_schema_and_runtime_support.md) | `Message`, `TextContent`, `ImageContent` |
| [logging](logging.md) | `llm_prompt_logger` / `llm_response_logger` sinks used by `DebugMixin` |
| [agent_controller_core](agent_controller_core.md) | Main consumer of the completion loop |
| [memory_and_condensers](memory_and_condensers.md) | Uses `get_token_count()` and `completion()` for summarization |
| [server_sessions](server_sessions.md) | `ConversationStats` aggregates per-service metrics |
