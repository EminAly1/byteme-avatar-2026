import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import {
  distributionSchema,
  transferSchema,
  reworkDraftSchema,
  reworkCloseSchema,
  reworkClosePayload,
  cancelSchema,
  turkeyDate,
} from "../src/lib/operational-validation";
import { DistributionEvidence } from "../src/components/DistributionEvidence";
import { ProfitMetricsView } from "../src/components/Profitability";
import type { TraceReport } from "../src/lib/modules";
import type { SecondTier } from "../src/lib/operational-types";
const a = "00000000-0000-4000-8000-000000000001",
  b = "00000000-0000-4000-8000-000000000002";
const closing = () => ({
  output_location_id: a,
  outputs: [
    {
      product_id: b,
      lot_code: "KURGUSAL-NEW",
      quantity: "9,5",
      expires_at: "",
      explanation: "",
    },
  ],
  loss_quantity: "0,5",
  loss_kind: "other_loss" as const,
  loss_reason: "KURGUSAL ölçüm",
  service_amount: "15,00",
  invoice_reference: "KURGUSAL-REF",
});
describe("operasyon girişleri ve gerçek şema gövdeleri", () => {
  it.each(["0", "-1", "1.1234567", "NaN"])(
    "geçersiz %s dağıtım miktarını reddeder",
    (quantity) => {
      expect(
        distributionSchema.safeParse({
          source_shipment_line_id: a,
          recipient_party_id: b,
          quantity,
          distributed_at: "2026-10-27T12:30",
          reference: "R",
          evidence_note: "N",
        }).success,
      ).toBe(false);
    },
  );
  it.each(["2026-02-30T12:00", "2026-10-27T25:00", "", "2026-10-27T12:00Z"])(
    "geçersiz yerel tarihi reddeder: %s",
    (value) => expect(turkeyDate.safeParse(value).success).toBe(false),
  );
  it("Türkiye saatini kayıpsız UTC isteğine çevirebilir", () => {
    expect(turkeyDate.safeParse("2026-10-27T12:30:40.123").success).toBe(true);
    expect(new Date("2026-10-27T12:30:40.123+03:00").toISOString()).toBe(
      "2026-10-27T09:30:40.123Z",
    );
  });
  it("aynı kaynak ve hedefi reddeder", () => {
    expect(
      transferSchema.safeParse({
        source: a + "|" + b,
        to_location_id: b,
        quantity: "7",
        reason: "T",
        reference: "",
      }).success,
    ).toBe(false);
  });
  it("rework taslağı ürün seçimi ister; kesin stok veya maliyet hesabı içermez", () => {
    expect(
      reworkDraftSchema.safeParse({
        code: "R",
        source: a + "|" + b,
        input_quantity: "10",
        reason: "N",
        output_product_ids: [],
      }).success,
    ).toBe(false);
  });
  it("rework 10=9,5+0,5 ve açık gerçek hizmet gövdesini korur", () => {
    const values = closing();
    expect(reworkCloseSchema("10").safeParse(values).success).toBe(true);
    const body = reworkClosePayload(values);
    expect(body.outputs[0]).toEqual({
      product_id: b,
      lot_code: "KURGUSAL-NEW",
      quantity: "9.5",
      unit: "kg",
    });
    expect(body.differences).toEqual([
      { kind: "other_loss", quantity: "0.5", reason: "KURGUSAL ölçüm" },
    ]);
    expect(body.service_costs).toEqual([
      { amount: "15.00", invoice_reference: "KURGUSAL-REF" },
    ]);
    expect(values.outputs[0].quantity).toBe("9,5");
  });
  it.each(["loss_reason", "invoice_reference"] as const)(
    "kesin kapanışta gerekli açıklamayı ister: %s",
    (key) => {
      const values = closing();
      values[key] = "";
      expect(reworkCloseSchema("10").safeParse(values).success).toBe(false);
    },
  );
  it("bedelsiz/kayıpsız kapanışta açık boş hizmet ve fark dizisi gönderir", () => {
    const values = closing();
    values.outputs[0].quantity = "10";
    values.loss_quantity = "0";
    values.loss_reason = "";
    values.service_amount = "0";
    values.invoice_reference = "";
    expect(reworkCloseSchema("10").safeParse(values).success).toBe(true);
    expect(reworkClosePayload(values)).toMatchObject({
      service_costs: [],
      differences: [],
    });
  });
  it("kayıp denge hatası ve çift lot kodunu reddeder", () => {
    const values = closing();
    values.outputs[0].quantity = "8";
    expect(reworkCloseSchema("10").safeParse(values).success).toBe(false);
    values.outputs.push({ ...values.outputs[0] });
    expect(reworkCloseSchema("16.5").safeParse(values).success).toBe(false);
  });
  it("iptalde uyarı onayı zorunludur", () =>
    expect(
      cancelSchema.safeParse({
        acceptance_location_id: a,
        reason: "N",
        acknowledged: false,
      }).success,
    ).toBe(false));
});
it("gerçek kayıt yoksa ikinci kademe bilinmiyor kalır", () => {
  render(
    <MemoryRouter>
      <DistributionEvidence
        customerId={a}
        report={
          {
            second_tier_distributions: [],
            unknown_distributions: [],
            lots: [],
          } as unknown as TraceReport
        }
      />
    </MemoryRouter>,
  );
  expect(screen.getByText("Bilinmiyor")).toBeVisible();
});
it("kayıtlı X, 12 paket ve belgelenmiş 18 gösterilir; fiziksel stok olduğu söylenmez", () => {
  const record = {
    id: b,
    source_customer_id: a,
    recipient_name: "KURGUSAL X",
    quantity: "12",
    unit: "package",
    reference: "REF",
    distributed_at: "2026-10-27T09:00:00Z",
    recipient_contact: null,
  } as SecondTier;
  const report = {
    second_tier_distributions: [record],
    unknown_distributions: [
      {
        customer_id: a,
        unallocated_documented_quantities: [
          {
            source_shipment_line_id: b,
            lot_id: a,
            quantity: "18",
            unit: "package",
            physical_stock: false,
          },
        ],
      },
    ],
    lots: [],
  } as unknown as TraceReport;
  render(
    <MemoryRouter>
      <DistributionEvidence customerId={a} report={report} />
    </MemoryRouter>,
  );
  expect(screen.getByText("KURGUSAL X")).toBeVisible();
  expect(screen.getByText(/12 paket/)).toBeVisible();
  expect(screen.getByText("18 paket")).toBeVisible();
  expect(
    screen.getByText(
      "Belgelenmiş tahsis edilmemiş miktar — fiziksel stok doğrulanmadı",
    ),
  ).toBeVisible();
  expect(screen.queryByText("Bilinmiyor")).not.toBeInTheDocument();
});
it("kârlılık backend sayılarını Türkçe gösterir; sıfır gelirde marj uydurmaz", () => {
  render(
    <ProfitMetricsView
      metrics={{
        net_revenue_eur: "0.00",
        recognized_cost_eur: "18.158824",
        gross_profit_eur: "-18.158824",
        gross_profit_display_eur: "-18.16",
        margin_percent: null,
      }}
    />,
  );
  expect(screen.getByText("0,00 €")).toBeVisible();
  expect(screen.getByText("18,158824 €")).toBeVisible();
  expect(screen.getByText("-18,16 €")).toBeVisible();
  expect(screen.getByText("Hesaplanamıyor")).toBeVisible();
});
