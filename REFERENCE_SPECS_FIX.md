# Reference Specs Upload Feature - Issue Resolution

## Problem Summary

The "Reference Specs (Optional)" upload feature in the chat interface was not working due to missing dependencies for PDF text extraction.

## Root Cause

The `extract_text_from_pdf()` function in [src/services/rag_service.py](src/services/rag_service.py:315-336) requires OCR dependencies that were not installed:

1. **Python packages**:
   - `pdf2image` - Converts PDF pages to images
   - `pytesseract` - Python wrapper for Tesseract OCR
   - `Pillow` - Image processing library

2. **System dependencies** (already present on Mac):
   - `poppler-utils` - Provides `pdftoppm` for PDF to image conversion
   - `tesseract-ocr` - OCR engine for text extraction

## What Was Happening

When a user uploaded a reference specification PDF:

1. ✅ File was saved successfully to uploads folder
2. ✅ `/api/io-allocation/chat/upload-spec` endpoint was called
3. ❌ `extract_text_from_pdf()` failed silently (caught exception on line 334)
4. ❌ Returned empty string `""` instead of extracted text
5. ❌ The `if spec_text:` check on line 1303 of app.py failed
6. ❌ User received error message: "Could not extract text from {filename}"

## Solution Implemented

### 1. Updated requirements.txt

Added missing dependencies:

```diff
anthropic>=0.30.0
flask>=2.0.0
+pdf2image>=1.16.0
+pytesseract>=0.3.10
+Pillow>=10.0.0
```

### 2. Installed Dependencies

```bash
pip3 install pdf2image pytesseract Pillow
```

### 3. Verified System Dependencies

Confirmed that poppler and tesseract are installed:
- `/opt/homebrew/bin/pdftoppm` ✓
- `/opt/homebrew/bin/tesseract` ✓

## How It Works Now

When a reference spec PDF is uploaded:

1. User selects PDF file from "Reference Specs (Optional)" section
2. Frontend calls `/api/io-allocation/chat/upload-spec`
3. Backend saves file as `spec_{session_id}_{filename}.pdf`
4. `extract_text_from_pdf()` converts PDF pages to images using `pdf2image`
5. `pytesseract` performs OCR on each page
6. Extracted text is chunked and added to RAG assistant's document store
7. AI assistant can now reference the spec content when answering questions

## Testing the Fix

To verify the fix works:

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Navigate to**: `http://localhost:5000/io-allocation/chat`

3. **Upload an I/O list** (Excel or PDF)

4. **Upload a reference spec PDF** using "Reference Specs (Optional)" section

5. **Verify success**:
   - You should see: "📄 Added reference document: **{filename}**. I'll ensure compliance with this spec."
   - Ask the AI: "What specifications did I upload?"
   - The AI should mention the uploaded document

## Technical Details

### PDF Extraction Function

Located at [src/services/rag_service.py](src/services/rag_service.py:315-336):

```python
def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file using OCR."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(filepath, dpi=200)
        text_parts = []

        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            text_parts.append(f"--- Page {i+1} ---\n{text}")

        return "\n\n".join(text_parts)

    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""
```

### RAG Integration

1. **Document Storage**: Specs are stored in `RAGAssistant.document_store`
2. **Chunking**: Text is split into 1500-character chunks with 200-char overlap
3. **Retrieval**: When user asks questions, relevant chunks are retrieved using keyword matching
4. **Context Injection**: Retrieved chunks are added to Claude's system prompt

### API Endpoints

**Initial Upload (with I/O list)**:
```
POST /api/io-allocation/chat/start
FormData:
  - io_list: Excel/PDF file
  - vendor: String
  - specs[]: Array of PDF files (optional)
```

**Additional Spec Upload**:
```
POST /api/io-allocation/chat/upload-spec
FormData:
  - session_id: String
  - spec: PDF file
```

## Alternative PDF Extraction Methods

If OCR is too slow or inaccurate, consider these alternatives:

### Option 1: PyPDF2 (for text-based PDFs)
```python
import PyPDF2

def extract_text_simple(filepath: str) -> str:
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
```

### Option 2: pdfplumber (better formatting)
```python
import pdfplumber

def extract_text_structured(filepath: str) -> str:
    with pdfplumber.open(filepath) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text
```

### Option 3: Hybrid approach
```python
def extract_text_hybrid(filepath: str) -> str:
    """Try PyPDF2 first, fall back to OCR if needed."""
    # Try text extraction first
    text = extract_text_simple(filepath)

    # If mostly empty, use OCR
    if len(text.strip()) < 100:
        text = extract_text_from_pdf(filepath)

    return text
```

## Future Enhancements

1. **Progress indicator** for large PDF uploads
2. **Preview** of extracted text before adding to RAG
3. **Multiple format support** (Word docs, Excel specs)
4. **Better error messages** showing exactly what went wrong
5. **Chunk visualization** showing what parts of spec are being used
6. **Spec management UI** to remove/reorder uploaded specs

## Deployment Considerations

When deploying to production:

1. **Ensure system dependencies are installed**:
   ```dockerfile
   # Dockerfile
   RUN apt-get update && apt-get install -y \
       poppler-utils \
       tesseract-ocr
   ```

2. **Railway/Render deployment**:
   - Add buildpack for poppler and tesseract
   - Or use Docker with dependencies pre-installed

3. **Performance**: OCR is CPU-intensive
   - Consider caching extracted text
   - Use background job queue for large PDFs
   - Set reasonable file size limits

---

**Status**: ✅ Fixed and tested
**Date**: 2024-12-18
**Affected Files**:
- `requirements.txt` (updated)
- `src/services/rag_service.py` (no changes needed)
- `app.py` (no changes needed)
