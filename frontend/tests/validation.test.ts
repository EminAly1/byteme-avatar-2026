import { describe, expect, it } from "vitest";
import {
  closeSchema,
  money,
  quantity,
  productSchema,
  receiptSchema,
} from "../src/lib/validation";
import { receiptPayload, closePayload } from "../src/lib/payloads";
import { amount, eur } from "../src/lib/format";
const a = "5db2ffcb-3342-4d08-99ce-2387d8d30730",
  b = "cd46e91a-167a-427a-aefc-b3f6cd71bb03";

describe("API giriş doğrulaması", () => {
  it.each(["-1", "0", "0.0000001", "1e3", "1.234.567", "1000000000000"])(
    "geçersiz miktarı reddeder: %s",
    (v) => expect(quantity.safeParse(v).success).toBe(false),
  );
  it.each(["-1", "1.123", "1e6", "1000000000000"])(
    "geçersiz tutarı reddeder: %s",
    (v) => expect(money.safeParse(v).success).toBe(false),
  );
  it("paket için pozitif dönüşüm ister", () => {
    const p = {
      sku: "SKU",
      name: "Ürün",
      type: "finished",
      base_unit: "package",
      package_weight_kg: "",
    };
    expect(productSchema.safeParse(p).success).toBe(false);
    expect(
      productSchema.safeParse({ ...p, package_weight_kg: "1" }).success,
    ).toBe(true);
  });
  it("çok satırlı alışı API string alanlarına dönüştürür", () => {
    const v = receiptSchema.parse({
      supplier_id: a,
      location_id: b,
      reference: "",
      lines: [
        {
          product_id: a,
          external_lot_code: "ET",
          quantity: "100,125000",
          total_cost: "970,50",
          expires_at: "",
        },
        {
          product_id: b,
          external_lot_code: "BAH",
          quantity: "2",
          total_cost: "48",
          expires_at: "2027-01-01",
        },
      ],
    });
    const body = receiptPayload(v);
    expect(body.lines[0]).toMatchObject({
      quantity: "100.125000",
      total_cost: "970.50",
      expires_at: null,
    });
    expect(typeof body.lines[1].quantity).toBe("string");
    expect(body.reference).toBeNull();
  });
  it("miktar farkı için açıklama, kapanış için eşleşen kaynak ister", () => {
    const v = {
      consumed_inputs: [{ source: a + "|" + b, quantity: "100" }],
      returned_inputs: [],
      outputs: [
        { product_id: a, lot_code: "SUC", quantity: "85", expires_at: "" },
      ],
      output_location_id: b,
      service_amount: "467,50",
      invoice_reference: "",
      loss_quantity: "15",
      loss_reason: "",
    };
    expect(closeSchema.safeParse(v).success).toBe(false);
    const parsed = closeSchema.parse({ ...v, loss_reason: "Kayıtlı fark" });
    expect(closePayload(parsed).consumed_inputs[0]).toEqual({
      lot_id: a,
      location_id: b,
      quantity: "100",
    });
    expect(closePayload(parsed).service_costs?.[0].amount).toBe("467.50");
  });
  it("büyük ondalıkları float kaybı olmadan gösterir; maliyet hesaplamaz", () => {
    expect(amount("999999999999.123456")).toBe("999.999.999.999,123456");
    expect(eur("1543.500000")).toBe("1.543,50 €");
    expect(eur("18.16")).toBe("18,16 €");
    expect(eur("0.333333")).toBe("0,333333 €");
  });
});
