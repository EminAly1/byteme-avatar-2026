# ByteMe web yönetim paneli

`feature/web-dashboard`, backend commit’i **25c6cb48c4b923bb78e78293f7826b78fa8248ff** üzerinden geliştirilmiştir. Yalnızca frontend/ değiştirilir. Bu branch, feature/backend-core’a bağımlıdır; önerilen PR hedefi backend-core’dur. Mevcut backend, Android, ML ve ortak docs dosyaları değiştirilmedi.

## Çalışan ekranlar

- Genel bakış: tüm API sayfaları tamamlandıktan sonra ürün, stoklu lot/konum, alış ve açık emir sayıları. Farklı stok birimleri toplanmaz; satış/kâr gibi API’de olmayan metrikler gösterilmez.
- Ürünler: liste, SKU/ad araması, tür filtresi, ürün oluşturma, paket kg dönüşümü.
- İş ortakları ve depolar: tedarikçi/dış üretici rolleri, iletişim, işletme deposu, üretici konumu ve firma ilişkisi, karantina.
- Alış/lot girişi: çok satırlı alış, toplam satır maliyeti, lot kodu, opsiyonel son tüketim tarihi, depo ve kayıt ayrıntıları.
- Stok: ürün/lot/konum filtreleri, backend bakiyesi ve kullanılabilir miktar, bloke/kullanılamaz durumları, imzalı stok hareketleri.
- Dış üretim: ayrı emir oluşturma → hammadde sevki → fiilî tüketim/iade → mamul/hizmet/miktar farkı ile kapanış. Kapanış sonrası gerçek maliyet, EKP ve kayıtlı kaynak lot bağlantıları.
- Kuzu parçalama, satış raporları, tam lot izlenebilirliği, recall ve ML menüleri açıkça **Geliştirme aşamasında** durumundadır; sahte işlem göndermez.

React Router, TanStack Query, React Hook Form + Zod ve yeniden kullanılabilir form/tablo/durum/onay bileşenleri kullanılır. Maliyet veya stok muhasebesi frontend’de hesaplanmaz; yalnızca backend ondalık string sonuçları formatlanır. Saatler Europe/Istanbul ile gösterilir.

## Yerel çalıştırma ve güvenlik

Önce backend/README.md akışıyla MySQL, migration ve backend’i başlatın. Backend ve Vite Node süreçlerine **aynı AVATAR_API_KEY** güvenli process ortamından verilmelidir. Anahtarı kaynak koduna, VITE_* değişkenine, tarayıcı storage’ına veya komut/log çıktısına koymayın. Frontend .env dosyasından API anahtarı otomatik okunmaz.

```bash
# AVATAR_API_KEY zaten güvenli process ortamında export edilmişken
cd frontend
npm ci
npm run dev
```

Yalnızca `http://127.0.0.1:5173` origin’i kullanılır. `localhost` farklı origin’dir ve proxy’de kabul edilmez. Vite `127.0.0.1` adresine bağlanır; CLI ile `--host 0.0.0.0` verilirse başlatma reddedilir. Vite sunucu anahtarını `/api/v1` → backend `/v1` isteklerine kendi ekler; tarayıcı hiçbir X-API-Key göndermez.

Varsayılan backend hedefi `http://127.0.0.1:8000`. Gerekirse Vite process ortamında **AVATAR_API_PROXY_TARGET** veya sır içermeyen mevcut **VITE_API_PROXY_TARGET** ayarlanabilir; hedef yalnızca HTTP loopback IP’si olabilir. Kullanıcı bilgisi/path/query içeren veya uzak hedefler reddedilir. Host/Origin/cross-site denetimi vardır; yazma istekleri aynı Origin’i gerektirir. Proxy yanlış/missing key durumunda 401/503; ağ kesintisinde hata gösterir, örnek verileri canlı veri gibi sunmaz.

Bu düzen **yalnızca yerel demo/geliştirme** içindir. Vite geliştirme sunucusu kimlik doğrulama servisi değildir. Aynı makine/aynı origin’deki güvenilmeyen süreçlere karşı tam bir güvenlik sınırı sağlamaz. Üretimde kullanıcı oturumları, backend yetkilendirmesi, TLS ve uygun dağıtım sunucusu gerekir. Mevcut Docker frontend için portu dışarı açmak veya proxy’yi gevşetmek bu çözümün kapsamında değildir. `npm run preview` statik derleme önizlemesidir; API proxy’si kapalıdır.

## İstek ve hata davranışı

- Tüm POST’lar yeni bir UUID `Idempotency-Key` ile başlar; kullanıcı onayından önce istek gönderilmez.
- Ağ hatası/5xx sonucunda aynı gövde ve anahtar korunur; otomatik yeni anahtar üretilmez. Form kilitlenir ve **Aynı işlemi tekrar dene** sunulur.
- Sonucu belirsiz istek/form bilgisi sekmeye özel sessionStorage’da tutulur; sayfa yeniden açıldığında aynı komut geri alınır. Bu bilgi **API anahtarı içermez**. Başarılı cevap veya kesin 4xx sonrasında kaldırılır. Storage kapalıysa sayfa belleğinde retry çalışır; sayfayı kapatmayın.
- 401, 409, 422, 503 Türkçe açıklanır. Miktar ve para string’dir; virgül nokta haline getirilir, tutar hesaplanmaz. Backend doğrulaması son otoritedir.
- `next_cursor` bitene kadar tüm sayfalar okunur; tekrar eden cursor hata sayılır. Arama/filtre bu tamamlanmış listede yapılır. Bu yaklaşım küçük prototip verisine uygundur; büyük veri için backend filtreleme/toplam endpoint’i ve kademeli listeler sonraki iştir.

## API tipleri

`src/lib/openapi.d.ts` çalışan backend’in `/openapi.json` çıktısından openapi-typescript 7.13.0 ile üretilmiştir. `payloads.ts` bütün yazma gövdelerini bu request tipleriyle kontrol eder. Backend okuma cevapları OpenAPI’de ayrıntılı modellenmediği için `types.ts` cevap tipleri gerçek API/service çıktısına göre elle tanımlanır ve tarayıcı testlerinde doğrulanır.

Pydantic OpenAPI Decimal girişlerini sayı/string olarak gösterse de backend’in BeforeValidator’ı string gerektirir; frontend yalnızca string gönderir. TypeScript 7 altyapısı korundu. Tip üreticisinin TypeScript 5 peer şartı nedeniyle üretim komutu proje bağımlılık ağacından ayrı geçici bir dizinde çalıştırılabilir:

```bash
# Backend açıkken; çıktı yolunu kendi checkout yolunuza göre ayarlayın.
cd /tmp
npm exec --yes --package=openapi-typescript@7.13.0 --package=typescript@5 -- openapi-typescript http://127.0.0.1:8000/openapi.json -o /workspace/byteme-avatar-2026/frontend/src/lib/openapi.d.ts
```

## Testler

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm run test
# Gerçek MySQL/backend + aynı anahtarlı Vite açıkken:
npm run test:e2e
```

E2E sistem Chromium’unu kullanır (`/usr/bin/chromium`, gerekirse CHROMIUM_PATH ile değiştirin). Backend’in canonical demosu önceden repo kökünden `PYTHONPATH=backend backend/.venv/bin/python -m app.demo` ile yüklenmiş olmalıdır. AVATAR_API_KEY, sızıntı kontrolü için Playwright’ın Node process ortamında da gerekir; tarayıcıya verilmez. Testler üretim DB’sinde çalıştırılmamalıdır: WEB- önekli ürün/firma/alış/emir kayıtları oluşturur, mevcut veriyi silmez. Başarısız test sonrası da bu kayıtlar kalabilir.

Sonuçlar: **25 birim/bileşen testi**, **4 gerçek Chromium testi** geçti. Ayrıntılar [TEST_REPORT.md](TEST_REPORT.md). Ekran görüntüleri/test çıktıları ignored test-results/ altındadır. Backend testleri bu frontend görevinde yeniden çalıştırılmadı.
