import {
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { X } from "lucide-react";
// Keep Tab navigation inside the modal instead of visiting browser chrome at the boundary.
function containDialogFocus(event: KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== "Tab") return;
  const candidates = Array.from(
    event.currentTarget.querySelectorAll<HTMLElement>(
      "button, a[href], input, select, textarea, summary, [tabindex]",
    ),
  ).filter(
    (el) =>
      el.tabIndex >= 0 &&
      !el.hasAttribute("disabled") &&
      el.getClientRects().length > 0 && el.checkVisibility(),
  );
  const first = candidates[0],
    last = candidates[candidates.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
export function ConfirmDialog({
  title = "İşlemi onaylayın",
  children,
  onCancel,
  onConfirm,
  confirmLabel = "Onayla ve kaydet",
  confirmDisabled = false,
  danger = false,
}: {
  title?: string;
  children: ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
  confirmDisabled?: boolean;
  danger?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null), cancel = useRef<HTMLButtonElement>(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    cancel.current?.focus();
    return () => {
      if (dialog?.open && dialog.isConnected) dialog.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={id}
      onKeyDown={containDialogFocus}
      onCancel={(e) => {
        e.preventDefault();
        ref.current?.close();
        onCancel();
      }}
    >
      <h2 id={id}>{title}</h2>
      {children}
      <div className="actions">
        <button
          ref={cancel}
          type="button"
          autoFocus
          className="button"
          onClick={() => {
            ref.current?.close();
            onCancel();
          }}
        >
          Vazgeç
        </button>
        <button
          type="button"
          className={"button " + (danger ? "danger" : "primary")}
          disabled={confirmDisabled}
          onClick={() => {
            ref.current?.close();
            onConfirm();
          }}
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
export function DetailDrawer({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => {
      if (el?.open && el.isConnected) el.close();
    };
  }, []);
  return (
    <dialog
      className="detail-drawer"
      ref={ref}
      aria-labelledby={id}
      onKeyDown={containDialogFocus}
      onCancel={(e) => {
        e.preventDefault();
        ref.current?.close();
        onClose();
      }}
    >
      <div className="section-head">
        <h2 id={id}>{title}</h2>
        <button
          className="icon-button"
          autoFocus
          onClick={() => {
            ref.current?.close();
            onClose();
          }}
          aria-label="Ayrıntıyı kapat"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
