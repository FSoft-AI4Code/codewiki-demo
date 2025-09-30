# CodeAct Agents Module

The CodeAct Agents module implements specialized AI agents that consolidate actions into a unified code action space, following the CodeAct paradigm for both simplicity and performance. This module provides three distinct agent implementations: CodeActAgent (the core implementation), LocAgent (location-aware variant), and ReadOnlyAgent (safe exploration variant).

## Architecture Overview

```mermaid
graph TB
    subgraph "CodeAct Agents Module"
        CA[CodeActAgent]
        LA[LocAgent]
        ROA[ReadOnlyAgent]
        
        subgraph "Tools & Function Calling"
            CFT[CodeAct Function Tools]
            LFT[Loc Function Tools]
            RFT[ReadOnly Function Tools]
        end
        
        subgraph "Core Tools"
            BT[Bash Tool]
            IPT[IPython Tool]
            ET[Editor Tools]
            BRT[Browser Tool]
            TT[Think Tool]
            FT[Finish Tool]
            CTT[Condensation Tool]
            TTT[Task Tracker Tool]
        end
    end
    
    subgraph "Dependencies"
        direction TB
        AGT[Agent Base Class]
        LLM[LLM Integration]
        STATE[State Management]
        MEMORY[Conversation Memory]
        CONDENSER[Memory Condenser]
        RUNTIME[Runtime System]
    end
    
    CA --> AGT
    LA --> CA
    ROA --> CA
    
    CA --> CFT
    LA --> LFT
    ROA --> RFT
    
    CFT --> BT
    CFT --> IPT
    CFT --> ET
    CFT --> BRT
    CFT --> TT
    CFT --> FT
    CFT --> CTT
    CFT --> TTT
    
    CA --> LLM
    CA --> STATE
    CA --> MEMORY
    CA --> CONDENSER
    CA --> RUNTIME
    
    classDef agent fill:#e1f5fe
    classDef tool fill:#f3e5f5
    classDef dependency fill:#fff3e0
    
    class CA,LA,ROA agent
    class BT,IPT,ET,BRT,TT,FT,CTT,TTT tool
    class AGT,LLM,STATE,MEMORY,CONDENSER,RUNTIME dependency
```

## Core Components

### CodeActAgent

The primary agent implementation that consolidates LLM actions into a unified code action space.

**Key Features:**
- **Unified Action Space**: Combines conversation and code execution into a single interface
- **Multi-Tool Support**: Integrates bash commands, Python execution, file editing, and web browsing
- **Memory Management**: Uses conversation memory and condensation for efficient context handling
- **Function Calling**: Supports structured tool invocation through LLM function calling

**Core Capabilities:**
1. **Converse**: Natural language communication with users
2. **CodeAct**: Task execution through code (bash commands and Python)
3. **File Operations**: Reading, editing, and managing files
4. **Web Browsing**: Interactive web navigation and content extraction
5. **Task Management**: Planning and tracking task progress

### LocAgent

A specialized variant of CodeActAgent with location-aware capabilities.

**Specializations:**
- Inherits all CodeActAgent functionality
- Uses custom function calling implementation for location-specific operations
- Optimized for tasks requiring spatial or location-based reasoning

### ReadOnlyAgent

A safety-focused variant that restricts operations to read-only tools.

**Safety Features:**
- **Read-Only Operations**: Only allows non-destructive operations
- **Safe Exploration**: Ideal for codebase analysis without modification risk
- **Restricted Tool Set**: Limited to grep, glob, view, think, finish, and web_read tools
- **MCP Tool Restriction**: Explicitly disables MCP tools for additional safety

## Tool System Architecture

```mermaid
graph LR
    subgraph "Tool Categories"
        subgraph "Execution Tools"
            BASH[Bash Command Tool]
            PYTHON[IPython Tool]
        end
        
        subgraph "File Tools"
            EDITOR[String Replace Editor]
            LLMEDITOR[LLM-Based Editor]
        end
        
        subgraph "Navigation Tools"
            BROWSER[Browser Tool]
            TASK[Task Tracker]
        end
        
        subgraph "Communication Tools"
            THINK[Think Tool]
            FINISH[Finish Tool]
            CONDENSE[Condensation Request]
        end
    end
    
    subgraph "Agent Configurations"
        CA_CONFIG[CodeActAgent Config]
        LA_CONFIG[LocAgent Config]
        ROA_CONFIG[ReadOnlyAgent Config]
    end
    
    CA_CONFIG --> BASH
    CA_CONFIG --> PYTHON
    CA_CONFIG --> EDITOR
    CA_CONFIG --> LLMEDITOR
    CA_CONFIG --> BROWSER
    CA_CONFIG --> TASK
    CA_CONFIG --> THINK
    CA_CONFIG --> FINISH
    CA_CONFIG --> CONDENSE
    
    LA_CONFIG --> BASH
    LA_CONFIG --> PYTHON
    LA_CONFIG --> EDITOR
    LA_CONFIG --> BROWSER
    LA_CONFIG --> THINK
    LA_CONFIG --> FINISH
    
    ROA_CONFIG --> THINK
    ROA_CONFIG --> FINISH
    ROA_CONFIG -.-> BROWSER
    
    classDef execution fill:#ffcdd2
    classDef file fill:#c8e6c9
    classDef navigation fill:#bbdefb
    classDef communication fill:#f8bbd9
    classDef config fill:#fff9c4
    
    class BASH,PYTHON execution
    class EDITOR,LLMEDITOR file
    class BROWSER,TASK navigation
    class THINK,FINISH,CONDENSE communication
    class CA_CONFIG,LA_CONFIG,ROA_CONFIG config
```

## Agent Lifecycle and Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant LLM
    participant Tools
    participant Runtime
    participant Memory
    
    User->>Agent: Initial Message
    Agent->>Memory: Process Events
    Memory->>Agent: Condensed History
    Agent->>Agent: Build Messages
    Agent->>LLM: Send Messages + Tools
    LLM->>Agent: Response with Tool Calls
    Agent->>Agent: Parse Response to Actions
    
    loop For Each Action
        Agent->>Tools: Execute Tool
        Tools->>Runtime: Perform Operation
        Runtime->>Tools: Return Result
        Tools->>Agent: Tool Response
        Agent->>Memory: Store Observation
    end
    
    Agent->>User: Final Response
```

## Memory and Context Management

```mermaid
graph TB
    subgraph "Memory System"
        CM[Conversation Memory]
        CONDENSER[Memory Condenser]
        
        subgraph "Memory Operations"
            PROCESS[Process Events]
            CONDENSE[Condense History]
            CACHE[Apply Caching]
        end
    end
    
    subgraph "State Management"
        STATE[Current State]
        HISTORY[Event History]
        METADATA[LLM Metadata]
    end
    
    subgraph "LLM Integration"
        MESSAGES[Message Construction]
        CONTEXT[Context Window Management]
        CACHING[Prompt Caching]
    end
    
    STATE --> CM
    HISTORY --> CONDENSER
    
    CM --> PROCESS
    CONDENSER --> CONDENSE
    CM --> CACHE
    
    PROCESS --> MESSAGES
    CONDENSE --> CONTEXT
    CACHE --> CACHING
    
    MESSAGES --> LLM[LLM Completion]
    CONTEXT --> LLM
    CACHING --> LLM
    
    classDef memory fill:#e8f5e8
    classDef state fill:#fff3e0
    classDef llm fill:#e3f2fd
    
    class CM,CONDENSER,PROCESS,CONDENSE,CACHE memory
    class STATE,HISTORY,METADATA state
    class MESSAGES,CONTEXT,CACHING,LLM llm
```

## Configuration and Customization

### Agent Configuration Options

```mermaid
graph LR
    subgraph "Agent Config"
        SYSTEM[System Prompt]
        TOOLS_CONFIG[Tool Configuration]
        MEMORY_CONFIG[Memory Configuration]
        LLM_CONFIG[LLM Configuration]
    end
    
    subgraph "Tool Toggles"
        CMD[enable_cmd]
        THINK[enable_think]
        FINISH[enable_finish]
        BROWSE[enable_browsing]
        JUPYTER[enable_jupyter]
        PLAN[enable_plan_mode]
        EDITOR[enable_editor]
        LLM_EDITOR[enable_llm_editor]
        CONDENSE[enable_condensation_request]
    end
    
    TOOLS_CONFIG --> CMD
    TOOLS_CONFIG --> THINK
    TOOLS_CONFIG --> FINISH
    TOOLS_CONFIG --> BROWSE
    TOOLS_CONFIG --> JUPYTER
    TOOLS_CONFIG --> PLAN
    TOOLS_CONFIG --> EDITOR
    TOOLS_CONFIG --> LLM_EDITOR
    TOOLS_CONFIG --> CONDENSE
    
    classDef config fill:#f3e5f5
    classDef toggle fill:#e8f5e8
    
    class SYSTEM,TOOLS_CONFIG,MEMORY_CONFIG,LLM_CONFIG config
    class CMD,THINK,FINISH,BROWSE,JUPYTER,PLAN,EDITOR,LLM_EDITOR,CONDENSE toggle
```

## Integration Points

### Dependencies on Other Modules

- **[core_agent_system](core_agent_system.md)**: Base Agent class and state management
- **[llm_integration](llm_integration.md)**: LLM communication and routing
- **[events_and_actions](events_and_actions.md)**: Action and observation handling
- **[runtime_system](runtime_system.md)**: Code execution environment
- **Memory System**: Conversation memory and condensation capabilities

### Runtime Requirements

```mermaid
graph TB
    subgraph "Runtime Dependencies"
        PLUGINS[Sandbox Plugins]
        SKILLS[Agent Skills Requirement]
        JUPYTER[Jupyter Requirement]
    end
    
    subgraph "Platform Support"
        LINUX[Linux Support]
        WINDOWS[Windows Support]
        MACOS[macOS Support]
    end
    
    subgraph "Tool Limitations"
        BROWSE_WIN[Browser Tool - Windows Limited]
        MCP_RO[MCP Tools - ReadOnly Disabled]
    end
    
    PLUGINS --> SKILLS
    PLUGINS --> JUPYTER
    
    LINUX --> BROWSE_WIN
    WINDOWS --> BROWSE_WIN
    
    classDef requirement fill:#ffcdd2
    classDef platform fill:#c8e6c9
    classDef limitation fill:#fff3e0
    
    class PLUGINS,SKILLS,JUPYTER requirement
    class LINUX,WINDOWS,MACOS platform
    class BROWSE_WIN,MCP_RO limitation
```

## Usage Patterns

### CodeActAgent Usage
```python
# Standard usage for general-purpose tasks
agent = CodeActAgent(config, llm_registry)
action = agent.step(state)
```

### LocAgent Usage
```python
# For location-aware tasks
agent = LocAgent(config, llm_registry)
action = agent.step(state)
```

### ReadOnlyAgent Usage
```python
# For safe codebase exploration
agent = ReadOnlyAgent(config, llm_registry)
action = agent.step(state)  # Only read-only operations
```

## Function Calling Architecture

```mermaid
graph TB
    subgraph "Function Calling Flow"
        RESPONSE[LLM Response]
        PARSER[Response Parser]
        ACTIONS[Action List]
        QUEUE[Pending Actions Queue]
    end
    
    subgraph "Tool Execution"
        TOOL_CALL[Tool Call]
        TOOL_EXEC[Tool Execution]
        OBSERVATION[Observation]
    end
    
    subgraph "Agent Variants"
        CA_FC[CodeAct Function Calling]
        LA_FC[Loc Function Calling]
        RO_FC[ReadOnly Function Calling]
    end
    
    RESPONSE --> PARSER
    PARSER --> ACTIONS
    ACTIONS --> QUEUE
    QUEUE --> TOOL_CALL
    TOOL_CALL --> TOOL_EXEC
    TOOL_EXEC --> OBSERVATION
    
    CA_FC --> PARSER
    LA_FC --> PARSER
    RO_FC --> PARSER
    
    classDef flow fill:#e3f2fd
    classDef execution fill:#f3e5f5
    classDef variant fill:#e8f5e8
    
    class RESPONSE,PARSER,ACTIONS,QUEUE flow
    class TOOL_CALL,TOOL_EXEC,OBSERVATION execution
    class CA_FC,LA_FC,RO_FC variant
```

## Error Handling and Safety

### Safety Mechanisms
- **ReadOnlyAgent**: Prevents destructive operations
- **Tool Validation**: Checks tool availability and compatibility
- **Platform Checks**: Validates tool support on current platform
- **MCP Tool Control**: Selective enabling/disabling of external tools

### Error Recovery
- **Pending Actions Queue**: Maintains action continuity across errors
- **State Validation**: Ensures valid conversation state
- **Memory Condensation**: Handles context overflow gracefully

## Performance Considerations

### Memory Optimization
- **Event Condensation**: Reduces memory footprint of long conversations
- **Message Caching**: Optimizes repeated LLM calls
- **Tool Description Optimization**: Adjusts tool descriptions based on LLM model

### Execution Efficiency
- **Pending Actions**: Batches multiple actions for efficient execution
- **Tool Selection**: Dynamic tool loading based on configuration
- **Context Management**: Intelligent context window utilization

## Future Extensions

The CodeAct Agents module is designed for extensibility:

1. **New Agent Types**: Easy addition of specialized agent variants
2. **Tool Integration**: Modular tool system for new capabilities
3. **Memory Strategies**: Pluggable memory and condensation approaches
4. **Platform Support**: Expandable runtime environment support

This module serves as the foundation for intelligent code-aware AI agents that can understand, navigate, and interact with software development environments while maintaining safety and efficiency.