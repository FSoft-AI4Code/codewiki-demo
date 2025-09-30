# helpers.collection Module Documentation

## Overview

The `helpers.collection` module provides essential utility functions for array manipulation, binary search operations, and array event listening. This module serves as a foundational component in the Chart.js ecosystem, offering efficient data structure operations that are critical for chart data processing and management.

## Purpose and Core Functionality

The module specializes in three main areas:

1. **Binary Search Operations**: Efficient searching in sorted arrays and objects
2. **Array Event Listening**: Reactive array manipulation with event hooks
3. **Array Utilities**: Common array operations like filtering and deduplication

These utilities are particularly important for handling large datasets in charts, where performance is crucial for smooth user interactions and real-time data updates.

## Architecture

### Component Structure

```mermaid
graph TD
    A[helpers.collection Module] --> B[Binary Search Functions]
    A --> C[Array Event System]
    A --> D[Utility Functions]
    
    B --> B1[_lookup]
    B --> B2[_lookupByKey]
    B --> B3[_rlookupByKey]
    
    C --> C1[ArrayListener Interface]
    C --> C2[listenArrayEvents]
    C --> C3[unlistenArrayEvents]
    
    D --> D1[_filterBetween]
    D --> D2[_arrayUnique]
```

### Dependencies

```mermaid
graph LR
    A[helpers.collection] --> B[helpers.core]
    B --> C[_capitalize function]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
```

The module depends on the [`helpers.core`](helpers.core.md) module for the `_capitalize` function, which is used to transform method names for the array event system.

## Core Components

### ArrayListener Interface

The `ArrayListener` interface defines the contract for objects that want to listen to array manipulation events:

```typescript
interface ArrayListener<T> {
  _onDataPush?(...item: T[]): void;
  _onDataPop?(): void;
  _onDataShift?(): void;
  _onDataSplice?(index: number, deleteCount: number, ...items: T[]): void;
  _onDataUnshift?(...item: T[]): void;
}
```

### Binary Search Functions

#### `_lookup`
Performs binary search on sorted arrays with customizable comparison function.

#### `_lookupByKey`
Searches objects in an array by a specific key value, useful for finding data points in chart datasets.

#### `_rlookupByKey`
Reverse binary search for finding the rightmost occurrence of a value.

### Array Event System

#### `listenArrayEvents`
Hooks into array mutation methods (`push`, `pop`, `shift`, `splice`, `unshift`) and notifies listeners after modifications. This is crucial for reactive chart updates when data changes.

#### `unlistenArrayEvents`
Removes event listeners and cleans up attached properties when no listeners remain.

## Data Flow

### Array Event Flow

```mermaid
sequenceDiagram
    participant Array
    participant EventSystem
    participant Listener
    participant Chart
    
    Array->>EventSystem: push(item)
    EventSystem->>EventSystem: Execute original push
    EventSystem->>Listener: _onDataPush(item)
    Listener->>Chart: Update visualization
    EventSystem->>Array: Return result
```

### Binary Search Flow

```mermaid
flowchart TD
    A[Start Search] --> B{Array Empty?}
    B -->|Yes| C[Return null]
    B -->|No| D[Calculate Midpoint]
    D --> E{Compare Value}
    E -->|Less| F[Search Left Half]
    E -->|Greater| G[Search Right Half]
    E -->|Equal| H[Return Index Range]
    F --> D
    G --> D
```

## Integration with Chart.js Ecosystem

### Relationship to Core Components

```mermaid
graph TB
    A[helpers.collection] --> B[DatasetController]
    A --> C[Scale]
    A --> D[Animation System]
    
    B --> E[Data Processing]
    C --> F[Tick Calculation]
    D --> G[Data Animation]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
```

The collection helpers are used throughout the Chart.js system:

- **[`DatasetController`](core.md#dataset-controller)**: Uses binary search for efficient data point lookup during rendering and interaction
- **[`Scale`](core.md#scale-system)**: Utilizes `_filterBetween` for determining visible data ranges
- **[Animation System](core.md#animation-system)**: Leverages array events for reactive data updates during animations

### Usage in Data Processing

```mermaid
graph LR
    A[Raw Data] --> B[Array Events]
    B --> C[Data Processing]
    C --> D[Binary Search]
    D --> E[Filtered Data]
    E --> F[Chart Rendering]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#9f9,stroke:#333,stroke-width:2px
```

## Process Flows

### Data Update with Array Events

```mermaid
flowchart TD
    A[User Updates Data] --> B[Array Method Called]
    B --> C[Hooked Method Executes]
    C --> D[Original Operation Performed]
    D --> E[Event Notification Sent]
    E --> F[Chart Components Notified]
    F --> G[Chart Re-renders]
    G --> H[Animation Triggered]
```

### Efficient Data Lookup

```mermaid
flowchart TD
    A[Chart Interaction] --> B[Get Mouse Position]
    B --> C[Convert to Data Coordinate]
    C --> D[Binary Search for Nearest Point]
    D --> E[Return Data Index]
    E --> F[Highlight Data Point]
```

## Performance Considerations

### Binary Search Optimization
- O(log n) time complexity for data lookup
- Essential for large datasets (thousands of points)
- Reduces rendering time for data-intensive charts

### Array Event System
- Minimal overhead when no listeners attached
- Only hooks methods when listeners are present
- Automatic cleanup prevents memory leaks

### Memory Management
- `_arrayUnique` uses Set for efficient deduplication
- Event listeners are properly cleaned up
- No circular references in hooked arrays

## Best Practices

### When to Use Binary Search
- Sorted data arrays
- Frequent lookup operations
- Large datasets where O(n) is prohibitive

### Array Event Usage
- Listen to data changes for reactive updates
- Always unlisten when component is destroyed
- Use for coordinating multiple chart components

### Performance Tips
- Use `_filterBetween` for viewport-based rendering
- Implement `_arrayUnique` before processing duplicate data
- Consider array event overhead for high-frequency updates

## Related Documentation

- [`helpers.core`](helpers.core.md) - Core utility functions including string manipulation
- [`core.datasetController`](core.md#dataset-controller) - Uses collection helpers for data management
- [`core.scale`](core.md#scale-system) - Leverages binary search for tick calculation
- [`core.animation`](core.md#animation-system) - Integrates with array events for smooth transitions

## API Reference

### Functions

#### `_lookup(table, value, cmp?)`
Performs binary search on a sorted array.

**Parameters:**
- `table`: Sorted array to search
- `value`: Value to find
- `cmp`: Optional comparison function

**Returns:** Object with `lo` and `hi` indices

#### `_lookupByKey(table, key, value, last?)`
Searches objects by key value.

**Parameters:**
- `table`: Array of objects
- `key`: Property name to search by
- `value`: Value to find
- `last`: Whether to find last occurrence

**Returns:** Object with `lo` and `hi` indices

#### `listenArrayEvents(array, listener)`
Hooks array methods for event notification.

**Parameters:**
- `array`: Array to hook
- `listener`: Object implementing ArrayListener interface

#### `unlistenArrayEvents(array, listener)`
Removes array event hooks.

**Parameters:**
- `array`: Array with hooks
- `listener`: Listener to remove

#### `_filterBetween(values, min, max)`
Filters array to values within range.

**Parameters:**
- `values`: Sorted array
- `min`: Minimum value
- `max`: Maximum value

**Returns:** Filtered array

#### `_arrayUnique(items)`
Removes duplicates from array.

**Parameters:**
- `items`: Array with potential duplicates

**Returns:** Array with unique values