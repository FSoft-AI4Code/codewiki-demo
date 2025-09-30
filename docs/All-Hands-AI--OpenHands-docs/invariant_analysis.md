# Invariant Analysis Module

The invariant_analysis module provides advanced security analysis capabilities for OpenHands by integrating with Invariant Labs' security analysis platform. This module enables real-time monitoring and risk assessment of agent actions through policy-based security analysis.

## Overview

The invariant_analysis module is a specialized security component within the broader [security_system](security_system.md) that leverages external security analysis services to evaluate agent actions against predefined security policies. It provides containerized security analysis through Docker integration and maintains persistent monitoring sessions for comprehensive security oversight.

## Architecture

```mermaid
graph TB
    subgraph "Invariant Analysis Module"
        IA[InvariantAnalyzer]
        IC[InvariantClient]
        TE[TraceElement]
        P[Parser]
        N[Nodes]
    end
    
    subgraph "External Services"
        IS[Invariant Server]
        DC[Docker Container]
    end
    
    subgraph "Core System"
        SA[SecurityAnalyzer]
        A[Action]
        ASR[ActionSecurityRisk]
    end
    
    subgraph "Event System"
        E[Event]
        O[Observation]
    end
    
    IA --> SA
    IA --> IC
    IA --> P
    IC --> IS
    IA --> DC
    P --> TE
    P --> N
    P --> A
    P --> O
    IA --> ASR
    
    classDef module fill:#e1f5fe
    classDef external fill:#fff3e0
    classDef core fill:#f3e5f5
    classDef event fill:#e8f5e8
    
    class IA,IC,TE,P,N module
    class IS,DC external
    class SA,A,ASR core
    class E,O event
```

## Core Components

### InvariantAnalyzer

The main security analyzer that orchestrates the security analysis process:

```mermaid
graph LR
    subgraph "InvariantAnalyzer Lifecycle"
        I[Initialize] --> DC[Docker Container]
        DC --> AC[API Connection]
        AC --> PM[Policy Management]
        PM --> AR[Action Risk Assessment]
        AR --> C[Cleanup]
    end
    
    subgraph "Risk Assessment Flow"
        A[Action] --> PE[Parse Element]
        PE --> TR[Update Trace]
        TR --> MC[Monitor Check]
        MC --> RR[Risk Result]
    end
```

**Key Features:**
- Docker-based containerized security analysis
- Session-based monitoring with persistent state
- Policy-driven risk assessment
- Real-time action evaluation

**Risk Assessment Process:**
1. Parses incoming actions into trace elements
2. Maintains cumulative trace history
3. Evaluates actions against security policies
4. Returns structured risk assessments

### InvariantClient

HTTP client for communicating with the Invariant security service:

```mermaid
graph TB
    subgraph "InvariantClient Structure"
        IC[InvariantClient]
        P[Policy Manager]
        M[Monitor Manager]
        S[Session Manager]
    end
    
    subgraph "API Operations"
        SN[Session New]
        PN[Policy New]
        MN[Monitor New]
        MC[Monitor Check]
        PA[Policy Analyze]
    end
    
    IC --> P
    IC --> M
    IC --> S
    P --> PN
    P --> PA
    M --> MN
    M --> MC
    S --> SN
    
    classDef client fill:#e3f2fd
    classDef manager fill:#f1f8e9
    classDef api fill:#fff8e1
    
    class IC client
    class P,M,S manager
    class SN,PN,MN,MC,PA api
```

**Capabilities:**
- Session lifecycle management
- Policy creation and template retrieval
- Monitor setup and real-time checking
- Error handling and timeout management

### Parser System

Converts OpenHands events into Invariant-compatible trace elements:

```mermaid
graph LR
    subgraph "Event Processing"
        A[Action] --> PA[parse_action]
        O[Observation] --> PO[parse_observation]
        PA --> TE[TraceElement]
        PO --> TE
    end
    
    subgraph "Trace Elements"
        TE --> M[Message]
        TE --> TC[ToolCall]
        TE --> TO[ToolOutput]
        TE --> F[Function]
    end
    
    subgraph "State Management"
        IS[InvariantState]
        T[Trace History]
        IS --> T
    end
```

**Supported Conversions:**
- **MessageAction** → Message nodes (user/assistant roles)
- **Actions with tools** → ToolCall + Function nodes
- **Observations** → ToolOutput nodes
- **State changes** → Filtered appropriately

## Integration Points

### Security System Integration

```mermaid
graph TB
    subgraph "Security System"
        SA[SecurityAnalyzer]
        LRA[LLMRiskAnalyzer]
        IA[InvariantAnalyzer]
    end
    
    subgraph "Core Agent System"
        A[Agent]
        AP[ActionParser]
        TCS[TrafficControlState]
    end
    
    subgraph "Events & Actions"
        AC[Action]
        OB[Observation]
        ASR[ActionSecurityRisk]
    end
    
    SA --> IA
    SA --> LRA
    A --> SA
    AP --> AC
    AC --> IA
    IA --> ASR
    OB --> IA
    
    classDef security fill:#ffebee
    classDef core fill:#e8f5e8
    classDef events fill:#e3f2fd
    
    class SA,LRA,IA security
    class A,AP,TCS core
    class AC,OB,ASR events
```

### Runtime Dependencies

```mermaid
graph TB
    subgraph "External Dependencies"
        D[Docker Engine]
        IS[Invariant Server Image]
        N[Network Ports]
    end
    
    subgraph "Python Dependencies"
        DC[docker-py]
        H[httpx]
        P[pydantic]
    end
    
    subgraph "OpenHands Core"
        L[Logger]
        E[Events System]
        RU[Runtime Utils]
    end
    
    IA[InvariantAnalyzer] --> D
    IA --> IS
    IA --> N
    IA --> DC
    IA --> H
    IA --> P
    IA --> L
    IA --> E
    IA --> RU
```

## Data Flow

### Security Analysis Pipeline

```mermaid
sequenceDiagram
    participant Agent
    participant InvariantAnalyzer
    participant Parser
    participant InvariantClient
    participant InvariantServer
    
    Agent->>InvariantAnalyzer: security_risk(action)
    InvariantAnalyzer->>Parser: parse_element(trace, action)
    Parser-->>InvariantAnalyzer: new_elements
    InvariantAnalyzer->>InvariantAnalyzer: update trace
    InvariantAnalyzer->>InvariantClient: monitor.check(past, pending)
    InvariantClient->>InvariantServer: POST /monitor/{id}/check
    InvariantServer-->>InvariantClient: risk_results
    InvariantClient-->>InvariantAnalyzer: (results, error)
    InvariantAnalyzer->>InvariantAnalyzer: get_risk(results)
    InvariantAnalyzer-->>Agent: ActionSecurityRisk
```

### Container Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> CheckingExisting: Docker client ready
    CheckingExisting --> StartingExisting: Container exists (stopped)
    CheckingExisting --> CreatingNew: No container found
    StartingExisting --> WaitingForReady
    CreatingNew --> WaitingForReady
    WaitingForReady --> Ready: Container running
    WaitingForReady --> Timeout: Timeout exceeded
    Ready --> Processing: Handle requests
    Processing --> Ready: Continue processing
    Ready --> Stopping: close() called
    Stopping --> [*]
    Timeout --> [*]
```

## Configuration and Setup

### Docker Requirements

The module requires Docker to be running and accessible:

```python
# Container configuration
container_name = 'openhands-invariant-server'
image_name = 'ghcr.io/invariantlabs-ai/server:openhands'
api_host = 'http://localhost'
timeout = 180  # seconds
```

### Policy Management

Security policies can be:
- **Template-based**: Retrieved from Invariant service defaults
- **Custom**: Provided during analyzer initialization
- **Dynamic**: Updated through the Policy API

### Session Management

Each analyzer instance maintains:
- **Unique session ID**: For isolation between analysis sessions
- **Persistent trace**: Cumulative action history
- **Monitor state**: Policy evaluation context

## Error Handling

### Container Management Errors

```mermaid
graph TB
    subgraph "Error Scenarios"
        DE[Docker Engine Unavailable]
        CF[Container Failure]
        NE[Network Error]
        TO[Timeout]
    end
    
    subgraph "Recovery Strategies"
        ER[Exception Raising]
        LO[Logging]
        RT[Retry Logic]
        GD[Graceful Degradation]
    end
    
    DE --> ER
    CF --> RT
    NE --> LO
    TO --> GD
```

### API Communication Errors

- **Network timeouts**: Configurable timeout with retry logic
- **HTTP errors**: Proper error propagation and logging
- **Service unavailability**: Graceful degradation to unknown risk level

## Performance Considerations

### Resource Management

- **Container reuse**: Existing containers are restarted rather than recreated
- **Port allocation**: Dynamic port finding to avoid conflicts
- **Memory efficiency**: Trace elements use Pydantic models for optimal serialization

### Scalability Factors

- **Session isolation**: Multiple analyzer instances can run concurrently
- **Stateful analysis**: Trace history enables context-aware security analysis
- **Async compatibility**: Designed for async/await patterns

## Security Implications

### Isolation

- **Containerized execution**: Security analysis runs in isolated Docker environment
- **Network boundaries**: Communication limited to HTTP API calls
- **Session separation**: Each analysis session maintains independent state

### Data Privacy

- **Local processing**: Sensitive data processed within controlled environment
- **Configurable policies**: Security rules can be customized per deployment
- **Audit trail**: Complete trace history maintained for security review

## Usage Examples

### Basic Security Analysis

```python
# Initialize analyzer with default policy
analyzer = InvariantAnalyzer()

# Evaluate action security risk
risk = await analyzer.security_risk(action)

# Cleanup resources
await analyzer.close()
```

### Custom Policy Analysis

```python
# Initialize with custom security policy
custom_policy = "..."
analyzer = InvariantAnalyzer(policy=custom_policy)

# Process multiple actions
for action in actions:
    risk = await analyzer.security_risk(action)
    if risk == ActionSecurityRisk.HIGH:
        # Handle high-risk action
        pass
```

## Related Documentation

- [security_system](security_system.md) - Overall security architecture
- [events_and_actions](events_and_actions.md) - Event system integration
- [core_agent_system](core_agent_system.md) - Agent integration points
- [runtime_system](runtime_system.md) - Docker and container management

## Future Enhancements

### Planned Features

- **Policy versioning**: Support for policy evolution and rollback
- **Batch analysis**: Efficient processing of multiple actions
- **Custom risk metrics**: Extended risk assessment capabilities
- **Integration APIs**: Enhanced integration with external security tools

### Optimization Opportunities

- **Connection pooling**: Reuse HTTP connections for better performance
- **Caching strategies**: Cache policy evaluations for repeated patterns
- **Streaming analysis**: Real-time analysis of action streams
- **Distributed deployment**: Support for distributed security analysis