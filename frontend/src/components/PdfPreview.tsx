import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Download, Printer, Share2, X, ZoomIn, ZoomOut } from "lucide-react";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { containDialogFocus } from "./dialogs";
import { ErrorBox, LoadingSkeleton } from "./ui";

/** Locally bundled PDF.js; renders the server's actual PDF bytes, without an external viewer. */
function PdfPages({ blob, zoom }: { blob: Blob; zoom: number }) {
  const root = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0),
    [pages, setPages] = useState(0),
    [ready, setReady] = useState(false),
    [error, setError] = useState<unknown>();
  useEffect(() => {
    const node = root.current;
    if (!node) return;
    const observer = new ResizeObserver((entries) =>
      setWidth(Math.floor(entries[0].contentRect.width)),
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!width) return;
    let cancelled = false,
      destroy: undefined | (() => void);
    setReady(false);
    setError(undefined);
    const host = root.current!;
    host.replaceChildren();
    void (async () => {
      const pdfjs = await import("pdfjs-dist");
      if (cancelled) return;
      pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
      const task = pdfjs.getDocument({
        data: new Uint8Array(await blob.arrayBuffer()),
      });
      destroy = () => {
        void task.destroy();
      };
      const pdf = await task.promise;
      if (cancelled) return;
      setPages(pdf.numPages);
      for (let index = 1; index <= pdf.numPages; index++) {
        if (cancelled) return;
        const page = await pdf.getPage(index);
        if (cancelled) return;
        const unscaled = page.getViewport({ scale: 1 });
        const cssScale = (Math.min(width, 794) * zoom) / unscaled.width;
        const ratio = Math.min(devicePixelRatio || 1, 2);
        const viewport = page.getViewport({ scale: cssScale * ratio });
        const canvas = document.createElement("canvas");
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        canvas.style.width = Math.ceil(viewport.width / ratio) + "px";
        canvas.style.height = Math.ceil(viewport.height / ratio) + "px";
        canvas.setAttribute("role", "img");
        canvas.setAttribute(
          "aria-label",
          `PDF sayfa ${index} / ${pdf.numPages}`,
        );
        const figure = document.createElement("figure"),
          caption = document.createElement("figcaption");
        caption.textContent = `Sayfa ${index} / ${pdf.numPages}`;
        figure.append(canvas, caption);
        host.append(figure);
        await page.render({ canvas, viewport }).promise;
      }
      if (!cancelled) setReady(true);
    })().catch((err) => {
      if (!cancelled) setError(err);
    });
    return () => {
      cancelled = true;
      destroy?.();
      host.replaceChildren();
    };
  }, [blob, width, zoom]);
  return (
    <>
      {error ? <ErrorBox error={error} /> : !ready && <LoadingSkeleton />}
      <p className="caption" role="status">
        {ready
          ? `${pages} sayfalı PDF hazır.`
          : "Gerçek PDF sayfaları hazırlanıyor…"}
      </p>
      <div className="pdf-pages" ref={root} />
    </>
  );
}
export function PdfPreview({
  blob,
  onClose,
  onDownload,
  onPrint,
  children,
  busy = false,
  returnFocus,
}: {
  blob: Blob;
  onClose: () => void;
  onDownload: () => void;
  onPrint?: () => void;
  children: ReactNode;
  busy?: boolean;
  returnFocus?: HTMLElement;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    close = useRef<HTMLButtonElement>(null),
    id = useId();
  const [zoom, setZoom] = useState(1),
    [text, setText] = useState(false),
    [shareError, setShareError] = useState("");
  const file = new File([blob], "AVATAR-belge.pdf", {
    type: "application/pdf",
  });
  const canShare = !!navigator.canShare?.({ files: [file] });
  useEffect(() => {
    const opener =
        returnFocus || (document.activeElement as HTMLElement | null),
      dialog = ref.current;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog?.showModal();
    close.current?.focus();
    return () => {
      if (dialog?.open) dialog.close();
      document.body.style.overflow = previous;
      if (opener?.isConnected) requestAnimationFrame(() => opener.focus());
    };
  }, []);
  async function share() {
    try {
      await navigator.share({ files: [file], title: "AVATAR belge taslağı" });
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError"))
        setShareError(
          "Paylaşım açılamadı. PDF indir seçeneğini kullanabilirsiniz.",
        );
    }
  }
  return (
    <dialog
      className="pdf-modal"
      ref={ref}
      aria-labelledby={id}
      onKeyDown={containDialogFocus}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <header className="pdf-modal-header">
        <div>
          <h2 id={id}>Belge önizleme</h2>
          <p className="caption">Gerçek PDF · A4 · Geçici taslak</p>
        </div>
        <button
          ref={close}
          className="icon-button"
          autoFocus
          aria-label="Önizlemeyi kapat"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      <div className="pdf-modal-tools">
        <div className="document-actions">
          <button
            className="button primary"
            onClick={onDownload}
            disabled={busy}
          >
            <Download size={17} />
            PDF indir
          </button>
          {onPrint && (
            <button className="button" onClick={onPrint} disabled={busy}>
              <Printer size={17} />
              Yazdır
            </button>
          )}
          {canShare && (
            <button className="button" onClick={() => void share()}>
              <Share2 size={17} />
              Paylaş
            </button>
          )}
        </div>
        <div className="document-actions">
          <button
            className="button"
            aria-pressed={text}
            onClick={() => setText(!text)}
          >
            {text ? "PDF görünümü" : "Metin görünümü"}
          </button>
          {!text && (
            <>
              <button
                className="icon-button"
                aria-label="Uzaklaştır"
                disabled={zoom <= 1}
                onClick={() => setZoom((z) => Math.max(1, z - 0.25))}
              >
                <ZoomOut size={18} />
              </button>
              <span className="caption">%{Math.round(zoom * 100)}</span>
              <button
                className="icon-button"
                aria-label="Yakınlaştır"
                disabled={zoom >= 2}
                onClick={() => setZoom((z) => Math.min(2, z + 0.25))}
              >
                <ZoomIn size={18} />
              </button>
            </>
          )}
        </div>
      </div>
      {shareError && (
        <p className="notice" role="status">
          {shareError}
        </p>
      )}
      <div
        className="pdf-modal-body"
        tabIndex={0}
        aria-label="Kaydırılabilir belge"
      >
        {text ? children : <PdfPages blob={blob} zoom={zoom} />}
      </div>
    </dialog>
  );
}
