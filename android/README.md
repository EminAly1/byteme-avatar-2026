# Android — Ajan C

Bu aşamada uygulama kodu yoktur. Hedef: Kotlin, Jetpack Compose, Room (SQLite), Retrofit. Android SDK/JDK/Gradle sürümlerini ilk Android PR'ında sabitleyin; gerçek emülatör/cihaz testi ayrıca gereklidir.

İlk dilim: ürün/lot stoklarını API'den alma, lot seçerek satış taslağı oluşturma, backend onaylı satış gösterme. Room bir önbellek ve outbox'tır; merkezi stok otoritesi MySQL'dir. Offline satış yalnızca bekleyen taslaktır; kesinleşmiş stok veya satış olarak gösterilmez.

Her outbox komutu UUID idempotency anahtarı taşır. Bağlantıda FIFO gönder; timeout sonrası aynı anahtarla tekrar gönder. Backend satış + stok hareketini atomik kaydeder. 409 (blokeli lot/yetersiz stok/anahtar çakışması) insan müdahalesi gerektirir, kör tekrar yoktur. API sonucu ve server kimlikleri Room transaction'ıyla kaydedilir. Senkronizasyonda authoritative snapshot ilk prototip için yeterli; cursor tabanlı delta sonraki optimizasyondur. Offline eski veriden geri çağırma güvenliği garanti edilemez; bu yüzden offline kesin satış yoktur.

Backend bağlantısı emülatörde host için 10.0.2.2 olabilir; localhost cihazın kendisidir. Parola/APİ anahtarı kod içine gömülmez. İş mantığı ve maliyet dağıtımı backend'de kalır. Sözleşme: ../docs/api-contract.md.
