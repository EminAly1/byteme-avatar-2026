import { z } from "zod";
import { decimal } from "./format";

const text = (max = 200) =>
  z
    .string()
    .trim()
    .min(1, "Bu alan gerekli.")
    .max(max, `En fazla ${max} karakter.`);
export const id = z.string().uuid("Bir kayıt seçin.");
export const quantity = z
  .string()
  .refine(
    (s) =>
      /^(0|[1-9]\d{0,11})([.,]\d{1,6})?$/.test(s.trim()) && /[1-9]/.test(s),
    "Pozitif miktar girin; en fazla 6 ondalık hane kullanın.",
  );
export const nonnegative = z
  .string()
  .refine(
    (s) => /^(0|[1-9]\d{0,11})([.,]\d{1,6})?$/.test(s.trim()),
    "Sıfır veya pozitif değer girin; en fazla 6 ondalık hane.",
  );
export const money = z
  .string()
  .refine(
    (s) => /^(0|[1-9]\d{0,11})([.,]\d{1,2})?$/.test(s.trim()),
    "Tutar sıfır veya pozitif olmalı; en fazla 2 ondalık hane.",
  );
export const expiry = z
  .string()
  .refine(
    (s) =>
      !s ||
      (/^\d{4}-\d{2}-\d{2}$/.test(s) &&
        !Number.isNaN(Date.parse(s)) &&
        new Date(s).toISOString().slice(0, 10) === s),
    "Geçerli bir tarih girin.",
  );
const optionalCode = z.string().trim().max(100, "En fazla 100 karakter.");
export const productSchema = z
  .object({
    sku: text(64),
    name: text(),
    type: z.enum(["raw", "finished", "byproduct"]),
    base_unit: z.enum(["kg", "package", "unit"]),
    package_weight_kg: z.string(),
  })
  .superRefine((v, ctx) => {
    if (
      v.base_unit === "package" &&
      !quantity.safeParse(v.package_weight_kg).success
    )
      ctx.addIssue({
        code: "custom",
        path: ["package_weight_kg"],
        message: "Paket için pozitif kg dönüşümü girin.",
      });
  });
export const partySchema = z.object({
  name: text(),
  roles: z
    .array(z.enum(["supplier", "producer", "customer"]))
    .min(1, "En az bir rol seçin."),
  contact: z.string().trim().max(300),
});
export const locationSchema = z
  .object({
    name: text(),
    kind: z.enum(["warehouse", "external_producer", "quarantine"]),
    party_id: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.kind === "external_producer" && !id.safeParse(v.party_id).success)
      ctx.addIssue({
        code: "custom",
        path: ["party_id"],
        message: "Üretici seçin.",
      });
  });
export const receiptSchema = z.object({
  supplier_id: id,
  location_id: id,
  reference: optionalCode,
  lines: z
    .array(
      z.object({
        product_id: id,
        external_lot_code: text(100),
        quantity,
        total_cost: money,
        expires_at: expiry,
      }),
    )
    .min(1)
    .max(100),
});
export const operationSchema = z.object({ code: text(100), producer_id: id });
const dispatchLine = z.object({ lot_id: id, quantity });
export const dispatchSchema = z
  .object({
    from_location_id: id,
    to_location_id: id,
    lines: z.array(dispatchLine).min(1).max(100),
  })
  .superRefine((v, ctx) => {
    if (new Set(v.lines.map((x) => x.lot_id)).size !== v.lines.length)
      ctx.addIssue({
        code: "custom",
        path: ["lines"],
        message: "Her lot yalnızca bir satırda yer alabilir.",
      });
  });
const source = z
  .string()
  .refine(
    (s) =>
      s.split("|").length === 2 &&
      s.split("|").every((x) => id.safeParse(x).success),
    "Sevk edilmiş lot ve konum seçin.",
  );
export const closeSchema = z
  .object({
    consumed_inputs: z.array(z.object({ source, quantity })).min(1).max(100),
    returned_inputs: z
      .array(z.object({ source, to_location_id: id, quantity }))
      .max(100),
    output_location_id: id,
    outputs: z
      .array(
        z.object({
          product_id: id,
          lot_code: text(100),
          quantity,
          expires_at: expiry,
        }),
      )
      .min(1)
      .max(100),
    service_amount: money,
    invoice_reference: optionalCode,
    loss_quantity: nonnegative,
    loss_reason: z.string().trim().max(500),
  })
  .superRefine((v, ctx) => {
    if (/[1-9]/.test(v.loss_quantity) && !v.loss_reason)
      ctx.addIssue({
        code: "custom",
        path: ["loss_reason"],
        message: "Miktar farkının nedenini açıklayın.",
      });
    for (const key of ["consumed_inputs", "returned_inputs"] as const)
      if (new Set(v[key].map((x) => x.source)).size !== v[key].length)
        ctx.addIssue({
          code: "custom",
          path: [key],
          message: "Aynı lot/konum tekrarlanamaz.",
        });
    if (
      new Set(v.outputs.map((x) => x.product_id + "|" + x.lot_code)).size !==
      v.outputs.length
    )
      ctx.addIssue({
        code: "custom",
        path: ["outputs"],
        message: "Aynı ürün ve lot kodu tekrarlanamaz.",
      });
  });
export const cleanDecimal = decimal;
