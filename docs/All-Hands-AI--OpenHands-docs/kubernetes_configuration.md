# Kubernetes Configuration Module

## Overview

The `kubernetes_configuration` module provides configuration management for Kubernetes-based runtime environments in OpenHands. This module defines the `KubernetesConfig` class, which encapsulates all necessary parameters for deploying and managing OpenHands runtime pods in Kubernetes clusters.

The module serves as the configuration foundation for the [kubernetes_runtime](runtime_implementations.md#kubernetes-runtime) implementation, enabling containerized execution environments with full Kubernetes orchestration capabilities including resource management, networking, storage, and security configurations.

## Architecture

```mermaid
graph TB
    subgraph "Configuration Layer"
        KC[KubernetesConfig]
        TOML[TOML Configuration]
    end
    
    subgraph "Runtime Layer"
        KR[KubernetesRuntime]
        K8sClient[Kubernetes Client]
    end
    
    subgraph "Kubernetes Resources"
        Pod[Runtime Pod]
        PVC[Persistent Volume Claim]
        Svc[Services]
        Ing[Ingress]
    end
    
    TOML --> KC
    KC --> KR
    KR --> K8sClient
    K8sClient --> Pod
    K8sClient --> PVC
    K8sClient --> Svc
    K8sClient --> Ing
    
    classDef config fill:#e1f5fe
    classDef runtime fill:#f3e5f5
    classDef k8s fill:#e8f5e8
    
    class KC,TOML config
    class KR,K8sClient runtime
    class Pod,PVC,Svc,Ing k8s
```

## Core Components

### KubernetesConfig

The `KubernetesConfig` class is a Pydantic model that defines all configuration parameters required for Kubernetes runtime deployment:

#### Resource Management
- **CPU and Memory**: Configurable resource requests and limits for runtime pods
- **Storage**: Persistent volume claim configuration with customizable size and storage class
- **Privileged Mode**: Support for Docker-in-Docker scenarios

#### Networking Configuration
- **Ingress**: Domain configuration and TLS secret management
- **Service Discovery**: Internal cluster networking setup
- **Port Management**: Container and service port configuration

#### Security and Access Control
- **Image Pull Secrets**: Support for private container registries
- **Node Scheduling**: Node selector and toleration configurations
- **TLS Configuration**: Secure ingress with certificate management

#### Namespace Management
- **Multi-tenancy**: Configurable Kubernetes namespace isolation
- **Resource Organization**: Logical grouping of related resources

## Configuration Schema

```mermaid
classDiagram
    class KubernetesConfig {
        +str namespace
        +str ingress_domain
        +str pvc_storage_size
        +str|None pvc_storage_class
        +str resource_cpu_request
        +str resource_memory_request
        +str resource_memory_limit
        +str|None image_pull_secret
        +str|None ingress_tls_secret
        +str|None node_selector_key
        +str|None node_selector_val
        +str|None tolerations_yaml
        +bool privileged
        +from_toml_section(data: dict) dict[str, KubernetesConfig]
    }
    
    class BaseModel {
        <<Pydantic>>
    }
    
    KubernetesConfig --|> BaseModel
```

## Configuration Parameters

### Core Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `namespace` | `str` | `'default'` | Kubernetes namespace for OpenHands resources |
| `ingress_domain` | `str` | `'localhost'` | Base domain for ingress resources |
| `privileged` | `bool` | `False` | Enable privileged mode for Docker-in-Docker |

### Resource Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `resource_cpu_request` | `str` | `'1'` | CPU request for runtime pods |
| `resource_memory_request` | `str` | `'1Gi'` | Memory request for runtime pods |
| `resource_memory_limit` | `str` | `'2Gi'` | Memory limit for runtime pods |

### Storage Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pvc_storage_size` | `str` | `'2Gi'` | Size of persistent volume claim |
| `pvc_storage_class` | `str \| None` | `None` | Storage class for PVCs |

### Security Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_pull_secret` | `str \| None` | `None` | Secret for private registries |
| `ingress_tls_secret` | `str \| None` | `None` | TLS secret for ingress |

### Scheduling Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_selector_key` | `str \| None` | `None` | Node selector key for pod scheduling |
| `node_selector_val` | `str \| None` | `None` | Node selector value for pod scheduling |
| `tolerations_yaml` | `str \| None` | `None` | YAML string defining pod tolerations |

## Integration with Runtime System

```mermaid
sequenceDiagram
    participant Config as Configuration
    participant Runtime as KubernetesRuntime
    participant K8sAPI as Kubernetes API
    participant Resources as K8s Resources
    
    Config->>Runtime: Initialize with KubernetesConfig
    Runtime->>Runtime: Validate configuration
    Runtime->>K8sAPI: Create Kubernetes client
    Runtime->>Resources: Create PVC with storage config
    Runtime->>Resources: Create Pod with resource limits
    Runtime->>Resources: Create Services for networking
    Runtime->>Resources: Create Ingress with domain config
    Resources-->>Runtime: Resources created successfully
    Runtime-->>Config: Runtime ready
```

## Configuration Loading

The module supports loading configuration from TOML files through the `from_toml_section` class method:

```python
# Example TOML configuration
[kubernetes]
namespace = "openhands-dev"
ingress_domain = "dev.example.com"
pvc_storage_size = "5Gi"
pvc_storage_class = "fast-ssd"
resource_cpu_request = "2"
resource_memory_request = "2Gi"
resource_memory_limit = "4Gi"
image_pull_secret = "registry-secret"
ingress_tls_secret = "tls-secret"
privileged = true
```

## Error Handling and Validation

```mermaid
flowchart TD
    A[Load TOML Config] --> B{Valid Configuration?}
    B -->|Yes| C[Create KubernetesConfig]
    B -->|No| D[ValidationError]
    C --> E[Initialize Runtime]
    D --> F[Raise ValueError]
    E --> G{Runtime Creation Success?}
    G -->|Yes| H[Runtime Ready]
    G -->|No| I[Runtime Error]
    
    classDef success fill:#d4edda
    classDef error fill:#f8d7da
    classDef process fill:#fff3cd
    
    class C,E,H success
    class D,F,I error
    class A,B,G process
```

## Dependencies

The kubernetes_configuration module integrates with several other system components:

- **[runtime_system](runtime_system.md)**: Provides the base runtime infrastructure
- **[kubernetes_runtime](runtime_implementations.md#kubernetes-runtime)**: Implements the actual Kubernetes runtime using this configuration
- **[core_configuration](core_configuration.md)**: Part of the broader configuration management system
- **[security_configuration](security_configuration.md)**: Works alongside security settings for comprehensive runtime security

## Usage Examples

### Basic Configuration

```python
from openhands.core.config.kubernetes_config import KubernetesConfig

# Create basic configuration
config = KubernetesConfig(
    namespace="my-namespace",
    ingress_domain="my-app.example.com",
    pvc_storage_size="10Gi"
)
```

### Advanced Configuration with Security

```python
# Advanced configuration with security and scheduling
config = KubernetesConfig(
    namespace="production",
    ingress_domain="prod.example.com",
    pvc_storage_size="50Gi",
    pvc_storage_class="premium-ssd",
    resource_cpu_request="4",
    resource_memory_request="8Gi",
    resource_memory_limit="16Gi",
    image_pull_secret="prod-registry-secret",
    ingress_tls_secret="prod-tls-cert",
    node_selector_key="workload-type",
    node_selector_val="openhands",
    privileged=True
)
```

### Loading from TOML

```python
# Load from TOML configuration
toml_data = {
    "namespace": "staging",
    "ingress_domain": "staging.example.com",
    "pvc_storage_size": "20Gi",
    "resource_cpu_request": "2",
    "resource_memory_request": "4Gi"
}

config_mapping = KubernetesConfig.from_toml_section(toml_data)
kubernetes_config = config_mapping["kubernetes"]
```

## Best Practices

### Resource Planning
- **CPU Requests**: Set based on expected workload requirements
- **Memory Limits**: Configure to prevent resource exhaustion
- **Storage Size**: Plan for workspace and temporary file requirements

### Security Considerations
- **Image Pull Secrets**: Always use for production deployments with private registries
- **TLS Configuration**: Enable TLS for all external-facing ingress resources
- **Privileged Mode**: Only enable when Docker-in-Docker functionality is required

### Operational Excellence
- **Namespace Isolation**: Use dedicated namespaces for different environments
- **Node Scheduling**: Leverage node selectors and tolerations for workload placement
- **Storage Classes**: Choose appropriate storage classes based on performance requirements

## Monitoring and Observability

The configuration enables comprehensive monitoring through:

- **Resource Metrics**: CPU, memory, and storage utilization tracking
- **Network Monitoring**: Ingress and service connectivity metrics
- **Security Auditing**: Access control and privilege escalation monitoring
- **Operational Metrics**: Pod lifecycle and scheduling effectiveness

This module forms the foundation for robust, scalable, and secure Kubernetes-based runtime environments in the OpenHands system.