# Linux / Zorin OS Android kurulumu

Android Studio’da bu deponun **android/** klasörünü açın. Backend’i ayrı terminalde mevcut backend/README.md ile çalıştırın; bu proje backend kaynaklarını değiştirmez. Yarışma PDF’sinin Kotlin+SQLite gereksinimi Room üzerinden karşılanır.

## Sabit araçlar

| Araç | Sürüm |
| --- | --- |
| JDK | Temurin 17.0.17+10 (JDK, yalnız JRE değil); JVM hedefi 17 |
| Gradle Wrapper | 8.10.2, resmî dağıtım SHA-256 kontrolü |
| Android Gradle Plugin | 8.7.3 |
| Kotlin / Compose compiler | 2.0.21 / Kotlin Compose plugin |
| KSP | 2.0.21-1.0.28 |
| compileSdk / targetSdk / minSdk | 35 / 35 / 26 |
| Build Tools | 35.0.0 |
| Compose BOM / Material 3 | 2024.12.01 / BOM sürümü |
| Room | 2.7.0 |
| Retrofit / OkHttp | 2.11.0 / 4.12.0 |

Android Studio’nun Gradle JDK ayarını JDK 17 kurulumunuza yönlendirin. Linux paket yöneticisindeki `openjdk-17-jdk` bir seçenek; yalnız `java -version` çıktısı yeterli değildir, `javac -version` da çalışmalıdır. Gradle sürümü wrapper’dan gelir, global Gradle kurulumu gerekmez.

Android Studio → SDK Manager: Android SDK Platform 35, Build Tools 35.0.0, Platform Tools ve Android Emulator kurun. Device Manager’dan test için telefon oluşturun. Bu raporda başarıyla kullanılan imaj **API 28 AOSP x86_64**; API 35 Google APIs imajında bu hızlandırmasız bulutta instrumentation başlangıcı başarısız oldu. API 35 için donanım hızlandırmalı ayrıca doğrulama gerekir. Linux’ta KVM destekli emülatör için BIOS sanallaştırması ve kullanıcının KVM erişimi gerekir; gerçek USB cihazı da kullanılabilir. Bu adımlar Zorin/Linux kurulum yönergesidir; bulut doğrulamasının gerçek sonuçları [VALIDATION.md](VALIDATION.md) içindedir.

```bash
cd android
# Kendi JDK ve SDK konumlarınızı kullanın.
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME="$HOME/Android/Sdk"
./gradlew test
./gradlew lintDebug
./gradlew assembleDebug
./gradlew assembleDebugAndroidTest
```

Room şeması app/schemas altında sürümlenir; destructive fallback yoktur. Gelecek DB sürümlerinde açık Room Migration ve mevcut draft/outbox anahtarlarını koruyan migration testleri zorunludur. İlk sürümün başlangıç şeması v1’dir; v0’dan veri aktarımı iddiası yoktur.

Salt okunur home bulunan bulut ortamında GRADLE_USER_HOME ve ANDROID_USER_HOME için yazılabilir /tmp dizinleri kullanılabilir. Proxy gerekiyorsa ayarı kendi kullanıcı Gradle yapılandırmanıza koyun; proxy/SDK/JDK mutlak yollarını veya credentials’ı projeye commit etmeyin. Kurumsal CA varsa JDK’nın güvenilir CA deposunu doğru ayarlayın; TLS doğrulamasını kapatmayın. Robolectric test JVM’i Gradle’ın proxy/truststore sistem ayarlarını devralır; test cache’i build/test-home altındadır.

## Backend bağlantısı

Backend aynı bilgisayarda 127.0.0.1:8000 dinleyebilir. Emülatör uygulamasındaki bağlantı ekranına `http://10.0.2.2:8000/` girin. 10.0.2.2 Android emülatörünün host köprüsüdür; cihazın localhost’u bilgisayar değildir.

Uygulamada dişli simgesi → sunucu ve kullanıcı tarafından verilen API anahtarı → güvenli kaydet. Anahtar APK/BuildConfig içinde bulunmaz; Android Keystore AES-GCM ile şifrelenip uygulamanın özel alanında saklanır. Mevcut sunucu için alanı boş bırakmak kayıtlı anahtarı korur. Başka sunucu seçerken yeni anahtar gerekir. Bir outbox kaydı farklı sunucuya otomatik gönderilmez.

USB fiziksel debug cihazında `adb reverse tcp:8000 tcp:8000` kullanıp uygulamaya `http://127.0.0.1:8000/` girilebilir. Debug HTTP izinleri yalnız localhost, 127.0.0.1, 10.0.2.2 içindir. Release manifest cleartext’i kapatır; uygulama ayarı da HTTPS zorunlu tutar. Release için gerçek backend kullanıcı/rol yetkilendirmesi ve TLS kurulumu ayrıca gereklidir; X-API-Key üretim oturumu değildir. Hiçbir HTTP header/body logger eklenmedi; redirect’ler kapalıdır.

## APK ve cihaz testleri

```bash
# android/ içinde
adb devices
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.byteme.avatar/.MainActivity
./gradlew connectedDebugAndroidTest -Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true
```

APK tam göreli yolu: `android/app/build/outputs/apk/debug/app-debug.apk`. APK ve build raporları Git’e eklenmez. Debug APK geliştirme anahtarıyla imzalanır; release signing secret’ı projede yoktur.

`DeviceTests` gerçek SQLite dosyasını kapatıp tekrar açmayı ve Android Keystore’u test eder. `BackendDemoTest` gerçek FastAPI/MySQL ve özel fixture gerektirir; `OfflineDeviceTest` önceden doldurulmuş demo kataloğunu kullanır. Ön koşulları yoksa ilgili test **skip** olur ve bu senaryolar başarılı sayılamaz. Robolectric/MockWebServer testleri gerçek sunucu veya cihaz testlerinin yerine geçmez.

## Güvenli, izole kuzu demosu

Yalnız ayrı test/demo MySQL veritabanını kullanın; gerçek işletme verisini bu komutlarla hazırlamayın. Mevcut backend migration’ını uygulayıp API’yi başlatın. Repo kökünde, backend ile aynı AVATAR_API_KEY process ortamında:

```bash
export PYTHONPATH=backend
# Anahtarınızı terminale/loga yazdırmayın. Komuta argüman olarak vermeyin.
backend/.venv/bin/python android/tools/prepare_demo.py \
  --fixture /tmp/avatar-device-fixture.json
```

Bu komut mevcut app.demo_cutting’i kullanır. Quantity kesiminin butu önceki demo tarafından 5 kg’a düşürülmüştür; **value kesiminin satılmamış 6 kg but lotu** mobil test için seçilir. Parça ağırlıkları/referans fiyatlar ve fire açıklaması kurgusal etiketlidir. Ön koşul sağlanmıyorsa stokları geri yazmaz; yeni izole demo DB gerekir.

Özel fixture anahtar içerir, yalnız mode 0600 /tmp dosyasında tutulur. APK’ye veya Gradle instrumentation argümanına eklenmez. Debug uygulaması kurulduktan sonra cihazın uygulamaya özel alanına standart girdiden aktarın:

```bash
adb shell run-as com.byteme.avatar mkdir -p files
adb shell run-as com.byteme.avatar sh -c "'cat > files/demo-fixture.json'" \
  < /tmp/avatar-device-fixture.json
cd android
./gradlew connectedDebugAndroidTest -Pandroid.injected.androidTest.leaveApksInstalledAfterRun=true
# Test sonrası özel fixture’ı kaldırın; loglamayın/pull etmeyin.
adb shell run-as com.byteme.avatar rm -f files/demo-fixture.json
```

Manuel demo: stoktan value but lotunu seçin → 1 kg, fiyat, müşteri → özeti inceleyip kesin satış onayı → gerçek satış/satır/hareket kimlikleri → sunucudan yenilenmiş 5 kg bakiye. Bekleyen işlemde timeout olursa aynı anahtarla tekrar deneyin; yeni taslak açarak belirsiz işlemi çoğaltmayın. Kaynak lotu mevcut backend recall API’siyle bloke ettikten sonra eski önbellekten gelen yeni isteğin LOT_BLOCKED ile başarısız kalması gerekir.

Kesin satıştan önce/sonra uygulamayı normal kapatıp açmak kayıtları korur. Uninstall, `pm clear` ve veritabanını silmek kayıtları korumaz; belirsiz outbox işlemleri varken bunları uygulamayın. Backup/cihaz aktarımı kapalıdır. Senkronizasyon uygulama açıkken ağ dönüşünde veya kullanıcı yenilemesinde yapılır; kapalı uygulamada arka plan işleyicisi varmış gibi sunulmaz.
