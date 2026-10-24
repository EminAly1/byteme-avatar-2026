import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FormProvider,
  useForm,
  useFormContext,
  type DefaultValues,
  type FieldValues,
  type Resolver,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { ApiError, newCommand, send, type Command } from "../lib/api";
import { ErrorBox, Success } from "./ui";
import { loadPending, savePending, clearPending } from "../lib/pending";

interface Props<T extends FieldValues> {
  schema: z.ZodType<T>;
  defaults: DefaultValues<T>;
  path: string;
  label: string;
  confirmText: string;
  payload: (v: T) => unknown;
  onSuccess?: (result: unknown) => void;
  children: ReactNode;
}
export function CommandForm<T extends FieldValues>({
  schema,
  defaults,
  path,
  label,
  confirmText,
  payload,
  onSuccess,
  children,
}: Props<T>) {
  const [restored] = useState(() => loadPending(path));
  const form = useForm<T>({
    resolver: zodResolver(schema as never) as Resolver<T>,
    defaultValues: (restored?.values as DefaultValues<T>) || defaults,
  });
  const client = useQueryClient();
  const attempt = useRef<Command | null>(restored?.command || null);
  const [review, setReview] = useState<unknown | null>(null);
  const [uncertain, setUncertain] = useState(!!restored);
  const mutation = useMutation({
    mutationFn: () => send(attempt.current!),
    retry: false,
    onSuccess: (data) => {
      clearPending(path);
      attempt.current = null;
      setUncertain(false);
      void client.invalidateQueries();
      form.reset(defaults);
      onSuccess?.(data);
    },
    onError: (error) => {
      const unknown = error instanceof ApiError && error.uncertain;
      setUncertain(unknown);
      if (!unknown) {
        clearPending(path);
        attempt.current = null;
      }
    },
  });
  const locked = mutation.isPending || uncertain;
  useEffect(() => {
    if (!locked) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [locked]);
  function confirm() {
    attempt.current = newCommand(path, review);
    savePending({ command: attempt.current, values: form.getValues() });
    setReview(null);
    mutation.mutate();
  }
  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit((values) => {
          mutation.reset();
          setReview(payload(values));
        })}
        noValidate
      >
        <fieldset disabled={locked}>{children}</fieldset>
        {mutation.isError && <ErrorBox error={mutation.error} />}
        {mutation.isSuccess && (
          <Success>Kayıt backend tarafından onaylandı.</Success>
        )}
        {uncertain ? (
          <div className="retry-box">
            <p>
              İsteğin sonucu belirsiz. Form korunuyor; aynı içerik ve işlem
              anahtarıyla tekrar gönderin.
            </p>
            <button
              type="button"
              className="button primary"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              Aynı işlemi tekrar dene
            </button>
          </div>
        ) : (
          <button
            type="submit"
            className="button primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Kaydediliyor…" : label}
          </button>
        )}
      </form>
      {review !== null && (
        <div className="modal-backdrop">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            onKeyDown={(event) => {
              if (event.key === "Escape") setReview(null);
              if (event.key === "Tab") {
                const buttons = event.currentTarget.querySelectorAll("button"),
                  first = buttons[0],
                  last = buttons[buttons.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                  event.preventDefault();
                  last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                  event.preventDefault();
                  first.focus();
                }
              }
            }}
          >
            <h2 id="confirm-title">İşlemi onaylayın</h2>
            <p>{confirmText}</p>
            <p>
              Kaydetmeden önce girdiğiniz bilgilerin doğruluğunu kontrol edin.
            </p>
            <div className="actions">
              <button
                type="button"
                autoFocus
                className="button"
                onClick={() => setReview(null)}
              >
                Vazgeç
              </button>
              <button
                type="button"
                className="button primary"
                onClick={confirm}
              >
                Onayla ve kaydet
              </button>
            </div>
          </div>
        </div>
      )}
    </FormProvider>
  );
}
function errorAt(errors: unknown, path: string): string | undefined {
  let item = errors as Record<string, unknown>;
  for (const key of path.split(".")) {
    if (!item) return;
    item = item[key] as Record<string, unknown>;
  }
  if (typeof item?.message === "string") return item.message;
  const root = item?.root as Record<string, unknown> | undefined;
  return typeof root?.message === "string" ? root.message : undefined;
}
export function Field({
  name,
  label,
  type = "text",
  children,
  hint,
}: {
  name: string;
  label: string;
  type?: string;
  children?: ReactNode;
  hint?: string;
}) {
  const {
    register,
    formState: { errors },
  } = useFormContext();
  const error = errorAt(errors, name),
    id = "field-" + name;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children ? (
        <select
          id={id}
          {...register(name)}
          aria-invalid={!!error}
          aria-describedby={error ? id + "-error" : undefined}
        >
          {children}
        </select>
      ) : (
        <input
          id={id}
          type={type === "decimal" ? "text" : type}
          {...register(name)}
          autoComplete="off"
          inputMode={type === "decimal" ? "decimal" : undefined}
          aria-invalid={!!error}
          aria-describedby={error ? id + "-error" : undefined}
        />
      )}
      {hint && <small>{hint}</small>}
      {error && (
        <small id={id + "-error"} className="field-error">
          {error}
        </small>
      )}
    </div>
  );
}
export function ArrayError({ name }: { name: string }) {
  const {
    formState: { errors },
  } = useFormContext();
  const error = errorAt(errors, name);
  return error ? (
    <p className="field-error" role="alert">
      {error}
    </p>
  ) : null;
}
export function Options({
  items,
  placeholder = "Seçin",
}: {
  items: Array<{ id: string; name: string }>;
  placeholder?: string;
}) {
  return (
    <>
      <option value="">{placeholder}</option>
      {items.map((x) => (
        <option value={x.id} key={x.id}>
          {x.name}
        </option>
      ))}
    </>
  );
}
