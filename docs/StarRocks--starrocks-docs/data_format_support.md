# Data Format Support Module

## Introduction

The data_format_support module is a critical component of StarRocks' data ingestion system that handles the parsing, validation, and configuration of various data formats during load operations. This module provides the foundation for supporting multiple file formats including CSV, JSON, Parquet, ORC, and Avro, ensuring seamless data integration from diverse sources.

The module serves as the bridge between external data sources and StarRocks' internal data processing pipeline, managing format-specific configurations, header parsing, and format detection based on file extensions and user specifications.

## Architecture Overview

```mermaid
graph TB
    subgraph "Data Format Support Module"
        CSV[CSV Options Configuration]
        HTTP[HTTP Header Management]
        FORMAT[Format Detection Engine]
        CONFIG[Configuration Management]
    end
    
    subgraph "Load Operations"
        STREAM[Stream Load]
        BROKER[Broker Load]
        ROUTINE[Routine Load]
    end
    
    subgraph "File Formats"
        CSV_FILE[CSV Files]
        JSON_FILE[JSON Files]
        PARQUET_FILE[Parquet Files]
        ORC_FILE[ORC Files]
        AVRO_FILE[Avro Files]
    end
    
    CSV --> STREAM
    CSV --> BROKER
    HTTP --> STREAM
    FORMAT --> CSV_FILE
    FORMAT --> JSON_FILE
    FORMAT --> PARQUET_FILE
    FORMAT --> ORC_FILE
    FORMAT --> AVRO_FILE
    CONFIG --> STREAM
    CONFIG --> BROKER
    CONFIG --> ROUTINE
```

## Core Components

### CSVOptions Configuration Class

The `CSVOptions` class provides essential configuration parameters for CSV file processing:

```mermaid
classDiagram
    class CSVOptions {
        +String columnSeparator
        +String rowDelimiter
    }
    
    class Load {
        +getFormatType(String, String)
        +initColumns(Table, List, Map, ...)
        +checkMergeCondition(String, OlapTable, List, boolean)
    }
    
    CSVOptions --> Load : used by
```

**Key Features:**
- Configurable column separation characters (default: tab character `\t`)
- Configurable row delimiters (default: newline character `\n`)
- Integration with format detection logic
- Support for various CSV dialects and encodings

### StreamLoadHttpHeader Management

The `StreamLoadHttpHeader` class manages HTTP headers for stream load operations:

```mermaid
classDiagram
    class StreamLoadHttpHeader {
        +HTTP_FORMAT: String
        +HTTP_COLUMNS: String
        +HTTP_COLUMN_SEPARATOR: String
        +HTTP_ROW_DELIMITER: String
        +HTTP_JSONPATHS: String
        +HTTP_COMPRESSION: String
        +isEnabledBatchWrite(BaseRequest)
    }
```

**Header Categories:**
- **Format Headers**: Control data format specification
- **CSV Headers**: Manage CSV-specific parameters
- **JSON Headers**: Handle JSON path and structure configuration
- **Batch Write Headers**: Enable and configure batch processing
- **Compression Headers**: Specify compression types

## Format Detection Engine

### Automatic Format Detection

The format detection system automatically identifies file formats based on:

```mermaid
flowchart TD
    A[File Path or Format String] --> B{Format Specified?}
    B -->|Yes| C[Use Specified Format]
    B -->|No| D[Analyze File Extension]
    
    D --> E{Extension Check}
    E -->|.parquet/.parq| F[Parquet Format]
    E -->|.orc| G[ORC Format]
    E -->|.gz| H[CSV with Gzip]
    E -->|.bz2| I[CSV with Bzip2]
    E -->|.lz4| J[CSV with LZ4]
    E -->|.deflate| K[CSV with Deflate]
    E -->|.zst| L[CSV with Zstandard]
    E -->|Other| M[Plain CSV]
    
    C --> N[Return Format Type]
    F --> N
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
```

### Supported File Formats

| Format | Extension | MIME Type | Compression Support |
|--------|-----------|-----------|-------------------|
| CSV | `.csv` | text/csv | Gzip, Bzip2, LZ4, Deflate, Zstandard |
| JSON | `.json` | application/json | Gzip, Bzip2, LZ4, Deflate, Zstandard |
| Parquet | `.parquet`, `.parq` | application/octet-stream | Built-in compression |
| ORC | `.orc` | application/octet-stream | Built-in compression |
| Avro | `.avro` | application/avro | Built-in compression |

## Configuration Management

### Load Configuration Parameters

The module supports extensive configuration options for different load scenarios:

```mermaid
graph LR
    subgraph "Configuration Categories"
        CSV_CONFIG[CSV Configuration]
        JSON_CONFIG[JSON Configuration]
        COMPRESSION[Compression Settings]
        PERFORMANCE[Performance Tuning]
        VALIDATION[Data Validation]
    end
    
    subgraph "CSV Parameters"
        COL_SEP[Column Separator]
        ROW_DELIM[Row Delimiter]
        SKIP_HEADER[Skip Header]
        TRIM_SPACE[Trim Spaces]
        ENCLOSE[Enclose Character]
        ESCAPE[Escape Character]
    end
    
    subgraph "JSON Parameters"
        JSON_PATH[JSON Paths]
        JSON_ROOT[JSON Root]
        STRIP_ARRAY[Strip Outer Array]
    end
    
    CSV_CONFIG --> COL_SEP
    CSV_CONFIG --> ROW_DELIM
    CSV_CONFIG --> SKIP_HEADER
    CSV_CONFIG --> TRIM_SPACE
    CSV_CONFIG --> ENCLOSE
    CSV_CONFIG --> ESCAPE
    
    JSON_CONFIG --> JSON_PATH
    JSON_CONFIG --> JSON_ROOT
    JSON_CONFIG --> STRIP_ARRAY
```

## Integration with Load Operations

### Stream Load Integration

```mermaid
sequenceDiagram
    participant Client
    participant HTTP_Server
    participant StreamLoadHttpHeader
    participant Load_Engine
    participant Storage
    
    Client->>HTTP_Server: POST /api/{db}/{table}/_stream_load
    HTTP_Server->>StreamLoadHttpHeader: Parse Headers
    StreamLoadHttpHeader->>StreamLoadHttpHeader: Validate Configuration
    StreamLoadHttpHeader->>Load_Engine: Format Configuration
    Load_Engine->>Load_Engine: Process Data
    Load_Engine->>Storage: Write Data
    Storage->>HTTP_Server: Response
    HTTP_Server->>Client: Load Result
```

### Broker Load Integration

The data format support module integrates with broker load operations through:
- Format specification in load statements
- Configuration validation during job planning
- Runtime format detection and processing

## Error Handling and Validation

### Configuration Validation

The module implements comprehensive validation for:
- Format compatibility checks
- Header parameter validation
- Compression type verification
- Character encoding validation

### Error Recovery

```mermaid
flowchart TD
    A[Configuration Error] --> B{Error Type}
    B -->|Format Mismatch| C[Return Format Error]
    B -->|Invalid Parameter| D[Return Parameter Error]
    B -->|Compression Error| E[Return Compression Error]
    
    C --> F[Log Error Details]
    D --> F
    E --> F
    
    F --> G[Provide Correction Hints]
    G --> H[Continue Processing]
```

## Performance Optimization

### Batch Processing Support

The module supports batch write operations for improved performance:
- Configurable batch sizes
- Asynchronous commit options
- Parallel processing controls
- Memory management optimization

### Memory Management

```mermaid
graph TB
    subgraph "Memory Optimization"
        BUFFER[Buffer Management]
        STREAM[Streaming Processing]
        COMPRESS[Compression Handling]
        CACHE[Format Caching]
    end
    
    subgraph "Load Performance"
        THROUGHPUT[High Throughput]
        LATENCY[Low Latency]
        SCALABILITY[Horizontal Scaling]
    end
    
    BUFFER --> THROUGHPUT
    STREAM --> LATENCY
    COMPRESS --> THROUGHPUT
    CACHE --> LATENCY
```

## Security Considerations

### Data Validation

- Input sanitization for all format parameters
- File extension validation
- Compression bomb protection
- Memory usage limits

### Access Control

- Header-based authentication integration
- Format-specific permission checks
- Audit logging for configuration changes

## Dependencies

### Internal Dependencies

- **[load_export.md](load_export.md)**: Integrates with load operations for data ingestion
- **[storage_engine.md](storage_engine.md)**: Provides format support for storage operations
- **[query_execution.md](query_execution.md)**: Supports format-specific query processing

### External Dependencies

- Apache Thrift for serialization
- Compression libraries (Gzip, Bzip2, LZ4, Zstandard)
- JSON processing libraries
- Parquet and ORC format libraries

## Usage Examples

### CSV Configuration

```sql
-- Stream load with CSV format
 curl -X POST \
   -H "format: csv" \
   -H "column_separator: ," \
   -H "row_delimiter: \n" \
   -H "skip_header: 1" \
   -T data.csv \
   http://fe-host:8030/api/db/table/_stream_load
```

### JSON Configuration

```sql
-- Stream load with JSON format
curl -X POST \
  -H "format: json" \
  -H "jsonpaths: [\"$.id\", \"$.name\", \"$.value\"]" \
  -H "strip_outer_array: true" \
  -T data.json \
  http://fe-host:8030/api/db/table/_stream_load
```

### Format Detection

```java
// Automatic format detection based on file extension
TFileFormatType formatType = Load.getFormatType(null, "data.parquet");
// Returns: TFileFormatType.FORMAT_PARQUET

TFileFormatType formatType2 = Load.getFormatType(null, "data.csv.gz");
// Returns: TFileFormatType.FORMAT_CSV_GZ
```

## Future Enhancements

### Planned Features

- **Additional Format Support**: XML, Protocol Buffers
- **Enhanced Compression**: Brotli, LZMA support
- **Schema Evolution**: Automatic schema detection and mapping
- **Performance Monitoring**: Format-specific performance metrics
- **Intelligent Caching**: Format-aware caching strategies

### Optimization Roadmap

- Zero-copy data processing for supported formats
- Vectorized format parsing for improved performance
- Adaptive compression selection based on data characteristics
- Machine learning-based format optimization

## Conclusion

The data_format_support module is a foundational component that enables StarRocks to handle diverse data formats efficiently and reliably. Through its comprehensive configuration management, automatic format detection, and seamless integration with load operations, the module provides the flexibility and performance required for modern data integration scenarios. The modular design ensures easy extensibility for future format support while maintaining backward compatibility and performance standards.