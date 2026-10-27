# AVATAR 2026 — Ek Özellikler Yol Haritası

> **Durum:** EK-02 anomali MVP yerel kabulü tamamlandı (PR #31); diğer ek paketler planlıdır, tam release/teslim kabulü ayrı.  
> **Ekip:** ByteMe. **Ürün adı/markası:** ekip isminden bağımsız; “İZORA” yalnız geçici aday, marka doğrulaması ve nihai görsel onay bekliyor.  
> **Başlangıç:** 25 Ekim 2026. **Plan öncelik güncellemesi:** 27 Ekim 2026. **Yarışma teslimi:** 1 Kasım 2026, 23:59 (Europe/Istanbul).  
> **Ana takip:** [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md). **Görsel kriterler:** [FRONTEND_VISION.md](FRONTEND_VISION.md).

## Değişmez çalışma kuralları

1. **Ön koşul / sürüm kapısı:** Görev 12 PR #20, ikinci kademe PR #27 ve React iş akışları PR #29 `main` dalında; EK-02 PR #31 de birleştirildi. Yerel iş akışları kabul kanıtlıdır, **son birleşik `main` tam regresyonu, release/video ve gönderim hâlâ açık**. Her opsiyonel özellik ayrı branch/PR ve hedefli testle geliştirilir; zorunlu teslim riske atılmaz. Zorunlu yarışma kapsamı ve video/teslim riske atılmaz. Her opsiyonel özellik ayrı branch/PR, gerçek test ve geri alma planıyla geliştirilir.
2. MySQL merkezî kesin kayıt; Room/SQLite yalnız mobil cache, taslak ve outbox. Frontend ve Android stok, maliyet, kesin satış veya recall otoritesi olamaz.
3. İleri özelliklerde veri ve kimlik güvenliği önceliklidir. Prototip X-API-Key **gerçek kullanıcı/rol yetkilendirmesi değildir**; halka açık internete mevcut sistemi açma. TLS/rol/erişim denetimi ve belgelerde güvenli saklama gereklidir.
4. Fatura OCR, tahmin ve anomali çıktıları **insan onayı olmadan kesin stok veya maliyet defterine yazılmaz**. Desteklenmeyen gerçek-zaman, doğruluk veya resmî belge iddiası yapılmaz.
5. **Hızlı ama güvenli test:** Her kod PR'ında ilgili modül için en az pozitif, olumsuz, idempotency/rollback ve gerçek veriye etki testi; mevcut iş kurallarını bozan değişiklikte ilgili regresyon. 30–31 Ekim'de son `main` tam backend/ML + frontend/browser + mümkün Android ve demo regresyonu. Hiçbir zaman eski test silinmez/skip edilmez; tüm testleri yalnız en sona bırakma.
6. Tüm demo belge ve müşteri bilgileri kurgusal etiketli kalır; sır/gerçek kişisel belge örnekleri commit edilmez.

## Uygulama sırası ve durum tablosu

**29–30 Ekim hedefi için EK-02 ve EK-05 öne çekildi.** Diğer bütün EK maddeleri korunur. Aynı backend migration alanını iki ayrı ajanla eşzamanlı değiştirme; her değişiklik tek PR'da gözden geçirilir. Test kanıtı olmadan işaretleme yapma.

| ID | Öncelik | Paket | Durum | Bitiş/kabul özeti |
| --- | --- | --- | --- | --- |
| KAPI-00 | **Zorunlu önce** | Release/yarışma teslim kapısı | Yerel demo GO / tam teslim NO-GO | PR #20/27/29 işlevlerinin dar kabulü ve PR #31 anomali MVP kabulü var; son birleşik test, video/tag/APK paketi/gönderim yapılmadı |
| EK-01 | **P2** | Mobil ↔ web güncel veri/senkronizasyonu | Planlandı (30 Ekim sonrasına ertelenebilir) | Sunucu onaylı satış/lot/recall web'de kendiliğinden yenilenir; Android uygulama aktifken refresh; offline kesin satış iddiası yok |
| EK-02 | **P1 — 29 Ekim hedefi** | Anomali ve akıllı uyarı merkezi — MVP | **MVP tamamlandı; final birleşik kabul bekliyor** | [PR #31](https://github.com/EminAly1/byteme-avatar-2026/pull/31), [teknik kabul](ANOMALY_ALERTS_MVP.md): SKT geçmiş/yaklaşan, bloke lot, yapılandırılmış düşük stok, kayıtlı tahmin–gerçekleşme EKP/verim; 53 hedefli backend, 72 React unit ve 4 Chromium. **Mükerrer fatura alarmı EK-03/04/05 belge kimliği sonrası; henüz yok.** Gerçek anomali ML iddiası yok |
| EK-03 | **P2** | Güvenli belge altyapısı + mobil fotoğraf yükleme | Planlandı (fatura taslağını bloke etmez) | Mobil kameradan belge yüklendiğinde merkezî kayıtta ve web inceleme listesinde görünür; güvenli metadata/dosya/izinler |
| EK-04 | **P2** | Fatura ve irsaliye OCR + insan onay ekranı | Planlandı (30 Ekim sonrasında) | Türkçe alanlar, kalemler, güven puanı, hata düzeltme; onaysız kesin stok/alış yok; gerçek ölçüm raporu |
| EK-05 | **P1 — 30 Ekim hedefi** | Profesyonel proforma/satış özeti taslağı, PDF/çıktı — MVP | Planlandı | Gerçek satış/sevkiyat verisinden düzenlenebilir belge taslağı; A4 PDF/yazdır, tarihçe; satışın kesin defteri değişmez |
| EK-06 | **P2** | Ortak minimalist ürün kimliği / ikon | Planlandı | ByteMe'den bağımsız ürün simgesi; anlamlı üç aşamalı izlenebilirlik; Android adaptive icon, web favicon/PWA ve masaüstü kısayolunda aynı vektör |
| EK-07 | **P2** | Açık/koyu görünüm ve vurgu seçenekleri | Planlandı | Önce iki eksiksiz tema (sistem/manuel/kalıcı); dört bağımsız tema yerine gerekirse 2 tema × 2 erişilebilir vurgu paleti |
| EK-08 | **P2** | QR / barkodla lot izleme | Planlandı | Android kamera ve web tarama; lotun kesin UUID'sine yönlendirme; bozuk/tekrar kod ve bloke lot testleri |
| EK-09 | **P2** | Denetim izi ve belge değişiklik geçmişi | Planlandı | Belge OCR düzeltmesi, onay, iptal ve kritik karar için kim/neyi/ne zaman; gerçek kullanıcı kimliği olmadan sahte kişi atfetme |
| EK-10 | **P2** | Stok, EKP, verim ve kârlılık raporları | Planlandı | Tarih/lot filtreleri, CSV/XLSX/PDF dışa aktarım; backend kesin verisi, EUR/kg/paket birimleri ve erişim sınırları |
| EK-11 | **P2** | Yedekleme, kurtarma, rol/TLS üretim hazırlığı | Planlandı | MySQL volume dışında kontrollü yedek, geri yükleme testi, kullanıcı/rol/HTTPS ve veri saklama politikası; internet yayını öncesi zorunlu |
| EK-12 | **P3** | Uyarı bildirimleri ve tercihler | Planlandı | Uygulama içi bildirimi; e-posta/push ancak izin, rol, sağlayıcı ve testler uygunsa |
| TEM-SON | **En son** | Temiz `main` / teslim artefaktları | Bekliyor | Test **kaynakları** korunur; üretilmiş logs/screenshots/APK/build/cache gerekiyorsa CI/Release'e taşınır; link/test kırılmaz |

**P1:** yarışma demosuna ve kullanıcının ana hedefine doğrudan değer katan opsiyonel iş, yalnız süre/GO uygunsa. **P2:** teslim riske girmemişse; çoğu sonraki sürüm. **P3:** sonra.

## 27–31 Ekim kısa sprint ve kesin kapsam

**Hedef**, 29 Ekim sonuna kadar EK-02'nin; 30 Ekim sonuna kadar EK-05'in dar kapsamlı, gerçek veri kaynaklı ve test edilmiş MVP'lerinin `main` üzerinde olmasıdır. **Bu bir plan/hedeftir, tamamlanma garantisi veya gerçekleşmiş durum değildir.** 31 Ekim tam teslim/demoya ayrılan emniyet payıdır. 1 Kasım 23:59 (Europe/Istanbul) son teslimi beklemeden mümkünse 31 Ekim'de gönderim yap.

| Tarih | Ana teslim | Kabul ve kesme kuralı |
| --- | --- | --- |
| **27 Ekim** | Devam eden Görev 15 — LOT-10 kayıtlı ikinci kademe zinciri | Kod + dar MySQL testleri + PR; başarısız iş ana dalda yarım açılmaz |
| **28 Ekim** | Görev 16 — transfer, iade, iptal, rework, ikinci kademe ve kâr için mevcut premium React arayüzü | Gerçek API, temel responsive işlem kabulü; pahalı dekoratif yeniden tasarım yok |
| **29 Ekim** | **EK-02 anomali/uyarı MVP** | **27 Ekim yerel MVP ve PR #31 tamamlandı**. 29 Ekim hedefi erken karşılandı; son birleşik regresyon 31 Ekim. Desteklenen 6 kod, salt-okunur ve sentetik tahmin sınırları açık |
| **30 Ekim** | **EK-05 proforma/satış özeti PDF MVP** + release kontrollerini başlat | Gerçek Sale/Shipment kaynaklı, güzel A4 önizleme/print/PDF, izinli taslak alanları; kesin satır/lot/maliyet değişmez; 'resmî e-Fatura' iddiası yok |
| **31 Ekim** | Son `main` regresyonu, release, Android APK yolu, kullanım kılavuzu, yalnız üretilmiş log/görsel temizliği, video ve **gönderim hazırlığı** | P0'a rastlanırsa yalnız düzeltme; ek özellik branch'i kapalı kalır. Public repo/≤15 dk video linkleri kontrol edilir |
| **1 Kasım (yedek)** | Gönderim ve alındı teyidi | Son tarih **23:59 Türkiye saati**; son dakikaya bırakma |

### EK-02 — MVP yerel kabulü ve kalan işler (PR #31)
- **Uygulandı:** 5 kural ailesi/6 kod, aynı operasyon FK'lı ve işlem öncesi kayıtlı Ridge tahmin–gerçekleşme karşılaştırması, salt-okunur MySQL ve /uyarilar. Mevcut sentetik ML gerçek anomali doğruluğu iddiası değildir.
- SKT yaklaşması ve kayıtlı düşük stok dahil; ürün birimleri birbirine toplama. İlgili lot/işlem/kural/eşik/gözlenen değer/severity ve ne yapılacağını kullanıcıya açık Türkçe göster.
- **Kalan:** okundu/bildirim geçmişi, e-posta/push, web'den eşik yönetimi ve belge altyapısı gelince mükerrer fatura denetimi. Yeni eğitim pipeline'ı bu sürümde yok.
- Güvenli smoke: eşik altı/üstü, boş veri, blokeli lot, tekrar taramada mükerrer olay yok, stok ve recall defteri mutasyonsuz.

### EK-05 — 30 Ekim MVP için sınır
- **EK-03 belge fotoğraf yükleme ve EK-04 OCR gerekmiyor.** Uygulamadaki **kesinleşmiş Sale/Shipment** kayıtları belgeyi besler; önce mevcut kayıtlar üzerinden **Proforma / Satış Özeti** yazdır/indir.
- Kullanıcı düzenleyebilsin: taslak belge başlığı, notlar, vade/teslim notu gibi **muhasebe dışı alanlar**; kaynak satış miktar/fiyat/lot ve kesin muhasebe değişmez. Kalem düzeltme gerekliyse ayrı açık fark/onay akışı veya güvenli taslak bilgi satırı; 'kaynak satış tutarı değişti' izlenimi verilmez.
- A4 şık tipografi, tutarlı ürün kimliği **isim/logo henüz kesin değilse nötr simge**, yazdırma stili ve tarayıcı PDF; sunucu kalıcılığı ancak güvenli erişim + sınırlı migration ve yeterli test mümkünse. Kaydetme mümkün değilse açıkça *geçici yerel taslak* olarak göster.
- **Resmî e-Fatura/e-Arşiv değildir.** GİB entegrasyonu, vergisel kesin belge numaralama, mali mühür ve gönderim bu sprintte yok.
- Smoke: örnek satışla doğru ürün/adet/EUR toplamı, A4 print/PDF render, bozuk veri/boş kayıt, kritik alan salt-okunurluğu, mobil önizleme. Gizli müşteri verisini repoya commit etme.

### Geliştirmeler kalıcı plandan çıkarılmadı
- **Teslim sonrası veya P0 yoksa sonraki sprint:** EK-01 otomatik mobil/web senkron, EK-03 mobil kamera yükleme, EK-04 Türkçe OCR ve manuel düzeltme, EK-06 ürün logosu, EK-07 açık/koyu tema, EK-08 QR lot tarama, EK-09 audit, EK-10 raporlar, EK-11 gerçek auth/TLS + yedek/restore, EK-12 bildirim. EK-02 ve EK-05 MVP'leri daha sonra tam ürün kalitesine yükseltilir.
- **EK-11 kullanıcı/rol/TLS kamuya açık dağıtımdan önce zorunludur.** Yerel demo ile güvenli internet servisini aynı şey gibi sunma.
- Teslimde tamamlanmayan opsiyonel değişiklikler `main` yerine ayrı branch'te kalır. Yarışma videosu yalnız çalışan, test edilmiş özellikleri gösterir.

## Paket bazında kapsam ve kabul

### EK-01 — Gerçek veride cihazlar arası güncelleme
- İlk sürüm: React sorgularını makul zaman aralığında veya odak geldiğinde otomatik invalidation/refetch; Android aktif/yeniden açılışta katalog ve satış senkronizasyonu; son güncelleme zamanını göster.
- Gerçek zaman isteği sürerse: güvenli auth/rol sonrasında SSE olayları, reconnect+cursor/snapshot ve kesintide tam refetch. Polling ile veri değişmemişse gereksiz istek azalt.
- Test: Android 6→5 kg satış sonrası web açık stok ekranında yeni 5 kg, yeni recall sonrası bloke görünümü; iki sekme, bağlantı kopması, offline taslak, kayıp cevap ve aynı idempotency key.
- Mevcut durum: merkezî DB ortaktır, fakat açık web ekranında otomatik anlık senkron **henüz yoktur**.

### EK-02 — Anomali uyarıları
- İlk sürümde açıklanabilir kural motoru: önceden tanımlanmış sapma eşikleri, son kullanma tarihi yaklaşımı, negatif stok girişimi, olağan dışı fire ve mükerrer fatura (belge modülü gelince).
- Her uyarıda kaynak kayıt UUID'si, tarih, ölçü, eşik, severity, açıklama ve aksiyon; tekrarları birleştirme, okunma/çözülme durumları.
- İsteğe bağlı gerçek ML tabanlı anomali, ayrı veri/held-out ölçüm ve yanlış pozitif/negatif raporu olmadan “yapay zekâ doğrulandı” diye sunulmaz.
- Test: eşik altı/üstü, geçmiş veri yokluğu, aynı olayla uyarı çoğalmaması, recall kesin kayıtlarının etkilenmemesi.

### EK-03 — Belge yükleme altyapısı
- Doküman metadata tablosu, sahip/bağlantı (alış/tedarikçi/sevkiyat), dosya hash, güvenli blob saklama, boyut/MIME sınırı, uzantı-içerik uyumu, izinler, silme/saklama politikası ve güvenli dosya okuma.
- Android kamerayla çekilmiş fatura/irsaliye fotoğrafını **taslak belge** olarak yükleyebilir; web inceleme kuyruğunda görünür. Offline yükleme kuyruğu istenirse mükerrer aktarımı engeller.
- Fotoğraftan GPS/EXIF ifşası ve kişisel veri riskleri, dosya virüsü/zip bombası, yetkisiz belge erişimi ve loglarda OCR içeriği açık yazılmaması ele alınır.
- Test: aynı fotoğrafın tekrarı, büyük/bozuk dosya, kopan ağ, erişim sınırı, mobil→web gözlem. Gerçek cihaz ve HTTPS olmadan halka açık kullanım yok.

### EK-04 — Fatura/irsaliye OCR
- Türkçe belge görüntüsü/PDF'den OCR; düzenli alanlar: belge türü, numara, tarih, tedarikçi/alıcı, kalem, miktar/birim, fiyat, vergi ve toplam.
- Kaynak fotoğraf ve önerilen alanlar **yan yana**; alan güveni, kaynağa görsel bağ, elle düzeltme, toplam/matematik kontrolü, ürün eşleştirme ve onay tarihçesi.
- OCR kayıtları yalnız öneri; **manuel onay olmadan** receipt, kesin alış/stok veya resmî muhasebe kaydı oluşturmaz.
- Test: elle etiketlenmiş izinli Türkçe örneklerle alan F1/character error vb. anlamlı metrikler; bozuk/yarım/kesik belge, çift belge ve kullanıcı düzeltmesi. Sentetik belge deneylerini gerçek işletme isabeti diye sunma.

### EK-05 — Belge oluşturma, taslak düzenleme, PDF
- Satış/sevkiyat kayıtlarından şirket/alıcı/kalem/tutar **salt kaynak aktarımı**; açıklama, belge görseli, opsiyonel taslak satırı gibi izinli edit alanları.
- Değişiklik geçmişi ve sürüm, A4 baskı stili, PDF indirme, print preview, mobil görünüm. İki aşamalı onay.
- Satışın kesin tutarı/lot/fiyatı “taslak düzenlendi” bahanesiyle defterde değiştirilmez; düzeltme ayrı açık iş akışı gerektirir.
- **Resmî Türkiye e-Fatura/e-Arşiv değildir.** GİB veya yetkili entegratör olmadan bu isimle yasal belge düzenlendiği söylenmez; etiket “Proforma / Ticari belge taslağı / Satış özeti”.

### EK-06 ve EK-07 — Logo/tema
- Ürün ByteMe takımından ayrı kimlik taşır. Çalışma adı onaylanana dek marka kesinleştirilmez.
- Minimalist vektör simge üç kayıt düğümünü ve izlenebilirliği çağrıştırır; telif/marka taraması gerekir. Android adaptif ikon, maskable PWA, favicon ve desktop kısayolu aynı master SVG'den türetilir.
- Açık/koyu tema sistem tercihine uyar; kullanıcı seçimi kaydedilir; söz konusu iki vurgu seçeneği gerekiyorsa her tema ile birlikte toplam 4 **kombinasyon** olur.
- Test: 360–1440 responsive, dark/light tüm zorunlu ekranlarda WCAG AA hedefi, logo 16/32/48/192/512 ölçek ve Android yuvarlak/kare mask.

### EK-08...EK-12 — Kurumsal fayda
- QR: okunamaz etiket ve yanlış lot kimliğinde güvenli hata; kesin lot blokajı yalnız backend'den.
- Audit: belge ve kritik işlemlerin değişmez geçmişi; gerçek rol/kimlik geldikten sonra kullanıcıya atıf.
- Raporlar: önceden kaydedilmiş kesin maliyete dayalı VKP/brüt kâr/marj, stok/gelir; verim/kâr hesapları frontend'de tekrar formüllenmez.
- Yedek: test edilmiş restore ve silme/retention politikası; `docker compose down -v` rutin adım değildir.
- Bildirim: şeffaf opt-in ve bildirim yetkileri; otomatik dışa veri sızıntısı olmamalı.

## Çalışma düzeni

- Aynı anda yalnız **bir ortak backend şema değişikliği** yapan ajan. Her görev yeni branch: `feature/extras-<id>-...`, PR, değerlendirme, test, ardından merge.
- Belge/OCR ve anomali ayrı migration/test dizileriyle gelişir. Kaynak PDF'deki zorunlu senaryolar her yeni PR'da korunur.
- Her adım sonrası bu tablodaki **Durum** ve kanıt linkleri güncellenir; mevcut `PROJECT_CHECKLIST.md` 66 zorunlu görevi izlemeye devam eder.
- **TEM-SON en sona**: kanıtlar yeni depoda/CI/Release'te doğrulanmadan eski dosyayı kaldırma, test kaynak kodunu asla “main temizliği” için silme, force-push veya history rewrite yapma. Önceki Git commitleri tarihsel olarak kalır.
- **Kesin teslim:** 1 Kasım öncesi video/gönderim ve gönderim doğrulaması opsiyonel işlerden üstündür. Bir P1 ekstra özellik yarım kalırsa `main` üzerinde feature flag / ayrı branch ile kapalı tutulabilir; release demosu stabil kalır.
