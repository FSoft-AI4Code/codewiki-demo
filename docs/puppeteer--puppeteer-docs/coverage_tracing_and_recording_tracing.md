# Tracing

`packages/puppeteer-core/src/cdp/Tracing.ts` wraps the CDP tracing audit interface for page performance and timeline diagnostics.

## Responsibilities

`Tracing.start` validates that no trace is active, selects default timeline/V8 categories, optionally adds screenshot capture, separates included and excluded categories, and starts CDP tracing with `ReturnAsStream` transfer mode. The optional `path` is retained for stream output.

`Tracing.stop` listens for `Tracing.tracingComplete`, reads the returned protocol stream, resolves the trace as a `Uint8Array`, and ends recording. Stream failures are propagated through a deferred promise. Only one trace is allowed per browser according to the public contract.

`updateClient` replaces the underlying `CDPSession`, which is important when the owning page or backend reconnects. Session transport details are covered in [protocol transport and session infrastructure](protocol_transport_and_session_infrastructure.md).

```mermaid
flowchart LR
  A[Page.tracing.start] --> B[Build traceConfig]
  B --> C[CDP Tracing.start]
  C --> D[Browser emits trace events]
  D --> E[Page.tracing.stop]
  E --> F[CDP Tracing.end]
  F --> G[Tracing.tracingComplete]
  G --> H[Read protocol stream]
  H --> I[Uint8Array or path output]
```

The resulting JSON trace can be opened in Chrome DevTools or a compatible timeline viewer.
