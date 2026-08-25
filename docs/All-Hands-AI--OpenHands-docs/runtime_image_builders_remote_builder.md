# Runtime Image Builders — Remote Builder

## Introduction

The **remote builder** is the piece of OpenHands that builds sandbox container images *somewhere else*. Instead of talking to a local Docker daemon, it packs the build folder into a tarball, POSTs it to a hosted **Runtime API**, and then waits for that service to finish the build.

It exists for one reason: when OpenHands runs against a hosted runtime (see [runtime_implementations_orchestrated_remote_runtime.md](runtime_implementations_orchestrated_remote_runtime.md)), the machine running the agent usually has **no Docker daemon at all**. The remote builder gives that machine the same two capabilities a local Docker build gives — "build this folder into an image" and "does this image already exist?" — over plain HTTP.

The module has three parts:

| Component | File | Role |
|---|---|---|
| `RemoteRuntimeBuilder` | `openhands/runtime/builder/remote.py` | The remote build engine. Packs context, calls the Runtime API, polls until done. |
| `RuntimeBuilder` | `openhands/runtime/builder/base.py` | The abstract contract shared with the local Docker builder. |
| `send_request` | `openhands/runtime/utils/request.py` | Retrying HTTP helper used for every call to the Runtime API. |

---

## Where this module sits

The build *pipeline* (hashing, Dockerfile generation, tag selection) is completely builder-agnostic — it is documented in [runtime_image_builders_build_pipeline.md](runtime_image_builders_build_pipeline.md). The pipeline only knows the `RuntimeBuilder` interface, so swapping "build locally with Docker" for "build remotely over HTTP" is a one-line change of which object is handed in.

```mermaid
graph TD
    subgraph Callers
        RR[RemoteRuntime<br/>impl/remote/remote_runtime.py]
        KR[KubernetesRuntime / other hosted runtimes]
    end

    subgraph Pipeline["Build pipeline (builder-agnostic)"]
        BRI[build_runtime_image]
        BRIF[build_runtime_image_in_folder]
        BSI[_build_sandbox_image]
    end

    subgraph Contract
        RB[RuntimeBuilder<br/>abstract base]
    end

    subgraph Impls["Builder implementations"]
        RRB[RemoteRuntimeBuilder<br/>THIS MODULE]
        DRB[DockerRuntimeBuilder]
    end

    subgraph Transport
        SR[send_request<br/>tenacity retry]
        HS[HttpSession<br/>shared httpx client]
    end

    API[(Remote Runtime API<br/>/build /build_status /image_exists)]

    RR --> BRI
    KR --> BRI
    RR -- constructs --> RRB
    BRI --> BRIF --> BSI
    BRIF -. image_exists .-> RB
    BSI -. build .-> RB
    RB -.implemented by.-> RRB
    RB -.implemented by.-> DRB
    RRB --> SR --> HS --> API

    style RRB fill:#cfe8ff,stroke:#2b6cb0,stroke-width:2px
```

Related docs:
- [runtime_image_builders.md](runtime_image_builders.md) — the parent module overview.
- [runtime_image_builders_docker_builder.md](runtime_image_builders_docker_builder.md) — the local Docker/BuildKit sibling implementation.
- [runtime_image_builders_docker_builder_builder_interface.md](runtime_image_builders_docker_builder_builder_interface.md) — deeper notes on the `RuntimeBuilder` contract.
- [runtime_implementations_orchestrated_remote_runtime.md](runtime_implementations_orchestrated_remote_runtime.md) — the runtime that owns and drives this builder.

---

## The contract: `RuntimeBuilder`

`RuntimeBuilder` is a tiny abstract class with exactly two methods. Everything else in the build system is written against it.

```mermaid
classDiagram
    class RuntimeBuilder {
        <<abstract>>
        +build(path, tags, platform, extra_build_args) str
        +image_exists(image_name, pull_from_repo) bool
    }

    class RemoteRuntimeBuilder {
        +api_url: str
        +api_key: str
        +session: HttpSession
        +build(path, tags, platform, extra_build_args) str
        +image_exists(image_name, pull_from_repo) bool
    }

    class DockerRuntimeBuilder {
        +docker_client
        +rolling_logger
        +build(...) str
        +image_exists(...) bool
    }

    RuntimeBuilder <|-- RemoteRuntimeBuilder
    RuntimeBuilder <|-- DockerRuntimeBuilder
```

**`build(path, tags, platform=None, extra_build_args=None) -> str`**
Build the folder at `path` and tag it. Returns the final `name:tag` that should actually be used to run the container — a builder is allowed to change the tag (for example by adding a registry prefix), so callers must use the returned string, not the input tags. Raises `AgentRuntimeBuildError` on failure.

**`image_exists(image_name, pull_from_repo=True) -> bool`**
Answer whether that image is available. `pull_from_repo` tells a *local* builder whether it may pull from a registry to answer. For the remote builder the flag is meaningless (the registry is the only source of truth), so it is accepted and ignored.

---

## `RemoteRuntimeBuilder`

### Construction

```python
RemoteRuntimeBuilder(api_url, api_key, session=None)
```

- `api_url` — base URL of the Runtime API (`config.sandbox.remote_runtime_api_url`).
- `api_key` — the sandbox API key (`config.sandbox.api_key`).
- `session` — an optional `HttpSession`. `RemoteRuntime` passes **its own** session so the builder and the runtime share one connection pool and one set of headers.

The constructor stamps `X-API-Key: <api_key>` onto the session headers, so every later call is authenticated without repeating the key.

`HttpSession` (from `openhands/utils/http_session.py`) is a thin wrapper over a shared `httpx` client that merges these default headers into each request and refuses to be silently reused after close — this avoids the file-descriptor leaks that plain reusable sessions cause when combined with tenacity retries.

### `build()` — packaging and remote execution

The method does four things in order:

1. **Tar the context.** The whole build folder is streamed into an in-memory gzip tarball (`tarfile`, `arcname='.'`). Nothing is written to disk.
2. **Base64-encode it.** The tarball bytes are base64-encoded into a UTF-8 string, which becomes the `context` form field.
3. **POST `/build`.** Multipart form with `context`, `target_image` (= `tags[0]`), and one repeated `tags` field for every remaining tag. The response carries a `build_id` — the call returns immediately, the build runs asynchronously on the server.
4. **Poll `/build_status`.** Every 30 seconds, ask for the status of `build_id` until it reaches a terminal state.

```mermaid
sequenceDiagram
    participant P as _build_sandbox_image
    participant B as RemoteRuntimeBuilder
    participant S as send_request
    participant API as Runtime API

    P->>B: build(path, tags, platform)
    B->>B: tarfile.open(w:gz) → in-memory tar.gz
    B->>B: base64 encode
    B->>S: POST /build (context, target_image, tags[])
    S->>API: multipart upload (timeout 30s)
    API-->>S: {build_id}
    S-->>B: response

    loop every 30s until terminal / timeout / shutdown
        B->>S: GET /build_status?build_id=...
        S->>API: request
        API-->>S: {status, image?, error?}
        alt status == SUCCESS
            B-->>P: return status_data["image"]
        else status in FAILURE / INTERNAL_ERROR / TIMEOUT / CANCELLED / EXPIRED
            B-->>P: raise AgentRuntimeBuildError(error)
        else still running
            B->>B: sleep_if_should_continue(30)
        end
    end
```

### Build status state machine

```mermaid
stateDiagram-v2
    [*] --> Submitting
    Submitting --> RateLimited: HTTP 429
    RateLimited --> Submitting: sleep 30s, retry build()
    Submitting --> Polling: build_id received

    Polling --> Polling: non-terminal status → sleep 30s
    Polling --> Success: status == SUCCESS
    Polling --> Failed: FAILURE / INTERNAL_ERROR /<br/>TIMEOUT / CANCELLED / EXPIRED
    Polling --> TimedOut: elapsed > 30 min
    Polling --> Interrupted: should_continue() == False

    Success --> [*]: return image name
    Failed --> [*]: AgentRuntimeBuildError
    TimedOut --> [*]: AgentRuntimeBuildError
    Interrupted --> [*]: AgentRuntimeBuildError("Build interrupted")
```

Three ways the loop can end badly, all surfaced as `AgentRuntimeBuildError` (a subclass of `AgentRuntimeError`):

- **Server-reported failure** — the status is one of the five terminal error states; the server's `error` field is used as the message, falling back to a generated one that includes the `build_id` for support lookups.
- **Client-side timeout** — more than 30 minutes of wall clock elapsed since submission.
- **Shutdown** — `should_continue()` from the shutdown listener returned `False` because the process received a termination signal. Both the loop condition and the sleep (`sleep_if_should_continue`) check this, so a Ctrl-C is honored within about a second instead of hanging for the remaining sleep interval.

A non-200 on `/build_status` itself is also converted into `AgentRuntimeBuildError` with the raw response text.

### `image_exists()` — the cache check

```mermaid
sequenceDiagram
    participant P as build_runtime_image_in_folder
    participant B as RemoteRuntimeBuilder
    participant API as Runtime API

    P->>B: image_exists("repo:hash", pull_from_repo=False)
    B->>API: GET /image_exists?image=repo:hash
    alt status != 200
        B-->>P: raise AgentRuntimeBuildError
    else exists
        API-->>B: {exists: true, image: {upload_time, image_size_bytes}}
        B-->>P: True (logs age + size in MB)
    else missing
        API-->>B: {exists: false}
        B-->>P: False
    end
```

This is the hot path in practice. The pipeline calls `image_exists` up to three times per launch (exact source hash → lock-file hash → versioned tag) to decide whether to skip the build entirely or build from a cheaper base layer. Most agent sessions therefore never reach `build()` at all — they hit the first check and reuse an existing image.

---

## Transport layer: `send_request`

Every HTTP call in this module goes through `send_request`, so the retry and error semantics are uniform.

```mermaid
flowchart TD
    A[send_request session, method, url] --> B[session.request timeout default 60s]
    B --> C{raise_for_status}
    C -- ok --> D[return response]
    C -- HTTPError --> E[try parse JSON body for 'detail']
    E --> F[close response]
    F --> G[raise RequestHTTPError with detail]
    G --> H{status == 429?}
    H -- yes --> I[tenacity: wait exponential 4s..60s]
    I --> J{attempt < 3<br/>and not shutting down?}
    J -- yes --> B
    J -- no --> K[propagate]
    H -- no --> K
```

Key points:

- **`RequestHTTPError`** subclasses `httpx.HTTPStatusError` and appends the server's `detail` field to the message, so API errors are readable in logs instead of being bare status codes.
- **Retries only on 429.** `is_retryable_error` matches nothing else — 4xx/5xx failures fail fast rather than hammering the API.
- **Backoff** is exponential between 4 and 60 seconds, capped at 3 attempts.
- **Shutdown-aware.** The stop condition is `stop_after_attempt(3) | stop_if_should_exit()`, so a shutdown signal cancels pending retries immediately. `stop_if_should_exit` is shared with the rest of the runtime layer (see [runtime_utils.md](runtime_utils.md)).
- **Responses are closed** on the error path, which is what keeps connections from leaking under repeated failures.

The same helper is used by `RemoteRuntime` for its `/start`, `/pause`, `/stop` and session calls — builder and runtime share one transport policy.

---

## End-to-end: how a remote build is triggered

```mermaid
flowchart TD
    A[RemoteRuntime.connect] --> B[_start_or_attach_to_runtime]
    B --> C{existing session runtime?}
    C -- yes --> Z[attach and wait until alive]
    C -- no --> D{runtime_container_image configured?}
    D -- yes --> Y[use it directly, skip build]
    D -- no --> E[_build_runtime]

    E --> F[GET /registry_prefix<br/>set OH_RUNTIME_RUNTIME_IMAGE_REPO]
    F --> G[build_runtime_image base_image, self.runtime_builder]
    G --> H[hash lock files + source files<br/>compute source / lock / versioned tags]
    H --> I{image_exists hash tag?}
    I -- yes --> R[reuse image, no build]
    I -- no --> J[choose base: LOCK / VERSIONED / SCRATCH<br/>via image_exists probes]
    J --> K[prep_build_folder: Dockerfile + sources]
    K --> L[RemoteRuntimeBuilder.build]
    L --> M[tar + base64 + POST /build + poll]
    M --> N[image name returned]
    N --> O[GET /image_exists to confirm]
    O --> P[_start_runtime: POST /start with image]
    R --> O
    Y --> P
    P --> Z

    style L fill:#cfe8ff,stroke:#2b6cb0,stroke-width:2px
    style M fill:#cfe8ff,stroke:#2b6cb0,stroke-width:2px
```

Two details worth noting about this flow:

- Before building, `RemoteRuntime` asks the API for a `registry_prefix` and exports it as `OH_RUNTIME_RUNTIME_IMAGE_REPO`. That makes the pipeline generate tags pointing at the **service's own registry**, so the built image is immediately pullable by the sandbox scheduler.
- After the builder returns, the runtime independently re-checks `/image_exists`. This is a belt-and-braces guard against a build that reported success but did not land in the registry.

---

## Local vs. remote builder — the practical differences

| Aspect | `DockerRuntimeBuilder` | `RemoteRuntimeBuilder` |
|---|---|---|
| Where the build runs | Local Docker/Podman daemon via `docker buildx` | Hosted Runtime API service |
| Context transfer | Path handed to buildx | In-memory `tar.gz`, base64-encoded, uploaded |
| Progress feedback | Live streamed build log via `RollingLogger` | Coarse status string every 30s |
| Multiple tags | First tag built, second tag applied locally after build | All tags sent in the request; server tags them |
| `platform` | Passed as `--platform` | Accepted but **not forwarded** — the service picks the platform |
| `extra_build_args` | Appended to the buildx command | Accepted but **not forwarded** |
| `pull_from_repo` | Meaningful — controls a registry pull attempt | Ignored — the registry is the only source |
| Failure signal | `subprocess.CalledProcessError` / `AgentRuntimeBuildError` | `AgentRuntimeBuildError` |
| Prerequisites | Docker ≥ 18.09 (or Podman ≥ 4.9) + buildx | Only network access + API key |

---

## Behavior notes and gotchas

These are real characteristics of the current code that maintainers should know:

- **Rate-limit handling is doubled up.** `send_request` already retries 429 three times with backoff. On top of that, `build()` catches `httpx.HTTPError`, and if the status is 429 sleeps 30s and calls itself recursively. In the worst case the same build can be re-attempted many times.
- **The recursive retry drops arguments.** The retry call is `self.build(path, tags, platform)` — `extra_build_args` is not passed through. Harmless today because the remote path ignores that argument anyway, but it is a trap if forwarding is ever implemented.
- **The 429 branch assumes `e.response` exists.** A transport-level `httpx.HTTPError` (connection reset, DNS failure) has no `.response`, so the handler itself would raise `AttributeError` instead of a clean error.
- **Timeout comment vs. code.** `timeout = 30 * 60` with the comment `# 20 minutes in seconds`. The code is 30 minutes; the comment is stale.
- **Upload timeout is 30 seconds.** That covers the request to *submit* the build, not the build itself. A very large build context on a slow link can trip it.
- **Base64 inflates the payload ~33%** and the whole tarball is held in memory twice (raw + encoded). Build folders are small (Dockerfile plus source), so this is fine in practice, but it is not a design that scales to huge contexts.
- **Polling every 30 seconds** means the reported build time can overshoot the real one by up to half a minute, and short builds still cost at least one poll interval.

---

## Extending the module

To add a new builder backend (a different build service, a CI-based builder), implement `RuntimeBuilder`'s two methods and hand the instance to `build_runtime_image`. Nothing else changes — the hashing, Dockerfile generation and tag strategy in [runtime_image_builders_build_pipeline.md](runtime_image_builders_build_pipeline.md) are reused unchanged.

Two contract obligations are easy to miss:

1. `build()` must return the image reference that is actually usable afterwards, not an echo of `tags[0]`.
2. `image_exists()` must be **cheap and honest** — the pipeline calls it several times per session and treats a `True` as permission to skip the build entirely.
