declare module "pdfjs-dist/legacy/build/pdf" {
  type PDFPage = {
    cleanup: () => void;
    getViewport: (options: { scale: number }) => { width: number; height: number };
    render: (options: {
      canvasContext: CanvasRenderingContext2D;
      viewport: { width: number; height: number };
    }) => { promise: Promise<void> };
  };

  type PDFDocument = {
    numPages: number;
    getPage: (pageNumber: number) => Promise<PDFPage>;
  };

  const pdfjsLib: {
    GlobalWorkerOptions: { workerSrc: string };
    getDocument: (source: string) => {
      promise: Promise<PDFDocument>;
      destroy: () => Promise<void>;
    };
  };

  export = pdfjsLib;
}

declare module "pdfjs-dist/legacy/build/pdf.worker?url" {
  const workerUrl: string;
  export default workerUrl;
}
