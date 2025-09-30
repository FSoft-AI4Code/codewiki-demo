# Optimizer Module Documentation

## Introduction

The optimizer module is the core component of StarRocks' SQL query optimization engine. It transforms parsed SQL statements into efficient execution plans by applying cost-based optimization techniques, rule-based transformations, and statistical analysis. The module serves as the bridge between the SQL parser/analyzer and the query execution engine, ensuring optimal query performance across distributed environments.

## Architecture Overview

```mermaid
graph TB
    subgraph "SQL Processing Pipeline"
        Parser[SQL Parser] --> Analyzer[SQL Analyzer]
        Analyzer --> Optimizer[Optimizer Module]
        Optimizer --> Planner[Plan Fragment Builder]
        Planner --> Execution[Query Execution]
    end
    
    subgraph "Optimizer Core Components"
        OptimizerFactory[OptimizerFactory] --> OptExpression[OptExpression Builder]
        OptExpression --> RuleEngine[Transformation Rules]
        RuleEngine --> CostModel[Cost Model]
        CostModel --> Statistics[Statistics Engine]
        Statistics --> PlanSelector[Plan Selector]
    end
    
    subgraph "Supporting Systems"
        Catalog[Catalog Manager] --> Statistics
        StatisticsCollector[Statistics Collector] --> Statistics
        MV[Rewrite Engine] --> RuleEngine
        JoinReorder[Join Reorder] --> RuleEngine
    end
```

## Core Components

### 1. Optimizer Factory and Expression Building

The optimizer module provides a factory pattern for creating optimizer instances and building logical expressions:

```mermaid
classDiagram
    class OptimizerFactory {
        +createOptimizer(): Optimizer
        +createCascadesOptimizer(): CascadesOptimizer
        +createRuleBasedOptimizer(): RuleBasedOptimizer
    }
    
    class OptExpression {
        +Builder: OptExpressionBuilder
        +build(): OptExpression
        +addChild(OptExpression)
        +setProperty(Property)
    }
    
    class OptExpressionBuilder {
        +setOperator(Operator)
        +addInput(OptExpression)
        +setStatistics(Statistics)
        +build(): OptExpression
    }
    
    OptimizerFactory --> OptExpression : creates
    OptExpression --> OptExpressionBuilder : uses
```

**Key Components:**
- `OptimizerFactory.OptimizerFactory`: Creates appropriate optimizer instances based on query characteristics
- `OptExpression.Builder`: Builds logical expression trees representing query operations
- `PropertyDeriverBase.PropertyDeriverBase`: Derives properties for logical expressions

### 2. Cost Model and Statistics

The cost model evaluates different execution strategies using statistical information:

```mermaid
graph LR
    subgraph "Statistics Components"
        Statistics[Statistics Engine] --> ColumnStats[Column Statistics]
        Statistics --> ExprStats[Expression Statistics]
        Statistics --> PredStats[Predicate Statistics]
        
        ColumnStats --> Builder[ColumnStatistic.Builder]
        ExprStats --> ExprCalc[ExpressionStatisticCalculator]
        PredStats --> PredCalc[PredicateStatisticsCalculator]
    end
    
    subgraph "Cost Model"
        CostModel[CostModel] --> BinaryCalc[BinaryPredicateStatisticCalculator]
        CostModel --> Statistics
        CostModel --> PlanCost[Plan Cost Calculation]
    end
```

**Key Components:**
- `CostModel.CostModel`: Main cost evaluation engine for execution plans
- `Statistics.Statistics`: Statistical information about data distribution
- `ColumnStatistic.Builder`: Builder for column-level statistics
- `BinaryPredicateStatisticCalculator.BinaryPredicateStatisticCalculator`: Calculates statistics for binary predicates
- `ExpressionStatisticCalculator.ExpressionStatisticCalculator`: Computes statistics for expressions
- `PredicateStatisticsCalculator.PredicateStatisticsCalculator`: Evaluates predicate selectivity

### 3. Operator System

The operator system defines logical and physical operators for query representation:

```mermaid
classDiagram
    class OperatorBuilderFactory {
        +createLogicalBuilder(): LogicalOperatorBuilder
        +createPhysicalBuilder(): PhysicalOperatorBuilder
    }
    
    class OperatorVisitor {
        +visitLogicalScan(): R
        +visitPhysicalHashJoin(): R
        +visitLogicalAggregation(): R
        +visitPhysicalSort(): R
    }
    
    class ColumnFilterConverter {
        +convertToColumnFilter(): ColumnFilter
        +convertFromPredicate(): ScalarOperator
    }
    
    OperatorBuilderFactory --> OperatorVisitor : uses
    ColumnFilterConverter --> OperatorVisitor : interacts
```

**Key Components:**
- `OperatorBuilderFactory.OperatorBuilderFactory`: Creates builders for different operator types
- `OperatorVisitor.OperatorVisitor`: Visitor pattern for operator traversal and processing
- `ColumnFilterConverter.ColumnFilterConverter`: Converts between different filter representations

### 4. Rule-Based Optimization

Transformation rules optimize logical plans through pattern matching and rewriting:

```mermaid
graph TD
    subgraph "Rule Categories"
        JoinReorder[Join Reorder Rules] --> JoinReorderFactory[JoinReorderFactory]
        MVRewrite[Materialized View Rewrite] --> MVRewriter[MaterializedViewRewriter]
        CTEOpt[CTE Optimization] --> CTEUtils[CTEUtils]
        SubqueryOpt[Subquery Optimization] --> SubqueryUtils[SubqueryUtils]
    end
    
    subgraph "Rule Engine"
        RuleEngine[Rule Engine] --> PatternMatch[Pattern Matching]
        RuleEngine --> Transformation[Transformation]
        RuleEngine --> CostEval[Cost Evaluation]
    end
    
    JoinReorderFactory --> RuleEngine
    MVRewriter --> RuleEngine
    CTEUtils --> RuleEngine
    SubqueryUtils --> RuleEngine
```

**Key Components:**
- `JoinReorderFactory.JoinReorderFactory`: Manages join reordering strategies
- `MaterializedViewRewriter.MaterializedViewRewriter`: Rewrites queries using materialized views
- `CTEUtils.CTEUtils`: Optimizes Common Table Expressions
- `SubqueryUtils.SubqueryUtils`: Handles subquery optimization
- `ConstantOperatorUtils.ConstantOperatorUtils`: Manages constant folding and propagation

### 5. Plan Enumeration and Selection

The optimizer explores the plan space and selects the optimal execution strategy:

```mermaid
graph LR
    subgraph "Plan Enumeration"
        EnumeratePlan[EnumeratePlan] --> PlanSpace[Plan Space Exploration]
        PlanSpace --> Memo[Memo Structure]
        Memo --> Winner[Winner Selection]
    end
    
    subgraph "Plan Validation"
        PlanValidator[PlanValidator.Checker] --> PropertyCheck[Property Validation]
        PlanValidator --> CostCheck[Cost Validation]
        PlanValidator --> CorrectnessCheck[Correctness Validation]
    end
    
    Winner --> PlanValidator
```

**Key Components:**
- `EnumeratePlan.EnumeratePlan`: Systematically explores the plan space
- `PlanValidator.Checker`: Validates generated execution plans
- `TaskContext.TaskContext`: Provides context for optimization tasks

### 6. Utility Components

Supporting utilities for optimization processes:

```mermaid
graph LR
    subgraph "Utilities"
        TraceUtil[OptimizerTraceUtil] --> Debug[Debug Support]
        LogicalPrinter[LogicalPlanPrinter] --> Visualization[Plan Visualization]
        WindowTransformer[WindowTransformer] --> WindowOpt[Window Optimization]
        MVUtils[MVUtils] --> MVHelper[Materialized View Helpers]
    end
```

**Key Components:**
- `OptimizerTraceUtil.OptimizerTraceUtil`: Provides optimization tracing and debugging
- `LogicalPlanPrinter.LogicalPlanPrinter`: Prints logical plans for analysis
- `WindowTransformer.WindowTransformer`: Optimizes window functions
- `MVUtils.MVUtils`: Utilities for materialized view optimization

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Parser as SQL Parser
    participant Analyzer as SQL Analyzer
    participant Optimizer as Optimizer Module
    participant Catalog as Catalog
    participant Stats as Statistics
    participant Planner as Plan Fragment Builder
    
    Parser->>Analyzer: Parsed AST
    Analyzer->>Optimizer: Analyzed Query
    Optimizer->>Catalog: Request Metadata
    Catalog-->>Optimizer: Table/Column Info
    Optimizer->>Stats: Request Statistics
    Stats-->>Optimizer: Column Statistics
    
    loop Optimization Iterations
        Optimizer->>Optimizer: Apply Transformation Rules
        Optimizer->>Optimizer: Calculate Costs
        Optimizer->>Optimizer: Update Best Plan
    end
    
    Optimizer->>Planner: Optimal Logical Plan
    Planner->>Planner: Convert to Physical Plan
    Planner-->>Optimizer: Execution Plan
```

## Integration with Other Modules

### 1. Parser and Analyzer Integration

The optimizer receives analyzed query structures from the [parser](parser.md) and [analyzer](analyzer.md) modules:

- **Input**: Logical query representation with resolved tables, columns, and expressions
- **Output**: Optimized logical plan ready for physical planning
- **Coordination**: Shares expression contexts and metadata with analyzer components

### 2. Statistics Integration

Deep integration with the [statistics](statistics.md) module for cost-based decisions:

```mermaid
graph LR
    subgraph "Statistics Flow"
        StatsCollector[Statistics Collector] --> StatsCache[Statistics Cache]
        StatsCache --> Optimizer[Optimizer]
        Optimizer --> StatsUpdater[Statistics Updater]
    end
```

### 3. Catalog Integration

Relies on [catalog](catalog.md) for metadata and schema information:

- Table structure and partitioning information
- Index and constraint definitions
- Data distribution and storage format details

### 4. Execution Integration

Interfaces with [query execution](query_execution.md) through the planner:

```mermaid
graph TD
    Optimizer --> LogicalPlan[Logical Plan]
    LogicalPlan --> PlanFragmentBuilder[Plan Fragment Builder]
    PlanFragmentBuilder --> PhysicalPlan[Physical Plan]
    PhysicalPlan --> ExecutionEngine[Execution Engine]
```

## Optimization Process Flow

```mermaid
graph TD
    Start[Start Optimization] --> Init[Initialize Optimizer]
    Init --> Parse[Parse Input Plan]
    Parse --> Validate[Validate Plan Structure]
    
    Validate --> RuleBased[Apply Rule-Based Optimizations]
    RuleBased --> CostBased[Apply Cost-Based Optimizations]
    
    CostBased --> JoinOpt[Optimize Join Order]
    JoinOpt --> MVRewrite[Rewrite with MVs]
    MVRewrite --> SubqueryOpt[Optimize Subqueries]
    SubqueryOpt --> CTFOpt[Optimize CTEs]
    
    CTFOpt --> PropertyDerive[Derive Properties]
    PropertyDerive --> CostCalc[Calculate Costs]
    CostCalc --> PlanSelect[Select Best Plan]
    
    PlanSelect --> ValidateFinal[Validate Final Plan]
    ValidateFinal --> Output[Output Optimized Plan]
```

## Key Features

### 1. Cost-Based Optimization
- Sophisticated cost model considering CPU, memory, and I/O costs
- Statistical analysis for cardinality estimation
- Adaptive optimization based on runtime feedback

### 2. Rule-Based Transformation
- Extensive set of transformation rules
- Pattern matching for plan optimization
- Heuristic optimizations for common patterns

### 3. Advanced Join Optimization
- Multi-table join reordering
- Bushy tree exploration
- Join algorithm selection based on data characteristics

### 4. Materialized View Rewrite
- Automatic query rewriting using materialized views
- Partial and complete rewrite capabilities
- Incremental maintenance support

### 5. Distributed Optimization
- Partition-aware optimization
- Network cost consideration
- Parallel execution planning

## Performance Considerations

### 1. Optimization Time vs. Execution Time
- Configurable optimization timeout
- Progressive optimization for complex queries
- Plan caching for repeated queries

### 2. Memory Management
- Bounded memory usage during optimization
- Efficient data structures for plan representation
- Garbage collection optimization

### 3. Concurrency
- Thread-safe optimization for concurrent queries
- Resource isolation between optimization tasks
- Priority-based optimization scheduling

## Configuration and Tuning

### 1. Optimization Levels
- **Rule-based only**: Fast optimization for simple queries
- **Cost-based**: Full optimization with statistics
- **Adaptive**: Runtime feedback integration

### 2. Statistics Management
- Automatic statistics collection
- Manual statistics update
- Statistics approximation for large datasets

### 3. Rule Configuration
- Enable/disable specific transformation rules
- Rule priority configuration
- Custom rule development support

## Monitoring and Debugging

### 1. Optimization Tracing
- Detailed optimization step logging
- Plan transformation visualization
- Cost calculation debugging

### 2. Performance Metrics
- Optimization time tracking
- Plan quality assessment
- Rule effectiveness analysis

### 3. Troubleshooting Tools
- Plan comparison utilities
- Statistics validation tools
- Optimization hint system

## Future Enhancements

### 1. Machine Learning Integration
- ML-based cardinality estimation
- Adaptive cost model tuning
- Query performance prediction

### 2. Advanced Optimization Techniques
- Genetic algorithms for complex queries
- Simulated annealing for plan exploration
- Reinforcement learning for optimization decisions

### 3. Cloud-Native Optimization
- Serverless optimization capabilities
- Elastic resource utilization
- Multi-cloud optimization strategies

## References

- [Parser Module](parser.md) - SQL parsing and initial AST generation
- [Analyzer Module](analyzer.md) - Semantic analysis and query validation
- [Statistics Module](statistics.md) - Statistical information management
- [Catalog Module](catalog.md) - Metadata and schema management
- [Query Execution](query_execution.md) - Physical plan execution
- [Planner Module](planner.md) - Physical plan generation