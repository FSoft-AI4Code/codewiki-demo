# Microsoft GraphRAG Repository Overview

## Purpose

GraphRAG is a modular, end-to-end system that turns unstructured text into a **queryable knowledge graph** and provides **multiple search strategies** (local, global, basic RAG, DRIFT) to retrieve and synthesize information.  
It is designed for scenarios where documents are too large or too numerous for simple vector search, and where users need **multi-hop, community-level, or iterative** answers backed by explicit citations.

## End-to-End Architecture

```mermaid
graph TD
    %% ===== INPUT =====
    Docs[Raw Documents] --> Chunk[Text Chunker]
    
    %% ===== INDEXING PIPELINE =====
    Chunk --> Extract[Graph Extractor<br/>(Entities & Relationships)]
    Extract --> EmbedTxt[Text Embedder]
    Extract --> EmbedGraph[Graph Embedder]
    Extract --> CommDetect[Community Detector]
    CommDetect --> CommSumm[Community Report Generator]
    
    %% ===== STORAGE =====
    EmbedTxt --> VS[Vector Store<br/>(LanceDB / Azure AI / Cosmos)]
    EmbedGraph --> VS
    CommSumm --> VS
    Extract --> Cache[Pipeline Cache]
    CommSumm --> Cache
    
    %% ===== QUERY TIME =====
    Q[User Query] --> QB{Query Router}
    QB --> |Local| LS[Local Search<br/>Entity-centric]
    QB --> |Global| GS[Global Search<br/>Community Map-Reduce]
    QB --> |Basic| BS[Basic RAG<br/>Vector only]
    QB --> |Drift| DS[DRIFT Search<br/>Iterative]
    
    VS --> LS
    VS --> GS
    VS --> BS
    VS --> DS
    
    LS --> LLM[Language Model]
    GS --> LLM
    BS --> LLM
    DS --> LLM
    
    LLM --> A[Answer + Citations]
```

## Core Modules & Quick Links

| Module | Responsibility | Key Classes / Docs |
|--------|----------------|--------------------|
| **data_models** | Typed entities, relationships, communities, reports | [Community](data_models/community_models.md), [Entity](data_models/core_entities.md) |
| **configuration** | Central, validated config for every component | [GraphRagConfig](configuration/configuration.md) |
| **index_operations** | Graph extraction, embedding, community summarization | [GraphExtractor](index_operations/graph_extraction.md), [TextEmbedder](index_operations/text_embedding.md) |
| **storage** | Pluggable backends (file, blob, Cosmos, memory) | [PipelineStorage](storage/storage.md) |
| **caching** | LLM-response & intermediate-result cache | [PipelineCache](caching/caching.md) |
| **language_models** | Unified chat & embedding model interface | [ChatModel](language_models/language_model_protocol.md), [ModelFactory](language_models/language_model_factory.md) |
| **vector_stores** | Vector DB abstraction (LanceDB, Azure AI, Cosmos) | [BaseVectorStore](vector_stores/base.md) |
| **query_system** | Local, Global, Basic, DRIFT search strategies | [LocalSearch](query_system/structured_search.md), [GlobalSearch](query_system/structured_search.md) |
| **pipeline_infrastructure** | Orchestrates indexing workflows | [Pipeline](pipeline_infrastructure/typing.md), [PipelineFactory](pipeline_infrastructure/workflows.md) |
| **callbacks** | Progress, logging, telemetry hooks | [WorkflowCallbacks](callbacks/workflow_management.md) |
| **unified-search-app** | Streamlit demo UI | [KnowledgeModel](unified_search_app/knowledge_loader.md) |

## Quick Start Flow

1. **Index**  
   `PipelineFactory` → `Pipeline` → `index_operations` → store in `VectorStore` + `PipelineStorage`

2. **Query**  
   `SearchType` → `LocalSearch` / `GlobalSearch` / `BasicSearch` / `DRIFTSearch` → `LanguageModel` → `SearchResult`

3. **Observe**  
   `WorkflowCallbacks` → console / custom telemetry

## Extensibility Points

- **New vector DB**: implement `BaseVectorStore` and register with `VectorStoreFactory`  
- **New LLM provider**: implement `ChatModel` or `EmbeddingModel` and register with `ModelFactory`  
- **New search strategy**: subclass `BaseSearch` and add to `SearchType` enum  
- **Custom workflow**: register with `PipelineFactory` under a new `IndexingMethod`

All configuration is centralized in `GraphRagConfig`, enabling full control without code changes.