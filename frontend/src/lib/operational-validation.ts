import { z } from 'zod';
import { id, quantity, nonnegative, money, expiry } from './validation';
import { source, text } from './module-validation';
import { decimal } from './format';
import { balance } from './quantity';

export const turkeyDate = z.string().refine(value => {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/.test(value)) return false;
  const date = new Date(value + '+03:00');
  return !Number.isNaN(date.valueOf()) &&
    new Date(date.valueOf() + 3 * 3600000).toISOString().slice(0, value.length) === value;
}, 'Geçerli Türkiye tarihi ve saati girin.');
export function turkeyNow() {
  return new Date(Date.now() + 3 * 3600000).toISOString().slice(0, 23);
}
export const distributionSchema = z.object({
  source_shipment_line_id: id, recipient_party_id: id, quantity,
  distributed_at: turkeyDate, reference: text(), evidence_note: text(500),
});
export const transferSchema = z.object({
  source, to_location_id: id, quantity, reference: z.string().trim().max(100), reason: text(500),
}).superRefine((value, ctx) => {
  if (value.source.split('|')[1] === value.to_location_id)
    ctx.addIssue({ code: 'custom', path: ['to_location_id'], message: 'Kaynak ve hedef depo farklı olmalı.' });
});
export const returnSchema = z.object({
  sale_id: id, shipment_line_id: id, quantity, acceptance_location_id: id, reason: text(500),
});
export const cancelSchema = z.object({
  acceptance_location_id: id, reason: text(500),
  acknowledged: z.boolean().refine(Boolean, 'İptal ve karantina uyarısını onaylayın.'),
});
export const reworkDraftSchema = z.object({
  code: text(), source, input_quantity: quantity, reason: text(500),
  output_product_ids: z.array(id).min(1, 'En az bir çıktı ürünü seçin.').max(100),
});
export const reworkCloseSchema = (input: string) => z.object({
  output_location_id: id,
  outputs: z.array(z.object({ product_id: id, lot_code: text(), quantity, expires_at: expiry,
    explanation: z.string().trim().max(500) })).min(1).max(100),
  loss_quantity: nonnegative, loss_kind: z.enum(['waste', 'other_loss']),
  loss_reason: z.string().trim().max(500), service_amount: money,
  invoice_reference: z.string().trim().max(100),
}).superRefine((value, ctx) => {
  if (/[1-9]/.test(value.loss_quantity) && !value.loss_reason)
    ctx.addIssue({ code: 'custom', path: ['loss_reason'], message: 'Miktar farkının nedeni gerekli.' });
  if (/[1-9]/.test(value.service_amount) && !value.invoice_reference)
    ctx.addIssue({ code: 'custom', path: ['invoice_reference'], message: 'Fiilî hizmet bedelinin belge referansı gerekli.' });
  const b = balance(input, value.outputs.map(row => row.quantity), [value.loss_quantity]);
  if (b && !b.balanced)
    ctx.addIssue({ code: 'custom', path: ['outputs'], message: 'Girdi kg = çıktılar + açıklanmış kayıp olmalı.' });
  if (new Set(value.outputs.map(row => row.product_id + '|' + row.lot_code)).size !== value.outputs.length)
    ctx.addIssue({ code: 'custom', path: ['outputs'], message: 'Aynı ürün ve lot kodu tekrarlanamaz.' });
});
export const reworkClosePayload = (value: z.infer<ReturnType<typeof reworkCloseSchema>>) => ({
  output_location_id: value.output_location_id,
  outputs: value.outputs.map(row => ({ product_id: row.product_id, lot_code: row.lot_code,
    quantity: decimal(row.quantity), unit: 'kg', ...(row.expires_at ? { expires_at: row.expires_at } : {}),
    ...(row.explanation ? { explanation: row.explanation } : {}) })),
  differences: /[1-9]/.test(value.loss_quantity) ? [{ kind: value.loss_kind,
    quantity: decimal(value.loss_quantity), reason: value.loss_reason }] : [],
  service_costs: /[1-9]/.test(value.service_amount) ? [{ amount: decimal(value.service_amount),
    invoice_reference: value.invoice_reference }] : [],
});
