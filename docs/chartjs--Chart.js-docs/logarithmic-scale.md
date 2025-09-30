# Logarithmic Scale Module

## Introduction

The logarithmic-scale module provides specialized scaling functionality for data visualization, implementing a logarithmic scale that handles data spanning multiple orders of magnitude. This scale type is essential for displaying exponential growth patterns, scientific data, financial charts, and any datasets where values range from very small to very large numbers.

## Architecture Overview

The LogarithmicScale extends the base Scale class and inherits from LinearScaleBase, providing logarithmic transformations for data visualization. The module implements sophisticated tick generation algorithms that create meaningful logarithmic intervals while maintaining visual clarity.

```mermaid
classDiagram
    class Scale {
        <<abstract>>
        +id: string
        +defaults: object
        +min: number
        +max: number
        +options: object
        +parse(raw, index)
        +getPixelForValue(value)
        +getValueForPixel(pixel)
    }
    
    class LinearScaleBase {
        <<abstract>>
        +parse(raw, index)
    }
    
    class LogarithmicScale {
        +id: string
        +defaults: object
        +start: number
        +end: number
        +_startValue: number
        +_valueRange: number
        +_zero: boolean
        +parse(raw, index)
        +determineDataLimits()
        +handleTickRangeOptions()
        +buildTicks()
        +getLabelForValue(value)
        +configure()
        +getPixelForValue(value)
        +getValueForPixel(pixel)
    }
    
    class Ticks {
        <<static>>
        +formatters.logarithmic(value)
    }
    
    Scale <|-- LinearScaleBase : extends
    LinearScaleBase <|-- LogarithmicScale : extends
    LogarithmicScale ..> Ticks : uses
```

## Component Dependencies

The logarithmic-scale module integrates with several core systems:

```mermaid
graph TD
    LS[LogarithmicScale] --> |extends| LSB[LinearScaleBase]
    LS --> |extends| S[Scale]
    LS --> |uses| T[Ticks]
    LS --> |uses| HC[helpers.core]
    LS --> |uses| HI[helpers.intl]
    LS --> |uses| HM[helpers.math]
    
    HC --> |finiteOrDefault| LS
    HI --> |formatNumber| LS
    HM --> |log10| LS
    HM --> |_setMinAndMaxByKey| LS
    
    subgraph "Core Systems"
        S
        T
    end
    
    subgraph "Helper Functions"
        HC
        HI
        HM
    end
```

## Core Functionality

### Data Parsing and Validation

The LogarithmicScale implements specialized parsing logic to handle logarithmic data requirements:

```javascript
parse(raw, index) {
    const value = LinearScaleBase.prototype.parse.apply(this, [raw, index]);
    if (value === 0) {
        this._zero = true;
        return undefined;
    }
    return isFinite(value) && value > 0 ? value : null;
}
```

**Key behaviors:**
- Zero values are flagged and converted to `undefined` (logarithm of zero is undefined)
- Only positive finite values are accepted (logarithm requires positive numbers)
- Invalid values return `null` for proper handling

### Tick Generation Algorithm

The module implements a sophisticated tick generation system that creates meaningful logarithmic intervals:

```mermaid
flowchart TD
    Start[Start Tick Generation] --> GetRange[Get Data Range]
    GetRange --> CalcExp[Calculate Exponent Range]
    CalcExp --> GenTicks[Generate Ticks]
    GenTicks --> CheckMajor[Check Major Ticks]
    CheckMajor --> AdjustRange[Adjust Scale Range]
    AdjustRange --> ReturnTicks[Return Ticks Array]
    
    GenTicks --> Loop{Value < Max?}
    Loop -->|Yes| AddTick[Add Tick to Array]
    AddTick --> IncSig[Increment Significand]
    IncSig --> CheckSig{Significand >= 20?}
    CheckSig -->|Yes| IncExp[Increment Exponent]
    IncExp --> ResetSig[Reset Significand]
    ResetSig --> CalcValue[Calculate New Value]
    CalcValue --> Loop
    CheckSig -->|No| CalcValue
    Loop -->|No| AddLast[Add Final Tick]
    AddLast --> ReturnTicks
```

### Scale Configuration

The logarithmic scale configures itself based on data characteristics:

```javascript
configure() {
    const start = this.min;
    super.configure();
    this._startValue = log10(start);
    this._valueRange = log10(this.max) - log10(start);
}
```

This establishes the logarithmic baseline for pixel-to-value conversions.

## Data Flow

### Value-to-Pixel Conversion

```mermaid
sequenceDiagram
    participant Chart
    participant LogScale as LogarithmicScale
    participant PixelCalc as Pixel Calculator
    
    Chart->>LogScale: getPixelForValue(value)
    LogScale->>LogScale: Check if value is 0/undefined
    LogScale->>LogScale: Apply logarithmic transformation
    LogScale->>LogScale: Calculate decimal position
    LogScale->>PixelCalc: Convert decimal to pixel
    PixelCalc-->>Chart: Return pixel position
```

### Pixel-to-Value Conversion

```mermaid
sequenceDiagram
    participant Chart
    participant LogScale as LogarithmicScale
    participant MathCalc as Math Calculator
    
    Chart->>LogScale: getValueForPixel(pixel)
    LogScale->>LogScale: Convert pixel to decimal
    LogScale->>MathCalc: Apply inverse logarithmic transformation
    MathCalc-->>Chart: Return actual value
```

## Integration with Chart System

The LogarithmicScale integrates with the broader chart ecosystem through several key interfaces:

```mermaid
graph LR
    subgraph "Chart System"
        CC[Chart Configuration]
        DC[Dataset Controller]
        EL[Element Layer]
    end
    
    subgraph "Logarithmic Scale"
        LS[LogarithmicScale]
        TG[Tick Generator]
        LC[Label Formatter]
    end
    
    CC --> |scale options| LS
    DC --> |data limits| LS
    LS --> |pixel positions| EL
    LS --> |tick values| TG
    TG --> |formatted labels| LC
    LC --> |display labels| EL
```

## Key Features

### 1. Automatic Range Handling
- Handles zero and negative values gracefully
- Automatically adjusts range based on data distribution
- Supports `beginAtZero` option for special cases

### 2. Intelligent Tick Generation
- Creates logarithmically spaced ticks (1, 2, 3, ..., 10, 20, 30, ..., 100, etc.)
- Identifies major ticks (powers of 10) for emphasis
- Adapts tick density based on scale range

### 3. Internationalization Support
- Uses `formatNumber` helper for locale-aware number formatting
- Supports custom formatting through options

### 4. Flexible Bounds Handling
- Supports different bound modes ('ticks', 'data')
- Handles reversed scales
- Maintains consistent behavior across different data ranges

## Usage Patterns

### Basic Configuration
```javascript
{
    type: 'logarithmic',
    ticks: {
        callback: function(value) {
            return value.toExponential();
        }
    }
}
```

### Scientific Data Visualization
The logarithmic scale excels at displaying:
- Exponential growth/decay data
- Data spanning multiple orders of magnitude
- Scientific measurements (pH, decibels, earthquake magnitudes)
- Financial data (stock prices, market caps)

## Error Handling

The module implements robust error handling for edge cases:

1. **Zero Values**: Converted to `undefined` since log(0) is mathematically undefined
2. **Negative Values**: Return `null` to prevent logarithm of negative numbers
3. **Infinite Values**: Filtered out during data limit determination
4. **Empty Datasets**: Default to reasonable ranges (1-10)

## Performance Considerations

- Tick generation algorithm is optimized for large data ranges
- Uses mathematical operations sparingly in hot paths
- Caches calculated values where possible
- Efficiently handles both small and large datasets

## Related Modules

- [linear-scale](linear-scale.md) - Linear scaling implementation
- [scale-system](scale-system.md) - Base scale functionality
- [core.ticks](core.ticks.md) - Tick formatting utilities
- [helpers.math](helpers.math.md) - Mathematical utility functions

## API Reference

### Constructor Options
- `min`: Minimum scale value
- `max`: Maximum scale value
- `beginAtZero`: Force scale to start at zero (special handling)
- `ticks.callback`: Custom tick formatting function
- `ticks.major.enabled`: Enable major tick emphasis

### Methods
- `parse(raw, index)`: Parse and validate data values
- `determineDataLimits()`: Calculate scale range from data
- `buildTicks()`: Generate logarithmic tick marks
- `getPixelForValue(value)`: Convert data value to pixel position
- `getValueForPixel(pixel)`: Convert pixel position to data value
- `getLabelForValue(value)`: Format value for display