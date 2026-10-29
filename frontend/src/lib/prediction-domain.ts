import type { z } from "zod";
import type { ModelInfo } from "./modules";

export const modelFieldNames: Record<string, string> = {
  meat_kg: "Planlanan et", spice_kg: "Planlanan baharat", casing_kg: "Planlanan kılıf",
  meat_cost_eur: "Et maliyeti", spice_cost_eur: "Baharat maliyeti", casing_cost_eur: "Kılıf maliyeti",
  package_weight_kg: "Paket ağırlığı", estimated_service_eur: "Hizmet ön teklifi",
  input_weight_kg: "Kesim giriş ağırlığı",
};
export const domainNumber = (n: number) => n.toLocaleString("tr-TR", { maximumFractionDigits: 6 });
export function modelHint(model: ModelInfo, field: string) {
  const spec = model.feature_schema[field];
  if (spec?.minimum === undefined || spec.maximum === undefined) return "";
  const c = model.input_constraints?.find(c => c.field === field);
  return `Desteklenen aralık ${domainNumber(spec.minimum)}–${domainNumber(spec.maximum)} ${spec.unit || ""}.` +
    (c ? ` Et miktarının %${domainNumber(c.minimum * 100)}–%${domainNumber(c.maximum * 100)}’ü.` : "");
}
export function predictionDomainIssues(values: Record<string, unknown>, model: ModelInfo) {
  const errors: Array<{ field: string; message: string }> = [];
  const numeric = (k: string) => Number(String(values[k]).replace(",", "."));
  for (const [field, spec] of Object.entries(model.feature_schema)) {
    if (!(field in values) || spec.minimum === undefined || spec.maximum === undefined) continue;
    const value = numeric(field);
    if (!Number.isFinite(value) || value < spec.minimum || value > spec.maximum) {
      errors.push({ field, message: `${modelFieldNames[field] || field}: ${modelHint(model, field)}` });
    }
  }
  for (const c of model.input_constraints || []) {
    if (errors.some(e => e.field === c.field || e.field === c.relative_to)) continue;
    const source = numeric(c.relative_to), value = numeric(c.field);
    if (Number.isFinite(source) && Number.isFinite(value) && !(source*c.minimum-1e-9 <= value && value <= source*c.maximum+1e-9)) {
      errors.push({ field: c.field, message: `Seçili et miktarı için ${domainNumber(source*c.minimum)}–${domainNumber(source*c.maximum)} kg girin.` });
    }
  }
  return errors;
}
export function predictionSchemaForModel<T extends Record<string, unknown>>(base: z.ZodType<T>, model: ModelInfo) {
  return base.superRefine((values, ctx) => {
    for (const error of predictionDomainIssues(values, model)) ctx.addIssue({ code: "custom", path: [error.field], message: error.message });
  });
}
