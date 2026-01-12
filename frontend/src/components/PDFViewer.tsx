"use client";

import { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, X, Search } from "lucide-react";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Set worker path
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerProps {
    isOpen: boolean;
    onClose: () => void;
    fileUrl: string;
    fileName: string;
    highlightPage?: number;
    highlightText?: string;
    startCharIdx?: number;
    endCharIdx?: number;
    citations?: Array<{
        page_number?: number;
        start_char_idx?: number;
        end_char_idx?: number;
        content?: string;
    }>;
}

export function PDFViewer({
    isOpen,
    onClose,
    fileUrl,
    fileName,
    highlightPage,
    highlightText,
    startCharIdx,
    endCharIdx,
    citations = [],
}: PDFViewerProps) {
    const [numPages, setNumPages] = useState<number>(0);
    const [pageNumber, setPageNumber] = useState<number>(1);
    const [pdfText, setPdfText] = useState<string>("");
    const [highlightedRanges, setHighlightedRanges] = useState<Array<{ start: number; end: number; page: number }>>([]);
    const textLayerRef = useRef<HTMLDivElement>(null);
    const pageRef = useRef<HTMLDivElement>(null);

    // Extract text from PDF and calculate highlights
    useEffect(() => {
        if (!isOpen || !fileUrl) return;

        const extractText = async () => {
            try {
                const loadingTask = pdfjs.getDocument(fileUrl);
                const pdf = await loadingTask.promise;
                let fullText = "";
                const ranges: Array<{ start: number; end: number; page: number }> = [];

                // Extract text from all pages
                for (let i = 1; i <= pdf.numPages; i++) {
                    const page = await pdf.getPage(i);
                    const textContent = await page.getTextContent();
                    const pageText = textContent.items
                        .map((item: any) => item.str)
                        .join(" ");
                    
                    const pageStartIdx = fullText.length;
                    fullText += pageText + "\n";

                    // Check if this page has highlights
                    if (citations.length > 0) {
                        citations.forEach((citation) => {
                            if (citation.page_number === i && citation.start_char_idx !== undefined && citation.end_char_idx !== undefined) {
                                // Adjust offsets relative to this page
                                const relativeStart = citation.start_char_idx - pageStartIdx;
                                const relativeEnd = citation.end_char_idx - pageStartIdx;
                                
                                if (relativeStart >= 0 && relativeEnd <= pageText.length) {
                                    ranges.push({
                                        start: relativeStart,
                                        end: relativeEnd,
                                        page: i,
                                    });
                                }
                            }
                        });
                    } else if (highlightPage === i && startCharIdx !== undefined && endCharIdx !== undefined) {
                        // Single highlight case
                        const relativeStart = startCharIdx - pageStartIdx;
                        const relativeEnd = endCharIdx - pageStartIdx;
                        
                        if (relativeStart >= 0 && relativeEnd <= pageText.length) {
                            ranges.push({
                                start: relativeStart,
                                end: relativeEnd,
                                page: i,
                            });
                        }
                    }
                }

                setPdfText(fullText);
                setHighlightedRanges(ranges);
            } catch (error) {
                console.error("Error extracting PDF text:", error);
            }
        };

        extractText();
    }, [isOpen, fileUrl, highlightPage, startCharIdx, endCharIdx, citations]);

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
        setNumPages(numPages);
        // Jump to highlight page if provided
        if (highlightPage) {
            setPageNumber(highlightPage);
        } else if (citations.length > 0 && citations[0].page_number) {
            setPageNumber(citations[0].page_number);
        }
    }

    // Highlight text in the PDF page using text matching
    useEffect(() => {
        if (!textLayerRef.current || highlightedRanges.length === 0) return;

        const highlightTextInPage = () => {
            const textLayer = textLayerRef.current;
            if (!textLayer) return;

            const currentPageRanges = highlightedRanges.filter((r) => r.page === pageNumber);
            if (currentPageRanges.length === 0) return;

            // Get citation content to highlight
            const citationTexts = citations
                .filter((c) => c.page_number === pageNumber)
                .map((c) => c.content?.substring(0, 100) || "")
                .filter(Boolean);

            // Find and highlight matching text spans
            const textDivs = textLayer.querySelectorAll<HTMLElement>(".react-pdf__Page__textContent span");
            
            // Clear previous highlights
            textDivs.forEach((span) => {
                span.style.backgroundColor = "";
                span.style.color = "";
                span.classList.remove("highlighted-text");
            });

            // Highlight based on citation content matching
            citationTexts.forEach((citationText) => {
                const searchText = citationText.toLowerCase().trim();
                if (searchText.length < 10) return; // Skip very short texts

                textDivs.forEach((span) => {
                    const spanText = (span.textContent || "").toLowerCase();
                    
                    // Check if span contains part of the citation text
                    if (spanText.includes(searchText.substring(0, 20)) || 
                        searchText.includes(spanText.substring(0, 20))) {
                        span.style.backgroundColor = "rgba(255, 255, 0, 0.5)";
                        span.style.color = "#000";
                        span.style.borderRadius = "2px";
                        span.style.padding = "1px 2px";
                        span.style.fontWeight = "500";
                        span.classList.add("highlighted-text");
                    }
                });
            });

            // Also try to highlight based on character offsets if available
            currentPageRanges.forEach((range) => {
                let charCount = 0;
                textDivs.forEach((span) => {
                    const spanText = span.textContent || "";
                    const spanStart = charCount;
                    const spanEnd = charCount + spanText.length;

                    // Check if this span overlaps with highlight range
                    if (spanStart < range.end && spanEnd > range.start) {
                        if (!span.classList.contains("highlighted-text")) {
                            span.style.backgroundColor = "rgba(255, 255, 0, 0.5)";
                            span.style.color = "#000";
                            span.style.borderRadius = "2px";
                            span.style.padding = "1px 2px";
                            span.style.fontWeight = "500";
                            span.classList.add("highlighted-text");
                        }
                    }

                    charCount = spanEnd;
                });
            });
        };

        // Delay to ensure text layer is rendered
        const timeoutId = setTimeout(highlightTextInPage, 800);
        return () => clearTimeout(timeoutId);
    }, [pageNumber, highlightedRanges, citations]);

    const goToPrevPage = () => setPageNumber((prev) => Math.max(prev - 1, 1));
    const goToNextPage = () => setPageNumber((prev) => Math.min(prev + 1, numPages));

    // Find next page with highlights
    const goToNextHighlight = () => {
        const currentPageRanges = highlightedRanges
            .filter((r) => r.page > pageNumber)
            .sort((a, b) => a.page - b.page);
        
        if (currentPageRanges.length > 0) {
            setPageNumber(currentPageRanges[0].page);
        }
    };

    // Find previous page with highlights
    const goToPrevHighlight = () => {
        const currentPageRanges = highlightedRanges
            .filter((r) => r.page < pageNumber)
            .sort((a, b) => b.page - a.page);
        
        if (currentPageRanges.length > 0) {
            setPageNumber(currentPageRanges[0].page);
        }
    };

    const hasHighlights = highlightedRanges.length > 0;
    const currentPageHasHighlights = highlightedRanges.some((r) => r.page === pageNumber);

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span>{fileName}</span>
                            {hasHighlights && (
                                <span className="text-xs px-2 py-1 bg-violet-500/20 text-violet-300 rounded-full">
                                    {highlightedRanges.length} highlight{highlightedRanges.length !== 1 ? "s" : ""}
                                </span>
                            )}
                        </div>
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X className="h-4 w-4" />
                        </Button>
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-auto bg-gray-100 dark:bg-gray-900 p-4 flex items-center justify-center relative">
                    <Document
                        file={fileUrl}
                        onLoadSuccess={onDocumentLoadSuccess}
                        loading={<div className="text-white">Loading PDF...</div>}
                        error={<div className="text-red-400">Failed to load PDF</div>}
                    >
                        <div ref={pageRef} className="relative">
                            <Page
                                pageNumber={pageNumber}
                                renderTextLayer={true}
                                renderAnnotationLayer={true}
                                className="shadow-lg"
                            >
                                <div
                                    ref={textLayerRef}
                                    className="react-pdf__Page__textContent"
                                    style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
                                />
                            </Page>
                            
                            {/* Highlight indicator */}
                            {currentPageHasHighlights && (
                                <div className="absolute top-2 right-2 px-2 py-1 bg-yellow-400/90 text-black text-xs rounded shadow-lg flex items-center gap-1">
                                    <Search className="w-3 h-3" />
                                    Highlighted
                                </div>
                            )}
                        </div>
                    </Document>
                </div>

                <div className="flex items-center justify-between border-t pt-4 gap-4">
                    <div className="flex items-center gap-2">
                        <Button onClick={goToPrevPage} disabled={pageNumber <= 1} variant="outline" size="sm">
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            Previous
                        </Button>
                        
                        {hasHighlights && (
                            <>
                                <Button 
                                    onClick={goToPrevHighlight} 
                                    disabled={!highlightedRanges.some((r) => r.page < pageNumber)}
                                    variant="outline" 
                                    size="sm"
                                    className="text-yellow-400 border-yellow-400/30 hover:bg-yellow-400/10"
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                    Prev Highlight
                                </Button>
                                <Button 
                                    onClick={goToNextHighlight} 
                                    disabled={!highlightedRanges.some((r) => r.page > pageNumber)}
                                    variant="outline" 
                                    size="sm"
                                    className="text-yellow-400 border-yellow-400/30 hover:bg-yellow-400/10"
                                >
                                    Next Highlight
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </>
                        )}
                    </div>

                    <span className="text-sm text-gray-600 dark:text-gray-400">
                        Page {pageNumber} of {numPages}
                    </span>

                    <Button onClick={goToNextPage} disabled={pageNumber >= numPages} variant="outline" size="sm">
                        Next
                        <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                </div>

                {highlightText && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 italic border-t pt-2">
                        Highlighted: "{highlightText.substring(0, 100)}..."
                    </div>
                )}

                {citations.length > 0 && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 border-t pt-2 space-y-1">
                        <p className="font-medium">Citations on this page:</p>
                        {citations
                            .filter((c) => c.page_number === pageNumber)
                            .map((citation, idx) => (
                                <p key={idx} className="pl-2">
                                    • {citation.content?.substring(0, 80)}...
                                </p>
                            ))}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
