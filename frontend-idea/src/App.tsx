import { OcrViewer } from "./components/ocr-viewer/OcrViewer";
import "./index.css";

export function App() {
  return (
    <div className="container mx-auto p-8 text-center relative z-10">
      <h1 className="text-5xl font-bold my-4 leading-tight">OCR PDF Viewer</h1>
      <OcrViewer />
    </div>
  );
}

export default App;
