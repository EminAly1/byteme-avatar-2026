import type { Page } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public uncertain = false,
  ) {
    super(message);
  }
}
const fieldNames: Record<string, string> = {
  product_id: "Ürün",
  supplier_id: "Tedarikçi",
  producer_id: "Dış üretici",
  location_id: "Konum",
  lot_id: "Lot",
  quantity: "Miktar",
  total_cost: "Toplam maliyet",
  amount: "Tutar",
  expires_at: "Son tüketim tarihi",
  lines: "Satırlar",
  consumed_inputs: "Tüketim",
  returned_inputs: "İade",
  outputs: "Mamul",
  service_costs: "Hizmet",
  output_location_id: "Mamul deposu",
  loss_quantity: "Miktar farkı",
  loss_reason: "Fark açıklaması",
  code: "Emir numarası",
  from_location_id: "Çıkış konumu",
  to_location_id: "Kabul konumu",
  currency: "Para birimi",
  external_lot_code: "Lot numarası",
  lot_code: "Lot numarası",
  sku: "SKU",
  name: "Ad",
  package_weight_kg: "Paket kg dönüşümü",
  base_unit: "Birim",
  kind: "Tür",
  type: "Tür",
  roles: "Roller",
};
const messages: Record<number, string> = {
  401: "Bağlantı yetkilendirilemedi. Yerel sunucunun API anahtarı ayarını kontrol edin.",
  403: "Bu yerel bağlantıya erişim reddedildi.",
  409: "İşlem mevcut kayıtlarla çakışıyor. Stok, lot ve emir durumunu kontrol edin.",
  422: "Bazı alanlar geçersiz. Birim, miktar, tarih ve gerekli alanları kontrol edin.",
  503: "API veya veritabanı hazır değil. Bağlantıyı kontrol edip tekrar deneyin.",
};

const domainMessages: Record<string, string> = {
  LOT_BLOCKED:
    "Bu lot geri çağırma kapsamında bloke. Satış, sevk veya tüketim yapılamaz; lot kaydını inceleyin.",
  LOT_EXPIRED:
    "Lotun son tüketim tarihi geçmiş. Kullanılabilir başka lot seçin.",
  INSUFFICIENT_STOCK:
    "Seçili konumda yeterli stok yok. Bakiyeyi yenileyip miktarı kontrol edin.",
  MASS_BALANCE:
    "Giriş ağırlığı, ürün/yan ürün ve açıklanmış farklarla dengelenmiyor. Tartımları kontrol edin.",
  RECIPE_UNAVAILABLE: "Reçete sürümü kullanıma kapalı. Açık bir sürüm seçin.",
  FORECAST_TOO_LATE:
    "İşlem başlamış veya kapanmış. Yeni işlem öncesi tahmin kaydedilemez; önceki tahmin kaydını açın.",
  MODEL_UNAVAILABLE:
    "Tahmin modeli hazır değil veya geçersiz. Tahmin üretilmedi; model kurulumunu kontrol edin.",
  PREDICTION_OUT_OF_DOMAIN:
    "Girdiler modelin desteklediği sentetik aralık dışında. Formdaki sınırları kontrol edin.",
  IDEMPOTENCY_CONFLICT:
    "Bu işlem anahtarı başka bir içerikle kullanılmış. Mevcut işlemin sonucunu inceleyin.",
  SALE_LINE_ALREADY_SHIPPED:
    "Bu satış satırı daha önce sevk edilmiş. Sevkiyat kayıtlarını yenileyin.",
};
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api/v1" + path, {
      ...options,
      signal: options.signal || AbortSignal.timeout(15000),
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Sunucudan yanıt alınamadı. İşlemin kaydedilmiş olabileceğini unutmayın; aynı isteği tekrar deneyin.",
      true,
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const details = Array.isArray(body?.detail)
      ? body.detail
          .map((x: { loc?: Array<string | number> }) =>
            x.loc
              ?.slice(1)
              .map((k) =>
                typeof k === "number" ? `${k + 1}. satır` : fieldNames[k],
              )
              .filter(Boolean)
              .join(" / "),
          )
          .filter(Boolean)
          .join(", ")
      : "";
    throw new ApiError(
      response.status,
      body?.error?.code || "HTTP_ERROR",
      `${domainMessages[body?.error?.code] || (messages[response.status] || "İstek tamamlanamadı.") + (body?.error?.message ? " " + body.error.message : "")}${details ? " Alanlar: " + details : ""}`,
      response.status >= 500,
    );
  }
  if (body === null)
    throw new ApiError(
      0,
      "INVALID_RESPONSE",
      "Sunucunun yanıtı okunamadı. Aynı işlemi tekrar deneyin.",
      true,
    );
  return body as T;
}

export async function all<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  let cursor: string | null = null;
  const result: T[] = [],
    seen = new Set<string>();
  do {
    const search = new URLSearchParams(
      path.includes("?") ? path.split("?")[1] : "",
    );
    search.set("limit", "100");
    if (cursor) search.set("cursor", cursor);
    const page = await request<Page<T>>(path.split("?")[0] + "?" + search, {
      signal,
    });
    result.push(...page.items);
    cursor = page.next_cursor;
    if (cursor && seen.has(cursor))
      throw new ApiError(
        0,
        "PAGINATION",
        "Kayıt sayfaları tamamlanamadı. Listeyi yenileyin.",
      );
    if (cursor) seen.add(cursor);
  } while (cursor);
  return result;
}

export interface Command {
  path: string;
  key: string;
  body: unknown;
}
export const newCommand = (path: string, body: unknown): Command => ({
  path,
  body,
  key: crypto.randomUUID(),
});
export function send<T>(command: Command) {
  return request<T>(command.path, {
    method: "POST",
    headers: { "Idempotency-Key": command.key },
    body: JSON.stringify(command.body),
  });
}
