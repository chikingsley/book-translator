
import { useState } from "react";
import { Button } from "@/components/ui/button";

export interface Word {
  text: string;
  bbox: [number, number, number, number];
}

export interface PageData {
  image_url: string;
  width?: number;
  height?: number;
  words: Word[];
  markdown?: string;
}

interface PageProps {
  page: PageData;
}

export function Page({ page }: PageProps) {
  const [showOverlay, setShowOverlay] = useState(true);
  const [showImage, setShowImage] = useState(true);
  const [showTextOnImage, setShowTextOnImage] = useState(false);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  
  // Calculate scale based on actual image size vs original PDF size
  const scaleX = imageSize.width && page.width ? imageSize.width / page.width : 1;
  const scaleY = imageSize.height && page.height ? imageSize.height / page.height : 1;

  console.log("Page data:", page);
  console.log("Number of words:", page.words?.length || 0);
  console.log("Has markdown:", !!page.markdown);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageSize({ width: img.offsetWidth, height: img.offsetHeight });
  };

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        <Button 
          onClick={() => setShowImage(!showImage)}
          variant="outline"
          size="sm"
        >
          {showImage ? "Hide" : "Show"} Image
        </Button>
        <Button 
          onClick={() => setShowOverlay(!showOverlay)}
          variant="outline"
          size="sm"
        >
          {showOverlay ? "Hide" : "Show"} OCR Overlay
        </Button>
        {showImage && showOverlay && (
          <Button 
            onClick={() => setShowTextOnImage(!showTextOnImage)}
            variant="outline"
            size="sm"
          >
            {showTextOnImage ? "Hide" : "Show"} Text on Image
          </Button>
        )}
      </div>
      <div style={{ position: "relative", width: "100%", backgroundColor: !showImage ? "#f5f5f5" : "transparent", minHeight: !showImage ? "800px" : "auto" }}>
        {showImage && <img src={page.image_url} alt="PDF Page" style={{ width: "100%", height: "auto", display: "block" }} onLoad={handleImageLoad} />}
        {showOverlay && page.words && page.words.length > 0 ? page.words.map((word, index) => {
        const [x0, y0, x1, y1] = word.bbox;
        const boxHeight = (y1 - y0) * scaleY;
        const fontSize = Math.max(8, Math.min(boxHeight * 0.8, 24)); // 80% of box height, min 8px, max 24px
        
        return (
          <div
            key={index}
            style={{
              position: "absolute",
              left: `${x0 * scaleX}px`,
              top: `${y0 * scaleY}px`,
              width: `${(x1 - x0) * scaleX}px`,
              height: `${boxHeight}px`,
              border: showImage ? (showTextOnImage ? "1px solid rgba(0, 100, 255, 0.2)" : "1px solid rgba(0, 100, 255, 0.1)") : "1px solid rgba(0, 100, 255, 0.8)",
              backgroundColor: showImage ? (showTextOnImage ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 100, 255, 0.02)") : "rgba(255, 255, 255, 0.9)",
              color: showImage ? (showTextOnImage ? "rgba(0, 0, 100, 0.9)" : "transparent") : "blue",
              fontSize: `${fontSize}px`,
              lineHeight: `${boxHeight}px`,
              whiteSpace: "nowrap",
              overflow: "hidden",
              padding: "0",
              fontWeight: !showImage || showTextOnImage ? "500" : "normal",
              fontFamily: "system-ui, -apple-system, sans-serif",
              textShadow: showImage && showTextOnImage ? "0 0 3px rgba(255, 255, 255, 0.8)" : "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-start",
              paddingLeft: "2px",
            }}
            title={word.text} // Show text on hover
          >
            {word.text}
          </div>
        );
      }) : (
        showOverlay && !showImage && (
          page.markdown ? (
            <div style={{ padding: "20px", whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: "14px", lineHeight: "1.6" }}>
              {page.markdown}
            </div>
          ) : (
            <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
              No OCR text detected on this page
            </div>
          )
        )
      )}
      </div>
    </div>
  );
}
