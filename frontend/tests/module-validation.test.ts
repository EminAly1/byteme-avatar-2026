import { describe, it, expect } from "vitest";
import { balance, micro } from "../src/lib/quantity";
import {
  recipeSchema,
  cuttingCloseSchema,
  saleSchema,
  cuttingPredictionSchema,
  productionPredictionSchema,
} from "../src/lib/module-validation";
import {
  cuttingPostPayload,
  linkedShipmentPayload,
  productionPredictionPayload,
  salePayload,
} from "../src/lib/module-payloads";
import type { SaleDetail } from "../src/lib/modules";
const ids = Array.from(
  { length: 8 },
  (_, i) => `00000000-0000-4000-8000-${String(i + 1).padStart(12, "0")}`,
);
const close = {
  source: ids[0] + "|" + ids[1],
  quantity: "25",
  output_location_id: ids[1],
  outputs: [
    {
      product_id: ids[2],
      lot_code: "PART",
      quantity: "22",
      expires_at: "",
      explanation: "",
      byproduct: false,
    },
  ],
  differences: [
    { kind: "waste" as const, quantity: "3", reason: "Ölçülmüş test farkı" },
  ],
};
describe("işlem öncesi doğrulama; kesin maliyet hesaplamaz", () => {
  it("kg dengesini ondalık metinle ve tam hassasiyetle kontrol eder", () => {
    expect(balance("0,3", ["0.1", "0.2"], [])?.balanced).toBe(true);
    expect(balance("25", ["22"], ["3"])?.balanced).toBe(true);
    expect(balance("25", ["22"], [])?.balanced).toBe(false);
    expect(micro("NaN")).toBeNull();
    expect(micro("Infinity")).toBeNull();
    expect(micro("-1")).toBeNull();
  });
  it("eksik fark ve açıklamasız farkı reddeder", () => {
    expect(
      cuttingCloseSchema.safeParse({ ...close, differences: [] }).success,
    ).toBe(false);
    expect(
      cuttingCloseSchema.safeParse({
        ...close,
        differences: [{ kind: "waste", quantity: "3", reason: "" }],
      }).success,
    ).toBe(false);
    expect(cuttingCloseSchema.safeParse(close).success).toBe(true);
  });
  it("yan ürün için stoklanan çıktı ve açıklama ister; fire türü olarak kabul etmez", () => {
    expect(
      cuttingCloseSchema.safeParse({
        ...close,
        outputs: [{ ...close.outputs[0], byproduct: true }],
      }).success,
    ).toBe(false);
    expect(
      cuttingCloseSchema.safeParse({
        ...close,
        outputs: [
          {
            ...close.outputs[0],
            byproduct: true,
            explanation: "Ayrı yan ürün kaydı",
          },
        ],
      }).success,
    ).toBe(true);
    expect(
      cuttingCloseSchema.safeParse({
        ...close,
        differences: [{ kind: "byproduct", quantity: "3", reason: "Yan ürün" }],
      }).success,
    ).toBe(false);
  });
  it("value reçetesinde pozitif referans ve tekil ürünleri doğrular", () => {
    const v = {
      code: "R",
      version: "1",
      species: "Kuzu",
      input_product_id: ids[0],
      allocation_method: "value",
      lines: [{ product_id: ids[2], reference_eur_per_kg: "" }],
    };
    expect(recipeSchema.safeParse(v).success).toBe(false);
    expect(
      recipeSchema.safeParse({
        ...v,
        lines: [{ product_id: ids[2], reference_eur_per_kg: "20,00" }],
      }).success,
    ).toBe(true);
    expect(
      recipeSchema.safeParse({
        ...v,
        allocation_method: "quantity",
        lines: [v.lines[0], v.lines[0]],
      }).success,
    ).toBe(false);
  });
  it("kesim payloadında UI byproduct alanını çıkarır; miktarlar string kalır", () => {
    const p = cuttingPostPayload({ ...close, quantity: "25,0" });
    expect(p.consumed_inputs[0].quantity).toBe("25.0");
    expect(p.outputs[0]).not.toHaveProperty("byproduct");
    expect(p.outputs[0].unit).toBe("kg");
    expect(p.differences?.[0].quantity).toBe("3");
  });
  it("lotlu satışta fiyat/miktarı string gönderir ve duplicate kaynakları reddeder", () => {
    const v = {
      customer_id: ids[4],
      lines: [
        { source: ids[0] + "|" + ids[1], quantity: "1,5", unit_price: "25,00" },
      ],
    };
    expect(salePayload(v).lines[0]).toMatchObject({
      lot_id: ids[0],
      location_id: ids[1],
      quantity: "1.5",
      unit_price: "25.00",
    });
    expect(
      saleSchema.safeParse({ ...v, lines: [v.lines[0], v.lines[0]] }).success,
    ).toBe(false);
  });
  it("bağlı sevkiyat satışın tam satır UUID, konum ve miktarını kullanır; ikinci stok hesabı yapmaz", () => {
    const sale = {
      id: ids[4],
      customer_id: ids[5],
      lines: [
        {
          id: ids[6],
          lot_id: ids[0],
          location_id: ids[1],
          quantity: "1.000000",
          unit: "kg",
        },
      ],
    } as SaleDetail;
    expect(linkedShipmentPayload(sale, [ids[6]])).toEqual({
      sale_id: ids[4],
      customer_id: ids[5],
      lines: [
        {
          sale_line_id: ids[6],
          lot_id: ids[0],
          location_id: ids[1],
          quantity: "1.000000",
          unit: "kg",
        },
      ],
    });
  });
  it("ML kesim eşlemesinde beş farklı gerçek ürün UUID ister", () => {
    const v = {
      operation_id: "",
      recipe_version_id: ids[0],
      species: "Kuzu",
      input_weight_kg: "25",
      part_products: {
        leg: ids[2],
        shoulder: ids[3],
        back: ids[4],
        rib: ids[5],
        mince: ids[6],
      },
    };
    expect(cuttingPredictionSchema.safeParse(v).success).toBe(true);
    expect(
      cuttingPredictionSchema.safeParse({
        ...v,
        part_products: { ...v.part_products, leg: ids[3] },
      }).success,
    ).toBe(false);
  });
  it("üretim tahmini girdi allowlistinden gerçekleşme hedefleri payloadına sızmaz", () => {
    const v = productionPredictionSchema.parse({
      operation_id: "",
      output_product_id: "",
      meat_type: "beef",
      meat_kg: "100",
      spice_kg: "2",
      casing_kg: "5",
      meat_cost_eur: "970",
      spice_cost_eur: "48",
      casing_cost_eur: "58",
      planned_producer_profile: "producer_a",
      package_weight_kg: "1",
      estimated_service_eur: "450",
      actual_finished_quantity: "85",
      actual_ekp: "18.16",
    });
    const p = productionPredictionPayload(v);
    expect(p).not.toHaveProperty("actual_finished_quantity");
    expect(p).not.toHaveProperty("actual_ekp");
    expect(p.estimated_service_eur).toBe("450");
    expect(p.operation_id).toBeNull();
  });
});
