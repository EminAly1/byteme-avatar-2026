# AVATAR — Görev28 son kabul

**31 Ekim 2026 · ByteMe.** Başlangıç `a7c80bc1652100f9a55c5ea17ed778477feb02cf` / PR #45.
Branch `feature/final-ux-crud-demo-v1`; [Issue #39](https://github.com/EminAly1/byteme-avatar-2026/issues/39).

## Kullanıcı sorunları ve düzeltmeler

- **Alış:** Görüntüle ve yeni alış sonrası gerçek GET ayrıntısı drawer'da açılır.
  Referans/tedarikçi/depo/tarih, ürün/lot/birim ve Decimal backend toplamı; frontend
  mali hesap yapmaz. Yükleniyor/hata/boş durum, mobil tam genişlik, Escape ve
  geri odak çalışır. Yeniden görüntülemede stok değişmez, API yazma isteği oluşmaz.
- **Formlar:** Ürün–lot, miktar–EUR ve tarih grupları; ortak 20 px ritim, 44 px silme
  alanı, üstten hizalı etiket/input/yardım. Mobil tek sütun; rastgele ekran CSS'i yok.
- **Reçete:** Boş filtrenin raw/kg kaynak ve Mamul/Yan ürün kg parça gereksinimi
  açıklanır. Taslağı kaybetmeden gerçek parça ürünü oluşturma; yeni kart katalogdan
  seçilir. Farklı ürünler tek reçetede; tekrar ürün devre dışı/alan hatası. Sürümleme,
  dağıtım, gerçek lot ve kesim kapanışı korunur.
- **AI:** Plan/malzeme/maliyet/paket/isteğe bağlı işlem kartları ve belirgin model
  sekmeleri. Metadata sınırları, örnek doldurma, alan hataları, model sürümü ve
  geçmiş korunur. KPI, beş parça çubuğu ve gerçekleşme tablosu yalnız sunucu çıktısı;
  gerçekleşme yokken **Henüz gerçekleşmedi**. **6.000 SYNTHETIC/0 gerçek tarihsel
  veri ve bazı metrik gerilemeleri** açık; model yeniden eğitilmedi.

## Gerçek CRUD ve değişmez geçmiş

| Kayıt | Gerçek endpoint | İzinli PATCH | DELETE |
| --- | --- | --- | --- |
| Ürün | GET/PATCH/DELETE /v1/products/{id} | name | Yalnız referanssız kart |
| Firma | GET/PATCH/DELETE /v1/parties/{id} | name ve/veya nullable contact | Yalnız referanssız kart |
| Depo | GET/PATCH/DELETE /v1/locations/{id} | name | Yalnız referanssız kart |

X-API-Key ve yazmada UUID Idempotency-Key gerekir. Silme açık iki aşamalı onaylı;
transaction/ebeveyn kilidi/FK ve iş JSON referansı denetimi var. Bağlı kart409
MASTER_IN_USE; yasak alan422. JSON referansı oluşturan rework taslağı ve üretim
tahmini de ürün kilidi tutar. Finansal hesap/şema/model değiştirilmedi.
Tür/birim/paket dönüşümü/SKU/roller/konum ilişkisi kilitlidir. Ad/iletişim güncel
ana kart bilgisidir; tarihsel fatura adresi/defter yeniden yazımı değildir.

Kesin alış, lot, hareket, üretim, kesim, satış, transfer, iade ve reçete geçmişi
silinmez. Listelerde ortak İşlemler düzeni; var olan tam işlem bağlantıları korunur.
Tekil endpoint yoksa **Kayıt özeti** yalnız gerçek liste yanıtını gösterir. Desteksiz
Düzenle/Sil açıklamalı devre dışıdır; uygun satış iade/iptali mevcut ayrı akıştadır.
Uyarı hesaplanan veridir. Reçetede yeni sürüm/kullanılabilirlik; belgede yalnız
geçici not düzenleme ve gerçek satıştan PDF. Sahte silme/arşivleme yoktur.

## Test kapısı

| Kontrol | Sonuç / sınır |
| --- | --- |
| React typecheck/build | Başarılı; son AI kaynak değişikliğinden sonra geçti |
| React unit | **107 passed**, 13 dosya; 35 hedefli tekrar 107'ye eklenmez |
| Gerçek MySQL/API | **20 hedefli passed**:15 master +2 çekirdek maliyet/replay +1 tahmin +2 rework;0 skipped |
| DEMO/APK testleri | **6 passed**:2 katalog/guard +4 paylaşım;0 skipped |
| Gerçek Chromium | **5 farklı senaryo**: alış;parça/reçete;üç master CRUD/bağlı ret;iki V2;eski AI kayıp-cevap/reload. P0 tekrarları yeni test sayılmaz |
| Responsive | **390/768/1440px** alış drawer/hizalama ve AI formunda taşma yok; AI sonuç768/1440 ayrıca açıldı |
| Gerçek APK CLI aktarımı | Loopback HTTP 17.178.340 byte/SHA256 eşit; tek GET sonrası süreç kapandı |
| Android | Kaynaklar değişmedi; yalnız assemblePreview **38/38 UP-TO-DATE**. Host/lint/cihaz paketi tekrar koşulmadı |
| Güvenlik | diff/Gitleaks ve özel değer taraması; yeni APK/env/Keystore/token/ham log Git dışında |

MySQL8: `avatar_task28_core_test` yıkıcı pytest, `avatar_task28_ui_test` gerçek UI,
`avatar_task28_demo_test` saf katalog için ayrıdır. Eski DB/volume silinmedi.
Zorunlu **1.543,50 EUR /18,16 EUR** maliyet, idempotency/FK, silme–alış ve JSON
referansı yarışları geçti. İlk nested-form/viewport-odak ve 3 sunum unit hatası
ilgili düzeltmelerle tekrar geçti; test/assertion silme veya skip yok. Son ekran
kanıtında duran geliştirme sunucusu yeniden başlatıldı; bu bir ürün testi başarısı
gibi sunulmaz. Backend tam-suite/Docker image rebuild'i tekrarlanmadı.

## Ekran kanıtları

Yalnız TEST/KURGUSAL veriler; API anahtarı/gerçek kişi yok. Başarılı gerçek akış
kayıtlarıdır; Android/SystemUI hata ekranı kabul kanıtı değildir.

| Ekran | Kanıt |
| --- | --- |
| Alış390px | [Drawer](evidence/final-ux-crud-demo/receipt-390.png) |
| Alış768px | [Drawer](evidence/final-ux-crud-demo/receipt-768.png) |
| Alış1440px | [Drawer](evidence/final-ux-crud-demo/receipt-1440.png) |
| Gerçek ürün/reçete | [Kaydedilen reçete](evidence/final-ux-crud-demo/recipe.png) |
| AI390px | [Girdi kartları](evidence/final-ux-crud-demo/ai-form-390.png) |
| AI768px | [Beş parça](evidence/final-ux-crud-demo/ai-cutting-768.png) |
| AI1440px | [Üretim sonucu](evidence/final-ux-crud-demo/ai-result-1440.png) |

## DEMO ve APK kolaylığı

`app.demo_catalog --confirm-database AD_test` yalnız açık onaylı yerel *_test
şemasında çalışır; canlı/default avatar ve yanlış onay bağlantıdan önce reddedilir.
**11 DEMO ürün**: bütün kuzu/dana/baharat/bağırsak/but/kol/sırt/kaburga/kıyma/sucuk/
kemik; 3 firma, 3 konum, 1 beş-parça reçete. İkinci bağımsız CLI çalışması aynı sonucu
verdi; snapshot değişmedi. Demo şemasında **alış 0, lot 0, satış 0, stok hareketi 0**.
Uygulama açılışında seed veya otomatik mali kayıt yoktur.

APK: `/workspace/artifacts/AVATAR-Preview-final-ui-polish.apk`,
com.byteme.avatar.preview,0.1.0-preview.2/code1, minSdk26/target35.
SHA256: **1d9a671d80d55c9ad6bcb4fe0ce5712463a256dc781756d7bed22092a68320e1**.
Görev28 Android'i değiştirmez; eski kurulum/uninstall/pm clear/veri silme yoktur.

[İndir/kur](INDIRME.md): `tools/share_apk.py` güncel build metadata/hash'ini doğrular;
rastgele 256 bit token, tek GET, varsayılan 180 sn/üst sınır 600 sn, idle kapanış ve hatalı
deneme sınırı. Yalnız izinli APK; klasör/env/API/DB yok. LAN açık --allow-lan ve
belirli özel IPv4 ister; genel 0.0.0.0 yok. HTTP yalnız güvenilir Wi-Fi içindir.
Fiziksel Wi-Fi/telefon ve QR denenmedi (qrencode kurulu değil). Genel Release/asset
URL'si yok; araç çalıştığı süre için terminalde gerçek geçici adres üretir.

## Güvenlik kararı ve kalanlar

[Wi-Fi eşleştirme planı](SECURE_DEVICE_PAIRING_PLAN.md): yönetici onayı, gerçek
kimlik doğrulama, HTTPS/mTLS, tek kullanımlık kod/rate limit, cihaz iptali/Keystore
ve replay/sahte keşif testleri **ayrı görev**. Genel API HTTP/LAN'a açılmadı.
Mevcut X-API-Key üretim oturumu değildir; APK token'ı eşleştirme kodu değildir.

Açık işlevsel P0 engeli tespit edilmedi. Fiziksel Android/LAN, Firefox/Safari,
manuel ekran okuyucu/tam WCAG ve bütün eski backend/e2e matrisi doğrulanmadı.
API35 başlatılmadı: **NO ACCEPTANCE / 0 test**. RBAC/TLS üretim dağıtımı, gerçek veri
ML kabulü, e-Fatura veya resmî yarışma gönderimi tamamlandı sayılmaz.

## Git checkpoint'leri

- Aşama1 **444a452cdb7052f67eaec410882edacec058dbd6**; push/uzak SHA doğrulandı.
- Aşama2 **fa09c475ac142bf3d1b3f2323f9cf6d94eb07f58**; push/uzak SHA doğrulandı.
- Aşama3 **aa1402024d156f93673db01a96f7ac502b6644d6**; push/uzak SHA doğrulandı.
- Main hedefli PR denemesi GraphQL **Forbidden** verdi; PR oluşturulamadı.
  Main'e merge yapılmadı. Son dokümantasyon commit'i branch başındadır.
- [Main hedefli manuel PR](https://github.com/EminAly1/byteme-avatar-2026/compare/main...feature/final-ux-crud-demo-v1?expand=1).
