# OCR and Vision

Industrial environments frequently rely on scanned PDFs, maintenance logs, and images of technical documentation. The Sovereign AI Workbench includes a robust pipeline to extract and assess this content.

## Processing Pipeline

1. **OCR Extraction:** Scanned documents and images undergo Optical Character Recognition (OCR) using local libraries (e.g., PyMuPDF).
2. **Quality Assessment:** The `OCRQualityService` evaluates the extracted text. It looks for typical OCR failures: garbage character ratios, broken formatting, missing spaces, and unrecognized symbols.
3. **Vision Fallback:** If the local environment supports it and the document is highly visual (e.g., diagrams, dense tables), the local vision model (`llava:7b`) can be invoked by the backend to analyze the image directly.

## Reliability States (Human-in-the-Loop)

Because corrupted text poisons the RAG vector store and degrades AI responses, all extracted documents are graded into one of four specific enumeration states:

- `accepted`: Extraction is clean and highly reliable. The document is automatically eligible for Knowledge indexing.
- `accepted_with_warnings`: Extraction is usable but contains minor formatting issues or sparse text. Eligible for Knowledge indexing, but user awareness is recommended.
- `review_required`: Significant portions of the text appear garbled, or the OCR confidence is low. **Knowledge indexing is blocked** until a human reviews the extraction and manually accepts it in the TUI.
- `reupload_required`: Extraction completely failed or the image is illegible. The document cannot be indexed.

This strict reliability gating ensures that the models are only grounded on high-quality text, preventing the "garbage in, garbage out" problem common in enterprise RAG systems.
