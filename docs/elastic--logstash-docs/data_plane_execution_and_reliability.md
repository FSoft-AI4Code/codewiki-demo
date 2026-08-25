# Data Plane Execution and Reliability

## Purpose

The `data_plane_execution_and_reliability` module runs and supervises Logstash pipelines after configuration compilation. It reconciles desired and actual pipeline state, coordinates pipeline-to-pipeline event delivery, and provides durable handling for normal input buffering and processing failures.

Its main reliability mechanisms are:

- Lifecycle convergence, reporting, and graceful or guarded shutdown.
- In-process communication between pipelines.
- Persistent queues for acknowledged event durability.
- Dead-letter queues for failed-event retention and replay.

## Architecture

```mermaid
flowchart TB
    Config[Compiled pipeline configuration] --> Lifecycle[Pipeline lifecycle and execution]

    Lifecycle --> Runtime[Running pipeline]
    Runtime --> Plugins[Inputs, filters, and outputs]

    Plugins --> P2P[Pipeline-to-pipeline communication]
    P2P --> Runtime

    Runtime --> PQ[Persistent queue]
    Runtime --> DLQ[Dead-letter queue]

    Lifecycle --> Reports[Convergence results, metrics, snapshots]
    Reports --> Shutdown[Shutdown supervision]
```

### Pipeline lifecycle and execution

```mermaid
sequenceDiagram
    participant A as LogStash::Agent
    participant R as StateResolver
    participant G as PipelinesRegistry
    participant X as Pipeline actions
    participant P as Pipeline runtime

    A->>R: Compare desired and current state
    R-->>A: Create, reload, stop, or delete actions
    A->>X: Execute ordered actions
    X->>G: Lock pipeline state
    G->>P: Start, replace, terminate, or remove
    P-->>A: Report lifecycle result
    A->>A: Publish events and convergence status
```

Lifecycle coordination protects per-pipeline state, reports failures without abandoning other actions, and monitors stalled shutdowns through runtime snapshots.

### Durable data paths

```mermaid
flowchart LR
    Event[Pipeline event] --> Normal[Normal processing]
    Normal -->|queue.type: persisted| PQ[Persistent queue]
    Normal -->|processing failure| DLQ[Dead-letter queue]

    PQ --> Pages[Page files and checkpoints]
    Pages --> Recovery[Restart recovery]
    Recovery --> Normal

    DLQ --> Segments[DLQ log segments]
    Segments --> Reader[DLQ reader and replay]
    Reader --> Replay[Reprocess or inspect event]
```

Persistent queues protect normal pipeline delivery across restarts using page files, checkpoints, acknowledgements, checksums, and exclusive queue locks. Dead-letter queues separately preserve events rejected during processing and support ordered reading, seeking, replay, and acknowledgement-driven cleanup.

### Pipeline-to-pipeline communication

```mermaid
flowchart LR
    Source[Source pipeline] --> Output[Pipeline output]
    Output --> Bus[PipelineBusV2]
    Bus --> Address[AddressState]
    Address --> Input[Destination pipeline input]
    Input --> Queue[Destination queue]
    Queue --> Destination[Destination pipeline]

    Bus --> Retry{ensure_delivery}
    Retry -->|Unavailable or failed| Bus
```

The pipeline bus is an in-process transport. It registers logical addresses, clones event batches for destinations, retries failed delivery when `ensure_delivery` is enabled, and coordinates sender/input shutdown.

## Repository structure

```text
data_plane_execution_and_reliability/
├── pipeline_lifecycle_and_execution/
│   ├── pipeline_lifecycle_and_execution_state_convergence/
│   └── pipeline_lifecycle_and_execution_reporting/
├── pipeline_to_pipeline_communication/
├── persistent_queue/
│   ├── persistent_queue_storage_and_recovery/
│   ├── persistent_queue_configuration_and_factory/
│   └── persistent_queue_queue_utilities/
└── dead_letter_queue/
```

The implementation is primarily under:

- `logstash-core` — lifecycle and execution coordination.
- `logstash-core/src/main/java/org/logstash/plugins/pipeline` — pipeline-to-pipeline transport.
- `logstash-core/src/main/java/org/logstash/ackedqueue` — persistent queue implementation.
- `logstash-core/src/main/java/org/logstash/common` — dead-letter queue implementation.

## Core component documentation

- [Pipeline lifecycle and execution](pipeline_lifecycle_and_execution.md)
  - [State convergence and registry](pipeline_lifecycle_and_execution_state_convergence.md)
  - [Execution reporting and shutdown](pipeline_lifecycle_and_execution_reporting.md)
- [Pipeline-to-pipeline communication](pipeline_to_pipeline_communication.md)
- [Persistent queue](persistent_queue.md)
  - [Storage and recovery](persistent_queue_storage_and_recovery.md)
  - [Configuration and factory](persistent_queue_configuration_and_factory.md)
  - [Queue utilities](persistent_queue_queue_utilities.md)
- [Dead-letter queue](dead_letter_queue.md)
  - [Writer and factory](dead_letter_queue_writer_and_factory.md)
  - [Reader and cleanup](dead_letter_queue_reader_and_cleanup.md)
  - [Record I/O](dead_letter_queue_record_io.md)