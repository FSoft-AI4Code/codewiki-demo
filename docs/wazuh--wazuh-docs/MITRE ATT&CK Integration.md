# MITRE ATT&CK Integration

The MITRE ATT&CK Integration module provides a comprehensive framework for querying and retrieving information from the Wazuh database related to the MITRE ATT&CK framework. This module allows users to explore relationships between different ATT&CK entities, such as techniques, tactics, mitigations, groups, and software.

## Architecture

The module is designed around a set of specialized classes that inherit from a common base class, `WazuhDBQueryMitre`. This base class extends the functionality of the [Core Framework's](Core-Framework.md) `WazuhDBQuery` to interact with the Wazuh database using a MITRE-specific query format.

```mermaid
graph TD
    A[WazuhDBQuery] --> B(WazuhDBQueryMitre);
    B --> C{WazuhDBQueryMitreRelational};
    B --> D[WazuhDBQueryMitreMetadata];
    B --> E[WazuhDBQueryMitreReferences];
    B --> F[WazuhDBQueryMitreTactics];
    B --> G[WazuhDBQueryMitreTechniques];
    B --> H[WazuhDBQueryMitreMitigations];
    B --> I[WazuhDBQueryMitreGroups];
    B --> J[WazuhDBQueryMitreSoftware];
    C --> K[WazuhDBQueryMitreRelationalPhase];
    C --> L[WazuhDBQueryMitreRelationalMitigate];
    C --> M[WazuhDBQueryMitreRelationalUse];
```

### Component Interaction

The following diagram illustrates how the different components interact to retrieve and format MITRE ATT&CK data.

```mermaid
sequenceDiagram
    participant User
    participant API
    participant WazuhDBQueryMitreSubclass
    participant WazuhDBQueryMitreRelationalSubclass
    participant WazuhDBBackend

    User->>API: Request MITRE data (e.g., techniques)
    API->>WazuhDBQueryMitreSubclass: Instantiate and run query
    WazuhDBQueryMitreSubclass->>WazuhDBBackend: Execute main query
    WazuhDBBackend-->>WazuhDBQueryMitreSubclass: Return main data
    WazuhDBQueryMitreSubclass->>WazuhDBQueryMitreRelationalSubclass: Instantiate and run relational queries
    WazuhDBQueryMitreRelationalSubclass->>WazuhDBBackend: Execute relational queries
    WazuhDBBackend-->>WazuhDBQueryMitreRelationalSubclass: Return relational data
    WazuhDBQueryMitreRelationalSubclass-->>WazuhDBQueryMitreSubclass: Return formatted relational data
    WazuhDBQueryMitreSubclass-->>API: Return combined data
    API-->>User: Return MITRE data
```

## Core Components

The module is composed of the following core components:

### `WazuhDBQueryMitre`

This is the base class for all MITRE-related database queries. It inherits from `WazuhDBQuery` and configures the `WazuhDBBackend` to use the `mitre` query format. It also introduces the concept of `relation_fields`, which are fields that are not directly in the database but are computed based on relationships between different MITRE entities.

### `WazuhDBQueryMitreRelational`

This abstract class is the base for handling many-to-many relationships between MITRE entities. It provides a common interface for querying and formatting relational data.

- **`WazuhDBQueryMitreRelationalPhase`**:  Handles the relationship between techniques and tactics.
- **`WazuhDBQueryMitreRelationalMitigate`**: Handles the relationship between techniques and mitigations.
- **`WazuhDBQueryMitreRelationalUse`**: Handles the relationship between techniques, groups, and software.

### Main Entity Query Classes

These classes are responsible for querying the main MITRE entities. They use the relational query classes to fetch and embed related information.

- **`WazuhDBQueryMitreTactics`**: Queries MITRE tactics and their related techniques and references.
- **`WazuhDBQueryMitreTechniques`**: Queries MITRE techniques and their related tactics, mitigations, software, groups, and references.
- **`WazuhDBQueryMitreMitigations`**: Queries MITRE mitigations and their related techniques and references.
- **`WazuhDBQueryMitreGroups`**: Queries MITRE groups and their related software, techniques, and references.
- **`WazuhDBQueryMitreSoftware`**: Queries MITRE software and their related groups, techniques, and references.

### Other Components

- **`WazuhDBQueryMitreMetadata`**: Queries metadata about the MITRE ATT&CK data in the database.
- **`WazuhDBQueryMitreReferences`**: Queries the references associated with MITRE entities.

## Data Flow

The following diagram shows the data flow when a user requests information about MITRE techniques.

```mermaid
graph TD
    subgraph User Request
        A[GET /mitre/techniques]
    end

    subgraph API Layer
        B[API Endpoint] --> C{WazuhDBQueryMitreTechniques};
    end

    subgraph Database Query
        C -->|Main Query| D[technique table];
        C -->|Relational Queries| E[WazuhDBQueryMitreRelationalPhase];
        C -->|Relational Queries| F[WazuhDBQueryMitreRelationalMitigate];
        C -->|Relational Queries| G[WazuhDBQueryMitreRelationalUse];
        C -->|Relational Queries| H[WazuhDBQueryMitreReferences];
    end

    subgraph Database
        E --> I[phase table];
        F --> J[mitigate table];
        G --> K[use table];
        H --> L[reference table];
    end

    subgraph Response Generation
        M{Data Aggregation} --> N[Formatted JSON Response];
        D --> M;
        I --> M;
        J --> M;
        K --> M;
        L --> M;
    end

    A --> B;
    C --> M;
    N --> A;
```

## External Dependencies

- **[Core Framework](Core-Framework.md)**: The MITRE ATT&CK Integration module relies on the `WazuhDBQuery` and `WazuhDBBackend` classes from the Core Framework to interact with the Wazuh database.
