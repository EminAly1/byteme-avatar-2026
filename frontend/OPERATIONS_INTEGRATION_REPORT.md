# Görev 16 — Operasyon ekranları entegrasyonu

27 Ekim 2026 (Europe/Istanbul). Main tabanı `3dd4316e102a0d1e89461f362ff99351613aea96`; PR #1–#28 atalıkları doğrulandı. Branch `feature/frontend-operational-flows`. Yalnız frontend değiştirildi; backend/migration/Android/ML/Compose ve ortak checklist korunur. Yeniden markalama yapılmadı.

## Ekranlar ve gerçek API bağlantıları

| Ekran | Gerçek bağlantı ve davranış |
| --- | --- |
| `/dagitimlar`, `/dagitimlar/:id` | GET/POST `/distributions/second-tier`, GET detay; sevkiyat satırı, kayıtlı alıcı, miktar, Türkiye tarihi/saati, referans, açıklama, onay, liste ve gerçek kayıt ayrıntısı |
| `/sevkiyatlar?shipment=…` | Kaynak ShipmentLine'dan ikinci kademe formuna doğrudan bağlantı |
| `/izlenebilirlik?lot=…`, `/geri-cagirma/:id` | Mevcut trace/recall GET'lerinden kayıtlı ikinci kademe alıcı ve snapshot; B/C için kayıt yoksa Bilinmiyor |
| `/satislar/:id` | GET `/sales/{id}/profitability`: orijinal gelir/maliyet/VKP/brüt kâr/marj, iade/iptal sonrası net sonuç ve hesap sınırları |
| `/hareketler?islem=transfer` | POST/GET `/transfers`; kaynak lot/depo, farklı hedef, miktar/referans/neden, ön bakiye, onay, backend'den yenilenen iki depo bakiyesi |
| `/hareketler?islem=iade` | Kayıtlı satış ve bağlı sevkiyat satırından tek satırlı POST `/returns`; GET liste/detay, karantina kabulü ve gelir/tarihsel maliyet düzeltmesi |
| `/hareketler?islem=iptal&sale=…` | POST `/sales/{id}/cancel`, GET cancellation; sevk bilgisi ve backend uygunluk kontrolü, uyarı kutusu + ikinci modal onay; orijinal satış korunur |
| `/hareketler?islem=rework`, `/hareketler/rework/:id` | POST/GET `/reworks`, GET detay, POST kesin kapanış; taslak stok tüketmez, kg girdi/çoklu çıktı/tek açıklanmış kayıp/tek fiilî hizmet kalemi ve yeni lot bağlantıları |

Tüm yollar mevcut `/api/v1` yerel proxy üzerinden kullanılır. API anahtarı browser'a/VITE değişkenlerine taşınmaz. CommandForm/newCommand/send/pending altyapısı korunur: UUID idempotency, onayda donmuş gövde, timeout sonrası aynı istek, sekme yenilenince güvenli tekrar ve başarılı POST sonrası Query invalidation. Kapanmış rework veya iptal edilmiş satış, bekleyen kayıp cevap tekrarını gizlemez.

## Doğrulanan kabul

- A/B/C şirket sevkiyatı **30/25/30 = 85 paket**; A→X bildirimi **12 paket**; recall'da X gerçek kayıtla görünür. **18 paket**, “Belgelenmiş tahsis edilmemiş miktar — fiziksel stok doğrulanmadı” olarak sunulur. Market/tüketici satışları uydurulmaz; üst alıcı sayacı birinci kademe diye etiketlenir.
- Gerçek transfer **20→13/7 kg**; fazla miktar gerçek 409 ile reddedilir.
- Sevke bağlı 2 kg iade karantinada; kullanılabilir miktar **0**. Örnek gelir düzeltmesi 40 EUR, tarihsel maliyet düzeltmesi 20 EUR; kaynak satış net geliri 60 EUR/net maliyeti 30 EUR backend'den gösterilir.
- Stale ekranda sonradan sevk edilen satışın iptali backend 409 ile reddedilir; uygun satış iki onayla iptal edilir, kaynak satırlar değişmez.
- Rework taslağında 10 kg stok korunur; kesin kapanış **10 = 9,5 + 0,5 kg**, kayıtlı maliyet **100 + 15 = 115 EUR**. Sonradan recall edilen kaynak LOT_BLOCKED üretir; yeni çıktı oluşmaz.
- Dağıtım, rework kapanışı ve iptal POST'larının cevabı **gerçek sunucu commit'inden sonra** düşürüldü. Reload/retry aynı key/body ve aynı kesin UUID'yi kullandı; mükerrer stok/audit kaydı oluşmadı.

## Gerçek test sonuçları

| Kontrol | Sonuç |
| --- | --- |
| `npm ci --cache /tmp/avatar-task16-npm-cache` | Başarılı; 140 paket. İlk varsayılan cache denemesi salt okunur/oluşturulamayan kullanıcı dizini nedeniyle başarısızdı; lock/dependency değiştirilmedi |
| `npm run typecheck`, `npm run build` | Başarılı; route lazy loading korunur |
| `npm test` | **65 geçti**: önceki 45 + yeni 20; başarısız/atlanmış yok |
| Gerçek Chromium/FastAPI/MySQL | **14 geçti**: 11 yeni + 3 mevcut hedefli regresyon; başarısız/atlanmış yok |
| Responsive / erişilebilirlik | 390/768/1440 px: sayfa taşması yok; mobil/masaüstü beş yeni akışta otomatik WCAG etiket/kontrast kontrolleri bulgusuz; mevcut drawer klavye döngüsü korundu |

Tarayıcı koşusu yeni `avatar_task16_browser_test` MySQL 8.0.46 şemasında; mevcut Task15 instance'ı 127.0.0.1:33329, ayrı API 8007, Vite 5173 kullanıldı. Eski core/demo şemaları sıfırlanmadı. Test verileri KURGUSAL olarak ayrıdır. İlk genişletilmiş koşuda yeni dağıtım bağlantısının eski drawer son odağını değiştirmesi yakalandı; bağlantı audit referansından önceye taşındı. Mevcut test değiştirilmeden son 14/14 geçti.

Tekrar: aynı izole API/env ile `AVATAR_E2E_API_URL=http://127.0.0.1:8007` kullanın. Yeni dosya `tests/browser/operational-flows.spec.ts`; eski üç hedef: integration-v2 içindeki satış/sevkiyat ve trace/recall, release-hardening içindeki SKT. `AVATAR_E2E_ARTIFACT_DIR` ve Playwright `--output` için /tmp seçin. Ham loglar ve incelenen ekran görüntüleri yalnız `/tmp/avatar-task16-*` altında; Git'e eklenmedi.

## Sınırlar ve durum önerisi

Backend 360 testi bu görevde yeniden koşturulmadı; Android/ML eğitimi, bütün eski Chromium senaryoları, fiziksel cihaz ve production dağıtımı test edilmedi. Tam birleşik regresyon 30–31 Ekim final görevi kapsamındadır. Otomatik erişilebilirlik kontrolü tam manuel WCAG kabulü değildir.

İlk web sürümünde iade tek satır, rework tek kayıp ve tek hizmet kalemiyle girilir; çoklu çıktı lotu desteklenir. Karantina kalite serbest bırakma/değerleme, üçüncü kademe, dış fiziksel envanter, dağıtım düzeltme/iptali ve kullanıcı/rol sistemi eklenmedi. Anomali ve fatura/proforma geliştirmelerine başlanmadı. Finansal/stok iş kuralları backend'de; frontend yalnız giriş kontrolü ve gösterim yapar.

- **LOT-05:** Transfer/iade/iptal/rework web akışları için kabul kanıtı hazır. Karantina sınırlamaları açık; birleşik main kabulünü entegrasyon sorumlusu tamamlamalı.
- **LOT-10:** Kayıtlı ikinci kademe web/recall kabulü karşılandı; bilinmeyen dış stok ayrımı korunur. Main'e birleştirme ve son kabul beklenir.
- **URT-07:** Gerçek VKP/maliyet/brüt kâr/marj ve net düzeltme görünümü için Tamamlandı önerilir; vergi/genel gider veya nakit muhasebesi iddiası yoktur.

Değişen dosyalar: App/style; Sales/Trace/Dashboard/Operations ve yeni Distributions/Movements/Reworks sayfaları; forms ve yeni DistributionEvidence/Profitability bileşenleri; api/format/modules ve yeni operational-types/operational-validation; iki yeni test dosyası ve bu kısa rapor. Ortak PROJECT_CHECKLIST değiştirilmedi.

Güvenlik/koruma: Gitleaks 8.24.3 kaynak (485 dosya) ve tüm yerel Git geçmişinde sıfır bulgu verdi; dokuz gerçek gizli değer kaynakta ve 28 build dosyasında bulunmadı. Package/lock, pending ve proxy dosyaları değişmedi. Başlangıçtaki 15 Docker volume'u korundu. Git diff --check temiz; yalnız frontend altında 20 dosya değişti.
