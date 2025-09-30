# Packet Types Module Documentation

## Introduction

The packet-types module defines the core type definitions and interfaces for packet diagrams in Mermaid. Packet diagrams are specialized visualizations used to represent network packet structures, byte layouts, and protocol data units. This module provides the foundational data structures and styling options that enable the creation of detailed packet structure diagrams commonly used in network engineering, protocol analysis, and system documentation.

## Architecture Overview

The packet-types module serves as the type foundation for the packet diagram implementation, providing interfaces for data management, styling configuration, and packet structure representation.

```mermaid
graph TB
    subgraph "packet-types Module"
        PacketDB["PacketDB Interface"]
        PacketData["PacketData Interface"]
        PacketStyleOptions["PacketStyleOptions Interface"]
        PacketBlock["PacketBlock Type"]
        PacketWord["PacketWord Type"]
    end
    
    subgraph "Dependencies"
        Parser["@mermaid-js/parser<br/>Packet Type"]
        Config["PacketDiagramConfig"]
        DiagramDBBase["DiagramDBBase"]
        ArrayElement["ArrayElement Utility"]
    end
    
    PacketDB --> Config
    PacketDB --> DiagramDBBase
    PacketBlock --> Parser
    PacketBlock --> ArrayElement
    PacketWord --> PacketBlock
    PacketData --> PacketWord
    
    style PacketDB fill:#e1f5fe
    style PacketData fill:#e1f5fe
    style PacketStyleOptions fill:#e1f5fe
```

## Core Components

### PacketDB Interface

The `PacketDB` interface extends the base diagram database functionality to provide packet-specific data management capabilities.

```mermaid
classDiagram
    class PacketDB {
        <<interface>>
        +pushWord(word: PacketWord): void
        +getPacket(): PacketWord[]
    }
    
    class DiagramDBBase {
        <<interface>>
        +config: PacketDiagramConfig
    }
    
    PacketDB --|> DiagramDBBase : extends
```

**Key Features:**
- Manages packet word data through `pushWord` method
- Retrieves packet structure via `getPacket` method
- Inherits configuration management from `DiagramDBBase`
- Type-safe integration with Mermaid's diagram system

### PacketData Interface

The `PacketData` interface defines the structure for packet diagram data storage and transmission.

```mermaid
classDiagram
    class PacketData {
        <<interface>>
        +packet: PacketWord[]
    }
    
    class PacketWord {
        <<type>>
        +PacketBlock[]
    }
    
    class PacketBlock {
        <<type>>
        +RecursiveAstOmit
    }
    
    PacketData --> PacketWord : contains
    PacketWord --> PacketBlock : contains
```

### PacketStyleOptions Interface

Comprehensive styling configuration for packet diagrams, providing fine-grained control over visual appearance.

```mermaid
graph LR
    subgraph "PacketStyleOptions"
        A["byteFontSize"]
        B["startByteColor"]
        C["endByteColor"]
        D["labelColor"]
        E["labelFontSize"]
        F["blockStrokeColor"]
        G["blockStrokeWidth"]
        H["blockFillColor"]
        I["titleColor"]
        J["titleFontSize"]
    end
    
    subgraph "Visual Elements"
        A --> K["Byte Labels"]
        B --> L["Start Byte Indicators"]
        C --> M["End Byte Indicators"]
        D --> N["Field Labels"]
        E --> N
        F --> O["Block Borders"]
        G --> O
        H --> P["Block Backgrounds"]
        I --> Q["Diagram Title"]
        J --> Q
    end
```

**Style Properties:**
- **Byte Styling**: `byteFontSize`, `startByteColor`, `endByteColor`
- **Label Styling**: `labelColor`, `labelFontSize`
- **Block Styling**: `blockStrokeColor`, `blockStrokeWidth`, `blockFillColor`
- **Title Styling**: `titleColor`, `titleFontSize`

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Parser as "@mermaid-js/parser"
    participant PacketBlock as "PacketBlock Type"
    participant PacketWord as "PacketWord Type"
    participant PacketDB as "PacketDB"
    participant PacketData as "PacketData"
    
    Parser->>PacketBlock: AST Data
    PacketBlock->>PacketWord: Transform Blocks
    PacketWord->>PacketDB: pushWord()
    PacketDB->>PacketData: getPacket()
    PacketData-->>PacketDB: PacketWord[]
```

## Type Definitions

### PacketBlock
```typescript
export type PacketBlock = RecursiveAstOmit<ArrayElement<Packet['blocks']>>;
```

A type alias that transforms parser AST data into a simplified block representation, removing recursive structures while preserving essential packet field information.

### PacketWord
```typescript
export type PacketWord = Required<PacketBlock>[];
```

Represents a complete packet word as an array of required packet blocks, ensuring all block properties are defined for consistent rendering.

## Integration with Mermaid Ecosystem

```mermaid
graph TB
    subgraph "packet Module"
        PT["packet-types"]
        PDB["packet-db"]
    end
    
    subgraph "Mermaid Core"
        Config["config Module"]
        DiagramAPI["diagram-api Module"]
        Types["types Module"]
    end
    
    subgraph "Parser"
        ParserLib["@mermaid-js/parser"]
    end
    
    PT -.-> Config
    PT -.-> DiagramAPI
    PT -.-> Types
    PT -.-> ParserLib
    PDB -.-> PT
    
    style PT fill:#e3f2fd
    style PDB fill:#e3f2fd
```

## Module Dependencies

### Internal Dependencies
- **config Module**: Provides `PacketDiagramConfig` for diagram-specific configuration
- **diagram-api Module**: Supplies `DiagramDBBase` interface for database operations
- **types Module**: Offers `ArrayElement` utility type for array manipulation

### External Dependencies
- **@mermaid-js/parser**: Supplies the `Packet` AST type and `RecursiveAstOmit` utility for AST transformation

## Usage Patterns

### Data Management Flow
```mermaid
graph LR
    A["Parser Input"] --> B["PacketBlock Creation"]
    B --> C["PacketWord Assembly"]
    C --> D["PacketDB Storage"]
    D --> E["PacketData Retrieval"]
    E --> F["Rendering Engine"]
```

### Styling Configuration Flow
```mermaid
graph TD
    A["User Configuration"] --> B["PacketStyleOptions"]
    B --> C["Renderer"]
    C --> D["Visual Elements"]
    D --> E["Byte Labels"]
    D --> F["Block Styling"]
    D --> G["Title Appearance"]
```

## Related Documentation

- [packet-db.md](packet-db.md) - Database implementation for packet diagrams
- [config.md](config.md) - Configuration system overview
- [diagram-api.md](diagram-api.md) - Diagram API specifications
- [types.md](types.md) - Core type definitions

## Summary

The packet-types module provides the essential type infrastructure for packet diagram functionality in Mermaid. Through its well-defined interfaces and type aliases, it enables type-safe manipulation of packet data structures while maintaining flexibility for various network protocol representations. The comprehensive styling options allow for detailed customization of packet diagram appearance, making it suitable for both technical documentation and educational purposes.