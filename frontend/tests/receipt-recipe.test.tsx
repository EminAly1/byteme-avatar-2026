import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { Receipts } from "../src/pages/Receipts";
import { Cuttings } from "../src/pages/Cutting";
const id = "00000000-0000-4000-8000-000000000028";
const product = { id, created_at: "2026-10-31T09:00:00Z", sku: "TEST-28", name: "TEST kuzu", type: "raw", base_unit: "kg", package_weight_kg: null };
const receipt = { id, supplier_id: id, location_id: id, received_at: "2026-10-31T09:00:00Z", reference: "TEST alış", supplier_name: "TEST tedarikçi", location_name: "TEST depo", total_cost: "10.00", lines: [{ id, product_id: id, lot_id: id, product_name: "TEST kuzu", lot_code: "TEST-LOT", unit: "kg", quantity: "2.5", total_cost: "10.00" }] };
function mock(list = true) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") return Response.json(receipt);
    if (url.endsWith("/receipts/" + id)) return Response.json(receipt);
    let items: unknown[] = [];
    if (url.includes("/products?")) items = [product];
    if (url.includes("/parties?")) items = [{ id, name: "TEST tedarikçi", roles: ["supplier"] }];
    if (url.includes("/locations?")) items = [{ id, name: "TEST depo", kind: "warehouse" }];
    if (url.includes("/receipts?") && list) items = [receipt];
    return Response.json({ items, next_cursor: null });
  }); vi.stubGlobal("fetch", fetch); return fetch;
}
function mount(component: React.ReactNode) { return render(<MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{component}</QueryClientProvider></MemoryRouter>); }
afterEach(() => vi.unstubAllGlobals());
it("Görüntüle gerçek GET ayrıntısını drawer'da açar; kapatınca odağı geri verir, yazmaz", async () => {
  const fetch = mock(); mount(<Receipts />); const user = userEvent.setup();
  const opener = await screen.findByRole("button", { name: "Görüntüle" }); await user.click(opener);
  expect(await screen.findByRole("dialog", { name: "Alış ayrıntıları" })).toBeVisible();
  expect(screen.getByText("TEST-LOT")).toBeVisible();
  expect(screen.getAllByText("10,00 €").length).toBeGreaterThan(0);
  expect(fetch.mock.calls.some(([,init]) => init?.method === "POST")).toBe(false);
  await user.click(screen.getByLabelText("Ayrıntıyı kapat"));
  await waitFor(() => expect(opener).toHaveFocus());
});
it("yeni alış onayından sonra ayrıntı drawer'ı otomatik açılır", async () => {
  const fetch = mock(false); mount(<Receipts />); const user = userEvent.setup();
  await screen.findByLabelText("Tedarikçi");
  await user.selectOptions(screen.getByLabelText("Tedarikçi"), id);
  await user.selectOptions(screen.getByLabelText("Kabul deposu"), id);
  await user.selectOptions(screen.getByLabelText("Ürün 1"), id);
  await user.type(screen.getByLabelText("Lot numarası 1"), "TEST-LOT");
  await user.type(screen.getByLabelText("Miktar 1"), "2,5");
  await user.type(screen.getByLabelText("Toplam maliyet 1 (EUR)"), "10");
  await user.click(screen.getByRole("button", { name: "Alışı kaydet" }));
  await user.click(await screen.findByRole("button", { name: "Onayla ve kaydet" }));
  expect(await screen.findByRole("dialog", { name: "Alış ayrıntıları" })).toBeVisible();
  await waitFor(() => expect(fetch.mock.calls.filter(([,init]) => init?.method === "POST")).toHaveLength(1));
});
it("boş parça filtresi nedenini ve gerçek kg ürün oluşturma kısayolunu gösterir", async () => {
  mock(); mount(<Cuttings />); const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Yeni reçete" }));
  expect(screen.getByText("Uygun parça ürünü bulunamadı")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Parça ürünü oluştur" }));
  expect(screen.getByRole("dialog", { name: "Parça ürünü oluştur" })).toBeVisible();
  expect(screen.getByLabelText("Ürün türü")).toHaveValue("finished");
  expect(screen.getByLabelText("Stok birimi")).toHaveValue("kg");
});
