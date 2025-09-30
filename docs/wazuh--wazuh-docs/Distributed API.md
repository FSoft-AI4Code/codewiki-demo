# Distributed API Module

## Overview

The Distributed API (DAPI) module is a critical component of Wazuh's cluster architecture that enables seamless distribution and execution of API requests across multiple nodes in a clustered environment. It provides intelligent request routing, load balancing, and fault tolerance for API operations in distributed Wazuh deployments.

The module acts as a middleware layer that abstracts the complexity of cluster communication, allowing API requests to be executed on the most appropriate node based on data locality, node capabilities, and system state. It supports both synchronous and asynchronous operations while maintaining security through RBAC integration and ensuring data consistency across the cluster.

## Architecture

### Core Components

The Distributed API module consists of four main components that work together to provide distributed request processing:

```mermaid
graph TB
    subgraph "Distributed API Module"
        DA[DistributedAPI]
        WRQ[WazuhRequestQueue]
        ARQ[APIRequestQueue]
        SSRQ[SendSyncRequestQueue]
    end
    
    subgraph "External Dependencies"
        CM[Cluster Management]
        RBAC[RBAC Security]
        CF[Core Framework]
        CL[Communication Layer]
        AM[Agent Management]
    end
    
    DA --> WRQ
    ARQ --> DA
    SSRQ --> WRQ
    
    DA --> CM
    DA --> RBAC
    DA --> CF
    DA --> CL
    DA --> AM
    
    style DA fill:#e1f5fe
    style WRQ fill:#f3e5f5
    style ARQ fill:#e8f5e8
    style SSRQ fill:#fff3e0
```

### Component Relationships

```mermaid
classDiagram
    class DistributedAPI {
        +f: Callable
        +logger: Logger
        +f_kwargs: Dict
        +node: Handler
        +request_type: str
        +rbac_permissions: Dict
        +distribute_function()
        +execute_local_request()
        +execute_remote_request()
        +forward_request()
        +get_solver_node()
    }
    
    class WazuhRequestQueue {
        +request_queue: Queue
        +server: Server
        +add_request(request)
    }
    
    class APIRequestQueue {
        +logger: Logger
        +run()
    }
    
    class SendSyncRequestQueue {
        +logger: Logger
        +run()
    }
    
    WazuhRequestQueue <|-- APIRequestQueue
    WazuhRequestQueue <|-- SendSyncRequestQueue
    APIRequestQueue --> DistributedAPI
    SendSyncRequestQueue --> DistributedAPI
```

## Core Components

### DistributedAPI

The `DistributedAPI` class is the central orchestrator that handles the distribution logic for API requests across cluster nodes.

**Key Responsibilities:**
- **Request Routing**: Determines whether to execute requests locally, remotely, or forward them to other nodes
- **Node Selection**: Identifies the optimal node(s) to handle specific requests based on data locality
- **Error Handling**: Provides comprehensive error management with detailed error information
- **Security Integration**: Enforces RBAC permissions and user context across distributed operations
- **Performance Optimization**: Manages timeouts, process pools, and asynchronous execution

**Request Types:**
- `local_master`: Execute on master node only
- `local_any`: Execute on current node regardless of type
- `distributed_master`: Distribute across cluster from master node

### WazuhRequestQueue

Base class for request queue management that provides the foundation for asynchronous request processing.

**Features:**
- **Asynchronous Queue**: Uses asyncio.Queue for non-blocking request handling
- **Request Buffering**: Manages incoming requests in a FIFO manner
- **Server Integration**: Maintains reference to cluster server for node communication

### APIRequestQueue

Specialized queue for handling distributed API requests with comprehensive logging and error management.

**Capabilities:**
- **Background Processing**: Continuously processes API requests in the background
- **Node Resolution**: Resolves target nodes for request forwarding
- **Response Management**: Handles successful responses and error conditions
- **Logging Integration**: Provides detailed logging with cluster-specific filters

### SendSyncRequestQueue

Dedicated queue for handling synchronous communication requests between cluster nodes.

**Functions:**
- **Sync Operations**: Manages synchronous inter-node communication
- **Daemon Integration**: Handles requests to specific Wazuh daemons
- **Error Recovery**: Provides robust error handling for sync operations

## Request Flow Architecture

```mermaid
flowchart TD
    A[API Request] --> B{DAPI Enabled?}
    B -->|No| C[Execute Locally]
    B -->|Yes| D{Cluster Status}
    D -->|Disabled| C
    D -->|Enabled| E{Request Type}
    
    E -->|local_any| C
    E -->|local_master & Master Node| C
    E -->|distributed_master & from_cluster| C
    E -->|distributed_master & Master Node| F[Forward Request]
    E -->|Other & Worker Node| G[Execute Remote]
    
    F --> H{Get Solver Nodes}
    H --> I[Node Selection]
    I --> J[Parallel Execution]
    J --> K[Aggregate Results]
    
    G --> L[Send to Master]
    L --> M[Master Processing]
    M --> N[Return Response]
    
    C --> O[Local Execution]
    O --> P[Process Pool]
    P --> Q[Return Result]
    
    K --> R[Final Response]
    N --> R
    Q --> R
```

## Data Flow Patterns

### Local Execution Flow

```mermaid
sequenceDiagram
    participant Client
    participant DAPI as DistributedAPI
    participant Pool as Process Pool
    participant Service as Wazuh Service
    
    Client->>DAPI: API Request
    DAPI->>DAPI: check_wazuh_status()
    DAPI->>Pool: Submit to Process Pool
    Pool->>Service: Execute Function
    Service-->>Pool: Result
    Pool-->>DAPI: Response
    DAPI-->>Client: JSON Response
```

### Remote Execution Flow

```mermaid
sequenceDiagram
    participant Worker
    participant DAPI as DistributedAPI
    participant Client as LocalClient
    participant Master
    
    Worker->>DAPI: API Request
    DAPI->>Client: get_client()
    DAPI->>Master: execute(command='dapi')
    Master->>Master: Process Request
    Master-->>DAPI: Response
    DAPI-->>Worker: JSON Response
```

### Forward Request Flow

```mermaid
sequenceDiagram
    participant API
    participant Master as Master DAPI
    participant Solver as get_solver_node()
    participant Workers as Worker Nodes
    
    API->>Master: distributed_master request
    Master->>Solver: Determine target nodes
    Solver-->>Master: Node mapping
    
    par Parallel Execution
        Master->>Workers: Forward to Node 1
        Master->>Workers: Forward to Node 2
        Master->>Workers: Forward to Node N
    end
    
    Workers-->>Master: Responses
    Master->>Master: Aggregate results
    Master-->>API: Combined response
```

## Integration Points

### Cluster Management Integration

The Distributed API integrates deeply with the [Cluster Management](Cluster%20Management.md) module:

- **Node Discovery**: Uses cluster topology information for request routing
- **Health Monitoring**: Integrates with cluster health checks before request execution
- **Communication Protocols**: Leverages cluster communication channels for inter-node requests

### RBAC Security Integration

Security is enforced through integration with [RBAC Security](RBAC%20Security.md):

- **Permission Validation**: Checks user permissions before request execution
- **Context Propagation**: Maintains user context across distributed operations
- **Node Access Control**: Enforces node-level access restrictions

### Agent Management Integration

Works closely with [Agent Management](Agent%20Management.md) for agent-specific operations:

- **Agent Location**: Determines which node manages specific agents
- **Agent Grouping**: Handles agent group operations across nodes
- **Load Distribution**: Distributes agent-related requests based on agent distribution

## Process Pool Management

The module implements sophisticated process pool management for optimal performance:

```mermaid
graph LR
    subgraph "Process Pools"
        TP[Thread Pool]
        AP[Authentication Pool]
        EP[Events Pool]
        PP[Process Pool]
    end
    
    subgraph "Function Categories"
        AF[Authentication Functions]
        EF[Event Functions]
        GF[General Functions]
        TF[Thread Functions]
    end
    
    AF --> AP
    EF --> EP
    GF --> PP
    TF --> TP
```

**Pool Selection Logic:**
- **Authentication Pool**: For user authentication and token validation functions
- **Events Pool**: For event processing and analysis functions
- **Thread Pool**: For I/O-bound operations
- **Process Pool**: For CPU-intensive operations (default)

## Error Handling and Resilience

### Error Classification

The module provides comprehensive error handling with detailed error information:

```mermaid
graph TD
    A[Request Error] --> B{Error Type}
    B -->|JSON Decode| C[WazuhInternalError 3036]
    B -->|Timeout| D[WazuhInternalError 3021]
    B -->|Service Down| E[WazuhInternalError 1017]
    B -->|Process Pool| F[WazuhInternalError 900/901]
    B -->|Database| G[WazuhInternalError 2008]
    B -->|Generic| H[WazuhInternalError 1000]
    
    C --> I[Error Response]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
```

### Resilience Features

- **Service Health Checks**: Validates required Wazuh services before request execution
- **Timeout Management**: Configurable timeouts with graceful degradation
- **Node Failover**: Automatic handling of node failures during request processing
- **Error Propagation**: Detailed error information with node-specific context

## Configuration and Tuning

### Key Configuration Parameters

- **Request Timeout**: `api_conf['intervals']['request_timeout']`
- **Authentication Pool Size**: `api_conf['authentication_pool_size']`
- **Distributed API Enable**: `cluster_items['distributed_api']['enabled']`

### Performance Tuning

- **Process Pool Sizing**: Adjust pool sizes based on workload characteristics
- **Timeout Configuration**: Balance responsiveness with operation completion
- **Node Selection Strategy**: Optimize based on network topology and data locality

## Security Considerations

### Authentication and Authorization

- **Token Validation**: Secure token handling across distributed operations
- **Permission Inheritance**: Proper RBAC permission propagation
- **User Context**: Maintains user identity throughout request lifecycle

### Data Protection

- **Sensitive Data Masking**: Automatic masking of passwords and tokens in logs
- **Secure Communication**: Encrypted communication between cluster nodes
- **Access Logging**: Comprehensive audit trail for distributed operations

## Monitoring and Observability

### Logging Framework

The module provides extensive logging capabilities:

- **Request Tracing**: Detailed logging of request flow and timing
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Metrics**: Execution time tracking and performance analysis

### Health Monitoring

- **Service Status**: Continuous monitoring of required Wazuh services
- **Node Connectivity**: Real-time cluster node health assessment
- **Queue Monitoring**: Request queue depth and processing metrics

## Best Practices

### Development Guidelines

1. **Error Handling**: Always implement comprehensive error handling with proper error codes
2. **Timeout Management**: Set appropriate timeouts for different operation types
3. **Resource Cleanup**: Ensure proper cleanup of local clients and resources
4. **Security Context**: Maintain proper RBAC context throughout request processing

### Operational Guidelines

1. **Cluster Health**: Monitor cluster health before deploying distributed operations
2. **Load Balancing**: Consider agent distribution when planning cluster topology
3. **Performance Monitoring**: Regular monitoring of request processing times and queue depths
4. **Security Auditing**: Regular review of distributed API access patterns and permissions

## Related Documentation

- [Cluster Management](Cluster%20Management.md) - Core cluster functionality and node management
- [RBAC Security](RBAC%20Security.md) - Role-based access control and security framework
- [Agent Management](Agent%20Management.md) - Agent lifecycle and distribution management
- [Communication Layer](Communication%20Layer.md) - Low-level cluster communication protocols
- [Core Framework](Core%20Framework.md) - Base framework components and utilities
- [API Framework](API%20Framework.md) - REST API implementation and middleware