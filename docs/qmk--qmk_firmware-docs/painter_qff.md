# Quantum Font File (QFF) Module Documentation

## Introduction

The `painter_qff` module implements the Quantum Font File (QFF) format for QMK Firmware's Quantum Painter system. This module provides functionality to create, parse, and manage font files specifically designed for embedded systems and mechanical keyboards. The QFF format enables efficient storage and rendering of fonts with support for both ASCII and Unicode character sets, compression, and various pixel formats.

## Architecture Overview

The QFF module is built around a structured font file format that organizes font data into discrete blocks, each serving a specific purpose in the font rendering pipeline.

```mermaid
graph TB
    subgraph "QFF Font File Structure"
        FD[QFFFontDescriptor]
        AT[QFFAsciiGlyphTableV1]
        UT[QFFUnicodeGlyphTableV1]
        PD[QGFFramePaletteDescriptorV1]
        DD[QFFFontDataDescriptorV1]
        
        FD --> AT
        FD --> UT
        FD --> PD
        FD --> DD
    end
    
    subgraph "Core Components"
        QFF[QFFFont]
        QGI[QFFGlyphInfo]
        
        QFF --> QGI
        QFF --> FD
        QFF --> AT
        QFF --> UT
        QFF --> DD
    end
    
    subgraph "External Dependencies"
        QGF[QGFBlockHeader]
        PIL[PIL Library]
        QP[qmk.painter]
        
        FD -.-> QGF
        QFF -.-> PIL
        QFF -.-> QP
    end
```

## Core Components

### QFFFont - Main Font Processing Engine

The `QFFFont` class serves as the primary interface for font processing and file generation. It orchestrates the entire font creation pipeline from TrueType fonts to QFF format.

```mermaid
classDiagram
    class QFFFont {
        -logger
        -image
        -glyph_data
        -glyph_height
        +generate_image(ttf_file, font_size, include_ascii, unicode_glyphs, include_before_left, use_aa)
        +save_to_image(img_file)
        +read_from_image(img_file, include_ascii, unicode_glyphs)
        +save_to_qff(format, use_rle, fp)
        -_parse_image(img, include_ascii, unicode_glyphs)
        -_extract_glyphs(format)
    }
```

**Key Responsibilities:**
- Font image generation from TrueType fonts
- Glyph extraction and measurement
- QFF file format serialization
- Compression optimization (RLE)
- Multi-format support

### QFFFontDescriptor - Font Metadata Container

The `QFFFontDescriptor` class encapsulates essential font metadata and file header information.

```mermaid
classDiagram
    class QFFFontDescriptor {
        +type_id: 0x00
        +length: 20
        +magic: 0x464651
        -header: QGFBlockHeader
        -version: 1
        -total_file_size: 0
        -line_height: 0
        -has_ascii_table: False
        -unicode_glyph_count: 0
        -format: 0xFF
        -flags: 0
        -compression: 0xFF
        -transparency_index: 0xFF
        +write(fp)
        +is_transparent: property
    }
```

**Key Attributes:**
- **Magic Number**: 0x464651 ("QFF" in ASCII)
- **Version**: Format version (currently 1)
- **Line Height**: Maximum glyph height
- **Format**: Pixel format identifier
- **Compression**: Compression method (0x01 for RLE, 0x00 for raw)
- **Transparency**: Support for transparent rendering

### Glyph Information Classes

#### QFFGlyphInfo - Individual Glyph Metadata

```mermaid
classDiagram
    class QFFGlyphInfo {
        -code_point
        -x
        -w
        -data_offset
        -image_uncompressed_bytes
        -image_compressed_bytes
        +write(fp, include_code_point)
    }
```

#### QFFAsciiGlyphTableV1 - ASCII Character Mapping

Manages the standard ASCII character set (0x20-0x7E, 95 characters) with fixed-size glyph descriptors.

```mermaid
classDiagram
    class QFFAsciiGlyphTableV1 {
        +type_id: 0x01
        +length: 95 * 3
        -header: QGFBlockHeader
        -glyphs: dict
        +add_glyph(glyph)
        +write(fp)
    }
```

#### QFFUnicodeGlyphTableV1 - Extended Unicode Support

Provides support for additional Unicode characters beyond the ASCII range.

```mermaid
classDiagram
    class QFFUnicodeGlyphTableV1 {
        +type_id: 0x02
        -header: QGFBlockHeader
        -glyphs: dict
        +add_glyph(glyph)
        +write(fp)
    }
```

### QFFFontDataDescriptorV1 - Image Data Storage

Encapsulates the actual glyph image data, supporting both compressed and uncompressed formats.

```mermaid
classDiagram
    class QFFFontDataDescriptorV1 {
        +type_id: 0x04
        -header: QGFBlockHeader
        -data: []
        +write(fp)
    }
```

## Data Flow Architecture

### Font Generation Pipeline

```mermaid
sequenceDiagram
    participant User
    participant QFFFont
    participant PIL
    participant QFFComponents
    participant FileSystem
    
    User->>QFFFont: generate_image(ttf_file, font_size)
    QFFFont->>PIL: Load TrueType font
    QFFFont->>QFFFont: Measure glyphs
    QFFFont->>PIL: Create image canvas
    QFFFont->>PIL: Render each glyph
    QFFFont->>QFFFont: Parse glyph positions
    QFFFont->>FileSystem: save_to_image()
    
    User->>QFFFont: save_to_qff(format, use_rle)
    QFFFont->>QFFFont: _extract_glyphs()
    QFFFont->>QFFComponents: Create descriptors
    QFFComponents->>FileSystem: Write QFF file
```

### File Format Structure

```mermaid
graph LR
    subgraph "QFF File Layout"
        A[QFFFontDescriptor<br/>20 bytes] --> B[QFFAsciiGlyphTableV1<br/>285 bytes]
        B --> C[QFFUnicodeGlyphTableV1<br/>variable]
        C --> D[QGFFramePaletteDescriptorV1<br/>variable]
        D --> E[QFFFontDataDescriptorV1<br/>variable]
    end
```

## Integration with Quantum Painter System

The QFF module integrates with the broader Quantum Painter ecosystem through shared components and utilities.

```mermaid
graph TB
    subgraph "Quantum Painter System"
        QFF[painter_qff]
        QGF[painter_qgf]
        QP[qmk.painter]
        
        QFF -.->|uses| QGF
        QFF -.->|uses| QP
        
        QGF -.->|block headers| QFF
        QP -.->|format conversion| QFF
        QP -.->|compression| QFF
    end
    
    subgraph "External Libraries"
        PIL[PIL/Pillow]
        MILC[milc.attrdict]
        
        QFF -.->|image processing| PIL
        QFF -.->|attribute dict| MILC
    end
```

## Key Features

### 1. Multi-Format Support
- Configurable pixel formats for different display types
- Automatic format conversion and optimization
- Palette generation for indexed color modes

### 2. Compression Optimization
- Run-Length Encoding (RLE) compression
- Automatic compression ratio evaluation
- Per-glyph compression decision making

### 3. Character Set Flexibility
- Standard ASCII character set (0x20-0x7E)
- Extended Unicode character support
- Custom glyph selection

### 4. Font Rendering Options
- Anti-aliasing control
- Baseline adjustment
- Glyph spacing configuration
- Transparency support

## Usage Patterns

### Font Generation from TrueType
```python
font = QFFFont(logger)
font.generate_image(
    ttf_file=Path("font.ttf"),
    font_size=12,
    include_ascii_glyphs=True,
    unicode_glyphs="→←↑↓",
    use_aa=True
)
font.save_to_qff(format, use_rle=True, fp)
```

### Font Processing from Image
```python
font = QFFFont(logger)
font.read_from_image(
    img_file=Path("font_image.png"),
    include_ascii_glyphs=True,
    unicode_glyphs=""
)
font.save_to_qff(format, use_rle=True, fp)
```

## File Format Specifications

### QFFFontDescriptor Format
- **Magic Number**: 3 bytes (0x464651)
- **Version**: 1 byte
- **Total File Size**: 4 bytes
- **Negated File Size**: 4 bytes (checksum)
- **Line Height**: 1 byte
- **ASCII Table Flag**: 1 byte
- **Unicode Glyph Count**: 2 bytes
- **Format**: 1 byte
- **Flags**: 1 byte
- **Compression**: 1 byte
- **Transparency Index**: 1 byte

### Glyph Data Encoding
- **ASCII Glyphs**: 3 bytes per glyph (no code point)
- **Unicode Glyphs**: 6 bytes per glyph (includes code point)
- **Data Offset**: 18 bits
- **Width**: 6 bits

## Performance Considerations

### Memory Efficiency
- Streaming file writes to minimize memory usage
- Optional RLE compression reduces file size
- Palette-based color modes for displays with limited color depth

### Processing Optimization
- Parallel glyph measurement during font generation
- Efficient image cropping and bounding box calculation
- Smart compression decision based on actual size reduction

## Error Handling

### Validation Checks
- Glyph count verification against input image markers
- File format validation through magic numbers
- Compression ratio evaluation before application

### Error Reporting
- Comprehensive logging throughout the font generation process
- Detailed error messages for common issues (missing glyphs, format mismatches)
- Validation of input parameters and file integrity

## Dependencies

### Internal Dependencies
- [painter_qgf.md](painter_qgf.md) - Block header format and palette descriptors
- [qmk.painter](qmk.painter) - Image conversion and compression utilities

### External Dependencies
- **PIL/Pillow**: Image processing and font rendering
- **pathlib**: File system operations
- **colorsys**: Color space conversions
- **milc.attrdict**: Attribute dictionary implementation

## Future Enhancements

### Potential Improvements
- Support for additional compression algorithms
- Variable-width font optimization
- Kerning table support
- Multi-language font subsetting
- Advanced anti-aliasing modes

### Format Extensions
- Version 2 format with extended features
- Additional metadata blocks
- Custom glyph shaping rules
- Color font support (COLR/CPAL tables)

## References

- [Quantum Painter QGF Format](painter_qgf.md) - Related image format documentation
- [QMK Firmware Documentation](https://docs.qmk.fm/) - Official QMK documentation
- [Quantum Painter QFF Specification](https://docs.qmk.fm/#/quantum_painter_qff) - Detailed format specification