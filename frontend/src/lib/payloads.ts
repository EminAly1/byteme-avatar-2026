import type { components } from "./openapi";
import type { z } from "zod";
import {
  productSchema,
  partySchema,
  locationSchema,
  receiptSchema,
  operationSchema,
  dispatchSchema,
  closeSchema,
  cleanDecimal,
} from "./validation";
type Backend = components["schemas"];
export const productPayload = (
  v: z.infer<typeof productSchema>,
): Backend["ProductCreate"] => ({
  ...v,
  package_weight_kg:
    v.base_unit === "package" ? cleanDecimal(v.package_weight_kg) : null,
});
export const partyPayload = (
  v: z.infer<typeof partySchema>,
): Backend["PartyCreate"] => ({ ...v, contact: v.contact || null });
export const locationPayload = (
  v: z.infer<typeof locationSchema>,
): Backend["LocationCreate"] => ({
  ...v,
  party_id: v.kind === "external_producer" ? v.party_id : null,
});
export const receiptPayload = (
  v: z.infer<typeof receiptSchema>,
): Backend["ReceiptCreate"] => ({
  ...v,
  reference: v.reference || null,
  lines: v.lines.map((x) => ({
    ...x,
    quantity: cleanDecimal(x.quantity),
    total_cost: cleanDecimal(x.total_cost),
    expires_at: x.expires_at || null,
  })),
});
export const operationPayload = (
  v: z.infer<typeof operationSchema>,
): Backend["OperationCreate"] => ({ ...v, kind: "external_production" });
export const dispatchPayload = (
  v: z.infer<typeof dispatchSchema>,
): Backend["DispatchCreate"] => ({
  ...v,
  lines: v.lines.map((x) => ({ ...x, quantity: cleanDecimal(x.quantity) })),
});
export const closePayload = (
  v: z.infer<typeof closeSchema>,
): Backend["OperationPost"] => ({
  consumed_inputs: v.consumed_inputs.map((x) => ({
    lot_id: x.source.split("|")[0],
    location_id: x.source.split("|")[1],
    quantity: cleanDecimal(x.quantity),
  })),
  returned_inputs: v.returned_inputs.map((x) => ({
    lot_id: x.source.split("|")[0],
    from_location_id: x.source.split("|")[1],
    to_location_id: x.to_location_id,
    quantity: cleanDecimal(x.quantity),
  })),
  output_location_id: v.output_location_id,
  outputs: v.outputs.map((x) => ({
    ...x,
    quantity: cleanDecimal(x.quantity),
    expires_at: x.expires_at || null,
  })),
  service_costs: [
    {
      amount: cleanDecimal(v.service_amount),
      currency: "EUR",
      invoice_reference: v.invoice_reference || null,
    },
  ],
  allocation_method: "quantity",
  loss_quantity: cleanDecimal(v.loss_quantity),
  loss_reason: v.loss_reason || null,
});
