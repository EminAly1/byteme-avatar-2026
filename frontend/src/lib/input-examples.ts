// Display hints only: never use an example as form state or a command value.
export function inputPlaceholder(
  name: string,
  label: string,
  type = "text",
  example?: string,
): string | undefined {
  if (!["text", "search", "number", "decimal"].includes(type)) return;
  const field = name.split(".").at(-1)!;
  let value = example;
  if (!value) {
    if (type === "decimal") {
      value = /EUR|fiyat|bedel|maliyet/i.test(label)
        ? "18,16"
        : /kg/i.test(label) ? "2,5" : "2";
    } else {
      const examples: Record<string, string> = {
        sku: "ET-001",
        name: /[Ff]irma/.test(label) ? "Örnek Gıda" : /[Dd]epo/.test(label) ? "Soğuk depo" : "Dana eti",
        contact: "operasyon@example.invalid",
        code: /[Rr]eçete/.test(label) ? "REC-KUZU-01" : /[Kk]esim/.test(label) ? "KES-2026-046" : /[Rr]ework/.test(label) ? "RW-2026-046" : "URT-2026-046",
        version: "1",
        species: "Kuzu",
        external_lot_code: "ET-2026-001",
        lot_code: "LOT-2026-046",
        reference: "BELGE-2026-001",
        invoice_reference: "HIZMET-2026-001",
        reason: /[İi]ade/.test(label) ? "Ambalaj hasarı bildirimi" : /[İi]ptal/.test(label) ? "Sevk öncesi müşteri talebi" : /[Tt]ransfer/.test(label) ? "Depolar arası sevk" : "İşlem için ayrılan parti",
        loss_reason: "Tartım sonrası açıklanan miktar farkı",
        explanation: "İlk partinin kabulü",
        evidence_note: "Alıcının tarihli teslim bildirimi",
        title: "Proforma taslağı",
        description: "Seçilen satışın ürün özeti",
        seller_name: "Örnek Gıda",
        seller_contact: "belge@example.invalid",
        payment_note: "Vade için müşteriyle görüşülecek",
        delivery_note: "Soğuk zincirle teslim",
        note: "Teslimattan önce alıcıyı arayın",
      };
      value = examples[field] || "İşleme ilişkin açıklama";
    }
  }
  if (type === "decimal") value = value.replace(".", ",");
  return value.startsWith("Örn:") ? value : "Örn: " + value;
}
