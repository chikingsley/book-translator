
import { useState } from "react";
import { Page, PageData } from "./Page";
import { SideBySideView } from "./SideBySideView";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function OcrViewer() {
  const [pages, setPages] = useState<PageData[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [viewMode, setViewMode] = useState<"overlay" | "side-by-side">("overlay");
  const [sessionId, setSessionId] = useState<string>("");

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/ocr", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Backend error:", errorData);
        throw new Error(errorData.error || "Failed to process PDF");
      }

      const data = await response.json();
      setPages(data.pages);
      setSessionId(data.session_id);
      setCurrentPage(0);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-center gap-4 mb-4">
        <Input type="file" onChange={handleFileChange} accept=".pdf" />
        {isLoading && <p>Processing...</p>}
      </div>

      {pages.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Button onClick={() => setCurrentPage(p => Math.max(0, p - 1))} disabled={currentPage === 0}>
                Previous
              </Button>
              <span>Page {currentPage + 1} of {pages.length}</span>
              <Button onClick={() => setCurrentPage(p => Math.min(pages.length - 1, p + 1))} disabled={currentPage === pages.length - 1}>
                Next
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === "overlay" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("overlay")}
              >
                Overlay View
              </Button>
              <Button
                variant={viewMode === "side-by-side" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("side-by-side")}
              >
                Side by Side
              </Button>
            </div>
          </div>
          {viewMode === "overlay" ? (
            <Page page={pages[currentPage]} />
          ) : (
            <SideBySideView pages={pages} currentPage={currentPage} sessionId={sessionId} />
          )}
        </div>
      )}
    </div>
  );
}
