# Command & Configuration System

## Introduction

The Command & Configuration System module provides the foundational command-line interface and configuration management capabilities for the Trino Verifier service. This module serves as the entry point for the verifier application, handling command-line argument parsing, configuration loading, and application initialization through dependency injection.

The system is built using the Picocli framework for command-line parsing and Google Guice for dependency injection, providing a robust and extensible foundation for the verification workflow.

## Architecture Overview

The Command & Configuration System acts as the orchestration layer for the Trino Verifier, managing the complete lifecycle from command-line invocation to query verification execution. It integrates with multiple subsystems including the [Query Execution & Validation Engine](Trino%20Verifier.md#query-execution--validation-engine), [Query Pair Management](Trino%20Verifier.md#query-pair-management), and various data source modules.

```mermaid
graph TB
    subgraph "Command & Configuration System"
        VC[VerifyCommand]
        VP[VersionProvider]
        DM[DataSourceModule]
        VDP[VerifierDaoProvider]
        BC[Bootstrap Configuration]
    end
    
    subgraph "External Dependencies"
        PC[Picocli Framework]
        GI[Google Guice]
        AB[AirLift Bootstrap]
        JM[JsonModule]
    end
    
    subgraph "Trino Verifier Components"
        TVM[TrinoVerifierModule]
        VC2[VerifierConfig]
        VD[VerifierDao]
        V[Verifier]
    end
    
    subgraph "Query Processing"
        SP[SqlParser]
        QR[QueryRewriter]
        QP[QueryPair]
    end
    
    VC --> PC
    VC --> VP
    VC --> BC
    BC --> AB
    BC --> GI
    BC --> JM
    BC --> TVM
    BC --> DM
    DM --> VDP
    VDP --> VD
    VC --> VC2
    VC --> V
    VC --> SP
    VC --> QR
    VC --> QP
```

## Core Components

### VerifyCommand

The `VerifyCommand` class serves as the main entry point for the Trino Verifier application. It implements the `Runnable` interface and is annotated with Picocli's `@Command` annotation to define the command-line interface structure.

**Key Responsibilities:**
- Command-line argument parsing and validation
- Configuration file loading and processing
- Dependency injection container initialization
- Query filtering and transformation
- JDBC driver management
- Verification execution orchestration

**Command-Line Interface:**
```bash
trina-verifier <configuration-file> [options]
```

**Available Options:**
- `--help, -h`: Display help message and exit
- `--version`: Print version information and exit

### VersionProvider

The `VersionProvider` class implements Picocli's `IVersionProvider` interface to provide version information for the application. It dynamically retrieves the implementation version from the package metadata.

**Features:**
- Automatic version detection from package implementation
- Integration with Picocli's version help system
- Graceful handling of missing version information

## Configuration Management

### Configuration Loading Process

The configuration system follows a systematic approach to load and validate application settings:

```mermaid
sequenceDiagram
    participant User
    participant VerifyCommand
    participant Bootstrap
    participant VerifierConfig
    participant Injector
    
    User->>VerifyCommand: Execute with config file
    VerifyCommand->>VerifyCommand: Set system property "config"
    VerifyCommand->>Bootstrap: Initialize with modules
    Bootstrap->>Injector: Create injector
    Injector->>VerifierConfig: Load configuration
    VerifierConfig->>VerifyCommand: Return config instance
    VerifyCommand->>VerifyCommand: Validate configuration
    VerifyCommand->>Verifier: Execute verification
```

### Configuration Modules

The system uses a modular approach to configuration with several key modules:

1. **JsonModule**: Handles JSON serialization and deserialization
2. **TrinoVerifierModule**: Core verifier-specific bindings and configurations
3. **DataSourceModule**: Database connection and DAO provider configuration

### Dependency Injection Architecture

The system leverages Google Guice for dependency injection, providing a clean separation of concerns and testability:

```mermaid
graph LR
    subgraph "Guice Modules"
        JM[JsonModule]
        TVM[TrinoVerifierModule]
        DSM[DataSourceModule]
        AMM[Additional Modules]
    end
    
    subgraph "Provided Services"
        VC[VerifierConfig]
        VD[VerifierDao]
        CF[ConnectionFactory]
        J[Jdbi Instance]
    end
    
    subgraph "Bindings"
        DSM --> CF
        DSM --> J
        J --> VD
    end
    
    TVM --> VC
    AMM --> VariousServices
```

## Query Processing Pipeline

### Query Filtering and Transformation

The Command & Configuration System implements a sophisticated query processing pipeline that handles various aspects of query preparation:

```mermaid
graph TD
    Start[Query Loading] --> TypeFilter[Query Type Filtering]
    TypeFilter --> Override[Configuration Overrides]
    Override --> ShadowRewrite[Shadow Write Rewriting]
    ShadowRewrite --> Final[Final Query List]
    
    subgraph "Type Filtering"
        TP[Test Query Types]
        CP[Control Query Types]
        ST[Statement Analysis]
    end
    
    subgraph "Overrides"
        CO[Catalog Override]
        SO[Schema Override]
        UO[Username Override]
        PO[Password Override]
    end
    
    TypeFilter --> TP
    TypeFilter --> CP
    TypeFilter --> ST
    Override --> CO
    Override --> SO
    Override --> UO
    Override --> PO
```

### Query Type Classification

The system classifies queries into three main categories based on SQL statement analysis:

- **READ**: SELECT, SHOW, EXPLAIN statements
- **CREATE**: CREATE TABLE, CREATE VIEW, CREATE MATERIALIZED VIEW statements
- **MODIFY**: INSERT, UPDATE, DELETE, DROP, ALTER statements

This classification is performed by analyzing the AST (Abstract Syntax Tree) of SQL statements using the [SQL Parser & AST](SQL%20Parser%20&%20AST.md) module.

## JDBC Driver Management

### Dynamic Driver Loading

The system supports dynamic loading of JDBC drivers for both test and control database connections:

```mermaid
sequenceDiagram
    participant VerifyCommand
    participant URLClassLoader
    participant DriverManager
    participant ForwardingDriver
    
    VerifyCommand->>VerifyCommand: Load driver JARs
    VerifyCommand->>URLClassLoader: Create class loader
    URLClassLoader->>VerifyCommand: Return class loader
    VerifyCommand->>Class: Load driver class
    Class->>VerifyCommand: Instantiate driver
    VerifyCommand->>ForwardingDriver: Create wrapper
    ForwardingDriver->>DriverManager: Register driver
```

### Driver Loading Features

- **JAR File Discovery**: Automatically discovers JDBC driver JAR files from specified directories
- **ClassLoader Isolation**: Uses URLClassLoader to isolate driver classes
- **Driver Registration**: Wraps drivers with ForwardingDriver for proper DriverManager registration
- **Multiple Driver Support**: Can load different drivers for test and control connections

## Integration with Trino Verifier

### System Integration Points

The Command & Configuration System integrates with various components of the Trino Verifier:

```mermaid
graph TB
    CCS[Command & Configuration System]
    
    subgraph "Verifier Components"
        QE[Query Execution Engine]
        QPM[Query Pair Management]
        QEV[Query Execution & Validation]
    end
    
    subgraph "External Systems"
        TC[Test Cluster]
        CC[Control Cluster]
        DB[Query Database]
    end
    
    CCS --> QE
    CCS --> QPM
    CCS --> QEV
    CCS --> TC
    CCS --> CC
    CCS --> DB
    
    QE --> TC
    QE --> CC
    QPM --> DB
    QEV --> TC
    QEV --> CC
```

### Configuration Validation

The system performs comprehensive validation of configuration parameters:

- **Event Client Validation**: Ensures specified event clients are supported
- **Query Type Validation**: Validates allowed query types for test and control clusters
- **Shadow Write Validation**: Ensures proper configuration for write shadowing mode
- **JDBC Driver Validation**: Validates driver availability and compatibility

## Error Handling and Logging

### Exception Management

The system implements robust error handling with appropriate logging:

- **Configuration Errors**: Detailed error messages for invalid configurations
- **Database Connection Errors**: Graceful handling of connection failures
- **Query Processing Errors**: Proper error propagation during query rewriting
- **Driver Loading Errors**: Comprehensive error handling for JDBC driver issues

### Logging Integration

The system uses AirLift's logging framework to provide structured logging throughout the verification process:

- **Startup Logging**: Configuration loading and initialization status
- **Query Processing Logging**: Progress tracking during query filtering and rewriting
- **Error Logging**: Detailed error information with stack traces
- **Performance Logging**: Timing information for critical operations

## Extensibility Features

### Module System

The Command & Configuration System supports extensibility through additional modules:

```java
protected Iterable<Module> getAdditionalModules()
{
    return ImmutableList.of();
}
```

This method can be overridden to provide custom Guice modules for extended functionality.

### Custom Query Filtering

The system allows for custom query filtering through method overriding:

```java
protected List<QueryPair> filterQueries(List<QueryPair> queries)
{
    return queries;
}
```

### Database Connection Customization

Custom database connection strategies can be implemented:

```java
protected ConnectionFactory getQueryDatabase(Injector injector)
{
    // Custom connection implementation
}
```

## Performance Considerations

### Concurrent Query Processing

The system implements concurrent query rewriting to improve performance:

- **Thread Pool Management**: Configurable thread pool for parallel processing
- **Completion Service**: Uses ExecutorCompletionService for efficient task coordination
- **Progress Tracking**: Real-time progress reporting during query processing

### Memory Management

- **Immutable Data Structures**: Uses Guava's immutable collections for thread safety
- **Resource Cleanup**: Proper cleanup of database connections and thread pools
- **Lifecycle Management**: Integration with AirLift's lifecycle management for proper shutdown

## Security Considerations

### Credential Management

The system handles database credentials securely:

- **Configuration-Based Credentials**: Supports credential overrides through configuration
- **Password Protection**: Proper handling of sensitive configuration parameters
- **Connection Security**: Support for secure database connections

### Access Control

- **Configuration File Access**: Proper file system permissions for configuration files
- **JDBC Driver Security**: Secure loading of JDBC drivers from specified paths
- **Network Security**: Support for secure network connections to database systems

## Testing and Quality Assurance

### Testability Features

The system is designed with testability in mind:

- **Dependency Injection**: All dependencies are injected for easy mocking
- **VisibleForTesting**: Key methods are annotated for testing access
- **Modular Design**: Clear separation of concerns enables unit testing

### Configuration Testing

- **Configuration Validation**: Comprehensive validation of configuration parameters
- **Mock Support**: Easy integration with mock objects for testing
- **Error Simulation**: Ability to simulate various error conditions for testing

This comprehensive command and configuration system provides a solid foundation for the Trino Verifier, ensuring reliable and efficient query verification workflows while maintaining flexibility and extensibility for future enhancements.