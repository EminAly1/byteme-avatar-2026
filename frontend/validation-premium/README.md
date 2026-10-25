# Görev 11 doğrulama kanıtları

- `before/`: ana sürüm `63a9c86` üzerinde, uygulama düzenlemesinden önce çekilen 14 PNG.
- `after/`: aynı görsel veritabanındaki aynı kayıtların 14 PNG karşılığı ve ek mobil satış formu.
- `regression/`: ayrı kabul veritabanındaki mevcut E2E senaryolarının JSON ve PNG çıktıları.
- `logs/`: gerçek komut çıktıları. Zamanlama/yerel UUID farklılıkları beklenir.
- `history.json`, `scope.json`, `performance.json`, `contrast.json`, `visual-checks.json`, `fixture-verification.json`: kontrol yöntemleri ve sonuçları.

Karşılaştırma görüntüleri için `avatar_ux_visual_test`, son işlem testleri için `avatar_ux_acceptance_test` kullanıldı. Önceki `avatar_ux_core_test` kayıtları silinmedi. Parolalar ve API anahtarı repo dışında tutuldu. Anahtar Node/Vite sürecinde kalır.

Yeniden üretim: README'deki backend/MySQL migration ve demo adımlarını yalnız izole bir `*_test` veritabanında çalıştırın. Görsel referans dosyasındaki rotalar bu koşunun gerçek demo UUID'leridir; yeni fixture'da bunları demo API yanıtlarına göre güncelleyin. Vite'ı mevcut güvenli proxy ayarlarıyla bu backend'e yönlendirin, sonra repo kökünden:

```sh
node frontend/validation-premium/capture.mjs
```

Bu betik tarayıcıdaki API yazmalarını engeller, beş viewport'ta taşma/dokunma alanlarını ve 15 dolu ekran/formda axe'ı kontrol eder. `CHROMIUM_PATH` ve `AVATAR_UI_URL` isteğe bağlıdır. İşlem testleri için `AVATAR_E2E_DATABASE` ve sunucu tarafındaki anahtarı mevcut frontend/VALIDATION_V2.md yönergelerine göre yapılandırın:

```sh
cd frontend
AVATAR_E2E_ARTIFACT_DIR=validation-premium/regression npm run test:e2e
AVATAR_E2E_ARTIFACT_DIR=validation-premium/regression npm run test:e2e:missing-models
```

Eksik-model profili 5173 portunu kendisi kullanır; normal Vite süreci önceden kapatılmalıdır. Veritabanı parmak izleri SQLAlchemy metadata tablolarındaki satırların sıralanmış tam gösterimlerinden SHA-256 ile üretildi; görsel yakalamalar öncesi/sonrası eşitlik bu koşu için kaydedildi. Yeni fixture'ın hash'lerinin bu koşuyla aynı olması beklenmez.
