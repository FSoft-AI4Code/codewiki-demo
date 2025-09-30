# Packet Database Module Documentation

## Introduction

The packet-db module is a core component of the Mermaid diagramming library that provides database functionality for packet diagrams. Packet diagrams are specialized visualizations used to represent data packet structures, bit fields, and protocol specifications in networking and communication systems.

This module implements the `PacketDB` class which serves as the central data store and configuration manager for packet diagram rendering, following Mermaid's standard diagram database pattern.

## Architecture Overview

The packet-db module is part of the larger packet diagram ecosystem within Mermaid. It implements the `DiagramDB` interface and integrates with the common diagram database utilities while providing packet-specific data management capabilities.

```mermaid
graph TB
    subgraph "Packet Module Ecosystem"
        PB[PacketDB]
        PT[Packet Types]
        PS[Packet Style]
    end
    
    subgraph "Core Mermaid Infrastructure"
        DB[DiagramDB Interface]
        CC[Common Config]
        CD[Common DB]
        DC[Diagram Config]
    end
    
    PB -.->|implements| DB
    PB -.->|uses| CC
    PB -.->|extends| CD
    PB -.->|configures| DC
    
    PT -.->|defines| PB
    PS -.->|styles| PB
```

## Core Components

### PacketDB Class

The `PacketDB` class is the primary component of this module, implementing the `DiagramDB` interface to provide packet diagram-specific functionality.

```mermaid
classDiagram
    class PacketDB {
        -packet: PacketWord[]
        +getConfig(): PacketDiagramConfig
        +getPacket(): PacketWord[]
        +pushWord(word: PacketWord): void
        +clear(): void
        +setAccTitle(title: string): void
        +getAccTitle(): string
        +setDiagramTitle(title: string): void
        +getDiagramTitle(): string
        +getAccDescription(): string
        +setAccDescription(description: string): void
    }
    
    class DiagramDB {
        <<interface>>
    }
    
    class CommonDB {
        <<utility functions>>
    }
    
    PacketDB ..|> DiagramDB : implements
    PacketDB ..> CommonDB : uses
```

## Data Flow Architecture

The packet database follows a standard data flow pattern within the Mermaid ecosystem:

```mermaid
sequenceDiagram
    participant Parser
    participant PacketDB
    participant Config
    participant Renderer
    
    Parser->>PacketDB: pushWord(packetWord)
    Parser->>PacketDB: setDiagramTitle(title)
    Parser->>PacketDB: setAccDescription(desc)
    
    Renderer->>PacketDB: getPacket()
    Renderer->>PacketDB: getConfig()
    Renderer->>PacketDB: getDiagramTitle()
    Renderer->>PacketDB: getAccDescription()
    
    PacketDB->>Config: getConfig()
    Config-->>PacketDB: PacketDiagramConfig
    
    PacketDB-->>Renderer: packet data & config
```

## Component Relationships

The packet-db module integrates with several other Mermaid components:

```mermaid
graph LR
    subgraph "Packet Diagram Components"
        PDB[PacketDB]
        PT[Packet Types]
        PC[Packet Config]
    end
    
    subgraph "Mermaid Core"
        DBI[DiagramDB Interface]
        CC[Common Config]
        CD[Common DB]
        DC[Default Config]
    end
    
    subgraph "External Dependencies"
        UTIL[Utils]
    end
    
    PDB -->|implements| DBI
    PDB -->|uses| CC
    PDB -->|extends| CD
    PDB -->|loads| DC
    PDB -->|calls| UTIL
    
    PT -->|defines data| PDB
    PC -->|configures| PDB
```

## Configuration Management

The PacketDB module manages configuration through a hierarchical system:

```mermaid
graph TD
    DC[Default Config]
    CC[Common Config] 
    PC[Packet Config]
    FC[Final Config]
    PDB[PacketDB]
    
    DC -.->|base| FC
    CC -.->|override| FC
    PC -.->|specific| FC
    
    PDB --> FC
```

The configuration system:
1. Starts with `DEFAULT_CONFIG.packet` as the base configuration
2. Merges with common configuration from `commonGetConfig().packet`
3. Applies packet-specific adjustments (e.g., padding for bit display)
4. Returns the final merged configuration

## Data Management

### Packet Word Storage

The PacketDB maintains an array of `PacketWord` objects, which represent individual data segments within a packet structure. Each word contains information about bit fields, labels, and formatting.

### Common Database Integration

The module integrates with Mermaid's common database utilities for:
- Diagram title management
- Accessibility title and description handling
- Standard cleanup operations

## Process Flow

```mermaid
flowchart TD
    Start([Initialize])
    Config[Load Configuration]
    Parse[Parse Packet Words]
    Store[Store in Packet Array]
    Title[Set Diagram Title]
    Desc[Set Accessibility Description]
    Render[Render Request]
    GetData[Retrieve Packet Data]
    GetConfig[Retrieve Configuration]
    End([Render Complete])
    
    Start --> Config
    Config --> Parse
    Parse --> Store
    Store --> Title
    Title --> Desc
    Desc --> Render
    Render --> GetData
    Render --> GetConfig
    GetData --> End
    GetConfig --> End
```

## Integration Points

### With Parser
The parser calls `pushWord()` to add parsed packet segments to the database.

### With Renderer
The renderer calls `getPacket()` to retrieve the complete packet structure and `getConfig()` for rendering configuration.

### With Configuration System
Integrates with Mermaid's configuration system to provide diagram-specific settings while inheriting common configuration options.

## Key Features

1. **Type Safety**: Implements the `DiagramDB` interface ensuring consistency across diagram types
2. **Configuration Management**: Hierarchical configuration system with defaults and overrides
3. **Data Validation**: Filters out empty packet words during storage
4. **Accessibility Support**: Full support for accessibility titles and descriptions
5. **Standard Compliance**: Follows Mermaid's common database patterns and utilities

## Dependencies

- **Internal**: `config.js`, `defaultConfig.js`, `diagram-api/types.js`, `utils.js`, `common/commonDb.js`
- **External**: TypeScript type definitions for configuration and data structures

## Related Documentation

- [packet-types.md](packet-types.md) - Packet data type definitions
- [config.md](config.md) - Configuration system documentation
- [diagram-api.md](diagram-api.md) - Diagram API interface specifications
- [common-db.md](common-db.md) - Common database utilities

## Usage Example

```typescript
import { PacketDB } from './packet/db.js';

const packetDB = new PacketDB();

// Add packet words
packetDB.pushWord({ text: 'Header', bits: 8 });
packetDB.pushWord({ text: 'Data', bits: 16 });

// Set metadata
packetDB.setDiagramTitle('Network Packet Structure');
packetDB.setAccDescription('Ethernet packet with header and data fields');

// Get configuration
const config = packetDB.getConfig();

// Retrieve data for rendering
const packetData = packetDB.getPacket();
```