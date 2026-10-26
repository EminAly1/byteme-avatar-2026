# Kaynak, tutarsızlıklar ve açık kararlar

Kaynak docs/AVATAR_Assessment.pdf (3 sayfa), gerçekten okunmuştur. Belge gereksinim kaynağıdır; bu depo henüz bütün gereksinimleri uygulamaz. Teslim tarihi 1 Kasım 2026 kullanıcı talebinden gelir, PDF'de tarih yoktur.

| Konu | Kanıt / karar |
| --- | --- |
| Kuzu maliyeti | s.1: 25 kg × 11,50 EUR = 287,50 EUR, 351,00 EUR değildir. Gerçek belge toplamı yetkilice girilir; çelişen örnek sessizce düzeltilmez. |
| Kuzu ağırlığı | s.1: görseldeki parçalar 22 kg; 25 kg girişle 3 kg fark vardır. Görsel PDF'de ayrıntılı tablo olarak verilmemiştir; bu bilgi metindeki nota dayanır. 3 kg otomatik fire varsayılmaz, kullanıcı fire/yan ürün/fark olarak açıklar. |
| Sucuk maliyeti | 970 + 48 + 58 + 467,50 = 1.543,50 EUR; /85 = 18,158823… EUR. 18,16 yalnızca gösterimdir; 85×18,16=1.543,60. Ara hesap 6 hane, nihai kuruşta ROUND_HALF_UP; dağıtım artığı deterministik son uygun satıra eklenir ve toplam eşitliği test edilir. |
| Ağırlık dengesi | 107 kg girdi ve 85×1 kg çıktı örneğinde 22 kg fark var. Bu farkın fire, nem kaybı veya iade olduğuna ilişkin veri yok; işlem kapanışında açıklama ve miktar gerekir. |
| Birimler | kg ile adet/paket ayrı birimlerdir. SUC örneği için 1 paket=1 kg ürün dönüşümü sürümlü kayıtla tanımlanır, global eşitlik değildir. |
| Maliyet yöntemi | Prototip lota özgü gerçek alış maliyeti kullanır. FIFO/ortalama seçimi henüz istenmedi. Sevk edilen fakat iade edilen ham madde tüketilmiş sayılmaz; fiili tüketim kaydı esastır. |
| Dağıtım | Miktar veya değer ağırlıklı anahtar işlemde sürümlü snapshot olarak saklanır. Sıfır toplam ağırlık/referans değer reddedilir. Fireye maliyet yükleme politikası kullanıcıyla netleşene dek normal fire maliyeti satılabilir çıktılara dağıtılır; yan ürün değerleri açıkça kaydedilir. |
| VKP ve marj | Tek para birimi EUR, vergi/kur/diskontolar ilk prototip dışında. Net VKP, brüt kâr=VKP−EKP; marj=kâr/VKP, maliyet üstü oran ayrı kavramdır. VKP=0 için marj null. İşletme doğrulaması bekler. |
| Lot kimliği | İç UUID, tedarikçi lot kodundan ayrıdır; kod global benzersiz varsayılmaz. Parti+ürün+tedarikçi ile gelen tekrarlar idempotency ile yönetilir. |
| Recall kapsamı | İleri/geri izleme tam kayıt grafını dolaşır; yalnızca kaydedilmiş ikinci kademe alıcı gösterilir. Türetilen tüm etkilenen lotlar bloklanır; kapatılmamış üretimde bloke girdi kullanımı da reddedilir. |
| Offline satış | PDF tutarlı SQLite/MySQL senkronizasyonu ister ama çatışma kuralı vermez. Güvenli varsayım: offline yalnızca taslak, kesin satış backend onayından sonra. |
| Güvenlik | İş endpoint’leri X-API-Key ile yerel demo istemcisini doğrular; gerçek kullanıcı oturumu ve roller yoktur. İnternet üretimi ve fiziksel cihaz HTTPS kabulü uygulanmadı. |
| ML | İki model zorunlu; OCR ve anomali isteğe bağlı ve bu aşama dışında. Her model 600 SYNTHETIC kayıtla eğitildi; gerçek tarihsel kayıt 0. Gerçek işletme performansı doğrulanmadı. |

FastAPI kullanıcının seçimi ve PDF'nin “Go veya uygun modern teknoloji” koşuluyla uyumludur. Android ve iki sentetik ML modeli uygulanmıştır; güncel kanıt RELEASE_READINESS.md içindedir.


## Görev 12 kapsam açıklaması

Kuzu notunda PDF adaydan çelişkiyi saptayıp açıklamasını ister; gerçek fatura sunma koşulu eklemez. 287,50 EUR ve açıkça kurgusal parça ağırlıklarıyla yapılan demo bu açıklamayı somutlaştırır; 3 kg farkın gerçek işletme sınıfı otomatik atanmaz.

VKP raporu gerçekleşmiş SaleLine.unit_price değerini net EUR fiyatı olarak kullanır. Brüt kâr Sale.total_amount − SaleLine.consumed_cost toplamıdır; marj net gelire bölünür, sıfır gelirde null. Yeni stok/muhasebe kaydı oluşturulmaz. Vergi, iskonto, müşteri iadesi ve genel giderler modellenmediğinden şirket net kârı iddiası yoktur.

Demo kayıtları ayrı *_test şemasında KURGUSAL/SYNTHETIC veri setidir. ET/URT/SUC kodları PDF senaryosu için korunur. Eski seed isimleri/payload'ları değiştirilmedi: sabit idempotency anahtarlarının gövdelerini sonradan değiştirmek 409 yaratır. Veri seti manifest'i ve demo raporu kayıtların tamamını kurgusal olarak etiketler; gerçek işletme verisiyle birleştirilmez.
