# AVATAR — İndir ve kur

**ByteMe · 31 Ekim 2026 · Önizleme 0.1.0-preview.2.** Linux üzerinde yerel demo;
Android 8.0 / API26 ve üzeri için geliştirme imzalı APK.

## Android uygulamasını indir

**GitHub Release zorunlu değildir.** Güncel APK'yı bilgisayardan aynı güvenilir
Wi-Fi'daki telefona tek kullanımlık linkle aktarabilirsiniz. Şu anda herkese açık
APK URL'si yoktur. Web'deki **Android Uygulamasını İndir** düğmesi yalnız aktif
yerel paylaşım varsa gerçek QR gösterir.

### Tek kullanımlık yerel paylaşım

1. Repo kökünde `./android/gradlew -p android assemblePreview` çalıştırın.
   Görev29B bağlantı rehberini içeren Preview APK yeniden derlendi; güncel hash aşağıdadır.
2. `sha256sum android/app/build/outputs/apk/preview/app-preview.apk` ile hash'i
   kontrol edin. Bu ortamın kabul edilmiş hash'i aşağıdadır; farklı makine/debug
   imzası farklı hash üretir. APK'nin kaynağını ve build'ini doğrulayın.
3. Bilgisayarın Wi-Fi IPv4 adresi ve doğruladığınız hash ile başlatın:

```bash
# IP ve hash alanlarını kendi doğruladığınız değerlerle değiştirin.
python3 tools/share_apk.py --sha256 DOGRULANMIS_64_HANELI_SHA256 \
  --bind 192.168.1.10 --allow-lan --ttl 180
```

Araç APK boyutu/hash/sürüm bilgisini yazdırır; **token veya geçici URL terminale
ve erişim loguna yazılmaz**. Web panelinde **Android Uygulamasını İndir** düğmesini
açın. Telefonun standart kamerasıyla QR'ı okuyup tarayıcıda indirin; özel Android
QR tarayıcısı gerekmez. Alternatif olarak popup'tan bağlantıyı kopyalayın. Hash'i
eşleştirin ve APK'yı açın. Yalnız gerekli dosya uygulamasına kurulum izni verin.

- Link güçlü rastgele token içerir; bir GET indirmesi veya süre sonunda servis
  kendiliğinden kapanır. Başarısız/yarım indirmede aracı yeniden başlatın.
- `--allow-lan` olmadan varsayılan 127.0.0.1; belirsiz 0.0.0.0 veya genel IP kabul
  edilmez. Varsayılan adres yalnız bu bilgisayarda açılır; telefon için yukarıdaki
  açık Wi-Fi IP/--allow-lan komutunu kullanın. Araç yalnız bu APK'yı sunar; klasör listesi/proje/env/API/DB erişimi yoktur.
- HTTP şifrelenmez; yalnız güvenilir yerel Wi-Fi'da kısa aktarım içindir. URL'yi
  herkese açık paylaşmayın. API anahtarı/cihaz eşleştirme kodu bu linkte bulunmaz.
- Telefonla aynı Wi-Fi ve bilgisayarın seçilen portuna erişim gerekir. Ana uygulama
  portlarını LAN'a açmayın. Gerçek Wi-Fi/telefon aktarımı bu bulutta denenmedi;
  Görev29A kabulünde gerçek APK bu bulutun özel IPv4 arabiriminde aynı makineden
  indirildi ve web QR'ı çözüldü. Fiziksel Wi-Fi/telefon kabulü değildir.
- Araç seçilen APK hash'ini hem verdiğiniz hash'le hem güncel Preview build/metadata
  ile karşılaştırır; eski APK ve yanlış paket paylaşımını reddeder.

### Web panelinden QR ile indirme

**Linux / aynı kullanıcı:** `npm ci` sonrası web'i normal biçimde
`http://127.0.0.1:5173` üzerinde çalıştırın. Yukarıdaki paylaşım komutu otomatik
olarak `/tmp/.avatar-apk-share-<UID>/status.sock` oluşturur (TMPDIR ayarlanmışsa
o dizin kullanılır). Dizin 0700, soket 0600 ve aynı kullanıcıya ait olmalıdır.
Token yalnız çalışan süreçlerin/popup'ın belleğindedir; durum dosyası yazılmaz.
Web'in Node süreci bu Unix soketinden yalnız durumu okur. FastAPI'ye APK endpoint'i
eklenmedi. Web/API/MySQL'yi LAN'a açmayın.

- Özel yol gerekiyorsa araçta `--status-socket /OZEL_0700_DIZIN/status.sock`,
  web'in **sunucu** ortamında `AVATAR_APK_STATUS_SOCKET` aynı mutlak yol olsun.
  Yolu repo dışına koyun; `VITE_*` ortamına token/anahtar eklemeyin.
- Popup URL'yi `/api/apk-share` üzerinden aynı origin'den ve özel başlıkla okur;
  yabancı Host/Origin/site, sorgu parametresi ve yazma isteği reddedilir.
- Tek indirme, kapanış, hata veya süre sonu QR'ı kaldırır. **Paylaşımı kontrol et**
  yalnız durum okur; yeni paylaşım/token başlatmaz. Yenisi için terminal komutunu
  tekrar çalıştırın. Popup kapatıldığında QR/URL sorgu önbelleği silinir.
- `localhost` paylaşımı telefona erişilebilir sayılmaz; o durumda QR gösterilmez.
- Saf statik `dist`/`vite preview` dağıtımı IPC köprüsü içermez; bu yerel akış
  mevcut Vite demo sunucusunu gerektirir. Socket desteklenmeyen ortamda kapalı kalır.

**Docker Compose (isteğe bağlı):** Önce host'ta paylaşım komutunu başlatın. Host
kullanıcısının UID'si frontend imajındaki `node` kullanıcısıyla aynı olmalı (1000).
Uyuşmazsa izinleri gevşetmeyin; aynı kullanıcıyla host Node yolunu kullanın.
Özel env dosyasını aşağıdaki örnekte kendi mevcut dosyanızla değiştirin:

```bash
export AVATAR_APK_STATUS_DIR="/tmp/.avatar-apk-share-$(id -u)"
docker compose --env-file /tmp/avatar-delivery.env \
  -f docker-compose.yml -f docker-compose.apk-qr.yml config --quiet
docker compose --env-file /tmp/avatar-delivery.env \
  -f docker-compose.yml -f docker-compose.apk-qr.yml up -d --build frontend
```

Override yalnız özel dizini salt okunur bağlar; ek TCP portu, anahtar veya
veritabanı paylaşmaz. Host'ta sonraki paylaşım aynı dizinde yeni soket oluşturur.
Mevcut volume'u silmeyin. Docker Desktop/Windows/macOS soket aktarımı bu görevde
doğrulanmadı; hata durumunda QR üretilmez.

[Wi-Fi bağlantı kodu için güvenlik planı](SECURE_DEVICE_PAIRING_PLAN.md) ayrı
gelecek görevdir; bu indirme aracı otomatik sunucu eşleştirmesi yapmaz.

## 1. Android uygulaması

**Bu teslim oturumunda Release yayımlanamadı:** GitHub Releases API `Forbidden`
döndürdü. Henüz doğrulanmış herkese açık APK indirme URL'si yoktur; yukarıdaki yerel aktarım Release gerektirmez.
Kaynak kod: [güncel `main`](https://github.com/EminAly1/byteme-avatar-2026/tree/main). Paketleme [PR #43](https://github.com/EminAly1/byteme-avatar-2026/pull/43) ile birleşti; herkese açık APK Release/asset hâlâ yok.

Hazır dosyalar bu çalışma ortamında korunur:

- APK: `/workspace/artifacts/AVATAR-Preview-connection-guide.apk`
- Hash dosyası: `/workspace/artifacts/AVATAR-Preview-connection-guide.apk.sha256`
- SHA256: `0affc5b5ba72650ec33fe96fa23c5fdec87cc83134cb8f9c1b75065a911cfd3e`
- Paket: `com.byteme.avatar.preview`; görünen ad **AVATAR Preview**.
- Sürüm: **0.1.0-preview.2**, versionCode **1**, minSdk **26**, targetSdk **35**.
- Sertifika SHA256: `b9fbe028ac6c63fc1f873fbe446a0693be3f6260d57807f89d75ad6ef0418f9f`.

Eski `com.byteme.avatar` farklı sertifikalıdır. Yeni Preview ayrı paket ve ayrı
veri alanı kullanır. **Eski uygulamayı kaldırmayın, verisini temizlemeyin.**
Eski Room taslakları/outbox ve bağlantı bilgileri Preview'a otomatik aktarılmaz.
İki uygulamayı aynı anda aynı bekleyen satışı göndermek için kullanmayın.
Yeni paketin kimliği APK'den doğrulandı; telefonda yan yana kurulum henüz denenmedi.

Ekip APK'yı güvenilir kanaldan telefona aktardıktan sonra dosyayı açıp yalnız o
dosya uygulaması için kurulum izni verebilir. Kurulum sonrasında izni kapatın.
ADB ile **yeni paket** kurulumu:

```bash
sha256sum AVATAR-Preview-v0.1.0-preview.2.apk
adb devices
adb install AVATAR-Preview-v0.1.0-preview.2.apk
adb shell am start -n com.byteme.avatar.preview/com.byteme.avatar.MainActivity
```

Sertifika/kurulu paket hatasında durun; uninstall, `pm clear` veya zorla üzerine
yazma uygulamayın. Bu APK debug imzalıdır; mağaza/üretim dağıtımı değildir.

## 2. Bilgisayarda web, FastAPI ve MySQL

Linux üzerinde Docker Engine + Compose/BuildKit ve Python3.12 gerekir. Kaynak
derlemesi için Node ≥22.12; Android derlemesi için JDK17/SDK35 kullanılır.
Depo kökünde, kullanılmayan bir proje adı/port ve yeni `*_test` şemasıyla:

```bash
python3 tools/release_env.py init --env-file /tmp/avatar-delivery.env \
  --project avatar-delivery-demo --mysql-port 33330
docker compose --env-file /tmp/avatar-delivery.env config --quiet
docker compose --env-file /tmp/avatar-delivery.env build
docker compose --env-file /tmp/avatar-delivery.env up --no-build -d --wait
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/ready
```

Web panelini **http://127.0.0.1:5173** adresinde açın. Backend migration'ları
başlangıçta uygular; MySQL portu yalnız loopback'e açılır. Mevcut volume veya
işletme kayıtlarını silmeyin. Özel env dosyası repo dışında 0600 izniyle oluşur;
anahtar/parolaları Git'e, videoya veya APK'ye koymayın. Güvenli durdurma:
`docker compose --env-file /tmp/avatar-delivery.env stop`.

[Tam kurulum ve ağ kısıtı çözümü](../README.md#güvenli-temiz-compose-kurulumu)
· [Demo veri hazırlığı](DEMO_RUNBOOK.md).

## 3. Telefonu aynı sisteme bağla

Android Ana Sayfa → **Bağlantı yardımı**, USB/kablosuz ADB adımlarını gösterir.
İlk açılışta **Sunucuya bağlan** ile ayarları kaydedin, ardından **Bağlantıyı kontrol et**
ile gerçek API isteğinin sonucunu görün: Bağlı değil / Bağlanıyor / Bağlandı / Hata.
QR ile APK indirmek otomatik sunucu eşleştirmesi değildir.
[Görev29B APK ve kabul sonucu](ANDROID_CONNECTION_GUIDE_ACCEPTANCE.md).

Bilgisayarda backend çalışırken yetkilendirilmiş USB hata ayıklama bağlantısı kurun:

```bash
adb reverse tcp:8000 tcp:8000
```

Preview **Ayarlar** ekranında sunucu `http://127.0.0.1:8000/` ve bilgisayardaki
aynı özel env dosyasının `AVATAR_API_KEY` değerini güvenli biçimde girin.
Anahtar komut argümanına/loga yazılmaz; cihazda Keystore ile korunur. Yeni Preview
boş veriyle başlar; katalog sunucudan alınır. Fiziksel cihaz bağlantısı bu oturumda
test edilmedi. LAN IP'sine HTTP açmak için ağ politikasını gevşetmeyin.

USB yerine Android11+ cihazlarda aynı güvenilir ağda
[resmî kablosuz ADB eşleştirme yönergesi](https://developer.android.com/tools/adb#wireless-android11-command-line)
kullanılabilir. Eşleştirme sonrasında yine `adb reverse` gerekir; backend'i
internete açmayın. Kablosuz bağlantı bu teslimde denenmedi.

## 4. Kullanım ve sorun giderme

- Beş sekme: **Ana Sayfa, Stok, Satış, Bekleyenler, Uyarılar**. Ayarlar üstte;
  **Belgeler** Ana Sayfa/satış geçmişindedir.
- Satış yalnız backend onayıyla kesindir; offline kayıt taslaktır. Belirsiz yanıt
  için aynı kalıcı key/body ile devam edin; yeni satış oluşturmayın.
- Kritik uyarı alınamazsa hata gösterilir; uyarı hatası satış senkronizasyonunu durdurmaz.
- PDF için onaylı satış → proforma/satış özeti → önizleme → kaydet/paylaş.
  Satış fiyatı/miktarı/lotu değiştirilemez; proforma resmî e-Fatura değildir.
  Native PDF, dosya seçici ve paylaşma cihaz kabulü bekler.
- `401`: aynı sunucu/anahtarı kontrol edin. `503`: MySQL, migration ve modelleri
  kontrol edin. `LOT_BLOCKED/LOT_EXPIRED`: uygun başka lot seçin; blok kaldırmayın.
- PDF `409`: kaynak değişmiştir; belgeyi yeniden yükleyip inceleyin.
- Build ağ hatasında [README](../README.md) içindeki doğrulanmış proxy/CA yolunu
  kullanın; TLS doğrulamasını kapatmayın.

[Kullanım kılavuzu](USER_GUIDE.md) · [Güncel kabul ve sınırlar](FINAL_RELEASE_READINESS.md)
· [14:30 video planı](FINAL_DEMO_SCRIPT.md).

## 5. Ekip için manuel Release yükleme

1. Paketleme [PR #43](https://github.com/EminAly1/byteme-avatar-2026/pull/43) `main` dalına alındı. APK kod commit'i ve hash/sertifikasını doğrulayın;
   güncel APK için [Görev29B kabulündeki](ANDROID_CONNECTION_GUIDE_ACCEPTANCE.md)
   Android kaynaklarını ve yeni SHA256'yı kullanın. Eski APK hash'ini kullanmayın.
2. Yetkili ekip hesabıyla GitHub deposu → **Releases → Draft a new release**.
   `v0.1.0-preview.2` etiketinin boşta olduğunu tekrar kontrol edin; varsa mevcut
   etiketi oynatmadan yeni etiket seçin. İncelenmiş kaynak commit'ini hedefleyin.
3. Başlık **AVATAR Preview 0.1.0-preview.2**, tür **Pre-release**. APK ve `.sha256`
   dosyasını asset olarak ekleyin; kaynak Git ağacına eklemeyin.
4. Debug imza, ayrı paket/taşınmayan eski veriler, cihaz kabulü eksikleri ve
   SYNTHETIC ML sınırlarını açıklamaya ekleyin. Yayımlayın.
5. Oturumsuz gerçek APK indirmesini açın; indirilen dosyanın SHA256'sını eşleştirin.
   **Ancak bu doğrulamadan sonra** oluşan gerçek Release/asset URL'sini buraya,
   README'ye ve e-posta taslağına ekleyin.

Bu oturumda Release/tag oluşturulmadı; video çekilmedi/yüklenmedi, e-posta
gönderilmedi. Son insan adımları: cihaz provası, gerçek indirme
alanı, ≤15 dakika video ve **1 Kasım 2026 23:59 Türkiye saati** öncesi gönderim/alındı.
