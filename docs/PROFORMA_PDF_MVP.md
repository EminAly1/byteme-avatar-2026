# EK-05 — Proforma / satış özeti PDF MVP

27 Ekim 2026, Europe/Istanbul. Branch `feature/proforma-pdf-mvp`; main tabanı `5231684dc352af0634322dba3a99475a00fc0036` (PR #31/#32 dahil). **Yerel MVP kabulü başarılı; main merge ve Görev 19 birleşik kabulü ayrı.** Ortak checklist ve roadmap değiştirilmedi.

## Kurtarma

Kesintiden önceki 15 kaynak/bağımlılık/font dosyasının tamamı ve feature branch korundu; yeniden yazılmadı. Geçici `/tmp` ortamı/loglar kayboldu. Kurtarılan kaynaklar test edilmemiş olarak açıkça etiketlenen `9d42cfe` WIP checkpoint'iyle push edildi. Sonra eksik demo/testler eklendi ve mevcut kod tamamlandı. Eski Docker volume'ları/senaryo kaynakları silinmedi; ayrı Task18 şemaları kullanıldı.

## Ekranlar ve kaynaklar

- `/belgeler`: mevcut `GET /v1/sales?limit=20&cursor=...` ile tek satış sayfası; tüm katalog tarayıcıya yüklenmez.
- `/belgeler/satis/:id`: müşteri, kesin kalemler, kaynak lotlar, bağlı sevkiyatlar, iade/iptal ve canlı belge önizlemesi.
- `/satislar/:id`: **Belge taslağı oluştur** bağlantısı; belge ekranından kaynak satışa dönüş.
- `GET /v1/document-drafts/sales/{sale_id}`: yalnız seçilen satış için müşteri belgesi projeksiyonu. Sale/SaleLine→Party/Product/Lot; Shipment.sale_id ve ShipmentLine.sale_line_id; gerçek CustomerReturn/SaleCancellation ilişkileri.
- `POST /v1/document-drafts/proforma/pdf`: `sale_id`, `kind` (`proforma`/`sale_summary`), `expected_source_fingerprint` ve `draft` alır. **Muhasebe komutu değildir**; geçici PDF byte yanıtıdır.

Mevcut satış/sevkiyat/ürün/lot/party API'leri korunur. Yeni dar projeksiyon aynı MySQL modellerini ve mevcut `sales.profitability()` / düzeltme mantığını kullanır. Kesin satır toplamları ve satış toplamı yeniden tarayıcıda hesaplanmaz. Kârlılık servisinden yalnız düzeltme tutarları/durum ve net satış geliri projekte edilir; şirket içi maliyet, brüt kâr ve marj müşteri yanıtına/PDF'ye girmez.

Party adı/iletişimi **güncel iş ortağı kaydıdır**, tarihsel fatura adresi değildir. Sevkiyatta kayıtlı alıcı snapshot'ı gösterilir. Bağımsız sevkiyattan satış fiyatı türetilmez; gerçek satış FK'sı olmayan sevkiyat eklenmez. KDV/vergi oranı, dahil/hariç tutar ve tahsilat/nakit iade durumu uydurulmaz. Para birimi EUR, hesap otoritesi mevcut backend Decimal/DECIMAL kayıtlarıdır.

## Taslak ve kesin satış ayrımı

İki görünümde de zorunlu etiket başlık/alt açıklamadan bağımsızdır:

- **PROFORMA TASLAĞI — RESMÎ FATURA DEĞİLDİR**: kaynak satıştan ticari bilgilendirme taslağı.
- **SATIŞ ÖZETİ — MALİ BELGE DEĞİLDİR**: kesin satışın ve sonraki kayıtlı düzeltmelerin özeti.

Orijinal toplam, iade gelir düzeltmesi, iptal gelir düzeltmesi ve backend'den gelen düzeltme sonrası tutar ayrı gösterilir. Tam iade/iptal, belge başında ve durum bölümünde **GÜNCEL ÖDEME TALEBİ DEĞİLDİR** şeklinde belirtilir; PDF her sayfada kaynak durumunu tekrarlar. Kısmi iade orijinal satır miktar/fiyatını değiştirmez. Hiçbiri ödendi/ödenecek bakiye veya kayıtlı nakit iadesi iddia etmez.

Yalnız belge başlığı (120), açıklama (600), satıcı unvanı (200), satıcı iletişimi (300), belge tarihi, ödeme/vade notu (500), teslimat notu (500), özel not (1500), taslak referansı (100 karakter) ve kullanıcı beyanı demo etiketi düzenlenir. Metin alanları en fazla 21 satır; kontrol/yön değiştirme karakterleri reddedilir. Satıcı bilgisi doğrulanmamış kullanıcı taslağıdır. Kaynak satış tarihi, müşteri UUID, lot, miktar/fiyat/toplam ve maliyet değiştirilemez. Beklenmeyen JSON alanları 422 ile reddedilir.

**Geçici taslak — sunucuda saklanmıyor.** React state kullanılır; sayfadan ayrılınca taslak sıfırlanır. Veritabanı tablosu, migration, belge numarası, kaydetme/sürüm/audit geçmişi yoktur.

## PDF ve yazdırma mimarisi

ReportLab **5.1.0** ile backend'de `BytesIO` içine gerçek A4 portre (210×297 mm) PDF üretilir. Harici PDF API'si, HTML tarayıcı servisi veya müşteri dosyası için sunucu diski kullanılmaz. İndirilebilir yanıtta `application/pdf`, `Cache-Control: no-store`, `nosniff` ve yalnız doğrulanmış UUID/belge türünden güvenli `Content-Disposition` dosya adı vardır. Başlık/not dosya adına girmez.

Türkçe için [DejaVu Sans](https://dejavu-fonts.github.io/) Regular/Bold fontları uygulama asset'i olarak gömülüdür; [dağıtım lisansı](../backend/app/assets/fonts/LICENSE.txt) birlikte korunur. Sistem font kurulumu veya ağdan font indirme gerekmez; mevcut backend Dockerfile'ın `COPY backend/app` adımı bunları kapsar. Kullanıcı/veritabanı metni ReportLab markup'ına geçirilmeden escape edilir; URL/resim/JavaScript olarak çalıştırılmaz. A4 tablo başlıkları sayfalarda tekrarlanır; satırlar bölünmeden ilerler ve durum/uyarı alt bilgisi her sayfada bulunur.

Önizleme mobil ekrana uyarlanır; PDF ile aynı kaynak alanlarını gösterir, piksel düzeyinde aynı sayfa düzeni iddiası yoktur. **PDF indir**, sunucu PDF'sini indirir; **Yazdır**, ayrı taze kaynak GET kontrolünden sonra gerçek `window.print()` çağırır. Print CSS panel/menü/formları gizler, A4 ve tekrarlanan tablo başlığı kullanır.

PDF POST'u satış ve düzeltmeleri MySQL'den tekrar okur. Kaynak fingerprint'i önizlemeyle uyuşmazsa **409 DOCUMENT_SOURCE_CHANGED**; kullanıcı önce önizlemeyi yeniler. Yazdırmada da kaynak değiştiyse önizleme yenilenir ve tekrar inceleme istenir. Bu, okuma anının tutarlı görünümüdür; gelecekteki düzeltmelere karşı tarihsel belge garantisi değildir.

## Salt okunurluk ve güvenlik

Kaynak ve PDF aynı **REPEATABLE READ + SET TRANSACTION READ ONLY** snapshot akışındadır; autoflush kapalı, session sonunda rollback. Satış/stok/maliyet/recall/idempotency komutları çağrılmaz. Sonraki normal POST'un çalışmasıyla bağlantı havuzu yazma davranışının korunduğu da test edildi. X-API-Key mevcut server-side Vite/proxy'de kalır; browser bundle'a taşınmaz. Üretim RBAC/TLS kabulü bu görev kapsamında değildir.

Gitleaks 8.24.3 (indirilen binary checksum doğrulandı) ile 511 kaynak dosyası ve tüm yerel Git geçmişi sıfır bulgu verdi. Üç gerçek gizli değer kaynaklarda ve 36 build dosyasında bulunmadı. Mevcut 23 çekirdek/ortak dosya byte düzeyinde aynı; 15 Docker volume'u korundu. Yalnız izin verilen 20 dosya değişti. `git diff --check` temiz; PDF/log/screenshot/özel env Git'e alınmadı.

## Gerçek doğrulama

| Kontrol | Sonuç |
| --- | --- |
| Hedefli gerçek MySQL pytest | **27 passed**, başarısız/atlanmış yok: 22 yeni belge testi + mevcut 4 health/1 zorunlu maliyet-lot testi |
| React birim/bileşen | **83 passed**: önceki 72 + 11 yeni; başarısız/atlanmış yok |
| Typecheck / build | Başarılı (`npm run build` typecheck içerir) |
| Gerçek Chromium | **3 passed**: canlı satış→belge→PDF/yazdır; iade/iptal ve 45 satır; 390/1440 px, gerçek 404/401, kaynak satış bağlantısı ve otomatik axe sıfır ihlal |
| PDF parser | `pypdf==6.21.3`, gerçek indirilmiş dosyalar strict modda açıldı; A4 MediaBox, Türkçe, tutarlar, lotlar ve sayfa sayıları doğrulandı |
| MySQL yazma koruması | Enjekte edilen INSERT, gerçek **1792** hatasıyla reddedildi; yalnız SELECT/SET gözlendi |
| Sağlık / şema | `/health` ve `/health/ready` 200; MySQL 8.0.46/InnoDB, mevcut Alembic head `f1507a26b001`; yeni tablo/migration yok |

İlk geliştirme turlarındaki yeni fixture/erişilebilir seçici/TypeScript test hataları düzeltildi; eski testler silinmedi veya skip edilmedi. Mevcut Starlette/AnyIO deprecation uyarısı kabulü etkilemedi. Tam 360+ backend/ML regresyonu, tüm eski Chromium paketleri, Android ve Docker image rebuild'i bu görevde çalıştırılmadı; **Görev 19** birleşik kabulüne aittir. Fiziksel yazıcı testi yapılmadı; gerçek Chromium beforeprint olayı ve A4 baskı PDF'si doğrulandı.

## Kurgusal gerçek-DB demo

Yıkıcı test yalnız `avatar_task18_core_test`; demo ve Chromium yalnız `avatar_task18_demo_test`. Önceki Task13–17 ve işletme şemaları sıfırlanmadı. Mevcut ET→URT→SUC, 85 paket/1.543,50 EUR üretim ve Market A/B/C sevkiyat demo kodları korunur; yeni ayrı demo şemasına mevcut API'lerle açıkça hazırlanır.

| Kaynak durum | Orijinal EUR | Düzeltme sonrası EUR | Gerçek PDF |
| --- | ---: | ---: | --- |
| Aktif, Market A / 30 paket | 750,00 | 750,00 | 1 sayfa |
| Kısmi iade, Market B / 25 paket; 2 paket iade | 625,00 | 575,00 | 2 sayfa |
| Tam iade, Market C | 750,00 | 0,00 | 2 sayfa |
| Sevksiz satış iptali | 15,98 | 0,00 | 2 sayfa |
| Uzun Türkçe ürün/müşteri, 45 kalem ve 2 bağlı sevkiyat | 138,60 | 138,60 | 8 sayfa |

Bu rakamlar **KURGUSAL demo**; 25 EUR/paket satış fiyatı işletme verisi veya değerlendirme PDF'sinin zorunlu fiyatı değildir. Beş gerçek PDF tekrar okunurken ve tarayıcı kabulünde bütün **30 tablo** korundu; SHA256:

`93ebe8432d1b558b4563a08f145c7ba61ed52e2841ac65b9689d6e22c884b77d`

Tekrarlamak için önce ayrı *_test şemasına migration uygulayıp özel process env ile API'yi başlatın. `AVATAR_API_BASE_URL=http://127.0.0.1:8009 python -m app.demo_documents --prepare` yalnız açık hazırlık aşamasında kurgusal kayıtları oluşturur; JSON'u repo dışında seed dosyasına kaydedin. Ardından `python -m app.demo_documents --verify --seed-file /tmp/avatar-task18-seed.json` yalnız GET ve salt okunur PDF POST yapar; 30 tablo hash'ini ve gerçek PDF'leri doğrular. `--verify` için requirements-dev gerekir. Ham PDF/JSON/PNG/JUnit/log yalnız `/tmp` altında; Git'e eklenmez.

## Sınırlar ve sonraki entegrasyon

GİB/entegratör, mali mühür, resmî numaralama, KDV hesabı ve gönderim olmadığı için **e-Fatura/e-Arşiv değildir**. Kalıcı belge arşivi/sürüm/audit, OCR, Android kamera, ödeme/tahsilat, e-posta/push ve yeni marka/logo bu MVP'de yoktur. EK-03 ileride erişim kontrollü belge metadata/dosya altyapısını; EK-04 OCR ve insan onayıyla kaynak eşlemesini ekleyebilir. Bunlar mevcut taslak endpoint'inin kesin deftere yazmasına izin vermez; ayrı onay ve audit tasarımı gerektirir.
