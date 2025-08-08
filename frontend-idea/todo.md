# OCR Viewer TODO List

## Core Features

### 1. Line-by-Line Editing Mode

- [ ] Click on any word to make it editable inline
- [ ] Group words into lines based on Y-coordinates
- [ ] Save changes back to a markdown file in real-time
- [ ] Track changes/diffs between original and edited
- [ ] Keyboard shortcuts (Tab to next word, Enter to next line)
- [ ] Auto-save with debouncing

### 2. Side-by-Side View

- [ ] Split view: PDF image left, editable text right
- [ ] Synchronized scrolling between panels
- [ ] Click on image highlights corresponding text
- [ ] Click on text highlights corresponding region in image
- [ ] Adjustable panel widths
- [ ] Toggle between side-by-side and overlay modes

### 3. Smart Editing Features

- [ ] Auto-group words into paragraphs based on spacing
- [ ] Detect and preserve formatting (bold, italic, headers)
- [ ] Find & replace across the document
- [ ] Basic spell check with suggestions
- [ ] Undo/redo functionality
- [ ] Export to clean markdown with proper formatting

### 4. Font Matching & Visual Fidelity (Editable PDF Recreation)

- [ ] Integrate WhatFontIs API to identify fonts from image regions
- [ ] Show font confidence percentage
- [ ] Auto-download and apply Google Fonts when matches found
- [ ] Fallback to similar fonts when exact match unavailable
- [ ] Adjust letter spacing, line height to match original exactly
- [ ] Save font information with the document
- [ ] "Perfect Mode" - overlay that's indistinguishable from original
- [ ] Click to edit any text while maintaining exact visual appearance
- [ ] Export as "visual markdown" with font/style metadata

## Additional Enhancements

### Accuracy & Verification

- [ ] Compare PyMuPDF vs Mistral OCR results
- [ ] Confidence scoring for each word
- [ ] Highlight low-confidence words
- [ ] Manual bounding box adjustment tool
- [ ] Batch accept/reject suggestions

### Performance & UX

- [ ] Lazy load pages for large documents
- [ ] Progress indicator for OCR processing
- [ ] Keyboard navigation throughout
- [ ] Dark mode support
- [ ] Remember user preferences

### Export Options

- [ ] Export to Markdown with formatting
- [ ] Export to plain text
- [ ] Export to JSON with positional data
- [ ] Export to "reproduction HTML" that looks like original
- [ ] Export edit history/changelog

## Technical Debt

- [ ] Add proper error handling for OCR failures
- [ ] Implement caching for processed pages
- [ ] Add tests for OCR accuracy
- [ ] Optimize for mobile/tablet viewing
- [ ] Add authentication for API keys

## Future Ideas

- [ ] Collaborative editing (multiple users)
- [ ] OCR for handwritten text
- [ ] Table detection and extraction
- [ ] Multi-language support
- [ ] Integration with citation managers
- [ ] Auto-detect document structure (chapters, sections)
