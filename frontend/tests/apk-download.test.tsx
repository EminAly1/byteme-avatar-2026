import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import ApkDownloadDialog from "../src/features/apk-download/ApkDownloadDialog";

const active = () => ({ state: "active", url: `http://192.168.1.20:8765/download/${"f".repeat(43)}`,
  version: "0.1.0-preview.2", bytes: 17178340, sha256: "a".repeat(64), expiresAt: Date.now() + 180000 });
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const close = vi.fn();
  const view = render(<QueryClientProvider client={client}><ApkDownloadDialog onClose={close} /></QueryClientProvider>);
  return { ...view, client, close };
}
function reply(value: unknown) { return new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } }); }
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

it("paylaşım yokken QR üretmez ve güvenli başlatma adımlarını gösterir", async () => {
  const fetch = vi.fn().mockResolvedValue(reply({ state: "inactive" })); vi.stubGlobal("fetch", fetch);
  const { close } = mount();
  expect(await screen.findByText("APK paylaşımı henüz başlatılmadı.")).toBeInTheDocument();
  expect(screen.queryByRole("img", { name: /QR kodu/ })).not.toBeInTheDocument();
  expect(screen.getByText(/--bind WIFI_IPV4_ADRESINIZ/)).toBeInTheDocument();
  expect(fetch.mock.calls[0][1].headers).toEqual({ "X-Avatar-Apk-Status": "1" });
  fireEvent.click(screen.getByRole("button", { name: "Ayrıntıyı kapat" })); expect(close).toHaveBeenCalledOnce();
});
it("gerçek durumdan yerel QR ve metadata oluşturur, yalnız açık istekle kopyalar, saklamaz", async () => {
  const status = active();
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(reply(status))));
  const copy = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText: copy }, configurable: true });
  const { unmount, client } = mount();
  expect(await screen.findByRole("img", { name: /QR kodu/ })).toBeInTheDocument();
  expect(screen.getByText(status.sha256)).toBeInTheDocument();
  expect((screen.getByRole("textbox", { name: "Geçici indirme bağlantısı" }) as HTMLInputElement).value === status.url).toBe(true);
  expect(copy).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "İndirme bağlantısını kopyala" }));
  expect(await screen.findByText("Bağlantı kopyalandı")).toBeInTheDocument();
  expect(copy.mock.calls[0][0] === status.url).toBe(true);
  expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
  unmount(); await waitFor(() => expect(client.getQueryData(["apk-share"])).toBeUndefined());
});
it("kontrol et yeni token üretmez; istek hatası önceki QR'ı gizler", async () => {
  const status = active();
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(reply(status))); vi.stubGlobal("fetch", fetch);
  mount(); await screen.findByRole("img", { name: /QR kodu/ });
  fireEvent.click(screen.getByRole("button", { name: "Paylaşımı kontrol et" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect((screen.getByRole("textbox") as HTMLInputElement).value === status.url).toBe(true);
  fetch.mockRejectedValue(new Error("offline"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Paylaşımı kontrol et" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Paylaşımı kontrol et" }));
  await screen.findByText(/Yerel APK paylaşımına erişilemiyor/);
  expect(screen.queryByRole("img", { name: /QR kodu/ })).not.toBeInTheDocument();
});
it("süre dolunca QR ve kopyalama kaybolur", async () => {
  const status = { ...active(), expiresAt: Date.now() + 2000 };
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(reply(status))));
  mount(); await screen.findByRole("img", { name: /QR kodu/ });
  vi.spyOn(Date, "now").mockReturnValue(status.expiresAt + 1000);
  await waitFor(() => expect(screen.queryByRole("img", { name: /QR kodu/ })).not.toBeInTheDocument());
  expect(screen.getByText(/Paylaşımın süresi doldu/)).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
it.each(["local_only", "used", "unavailable"])("%s durumunda indirilebilir QR göstermez", async (state) => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(reply({ state }))));
  mount(); await waitFor(() => expect(screen.queryByText("Yerel paylaşım kontrol ediliyor…")).not.toBeInTheDocument());
  expect(screen.queryByRole("img", { name: /QR kodu/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
});
