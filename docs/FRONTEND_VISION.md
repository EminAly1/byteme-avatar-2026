# ByteMe AVATAR 2026 — Profesyonel Frontend / UI–UX Vizyonu

**Durum:** Tasarım ve kabul hedefi (henüz uygulanmış olarak kabul edilmez). Kullanıcının 24 Ekim 2026 isteği. Yarışma son teslimi 1 Kasım 2026.

## Hedef ve yaklaşım
Gıda işletmesi üretim ve stok yönetimini günlük kullanıma uygun, güçlü bir **premium SaaS yönetim paneli** hissiyle sunmak. Yalnız değerlendirme PDF'sindeki minimum ekrana kapanmayıp, demo sırasında net ve güvenilir iş kararlarını destekleyen yararlı UX özellikleri eklenebilir. Öncelik: gerçek backend işlemleri, anlaşılır hata/sistem durumları ve yarışma demo akışı. Gösteriş için sahte KPI/veri/uyarı oluşturma.

## Görsel dil / art direction
- Modern, güven veren, kurumsal ama karakterli tasarım. Açık tema ilk seçenek; düşünülmüş koyu tema da mümkünse desteklensin.
- Tasarım tokenları: semantik yüzey, metin, border, vurgu, success/warning/danger, grafik renkleri; tercihen rafine lacivert/indigo ve teal aksanlar, sıcak nötrler. Palet birebir sabit değildir; bütün ekranda tutarlı olmalı.
- Net tipografik hiyerarşi, güçlü boşluk ritmi, yuvarlatılmış ama abartılmamış kartlar, ince çizgiler, fonksiyonel ikonlar; tutarlı buton ve alan stilleri.
- İkon sisteminde mevcut Lucide React'i yeniden kullan. Mevcut React 19, Vite, Tailwind, React Router, TanStack Query, React Hook Form/Zod ile uyumlu kal; gerektiğinde bileşen kütüphanesi kararını bütçe/build maliyetiyle değerlendir.
- Kontrollü hover/focus/transitions, hafif loading skeleton; dekoratif ağır animasyon, parallax veya dikkat dağıtan grafik kullanma. Reduced motion destekle.
- Ürün, lot, statü, stok/finans metrikleri görsel olarak birbirinden ayırt edilsin. Para birimi EUR, miktar birimleri ve Türkiye saat gösterimi doğru olsun.

## Responsive kriterleri
- **Desktop (>= 1280px):** kalıcı veya daralabilir sidebar, üst komut/arayıcı alanı, anlamlı tablo kolonları, kompakt/okunabilir KPI kartları, detay drawer/modal.
- **Tablet (~768–1024px):** daralabilir navigasyon, 2 kolon kart ızgarası, akıllı filtre paneli; tabloda gerekirse yatay kaydırma açıkça anlaşılır.
- **Mobil web (360–430px):** taşma/ekran dışı eylem yok; tek kolon, semantik kart liste veya kontrollü tablo alternatifi, kullanılabilir alt sayfa gezintisi veya drawer, başparmakla ulaşılabilir aksiyonlar, min 44px dokunma hedefi, klavye ve form hatalarında düzgün görünüm.
- Tasarım test viewport örnekleri: 360×800, 390×844, 768×1024, 1024×768, 1440×900. Hem portrenin hem landscape'in temel iş akışı kontrol edilsin.

## İş ekranları / öncelik
1. Dashboard: gerçek üretim emri durumu, stok/lot, kritik blokajlar, yapılan sevkiyatlar, tarihsel veriler varsa anlamlı analitik; API'de yoksa gösterme.
2. Hammadde/ürün, iş ortağı, depo, alış/lot ve stok yönetimi; arama, filtre, boş/hata/yükleniyor durumları.
3. Dış üretim/EKP: akışı adım adım sun, 1.543,50 EUR ve 18,16 EUR/pack hesaplarının kaynağını ve lot bağlantısını açıklığa kavuştur.
4. **Kuzu parçalama:** reçete ve versiyon seçimi, 25 kg→22 kg+3 kg fark denetimi, quantity/value maliyet karşılaştırması, parça lotlarının açık tablosu, işlem onayı ve transaction hatalarının anlaşılır gösterimi.
5. **Satış ve sevkiyat:** lot seçimi, blok/SKT uyarısı, kesin satış onayı, Market A/B/C 30/25/30 sevkiyat akışı, stok hareketini iki kez saymama.
6. **İleri/geri lot izleme ve recall:** erişilebilir ilişki grafı/tablo, kaynak→mamul→market zinciri, alıcı ve snapshot kontak bilgileri, tek işlemde recall ve bloke onayı, 409 LOT_BLOCKED görünümü. Network grafına eşdeğer erişilebilir liste alternatifi sun.
7. **İki zorunlu ML modelinin sonuçları:** tahmin / gerçek / sapma, model versiyonu, metrikler ve sentetik veri etiketi; model mevcut değilse tahmin uydurma.
8. Yararlı ekstra UX: kaydedilmiş filtreler (yerel/şeffaf), CSV rapor çıktısı, kritik lot etiketleri, toast bildirimleri, bağlamsal açıklamalar, tutarlı breadcrumb, klavye kısayolları (isteğe bağlı); sadece gerçek verilerle.

## Ürün davranışı ve güvenilirlik
- Önceki frontend güvenli loopback proxy tasarımını koru. API anahtarı browser storage, VITE_* veya açık kaynak içinde bulunamaz. Üretim auth'u varmış gibi davranma.
- Decimal giriş/çıktı string, hatalı para birimi/ölçü birimi uyarısı, idempotent retry, transient network ve 409/422/503 mesajları korunur.
- Kapanış, satış, recall gibi geri dönüşü zor eylemler için açık onay, işlem sonucu ve gerçek server ID gösterimi. Belirsiz ağ sonucunda aynı Idempotency-Key ile tekrar dene.
- A11y: klavye/focus görünürlüğü, etiketli formlar, erişilebilir dialog ve hata duyuruları, en az WCAG AA kontrastı (normal metinde 4.5:1), renk tek başına statü taşımasın, reduced motion.
- Kritik akışlarda kullanıcı testi: anlaşılır Türkçe mikro metinler, tarihçe, durum rozetleri, temiz boş durum, veri yükleniyor ve güvenli yeniden deneme.
- Gereksiz modal/aynı ekranı tekrarlayan birimler yok. Büyük ve aşırı kalabalık admin tablolarının mobil kullanımını özel tasarla.

## Kabul ve doğrulama
- Gerçek FastAPI + MySQL ile Chrome/Chromium'da her ana akış; mevcut ve yeni Playwright testleri, unit/component ve typecheck/build.
- Responsive ekran görüntüleri 360 / 390 / 768 / 1024 / 1440 genişlikte gözden geçirilsin. Kritik aksiyonlar görünür, basılabilir, taşma yok.
- Ekranların hiçbirinde demo/mock değerler gerçek canlı veri gibi sunulmasın. Sentetik eğitim/demo verisi belirgin etiketlensin.
- Kullanıcıya UI tasarımının önce/sonra ekran görüntüleri ve erişilebilir yerel demo adımları sağlansın.
- Zaman önceliği: yarışmanın zorunlu kapsamı ve Android/ML teslimi güvenceye alınmadan uzun süren görsel polish'a odaklanma. Temel çalışan UX → tam entegrasyon → profesyonel görsel iyileştirme ve ek özellik sırası.

Bu belge tasarım iş paketinin gereksinimidir, UI'ın zaten hazır olduğuna ilişkin test kanıtı değildir.


## Görsel kalite denetimi — 25 Ekim 2026, Frontend v2 sonrası karar

İşlevsel [Frontend v2](../frontend/VALIDATION_V2.md) PR #15 ile kabul edildi. Bir sonraki bağımsız geliştirme yalnız **frontend/** üzerinde tasarım/okunabilirlik/etkileşim ergonomisi iyileştirmesidir; backend, API gövdeleri, kesin maliyet, stok, recall ve tahmin hesapları **değiştirilmeyecek**. İzlenebilirlik, satış, sevkiyat, kesim ve AI akışları regresyona uğramamalı. Son görünüm ve mobil kullanıcı deneyimi yarışma videosundan **önce** doğrulanmalı; videodan sonra büyük UI refactor yapılmamalı.

### Gerçek Chromium ekran görüntülerinden saptanan sorunlar
- **Dashboard:** Büyük tanıtım banner'ı kritik KPI/hızlı aksiyonlardan önce çok yer kaplıyor. Hiyerarşi ve ekranın ilk bakışta anlaşılabilirliği geliştirilsin; sahte metrik eklenmesin.
- **Mobil satış:** Uzun kutu/form dizilimi, yön bulma ve `Formu kapat` gibi belirsiz etiketler. Kullanıcıya adım mantığı, görünür satış özeti, akıllı alan açıklamaları ve alttaki kritik onay için uygun ergonomi gerekiyor.
- **Kuzu parçalama masaüstü:** Parça adı/lot kodu satırlarında metinler birleşik görünüyor; satır hiyerarşisi, boşluk, monospace ID sunumu ve maliyet karşılaştırması gözden geçirilsin.
- **AI mobil:** Tekrarlanan sentetik veri uyarıları, altı basamaklı tahminler, çok uzun yatay kayan tablolar, göz yoran teknik UUID/metadata ve kalabalık sayfa. Özet → karşılaştırma → isteğe bağlı teknik detay hiyerarşisi kurulmalı. UI görünümünde kg/EUR en fazla anlamlı 2–3 ondalık tercih edilsin; **ham API değeri ve hesaplar değişmesin**, teknik ayrıntıda tam hassasiyet görülebilsin. Verim oranını anlamlı yüzde gösterimiyle açıkla.
- **Recall:** Etkilenen market ve 85 paket bilgisi raporun ilerleyen kısmında; üstte etki özeti, kritik durum ve aksiyonlara kolay erişim sağlanmalı. Teknik UUID'ler birincil başlık olmamalı. İlk kademe/son tüketici stok belirsizliği kesin biçimde korunmalı.
- **Mobil dashboard:** Uzun, yatay kayan operasyon/lot tabloları mobilde önemli satır verilerini saklıyor. Anlamlı responsive kart alternatifi veya açık tablonun tamamına erişim sağla.

### Görsel yön ve metin dili
Koyu gece laciverti/sıcak açık gri yüzeyler/rafine zümrüt-teal aksanlar bir başlangıç paletidir, zorunlu hex değil. Renkleri semantik tokenlarla belirle; kırmızı sadece gerçek engel/geri çağırma, amber uyarı, yeşil başarı gibi kullanılmalı. Ana CTA belirgin, ikincil işlemler sakin; hiçbiri ton farkı yüzünden kaybolmamalı. Tipografi için tablo, fiyat, stok, teknik kod ve gövde metninde farklı öncelikler. Türkçe metinler kısa ve işlem odaklı: `Formu kapat` yerine bağlama göre `Satış geçmişine dön`, `Yeni satış formunu gizle`; `Prediction UUID` yerine `Tahmin kaydı` + kopyalanabilir teknik referans. Birim/tarih/zaman dilimi açık yazılsın. Hassas 409/503/422 mesajlarının anlamı korunmalı.

### Polishing kabul kanıtı
- Önce/sonra **aynı demo ve aynı viewport/benzer veri** ile dashboard, satış, kesim, lot izleme, recall ve AI ekranları.
- 360×800, 390×844, 768×1024, 1024×768, 1440×900: kritik eylem ulaşılabilir; gereksiz yatay sayfa taşması yok. iPhone 360 genişlik hedefi minimum. Mobil kart veya kontrollü tablo davranışı açık ve test edilmiş.
- Renk kontrastı, klavye/focus ve reduced-motion korunur. Otomatik axe testi manuel kullanılabilirlik testinin yerine geçmez.
- Önceki 38 unit/component + 14 Chromium E2E + 1 eksik-model testi, ilgili frontend regresyonu geçmeli. Kullanıcı aksiyonlarının idempotency anahtarı/gövdesi ve backend hata cevabı değişmemeli.
- Vite'ın ~543 kB chunk uyarısı için **tercihen route-level lazy loading** yapılabilir, ancak kullanıcı iş akışı bozulmadan typecheck/build + kritik E2E ile doğrulanmalı. Uyarı eşiğini yükseltmek çözüm değildir.
- Şeffaf, tek ekran özeti + detay katmanı öncelikli; sadece süs olsun diye grafik/animasyon ekleme. Hiçbir gerçek veri sahte demo sayısıyla ikame edilmesin.
