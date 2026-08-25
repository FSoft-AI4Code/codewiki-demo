# Pipeline Language and Compilation

## Purpose

The `pipeline_language_and_compilation` module transforms Logstash Configuration Language (LSCL) into executable pipeline structures.

It:

- Parses and validates LSCL configuration.
- Converts syntax into intermediate representation (IR) expressions and statements.
- Assembles input, filter, and output graphs into a validated `PipelineIR`.
- Compiles graph topology into executable datasets.
- Bridges compiled datasets to Ruby plugins through JRuby.
- Preserves source metadata for diagnostics, graph identity, and configuration errors.

## Architecture

```mermaid
flowchart LR
    Sources[Configuration sources] --> Parser[LSCL configuration parser]
    Parser --> Statements[IR expressions and statements]
    Statements --> Assembly[IR assembly and ConfigCompiler]
    Assembly --> Graph[Pipeline IR graph]
    Graph --> PipelineIR[Validated PipelineIR]
    PipelineIR --> Datasets[Compiled dataset graph]
    Datasets --> Plugins[Ruby plugins via JRuby]
    Datasets --> Runtime[Pipeline execution]
```

The parser is responsible for textual syntax and semantic conversion, while the IR and graph layers construct and validate execution topology.

```mermaid
flowchart TD
    Config[LSCL configuration] --> AST[LSCL AST]
    AST --> Sections[Input / filter / output expressions]
    Sections --> Graphs[Graph fragments]
    Graphs --> Compose[Combine and chain graphs]
    Compose --> Validate[DAG validation and ordering]
    Validate --> Compile[Dataset compilation]
    Compile --> Execute[Event processing]
```

Conditional branches are represented as boolean graph edges and later become dataset splits during execution.

```mermaid
flowchart LR
    Condition[Pipeline condition] --> Branch[True / false BooleanEdge paths]
    Branch --> Graph[IR graph topology]
    Graph --> Split[Conditional dataset split]
    Split --> True[Matching events]
    Split --> False[Complement events]
    True --> Downstream[Downstream filters or outputs]
    False --> Downstream
```

## Core components

- **Pipeline configuration parser** — Converts LSCL text and source metadata into compiled input, filter, and output expressions.
- **Pipeline IR and compilation** — Assembles statements into `PipelineIR`, compiles graphs into datasets, and coordinates runtime plugin execution.
- **Pipeline IR graph** — Provides vertices, edges, boolean branches, graph composition, traversal, topological sorting, cycle detection, and structural comparison.

## Core documentation

- [Pipeline configuration parser](pipeline_configuration_parser.md)
- [Pipeline IR and compilation](pipeline_ir_and_compilation.md)
- [Pipeline IR graph](pipeline_ir_graph.md)

The subsystem integrates with configuration loading, plugin registration, event/JRuby interop, and pipeline lifecycle execution, which are documented by their respective runtime modules.