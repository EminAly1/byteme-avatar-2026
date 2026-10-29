# Görev 21 — Kontrollü geri çağırma kabul raporu

29 Ekim 2026, Europe/Istanbul. Başlangıç `origin/main`: `2918075a43e84a6440364ccdd6bbb5a5e12b8e2b` (PR #35 ve #36 dahil). Geliştirme: `feature/recall-safety-ux-v2`. Bu rapor yerel, izole prototip kabulüdür. Main'e birleştirme veya release etiketi bu görevin kapsamında yapılmaz.

## Yeni kullanıcı akışı

1. **Kaynak ve etki:** Kaynak lot, ürün, blokaj, gerçek türev lotlar ve her kayıtlı konumdaki miktar gösterilir. Birinci kademe alıcılar, kayıtlı ikinci kademe bildirimleri ve sevkiyat sayıları görünürdür. Önizleme kayıt oluşturmaz. Dış market stoğu/tüketici satışları bilinmiyor olarak kalır; belgelenmiş tahsis edilmemiş miktar fiziksel stok diye sunulmaz.
2. **Gerekçe ve risk:** Boş/yalnız boşluk gerekçe ile ilerlenemez. Kaynak tekrar gösterilir; yüksek risk, satışları engelleme, otomatik blok kaldırma ve otomatik bildirim bulunmadığı açıklanır. Kullanıcının ilk incelediği kapsam bu aşamadan itibaren sabit tutulur; genel yenileme veya cache güncellemesi sessizce yeni bir kapsam onaylatamaz.
3. **Kesin onay:** Ayrı native modalda lot/konum/alıcı özeti ve gerekçe tekrar gösterilir. Lot kodu elle, birebir eşleşecek şekilde yazılmadan **“Geri çağırmayı kesinleştir ve lotları bloke et”** düğmesi açılmaz. İlk odak Vazgeç'tedir; Tab modalda kalır, Escape önceki adıma ve onayı açan düğmeye döner. İstek sürerken tekrar gönderme kapalıdır. Belirsiz sonuç/reload özgün key/body ile kurtarılır.

Başarı mevcut gerçek recall ayrıntı sayfasında gösterilir. Zaten bloke lotlar açıkça belirtilir. Yanlış kaynak seçimini düzeltmek için kaynak/etki adımına dönülür; kaynak değiştirilirse gerekçe ve onay temizlenir. Mobilde tek sütun, masaüstünde kartlar ve yatay ilerleme göstergesi kullanılır. Genel tema ve diğer sayfalar yeniden tasarlanmadı.

## Backend ve stok bütünlüğü

[Salt okunur önizleme ve kesinleştirme sözleşmesi](../backend/RECALL_SAFETY.md), [API eki](api-contract.md) ve [makinece okunur kanıt](recall-safety/acceptance.json).

Yeni inceleme izi, kaynak, gerçek graf, stok, satış/sevk ve ikinci kademe raporunun SHA256 değeridir. Kesinleştirme mevcut sıralı lot kilitleri alındıktan ve graf tekrar doğrulandıktan sonra bu izi kontrol eder. Kaynak kodu uyuşmazsa `RECALL_SOURCE_MISMATCH`, kapsam değişmişse `RECALL_PREVIEW_STALE` / 409 döner; kullanıcı ilk adıma yönlendirilir. Kısmi recall/blokaj/idempotency kaydı kalmaz.

Yeni bir alt lotun eşzamanlı üretimle oluşması mevcut bütün-transaction retry protokolünü kullanır; güncel kapsam ilk incelenenden farklıysa yeni inceleme gerekir. Aynı key/body başarıdan sonra eski iz taşısa da saklı ilk cevabı alır; farklı body ile aynı key reddedilir. Eski komutların canonical hash'lerini koruyan geriye uyumluluk testi de geçti. Yeni tablo veya migration yoktur; şema `f1507a26b001`, 30 domain tablosu ve `alembic check` temizdir.

## Gerçek test sonuçları

| Kontrol | Sonuç | Kapsam |
| --- | --- | --- |
| MySQL 8.0.46 pytest | **254 geçti**, 0 başarısız/skip | 14 yeni inceleme testi + 240 mevcut recall, satış/sevk, kesim, rework, transfer/iade ve ikinci kademe regresyonu |
| React/Vitest | **89 geçti**, 0 başarısız/skip | 6 yeni wizard testi + mevcut 83 test; genel dialog varsayılanları dahil |
| TypeScript / Vite build | **Geçti** | Son kaynak üzerinde `npm run build` içindeki typecheck ve üretim build'i |
| Gerçek Chromium | **7 benzersiz senaryo geçti**, 0 son başarısız/skip | 3 yeni recall; mevcut ET→SUC→A/B/C, mobil/tablet, kayıp yanıtlı satış ve alış/SKT regresyonları |
| Erişilebilirlik / responsive | **9 tarama, 0 ihlal** | 3 aşama × 390/768/1440 px; `.recall-wizard` üzerinde WCAG A/AA otomatik kontrolleri; görüntüler ayrıca incelendi |
| Canlılık / hazırlık | **HTTP 200 / 200** | Yeni kodu çalıştıran yerel FastAPI; MySQL bağlantısı |
| Alembic şema karşılaştırması | **Geçti** | `No new upgrade operations detected.` |

Testler yalnız **yeni** `avatar_task21_core_test` ve `avatar_task21_web_test` şemalarında çalıştırıldı. Mevcut MySQL sunucusu/volume ve önceki demo kayıtları korundu; eski şemalarda silme testi yapılmadı. Backend sürümü host loopback `8003`, test Vite sunucusu `5173` üzerinden kullanıldı; tarayıcı API anahtarı taşımaz. Test bitiminde eski Compose uygulama servisleri geri başlatıldı ve HTTP 200/200 ile doğrulandı; yeni şemalar ve kanıtlar korundu.

İlk denemelerdeki başarısızlıklar saklanmıştır: Compose'un 5173 portunu ayırması, gerekçe alanının tam erişilebilir etiketi ve modal ilk odağı; ayrıca bir React testi gereksiz çift önizleme isteğini yakaladı. Sorunlar giderildi; testler silinmedi/skip edilmedi. Son kabul sayıları benzersiz testlerdir; tekrar koşumlar ek başarı olarak toplanmadı. Backend'de mevcut Starlette/AnyIO deprecation uyarısı sürüyor.

Tam backend/ML paketi, Android, model eğitimi ve internet dağıtımı bu görevde tekrar test edilmedi. Ham JUnit/log/9 PNG/erişilebilirlik JSON dosyaları `/tmp/avatar-task21/` içindedir; kaynak testler ve özet/hash'ler Git'te saklanır. İki görselin kullanıcıya indirilebilir kopyası `/workspace/shared/downloads/avatar-task21/` altında bulunur; büyük ham çıktılar Git'e eklenmez.

## Kabul ölçütleri ve kanıt yolları

| Beklenen davranış | Kanıt |
| --- | --- |
| Önizleme hiçbir tabloyu değiştirmez | [MySQL: bütün tablo snapshot karşılaştırması](../tests/test_recall_review_mysql.py) |
| Gerekçe eksik/boşsa ret | Aynı dosyadaki 3 parametrik API testi; [React wizard](../frontend/tests/recall.test.tsx) |
| Yanlış lot kodu kesin onayı açmaz | React + [gerçek Chromium](../frontend/tests/browser/recall-safety.spec.ts); ayrıca backend yanlış kodu reddeder |
| Kapsam değişince yeni inceleme | Stok değişimi, ikinci kademe bildirimi, gerçek kilit yarışında yeni türev; Chromium'da inceleme sonrası gerçek satış |
| Aynı komut mükerrer recall üretmez | Eşzamanlı aynı-key MySQL; gerçek commit sonrası yanıt düşürme/reload/aynı-key-body Chromium |
| Atomik blokaj ve kısmi hata güvenliği | Render hatasıyla rollback; örtüşen iki recall ve yeni türev kilit yarışları; mevcut motor regresyonları |
| İkinci kademe alıcı ve belirsiz dış stok | MySQL gerçek FK kanıtı + Chromium alıcı/“Bilinmiyor”/belgelenmiş miktar kontrolleri |
| Recall sonrası blokeli satış reddi | API `LOT_BLOCKED` / 409; hem MySQL hem Chromium |

Testi yeniden çalıştırırken `MYSQL_DATABASE` yalnız ayrı `_test` şeması olmalıdır. Başlangıç migration'ı ve test bağımlılıkları README'deki gibidir. Hedefli backend komutu:

```bash
AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest \
  tests/test_recall_review_mysql.py tests/test_trace_recall_mysql.py \
  tests/test_second_tier_mysql.py tests/test_reworks_mysql.py \
  tests/test_cuttings_mysql.py tests/test_transfers_returns_mysql.py \
  tests/test_sales_shipments_mysql.py -q
```

Frontend: `cd frontend && npm test && npm run build`. Gerçek tarayıcı için yerel backend/proxy aynı izole şemayı kullanmalı; `AVATAR_E2E_DATABASE`, sunucu tarafında `AVATAR_API_KEY` ve gerekiyorsa `AVATAR_E2E_API_URL` yapılandırılmalıdır. `npx playwright test tests/browser/recall-safety.spec.ts` yeni üç gerçek senaryoyu çalıştırır.

## Güvenlik sınırları ve teslim

İnceleme izi ve elle kod yazma bir yetki/rol/ikinci kişi onayı değildir. Yeni iki alan eski demo/API çağrılarını kırmamak için opsiyonel çifttir; bu alanları göndermeyen API istemcileri yeni inceleme izi kontrolünü kullanmaz. Ortak X-API-Key'in kullanıcı bazlı yetkilendirme ve denetim izi eksikliği sürer. Otomatik blok kaldırma, geri çağırmayı silme, alıcı bildirimi veya doğrulanmış dış stok eklenmedi.

Dört gerçek özel ortam değeri kaynak ve son frontend bundle'ında arandı; eşleşme yok. Gitleaks değişiklik adayı ve commit geçmişi taramaları temiz. Özel `.env`, anahtar, log ve test verileri commit edilmez. AGENTS.md, PROJECT_CHECKLIST, Android, ML, belge merkezi ve genel tema değiştirilmedi. Backend/web/ortak sözleşme yazarlığı bu görevde tek entegrasyon ajanındadır; eşzamanlı dosya düzenlemesi yapılmadı.

Branch push'u ve PR erişim sonucu son Türkçe teslim raporunda belirtilir. Main'e birleştirme yapılmaz.
