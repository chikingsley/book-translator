import { useState, useEffect, useRef } from "react";
import { PageData } from "./Page";
import { Button } from "@/components/ui/button";

interface SideBySideViewProps {
  pages: PageData[];
  currentPage: number;
  sessionId: string;
}

export function SideBySideView({ pages, currentPage, sessionId }: SideBySideViewProps) {
  const [text, setText] = useState("");
  const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(null);
  const imageRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  
  const page = pages[currentPage];
  
  // Initialize text from page data
  useEffect(() => {
    if (page) {
      // Use markdown if available, otherwise construct from words
      if (page.markdown) {
        setText(page.markdown);
      } else if (page.words && page.words.length > 0) {
        // Group words into lines based on Y coordinate
        const lines = groupWordsIntoLines(page.words);
        setText(lines.join("\n"));
      }
    }
  }, [page]);
  
  // Group words into lines based on Y coordinate
  function groupWordsIntoLines(words: typeof page.words) {
    if (!words || words.length === 0) return [];
    
    const sortedWords = [...words].sort((a, b) => {
      const aY = a.bbox[1];
      const bY = b.bbox[1];
      if (Math.abs(aY - bY) < 5) { // Same line threshold
        return a.bbox[0] - b.bbox[0]; // Sort by X if same line
      }
      return aY - bY; // Sort by Y
    });
    
    const lines: string[] = [];
    let currentLine: string[] = [];
    let lastY = sortedWords[0].bbox[1];
    
    sortedWords.forEach(word => {
      const y = word.bbox[1];
      if (Math.abs(y - lastY) > 10) { // New line threshold
        if (currentLine.length > 0) {
          lines.push(currentLine.join(" "));
          currentLine = [];
        }
        lastY = y;
      }
      currentLine.push(word.text);
    });
    
    if (currentLine.length > 0) {
      lines.push(currentLine.join(" "));
    }
    
    return lines;
  }
  
  // Synchronized scrolling
  const handleImageScroll = () => {
    if (imageRef.current && textRef.current) {
      const scrollPercentage = imageRef.current.scrollTop / 
        (imageRef.current.scrollHeight - imageRef.current.clientHeight);
      textRef.current.scrollTop = scrollPercentage * 
        (textRef.current.scrollHeight - textRef.current.clientHeight);
    }
  };
  
  const handleTextScroll = () => {
    if (imageRef.current && textRef.current) {
      const scrollPercentage = textRef.current.scrollTop / 
        (textRef.current.scrollHeight - textRef.current.clientHeight);
      imageRef.current.scrollTop = scrollPercentage * 
        (imageRef.current.scrollHeight - imageRef.current.clientHeight);
    }
  };
  
  const handleWordClick = (index: number) => {
    setSelectedWordIndex(index);
    // Could highlight corresponding text in the editor
  };
  
  return (
    <div className="flex h-[800px] gap-4">
      {/* Left panel - PDF Image */}
      <div 
        ref={imageRef}
        className="flex-1 overflow-auto border rounded-lg p-4 bg-gray-50"
        onScroll={handleImageScroll}
      >
        <div className="relative">
          <img 
            src={page.image_url} 
            alt="PDF Page" 
            className="w-full h-auto"
          />
          {/* Overlay clickable regions for words */}
          {page.words && page.words.map((word, index) => {
            const [x0, y0, x1, y1] = word.bbox;
            const isSelected = selectedWordIndex === index;
            
            return (
              <div
                key={index}
                onClick={() => handleWordClick(index)}
                className="absolute cursor-pointer transition-all"
                style={{
                  left: `${(x0 / (page.width || 1)) * 100}%`,
                  top: `${(y0 / (page.height || 1)) * 100}%`,
                  width: `${((x1 - x0) / (page.width || 1)) * 100}%`,
                  height: `${((y1 - y0) / (page.height || 1)) * 100}%`,
                  backgroundColor: isSelected 
                    ? "rgba(59, 130, 246, 0.3)" 
                    : "rgba(59, 130, 246, 0.05)",
                  border: isSelected 
                    ? "2px solid rgb(59, 130, 246)" 
                    : "1px solid transparent",
                }}
                title={word.text}
              />
            );
          })}
        </div>
      </div>
      
      {/* Right panel - Editable Text */}
      <div className="flex-1 flex flex-col">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-semibold">Extracted Text</h3>
          <Button 
            size="sm" 
            variant="outline"
            onClick={async () => {
              try {
                const response = await fetch("/api/save-markdown", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    session_id: sessionId,
                    page_number: currentPage + 1,
                    text: text
                  })
                });
                
                if (response.ok) {
                  const result = await response.json();
                  alert(`Saved to ${result.filename}`);
                } else {
                  alert("Failed to save markdown");
                }
              } catch (error) {
                console.error("Save error:", error);
                alert("Error saving markdown");
              }
            }}
          >
            Save as Markdown
          </Button>
        </div>
        <textarea
          ref={textRef as any}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onScroll={handleTextScroll}
          className="flex-1 w-full p-4 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Extracted text will appear here..."
        />
      </div>
    </div>
  );
}