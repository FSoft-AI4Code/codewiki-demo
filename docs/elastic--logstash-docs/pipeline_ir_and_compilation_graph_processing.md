# Pipeline IR and Compilation Graph Processing

## Introduction

The `pipeline_ir_and_compilation_graph_processing` module supplies the graph representation and graph algorithms underlying Logstash's pipeline intermediate representation. It turns pipeline sections into validated directed acyclic graphs, preserves conditional branches, supports composition of graph fragments, and exposes topology needed by IR assembly and executable dataset compilation.

This module is infrastructure rather than a standalone pipeline stage: [pipeline_ir_and_compilation_ir_assembly.md](pipeline_ir_and_compilation_ir_assembly.md) constructs and combines these graphs, while [pipeline_ir_and_compilation_dataset_runtime.md](pipeline_ir_and_compilation_dataset_runtime.md) consumes the assembled topology to build runtime datasets.

## Architecture overview

```mermaid
flowchart TB
    PARSER[Pipeline configuration parser] --> ASM[IR assembly]
    ASM --> GM[Graph model]
    GM --> ALG[Graph algorithms]
    ALG --> VALID[Validated DAG and sorted vertices]
    VALID --> ASM
    VALID --> COMP[Dataset/runtime compilation]
    GM --> BRANCH[Boolean conditional edges]
    BRANCH --> COMP
    COMP --> EXEC[Pipeline execution]
```

The graph model owns membership, connectivity, copying, chaining, validation, and identity. The algorithm layer calculates ranks, traverses lineage, produces topological order, and compares graph revisions.

## Sub-modules

| Sub-module | Documentation | Scope |
|---|---|---|
| Graph model | [pipeline_ir_and_compilation_graph_processing_graph_model.md](pipeline_ir_and_compilation_graph_processing_graph_model.md) | `Graph`, vertex/edge ownership, graph composition, Boolean edges, validation, hashing |
| Graph algorithms | [pipeline_ir_and_compilation_graph_processing_algorithms.md](pipeline_ir_and_compilation_graph_processing_algorithms.md) | Breadth-first ranking, depth-first traversal, topological sorting, cycle detection, graph diffs |

## Component interaction

```mermaid
graph LR
    CC[ConfigCompiler] -->|creates/chains| G[Graph]
    G --> V[Vertices]
    G --> E[Edges]
    E --> BE[BooleanEdge]
    G --> BFS[BreadthFirst]
    G --> DFS[DepthFirst via Vertex]
    G --> TS[TopologicalSort]
    G --> GD[GraphDiff]
    G --> PIR[PipelineIR]
    PIR --> DS[Dataset compiler/runtime]
```

## End-to-end processing

```mermaid
sequenceDiagram
    participant A as IR assembly
    participant G as Graph
    participant Algo as Graph algorithms
    participant C as Dataset compilation
    A->>G: create section graphs
    A->>G: combine and chain fragments
    G->>Algo: refresh ranks and topological order
    Algo-->>G: ranks / sorted vertices or cycle error
    G->>G: validate IDs and leaf structure
    G-->>A: assembled PipelineIR graph
    A-->>C: pipeline topology and plugin vertices
    C->>G: consume roots, leaves, ranks, sorted vertices
```

## Design characteristics

- Graph fragments are copied when combined, preventing one vertex or edge from belonging to multiple graphs.
- Conditional paths are explicit Boolean edges, so true and false branches remain distinguishable during comparison and compilation.
- Refresh is the consistency boundary: it recalculates derived indexes and ordering after mutations.
- Cycle detection protects downstream compilation, which assumes DAG execution paths.
- Source-aware equivalence and hashing support reproducibility, diagnostics, and change detection.

## Maintenance guidance

Changes to vertex edge acceptance, graph chaining, or topological ordering can alter pipeline execution semantics. Changes to source-component equality or unique hashing can affect graph comparison, caching, and diagnostics. When modifying these areas, verify both conditional and parallel/branched pipeline configurations, plus graph copy/combine behavior.
