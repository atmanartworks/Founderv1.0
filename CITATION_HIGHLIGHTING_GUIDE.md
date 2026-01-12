# Citation Highlighting Implementation Guide

## Overview

The citation highlighting feature allows users to click on citations in chat responses and automatically view the source document with the relevant text highlighted. This creates a seamless citation-to-highlight workflow.

## How It Works

### Backend (Already Implemented ✅)

1. **Character Offsets**: During document processing, character offsets (`start_char_idx`, `end_char_idx`) are calculated and stored in `document_chunks` table.

2. **Citation Metadata**: When generating responses, citations include:
   - `page_number`: Page where the text appears
   - `start_char_idx`: Starting character position
   - `end_char_idx`: Ending character position
   - `content`: The actual cited text
   - `document_id`: Reference to the source document

### Frontend (Implemented ✅)

1. **Citation Click Handler**: When a user clicks a citation badge `[1]`, `[2]`, etc.:
   - Extracts citation metadata (page number, character offsets)
   - Fetches document URL from Supabase Storage
   - Opens PDF viewer with highlighting parameters

2. **PDF Viewer Enhancement**:
   - Automatically navigates to the correct page
   - Highlights text using character offsets
   - Shows multiple highlights if multiple citations from same document
   - Provides navigation between highlighted sections

## Usage

### For Users

1. **Ask a question** in the chat interface
2. **View response** with citations like `[1]`, `[2]`
3. **Click citation badge** to open document viewer
4. **See highlighted text** automatically on the correct page
5. **Navigate** between multiple highlights using "Next Highlight" / "Prev Highlight" buttons

### For Developers

#### Opening PDF with Highlight

```typescript
// Citation object structure
const citation = {
    document_id: "uuid",
    document_title: "Document Name",
    page_number: 3,
    start_char_idx: 1500,
    end_char_idx: 1800,
    content: "The highlighted text content...",
    metadata: {
        storage_path: "user_id/uuid/filename.pdf",
        mime_type: "application/pdf",
        start_char_idx: 1500,
        end_char_idx: 1800,
        page_number: 3
    }
};

// Open PDF viewer
handleCitationClick(citation);
```

#### PDF Viewer Props

```typescript
<PDFViewer
    isOpen={boolean}
    onClose={() => void}
    fileUrl={string}              // Document URL from Supabase Storage
    fileName={string}             // Display name
    highlightPage={number}         // Page number to jump to
    startCharIdx={number}         // Character offset start (optional)
    endCharIdx={number}           // Character offset end (optional)
    citations={Array}             // Array of citations for multi-highlight
/>
```

## Technical Details

### Character Offset Calculation

Character offsets are calculated during document ingestion:

1. Full document text is extracted
2. Text is chunked with overlap
3. For each chunk, character positions are calculated:
   - `start_char_idx`: Position in full document where chunk starts
   - `end_char_idx`: Position where chunk ends

### Highlighting Algorithm

The PDF viewer uses two methods for highlighting:

1. **Text Matching**: Matches citation content against PDF text spans
2. **Character Offsets**: Uses stored offsets to highlight specific ranges

Both methods are used together for maximum accuracy.

### Limitations

1. **Offset Accuracy**: Character offsets are approximate, especially with:
   - Complex layouts
   - Tables and images
   - Special formatting

2. **Text Matching**: Works best with:
   - Plain text content
   - Standard PDF layouts
   - Clear text extraction

3. **Multi-page Citations**: Currently highlights on the page specified in `page_number`. Cross-page citations may need enhancement.

## Future Enhancements

1. **Better Offset Calculation**: Use Llama Parse's native offset tracking
2. **Cross-page Highlights**: Support citations spanning multiple pages
3. **Visual Indicators**: Add scroll-to-highlight animation
4. **Multiple Document Support**: Show highlights across multiple documents
5. **Highlight Persistence**: Remember highlights when navigating pages

## Troubleshooting

### Highlights Not Showing

1. **Check character offsets**: Verify `start_char_idx` and `end_char_idx` are stored
2. **Check page numbers**: Ensure `page_number` matches actual PDF pages
3. **Check text extraction**: Verify PDF text is extractable (not scanned image)
4. **Check console**: Look for errors in browser console

### Wrong Page Opened

1. **Verify page numbers**: Check that `page_number` in citation matches PDF
2. **Check document**: Ensure correct document is being opened
3. **Test with known citation**: Try with a citation you know the page for

### Highlighting Not Accurate

1. **Character offsets are approximate**: This is expected, especially with complex layouts
2. **Text matching helps**: The dual approach (offsets + text matching) improves accuracy
3. **Consider Llama Parse**: Better extraction provides more accurate offsets

## Testing

### Manual Testing

1. Upload a test PDF document
2. Wait for processing to complete
3. Ask a question that references the document
4. Click on a citation `[1]` in the response
5. Verify:
   - PDF opens on correct page
   - Text is highlighted (yellow background)
   - Navigation buttons work
   - Multiple highlights work if multiple citations

### Automated Testing (Future)

```typescript
// Example test case
test('citation click opens PDF with highlight', async () => {
    const citation = {
        document_id: 'test-id',
        page_number: 1,
        start_char_idx: 100,
        end_char_idx: 200,
        metadata: { storage_path: 'test/path.pdf' }
    };
    
    await handleCitationClick(citation);
    
    expect(pdfViewerOpen).toBe(true);
    expect(pdfHighlightPage).toBe(1);
    expect(pdfStartCharIdx).toBe(100);
});
```

## Related Files

- `frontend/src/components/PDFViewer.tsx` - Enhanced PDF viewer with highlighting
- `frontend/src/app/chat/page.tsx` - Chat interface with citation handling
- `backend/app/services/ingestion.py` - Document processing with offset calculation
- `backend/app/services/chat.py` - Citation generation with metadata

---

**Status**: ✅ Implemented and Ready for Use
**Last Updated**: 2024-12-XX

