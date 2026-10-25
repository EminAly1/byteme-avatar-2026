import { z } from "zod";
import { id, quantity, nonnegative, money, expiry } from "./validation";
import { balance } from "./quantity";
export const text = (max = 100) =>
  z.string().trim().min(1, "Bu alan gerekli.").max(max);
export const source = z
  .string()
  .refine(
    (v) =>
      v.split("|").length === 2 &&
      v.split("|").every((x) => id.safeParse(x).success),
    "Lot ve konum seçin.",
  );
export const recipeSchema = z
  .object({
    code: text(),
    version: z
      .string()
      .regex(/^[1-9]\d{0,8}$/, "Pozitif sürüm numarası girin."),
    species: text(200),
    input_product_id: id,
    allocation_method: z.enum(["quantity", "value"]),
    lines: z
      .array(z.object({ product_id: id, reference_eur_per_kg: z.string() }))
      .min(1)
      .max(100),
  })
  .superRefine((v, ctx) => {
    if (new Set(v.lines.map((l) => l.product_id)).size !== v.lines.length)
      ctx.addIssue({
        code: "custom",
        path: ["lines"],
        message: "Her parça ürünü bir kez seçilmelidir.",
      });
    v.lines.forEach((l, i) => {
      if (
        (v.allocation_method === "value" || l.reference_eur_per_kg) &&
        (!money.safeParse(l.reference_eur_per_kg).success ||
          !/[1-9]/.test(l.reference_eur_per_kg))
      )
        ctx.addIssue({
          code: "custom",
          path: ["lines", i, "reference_eur_per_kg"],
          message: "Pozitif referans EUR/kg girin; satış fiyatı değildir.",
        });
    });
  });
export const cuttingDraftSchema = z.object({
  code: text(),
  recipe_version_id: id,
});
export const cuttingCloseSchema = z
  .object({
    source,
    quantity,
    output_location_id: id,
    outputs: z
      .array(
        z.object({
          product_id: id,
          lot_code: text(),
          quantity,
          expires_at: expiry,
          explanation: z.string().trim().max(500),
          byproduct: z.boolean(),
        }),
      )
      .min(1)
      .max(100),
    differences: z
      .array(
        z.object({
          kind: z.enum(["waste", "other_loss"]),
          quantity,
          reason: text(500),
        }),
      )
      .max(100),
  })
  .superRefine((v, ctx) => {
    v.outputs.forEach((o, i) => {
      if (o.byproduct && !o.explanation)
        ctx.addIssue({
          code: "custom",
          path: ["outputs", i, "explanation"],
          message: "Yan ürün için açıklama gerekli.",
        });
    });
    const b = balance(
      v.quantity,
      v.outputs.map((x) => x.quantity),
      v.differences.map((x) => x.quantity),
    );
    if (b && !b.balanced)
      ctx.addIssue({
        code: "custom",
        path: ["outputs"],
        message:
          "Giriş kg, mamul + yan ürün + açıklanmış fark toplamına eşit olmalı.",
      });
    if (
      new Set(v.outputs.map((x) => x.product_id + "|" + x.lot_code)).size !==
      v.outputs.length
    )
      ctx.addIssue({
        code: "custom",
        path: ["outputs"],
        message: "Aynı ürün/lot tekrarlanamaz.",
      });
  });
export const saleSchema = z
  .object({
    customer_id: id,
    lines: z
      .array(z.object({ source, quantity, unit_price: money }))
      .min(1)
      .max(100),
  })
  .superRefine((v, ctx) => {
    if (new Set(v.lines.map((x) => x.source)).size !== v.lines.length)
      ctx.addIssue({
        code: "custom",
        path: ["lines"],
        message: "Aynı lot/konum tekrarlanamaz.",
      });
  });
export const independentShipmentSchema = z
  .object({
    customer_id: id,
    lines: z.array(z.object({ source, quantity })).min(1).max(100),
  })
  .superRefine((v, ctx) => {
    if (new Set(v.lines.map((x) => x.source)).size !== v.lines.length)
      ctx.addIssue({
        code: "custom",
        path: ["lines"],
        message: "Aynı lot/konum tekrarlanamaz.",
      });
  });
export const recallSchema = z.object({ source_lot_id: id, reason: text(500) });
const optionalId = z.union([id, z.literal("")]);
export const productionPredictionSchema = z
  .object({
    operation_id: optionalId,
    output_product_id: optionalId,
    meat_type: z.enum(["beef", "lamb"]),
    meat_kg: quantity,
    spice_kg: quantity,
    casing_kg: quantity,
    meat_cost_eur: nonnegative,
    spice_cost_eur: nonnegative,
    casing_cost_eur: nonnegative,
    planned_producer_profile: z.enum([
      "producer_a",
      "producer_b",
      "producer_c",
    ]),
    package_weight_kg: quantity,
    estimated_service_eur: nonnegative,
  })
  .superRefine((v, ctx) => {
    if (v.operation_id && !v.output_product_id)
      ctx.addIssue({
        code: "custom",
        path: ["output_product_id"],
        message: "İşleme bağlı tahminde paket ürünü seçin.",
      });
  });
export const cuttingPredictionSchema = z
  .object({
    operation_id: optionalId,
    recipe_version_id: id,
    species: z.literal("Kuzu"),
    input_weight_kg: quantity,
    part_products: z.object({
      leg: id,
      shoulder: id,
      back: id,
      rib: id,
      mince: id,
    }),
  })
  .superRefine((v, ctx) => {
    if (new Set(Object.values(v.part_products)).size !== 5)
      ctx.addIssue({
        code: "custom",
        path: ["part_products"],
        message: "Beş farklı reçete ürünü seçin.",
      });
  });
