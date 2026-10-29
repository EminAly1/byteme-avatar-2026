import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { RecallWizard } from "../src/components/RecallWizard";
import type { RecallPreview, TraceReport } from "../src/lib/modules";

const lot = "00000000-0000-4000-8000-000000000001";
const product = { id: "product", created_at: "2026-10-29T08:00:00Z", sku: "FOOD", name: "Kurgusal et", type: "raw", base_unit: "kg" };
const source = { id: lot, external_code: "ET-2026-001", product_id: product.id, product, blocked: false };
const report = {
  source_lot: source, lots: [source], stocks: [], buyers: [], shipments: [],
  second_tier_distributions: [], context_lots: [], operations: [], edges: [],
  total_shipped_quantities: [], unknown_distributions: [],
} as unknown as TraceReport;
const preview: RecallPreview = { preview_fingerprint: "recall-v1:" + "a".repeat(64), report };
function apiMock(write = vi.fn().mockResolvedValue(Response.json({ id: "saved" }, { status: 201 }))) {
  const fetch = vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === "POST") return write(url, options);
    if (url.includes("/recalls/preview")) return Response.json(preview);
    const items = url.includes("/lots") ? [source] : url.includes("/products") ? [product] : [];
    return Response.json({ items, next_cursor: null });
  });
  vi.stubGlobal("fetch", fetch);
  return { fetch, write };
}
function mount() {
  const success = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const rendered = render(<MemoryRouter><QueryClientProvider client={client}>
    <RecallWizard onSuccess={success} />
  </QueryClientProvider></MemoryRouter>);
  return { ...rendered, success, client };
}
async function choose(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(await screen.findByLabelText("Sorunlu kaynak lot"), lot);
  await screen.findByRole("heading", { name: "Etkilenen lotlar ve kayıtlı şirket stoğu" });
}
async function review(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Gerekçe ve riske ilerle" }));
  await user.type(screen.getByLabelText(/Geri çağırma nedeni/), "KURGUSAL kalite kontrol");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı gözden geçir" }));
  return screen.findByRole("dialog");
}
afterEach(() => vi.unstubAllGlobals());

it("kaynak seçimi ve önizleme yazmaz; gerekçe ve doğru elle lot kodu olmadan kesinleştiremez", async () => {
  const { write } = apiMock(), user = userEvent.setup(), mounted = mount();
  expect(screen.getByText(/bir kaynak lot seçin/)).toBeVisible();
  await choose(user);
  expect(write).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Gerekçe ve riske ilerle" }));
  expect(screen.getByText(/otomatik blok kaldırma bulunmuyor/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Geri çağırmayı gözden geçir" })).toBeDisabled();
  await user.type(screen.getByLabelText(/Geri çağırma nedeni/), "   ");
  expect(screen.getByRole("button", { name: "Geri çağırmayı gözden geçir" })).toBeDisabled();
  await user.clear(screen.getByLabelText(/Geri çağırma nedeni/));
  await user.type(screen.getByLabelText(/Geri çağırma nedeni/), "KURGUSAL risk");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı gözden geçir" }));
  const dialog = within(await screen.findByRole("dialog"));
  const finalize = dialog.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et" });
  expect(finalize).toBeDisabled();
  await user.type(dialog.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-002");
  expect(finalize).toBeDisabled(); expect(write).not.toHaveBeenCalled();
  expect(dialog.getByText(/Lot kodu eşleşmiyor/)).toBeVisible();
  await user.clear(dialog.getByLabelText("Kaynak lot kodunu elle yazın"));
  await user.type(dialog.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-001");
  await user.click(finalize);
  await waitFor(() => expect(mounted.success).toHaveBeenCalledOnce());
  const body = JSON.parse(write.mock.calls[0][1].body);
  expect(body).toMatchObject({ source_lot_id: lot, preview_fingerprint: preview.preview_fingerprint, confirmation_lot_code: "ET-2026-001" });
});

it("vazgeçme kesin istek üretmez; geri dönüldüğünde gerekçe korunur, kod yeniden gerekir", async () => {
  const { write } = apiMock(), user = userEvent.setup(); mount();
  await choose(user); await review(user);
  await user.click(screen.getByRole("button", { name: "Vazgeç" }));
  expect(screen.getByLabelText(/Geri çağırma nedeni/)).toHaveValue("KURGUSAL kalite kontrol");
  expect(write).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Kaynak ve etkiye dön" }));
  await user.click(screen.getByRole("button", { name: "Gerekçe ve riske ilerle" }));
  expect(screen.getByLabelText(/Geri çağırma nedeni/)).toHaveValue("KURGUSAL kalite kontrol");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı gözden geçir" }));
  expect(screen.getByLabelText("Kaynak lot kodunu elle yazın")).toHaveValue("");
});

it("belirsiz sonuç/reload aynı key/body ile tekrar edilir, yeni kaynak veya yeni komut açılmaz", async () => {
  const write = vi.fn().mockRejectedValueOnce(new TypeError("lost response"))
    .mockResolvedValueOnce(Response.json({ id: "saved" }, { status: 201 }));
  apiMock(write); const user = userEvent.setup(), mounted = mount();
  await choose(user); await review(user);
  await user.type(screen.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-001");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et" }));
  await screen.findByRole("button", { name: "Aynı işlemi tekrar dene" });
  expect(screen.queryByLabelText("Sorunlu kaynak lot")).not.toBeInTheDocument();
  mounted.unmount(); const restored = mount();
  await user.click(screen.getByRole("button", { name: "Aynı işlemi tekrar dene" }));
  await waitFor(() => expect(restored.success).toHaveBeenCalledOnce());
  expect(write.mock.calls[0][1].headers["Idempotency-Key"]).toBe(write.mock.calls[1][1].headers["Idempotency-Key"]);
  expect(write.mock.calls[0][1].body).toBe(write.mock.calls[1][1].body);
  expect(sessionStorage.getItem("avatar.pending:/recalls")).toBeNull();
});

it("güncel kapsam değişirse onay kapanır, kaynak incelemesine döner ve blok uydurmaz", async () => {
  const write = vi.fn().mockResolvedValue(Response.json({ error: { code: "RECALL_PREVIEW_STALE" } }, { status: 409 }));
  const { fetch } = apiMock(write); const user = userEvent.setup(); mount();
  await choose(user); await review(user);
  await user.type(screen.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-001");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et" }));
  await screen.findByText(/Kaynak veya etki kapsamı değişti/);
  expect(await screen.findByLabelText("Sorunlu kaynak lot")).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(sessionStorage.getItem("avatar.pending:/recalls")).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.includes("/recalls/preview"))).toHaveLength(2);
});

it("gönderim sürerken tekrar tıklanamaz", async () => {
  let finish!: (r: Response) => void;
  const write = vi.fn(() => new Promise<Response>(resolve => { finish = resolve; }));
  apiMock(write); const user = userEvent.setup(), mounted = mount();
  await choose(user); await review(user);
  await user.type(screen.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-001");
  await user.dblClick(screen.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et" }));
  expect(write).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Yanıt bekleniyor…" })).toBeDisabled();
  finish(Response.json({ id: "saved" }, { status: 201 }));
  await waitFor(() => expect(mounted.success).toHaveBeenCalledOnce());
});

it("genel yenileme incelenmiş kapsamı sessizce değiştiremez; kesin komut ilk incelenen izi taşır", async () => {
  const { fetch, write } = apiMock(), user = userEvent.setup(), mounted = mount();
  await choose(user); await review(user);
  await mounted.client.invalidateQueries();
  expect(fetch.mock.calls.filter(([path]) => path.includes("/recalls/preview"))).toHaveLength(1);
  // Even a different cache value cannot rewrite the local reviewed snapshot.
  mounted.client.setQueryData(["recall-preview", lot], { ...preview, preview_fingerprint: "recall-v1:" + "b".repeat(64) });
  await user.type(screen.getByLabelText("Kaynak lot kodunu elle yazın"), "ET-2026-001");
  await user.click(screen.getByRole("button", { name: "Geri çağırmayı kesinleştir ve lotları bloke et" }));
  await waitFor(() => expect(mounted.success).toHaveBeenCalledOnce());
  expect(JSON.parse(write.mock.calls[0][1].body).preview_fingerprint).toBe(preview.preview_fingerprint);
});
