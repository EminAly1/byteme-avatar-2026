export type Unit = "kg" | "package" | "unit";
export type ProductType = "raw" | "finished" | "byproduct";
export type Role = "supplier" | "producer" | "customer";
export type LocationKind = "warehouse" | "external_producer" | "quarantine";
export interface Entity {
  id: string;
  created_at: string;
}
export interface Product extends Entity {
  species?: string | null;
  sku: string;
  name: string;
  type: ProductType;
  base_unit: Unit;
  package_weight_kg: string | null;
}
export interface Party extends Entity {
  name: string;
  roles: Role[];
  contact: string | null;
}
export interface Location extends Entity {
  name: string;
  kind: LocationKind;
  party_id: string | null;
}
export interface Lot extends Entity {
  product_id: string;
  supplier_id: string | null;
  external_code: string;
  received_at: string;
  expires_at: string | null;
  blocked: boolean;
  original_quantity: string;
  total_cost: string;
  consumed_quantity: string;
  consumed_cost: string;
}
export interface Stock {
  lot_id: string;
  location_id: string;
  product_id: string;
  quantity: string;
  available_quantity: string;
  blocked: boolean;
}
export interface Movement extends Entity {
  lot_id: string;
  location_id: string;
  quantity: string;
  type: string;
  operation_id: string | null;
  receipt_line_id: string | null;
  transfer_group_id: string | null;
  reversal_of: string | null;
}
export interface Receipt extends Entity {
  supplier_id: string;
  location_id: string;
  received_at: string;
  reference: string | null;
}
export interface ReceiptLine extends Entity {
  product_name?: string;
  sku?: string;
  lot_code?: string;
  unit?: Unit;
  receipt_id: string;
  product_id: string;
  lot_id: string;
  quantity: string;
  total_cost: string;
}
export interface ReceiptDetail extends Receipt {
  supplier_name?: string;
  location_name?: string;
  total_cost?: string;
  lines: ReceiptLine[];
}
export interface Operation extends Entity {
  code: string;
  producer_id: string | null;
  kind: "external_production" | "cutting" | "rework";
  recipe_version_id: string | null;
  allocation_method: "quantity" | "value";
  status: "draft" | "posted";
  total_material_cost: string;
  total_service_cost: string;
  total_cost: string;
  loss_quantity: string;
  loss_reason: string | null;
  posted_at: string | null;
}
export interface Input extends Entity {
  lot_id: string;
  location_id: string;
  quantity: string;
  consumed_cost: string;
}
export interface Output extends Entity {
  lot_id: string;
  quantity: string;
  allocated_cost: string;
  allocation_weight: string;
  unit_cost: string;
  unit_cost_display: string;
  reference_eur_per_kg: string | null;
  explanation: string | null;
}
export interface LotLink extends Entity {
  input_lot_id: string;
  output_lot_id: string;
  attributed_input_quantity: string;
}
export interface OperationDetail extends Operation {
  currency: "EUR";
  total_cost_display: string;
  inputs: Input[];
  outputs: Output[];
  lot_links: LotLink[];
  service_costs: Array<
    Entity & {
      amount: string;
      currency: "EUR";
      invoice_reference: string | null;
    }
  >;
}
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}
