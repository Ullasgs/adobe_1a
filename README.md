# PDF Processing Solution 1(a) - Adobe India Hackathon 2025
## Installation and Usage

### Build Command


```bash
git clone https://github.com/Ullasgs/adobe_1a
```

### Navigate to the project in terminal
```bash
docker build --platform linux/amd64 -t pdf-processor .
```

### Run Command

```bash
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none pdf-processor
```

## Overview

This solution implements a PDF processing system that extracts structured data from PDF documents and outputs JSON files conforming to the specified schema. The solution uses PyMuPDF (fitz) for efficient PDF processing and is optimized for performance within the given constraints.

## Key Features

- **Intelligent Text Extraction**: Extracts text with proper structure recognition
- **Heading Detection**: Automatically identifies different heading levels (h1-h4) based on font size, style, and text patterns
- **Title Extraction**: Intelligently extracts document title from metadata or first page content
- **Performance Optimized**: Designed to process 50-page PDFs within 10 seconds
- **Memory Efficient**: Optimized for 16GB RAM constraint
- **Schema Compliant**: Outputs JSON files that conform to the required schema

## Architecture

### Core Components

1. **PDFProcessor Class**: Main processing engine that handles PDF analysis
2. **Text Extraction**: Uses PyMuPDF's text extraction capabilities
3. **Structure Analysis**: Analyzes font properties and text patterns to determine hierarchy
4. **Output Generation**: Creates structured JSON output conforming to the schema

### Processing Pipeline

1. **Input Scanning**: Scans `/app/input` directory for PDF files
2. **Document Analysis**: 
   - Extracts title from metadata or first page
   - Analyzes text blocks and font properties
   - Determines heading levels based on size and style
3. **Structure Detection**: 
   - Identifies headings using font size thresholds
   - Recognizes common heading patterns (numbering, etc.)
   - Classifies text into appropriate levels
4. **Output Generation**: Creates JSON files in `/app/output` directory

## Libraries and Models Used

### Primary Dependencies

- **PyMuPDF (fitz) v1.23.14**: 
  - Fast PDF processing library
  - Excellent text extraction capabilities
  - Font and style information access
  - Lightweight and efficient

### Built-in Libraries

- **os**: File system operations
- **json**: JSON output generation
- **re**: Regular expression pattern matching
- **pathlib**: Modern path handling



## Performance Optimizations

### Speed Optimizations

1. **Efficient Text Extraction**: Uses PyMuPDF's optimized text extraction
2. **Single Pass Processing**: Processes each PDF in one pass through pages
3. **Minimal Memory Footprint**: Processes documents page by page
4. **Optimized Font Analysis**: Caches font analysis results where possible

### Memory Management

1. **Document Cleanup**: Properly closes PDF documents after processing
2. **Streaming Processing**: Processes pages sequentially to minimize memory usage
3. **Efficient Data Structures**: Uses appropriate data types for minimal memory overhead

### Resource Constraints Compliance

- **Execution Time**: ≤ 10 seconds for 50-page PDFs
- **Memory Usage**: Optimized for 16GB RAM limit
- **CPU Utilization**: Efficient single-threaded processing
- **Model Size**: No ML models used, staying well under 200MB limit

## Output Schema Compliance

The solution generates JSON output that strictly follows the required schema:

```json
{
  "title": "string",
  "outline": [
    {
      "level": "string",
      "text": "string", 
      "page": "integer"
    }
  ]
}
```

### Level Classification

- **h1**: Large headings (font size ≥ 18pt, bold)
- **h2**: Medium headings (font size ≥ 16pt, bold)
- **h3**: Small headings (font size ≥ 14pt, bold)
- **h4**: Sub-headings (font size ≥ 12pt, bold)
- **text**: Regular text content

## Testing Strategy

### Local Testing

1. **Build the Docker image**:
   ```bash
   docker build --platform linux/amd64 -t pdf-processor .
   ```

2. **Test with sample data**:
   ```bash
   docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none pdf-processor
   ```

### Test Cases Covered

- **Simple PDFs**: Basic documents with clear structure
- **Complex PDFs**: Multi-column layouts, varied fonts
- **Large PDFs**: 50+ page documents for performance testing
- **Edge Cases**: PDFs without titles, unusual formatting

## Error Handling

- **File Access Errors**: Graceful handling of unreadable PDFs
- **Memory Constraints**: Efficient processing to avoid memory issues
- **Malformed PDFs**: Robust error handling for corrupted files
- **Empty Documents**: Proper handling of empty or minimal content

## Compliance Checklist

- Processes all PDFs from `/app/input` directory
- Generates `filename.json` for each `filename.pdf`
- Output format matches required JSON schema
- No internet access required during execution
- Works on AMD64 architecture
- Uses only open-source libraries
- Memory usage optimized for 16GB constraint
- Processing time optimized for 10-second constraint
- Dockerfile present and functional
- Complete documentation provided

