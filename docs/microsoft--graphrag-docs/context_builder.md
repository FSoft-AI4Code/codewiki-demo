# Context Builder Module Documentation

## Overview

The **context_builder** module is a core component of the GraphRAG query system responsible for preparing and organizing contextual information for different search modes. It provides the foundation for building relevant context that enables effective question answering over knowledge graphs.

The module implements a strategy pattern with specialized context builders for different search approaches: local search, global search, basic search, and DRIFT search. Each builder is designed to extract and format the most relevant information based on the specific search methodology.

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Context Builder Module"
        CB[ContextBuilderResult]
        GCB[GlobalContextBuilder<br/><i>Abstract Base</i>]
        LCB[LocalContextBuilder<br/><i>Abstract Base</i>]
        BCB[BasicContextBuilder<br/><i>Abstract Base</i>]
        DCB[DRIFTContextBuilder<br/><i>Abstract Base</i>]
        CH[ConversationHistory]
        CT[ConversationTurn]
        QAT[QATurn]
    end
    
    subgraph "Search System"
        BS[BaseSearch]
        LS[LocalSearch]
        GS[GlobalSearch]
        BS2[BasicSearch]
        DS[DRIFTSearch]
    end
    
    subgraph "Data Models"
        CM[Community Models]
        EM[Entity Models]
        RM[Relationship Models]
        DM[Document Models]
    end
    
    CB -->|used by| GCB
    CB -->|used by| LCB
    CB -->|used by| BCB
    
    GCB -->|implemented by| GS
    LCB -->|implemented by| LS
    BCB -->|implemented by| BS2
    DCB -->|implemented by| DS
    
    CH -->|used by| GCB
    CH -->|used by| LCB
    CH -->|used by| BCB
    
    CT -->|composes| CH
    QAT -->|derived from| CH
    
    LS -->|extends| BS
    GS -->|extends| BS
    BS2 -->|extends| BS
    DS -->|extends| BS
    
    GCB -->|accesses| CM
    LCB -->|accesses| EM
    LCB -->|accesses| RM
    BCB -->|accesses| DM
```

### Component Relationships

```mermaid
graph LR
    subgraph "Abstract Base Classes"
        GCB
        LCB
        BCB
        DCB
    end
    
    subgraph "Concrete Implementations"
        GCImpl[GlobalContextImpl]
        LCImpl[LocalContextImpl]
        BCImpl[BasicContextImpl]
        DCImpl[DRIFTContextImpl]
    end
    
    subgraph "Search Orchestration"
        GS
        LS
        BS
        DS
    end
    
    GCB -->|specializes| GCImpl
    LCB -->|specializes| LCImpl
    BCB -->|specializes| BCImpl
    DCB -->|specializes| DCImpl
    
    GCImpl -->|powers| GS
    LCImpl -->|powers| LS
    BCImpl -->|powers| BS
    DCImpl -->|powers| DS
```

## Core Components

### ContextBuilderResult

The `ContextBuilderResult` dataclass serves as the standardized output format for all context builders. It encapsulates:

- **context_chunks**: Formatted text chunks ready for LLM consumption
- **context_records**: Structured data records organized by type (entities, relationships, communities, etc.)
- **llm_calls**: Number of LLM calls made during context building
- **prompt_tokens**: Total tokens used in prompts
- **output_tokens**: Total tokens in outputs

### Abstract Base Classes

#### GlobalContextBuilder

The `GlobalContextBuilder` provides the interface for building context in global search mode. Global search operates on community-level summaries and is designed for high-level, holistic questions about the dataset.

**Key Characteristics:**
- Asynchronous operation (`async def build_context`)
- Operates on community reports and summaries
- Handles conversation history integration
- Optimized for broad, dataset-wide queries

#### LocalContextBuilder

The `LocalContextBuilder` defines the interface for local search context building. Local search focuses on specific entities and their immediate relationships, providing detailed, localized information.

**Key Characteristics:**
- Synchronous operation (`def build_context`)
- Entity-centric context building
- Relationship traversal and inclusion
- Optimized for specific, detailed queries

#### BasicContextBuilder

The `BasicContextBuilder` provides a simplified context building approach for basic search operations, typically working directly with document content.

**Key Characteristics:**
- Synchronous operation
- Document-based context
- Minimal processing overhead
- Suitable for straightforward queries

#### DRIFTContextBuilder

The `DRIFTContextBuilder` supports the DRIFT (Dynamic Reasoning over Information Flow and Topology) search methodology, which enables adaptive exploration of the knowledge graph.

**Key Characteristics:**
- Asynchronous operation
- Dynamic context adaptation
- Specialized for exploratory queries
- Returns DataFrame and metrics tuple

### ConversationHistory

The `ConversationHistory` class manages multi-turn conversation state and provides context formatting capabilities:

```mermaid
sequenceDiagram
    participant User
    participant CH as ConversationHistory
    participant CB as ContextBuilder
    participant Search as SearchEngine
    
    User->>CH: Add user query
    CH->>CH: Store ConversationTurn
    User->>Search: Submit query
    Search->>CB: Request context
    CB->>CH: Get conversation history
    CH->>CH: Convert to QA turns
    CH->>CH: Apply token limits
    CH->>CB: Return formatted context
    CB->>Search: Provide context chunks
    Search->>User: Return search results
    User->>CH: Add assistant response
```

**Key Features:**
- **Turn Management**: Stores conversation turns with roles (system, user, assistant)
- **QA Conversion**: Converts linear conversation to question-answer pairs
- **Token Management**: Applies token limits and recency bias
- **Context Formatting**: Prepares conversation history for system prompts

## Data Flow

### Context Building Process

```mermaid
flowchart TD
    Start([Query Received])
    --> CheckHistory{Conversation History?}
    
    CheckHistory -->|Yes| ProcessHistory[Process Conversation History]
    CheckHistory -->|No| SkipHistory[Skip History Processing]
    
    ProcessHistory --> DetermineSearch[Determine Search Type]
    SkipHistory --> DetermineSearch
    
    DetermineSearch -->|Global| GlobalPath[Global Context Building]
    DetermineSearch -->|Local| LocalPath[Local Context Building]
    DetermineSearch -->|Basic| BasicPath[Basic Context Building]
    DetermineSearch -->|DRIFT| DRIFTPath[DRIFT Context Building]
    
    GlobalPath --> FetchCommunities[Fetch Community Reports]
    FetchCommunities --> RankCommunities[Rank by Relevance]
    RankCommunities --> FormatGlobal[Format Global Context]
    
    LocalPath --> IdentifyEntities[Identify Relevant Entities]
    IdentifyEntities --> FetchRelationships[Fetch Relationships]
    FetchRelationships --> FetchTextUnits[Fetch Text Units]
    FetchTextUnits --> FormatLocal[Format Local Context]
    
    BasicPath --> FetchDocuments[Fetch Documents]
    FetchDocuments --> RankDocuments[Rank by Relevance]
    RankDocuments --> FormatBasic[Format Basic Context]
    
    DRIFTPath --> DynamicExplore[Dynamic Graph Exploration]
    DynamicExplore --> AdaptContext[Adapt Context]
    AdaptContext --> FormatDRIFT[Format DRIFT Context]
    
    FormatGlobal --> ApplyLimits[Apply Token Limits]
    FormatLocal --> ApplyLimits
    FormatBasic --> ApplyLimits
    FormatDRIFT --> ApplyLimits
    
    ApplyLimits --> ReturnResult[Return ContextBuilderResult]
    ReturnResult --> End([Context Ready])
```

### Integration with Search System

```mermaid
graph TB
    subgraph "Search Execution Flow"
        Q[User Query]
        SB[Search Begin]
        CB[Context Building]
        PR[Prompt Rendering]
        LLM[LLM Call]
        SR[Search Result]
    end
    
    subgraph "Context Builder Role"
        CH[Conversation History]
        CR[Context Records]
        CC[Context Chunks]
        CT[Token Counting]
    end
    
    Q --> SB
    SB --> CB
    CB --> CH
    CB --> CR
    CB --> CC
    CB --> CT
    
    CH --> PR
    CR --> PR
    CC --> PR
    CT --> PR
    
    PR --> LLM
    LLM --> SR
```

## Dependencies

### Internal Dependencies

The context_builder module relies on several core GraphRAG modules:

- **[data_models](data_models.md)**: Provides entity, relationship, community, and document models
- **[language_models](language_models.md)**: Supplies token encoding and text processing utilities
- **[query_system](query_system.md)**: Integrates with search orchestration

### External Dependencies

- **pandas**: Data manipulation and formatting
- **tiktoken**: Token counting and management
- **dataclasses**: Structured data representation

## Usage Patterns

### Local Search Context Building

Local search context builders typically:
1. Identify entities mentioned in the query
2. Extract related entities through relationship traversal
3. Include relevant text units and community information
4. Apply relevance scoring and ranking
5. Format results within token limits

### Global Search Context Building

Global search context builders typically:
1. Analyze query for high-level themes
2. Select relevant community reports
3. Rank communities by importance and relevance
4. Format community summaries for LLM consumption
5. Handle large context through chunking

### Conversation History Integration

All context builders support conversation history integration:
- Maintain conversation continuity
- Apply recency bias for relevance
- Respect token limits
- Format as structured data for LLM context

## Performance Considerations

### Token Management
- All builders implement token counting and limits
- Context is truncated when exceeding limits
- Recency bias ensures recent conversation turns are prioritized

### Asynchronous Operations
- Global and DRIFT builders support async operations
- Enables parallel context building for large datasets
- Improves response times for complex queries

### Memory Efficiency
- Context records are stored as pandas DataFrames
- Lazy loading of related entities and relationships
- Efficient data structures for large-scale operations

## Extension Points

### Custom Context Builders

New context builders can be created by extending the abstract base classes:

```python
class CustomContextBuilder(GlobalContextBuilder):
    async def build_context(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
        **kwargs,
    ) -> ContextBuilderResult:
        # Custom implementation
        pass
```

### Context Post-Processing

The `ContextBuilderResult` structure allows for:
- Custom context chunk formatting
- Additional metadata inclusion
- Performance metrics tracking
- Integration with monitoring systems

## Error Handling

The module implements robust error handling:
- Graceful degradation when entities/relationships are missing
- Token limit enforcement without crashes
- Empty context handling
- Conversation history validation

## Future Enhancements

Potential areas for enhancement include:
- Multi-language conversation history support
- Advanced relevance scoring algorithms
- Dynamic context adaptation based on query complexity
- Integration with external knowledge sources
- Enhanced conversation memory management