import type { z } from "zod";
import type { components } from "./openapi";
import { decimal } from "./format";
import {
  recipeSchema,
  cuttingDraftSchema,
  cuttingCloseSchema,
  saleSchema,
  independentShipmentSchema,
  productionPredictionSchema,
  cuttingPredictionSchema,
} from "./module-validation";
import type { SaleDetail } from "./modules";
type Backend = components["schemas"];
export const recipePayload = (
  v: z.infer<typeof recipeSchema>,
): Backend["RecipeCreate"] => ({
  ...v,
  version: Number(v.version),
  available: true,
  lines: v.lines.map((l) => ({
    product_id: l.product_id,
    reference_eur_per_kg: l.reference_eur_per_kg
      ? decimal(l.reference_eur_per_kg)
      : null,
  })),
});
export const cuttingDraftPayload = (
  v: z.infer<typeof cuttingDraftSchema>,
): Backend["CuttingCreate"] => v;
export const cuttingPostPayload = (
  v: z.infer<typeof cuttingCloseSchema>,
): Backend["CuttingPost"] => ({
  consumed_inputs: [
    {
      lot_id: v.source.split("|")[0],
      location_id: v.source.split("|")[1],
      quantity: decimal(v.quantity),
    },
  ],
  output_location_id: v.output_location_id,
  outputs: v.outputs.map((o) => ({
    product_id: o.product_id,
    lot_code: o.lot_code,
    quantity: decimal(o.quantity),
    unit: "kg",
    expires_at: o.expires_at || null,
    explanation: o.explanation || null,
  })),
  differences: v.differences.map((d) => ({
    ...d,
    quantity: decimal(d.quantity),
  })),
});
export const salePayload = (
  v: z.infer<typeof saleSchema>,
): Backend["SaleCreate"] => ({
  customer_id: v.customer_id,
  currency: "EUR",
  lines: v.lines.map((l) => ({
    lot_id: l.source.split("|")[0],
    location_id: l.source.split("|")[1],
    quantity: decimal(l.quantity),
    unit_price: decimal(l.unit_price),
  })),
});
export const shipmentPayload = (
  v: z.infer<typeof independentShipmentSchema>,
): Backend["ShipmentCreate"] => ({
  customer_id: v.customer_id,
  lines: v.lines.map((l) => ({
    lot_id: l.source.split("|")[0],
    location_id: l.source.split("|")[1],
    quantity: decimal(l.quantity),
  })),
});
export const linkedShipmentPayload = (
  sale: SaleDetail,
  lineIds: string[],
): Backend["ShipmentCreate"] => ({
  sale_id: sale.id,
  customer_id: sale.customer_id,
  lines: sale.lines
    .filter((l) => lineIds.includes(l.id))
    .map((l) => ({
      sale_line_id: l.id,
      lot_id: l.lot_id,
      location_id: l.location_id,
      quantity: l.quantity,
      unit: l.unit,
    })),
});
export const productionPredictionPayload = (
  v: z.infer<typeof productionPredictionSchema>,
): Backend["ProductionPrediction"] => ({
  ...v,
  operation_id: v.operation_id || null,
  output_product_id: v.output_product_id || null,
  meat_kg: decimal(v.meat_kg),
  spice_kg: decimal(v.spice_kg),
  casing_kg: decimal(v.casing_kg),
  meat_cost_eur: decimal(v.meat_cost_eur),
  spice_cost_eur: decimal(v.spice_cost_eur),
  casing_cost_eur: decimal(v.casing_cost_eur),
  package_weight_kg: decimal(v.package_weight_kg),
  estimated_service_eur: decimal(v.estimated_service_eur),
  currency: "EUR",
  quantity_unit: "package",
  material_unit: "kg",
});
export const cuttingPredictionPayload = (
  v: z.infer<typeof cuttingPredictionSchema>,
): Backend["CuttingPrediction"] => ({
  ...v,
  operation_id: v.operation_id || null,
  input_weight_kg: decimal(v.input_weight_kg),
  unit: "kg",
});
