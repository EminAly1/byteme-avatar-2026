# ML — Ajan C

Bu aşamada uygulama/model kodu yoktur. Python, pandas, scikit-learn kullanın; bağımlılıkları ilk ML PR'ında sabitleyin. Modeller operasyonel verinin yerine geçmez.

1. Üretim modeli: geçmiş kapatılmış emirlerin girdi ürün/miktarları ve dış üretici gibi işlem öncesi özelliklerinden beklenen mamul miktarı ve EKP tahmini. Gerçek sonuçları özelliklere sızdırmayın.
2. Parçalama modeli: tür, giriş ağırlığı ve işlem öncesi özelliklerden parça ağırlıkları tahmini. Gerçek fire ve parça miktarlarını yalnızca hedef/değerlendirme olarak kullanın.

Her model için anonymize veya açıkça sentetik etiketli örnek veri, sabit seed, zamana göre train/test ayrımı, eğitim kümesine dayanan basit ortalama/verim referansı ve model MAE karşılaştırması sunun. kg ve EUR/birim metriklerini ayırın; örnek sayısı ve küçük veri sınırlamasını raporlayın. Tahmin, gerçek ve sapmayı birlikte döndürün. Sentetik değerlendirmeyi gerçek işletme başarısı diye sunmayın.

Artifact metadata: model sürümü, eğitim zamanı, veri sürümü/hash'i, özellik şeması, metrikler. Artifact ve büyük veri ml/artifacts/ altında ignored tutulur. Güvenilmeyen pickle yüklemeyin. ML float çıktısı parasal defter hesabı değildir; gerçek maliyet Decimal backend hesabıdır. Geri çağırma/lot bağlantıları ML'ye başvurmaz. Önce offline eğitim/değerlendirme, sonra backend tahmin arayüzü; ayrı servis bu aşamada gerekli değil.
