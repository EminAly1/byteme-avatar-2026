export type AlertSeverity = 'critical' | 'warning' | 'info';
export type AlertRule = 'EXPIRY_PAST' | 'EXPIRY_SOON' | 'LOT_BLOCKED_STOCK' | 'LOW_AVAILABLE_STOCK' | 'PRODUCTION_EKP_DEVIATION' | 'YIELD_DEVIATION';
export const alertRules: Record<AlertRule, string> = {
  EXPIRY_PAST: 'SKT geçmiş', EXPIRY_SOON: 'SKT yaklaşıyor', LOT_BLOCKED_STOCK: 'Bloke stok',
  LOW_AVAILABLE_STOCK: 'Tanımlı düşük stok eşiği', PRODUCTION_EKP_DEVIATION: 'EKP tahmin–gerçekleşme', YIELD_DEVIATION: 'Verim tahmin–gerçekleşme',
};
export const alertSeverities: Record<AlertSeverity, string> = { critical: 'Kritik', warning: 'Uyarı', info: 'Bilgilendirme' };
export interface Alert {
  id: string; rule_code: AlertRule; severity: AlertSeverity;
  source_type: 'lot' | 'product' | 'operation'; source_id: string; source_label: string;
  location_id: string | null; title: string; message: string;
  observed_value: string; threshold_value: string; unit: string; threshold_unit: string;
  threshold_origin: 'demo' | 'operator_configured' | 'configured_review_window';
  evaluated_at: string; policy_version: string; policy_fingerprint: string;
  recommended_action: string; related_links: Array<{ label: string; href: string }>;
  predicted_value?: string; difference_value?: string; deviation_percent?: string;
  evidence: {
    product_name?: string; lot_code?: string; location_name?: string; location_kind?: string;
    physical_quantity?: string; available_quantity?: string; quantity_unit?: string;
    expires_at?: string | null; days_remaining?: number | null;
    related_recalls?: Array<{ recall_id: string; source_lot_id: string }>;
    model_version?: string; data_origin?: string; prediction_id?: string; operation_id?: string;
    prediction_recorded_at?: string; posted_at?: string; prediction_limitations?: string[];
    percentage_denominator?: string; explained_difference_kg?: string;
  };
}
export interface AlertCounts { total: number; critical: number; warning: number; info: number; by_rule: Partial<Record<AlertRule, number>> }
export interface AlertEvaluation {
  summary: AlertCounts; evaluated_at: string; diagnostics: Record<string, number>; history_persisted: false;
  policy: { version: string; fingerprint: string; timezone: 'Europe/Istanbul'; expiry_days: number; deviation_origin: string; cost_percent: string; yield_percent: string };
}
export interface AlertPage extends AlertEvaluation { items: Alert[]; next_cursor: string | null }
export const alertUnit = (unit: string) => ({ day: 'gün', package: 'paket', unit: 'adet', 'EUR/package': 'EUR/paket', 'kg/kg': 'kg çıktı / kg girdi' }[unit] || unit);
