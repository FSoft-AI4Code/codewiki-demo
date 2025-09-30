# Builder System Documentation

## Overview

The Builder System is a critical component of the OpenHands runtime infrastructure that provides an abstract interface for building runtime container images. This module defines the contract for runtime image builders and enables different runtime implementations to create and manage their execution environments.

The builder system serves as the foundation for creating containerized environments where OpenHands agents execute their tasks, ensuring consistent and reproducible runtime environments across different deployment scenarios.

## Core Architecture

### RuntimeBuilder Abstract Base Class

The `RuntimeBuilder` is the central abstraction that defines the interface for all runtime image builders in the OpenHands ecosystem.

```mermaid
classDiagram
    class RuntimeBuilder {
        <<abstract>>
        +build(path: str, tags: list[str], platform: str, extra_build_args: list[str]) str
        +image_exists(image_name: str, pull_from_repo: bool) bool
    }
    
    class DockerBuilder {
        +build(path, tags, platform, extra_build_args) str
        +image_exists(image_name, pull_from_repo) bool
    }
    
    class KubernetesBuilder {
        +build(path, tags, platform, extra_build_args) str
        +image_exists(image_name, pull_from_repo) bool
    }
    
    RuntimeBuilder <|-- DockerBuilder
    RuntimeBuilder <|-- KubernetesBuilder
    
    note for RuntimeBuilder "Abstract base class defining\nthe contract for runtime builders"
    note for DockerBuilder "Docker-specific implementation\nfor container image building"
    note for KubernetesBuilder "Kubernetes-specific implementation\nfor pod image building"
```

### Key Methods

#### build()
- **Purpose**: Builds runtime images from source directories
- **Parameters**:
  - `path`: Build directory containing Dockerfile and context
  - `tags`: List of tags to apply to the built image
  - `platform`: Target platform for multi-architecture builds
  - `extra_build_args`: Additional build arguments
- **Returns**: Final image name:tag for runtime usage
- **Raises**: `AgentRuntimeBuildError` on build failures

#### image_exists()
- **Purpose**: Checks if a runtime image exists locally or remotely
- **Parameters**:
  - `image_name`: Name of the image to check
  - `pull_from_repo`: Whether to pull from remote repository
- **Returns**: Boolean indicating image availability

## Integration with Runtime System

The Builder System integrates closely with the broader runtime infrastructure:

```mermaid
graph TB
    subgraph "Runtime System"
        A[Runtime Base] --> B[Local Runtime]
        A --> C[CLI Runtime]
        A --> D[Kubernetes Runtime]
    end
    
    subgraph "Builder System"
        E[RuntimeBuilder] --> F[Docker Builder]
        E --> G[Kubernetes Builder]
        E --> H[Custom Builder]
    end
    
    subgraph "Plugin System"
        I[Plugin Base] --> J[VSCode Plugin]
        I --> K[Jupyter Plugin]
        I --> L[Custom Plugins]
    end
    
    B --> F
    D --> G
    A --> I
    
    F --> M[Docker Images]
    G --> N[K8s Pod Images]
    H --> O[Custom Images]
    
    style E fill:#e1f5fe
    style A fill:#f3e5f5
    style I fill:#e8f5e8
```

### Runtime Dependencies

The builder system supports various runtime implementations:

- **[Local Runtime](runtime_implementations.md#local-runtime)**: Uses Docker builders for containerized execution
- **[CLI Runtime](runtime_implementations.md#cli-runtime)**: May use builders for isolated environments
- **[Kubernetes Runtime](runtime_implementations.md#kubernetes-runtime)**: Leverages Kubernetes-specific builders

## Build Process Flow

```mermaid
sequenceDiagram
    participant R as Runtime
    participant B as RuntimeBuilder
    participant I as Image Registry
    participant C as Container Engine
    
    R->>B: build(path, tags, platform, args)
    B->>B: Validate build context
    B->>C: Execute build command
    C->>C: Build image layers
    C->>I: Push to registry (if configured)
    I-->>C: Confirm push
    C-->>B: Return built image ID
    B->>B: Apply tags and mutations
    B-->>R: Return final image name:tag
    
    Note over R,C: Build process with error handling
    
    R->>B: image_exists(image_name, pull_from_repo)
    B->>I: Check remote registry
    I-->>B: Image availability status
    B->>C: Check local cache
    C-->>B: Local availability status
    B-->>R: Combined availability result
```

## Error Handling

The builder system implements robust error handling:

### AgentRuntimeBuildError
- Raised when image builds fail
- Contains detailed error information
- Enables runtime recovery strategies

### Common Error Scenarios
1. **Build Context Issues**: Missing Dockerfile, invalid paths
2. **Resource Constraints**: Insufficient memory/disk space
3. **Network Failures**: Registry connectivity issues
4. **Permission Errors**: Docker daemon access, registry authentication

## Configuration Integration

The builder system integrates with the [core configuration system](core_configuration.md):

```mermaid
graph LR
    subgraph "Configuration"
        A[OpenHandsConfig] --> B[SandboxConfig]
        B --> C[runtime_container_image]
        B --> D[base_container_image]
        B --> E[build_args]
    end
    
    subgraph "Builder System"
        F[RuntimeBuilder] --> G["build()"]
        G --> H[Image Building]
    end
    
    C --> F
    D --> F
    E --> G
    
    style A fill:#fff3e0
    style F fill:#e1f5fe
```

## Plugin Integration

The builder system works with the [plugin system](plugin_system.md) to create runtime environments with required capabilities:

### Plugin-Aware Building
- Builders can incorporate plugin requirements into images
- Dynamic plugin installation during build process
- Plugin-specific build arguments and configurations

### Build-Time Plugin Setup
```mermaid
graph TD
    A[Plugin Requirements] --> B[RuntimeBuilder]
    B --> C[Generate Build Context]
    C --> D[Include Plugin Dependencies]
    D --> E[Build Runtime Image]
    E --> F[Plugin-Ready Runtime]
    
    style A fill:#e8f5e8
    style B fill:#e1f5fe
    style F fill:#f3e5f5
```

## Security Considerations

### Build Security
- Secure build contexts with minimal attack surface
- Validation of build arguments and parameters
- Isolation of build processes from host system

### Image Security
- Base image vulnerability scanning
- Minimal runtime dependencies
- Secure default configurations

## Performance Optimization

### Build Caching
- Layer caching for faster subsequent builds
- Multi-stage build optimization
- Shared base image layers

### Resource Management
- Build resource limits and quotas
- Parallel build capabilities
- Build artifact cleanup

## Extension Points

The builder system provides several extension points:

### Custom Builder Implementation
```python
class CustomRuntimeBuilder(RuntimeBuilder):
    def build(self, path: str, tags: list[str], 
              platform: str | None = None,
              extra_build_args: list[str] | None = None) -> str:
        # Custom build logic
        pass
    
    def image_exists(self, image_name: str, 
                     pull_from_repo: bool = True) -> bool:
        # Custom existence check
        pass
```

### Builder Factory Pattern
- Dynamic builder selection based on runtime type
- Configuration-driven builder instantiation
- Plugin-based builder extensions

## Monitoring and Observability

### Build Metrics
- Build duration and success rates
- Image size and layer optimization
- Resource utilization during builds

### Logging and Debugging
- Detailed build logs and error traces
- Build context inspection capabilities
- Performance profiling for build optimization

## Related Documentation

- **[Runtime System](runtime_system.md)**: Overall runtime architecture
- **[Runtime Implementations](runtime_implementations.md)**: Specific runtime types
- **[Plugin System](plugin_system.md)**: Plugin architecture and integration
- **[Core Configuration](core_configuration.md)**: Configuration management
- **[Security System](security_system.md)**: Security considerations

## Future Enhancements

### Planned Features
- Multi-architecture build support
- Advanced caching strategies
- Build pipeline integration
- Custom registry support

### Extensibility Roadmap
- Builder plugin architecture
- Dynamic build optimization
- Cloud-native build services
- Integration with CI/CD pipelines

The Builder System serves as a foundational component that enables OpenHands to create consistent, secure, and optimized runtime environments across different deployment scenarios while maintaining flexibility for custom implementations and extensions.