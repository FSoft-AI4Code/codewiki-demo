# Window Aggregate Functions Module

## Introduction

The `aggregate_functions_window` module provides the core implementation of window functions in StarRocks, a distributed MPP (Massively Parallel Processing) database system. Window functions are analytical functions that perform calculations across a set of table rows related to the current row, enabling advanced analytical queries without the need for self-joins or subqueries.

This module is responsible for registering and managing all window-specific aggregate functions, including ranking functions, value functions, and analytical functions that operate over ordered partitions of data.

## Architecture Overview

### Module Position in System Architecture

```mermaid
graph TB
    subgraph "Query Execution Layer"
        SQL[SQL Parser]
        OPT[Query Optimizer]
        EXEC[Query Executor]
    end
    
    subgraph "Expression System"
        AGG_RES[Aggregate Resolver]
        WIN_RES[Window Resolver]
        EXPR_EVAL[Expression Evaluator]
    end
    
    subgraph "Storage Engine"
        SCAN[Table Scanner]
        SORT[Sorting Engine]
        PART[Partition Manager]
    end
    
    SQL --> OPT
    OPT --> EXEC
    EXEC --> AGG_RES
    AGG_RES --> WIN_RES
    WIN_RES --> EXPR_EVAL
    EXPR_EVAL --> SCAN
    SCAN --> SORT
    SORT --> PART
    
    style WIN_RES fill:#f9f,stroke:#333,stroke-width:4px
```

### Window Function Architecture

```mermaid
graph LR
    subgraph "Window Function Registration"
        WD[WindowDispatcher]
        AFR[AggregateFuncResolver]
        AF[AggregateFactory]
    end
    
    subgraph "Window Function Types"
        RANK[Ranking Functions<br/>rank, dense_rank, row_number]
        VALUE[Value Functions<br/>first_value, last_value, lead, lag]
        ANALYTIC[Analytic Functions<br/>cume_dist, percent_rank, ntile]
    end
    
    subgraph "Execution Context"
        FRAME[Window Frame]
        PARTITION[Partition By]
        ORDER[Order By]
    end
    
    WD --> AFR
    AFR --> AF
    AF --> RANK
    AF --> VALUE
    AF --> ANALYTIC
    
    RANK --> FRAME
    VALUE --> FRAME
    ANALYTIC --> FRAME
    
    FRAME --> PARTITION
    FRAME --> ORDER
```

## Core Components

### WindowDispatcher

The `WindowDispatcher` is a template-based function dispatcher that registers window functions for different data types. It uses compile-time type dispatching to generate optimized implementations for each supported logical type.

**Key Responsibilities:**
- Type-specific window function registration
- Template-based code generation for performance
- Support for aggregate-compatible types and object types
- Conditional compilation for type safety

**Supported Functions:**
- `first_value` / `first_value_in` (with ignore nulls)
- `last_value` / `last_value_in` (with ignore nulls)
- `lead` / `lead_in` (with ignore nulls)
- `lag` / `lag_in` (with ignore nulls)

### AggregateFuncResolver

The `AggregateFuncResolver` manages the registration and resolution of all aggregate functions, including window functions. It maintains a registry mapping function names to their implementations.

**Registration Process:**
```cpp
void register_window() {
    // Register type-specific window functions
    for (auto type : aggregate_types()) {
        type_dispatch_all(type, WindowDispatcher(), this);
    }
    
    // Register ranking and analytic functions
    add_aggregate_mapping_notnull<TYPE_BIGINT, TYPE_BIGINT>("rank", true, 
        AggregateFactory::MakeRankWindowFunction());
    // ... additional registrations
}
```

## Window Function Categories

### 1. Ranking Functions

```mermaid
graph TD
    subgraph "Ranking Functions"
        RANK[rank - Rank with gaps]
        DENSE_RANK[dense_rank - Rank without gaps]
        ROW_NUM[row_number - Sequential numbering]
        CUME_DIST[cume_dist - Cumulative distribution]
        PERCENT_RANK[percent_rank - Percentage rank]
        NTILE[ntile - Bucket division]
    end
    
    subgraph "Use Cases"
        TOP_N[Top-N Queries]
        PAGINATION[Result Pagination]
        PERCENTILE[Percentile Analysis]
        BUCKETING[Data Bucketing]
    end
    
    RANK --> TOP_N
    DENSE_RANK --> TOP_N
    ROW_NUM --> PAGINATION
    CUME_DIST --> PERCENTILE
    PERCENT_RANK --> PERCENTILE
    NTILE --> BUCKETING
```

**Implementation Details:**
- All ranking functions return `TYPE_BIGINT` or `TYPE_DOUBLE`
- Operate over the entire partition without frame specification
- Maintain ordering state during execution
- Support `ORDER BY` clause for ranking criteria

### 2. Value Functions

**First/Last Value Functions:**
- `first_value(column)` - First value in the window frame
- `first_value_in(column)` - First non-null value
- `last_value(column)` - Last value in the window frame
- `last_value_in(column)` - Last non-null value

**Lead/Lag Functions:**
- `lead(column, offset, default)` - Access subsequent rows
- `lag(column, offset, default)` - Access preceding rows
- Support for ignore nulls variants (`lead_in`, `lag_in`)

### 3. Analytic Functions

**Advanced Analytics:**
- `cume_dist()` - Cumulative distribution (0,1]
- `percent_rank()` - Relative rank percentage [0,1)
- `ntile(n)` - Divide into n buckets
- `session_number()` - Session identification

## Data Flow Architecture

### Query Processing Pipeline

```mermaid
sequenceDiagram
    participant SQL_Parser
    participant Optimizer
    participant Plan_Builder
    participant Executor
    participant Window_Functions
    participant Storage
    
    SQL_Parser->>Optimizer: Parse window function query
    Optimizer->>Plan_Builder: Generate execution plan
    Plan_Builder->>Executor: Create window operator
    Executor->>Storage: Scan partitioned data
    Storage-->>Executor: Return ordered partitions
    Executor->>Window_Functions: Apply window functions
    Window_Functions->>Window_Functions: Calculate frame boundaries
    Window_Functions->>Window_Functions: Compute function results
    Window_Functions-->>Executor: Return computed values
    Executor-->>SQL_Parser: Return final results
```

### Window Frame Processing

```mermaid
graph LR
    subgraph "Input Data"
        PARTITIONED[Partitioned Rows]
        ORDERED[Ordered within Partition]
    end
    
    subgraph "Frame Calculation"
        FRAME_DEF[Frame Definition]
        FRAME_BOUND[Boundary Calculation]
        FRAME_ROWS[Row Selection]
    end
    
    subgraph "Function Application"
        FUNC_SEL[Function Selection]
        STATE_INIT[State Initialization]
        COMPUTE[Value Computation]
    end
    
    PARTITIONED --> ORDERED
    ORDERED --> FRAME_DEF
    FRAME_DEF --> FRAME_BOUND
    FRAME_BOUND --> FRAME_ROWS
    FRAME_ROWS --> FUNC_SEL
    FUNC_SEL --> STATE_INIT
    STATE_INIT --> COMPUTE
```

## Integration with Other Modules

### Dependency Relationships

```mermaid
graph TB
    subgraph "Window Functions Module"
        WIN[aggregate_functions_window]
    end
    
    subgraph "Expression System"
        EXPR[expression_system]
        AGG[aggregate_functions]
    end
    
    subgraph "Type System"
        TYPE[type_system]
        LOGICAL[logical_type]
    end
    
    subgraph "Query Execution"
        EXEC[query_execution]
        SORT[sorting]
    end
    
    WIN --> EXPR
    WIN --> AGG
    WIN --> TYPE
    WIN --> LOGICAL
    WIN --> EXEC
    WIN --> SORT
    
    style WIN fill:#f9f,stroke:#333,stroke-width:4px
```

### Key Dependencies

1. **[expression_system](expression_system.md)**: Provides base expression evaluation framework
2. **[aggregate_functions](aggregate_functions.md)**: Supplies aggregate function implementations
3. **[type_system](type_system.md)**: Defines data type mappings and conversions
4. **[logical_type](logical_type.md)**: Provides type dispatch infrastructure
5. **[query_execution](query_execution.md)**: Integrates with execution pipeline
6. **[sorting](sorting.md)**: Handles ordering requirements for window functions

## Performance Considerations

### Optimization Strategies

1. **Template-Based Code Generation**: Uses C++ templates to generate type-specific implementations at compile time, eliminating runtime type dispatch overhead.

2. **Vectorized Execution**: Operates on columnar data in batches for better CPU cache utilization and SIMD instruction usage.

3. **Memory Management**: Efficient state management for window frames to minimize memory allocations during execution.

4. **Partition Pruning**: Leverages partition information to reduce the data volume processed by window functions.

### Execution Complexity

| Function Type | Time Complexity | Space Complexity | Description |
|---------------|-----------------|------------------|-------------|
| Ranking | O(n log n) | O(n) | Requires sorting within partitions |
| First/Last Value | O(n) | O(1) | Single pass with frame tracking |
| Lead/Lag | O(n) | O(k) | k = maximum offset value |
| Analytic | O(n) | O(1) | Single pass with state maintenance |

## Usage Examples

### Basic Window Functions

```sql
-- Ranking functions
SELECT 
    employee_id,
    department_id,
    salary,
    RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as salary_rank,
    DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as dense_rank,
    ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC) as row_num
FROM employees;

-- Value functions
SELECT 
    employee_id,
    department_id,
    salary,
    FIRST_VALUE(salary) OVER (PARTITION BY department_id ORDER BY hire_date) as first_salary,
    LAST_VALUE(salary) OVER (PARTITION BY department_id ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_salary,
    LAG(salary, 1) OVER (PARTITION BY department_id ORDER BY hire_date) as prev_salary,
    LEAD(salary, 1) OVER (PARTITION BY department_id ORDER BY hire_date) as next_salary
FROM employees;

-- Analytic functions
SELECT 
    employee_id,
    department_id,
    salary,
    CUME_DIST() OVER (PARTITION BY department_id ORDER BY salary) as salary_percentile,
    PERCENT_RANK() OVER (PARTITION BY department_id ORDER BY salary) as percent_rank,
    NTILE(4) OVER (PARTITION BY department_id ORDER BY salary) as salary_quartile
FROM employees;
```

### Advanced Window Frame Specifications

```sql
-- Moving average with frame specification
SELECT 
    date,
    revenue,
    AVG(revenue) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as seven_day_avg
FROM daily_revenue;

-- Session-based analysis
SELECT 
    user_id,
    event_time,
    SESSION_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) as session_id
FROM user_events;
```

## Error Handling and Edge Cases

### Null Value Handling

- Window functions respect SQL standard null handling
- `first_value_in` and `last_value_in` variants ignore null values
- Ranking functions treat nulls according to `ORDER BY` clause specification

### Frame Boundary Conditions

- Empty frames return null for value functions
- Single-row partitions handle ranking functions correctly
- Offset functions (lead/lag) return null for out-of-bound access

### Type Compatibility

- Window functions support all aggregate-compatible types
- Type-specific optimizations for primitive types
- Object type support for complex data types (JSON, ARRAY, MAP)

## Future Enhancements

### Planned Features

1. **Additional Window Functions**: Support for more analytical functions like `ratio_to_report`, `stddev` variants
2. **Performance Optimizations**: Enhanced vectorization and parallel execution strategies
3. **Frame Extensions**: Support for more complex frame specifications (RANGE with intervals)
4. **Memory Optimization**: Improved memory management for large window frames

### Integration Opportunities

1. **Materialized Views**: Integration with [materialized_views](materialized_views.md) for pre-computed window function results
2. **Query Optimization**: Enhanced cost-based optimization for window function queries
3. **Distributed Execution**: Improved distributed window function execution strategies

## References

- [Expression System](expression_system.md) - Base expression evaluation framework
- [Aggregate Functions](aggregate_functions.md) - General aggregate function implementations
- [Type System](type_system.md) - Data type management and conversions
- [Query Execution](query_execution.md) - Query execution pipeline integration
- [Sorting](sorting.md) - Ordering and sorting infrastructure