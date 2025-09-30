# Caching System Module Documentation

## Introduction

The caching-system module provides a dual-layer caching mechanism for search results, implementing both short-term and long-term storage strategies. This module is designed to optimize search performance by storing frequently accessed data and reducing redundant API calls to external search providers.

The caching system consists of two main components:
- **ShortTermCacheClient**: A Redis-based cache with vector similarity search capabilities for query-based caching
- **LongTermCacheClient**: A MongoDB-based cache for persistent storage of URL-specific details

## Architecture Overview

```mermaid
graph TB
    subgraph "Caching System Module"
        STCC[ShortTermCacheClient<br/>Redis-based]
        LTCC[LongTermCacheClient<br/>MongoDB-based]
        EC[EmbeddingClient]
        SR[SearchResponse]
    end
    
    subgraph "External Systems"
        Redis[(Redis Server)]
        MongoDB[(MongoDB Server)]
        SearchProviders[Search Providers<br/>Google, DuckDuckGo, SearXNG]
    end
    
    STCC -->|Vector Storage| Redis
    STCC -->|Embedding Generation| EC
    LTCC -->|Persistent Storage| MongoDB
    
    SearchProviders -->|Results| SR
    SR -->|Cache| STCC
    SR -->|Cache| LTCC
    
    style STCC fill:#e1f5fe
    style LTCC fill:#e1f5fe
    style Redis fill:#ffecb3
    style MongoDB fill:#ffecb3
```

## Core Components

### ShortTermCacheClient

The `ShortTermCacheClient` implements a sophisticated caching mechanism using Redis as the backend storage. It provides vector similarity search capabilities, allowing the system to find cached results for semantically similar queries.

#### Key Features:
- **Vector Similarity Search**: Uses Redis RediSearch with vector fields to find similar queries
- **Time-based Expiration**: Configurable expiration time for cache entries
- **Semantic Matching**: Employs cosine similarity for vector comparison
- **JSON Storage**: Utilizes Redis JSON for structured data storage

#### Architecture:

```mermaid
graph LR
    subgraph "ShortTermCacheClient Flow"
        Query[User Query] --> Embedding[Embedding Generation]
        Embedding --> VectorSearch[Vector Search in Redis]
        VectorSearch --> SimilarityCheck{Similarity > Threshold?}
        SimilarityCheck -->|Yes| ReturnCached[Return Cached Result]
        SimilarityCheck -->|No| ReturnNull[Return Null]
        
        NewResult[New Search Result] --> GenerateEmbedding[Generate Query Embedding]
        GenerateEmbedding --> StoreRedis[Store in Redis JSON]
        StoreRedis --> SetExpiry[Set Expiration]
    end
    
    style Query fill:#c8e6c9
    style ReturnCached fill:#a5d6a7
    style ReturnNull fill:#ffccbc
```

#### Implementation Details:

```python
# Index Configuration
index_name = "idx:search_vss"
schema = VectorField(
    "$.query_embedding",
    "FLAT",
    {
        "TYPE": "FLOAT32",
        "DIM": embedding_dim,
        "DISTANCE_METRIC": "COSINE",
    },
    as_name="vector"
)
```

The client creates a Redis search index with vector fields that enable K-nearest neighbor (KNN) searches. When a query is received, it:

1. Generates an embedding for the query using the `EmbeddingClient`
2. Performs a KNN search to find the most similar cached query
3. Checks if the similarity score exceeds the configured threshold
4. Returns the cached result if found, or `None` if no suitable match exists

### LongTermCacheClient

The `LongTermCacheClient` provides persistent caching capabilities using MongoDB as the backend storage. It focuses on caching detailed information associated with specific URLs, making it ideal for storing scraped content or detailed page information that doesn't change frequently.

#### Key Features:
- **URL-based Indexing**: Unique index on URL field for fast lookups
- **Persistent Storage**: MongoDB provides durable, long-term storage
- **Upsert Operations**: Efficient update-or-insert operations
- **Detail Caching**: Specifically designed for caching URL-specific details

#### Architecture:

```mermaid
graph LR
    subgraph "LongTermCacheClient Flow"
        URL[URL Request] --> MongoQuery[Query MongoDB]
        MongoQuery --> FoundCheck{Document Found?}
        FoundCheck -->|Yes| ReturnDetails[Return Cached Details]
        FoundCheck -->|No| ReturnNull[Return Null]
        
        NewDetails[New URL Details] --> UpsertOp[Upsert Operation]
        UpsertOp --> MongoStore[Store in MongoDB]
    end
    
    style URL fill:#c8e6c9
    style ReturnDetails fill:#a5d6a7
    style ReturnNull fill:#ffccbc
```

#### Implementation Details:

The client creates a unique index on the URL field to ensure fast lookups and prevent duplicate entries. The caching strategy is particularly effective for:
- Web scraping results
- Page metadata
- URL-specific content that remains relatively static
- Detailed information that complements search results

## Data Flow

### Search Result Caching Process

```mermaid
sequenceDiagram
    participant User
    participant SearchProvider
    participant ShortTermCache
    participant LongTermCache
    participant Redis
    participant MongoDB
    
    User->>SearchProvider: Search Query
    SearchProvider->>ShortTermCache: Check Cache
    ShortTermCache->>Redis: Vector Search
    Redis-->>ShortTermCache: Cached Result / Not Found
    
    alt Cache Miss
        SearchProvider->>SearchProvider: Perform Search
        SearchProvider->>ShortTermCache: Cache Results
        ShortTermCache->>Redis: Store with Embedding
        SearchProvider->>LongTermCache: Cache URL Details
        LongTermCache->>MongoDB: Upsert URL Details
    end
    
    SearchProvider-->>User: Return Results
```

### Cache Retrieval Process

```mermaid
sequenceDiagram
    participant User
    participant CacheSystem
    participant ShortTermCache
    participant LongTermCache
    participant Redis
    participant MongoDB
    
    User->>CacheSystem: Query Request
    CacheSystem->>ShortTermCache: Check Similar Queries
    ShortTermCache->>Redis: Vector Similarity Search
    Redis-->>ShortTermCache: Similar Query Found?
    
    alt Similar Query Found
        ShortTermCache-->>User: Return Cached Results
    else No Similar Query
        CacheSystem->>LongTermCache: Check URL Details
        LongTermCache->>MongoDB: Query by URL
        MongoDB-->>LongTermCache: Return Details
        LongTermCache-->>CacheSystem: Return Details
        CacheSystem-->>User: Combined Results
    end
```

## Dependencies

### Internal Dependencies

The caching-system module depends on several internal components:

```mermaid
graph TB
    subgraph "Caching System Dependencies"
        CS[Caching System]
        EC[EmbeddingClient]
        SR[SearchResponse Schema]
        Logger[Logger]
    end
    
    CS -->|Uses| EC
    CS -->|Validates| SR
    CS -->|Logs| Logger
    
    style CS fill:#e1f5fe
    style EC fill:#fff3e0
    style SR fill:#fff3e0
    style Logger fill:#fff3e0
```

- **[EmbeddingClient](embedding-client.md)**: Used by `ShortTermCacheClient` to generate vector embeddings for queries
- **[SearchResponse Schema](schemas.md)**: Validates and structures cached data
- **[Logger](logs.md)**: Provides logging functionality for cache operations

### External Dependencies

- **Redis Server**: Required for `ShortTermCacheClient` operations
- **MongoDB Server**: Required for `LongTermCacheClient` operations
- **Redis-py**: Python Redis client library
- **PyMongo**: Python MongoDB driver
- **NumPy**: For vector operations

## Integration with Search Providers

The caching system integrates seamlessly with the [search-providers](search-providers.md) module:

```mermaid
graph TB
    subgraph "Search Flow with Caching"
        SP[Search Providers<br/>Google, DuckDuckGo, SearXNG]
        CS[Caching System]
        User[User Request]
    end
    
    User -->|Query| CS
    CS -->|Cache Miss| SP
    CS -->|Cache Hit| User
    SP -->|Results| CS
    CS -->|Cached Results| User
    
    style CS fill:#e1f5fe
    style SP fill:#fff3e0
```

The caching system acts as an intermediary layer between users and search providers, significantly reducing response times for repeated or similar queries while maintaining data freshness through configurable expiration policies.

## Configuration

### ShortTermCacheClient Configuration

- **redis_url**: Connection string for Redis instance
- **expire_time**: Cache expiration time in seconds
- **sim_threshold**: Similarity threshold for vector matching (0.0 to 1.0)
- **embedding_dim**: Dimension of vector embeddings
- **embedding_client**: Instance of EmbeddingClient for vector generation

### LongTermCacheClient Configuration

- **mongo_url**: Connection string for MongoDB instance
- **db_name**: Name of the MongoDB database
- **collection_name**: Name of the collection for cache storage

## Best Practices

1. **Cache Key Strategy**: Use consistent hashing for cache keys to ensure uniform distribution
2. **Similarity Threshold**: Set appropriate similarity thresholds based on your use case (higher for stricter matching)
3. **Expiration Policies**: Configure expiration times based on data volatility and update frequency
4. **Index Management**: Monitor Redis and MongoDB index performance and optimize as needed
5. **Error Handling**: Implement proper error handling for cache misses and connection failures

## Performance Considerations

- **Vector Search Performance**: Redis vector search performance depends on embedding dimensions and dataset size
- **Memory Usage**: Monitor Redis memory usage for vector storage
- **MongoDB Indexing**: Ensure proper indexing for optimal query performance
- **Network Latency**: Consider co-locating cache servers with application servers to minimize latency

## Monitoring and Maintenance

- Monitor cache hit rates to evaluate effectiveness
- Track Redis memory usage and implement eviction policies if necessary
- Monitor MongoDB query performance and optimize indexes
- Set up alerts for cache server connectivity issues
- Regular cleanup of expired entries (handled automatically by Redis TTL)