import type { Entity, OperationDetail, Output, Unit } from './types';

export interface SecondTier extends Entity {
  source_shipment_line_id: string;
  source_shipment_id: string;
  source_customer_id: string;
  source_lot_id: string;
  product_id: string;
  recipient_party_id: string;
  recipient_name: string;
  recipient_contact: string | null;
  quantity: string;
  unit: Unit;
  distributed_at: string;
  reference: string;
  evidence_note: string;
  source_recipient_snapshot: { name: string; contact: string | null };
  recording_basis: string;
}
export interface Transfer extends Entity {
  lot_id: string;
  product_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: string;
  unit: Unit;
  transferred_at: string;
  reason: string;
  reference: string | null;
}
export interface Correction extends Entity {
  sale_id: string;
  customer_id: string;
  acceptance_location_id: string;
  reason: string;
  credit_amount: string;
  restored_cost: string;
  inventory_status: 'quarantine_only';
  cash_refund_status: 'not_recorded';
  lines?: Array<Entity & { lot_id: string; quantity: string; unit: Unit; credit_amount: string; restored_cost: string }>;
}
export interface ProfitMetrics {
  net_revenue_eur: string;
  recognized_cost_eur: string;
  gross_profit_eur: string;
  gross_profit_display_eur: string;
  margin_percent: string | null;
}
export interface Profitability extends ProfitMetrics {
  sale_id: string;
  currency: 'EUR';
  basis: string;
  limitations: string[];
  adjustments: {
    state: 'active' | 'cancelled' | 'returned' | 'partially_returned';
    return_ids: string[];
    cancellation_id: string | null;
    return_credit_eur: string;
    cancellation_credit_eur: string;
    cost_reversal_eur: string;
    cash_refund_status: string;
  };
  net_after_adjustments: ProfitMetrics;
  lines: Array<ProfitMetrics & {
    sale_line_id: string;
    lot_id: string;
    quantity: string;
    unit: Unit;
    vkp_eur_per_unit: string;
    recognized_unit_cost_eur: string;
  }>;
}
export interface ReworkPlan {
  code: string;
  source_lot_id: string;
  source_location_id: string;
  input_quantity: string;
  reason: string;
  output_product_ids: string[];
}
export interface Rework extends Omit<OperationDetail, 'outputs'> {
  allocation_snapshot: { plan: ReworkPlan };
  outputs: Array<Output & { product_id: string; lot_code: string; expires_at: string | null }>;
  differences: Array<{ kind: string; quantity: string; reason: string }>;
}
