import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { DocumentSheet } from "../src/components/DocumentSheet";
import { Documents, SaleDocument } from "../src/pages/Documents";
import {
  fetchDocumentPdf,
  initialDraft,
  type DocumentSource,
} from "../src/lib/documents";

const id = "00000000-0000-4000-8000-000000000018";
const source: DocumentSource = {
  sale_id: id,
  sold_at: "2026-10-27T10:00:00+00:00",
  currency: "EUR",
  source_fingerprint: "a".repeat(64),
  customer: { id, name: "KURGUSAL İğde Şarküteri", contact: null },
  customer_basis: "current_party_record_not_historical_billing_snapshot",
  original_total_eur: "39.40",
  state: "active",
  state_label: "Aktif satış",
  return_credit_eur: "0.00",
  cancellation_credit_eur: "0.00",
  net_after_adjustments_eur: "39.40",
  payment_status: "not_recorded",
  cash_refund_status: "not_recorded",
  tax_information: "not_recorded",
  lines: [
    {
      id,
      line_no: 1,
      product_id: id,
      product_name: "KURGUSAL ğ ü ş ı İ ö ç",
      sku: "DOC",
      lot_id: id,
      lot_code: "KURGUSAL-LOT-18",
      quantity: "2.500000",
      unit: "kg",
      unit_price_eur: "1.23",
      total_eur: "3.08",
    },
  ],
  shipments: [],
  corrections: [],
};
function wrap(children: React.ReactNode, path = "/belgeler") {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}
function editor() {
  return wrap(
    <Routes>
      <Route path="/belgeler/satis/:id/*" element={<SaleDocument />} />
    </Routes>,
    "/belgeler/satis/" + id,
  );
}
afterEach(() => vi.unstubAllGlobals());

it("kesin satırları ve toplamı kaynaktan gösterir; HTML metindir, kilitli alanlarda input yoktur", () => {
  const note = "<script>alert(1)</script> ğ ü ş ı İ ö ç";
  wrap(
    <DocumentSheet
      source={Object.freeze(source)}
      kind="proforma"
      draft={{ ...initialDraft(), note, demo: true }}
    />,
  );
  const sheet = screen.getByRole("article");
  expect(sheet).toHaveTextContent("2,5 kg");
  expect(sheet).toHaveTextContent("3,08 €");
  expect(sheet).toHaveTextContent("39,40 €");
  expect(sheet).toHaveTextContent(note);
  expect(sheet.querySelector("script")).toBeNull();
  expect(sheet.querySelector("input")).toBeNull();
  expect(sheet).toHaveTextContent("RESMÎ FATURA DEĞİLDİR");
  expect(sheet).toHaveTextContent("KURGUSAL DEMO");
  expect(sheet).toHaveTextContent("Vergi/KDV bilgisi kayıtlı değil");
  expect(sheet).not.toHaveTextContent("Brüt kâr");
});

it.each([
  ["returned", "Tam iade"],
  ["cancelled", "İptal edilmiş satış"],
])("%s kaydını güncel ödeme talebi olarak sunmaz", (state, label) => {
  wrap(
    <DocumentSheet
      source={{
        ...source,
        state: state as "returned" | "cancelled",
        state_label: label,
        net_after_adjustments_eur: "0.00",
      }}
      kind="sale_summary"
      draft={initialDraft()}
    />,
  );
  expect(screen.getByRole("article")).toHaveTextContent(
    "GÜNCEL ÖDEME TALEBİ DEĞİLDİR",
  );
  expect(screen.getByRole("article")).toHaveTextContent(
    "SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR",
  );
});

it("kısmi iadeyi orijinalden ayrı gösterir; sevkiyat yalnız gerçek bağlantıdan gelir", () => {
  wrap(
    <DocumentSheet
      source={{
        ...source,
        state: "partially_returned",
        state_label: "Kısmi iade",
        return_credit_eur: "1.23",
        net_after_adjustments_eur: "38.17",
        corrections: [
          {
            id,
            kind: "return",
            recorded_at: source.sold_at,
            reason: "KURGUSAL hasar",
            credit_eur: "1.23",
            lines: [
              {
                sale_line_id: id,
                lot_id: id,
                quantity: "1.000000",
                unit: "kg",
                credit_eur: "1.23",
              },
            ],
          },
        ],
        shipments: [
          {
            id,
            shipped_at: source.sold_at,
            recipient_name: "KURGUSAL alıcı",
            recipient_contact: null,
            lines: [
              {
                sale_line_id: id,
                lot_id: id,
                quantity: "2.500000",
                unit: "kg",
              },
            ],
          },
        ],
      }}
      kind="proforma"
      draft={initialDraft()}
    />,
  );
  expect(screen.getByRole("article")).toHaveTextContent("KISMİ İADE");
  expect(screen.getByRole("article")).toHaveTextContent("38,17 €");
  expect(screen.getByRole("article")).toHaveTextContent("KURGUSAL hasar");
  expect(screen.getByRole("article")).toHaveTextContent("KURGUSAL alıcı");
});

it("geçici not ayrı düzenleme ekranında uygulanır; yalnız kaynak GET yapılır, satış değişmez", async () => {
  const fetch = vi.fn().mockImplementation(async () => Response.json(source));
  vi.stubGlobal("fetch", fetch);
  editor();
  await screen.findByRole("article");
  await userEvent
    .setup()
    .click(screen.getByRole("link", { name: "Taslak düzenle" }));
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
  await userEvent
    .setup()
    .type(
      screen.getByLabelText(/^Özel not/),
      "KURGUSAL teslimat ğ ü ş ı İ ö ç",
    );
  await userEvent
    .setup()
    .click(
      screen.getByRole("button", {
        name: "Değişiklikleri bu görünümde uygula",
      }),
    );
  expect(screen.queryByLabelText(/^Özel not/)).not.toBeInTheDocument();
  expect(screen.getByRole("article")).toHaveTextContent(
    "KURGUSAL teslimat ğ ü ş ı İ ö ç",
  );
  expect(source.original_total_eur).toBe("39.40");
  expect(source.lines[0].quantity).toBe("2.500000");
  expect(
    fetch.mock.calls.every(
      ([, options]) => !options.method || options.method === "GET",
    ),
  ).toBe(true);
  expect(
    screen.getByRole("link", { name: "Kaynak satışa dön" }),
  ).toHaveAttribute("href", "/satislar/" + id);
  expect(screen.getByRole("button", { name: "PDF indir" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Yazdır" })).toBeVisible();
});

it("boş satış listesinde belge veya fiyat üretmez; liste tek sayfa ile sınırlıdır", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(Response.json({ items: [], next_cursor: null }));
  vi.stubGlobal("fetch", fetch);
  wrap(<Documents />);
  expect(await screen.findByText(/Henüz kayıtlı satış yok/)).toBeVisible();
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/sales?limit=20");
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
});

it("geçersiz kaynak veya API hatası halinde dışa aktarma göstermez", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ error: { code: "NOT_FOUND" } }, { status: 404 }),
      ),
  );
  editor();
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "PDF indir" }),
  ).not.toBeInTheDocument();
});

it("PDF istemcisi yalnız sale UUID, fingerprint ve izinli taslağı gönderir; anahtar veya kesin tutar göndermez", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response("%PDF-test-unit-only", {
        headers: { "content-type": "application/pdf" },
      }),
    );
  vi.stubGlobal("fetch", fetch);
  const draft = { ...initialDraft(), note: "KURGUSAL not" };
  const blob = await fetchDocumentPdf(source, "proforma", draft);
  expect(blob.type).toBe("application/pdf");
  const [, options] = fetch.mock.calls[0];
  expect(JSON.parse(options.body)).toEqual({
    sale_id: id,
    kind: "proforma",
    expected_source_fingerprint: source.source_fingerprint,
    draft,
  });
  expect(Object.keys(options.headers)).toEqual(["Content-Type"]);
  expect(options.body).not.toContain("39.40");
});

it.each([
  ["text/html", "<html>error</html>"],
  ["application/pdf", "not-a-pdf"],
])("yanlış MIME veya içerikte dosya indirmez: %s", async (mime, body) => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(body, { headers: { "content-type": mime } }),
      ),
  );
  await expect(
    fetchDocumentPdf(source, "proforma", initialDraft()),
  ).rejects.toMatchObject({ code: "DOCUMENT_PDF_FORMAT" });
});

it("PDF kaynağı değişince 409 hatasını anlaşılır gösterir", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json(
          { error: { code: "DOCUMENT_SOURCE_CHANGED" } },
          { status: 409 },
        ),
      ),
  );
  await expect(
    fetchDocumentPdf(source, "proforma", initialDraft()),
  ).rejects.toMatchObject({ status: 409, code: "DOCUMENT_SOURCE_CHANGED" });
});
