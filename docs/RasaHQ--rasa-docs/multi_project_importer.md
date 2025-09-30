# Multi-Project Importer Module

## Introduction

The Multi-Project Importer module provides a sophisticated data aggregation system for Rasa that enables importing and merging training data from multiple projects or directories. This module is particularly useful for organizations managing multiple conversational AI projects that need to share common training data, domain definitions, or configuration settings.

## Core Purpose

The `MultiProjectImporter` serves as a centralized data aggregation mechanism that:
- Imports training data from multiple project directories
- Merges domain definitions across projects
- Aggregates NLU training data and conversation stories
- Supports hierarchical project structures with import dependencies
- Enables code reuse and modular training data organization

## Architecture Overview

```mermaid
graph TB
    subgraph "MultiProjectImporter Architecture"
        MP[MultiProjectImporter]
        
        subgraph "Data Sources"
            CONFIG[Config Files]
            DOMAIN[Domain Files]
            NLU[NLU Data Files]
            STORIES[Story Files]
            E2E[End-to-End Test Files]
        end
        
        subgraph "Processing Pipeline"
            INIT[_init_from_path]
            DICT[_init_from_dict]
            DIR[_init_from_directory]
            FILE[_init_from_file]
        end
        
        subgraph "Data Aggregation"
            DOMAIN_MERGE[Domain Merger]
            STORY_AGG[Story Aggregator]
            NLU_AGG[NLU Data Aggregator]
        end
        
        CONFIG --> INIT
        INIT --> DICT
        INIT --> DIR
        INIT --> FILE
        
        DOMAIN --> DOMAIN_MERGE
        STORIES --> STORY_AGG
        NLU --> NLU_AGG
        E2E --> STORY_AGG
        
        DOMAIN_MERGE --> MP
        STORY_AGG --> MP
        NLU_AGG --> MP
    end
```

## Component Details

### MultiProjectImporter Class

The `MultiProjectImporter` extends `TrainingDataImporter` and implements a recursive import mechanism that processes project hierarchies through configuration-based imports.

#### Key Attributes

```mermaid
classDiagram
    class MultiProjectImporter {
        -config: Dict[Text, Any]
        -_domain_paths: List[Text]
        -_story_paths: List[Text]
        -_e2e_story_paths: List[Text]
        -_nlu_paths: List[Text]
        -_imports: List[Text]
        -_additional_paths: List[Text]
        -_project_directory: Text
        +__init__(config_file, domain_path, training_data_paths, project_directory)
        +get_domain() Domain
        +get_stories(exclusion_percentage) StoryGraph
        +get_conversation_tests() StoryGraph
        +get_config() Dict
        +get_nlu_data(language) TrainingData
        +training_paths() Set[Text]
        +is_imported(path) bool
    }
```

#### Initialization Process

```mermaid
sequenceDiagram
    participant Client
    participant MPI as MultiProjectImporter
    participant Config as Config Reader
    participant PathProcessor as Path Processor
    participant DataCollector as Data Collector
    
    Client->>MPI: __init__(config_file, ...)
    MPI->>Config: read_model_configuration(config_file)
    Config-->>MPI: config dict
    
    MPI->>MPI: _init_from_dict(config, project_directory)
    loop For each import path
        MPI->>PathProcessor: _init_from_path(import_path)
        alt is file
            PathProcessor->>MPI: _init_from_file(path)
            MPI->>Config: read_config_file(path)
        else is directory
            PathProcessor->>MPI: _init_from_directory(path)
            MPI->>DataCollector: walk directory tree
        end
    end
    
    MPI->>DataCollector: get_data_files(training_data_paths)
    DataCollector-->>MPI: categorized file paths
    MPI-->>Client: initialized importer
```

## Data Import Flow

### Import Resolution Algorithm

```mermaid
flowchart TD
    Start([Start Import Process])
    ReadConfig[Read Configuration File]
    ExtractImports[Extract Import Directives]
    ProcessEachImport{For Each Import}
    
    IsFile{Is File?}
    IsDirectory{Is Directory?}
    
    ReadConfigFile[Read Config File]
    ProcessDirectory[Process Directory Tree]
    
    CheckFileType{File Type}
    DomainFile[Domain File]
    NLUFile[NLU File]
    StoryFile[Story File]
    E2EFile[End-to-End File]
    ConfigFile[Config File]
    
    AddToPaths[Add to Appropriate Path Lists]
    RecurseProcess[Process Nested Imports]
    
    Start --> ReadConfig
    ReadConfig --> ExtractImports
    ExtractImports --> ProcessEachImport
    
    ProcessEachImport --> IsFile
    IsFile -->|Yes| ReadConfigFile
    IsFile -->|No| IsDirectory
    IsDirectory -->|Yes| ProcessDirectory
    
    ReadConfigFile --> CheckFileType
    ProcessDirectory --> CheckFileType
    
    CheckFileType --> DomainFile
    CheckFileType --> NLUFile
    CheckFileType --> StoryFile
    CheckFileType --> E2EFile
    CheckFileType --> ConfigFile
    
    DomainFile --> AddToPaths
    NLUFile --> AddToPaths
    StoryFile --> AddToPaths
    E2EFile --> AddToPaths
    ConfigFile --> RecurseProcess
    
    AddToPaths --> ProcessEachImport
    RecurseProcess --> ProcessEachImport
```

### Path Resolution Logic

```mermaid
graph LR
    subgraph "Path Resolution Hierarchy"
        PATH[Input Path]
        
        subgraph "Resolution Checks"
            NO_SKILLS{no_skills_selected?}
            IN_PROJECT{_is_in_project_directory?}
            IN_ADDITIONAL{_is_in_additional_paths?}
            IN_IMPORTED{_is_in_imported_paths?}
        end
        
        RESULT[Import Decision]
    end
    
    PATH --> NO_SKILLS
    NO_SKILLS -->|True| RESULT
    NO_SKILLS -->|False| IN_PROJECT
    IN_PROJECT -->|True| RESULT
    IN_PROJECT -->|False| IN_ADDITIONAL
    IN_ADDITIONAL -->|True| RESULT
    IN_ADDITIONAL -->|False| IN_IMPORTED
    IN_IMPORTED --> RESULT
```

## Data Aggregation Methods

### Domain Merging

```mermaid
sequenceDiagram
    participant Importer as MultiProjectImporter
    participant DomainLoader as Domain Loader
    participant Merger as Domain Merger
    
    Importer->>Importer: get_domain()
    loop For each domain path
        Importer->>DomainLoader: Domain.load(path)
        DomainLoader-->>Importer: Domain object
    end
    
    Importer->>Merger: reduce(merge, domains, empty_domain)
    Merger-->>Importer: Merged Domain
```

### Story and NLU Data Aggregation

The module uses utility functions from `rasa.shared.importers.utils` to aggregate story graphs and NLU training data from multiple file paths:

- **Stories**: `utils.story_graph_from_paths()` merges story files while handling exclusions
- **NLU Data**: `utils.training_data_from_paths()` combines NLU training data from multiple sources
- **Conversation Tests**: Separate aggregation for end-to-end test stories

## Integration with Rasa Ecosystem

### Relationship to Other Importers

```mermaid
graph TB
    subgraph "Importer Hierarchy"
        TDI[TrainingDataImporter]
        
        subgraph "Concrete Implementations"
            MPI[MultiProjectImporter]
            RFI[RasaFileImporter]
            CSI[CombinedDataImporter]
            E2E[E2EImporter]
            NSI[NluDataImporter]
        end
        
        subgraph "Utility Importers"
            RSI[ResponsesSyncImporter]
        end
    end
    
    TDI --> MPI
    TDI --> RFI
    TDI --> CSI
    TDI --> E2E
    TDI --> NSI
    TDI --> RSI
```

### Dependencies on Core Components

The MultiProjectImporter integrates with several core Rasa modules:

- **[shared_core](shared_core.md)**: Uses `Domain`, `StoryGraph`, and event structures
- **[shared_nlu](shared_nlu.md)**: Handles `TrainingData` and `Message` objects
- **[data_importers](data_importers.md)**: Extends base `TrainingDataImporter` interface

## Configuration Format

### Import Configuration Structure

```yaml
# config.yml
imports:
  - ../common_project
  - ./sub_project
  - /absolute/path/to/shared/data

# Other Rasa configuration...
pipeline:
  # NLU pipeline configuration
  
policies:
  # Core policies configuration
```

### Project Structure Example

```
main_project/
├── config.yml          # Main configuration with imports
├── domain.yml          # Main domain definition
├── data/
│   ├── nlu.yml        # Main NLU data
│   └── stories.yml    # Main stories
└── imports/
    ├── common/        # Imported common project
    │   ├── config.yml
    │   ├── domain.yml
    │   └── data/
    └── shared/        # Another imported project
        ├── domain.yml
        └── data/
```

## Usage Patterns

### Basic Multi-Project Setup

```python
from rasa.shared.importers.multi_project import MultiProjectImporter

# Initialize importer with main config
importer = MultiProjectImporter(
    config_file="config.yml",
    domain_path="domain.yml",
    training_data_paths=["data/"],
    project_directory="."
)

# Get aggregated data
domain = importer.get_domain()
stories = importer.get_stories()
nlu_data = importer.get_nlu_data()
config = importer.get_config()
```

### Advanced Configuration with Nested Imports

The importer supports deeply nested project structures where imported projects can themselves import other projects, creating a dependency graph of training data sources.

## Error Handling and Validation

### Import Validation

The module includes several validation mechanisms:

- **File Existence**: Validates that imported paths exist
- **Config File Validation**: Ensures imported files are valid Rasa configuration files
- **Circular Import Prevention**: Prevents infinite recursion through import tracking
- **Path Resolution**: Handles relative and absolute path resolution correctly

### Warning System

The module uses Rasa's warning system to alert users about:
- Missing import paths
- Invalid configuration files
- Experimental feature usage (marked with `@mark_as_experimental_feature`)

## Performance Considerations

### File System Operations

- Uses `os.walk()` with `followlinks=True` for directory traversal
- Implements path caching to avoid redundant file system checks
- Processes imports recursively but with cycle detection

### Memory Management

- Loads domain files on-demand during `get_domain()` calls
- Aggregates data incrementally rather than loading everything upfront
- Uses generator patterns where possible for large datasets

## Extension Points

### Custom Importers

Developers can extend the multi-project import functionality by:

1. **Subclassing MultiProjectImporter**: Override specific methods for custom behavior
2. **Implementing TrainingDataImporter**: Create completely custom importers
3. **Using CombinedDataImporter**: Chain multiple importers together

### Integration with Training Pipeline

The importer integrates seamlessly with Rasa's training pipeline through the [engine_graph](engine_graph.md) module, where it can be used as a data provider component.

## Best Practices

### Project Organization

1. **Hierarchical Structure**: Organize projects in a clear hierarchy
2. **Common Data Separation**: Keep shared data in separate, imported projects
3. **Configuration Management**: Use consistent configuration across projects
4. **Version Control**: Track imported projects as dependencies

### Performance Optimization

1. **Selective Imports**: Only import necessary projects to reduce loading time
2. **Data Caching**: Consider caching aggregated results for large projects
3. **Incremental Updates**: Use file modification tracking for efficient updates

## Troubleshooting

### Common Issues

1. **Import Loops**: Check for circular import dependencies
2. **Path Resolution**: Verify relative vs absolute path usage
3. **File Permissions**: Ensure read access to all imported paths
4. **Configuration Validation**: Validate YAML syntax in config files

### Debugging

Enable debug logging to trace import resolution:

```python
import logging
logging.getLogger('rasa.shared.importers.multi_project').setLevel(logging.DEBUG)
```

This provides detailed information about:
- Selected projects and import paths
- File discovery and categorization
- Domain merging process
- Path resolution decisions