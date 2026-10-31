# Görev 29A — Web QR ile APK indirme kabulü

31 Ekim 2026 · Branch: [`feature/web-apk-qr-download`](https://github.com/EminAly1/byteme-avatar-2026/tree/feature/web-apk-qr-download).
Taban: `57623df32ac73df0745df59e3864844baab61f04` (`origin/main`); PR #46'nın normal merge commit'i Git geçmişinde doğrulandı.
Main'e merge yapılmaz. [PR açma / karşılaştırma](https://github.com/EminAly1/byteme-avatar-2026/compare/main...feature/web-apk-qr-download).

## Tamamlanan akış

- Web'in üstündeki **Android Uygulamasını İndir** düğmesi mevcut modal/focus altyapısını açar. AVATAR Preview adı ve mevcut ikon kullanılır.
- Aktif paylaşımın gerçek özel IPv4 URL'si `qrcode` ile tarayıcıda SVG QR'a çevrilir. Harici QR servisine istek yoktur. Standart telefon kamerası/tarayıcısı yeterlidir.
- Sürüm, MiB ve kesin bayt boyutu, SHA256, geri sayım, kopyalama ve aynı güvenilir Wi-Fi açıklaması vardır. URL salt okunurdur; bilgisayarda yanlışlıkla tek indirmeyi tüketen indirme/prefetch linki oluşturulmaz.
- İlk kapalı durum: **“APK paylaşımı henüz başlatılmadı.”** QR yoktur; güncel araç komutu ve güvenli adımlar gösterilir. Yalnız loopback'te başlatılan paylaşımda da QR yoktur.
- Kullanım/kapanış, süre sonu ve erişim hatasında QR ve URL gizlenir. Durum açık popup'ta saniyede bir kontrol edilir; son kullanma zamanı ayrıca yerel sayaçla izlenir. Kontrol düğmesi yeni token üretmez; yeni paylaşımı operatör başlatır.
- Escape, Tab/Shift+Tab sınırları, kapatma sonrası düğmeye odak dönüşü ve kopyalama çalışır. Dar ekranda içerik popup içinde dikey kayar.

## Küçük yerel köprü ve güvenlik sınırı

`tools/share_apk.py` yalnız doğrulanmış güncel Preview APK'yı RAM'den sunar. Rastgele 32 bayt token, tek GET, varsayılan 180 saniye / en çok 600 saniye ve LAN için `--allow-lan` açık onayı korunur. HEAD indirmeyi tüketmez. Yanlış hash/eski build/paket ve genel/0.0.0.0 bind reddedilir.

`tools/apk_status_bridge.py`, repo **dışında** 0700 sahipli dizinde 0600 Unix soketi açar. Durum/token dosyası yazılmaz; soket kapanışta kaldırılır. Durum servisi için TCP/LAN portu yoktur. LAN APK listener'ında `/status`, API veya dizin sunumu yoktur. Varsayılan soket `/tmp/.avatar-apk-share-<UID>/status.sock`; TMPDIR ve belgelenmiş özel soket yolu desteklenir.

Vite `frontend/server/apk-share.ts` yalnız bu sahipliği/izinleri doğrulanmış soketten, sınırlı boyut ve timeout ile okur. Web'deki `/api/apk-share` yalnız tam yol/GET, `127.0.0.1:5173` Host, aynı Origin/site ve özel istek başlığıyla çalışır. Yabancı Origin/Host/site, yazma ve sorgu parametreleri reddedilir. Socket RPC'sine tarayıcı başlığı/API anahtarı aktarılmaz. Yanıtta `no-store`, `no-referrer`, `nosniff` vardır; URL ayrıca RFC1918 literal IPv4, token yolu, süre ve APK metadata açısından doğrulanır. Vite soket/gizli dosya yollarını sunmaz.

Token terminale/erişim loguna yazılmaz, kaynak/Git/localStorage/sessionStorage'a konmaz. Popup kapatılınca sorgu önbelleği hemen kaldırılır. Kopyalama yalnız açık kullanıcı eylemidir. Host web/API/MySQL portları loopback'te kaldı; FastAPI, MySQL, ML, Android, satış/recall iş mantığına dokunulmadı. APK paket/imzası değişmedi. Bu görev cihaz eşleştirmesi yapmaz.

Linux host Node kurulumu doğrudan çalışır. İsteğe bağlı `docker-compose.apk-qr.yml` yalnız özel soket dizinini salt okunur bağlar; port açmaz. Aynı UID gerekir. [Kurulum komutları](INDIRME.md#web-panelinden-qr-ile-indirme).

## Gerçek APK kanıtı

| Alan | Doğrulanan değer |
| --- | --- |
| Dosya | `android/app/build/outputs/apk/preview/app-preview.apk` — Git'e eklenmedi |
| Paket / sürüm | `com.byteme.avatar.preview` / `0.1.0-preview.2` |
| Kesin boyut | 17.178.340 bayt |
| SHA256 | `1d9a671d80d55c9ad6bcb4fe0ce5712463a256dc781756d7bed22092a68320e1` |
| Aktarım | Gerçek paylaşım aracının bu buluttaki özel IPv4 arabirimine bind edilmesi; aynı host'tan HTTP indirme |
| QR kanıtı | Chromium'daki gerçek SVG rasterize edildi, bağımsız `jsQR` decoder sonucu aktif servis URL'siyle birebir eşleşti |

Gerçek token veya onu kodlayan QR **Git kanıtına konmadı**. Aktif ekran görüntülerinde hem QR hem URL alanı maskelidir. QR doğrulaması screenshot üzerinden iddia edilmez; otomatik decoder karşılaştırmasıyla yapılır.

## Çalıştırılan kontroller

| Kontrol | Sonuç ve kapsam |
| --- | --- |
| `backend/.venv/bin/python -m pytest tests/test_share_apk.py tests/test_apk_status_bridge.py -q` | **6/6 geçti**; mevcut 4 test korundu. Güncel APK/hash, tek dosya, HEAD/GET, TTL/idle kapanış, açık LAN onayı; IPC izin/yol/başlık/metot, durum ve temizlik. Kontrollü APK fixture'ları; DB kullanılmadı. Mevcut Starlette/anyio deprecation uyarısı var. |
| `npm --prefix frontend test` | **117/117 geçti**, 15 dosya. Önceki 107 test korundu; 10 yeni unit/component testi. |
| İlgili 3 dosyanın son hedefli koşusu | **13/13 geçti**; durum doğrulama, Host/Origin/site/GET guard, IPC izin/metadata/boyut sınırı, kapalı/aktif/hata/süre sonu/kopyalama/önbellek davranışı. |
| `npm --prefix frontend run typecheck` ve `npm --prefix frontend run build` | **Geçti**; QR popup'ı ayrı lazy chunk. |
| `npm --prefix frontend run test:e2e:apk-qr` | **1/1 gerçek Chromium senaryosu geçti**: 390/768/1440 px kapalı/aktif popup, taşma, Escape/odak/Tab, gerçek clipboard, QR decode, metadata/URL, gerçek APK hash, tek GET, ikinci indirme reddi, gerçek yeni paylaşım, TTL sonrası QR/bağlantı kaldırma. |
| Gerçek HTTP sınır kontrolleri | Eksik özel başlık, yabancı Host/Origin ve same-site istekleri **403**. Vite soket dosya yolu **403**. APK listener'ında `/`, `/.env`, `/status`, `/v1/products`, `/api/apk-share`, yanlış token ve README yolu **404**; APK dışında içerik sunulmadı. |
| Git öncesi kontrol | `git diff --cached --check` ve Gitleaks staged-diff taraması geçti; gizli bilgi bulunmadı. APK, özel env/soket ve raw log stage edilmedi. |
| Docker sınırı | Compose override `config --quiet` geçti. Gerçek CLI soketine `node:24-alpine`, UID1000, **read-only mount / network none** ile bağlantı kuruldu; aktif durum ve gerçek hash doğrulandı. CLI token loglamadı; kapatınca soket kaldırıldı. |

Chromium senaryosunda yalnız iş kaydı/katalog istekleri boş kontrollü fixture ile karşılanır; **APK, durum köprüsü, QR ve indirme mock değildir**. Satış/stok/iş verisine yazma ve veri silme yapılmaz. Ağ paylaşımı için testte açık IPv4 ve doğrulanmış hash gerekir; otomatik başka arayüz seçilmez. Yeniden çalıştırma (web normal localhost sunucusunda açık, başka aktif paylaşım yokken):

```bash
AVATAR_APK_TEST_BIND=WIFI_IPV4_ADRESINIZ \
AVATAR_APK_TEST_SHA256=DOGRULANMIS_64_HANELI_SHA256 \
  npm --prefix frontend run test:e2e:apk-qr
```

## Kısa ekran kanıtı

| Genişlik | Paylaşım kapalı | Aktif, QR ve URL maskeli |
| --- | --- | --- |
| 390 px | [Ekran](evidence/apk-qr-download/inactive-390.png) | [Ekran](evidence/apk-qr-download/active-masked-390.png) |
| 768 px | [Ekran](evidence/apk-qr-download/inactive-768.png) | [Ekran](evidence/apk-qr-download/active-masked-768.png) |
| 1440 px | [Ekran](evidence/apk-qr-download/inactive-1440.png) | [Ekran](evidence/apk-qr-download/active-masked-1440.png) |

## Doğrulanmamış sınırlar

- Fiziksel Android telefon ve gerçek Wi-Fi kamera → tarayıcı indirmesi **test edilmedi**. Bulutun özel IPv4 testi fiziksel Wi-Fi kabulü değildir; gerçek operatör telefonun ulaşabildiği Wi-Fi adresini seçmelidir.
- Cihazda APK kurulumu/imza uyumu bu görevin testi değildir. Eski uygulama kaldırılmadı, Room/outbox/Keystore'a müdahale edilmedi.
- Tam Compose imaj rebuild/uygulama kabulü tekrar yapılmadı; yalnız konfigürasyon ve gerçek salt okunur Unix soketi mount testi yapıldı. UID uyuşmazlığında izin gevşetilmez.
- macOS/Windows/Docker Desktop IPC doğrulanmadı. Saf statik `dist`/`vite preview` yerel köprüyü sunmaz; mevcut Linux Vite demo akışı gerekir. Servis/izin sorunu durumunda indirme QR'ı kapalı kalır.
- İnternet yayını, genel APK deposu, otomatik sunucu eşleştirme ve backend LAN bind bu kapsamda yoktur.
