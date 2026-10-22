# Frontend doğrulama raporu

Tarih: 22 Ekim 2026. Branch: feature/web-dashboard. Başlangıç commit’i: 25c6cb48c4b923bb78e78293f7826b78fa8248ff. Backend ve ortak dosyalar değiştirilmedi.

| Kontrol | Gerçek sonuç |
| --- | --- |
| Temiz npm ci | Başarılı, package-lock.json ile |
| npm run typecheck | Başarılı, TypeScript 7 |
| npm run build | Başarılı, Vite üretim çıktısı |
| npm run test | **25 passed**, 4 dosya; atlanan/başarısız yok |
| npm run test:e2e | **4 passed**, gerçek sistem Chromium’u + MySQL/FastAPI + yerel Vite; mock backend kullanılmadı |
| Ekranlar | 1440×1000 masaüstü üretim, 834×1112 tablet genel bakış, 390×844 mobil menü/gelecek modül; viewport dışına yatay taşma kontrol edildi |
| Ek güvenlik kontrolleri | CLI ile 0.0.0.0 bind denemesi başlamadan reddedildi; dist ve commit içeriğinde bilinen yerel credential değerleri bulunmadı |
| Proxy | Hatalı Host, uzak Origin ve originsiz POST 403; API anahtarı olmayan tarayıcı GET’i Node proxy üzerinden 200; .env.runtime dosya erişimi 403 |

## Gerçek uçtan uca akış

Tarayıcıdan WEB- önekli tedarikçi, dış üretici, iki konum ve dört ürün oluşturuldu. Üç satırlı alışta 100 kg et/970 EUR, 2 kg baharat/48 EUR ve 5 kg bağırsak/58 EUR API’ye ondalık string gönderildi; lot satırları görünür oldu.

Ayrı emir oluşturma ve dispatch çağrılarından sonra üç hammadde tüketimi, 85 paket çıktı, 467,50 EUR hizmet ve açıklamalı 22 kg fark ile kapanış yapıldı. UI’de backend’in **1.543,50 EUR** toplamı, **18,16 EUR** birim gösterim EKP’si, üç kaynak lot ilişkisi ve **85 paket** mamul bakiyesi doğrulandı. Hareket geçmişinde mamul kabulü görüldü. Sayfa yeniden açıldığında aynı kapanış kaydı görüntülendi. Bu akışta tarayıcı JavaScript hatası yoktu.

Ayrıca mevcut ET-2026-001 → URT-2026-045 → SUC-2026-045 demosu gerçek backend kaydından görüntülendi. Frontend bu sonuçları kendisi hesaplamadı veya sabit örnek veriyle doldurmadı.

## Birim/bileşen kontrolleri

- Pozitif miktar, en fazla 6 ondalık; tutarda en fazla 2 ondalık; geçersiz/negatif/büyük değerlerin reddi.
- Paket kg dönüşümü, kapanışta miktar farkı açıklaması ve çok satırlı alış dönüşümü.
- Backend OpenAPI tiplerine bağlı payload’larda Decimal string kullanımı; büyük parasal string’lerde float hassasiyet kaybı olmadan gösterim.
- next_cursor sayfaları ve tekrarlayan cursor hatası; 401/409/422/503 hata eşlemesi.
- Geçersiz formda POST olmaması; onaydan vazgeçme; dizi kök hatasının görünmesi.
- Ağ hatasında anahtar/gövde korunması, form kilidi ve yeniden mount sonrası sessionStorage’dan aynı komutla devam; başarıda pending kaydının temizlenmesi.
- Loopback host/origin kontrolleri; tarayıcı isteklerinde X-API-Key bulunmaması; anahtarın istemci kodu/yanıtlarında görünmemesi.

İlk browser koşularında iki test seçicisi düzeltildi: toplam maliyet hem kart hem tabloda bulunduğu için tek hedef seçildi; stok filtresine açık erişilebilir etiket eklendi. Son koşuda dört test de geçti.

## Sınırlar

- Backend’de olmayan parçalama/satış/recall/ML iş akışları uygulanmadı ve başarılı diye raporlanmadı.
- Tablet/mobil kontrolleri tüm iş formlarının kapsamlı cihaz testi değildir; yalnız belirtilen görünüm ve navigasyonlar kontrol edildi. Firefox/Safari çalıştırılmadı.
- Gerçek timeout sonrası backend’de commit olmuş bir HTTP isteğinin yeniden gönderilmesi tarayıcıda zorlanmadı; kaybolan yanıt ve aynı anahtarla tekrar bileşen/istemci testlerinde simüle edildi. Backend’in kendi idempotency testleri bu görevde yeniden çalıştırılmadı.
- Üretim oturum/rol yetkilendirmesi, Docker dağıtımı, büyük veri performansı ve gerçek offline çalışma bu aşamada doğrulanmadı.
- E2E örnek kayıtları demo veritabanına WEB- önekiyle eklenir; temizlik için backend’de DELETE API bulunmadığından otomatik silinmez.
