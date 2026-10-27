import type { SecondTier } from './operational-types';
import type {
  Entity,
  Input,
  Lot,
  Location,
  Operation,
  OperationDetail,
  Output,
  Party,
  Product,
  Unit,
  Stock,
} from "./types";
export interface RecipeLine extends Entity {
  product_id: string;
  reference_eur_per_kg: string | null;
  product?: Product;
}
export interface Recipe extends Entity {
  code: string;
  version: number;
  species: string;
  input_product_id: string;
  allocation_method: "quantity" | "value";
  available: boolean;
  lines: RecipeLine[];
}
export interface RecipeSnapshot {
  schema_version: number;
  recipe_version_id: string;
  code: string;
  version: number;
  species: string;
  input_product_id: string;
  allocation_method: 'quantity' | 'value';
  policies: Record<string, unknown>;
  lines: Array<RecipeLine & {product: Product}>;
}
export interface Cutting extends OperationDetail {
  recipe_version_id: string;
  allocation_method: "quantity" | "value";
  allocation_snapshot: RecipeSnapshot;
  differences: Array<
    Entity & { kind: "waste" | "other_loss"; quantity: string; reason: string }
  >;
}
export interface Sale extends Entity {
  customer_id: string;
  sold_at: string;
  currency: "EUR";
  total_amount: string;
}
export interface SaleLine extends Entity {
  sale_id: string;
  line_no: number;
  product_id: string;
  lot_id: string;
  location_id: string;
  stock_movement_id: string;
  quantity: string;
  unit: Unit;
  unit_price: string;
  total_amount: string;
  consumed_cost: string;
}
export interface SaleDetail extends Sale {
  lines: SaleLine[];
}
export interface Shipment extends Entity {
  customer_id: string;
  sale_id: string | null;
  recipient_name: string;
  recipient_contact: string | null;
  shipped_at: string;
}
export interface ShipmentLine extends Entity {
  shipment_id: string;
  sale_line_id: string | null;
  product_id: string;
  lot_id: string;
  location_id: string;
  stock_movement_id: string;
  quantity: string;
  unit: Unit;
  consumed_cost: string;
}
export interface ShipmentDetail extends Shipment {
  lines: ShipmentLine[];
}
export interface TraceLot extends Lot {
  product: Product;
  supplier: Party | null;
}
export interface TraceEdge {
  operation_id: string;
  input_id: string;
  output_id: string;
  input_lot_id: string;
  output_lot_id: string;
  consumed_input_quantity: string;
  output_quantity: string;
  lot_link_id: string | null;
  attributed_input_quantity: string | null;
  physical_separation_verified: false;
}
export interface Buyer {
  customer_id: string;
  current_customer: Party;
  recipient_snapshots: Array<{
    shipment_id: string;
    shipped_at: string;
    recipient_name: string;
    recipient_contact: string | null;
  }>;
  quantities: Array<{
    lot_id: string;
    product_id: string;
    unit: Unit;
    recorded_sale_quantity: string;
    unshipped_sale_quantity: string;
    shipped_quantity: string;
    sale_line_ids: string[];
    shipment_line_ids: string[];
  }>;
}
export interface TraceReport {
  source_lot: TraceLot;
  direction: "forward" | "backward";
  lots: TraceLot[];
  context_lots: TraceLot[];
  affected_finished_lot_ids: string[];
  operations: Array<Operation & { inputs: Input[]; outputs: Output[] }>;
  edges: TraceEdge[];
  cycle_detected: boolean;
  stocks: Array<Stock & { unit: Unit; location: Location }>;
  blocked_stocks: Stock[];
  sales: SaleDetail[];
  shipments: ShipmentDetail[];
  buyers: Buyer[];
  total_shipped_quantities: Array<{
    product_id: string;
    unit: Unit;
    quantity: string;
  }>;
  second_tier_distributions: SecondTier[];
  unknown_distributions: Array<{
    customer_id: string;
    market_remaining_quantity: null;
    final_consumer_sold_quantity: null;
    second_tier_recipients: Array<{ distribution_id: string; recipient_party_id: string; recipient_name: string; recipient_contact: string | null }> | null;
    external_inventory_verified?: false;
    distribution_completeness?: string;
    unallocated_documented_quantities?: Array<{ source_shipment_line_id: string; lot_id: string; product_id: string; unit: Unit; quantity: string; physical_stock: false }>;
  }>;
}
export interface Recall extends Entity {
  source_lot_id: string;
  reason: string;
  report: TraceReport;
  affected_lot_ids?: string[];
}
export type Part = "leg" | "shoulder" | "back" | "rib" | "mince";
export const partNames: Record<Part, string> = {
  leg: "But",
  shoulder: "Omuz",
  back: "Sırt",
  rib: "Kaburga",
  mince: "Kıyma",
};
export interface Metric {
  mae: number;
  rmse: number;
  unit: string;
  n: number;
}
export interface ModelInfo {
  kind: "production" | "cutting";
  model_version: string;
  trained_at: string;
  data_origin: string;
  dataset_version: string;
  feature_schema_version: string;
  prediction_limitations: string[];
  metrics: {
    baseline_test: Record<string, Metric>;
    ridge_test: Record<string, Metric>;
    splits: Record<string, number>;
  };
}
export interface Comparison {
  predicted: string;
  actual: string | null;
  absolute_deviation: string | null;
  percentage_deviation: string | null;
}
export interface Prediction {
  id: string;
  kind: "production" | "cutting";
  operation_id: string | null;
  predicted_at: string;
  features: Record<string, string>;
  context: Record<string, unknown>;
  model_version: string;
  data_origin: string;
  prediction_limitations: string[];
  predicted_finished_quantity?: string;
  predicted_ekp_eur_per_unit?: string;
  predicted_total_cost_eur?: string;
  predicted_yield_ratio: string;
  predicted_total_weight_kg?: string;
  predicted_difference_kg?: string;
  predicted_leg_kg?: string;
  predicted_shoulder_kg?: string;
  predicted_back_kg?: string;
  predicted_rib_kg?: string;
  predicted_mince_kg?: string;
  comparison?: Record<string, Comparison>;
  actual_unavailable_reason?: string | null;
}
