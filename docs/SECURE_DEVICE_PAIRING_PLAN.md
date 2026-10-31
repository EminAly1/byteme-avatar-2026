# AVATAR — Güvenli cihaz eşleştirme planı

**Durum: tasarım; bu görevde eşleştirme servisi uygulanmadı.** Mevcut X-API-Key
ortak prototip anahtarı, yönetici oturumu veya cihaz kimliği değildir. Web/API/MySQL
portları loopback'te kalır; Android'in HTTP/LAN sınırı gevşetilmez. APK indirme
aracının geçici token'ı bir cihaz eşleştirme kodu veya API yetkisi değildir.

## Önerilen ayrı uygulama

1. **Güvenilir taşıma:** LAN'da yalnız HTTPS üzerinden ayrı, kontrollü giriş noktası.
   Sistemce güvenilen sunucu sertifikası veya yönetilen özel CA gerekir. İsteğe göre
   cihaz başına mTLS sertifikası. Kendi imzalı her sertifikayı kabul etme, hostname
   doğrulamasını kapatma veya genel HTTP API açma çözüm değildir.
2. **Yönetici onayı:** Önce gerçek yönetici kimlik doğrulaması ve dar roller gerekir.
   Yerel yönetici ekranı eşleştirmeyi başlatır; yeni cihazın adı/parmak izi gösterilir,
   kullanıcı açıkça onaylar. Mevcut ortak X-API-Key bu önkoşulu karşılamaz.
3. **Tek kullanımlık oturum:** Sunucuda en az 128 bit rastgele eşleştirme kimliği,
   en çok 60–120 sn ömür, atomik tüketim ve bağlı cihaz açık anahtarı/challenge.
   Elle girilen kısa kod tek başına kimlik doğrulama sayılmaz: TLS, yüksek entropili
   oturum, cihaz kanıtı ve yönetici onayıyla birlikte kullanılır.
4. **Deneme sınırı:** IP, oturum ve cihaz bazında oran sınırı; örneğin 5 yanlış
   denemede oturumu iptal et. Global limit/artan bekleme, yeniden başlatma ile limit
   sıfırlanmaması ve paralel denemelere atomik sayaç gerekir. Kod/anahtar loglanmaz.
5. **Cihaz kimliği:** Android kendi özel anahtarını Keystore'da üretir; sunucuya
   yalnız açık anahtar/CSR gider. Sunucu cihaz ID'si, kısıtlı kapsam ve kısa ömürlü
   yetki verir. Ana yönetici/API sırrı QR'a veya düz HTTP yanıtına konmaz.
6. **İptal/yenileme:** Yönetici kayıtlı cihazları görüp iptal eder; credential
   yenileme, son kullanım, kayıp cihaz ve anahtar rotasyonu açık politikaya bağlanır.
   İptal satış verisini silmez. Eski sunucuya ait frozen outbox başka sunucuya taşınmaz.
7. **Keşif ve QR:** mDNS yalnız adres önerir, güven kaynağı değildir. QR izinli
   HTTPS origin, sürüm, oturum kimliği, son kullanım ve doğrulanabilir sunucu kimliği
   taşır. İmzalı QR/pin güvenilir kaynaktan doğrulanır; kötü amaçlı host/redirect,
   URL içine anahtar koyma ve keyfî ağ hedefleri reddedilir. QR müşterinin/parolanın
   kendisini içermez; uygulama kullanıcıya bağlanacağı sunucuyu gösterir.
8. **Mevcut veri:** Room şeması/outbox/Keystore korunur. Bağlantı kimliği ve cihaz
   credential geçişi açık migration/prova gerektirir; bekleyen satış sessizce yeniden
   anahtarlanmaz veya farklı işletmeye gönderilmez.

## Kabul testleri — gelecek görevde çalıştırılacak

- Yanlış kullanıcı/yetki/anahtar ile başlatma ve onayın reddi; admin onayı olmadan yetki yok.
- Yanlış CA/hostname/pin, sahte mDNS ve değiştirilmiş QR'ın reddi; redirect/SSRF sınırı.
- Süresi geçen/yanlış kod, hız sınırı ve paralel tek kullanımlık kod tüketimi.
- Aynı kod/challenge/credential replay'i, başka cihaz anahtarıyla oturum çalma.
- İptal edilmiş cihaz ve sona ermiş yetkiyle stok/satış/PDF erişiminin reddi.
- TLS doğrulaması, kapsam ayrımı, sırların log/QR/APK içine çıkmaması.
- Room/outbox kalıcılığı, sunucu değişimi reddi, satış idempotency ve hata sonrası retry.
- Gerçek fiziksel Android'de sertifika güveni, Keystore ve ağ kopması provası.

Bu önkoşullar mevcut prototipte tamamlanmadığından Wi-Fi koduyla otomatik bağlantı
**ayrı güvenlik görevidir**. Bugünkü güvenli seçenek mevcut USB/eşleştirilmiş
kablosuz ADB reverse ve kullanıcı tarafından güvenli girilen bağlantı bilgisidir.
