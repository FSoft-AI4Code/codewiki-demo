# Metadata Module Documentation

## Introduction

The metadata module provides a comprehensive type system for defining and validating structured data types used throughout the application. It serves as the foundation for data serialization, configuration management, and inter-component communication by offering strongly-typed metadata definitions with built-in validation and C++ type mapping capabilities.

## Architecture Overview

The metadata module implements a hierarchical type system with the following key architectural components:

### Core Type Hierarchy

```mermaid
classDiagram
    class Type {
        <<abstract>>
        -c_type_override: str
        -val: any
        +set_val(val: any)
        +c_type(): str
        +get_type_typ_enum(): str
        +is_struct(): bool
        +is_array(): bool
    }
    
    class Bool {
        +c_type_class: "bool"
        +type_enum: "TYPE_BOOL"
        +is_valid_val(val: any): bool
    }
    
    class NumericType {
        <<abstract>>
    }
    
    class U16 {
        +c_type_class: "uint16_t"
        +type_enum: "TYPE_U16"
        +is_valid_val(val: any): bool
    }
    
    class U32 {
        +c_type_class: "uint32_t"
        +type_enum: "TYPE_U32"
        +is_valid_val(val: any): bool
    }
    
    class U64 {
        +c_type_class: "uint64_t"
        +type_enum: "TYPE_U64"
        +is_valid_val(val: any): bool
    }
    
    class I32 {
        +c_type_class: "int32_t"
        +type_enum: "TYPE_I32"
        +is_valid_val(val: any): bool
    }
    
    class Float {
        +c_type_class: "float"
        +type_enum: "TYPE_FLOAT"
        +is_valid_val(val: any): bool
    }
    
    class Color {
        +type_enum: "TYPE_COLOR"
    }
    
    class String {
        +c_type_class: "const char *"
        +type_enum: "TYPE_STR"
        +is_valid_val(val: any): bool
    }
    
    class WString {
        +c_type_class: "const WCHAR *"
        +type_enum: "TYPE_WSTR"
        +is_valid_val(val: any): bool
    }
    
    class Struct {
        <<abstract>>
        +c_type_class: ""
        +type_enum: "TYPE_STRUCT_PTR"
        +fields: list
        +values: list
        +name(): str
        +as_str(): str
    }
    
    class Array {
        +c_type_class: ""
        +type_enum: "TYPE_ARRAY"
        +typ: Type
        +values: list
        +name(): str
    }
    
    Type <|-- Bool
    Type <|-- NumericType
    Type <|-- String
    Type <|-- WString
    Type <|-- Float
    Type <|-- Struct
    Type <|-- Array
    NumericType <|-- U16
    NumericType <|-- U32
    NumericType <|-- U64
    NumericType <|-- I32
    U32 <|-- Color
```

### Field System Architecture

```mermaid
classDiagram
    class Field {
        -name: str
        -typ: Type
        -flags: int
        -val: any
        +c_type(): str
        +is_struct(): bool
        +is_signed(): bool
        +is_unsigned(): bool
        +is_bool(): bool
        +is_color(): bool
        +is_string(): bool
        +is_float(): bool
        +is_no_store(): bool
        +is_compact(): bool
        +is_array(): bool
        +set_val(val: any)
        +get_typ_enum(for_bin: bool): str
    }
    
    class Type {
        <<abstract>>
    }
    
    class ValidationFunctions {
        <<static>>
        +is_valid_signed(bits: int, val: any): bool
        +is_valid_unsigned(bits: int, val: any): bool
        +is_valid_string(val: any): bool
    }
    
    Field --> Type : contains
    Field ..> ValidationFunctions : uses
```

## Component Details

### Base Type System

#### Type Class
The abstract base class for all metadata types provides:
- **Value validation**: Ensures type safety through `is_valid_val()` method
- **C++ type mapping**: Maps Python types to corresponding C++ types via `c_type()`
- **Type enumeration**: Provides runtime type information through `get_type_typ_enum()`
- **Structure/array detection**: Helper methods for composite types

#### Primitive Types

**Bool Type**
- Maps to C++ `bool` type
- Validates boolean values (True/False only)
- Used for configuration flags and binary settings

**Numeric Types**
- **U16**: 16-bit unsigned integer (`uint16_t`)
- **U32**: 32-bit unsigned integer (`uint32_t`)
- **U64**: 64-bit unsigned integer (`uint64_t`)
- **I32**: 32-bit signed integer (`int32_t`)
- **Float**: Single-precision floating point (`float`)

Each numeric type includes range validation appropriate to its bit width and signedness.

**String Types**
- **String**: C-style string (`const char *`)
- **WString**: Wide string (`const WCHAR *`)
- Both accept None, str, and unicode types

**Color Type**
- Inherits from U32 but uses distinct type enum (`TYPE_COLOR`)
- Represents RGBA color values as 32-bit unsigned integers
- Provides semantic distinction from regular integers

### Composite Types

#### Struct Type
Abstract base class for user-defined structures:
- **Field definition**: Uses class-level `fields` list to define structure members
- **Type safety**: Validates field values during assignment
- **C++ mapping**: Generates appropriate pointer types (`StructName *`)
- **Reflection**: Provides runtime access to field information

#### Array Type
Container for homogeneous collections:
- **Struct-only restriction**: Currently supports only arrays of Struct types
- **Type validation**: Ensures all elements match the specified type
- **C++ mapping**: Maps to `Vec<StructName*> *` for efficient memory management

### Field System

The Field class provides metadata about individual data members:

#### Storage Flags
- **NoStore (1)**: Excludes field from serialization/storage
- **Compact (2)**: Enables compact binary storage format
- **Mutual exclusion**: NoStore and Compact flags are mutually exclusive

#### Type Introspection
Fields provide comprehensive type information:
- **Primitive detection**: `is_bool()`, `is_string()`, `is_float()`
- **Numeric classification**: `is_signed()`, `is_unsigned()`
- **Composite detection**: `is_struct()`, `is_array()`
- **Storage behavior**: `is_no_store()`, `is_compact()`

## Data Flow

```mermaid
flowchart TD
    A[User Code] -->|Define| B[Struct Definition]
    B --> C[Field Definitions]
    C -->|Validate| D[Type Validation]
    D -->|Success| E[Create Instance]
    D -->|Failure| F[Validation Error]
    E -->|Set Value| G[Field Assignment]
    G -->|Validate| H[Type Check]
    H -->|Success| I[Store Value]
    H -->|Failure| J[Assignment Error]
    I -->|Generate| K[C++ Type Info]
    K -->|Export| L[Code Generation]
    
    subgraph "Validation Layer"
        D
        H
        F
        J
    end
    
    subgraph "Type System"
        B
        C
        G
        I
    end
    
    subgraph "Code Generation"
        K
        L
    end
```

## Integration with Other Modules

The metadata module serves as a foundational component that other modules depend on for type-safe data handling:

### Upstream Dependencies
- **Utils Module**: Uses metadata types for configuration and data validation
- **UI Components**: Employs metadata for form validation and data binding
- **Document Formats**: Leverages metadata for document property definitions

### Downstream Consumers
- **Code Generation**: Metadata types drive automatic C++ wrapper generation
- **Serialization**: Provides type information for binary/text serialization formats
- **Configuration Management**: Enables strongly-typed configuration schemas

## Usage Patterns

### Defining Custom Structures
```python
class MyConfig(Struct):
    fields = [
        Field("enabled", Bool(True)),
        Field("timeout", U32(30)),
        Field("name", String("default")),
        Field("color", Color(0xFF0000FF))
    ]
```

### Creating Instances
```python
config = MyConfig(True, 60, "custom", 0x00FF00FF)
config.timeout = 120  # Automatic validation
```

### Type Introspection
```python
for field in config.values:
    print(f"{field.name}: {field.c_type()} ({field.get_typ_enum()})")
```

## Validation and Error Handling

The module implements comprehensive validation at multiple levels:

### Value Validation
- **Range checking**: Ensures numeric values fit within type bounds
- **Type checking**: Validates Python type compatibility
- **String validation**: Accepts None, str, and unicode types

### Structure Validation
- **Field compatibility**: Ensures Compact flag is only used with non-struct fields
- **Flag conflicts**: Prevents NoStore and Compact combination
- **Array homogeneity**: Validates all array elements match specified type

### Error Reporting
- **Descriptive messages**: Provides clear validation failure reasons
- **Type information**: Includes expected vs. actual type details
- **Field context**: Identifies problematic fields in composite types

## Performance Considerations

### Memory Efficiency
- **Compact storage**: Optional compact binary format for primitive fields
- **Pointer optimization**: Struct arrays use pointer vectors for efficiency
- **Lazy validation**: Validation occurs only during value assignment

### Code Generation
- **C++ type mapping**: Direct mapping to native C++ types
- **Template specialization**: Enables efficient C++ template instantiation
- **Compile-time optimization**: Type information available at compile time

## Extension Points

### Custom Types
New primitive types can be added by:
1. Inheriting from `Type` base class
2. Implementing `is_valid_val()` method
3. Defining appropriate C++ type mapping
4. Adding type enum constant

### Validation Extensions
Custom validation logic can be added through:
- Overriding `is_valid_val()` in type subclasses
- Implementing custom validation functions
- Adding new storage flags for specialized behavior

## Security Considerations

### Input Validation
- **Bounds checking**: Prevents integer overflow/underflow
- **Type safety**: Rejects invalid Python type conversions
- **String handling**: Proper handling of None and unicode strings

### Memory Safety
- **Pointer management**: Safe C++ pointer type generation
- **Array bounds**: Implicit bounds checking through type system
- **Resource cleanup**: Automatic cleanup of composite types

This metadata module provides a robust foundation for type-safe data handling throughout the application, enabling reliable configuration management, efficient serialization, and seamless C++ integration while maintaining flexibility for future extensions.