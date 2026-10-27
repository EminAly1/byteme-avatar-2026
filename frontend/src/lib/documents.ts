import { ApiError } from './api';
import type { Unit } from './types';

export type DocumentKind = 'proforma' | 'sale_summary';
export const documentLabels = {
  proforma: 'PROFORMA TASLAĞI — RESMÎ FATURA DEĞİLDİR',
  sale_summary: 'SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR',
};
export interface DraftFields {
  title: string; description: string; seller_name: string; seller_contact: string;
  document_date: string; payment_note: string; delivery_note: string; note: string;
  reference: string; demo: boolean;
}
export const draftLimits = {title:120,description:600,seller_name:200,seller_contact:300,payment_note:500,delivery_note:500,note:1500,reference:100};
export function initialDraft(): DraftFields {
  return {title:'',description:'',seller_name:'',seller_contact:'',document_date:new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Istanbul'}).format(new Date()),payment_note:'',delivery_note:'',note:'',reference:'',demo:false};
}
export interface DocumentSource {
  sale_id: string; sold_at: string; currency: 'EUR'; source_fingerprint: string;
  customer: {id:string;name:string;contact:string|null}; customer_basis: string;
  original_total_eur: string; state: 'active'|'partially_returned'|'returned'|'cancelled'; state_label: string;
  return_credit_eur:string; cancellation_credit_eur:string; net_after_adjustments_eur:string;
  payment_status:string;cash_refund_status:string;tax_information:string;
  lines: Array<{id:string;line_no:number;product_id:string;product_name:string;sku:string;lot_id:string;lot_code:string;quantity:string;unit:Unit;unit_price_eur:string;total_eur:string}>;
  shipments: Array<{id:string;shipped_at:string;recipient_name:string;recipient_contact:string|null;lines:Array<{sale_line_id:string;lot_id:string;quantity:string;unit:Unit}>}>;
  corrections: Array<{id:string;kind:'return'|'cancellation';recorded_at:string;reason:string;credit_eur:string;lines:Array<{sale_line_id:string;lot_id:string;quantity:string;unit:Unit;credit_eur:string}>}>;
}

export async function fetchDocumentPdf(source: DocumentSource, kind: DocumentKind, draft: DraftFields): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch('/api/v1/document-drafts/proforma/pdf', {method:'POST',signal:AbortSignal.timeout(30000),
      headers:{'Content-Type':'application/json'},body:JSON.stringify({sale_id:source.sale_id,kind,draft,expected_source_fingerprint:source.source_fingerprint})});
  } catch {
    throw new ApiError(0,'DOCUMENT_NETWORK','PDF alınamadı. Bağlantıyı kontrol edip tekrar deneyin. Kesin satış kaydı değiştirilmedi.');
  }
  if (!response.ok) {
    const body = await response.json().catch(()=>null);
    const message=response.status===409?'Kaynak satış veya düzeltmeler değişti. Önizlemeyi yenileyip PDF’yi tekrar oluşturun.':response.status===422?'Taslak alanlarını kontrol edin: uzunluk, tarih ve en fazla 21 satır sınırı.':response.status===401?'Belge bağlantısı yetkilendirilemedi. Yerel sunucunun bağlantı ayarını kontrol edin.':'PDF oluşturulamadı. Kaynak satışı ve bağlantıyı kontrol edip tekrar deneyin.';
    throw new ApiError(response.status,body?.error?.code||'DOCUMENT_PDF_ERROR',message);
  }
  if(response.headers.get('content-type')?.split(';')[0] !== 'application/pdf')
    throw new ApiError(0,'DOCUMENT_PDF_FORMAT','Sunucu geçerli PDF yanıtı vermedi. Dosya indirilmedi.');
  const blob=await response.blob();
  if(await blob.slice(0,5).text()!=='%PDF-') throw new ApiError(0,'DOCUMENT_PDF_FORMAT','PDF içeriği doğrulanamadı. Dosya indirilmedi.');
  return blob;
}

export function saveDocumentPdf(blob:Blob, id:string, kind:DocumentKind) {
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=`${kind}-${id}.pdf`;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
