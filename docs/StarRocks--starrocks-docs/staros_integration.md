# StarOS Integration Module Documentation

## Overview

The StarOS Integration module serves as the bridge between StarRocks and StarOS (Star Operating System), providing seamless integration for cloud-native storage and metadata management. This module enables StarRocks to leverage StarOS capabilities for distributed storage management, metadata coordination, and resource orchestration in cloud environments.

## Purpose and Core Functionality

The primary purpose of the StarOS Integration module is to:

1. **Provide unified storage management** - Integrate StarOS as the underlying storage layer for StarRocks
2. **Enable cloud-native features** - Support elastic scaling and resource management in cloud environments
3. **Coordinate metadata** - Synchronize metadata between StarRocks and StarOS
4. **Manage resource lifecycle** - Handle worker group provisioning and resource allocation
5. **Ensure high availability** - Provide fault tolerance and recovery mechanisms

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "StarRocks Frontend"
        FE[Frontend Server]
        GSM[GlobalStateMgr]
        StarMgrServer[StarMgrServer]
    end
    
    subgraph "StarOS Integration Layer"
        StarMgrServer
        StarOSAgent[StarOSAgent]
        JournalSystem[StarOSBDBJEJournalSystem]
        CheckpointController[CheckpointController]
        CheckpointWorker[StarMgrCheckpointWorker]
    end
    
    subgraph "StarOS Core"
        StarManagerServer[StarManagerServer]
        StarManager[StarManager]
        MetricsSystem[MetricsSystem]
    end
    
    subgraph "Storage Layer"
        BDBEnv[BDBEnvironment]
        Storage[Storage System]
    end
    
    FE --> GSM
    GSM --> StarOSAgent
    StarOSAgent --> StarMgrServer
    StarMgrServer --> JournalSystem
    StarMgrServer --> StarManagerServer
    StarManagerServer --> StarManager
    JournalSystem --> BDBEnv
    CheckpointController --> JournalSystem
    CheckpointWorker --> JournalSystem
    StarManager --> MetricsSystem
    StarManager --> Storage
```

### Component Relationships

```mermaid
graph LR
    subgraph "StarMgrServer Components"
        SMS[StarMgrServer]
        SH[SingletonHolder]
        CC[CheckpointController]
        CW[CheckpointWorker]
        SJ[StarOSBDBJEJournalSystem]
        SE[StateChangeExecution]
    end
    
    SMS -.->|manages| SH
    SMS -->|controls| CC
    SMS -->|manages| CW
    SMS -->|uses| SJ
    SMS -.->|implements| SE
    
    subgraph "External Dependencies"
        SMServer[StarManagerServer]
        SM[StarManager]
        GSM[GlobalStateMgr]
        SOA[StarOSAgent]
    end
    
    SMS -->|integrates| SMServer
    SMServer -->|provides| SM
    GSM -->|uses| SOA
    SOA -->|connects| SMServer
```

## Core Components

### StarMgrServer

The `StarMgrServer` class is the central component that manages the integration between StarRocks and StarOS. It implements a singleton pattern and provides coordination for:

- **Journal Management**: Handles transaction logs and metadata persistence
- **Checkpoint Operations**: Manages periodic snapshots for recovery
- **State Transitions**: Coordinates leader/follower transitions in HA setups
- **Configuration Synchronization**: Keeps StarOS configuration in sync with StarRocks

#### Key Methods:

- `initialize()`: Sets up the StarOS integration with proper configuration
- `becomeLeader()/becomeFollower()`: Handles HA state transitions
- `loadImage()/replayAndGenerateImage()`: Manages metadata persistence
- `getCurrentState()/getServingState()`: Provides access to server instances

### StarOSBDBJEJournalSystem

Manages the journaling system for StarOS metadata using BDB JE (Berkeley DB Java Edition):

- **Transaction Logging**: Records all metadata changes
- **Recovery Support**: Enables crash recovery through journal replay
- **Checkpoint Coordination**: Works with checkpoint workers for image generation

### CheckpointController & CheckpointWorker

Handle the checkpointing process for metadata persistence:

- **Periodic Snapshots**: Create consistent points for recovery
- **Image Management**: Generate and manage metadata images
- **Recovery Support**: Enable fast recovery from checkpoints

## Data Flow

### Initialization Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant SMS as StarMgrServer
    participant SMServer as StarManagerServer
    participant SOA as StarOSAgent
    participant SM as StarManager
    
    FE->>SMS: initialize()
    SMS->>SMS: Setup configuration
    SMS->>SMServer: new StarManagerServer()
    SMServer->>SM: start()
    SMS->>SOA: init(starMgrServer)
    SMS->>SMS: loadImage()
    SMS->>SMS: startCheckpointController()
    SMS->>SMS: startCheckpointWorker()
```

### Metadata Persistence Flow

```mermaid
sequenceDiagram
    participant Client
    participant SM as StarManager
    participant Journal as JournalSystem
    participant CC as CheckpointController
    participant Storage as File System
    
    Client->>SM: Metadata Operation
    SM->>Journal: Write Journal Entry
    Journal-->>SM: Acknowledge
    SM-->>Client: Operation Complete
    
    Note over CC: Periodic Checkpoint
    CC->>Journal: getReplayId()
    CC->>SM: dumpMeta()
    CC->>Storage: Write Image File
    CC->>Journal: Update Checkpoint
```

## Configuration Management

The module synchronizes configuration between StarRocks and StarOS:

```mermaid
graph LR
    subgraph "StarRocks Config"
        SRConfig[Config]
        Heartbeat[heartbeat_timeout_second]
        Balance[tablet_sched_disable_balance]
        GRPC[starmgr_grpc_timeout_seconds]
    end
    
    subgraph "StarOS Config"
        SOConfig[com.staros.util.Config]
        SOHeartbeat[WORKER_HEARTBEAT_INTERVAL_SEC]
        SOBalance[DISABLE_BACKGROUND_SHARD_SCHEDULE_CHECK]
        SOGRPC[GRPC_RPC_TIME_OUT_SEC]
    end
    
    SRConfig -->|"synchronizes"| SOConfig
    Heartbeat --> SOHeartbeat
    Balance --> SOBalance
    GRPC --> SOGRPC
```

## Integration Points

### With GlobalStateMgr

The StarMgrServer integrates with GlobalStateMgr through:

- **StarOSAgent**: Provides the interface for StarOS operations
- **Configuration Sync**: Registers config refresh listeners
- **State Management**: Coordinates with FE state transitions

### With Storage Engine

Integration with the storage engine enables:

- **Lake Storage Support**: Coordinates with lake storage components
- **Metadata Management**: Manages storage metadata through StarOS
- **Resource Allocation**: Handles worker group and shard allocation

## High Availability

### Leader-Follower Architecture

```mermaid
graph TB
    subgraph "Primary Cluster"
        Leader[StarMgrServer Leader]
        LeaderSM[StarManager Leader]
    end
    
    subgraph "Secondary Cluster"
        Follower1[StarMgrServer Follower]
        FollowerSM1[StarManager Follower]
        Follower2[StarMgrServer Follower]
        FollowerSM2[StarManager Follower]
    end
    
    Leader -->|"journal replication"| Follower1
    Leader -->|"journal replication"| Follower2
    LeaderSM -.->|"metadata sync"| FollowerSM1
    LeaderSM -.->|"metadata sync"| FollowerSM2
```

### Checkpoint and Recovery

The module implements a robust checkpoint and recovery mechanism:

1. **Periodic Checkpoints**: Creates consistent snapshots of metadata
2. **Journal Replay**: Enables recovery from the last checkpoint
3. **Image Management**: Maintains multiple checkpoint images
4. **Crash Recovery**: Automatically recovers from failures

## Monitoring and Metrics

Integration with the metrics system provides:

- **Performance Metrics**: Track operation latencies and throughput
- **Resource Usage**: Monitor worker group and shard allocation
- **Health Monitoring**: Track system health and availability
- **Prometheus Integration**: Export metrics for external monitoring

## Dependencies

### Internal Dependencies

- **[GlobalStateMgr](frontend_server.md)**: Coordinates with the main state manager
- **[BDBEnvironment](frontend_server.md)**: Uses BDB JE for journaling
- **[StarOSAgent](frontend_server.md)**: Provides StarOS interface
- **[CheckpointController](frontend_server.md)**: Manages checkpoint operations

### External Dependencies

- **StarOS Core**: The underlying StarOS manager and server components
- **BDB JE**: Berkeley DB Java Edition for transaction logging
- **Metrics System**: For monitoring and observability

## Usage Patterns

### Basic Initialization

```java
// Initialize StarMgrServer
StarMgrServer starMgrServer = StarMgrServer.getServingState();
starMgrServer.initialize(bdbEnvironment, baseImageDir);

// Access StarManager
StarManager starManager = starMgrServer.getStarMgr();
```

### State Management

```java
// Handle state transitions
StateChangeExecution execution = starMgrServer.getStateChangeExecution();
execution.transferToLeader();    // Become leader
execution.transferToNonLeader(FrontendNodeType.FOLLOWER); // Become follower
```

### Checkpoint Operations

```java
// Start checkpoint services
starMgrServer.startCheckpointController();
starMgrServer.startCheckpointWorker();

// Trigger manual checkpoint
starMgrServer.triggerNewImage();
```

## Best Practices

1. **Configuration Synchronization**: Ensure StarOS configuration stays in sync with StarRocks
2. **Monitoring**: Set up proper monitoring for StarOS integration metrics
3. **Backup Strategy**: Implement regular checkpoint backups
4. **Resource Management**: Monitor worker group allocation and balance
5. **Error Handling**: Implement proper error handling for StarOS operations

## Troubleshooting

### Common Issues

1. **Initialization Failures**: Check network connectivity and configuration
2. **Journal Replay Issues**: Verify BDB environment health
3. **Checkpoint Failures**: Check disk space and permissions
4. **State Transition Problems**: Verify HA configuration

### Diagnostic Tools

- **Metrics Collection**: Use built-in metrics for monitoring
- **Log Analysis**: Check StarMgrServer logs for errors
- **Journal Inspection**: Examine BDB journal for transaction issues
- **Image Verification**: Validate checkpoint image integrity

## Future Enhancements

The StarOS Integration module is designed to support:

- **Multi-Cloud Support**: Enhanced cloud provider integration
- **Auto-Scaling**: Dynamic resource allocation based on workload
- **Advanced Monitoring**: Enhanced observability and alerting
- **Performance Optimization**: Improved metadata operation performance
- **Security Enhancements**: Enhanced authentication and authorization