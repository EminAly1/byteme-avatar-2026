# AVATAR — Son UI/UX düzeltmesi

**31 Ekim 2026 · ByteMe** · Branch `feature/final-ui-polish`.
Başlangıç `origin/main`: `b2e5c118d6422cab048064f59dd15fdd498bf15e`.
Takip: [Issue #39](https://github.com/EminAly1/byteme-avatar-2026/issues/39).
Issue içeriğini okuma denemesi GitHub GraphQL `Forbidden` verdi; bu rapor
kullanıcının son tasarım talimatına dayanır, Issue kapatıldı iddiası değildir.

## Önceki sorun ve düzeltme

| Önceki sorun | Yapılan küçük düzeltme | Doğrulama |
| --- | --- | --- |
| Web formlarının çoğunda boş metin/sayı alanı örneksizdi | Ortak Field/NumberInput üzerinden alana uygun **Örn:**; ürün/firma/depo, alış/lot, üretim/sevk/kapanış, kesim/reçete, satış/sevkiyat, transfer/iade/iptal/rework, dağıtım ve AI alanları tarandı. Ayrı belge notları, arama ve kimlik filtreleri de kapsandı | Kaynak taraması, typecheck/build, unit ve aşağıdaki sınırlı Chromium kontrolü |
| Örnek sayıların gerçek değerle karışma riski | Placeholder yalnız görünüm özelliğidir; register/defaults/payload değiştirilmedi. AI metadata örnekleri `Örn: 25` / `Örn: 0,5` gösterilir; mevcut örnek doldurma butonu yalnız kullanıcı tıklayınca çalışır | Boş alanın boş kalması, zorunlu alan reddi ve mevcut AI/idempotency testleri |
| Yardım/hata bazı alanlarla ilişkisizdi | Etiket/input `htmlFor/id`, yardım/hata `aria-describedby`, hata `aria-invalid` ile bağlandı. Native tarih alanlarında desteklenmeyen placeholder yerine takvim yardımı kullanıldı | Unit ve Chromium erişilebilir ad/açıklama kontrolleri |
| Soluk örneklerin görünümü ve buton aralıkları tutarsızdı | Mevcut renk ailesi/ikonlar korundu; placeholder normal ağırlıkta, `#60747c`, opacity 1. Form eylemine 16px ve ürün formu–filtre arasına 20px boşluk | 390px ekran görüntüsü, örnek alanda ölçülen kontrast **≥4,5:1**, taşma kontrolü |
| Android boş sunucu alanına emülatör URL'si gerçek değer olarak geliyordu | Alan boş kalır; soluk HTTPS örneği gösterilir. Emülatör `10.0.2.2` ve telefon `127.0.0.1 + ADB reverse` yardımları ayrılır | Yeni host UI testi boş EditableText ve kaydetmenin engellenmesini doğrular |
| URL/eksik anahtar hatası ekran dışında kalabiliyordu | Hatalar ilgili alanın altında; `normalizeBase` mevcut politikası kullanılır. Dialog güvenli kayıt başarılı olunca kapanır | LAN HTTP/release HTTP reddi, başka sunucuya anahtar taşımama, aynı sunucuda kayıtlı anahtarı koruma host kontrolleri |
| Android satış ve geçici belge alanları örneksiz/uzun etiketliydi | Kg/adet/paket miktarı, EUR fiyat, dokuz izinli belge alanında Örn: ve ayrı kısa yardım; sayı klavyesinde ileri/bitti. Kaynak satış alanları salt okunur kalır | 34 host testi; Room/outbox/PDF repository testleri dahil |
| Tekrarlanan marka ve teknik dil | `AVATAR · AVATAR 2026` tekrarları sadeleşti. “Recall UUID” → “Geri çağırma kayıt kimliği”; belge kaynak kimlikleri **Teknik ayrıntılar** altında korunur. Android tarihsel belgede “Linux kurulum yönergeleri” düzeltildi | Kaynak ve mobil menü/footer kontrolü; ikonlar/ByteMe ekip adı/paketler korunur |
| Filtre ve kimlik aramasında ne girileceği açık değildi | Ürün araması ve mevcut lot/işlem/tahmin/geri çağırma kimlik filtrelerine örnek ve yardım eklendi; hata düzenlerken temizlenir | Chromium'da ürün ve kaynak filtre alanları; yeni filtre API'si/sayfalama yok |

## Test sonuçları

| Kontrol | Sonuç ve sınır |
| --- | --- |
| Web `npm run typecheck`, `npm run build` | Başarılı; son CSS/etiket değişikliklerinden sonra build/typecheck tekrar geçti |
| Web unit `npm test` | **103 passed**, 12 dosya. Son metin/etiket düzeltmelerinden sonra etkilenen forms/documents/recall/prediction-v2 paketleri **33 passed**; tekrarlar103'e eklenmez |
| Android `testDebugUnitTest` | **34 passed**,0 failure/error/skip; 31 mevcut + 3 yeni bağlantı UI/doğrulama testi. Robolectric host çalışmasıdır, API28 cihaz kabulü değildir |
| Android `lintDebug`, `lintPreview`, `assemblePreview` | Başarılı; iki lint raporu **0 issue**. Son Android kaynak değişikliğinden sonra kapı tekrar geçti |
| Gerçek Chromium 390px | **1 smoke passed**,11 rota/27 render edilmiş metin-sayı alanı; yatay taşma0, sayfa JavaScript hatası0, API yazma isteği0. Menü açma/Escape/odak/arka plan kilidi korundu |
| Türkçe giriş | Chromium ürün paket ağırlığı `0,5`, alış miktarı `0,000001`, EUR tutarı `18,16`; input değerleri korunur. Gerçek satış/alış kaydı gönderilmedi |
| Gizli bilgi/diff kontrolü | APK özel dosya ve güncel sır taraması, web bundle sır taraması, Gitleaks ve `git diff --check` temiz; APK/env/Keystore/ham log Git'e alınmadı |

İlk Chromium koşusu, yeni yardım metninin kimlik alanının erişilebilir adına
karışması nedeniyle başarısızdı. Etiket ve yardım ayrı bağlandı; **aynı tam
smoke assertion'ları değiştirilmeden tekrar geçti**. Son boşluk düzeltmesinden
sonra da aynı smoke geçti. Test silme/skip veya iş kuralı assertion'ı gevşetme yok.
AI testlerindeki iki eski placeholder beklentisi yalnız yeni `Örn: 25` metnine güncellendi.

Chromium rotaları: `/urunler`, `/is-ortaklari`, `/depolar`, `/alislar`, `/uretim`,
`/parcalama`, `/hareketler`, `/satislar`, `/yapay-zeka`, `/geri-cagirma`, `/uyarilar`.
Test veritabanı yalnız **avatar_final26_test**; UI smoke GET okur, kayıt oluşturmaz.
Bu şemada örneğin satış formu ve seçilmemiş kesim ayrıntıları dolu değildi;
rota açılması bu formların tüm durumlarının kabulü sayılmaz.

## APK ve veri koruması

- Yeni APK: `/workspace/artifacts/AVATAR-Preview-final-ui-polish.apk`, 17.178.340 byte.
- SHA256: `1d9a671d80d55c9ad6bcb4fe0ce5712463a256dc781756d7bed22092a68320e1`.
- `com.byteme.avatar.preview`, **AVATAR Preview**, 0.1.0-preview.2/code1, minSdk26/target35.
- Sertifika SHA256: `b9fbe028ac6c63fc1f873fbe446a0693be3f6260d57807f89d75ad6ef0418f9f`;
  önceki Preview anahtarıyla aynı. Asıl `com.byteme.avatar` kimliği/ikonları değişmedi.
- Cihaza kurulum/uninstall/pm clear/veri silme yapılmadı. Room/Keystore güvenlik
  uygulaması, outbox/frozen key-body, idempotency, belge/PDF istemcisi değiştirilmedi.
  Bağlantı UI'si yalnız kayıtlı anahtarın varlığını alır; gizli değeri alana doldurmaz.
- Backend/MySQL/ML kaynakları, API sözleşmeleri ve satış/recall iş kuralları değişmedi.
  Android beş sekmesi korunur; Belgeler mevcut Ana Sayfa/satış girişindedir.
  Önceki kabul raporları korunur; yalnız istenen Linux ifadesi tarihsel dosyada düzeltildi.

## Hâlâ doğrulanmamış ekranlar

- **Fiziksel Android/API28 cihaz testi yapılmadı. API35: NO ACCEPTANCE / 0 test.**
  Emülatör başlatılmadı/onarılmadı. Host UI testi fiziksel klavye/ekran okuyucu kabulü değildir.
- Cihazda gerçek bağlantı, satış/onay/offline, kritik uyarı ve PDF çizim/SAF/paylaşma
  bu görevde tekrar denenmedi. Keystore/Room/outbox için mevcut host testleri geçti.
- Dolu üretim sevk/kapanış, kesim çıktıları, iade/iptal/rework ve belge editörü/PDF
  için bütün cihaz/viewport/uçtan uca matris yeniden koşulmadı. Kaynak ortak alanları
  tarandı; mevcut birim testleri geçti. Satış/recall kesinleştirme smoke kapsamında yoktur.
- Web gerçek 390px Chromium kontrolüdür; fiziksel mobil tarayıcı, Firefox/Safari,
  tam WCAG/manuel ekran okuyucu kabulü veya backend regresyon suite'i değildir.
- Kaynaklar ayrı feature branch'inde push edilir; main'e kendimiz merge etmeyiz.
  [Main hedefli PR compare](https://github.com/EminAly1/byteme-avatar-2026/compare/main...feature/final-ui-polish?expand=1).
