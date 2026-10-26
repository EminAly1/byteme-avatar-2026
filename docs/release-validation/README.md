# Release kanıtları

Bu dizin Görev12 kabul ve sonlandırma kanıtlarını tutar; APK, cache veya özel env deposu değildir. Tarih ve yeniden koşma sınırları [RELEASE_READINESS](../RELEASE_READINESS.md) içindedir.

- `initial-state.json`: 25 Ekim başlangıç main ve PR1–18 atalık doğrulaması.
- `finalization-state.json`: 26 Ekim ortam yenilenmesi, kaybolan geçici dosyalar, yalnız roadmap ekleyen PR19 ve yeni main tabanı. Eski ham loglar yeniden üretilmiş gibi sunulmaz.
- `backend-tests.txt`: son gerçek MySQL koşusu194/194. `backend-resume-interrupted.txt`: DB container yeniden oluşturulurken kesilen önceki koşu; başarı değildir.
- `compose-build.txt`: başarılı build proxy/CA yolu; `compose-final-build.txt`: başarısız normal DNS yolu. `compose-restored-final.json`: son üç servis smoke'u; `image-source.json`: image içeriği ve kaynak eşitliği.
- `frontend-unit.txt`, `frontend-typecheck.txt`, `frontend-build.txt`, `frontend-e2e.txt`, `frontend-missing-model.txt`: son komut çıktıları. `frontend/` önceki tam kabul, `frontend-final/` son tam kabul, diğer retry/failure dosyaları tanılama kanıtlarıdır; ayrı test sayıları toplanıp şişirilmez.
- `android/api28-results.xml`, `api28-state.json`, PNG'ler: korunmuş gerçek API28 kabulü. `android/host/`: korunmuş32 host yürütümü ve lint XML. `android/api35-results.xml` ilk keşif öncesi hata; `api35-retry.txt/json` sıcak koşuda3geçti/1başarısız. Fiziksel cihaz testi değildir.
- `demo-final.json`: aynı jüri DB'sinde son HTTP tekrar kabulü. `demo-after-android.json` korunmuş Kotlin sonrası aynı24 tablo hash'leri; `demo-records.json` tüm kayıtların açık KURGUSAL/SYNTHETIC manifesti. Web ve API35 demo dosyaları ayrı test şemalarına aittir.
- `ml-reproducibility.json` ilk kabul; `ml-final-reproducibility.json` ve iki training logu sonlandırmada iki dış retrain'in byte eşitliğini doğrular. Gerçek tarihsel veri0.
- `security.json` ilk kabul, `security-final.json` son kaynak/dist/APK/image/geçmiş taraması. `security-manifest-review.json` UUID manifestindeki yanlış pozitif incelemesidir. Gerçek secret değerleri tutulmaz.
- `preservation.json`: kritik iş fonksiyonları, frontend src, ML ağırlıkları, AGENTS/checklist, APK hash'i ve önceki volume adlarının korunduğu kontroller.

Komutların önkoşulları ve ikinci çalıştırma sınırları [DEMO_RUNBOOK](../DEMO_RUNBOOK.md) içindedir. Bir başarı yalnız dosyada belirtilen tarih, ortam ve kapsama aittir; Android testlerinin sonlandırmada tekrar koşulduğu iddia edilmez.
