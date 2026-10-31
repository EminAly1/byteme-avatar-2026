# AVATAR — Kullanım kılavuzu · ByteMe

31 Ekim 2026. [İndirme ve kısa Linux kurulumu](INDIRME.md). Üretim, lotlu stok, satış ve geri çağırma prototipi. MySQL kesin kayıt; React işlem ekranı, Android Room ise cache/taslak/outbox'tır. Bütün örnekler **KURGUSAL / SYNTHETIC**. Ürün **AVATAR**, ekip **ByteMe**; ayrı demo APK adı **AVATAR Preview**.

## Yerel web kurulumu

Docker Compose/BuildKit, Python 3.12 ve Node ≥22.12 gerekir. Var olan servislerle 8000/5173/33330 portları çakışıyorsa yalnız size ait eski demo servislerini durdurun; veri/volume silmeyin. Yeni proje adı ve yeni *_test veritabanı kullanın.

```bash
python tools/release_env.py init --env-file /tmp/avatar-final.env \
  --project byteme-avatar-final-demo --mysql-port 33330
docker compose --env-file /tmp/avatar-final.env config --quiet
docker compose --env-file /tmp/avatar-final.env build
docker compose --env-file /tmp/avatar-final.env up --no-build -d --wait
python tools/verify_compose.py --env-file /tmp/avatar-final.env --output /tmp/avatar-final-smoke.json
```

Web: **http://127.0.0.1:5173**; API: http://127.0.0.1:8000. Anahtar `.env`/APK/browser bundle'a gömülmez; özel dosya 0600 olarak repo dışında kalır. Vite server-side proxy anahtarı ekler. `/health` süreç, `/health/ready` veritabanı sağlığıdır.

Bu bulutta standart Docker build DNS çözümleyemedi. Yalnız bu tür kısıt varsa belgeli alternatif:

```bash
python tools/release_env.py build-proxy --output /tmp/avatar-final-build-network.json
docker compose --env-file /tmp/avatar-final.env -f docker-compose.yml \
  -f /tmp/avatar-final-build-network.json build
docker compose --env-file /tmp/avatar-final.env up --no-build -d --wait
```

Proxy/CA process ayarları güvenilir olmalı; TLS doğrulamasını kapatmayın. Runtime servisleri host network kullanmaz; portlar loopback'tedir. Güvenli durdurma `docker compose --env-file /tmp/avatar-final.env stop`; yeniden başlatma `up --no-build -d --wait`. `down -v`, prune ve işletme DB'sinde yıkıcı test kullanmayın.

Demo CLI/testler için:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt -r ml/requirements.txt
npm --prefix frontend ci
```

Tam kurgusal hazırlık [DEMO_RUNBOOK](DEMO_RUNBOOK.md) içindedir. Test DB'leri ve browser profilleri demodan ayrıdır; kayıtları temizlemek için demo şemasında pytest çalıştırmayın.

## Android kurulumu ve bağlantısı

[İndir/kur ve imza güvenliği](INDIRME.md), [Linux geliştirme kurulumu](../android/ANDROID_SETUP.md).
JDK17, Gradle wrapper8.10.2, SDK35; minSdk26. Kaynaktan Preview APK:

```bash
./android/gradlew -p android testDebugUnitTest lintDebug assembleDebug lintPreview assemblePreview
adb install android/app/build/outputs/apk/preview/app-preview.apk
adb reverse tcp:8000 tcp:8000
```

Yeni **AVATAR Preview** paketi `com.byteme.avatar.preview` eski uygulamadan ayrıdır.
Eski uygulamanın Room/outbox verisi ve Keystore ayarları taşınmaz; eski uygulamayı
kaldırmayın/verisini silmeyin. Yeni paketin cihaz kurulumu henüz doğrulanmadı.
Mevcut debug paketi `com.byteme.avatar` korunur; farklı sertifikayla yükseltilmez.

Ayarlar üst çubuktadır. USB veya eşleştirilmiş kablosuz ADB'de sunucu
**http://127.0.0.1:8000/**, emülatörde **http://10.0.2.2:8000/**; aynı özel API
anahtarını ekrana güvenli biçimde girin. Anahtar Keystore ile şifrelenir;
Retrofit loguna/komut argümanına yazılmaz. Doğrudan LAN HTTP yerine ADB reverse
kullanın. [Kablosuz ADB](https://developer.android.com/tools/adb#wireless-android11-command-line)
cihazda ayrıca doğrulanmalıdır.

Beş alt sekme **Ana Sayfa / Stok / Satış / Bekleyenler / Uyarılar** korunur.
Stoklar kayıtlı ve kullanılabilir miktarı ayırır; `20.500000 → 20,5`,
`0.000001 → 0,000001`; gerçek değer değişmez. Blokeli/SKT geçmiş lot satılamaz.
Müşteri/lot/miktar/fiyat → özeti incele → kesin onay. Sekme değişiminde form korunur.
Başarı backend satış/satır/hareket UUID'leri ve yenilenmiş bakiye ile doğrulanır.
Offline kayıt **taslaktır**, kesin satış değildir; belirsiz cevapta aynı outbox
key/body ile devam edin. Recall `LOT_BLOCKED/NEEDS_ACTION` üretir.

Ana Sayfa kritik uyarı kartı ve **Uyarılar**, gerçek `/v1/alerts/summary` ve
`/v1/alerts` yanıtlarını kullanır. Kritik/Uyarı/Bilgi, lot/kaynak ve önerilen işlem
ayrıdır. Bağlantı hatası anlaşılır gösterilir; uyarı hatası satış sync'ini durdurmaz.
Uygulama içi uyarıdır; push/Firebase veya kapalı uygulamada bildirim iddiası yoktur.

**Belgeler** Ana Sayfa ve onaylı satış geçmişinden açılır; altıncı sekme eklenmez.
Onaylı satış seç → Proforma/Satış Özeti → salt-okunur ayrıntı → gerekirse ayrı
**Geçici notları düzenle** ekranı → **PDF önizle**. Kaynak müşteri, miktar, fiyat
ve lot kilitlidir. PDF backend'den gelir; MIME/imza/boyut kontrolünden sonra
PdfRenderer yalnız istenen sayfayı açar. **Kaydet** sistem dosya seçicisini,
**Paylaş** desteklenen cihazda dar kapsamlı content URI'yi kullanır. Genel
saklama izni yoktur. PDF409'da kaynak yenilenir. Proforma resmî e-Fatura değildir.
31 host testi ve PDF sözleşmesi geçmiştir; native çizim/SAF/paylaşım **cihazda
kabul edilmedi**. API28/fiziksel cihaz bu sürümde denenmedi;
**API35: NO ACCEPTANCE / 0 test**. [Görev25 kanıtı](ANDROID_DOCUMENTS_ACCEPTANCE.md).

## İlk kartlar, alış ve lot

1. `/urunler`: SKU, ürün türü ve stok birimini belirleyin. Paket ürününde paket kg dönüşümü gerekir. Kg/paket/adet birbirine toplanmaz.
2. `/is-ortaklari`: tedarikçi, müşteri veya dış üretici rolünü seçin.
3. `/depolar`: işletme deposu/dış üretici/karantina konumunu oluşturun.
4. `/alislar`: tedarikçi ve kabul deposu, ürün/lot/miktar/gerçek alış maliyeti ve varsa SKT girin. Onay sonrası lot ve stok hareketi oluşur.

`/stoklar` fiziksel ve kullanılabilir miktarı ayırır. Karantina, blokeli veya süresi geçmiş stok satılabilir sayılmaz. Bilinmeyen SKT uydurulmaz; miktar/para hesapları backend'e aittir.

## Dış üretim ve kuzu parçalama

`/uretim`: dış üretim emri → üreticiye sevk → fiilî tüketim, hammadde iadesi, hizmet referansı, mamul kabulü ve açıklamalı miktar farkı → kapanışı gözden geçirip onaylayın. Sevk mülkiyeti değiştirmez; kesin kapanış atomiktir.

Örnek: 970+48+58+467,50 = **1.543,50 EUR**, **85 paket**, gösterim EKP **18,16 EUR/paket**. Toplam, yuvarlanmış EKP × paket sayısından yeniden üretilmez.

`/parcalama`: sürümlü reçete/dağıtım yöntemi, kaynak kuzu lotu ve gerçek girdi/çıktılar. **25 kg →22 kg + açıklanmış3 kg**, gerçek örnek alış **287,50 EUR**. 3 kg fark otomatik “kanıtlanmış fire” değildir; PDF'nin 351 EUR tutarsızlığı varsayımlar belgesindedir. Beş parça gerçek lot/FK ve maliyetle oluşur.

## Satış, sevkiyat ve kârlılık

`/satislar`: müşteri, kullanılabilir lot/konum, miktar ve VKP → gözden geçirme → kesin onay. `/satislar/:id` fiyatları, stok hareketini, backend tüketim maliyeti/brüt kâr/marj ve iade/iptal sonrası netleşmiş sonucu gösterir. Bu şirket net kârı veya tahsilat muhasebesi değildir.

`/sevkiyatlar`: satışa bağlı sevk aynı satış hareketini referans alır; ikinci stok düşüşü yapmaz. Bağımsız sevkiyat kendi stok çıkışını oluşturur, satış/fiyat uydurmaz. Kurgusal Market A/B/C örneği **30/25/30=85 paket**.

## Transfer, iade, iptal ve rework

`/hareketler` kaynak konum/lot ve hedef konumla bağımsız transferi; satış detayındaki bağlantılar müşteri iadesi/iptali açar. Transfer örneği **20→13/7 kg**, maliyet değişmez. İade yalnız gerçekten sevk edilmiş satış satırından kabul edilir; sevksiz uygun satış iptal edilir. Her ikisi karantinaya gider; otomatik QA serbest bırakma/nakit iade yoktur.

Rework için mevcut kesin üretilmiş kg mamul kaynağını seçin → taslak → fiilî çıktı ve açıklanmış fark/hizmet → iki aşamalı kapanış. **10→9,5+0,5 kg**, **100+15=115 EUR**. Taslak stok tüketmez; kapanış yeni lot ve gerçek soy bağı oluşturur. Kaynak SKT uzatılmaz, karantina kalite onayı yerine kullanılamaz. Önceden recall edilmiş demo lotuyla yeni işlem denenmez; geçmiş kapanış incelenir.

## İkinci kademe ve geri çağırma

`/dagitimlar`: gerçek şirket sevkiyat satırı → kayıtlı ikinci kademe alıcı → miktar, olay tarihi, referans ve kanıt açıklaması. Örnekte Market A→Dağıtıcı X **12 paket**. Şirket sevkiyatı **85** kalır; A'nın tahsis edilmemiş **18 paketi fiziksel stok değildir**. Üçüncü kademe veya son tüketici verisi uydurulmaz.

`/izlenebilirlik`: lotu ve ileri/geri yönü seçin. Alış, girdiler, üretim/parçalama/rework, satış/sevkiyat ve kayıtlı sonraki alıcılar gerçek FK ile izlenir. `/geri-cagirma`: kaynak lotu ve zorunlu nedeni seçin → salt-okunur **Etkiyi önizle** → lot kodunu doğrulayarak kesin onay. Etki değişmişse409 ile yeniden inceleme gerekir; önizleme blok koymaz. Türevler atomik bloke olur; yeni satış reddedilir. Blok kaldırma/QA serbest bırakma bu sürümde yoktur.

## ML, uyarı ve belge

`/yapay-zeka`: üretim/EKP ve kuzu/beş parça modelleri. İşlemle karşılaştırmak için tahmin **işlem başlamadan** kayıtlı operasyon UUID'sine bağlanmalıdır. İki model toplam **6.000 SYNTHETIC kayıtla (3.000/model)**, **0 gerçek tarihsel veriyle** eğitildi; bazı v1/v2 metriklerinde gerileme vardır ([karşılaştırma](../ml/EVALUATION_REPORT.md)); gerçek işletme doğruluğu kanıtlanmadı. Kesin maliyet/lot ilişkileri ML'den gelmez.

`/uyarilar`: güncel SKT/blokaj, açık ürün-birim eşiğine göre düşük stok ve uygun kayıtlı tahmin–gerçekleşme sapmaları. Filtre, detay ve kaynak bağlantısı kullanın. Demo eşikleri işletme standardı değildir. Uyarılar stok/recall/maliyet yazmaz; kalıcı bildirim geçmişi yoktur.

`/belgeler` veya satış detayında **Belge taslağı oluştur**: proforma/satış özeti seçin; başlık, not, satıcı beyanı, belge tarihi, vade/teslim açıklamasını düzenleyin. Kesin müşteri, satış tarihi, fiyat, miktar ve lot kilitlidir. İade/iptal ve orijinal/düzeltilmiş tutarlar ayrı gösterilir. **PDF önizleme** sunucunun gerçek Türkçe A4 belgesini açar; **PDF indir** aynı belgeyi kaydeder; **Yazdır** ayrı tarayıcı işlevidir. Taslak React state'inde geçicidir; sunucuda saklanmaz. Resmî e-Fatura/e-Arşiv, KDV hesabı veya ödeme talebi iddiası yoktur. Demo belgesinde **Kurgusal demo** işaretini seçin.

## Sık karşılaşılan durumlar

| Durum | Yapılacak |
| --- | --- |
| 401 / bağlantı yetkilendirilemedi | API ve server-side proxy anahtarlarının aynı özel env'den geldiğini kontrol edin; anahtarı browser'a koymayın |
| 403 yerel erişim | Web'i tam `http://127.0.0.1:5173` ile açın; yabancı Host/Origin/origin'siz POST reddedilir. CLI'yi release_env ile çalıştırın |
| 503 / ready başarısız | MySQL health, migration ve model kurulumunu kontrol edin; kullanıcı verisini resetlemeyin |
| LOT_BLOCKED / LOT_EXPIRED | Başka uygun lot seçin; kalite/recall kaydını inceleyin, otomatik blok kaldırmayın |
| Yetersiz stok / birim uyuşmazlığı | Kaynak konum ve kullanılabilir miktarı yenileyin; kg/paket/adet eşleşmesini kontrol edin |
| Belirsiz timeout / kayıp cevap | Aynı kalıcı key/body ile devam edin; kör yeni satış/iptal oluşturmayın |
| PDF 409 kaynak değişti | Önizlemeyi yenileyin; iade/iptal/sevkiyat değişikliğini inceleyip tekrar indirin |
| Model 503 | Geçerli checksum'lu iki JSON modeli kurun; uydurma tahmin gösterilmez |

Gerçek kullanıcı oturumu/RBAC/TLS olmadığı için internete açık üretim dağıtımı yapılmamalıdır. Final test ve teslim sınırları [FINAL_RELEASE_READINESS.md](FINAL_RELEASE_READINESS.md) içindedir.
