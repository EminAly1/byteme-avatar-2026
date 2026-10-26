# Jüri demosu — Görev 12

**25 Ekim kabulü, 26 Ekim 2026 sonlandırması; yerel KURGUSAL/SYNTHETIC veri.** Bu belge [release kanıtları](release-validation/) ile birlikte okunur. Gerçek işletme verisi, gerçek kişi iletişimi veya üretim sunucusu kullanılmaz. API anahtarı tarayıcıya, APK'ye, komut argümanına veya Git'e konmaz.

## Komutların doğrulama durumu

Aşağıdaki Compose, host Python/Vite, pytest, npm, eğitim, demo ve cihaz komutlarının akışları bu bulutta çalıştırıldı. Örnek `/tmp/byteme-demo.env` yerine koşuda `/tmp/avatar-release-final.env`, proje `avatar-release-v1`, MySQL portu 33326 kullanıldı. Yeni makineye özgü JDK/SDK kurulumu ve fiziksel cihaz kabulü **doğrulama bekliyor**. Standart DNS ile doğrudan image build bu bulutta başarısız; build proxy/CA override'ı başarılı. Android SDK geçici kurulumu ortam yenilenmesinde kayboldu; korunmuş cihaz kanıtları sonlandırmada yeniden koşulmuş sayılmaz. API 35 kabul durumu ayrı [readiness](RELEASE_READINESS.md) belgesindedir.

## 1. Özel ortam ve temiz servisler

[README](../README.md) kurulum komutlarını kullanın. Önkoşullar: Docker/Compose/BuildKit, host Python 3.12, backend/ML bağımlılıklarını içeren venv; web host testi için Node >=22.12 ve Chromium. İlk seed'de kullanılmamış, yalnız bu demoya ait `*_test` şeması gerekir. **Eski stok sıfırlanmaz.**

```bash
python tools/release_env.py init --env-file /tmp/byteme-demo.env \
  --project byteme-avatar-demo --mysql-port 3306
docker compose --env-file /tmp/byteme-demo.env config --quiet
# Normal DNS yolu; bu bulutta DNS nedeniyle tamamlanmadı:
docker compose --env-file /tmp/byteme-demo.env build
# Bulutta gerçekten başarılı alternatif (HTTPS_PROXY ve güvenilir CA gerekir):
export DOCKER_CONFIG=/tmp/byteme-docker
python tools/release_env.py build-proxy --output /tmp/byteme-build-network.json
docker compose --env-file /tmp/byteme-demo.env \
  -f docker-compose.yml -f /tmp/byteme-build-network.json build
docker compose --env-file /tmp/byteme-demo.env up --no-build -d --wait
python tools/verify_compose.py --env-file /tmp/byteme-demo.env \
  --output /tmp/byteme-compose-result.json
```

Normal build başarılıysa override adımlarını atlayın. Yalnız build host ağı kullanılır; üç uygulama servisi bridge/container namespace'inde ve host loopback publish ile çalışır. `/health`, `/health/ready`, iki model, key zorunluluğu ve proxy Host/Origin sınırı doğrulanır. Özel dosyalar O_EXCL/0600 ile repo dışında üretilir. Mevcut volume parola değişikliğini otomatik uygulamaz; yanlış projeyi kullanmayın.

Host demo araçları için (pip/npm cache salt-okunur home'dan ayrı tutulabilir):

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt -r ml/requirements.txt
npm --prefix frontend ci
```

Venv/npm kurulumu, sürümler ve container bağımlılık kurulumu bu ortamda denendi; yeni işletim sisteminin paket yöneticisi kurulumu bu belgenin kabulü değildir.

## 2. Tekrarlanabilir HTTP akışı

```bash
python tools/release_env.py run --env-file /tmp/byteme-demo.env -- \
  backend/.venv/bin/python tools/verify_release_demo.py --output /tmp/byteme-demo.json
```

Bu araç mevcut `app.demo_sales_shipments` (içinde `app.demo`), `app.demo_cutting`, `app.demo_recall` ve `ml.scripts.demo_api` komutlarını kullanır. Gerçek ilk başarılı satış cevabını bir loopback test proxy'sinde düşürür; sunucu commit'inden sonra aynı key/body ile aynı satışa döner. Bütün akışı iki kez çalıştırır ve 24 tablonun satır hash'lerini karşılaştırır. Yeni kesin satış/kesim/recall oluşursa kabul başarısızdır. Sunucu kayıtları silinmez.

| Sıra | Ekranda/kanıtta gösterilecek işlem | Kesin kabul |
| --- | --- | --- |
| 1 | Ürün, tedarikçi, depo kartları | Ayrı UUID/FK; fixture tedarikçi ve iletişimleri kurgusal |
| 2 | Çok satırlı alış ve lot | ET-2026-001 ve diğer girdiler; SKT UI roundtrip ayrı E2E kanıtı |
| 3 | URT-2026-045 dış üretim, SUC-2026-045 | 970+48+58+467,50 = 1.543,50 EUR; 85 paket; gösterim 18,16, maliyet dengesi tam |
| 4 | Kuzu parçalama | İki ayrı kuzu/yöntem; 25 kg → 22 kg + açıklamalı 3 kg; her biri 287,50 EUR; 351 çelişkisi açıklanır |
| 5 | Gerçek Kotlin/Room satışı | Aşağıdaki cihaz adımı: value but 6→5 kg, aynı key/body replay; offline yalnız taslak |
| 6 | Market A/B/C satış/sevkiyatı | 30/25/30 paket, toplam85; satış+bağlı sevkiyat ikinci kez stok düşmez |
| 7 | ET ileri, SUC geri izleme | Kayıtlı input/output FK, tedarikçi/emir/market; bilinmeyen market kalanı null |
| 8 | Recall + stale Android satışı | ET türevleri ve ayrı kuzu kaynağı bloke; 409 LOT_BLOCKED, NEEDS_ACTION; yeni stok/satış yok |
| 9 | Üretim/EKP AI | Model sürümü, SYNTHETIC, tahmin; kesin EKP ayrı |
| 10 | Kuzu AI | Beş parça tahmini; fiziksel sınır; kesin lotlar ayrı |
| 11 | Gerçekleşme/sapma | 85 paket ve22 kg gerçek kapanış; backend karşılaştırması, ML defter değiştirmez |

HTTP aracı 6–11'i otomatik hazırlar; video sunumu için bu tablo sırası kullanılabilir. Kotlin adımı aynı şemadaki **ayrı value but** üzerinde gerçekleşir; ET/market veya ML kayıtlarını değiştirmez. Bütün PK kimliklerini ayrıca etiketlemek için `python tools/release_env.py run --env-file /tmp/byteme-demo.env -- backend/.venv/bin/python tools/export_demo_manifest.py --output /tmp/byteme-demo-records.json` çalıştırıldı; salt-okunur manifest üretir. Kayıt kimlikleri [demo.json](release-validation/demo.json), cihaz sonrası aynı kayıtların tekrar kanıtı [demo-after-android.json](release-validation/demo-after-android.json) içindedir.

Salt-okunur kârlılık `/api/v1/sales/{id}/profitability` ile web origin'inden görülebilir. Market A: gelir750, maliyet544,764706, brüt kâr205,235294 EUR, gösterim205,24 ve marj%27,364706. Satış anındaki tüketim maliyeti kullanılır; yuvarlanmış18,16 ile yeniden hesap yapılmaz. Özel React kâr paneli henüz yoktur.

## 3. Kotlin cihaz adımı ve ikinci çalıştırma

JDK17, Android SDK35/build-tools35, wrapper8.10.2 ve bağımsız AOSP x86_64 API28 test emülatörü kullanıldı. [Android kurulum](../android/ANDROID_SETUP.md). Aşağıdaki komutlar gerçek API28 koşusunun eşdeğeridir; emülatör seri numarasını doğrulayın.

```bash
./android/gradlew -p android test lintDebug assembleDebug assembleDebugAndroidTest
python tools/release_env.py run --env-file /tmp/byteme-demo.env -- \
  backend/.venv/bin/python android/tools/prepare_demo.py --fixture /tmp/byteme-device.json
adb -s emulator-5554 install -r android/app/build/outputs/apk/debug/app-debug.apk
adb -s emulator-5554 shell run-as com.byteme.avatar mkdir -p files
adb -s emulator-5554 shell run-as com.byteme.avatar sh -c "'cat > files/demo-fixture.json'" < /tmp/byteme-device.json
ANDROID_SERIAL=emulator-5554 ./android/gradlew -p android connectedDebugAndroidTest \
  -Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true
```

Fixture'ın `10.0.2.2:8000` adresi Android emülatörünün host loopback eşidir; host API portu internete açılmaz. Fixture yalnız testte okunur, test bitince kaldırılır. BuildConfig'e anahtar yazılmaz. API28 testleri gerçek satışı yapar, kayıp cevap tekrarını doğrular, sonra kaynağı recall eder. **Bu test yeni satış için ikinci kez çalıştırılmaz:** mevcut stok5/bloke olduğu için `prepare_demo.py` güvenli biçimde reddeder. Yeniden kabul gerekiyorsa yeni izole şema kullanın; eski DB/Room kayıtlarını koruyun.

Mevcut kayıtları tekrar doğrulamak için önce özgün server idempotency kaydını kontrol eden araç kullanılabilir:

```bash
python tools/release_env.py run --env-file /tmp/byteme-demo.env -- \
  backend/.venv/bin/python tools/verify_android_state.py --serial emulator-5554 \
  --fixture /tmp/byteme-device.json --output /tmp/byteme-android-state.json
adb -s emulator-5554 shell run-as com.byteme.avatar rm -f files/demo-fixture.json
python tools/release_env.py run --env-file /tmp/byteme-demo.env -- \
  backend/.venv/bin/python tools/verify_release_demo.py --output /tmp/byteme-after-android.json
```

İlk komut Room dosyasını özel geçici dizine alır, aynı key/body'nin server'da zaten var olduğunu doğrulamadan POST yapmaz; aynı satış döner. Force-stop/reopen sonrası outbox key/body/state ve backend hash'leri değişmemelidir. CONFIRMED + NEEDS_ACTION/LOT_BLOCKED ve ayrı offline taslak korunur. Test aracı uygulamayı force-stop durumunda bırakır; sunumda yeniden açın. Fiziksel telefon kabulü bu kanıt değildir.

Bu bulutta ADB host home'u salt-okunur olduğundan yalnız `/tmp` SDK kopyasında `python android/tools/cloud_adb.py --sdk /tmp/avatar-release-android/sdk` aracı denendi. Unmodified ADB özel tool container'ında varsayılan yazılabilir home ile, host loopback5037 üzerinde çalıştı. Bu, üç uygulama servisinin runtime ağını değiştirmez. Genel kalıcı SDK'ya bu workaround uygulanmaz. KVM yoktu; yazılım emülasyonu kullanıldı.

## 4. Ayrı test DB'leri

Demo şemasında veri silen pytest çalıştırmayın. Bu koşuda aynı **yeni** MySQL instance içinde core, migration, web, API28 ve API35 şemaları ayrıdır. Aşağıdaki komut avatar kullanıcısına yalnız ayrı test şemalarını verir; parola argümanda/logda gösterilmez:

```bash
docker compose --env-file /tmp/byteme-demo.env exec -T mysql sh -c \
 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot' <<'SQL'
CREATE DATABASE IF NOT EXISTS avatar_release_core_test;
CREATE DATABASE IF NOT EXISTS avatar_migration_test;
GRANT ALL ON avatar_release_core_test.* TO 'avatar'@'%';
GRANT ALL ON avatar_migration_test.* TO 'avatar'@'%';
SQL
python tools/release_env.py run --env-file /tmp/byteme-demo.env \
  --database avatar_release_core_test --tests -- \
  backend/.venv/bin/python -m pytest tests ml/tests -q
```

`--tests` orijinal demo şemasını reddeder. `avatar_migration_test` migration testlerinin downgrade/upgrade hedefidir; yalnız test instance'ında oluşturulur. Kullanıcı veritabanı/volume'u bu komutlara hedef verilmez.

Web kabulü için **ayrı** `avatar_release_web_test` şeması/grant ve aynı özel env'in MYSQL_DATABASE alanı bu şemaya ayarlanmış dış kopyası kullanıldı. Aynı Compose projesindeki backend/frontend bu env ile yeniden başlatıldı; migration ve `verify_release_demo.py` seed'i yapıldı. Çalışan web origin'i http://127.0.0.1:5173, tek worker ve gerçek Chromium gerekir:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test
python tools/release_env.py run --env-file /tmp/avatar-release-web.env -- \
  npm --prefix frontend run test:e2e
```

Bu son komutun `/tmp/avatar-release-web.env` dosyası yalnız mevcut bulut koşusunda hazırlandı; başka makinede yukarıdaki ayrı şema/env hazırlığı **önkoşuldur**. E2E kendi kurgusal işlem kayıtlarını oluşturur; demo DB yerine web DB kullanılır. Seed olmadan canonical ET/SUC kontrolleri geçmez.

Eksik-model503 profili de gerçekten denendi: Compose **frontend ve backend birlikte** durduruldu (5173 backend namespace'inde publish edilir); aynı web DB ile host backend127.0.0.1:8002, `AVATAR_ML_MODEL_DIR` var olmayan ayrı dizin; host Vite5173 `AVATAR_API_PROXY_TARGET=http://127.0.0.1:8002`. Bu profil açıkken `npm --prefix frontend run test:e2e:missing-models` geçti. Bu iki ortam değişkeni yalnız ilgili process'e verilir. Profil sonrası sahip olunan host process'leri kapatılır ve normal Compose env'iyle `up --no-build -d --wait` + smoke tekrar edilir. Model dosyaları silinmez. Otomatik process yönetimi içermeyen bu profil önkoşulları atlanırsa test geçerli değildir.

## 5. ML tekrar üretimi

Aşağıdaki komut iki kez, ayrı dış dizinlerde, aynı timestamp ile çalıştırıldı. Çalışan modellerin üstüne yazılmaz.

```bash
python tools/release_env.py run --env-file /tmp/byteme-demo.env -- \
  backend/.venv/bin/python -m ml.training.train --data /tmp/byteme-repro/data \
  --models /tmp/byteme-repro/models --evaluation /tmp/byteme-repro/evaluation \
  --trained-at 2026-10-25T00:00:00+00:00
```

Seed202609; CSV hash'leri, iki retrain'in byte eşitliği ve kayıtlı model ağırlıkları doğrulandı. Metadata timestamp'i farklıysa bütün JSON dosyası eşitliği beklenmez. 600+600 sentetik kayıt, 360/120/120 split; gerçek tarihsel satır0. MAE/RMSE sentetik test başarımıdır.

## 6. Video ve teslim hazırlığı

1. [Release readiness](RELEASE_READINESS.md) açık kapsamı ve API35 sonucunu okuyun; resmî teslim NO-GO maddelerini kapatmadan tüm gereksinimler tamamlandı demeyin.
2. Üç servis smoke'unu yeniden çalıştırın; özel env/fixture ve terminal geçmişini kayda almayın.
3. Web'i http://127.0.0.1:5173 açın; API28 emülatörde mevcut onaylı satış/LOT_BLOCKED kanıtını gösterin. Yeni işlem için mevcut lotu resetlemeyin.
4. Yukarıdaki 11 adımı ekranda anlatın; iki ML ekranında SYNTHETIC ve gerçek/sapma ayrımını gösterin. Gerekiyorsa yeni izole demo şemasıyla kayıt baştan yapılır.
5. Video çekimi/yükleme, public erişim denetimi ve yarışma gönderimi **yapılmadı; doğrulama bekliyor**. Mevcut checklist yarışma e-postasından en fazla15 dakika video ve kayıtlı üyenin aynı e-postayı yanıtlamasını aktarır; bunlar PDF'den doğrulanmış koşullar olarak sunulmaz.
6. Kaynak/kurulum/test kanıtlarını seçilen commit ile paketleyin; ayrı review/merge, sürüm etiketi ve insan teslim/alındı doğrulaması gerekir. Son tarih kullanıcı talimatıyla 1 Kasım2026 23:59 Europe/Istanbul.

Güvenli durdurma `docker compose --env-file /tmp/byteme-demo.env stop`; yeniden başlatma `up --no-build -d --wait`. **`down -v`, prune, eski DB drop/reset ve yeni idempotency key ile kör tekrar kullanılmaz.**
