# Event Center Module Documentation

## Introduction

The Event Center module serves as the central event management system within the Muya framework, providing a unified interface for handling both DOM events and custom application events. This module is crucial for maintaining loose coupling between components and enabling efficient event-driven communication throughout the application.

## Core Architecture

### EventCenter Class

The `EventCenter` class is the primary component that manages all event-related operations. It maintains two main data structures:
- `events`: An array tracking DOM event bindings with unique identifiers
- `listeners`: An object storing custom event listeners organized by event name

### Key Responsibilities

1. **DOM Event Management**: Attach, detach, and track DOM event listeners
2. **Custom Event System**: Subscribe, unsubscribe, and dispatch custom application events
3. **Event Lifecycle Management**: Prevent duplicate bindings and manage event cleanup
4. **One-time Event Handling**: Support for single-execution event listeners

## Architecture Diagram

```mermaid
graph TB
    subgraph "Event Center Module"
        EC[EventCenter]
        
        subgraph "DOM Events Management"
            AE[attachDOMEvent]
            DE[detachDOMEvent]
            DAE[detachAllDomEvents]
            CHB[checkHasBind]
        end
        
        subgraph "Custom Events Management"
            SUB[subscribe]
            UNSUB[unsubscribe]
            SUB1[subscribeOnce]
            DIS[dispatch]
            _SUB[_subscribe]
        end
        
        subgraph "Data Structures"
            EVTS[events Array]
            LIS[listeners Object]
            UID[getUniqueId]
        end
    end
    
    EC --> AE
    EC --> DE
    EC --> DAE
    EC --> CHB
    EC --> SUB
    EC --> UNSUB
    EC --> SUB1
    EC --> DIS
    EC --> _SUB
    
    AE --> EVTS
    AE --> UID
    DE --> EVTS
    DAE --> EVTS
    CHB --> EVTS
    
    SUB --> LIS
    UNSUB --> LIS
    SUB1 --> LIS
    DIS --> LIS
    _SUB --> LIS
    
    SUB1 --> _SUB
```

## Component Relationships

```mermaid
graph LR
    subgraph "Muya Framework"
        MUYA[src.muya.lib.index.Muya]
        EC[EventCenter]
        
        subgraph "Event Handlers"
            KE[Keyboard]
            CE[ClickEvent]
            CB[Clipboard]
            DD[DragDrop]
            ME[MouseEvent]
            RS[Resize]
        end
        
        subgraph "Content Management"
            CS[ContentState]
            CT[Content Types]
            CM[Content Manipulation]
        end
    end
    
    MUYA --> EC
    EC --> KE
    EC --> CE
    EC --> CB
    EC --> DD
    EC --> ME
    EC --> RS
    
    KE --> CS
    CE --> CS
    CB --> CS
    DD --> CS
    ME --> CS
    RS --> CS
    
    CS --> CT
    CS --> CM
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant C as Component
    participant EC as EventCenter
    participant DOM as DOM
    participant L as Listener
    
    Note over C,DOM: DOM Event Flow
    C->>EC: attachDOMEvent(target, event, listener)
    EC->>EC: checkHasBind()
    EC->>EC: getUniqueId()
    EC->>EC: Store event info
    EC->>DOM: addEventListener()
    EC-->>C: Return eventId
    
    DOM->>EC: Event triggered
    EC->>L: Execute listener
    
    C->>EC: detachDOMEvent(eventId)
    EC->>DOM: removeEventListener()
    EC->>EC: Remove from events array
    
    Note over C,L: Custom Event Flow
    C->>EC: subscribe(event, listener)
    EC->>EC: Store in listeners object
    
    C->>EC: dispatch(event, data)
    EC->>L: Execute all listeners
    EC->>EC: Remove once listeners
```

## Process Flow

### DOM Event Attachment Process

```mermaid
flowchart TD
    Start([Component requests DOM event binding])
    CheckDuplicate{Check if already bound}
    GenerateID[Generate unique event ID]
    StoreEvent[Store event information]
    AddListener[Call addEventListener]
    ReturnID[Return event ID]
    Skip[Return false]
    
    Start --> CheckDuplicate
    CheckDuplicate -->|Yes| Skip
    CheckDuplicate -->|No| GenerateID
    GenerateID --> StoreEvent
    StoreEvent --> AddListener
    AddListener --> ReturnID
```

### Custom Event Dispatch Process

```mermaid
flowchart TD
    Start([Component dispatches event])
    CheckListeners{Listeners exist?}
    IterateListeners[Iterate through listeners]
    ExecuteListener[Execute listener function]
    CheckOnce{Is once listener?}
    RemoveListener[Remove from listeners]
    Continue{More listeners?}
    End([Event dispatch complete])
    
    Start --> CheckListeners
    CheckListeners -->|No| End
    CheckListeners -->|Yes| IterateListeners
    IterateListeners --> ExecuteListener
    ExecuteListener --> CheckOnce
    CheckOnce -->|Yes| RemoveListener
    CheckOnce -->|No| Continue
    RemoveListener --> Continue
    Continue -->|Yes| IterateListeners
    Continue -->|No| End
```

## API Reference

### DOM Event Methods

#### `attachDOMEvent(target, event, listener, capture)`
Binds a DOM event listener and returns a unique identifier for later removal.

**Parameters:**
- `target`: DOM element to attach the event to
- `event`: Event name (e.g., 'click', 'keydown')
- `listener`: Event handler function
- `capture`: Boolean indicating capture phase

**Returns:** Unique event ID or `false` if already bound

#### `detachDOMEvent(eventId)`
Removes a DOM event listener using the ID returned by `attachDOMEvent`.

**Parameters:**
- `eventId`: Unique identifier returned by `attachDOMEvent`

#### `detachAllDomEvents()`
Removes all DOM event listeners managed by the EventCenter.

#### `checkHasBind(target, event, listener, capture)`
Checks if a specific DOM event binding already exists.

### Custom Event Methods

#### `subscribe(event, listener)`
Subscribes to a custom event.

**Parameters:**
- `event`: Event name
- `listener`: Callback function

#### `subscribeOnce(event, listener)`
Subscribes to a custom event that will be executed only once.

#### `unsubscribe(event, listener)`
Removes a custom event listener.

#### `dispatch(event, ...data)`
Dispatches a custom event to all subscribed listeners.

**Parameters:**
- `event`: Event name
- `...data`: Variable number of arguments passed to listeners

## Integration with Other Modules

The Event Center module integrates with various components throughout the system:

- **[Keyboard System](keyboard_system.md)**: Manages keyboard event bindings and shortcuts
- **[Click Event Handler](click_event_handler.md)**: Handles mouse click events
- **[Clipboard Manager](clipboard_manager.md)**: Manages copy/cut/paste operations
- **[Muya Framework](muya_framework.md)**: Provides the core event infrastructure
- **[Content Management](muya_content.md)**: Enables event-driven content updates

## Usage Examples

### Basic DOM Event Binding
```javascript
const eventCenter = new EventCenter()
const button = document.querySelector('#myButton')

const eventId = eventCenter.attachDOMEvent(
  button, 
  'click', 
  () => console.log('Button clicked!'),
  false
)

// Later, remove the event
eventCenter.detachDOMEvent(eventId)
```

### Custom Event System
```javascript
const eventCenter = new EventCenter()

// Subscribe to custom event
eventCenter.subscribe('contentChanged', (newContent) => {
  console.log('Content updated:', newContent)
})

// Dispatch event
eventCenter.dispatch('contentChanged', 'New markdown content')
```

### One-time Event Listener
```javascript
// Listen only once
eventCenter.subscribeOnce('appReady', () => {
  console.log('Application is ready!')
})

// This will trigger the listener
eventCenter.dispatch('appReady')

// This won't trigger it again
eventCenter.dispatch('appReady')
```

## Best Practices

1. **Always store event IDs**: Keep the IDs returned by `attachDOMEvent` for proper cleanup
2. **Use `detachAllDomEvents()` on cleanup**: Call this when destroying components
3. **Check for duplicates**: The system prevents duplicate bindings automatically
4. **Memory management**: Unsubscribe from custom events when components are destroyed
5. **Event naming**: Use descriptive names for custom events to avoid conflicts

## Error Handling

The Event Center implements defensive programming practices:
- Returns `false` for duplicate DOM event bindings
- Silently handles missing event IDs in `detachDOMEvent`
- Gracefully handles missing listeners in `unsubscribe`
- Prevents memory leaks through proper cleanup methods

## Performance Considerations

- Event lookups are O(n) for DOM events and O(1) for custom events
- The `checkHasBind` method iterates through all bound events
- Custom event dispatch is efficient with direct object property access
- Memory usage scales with the number of bound events and listeners