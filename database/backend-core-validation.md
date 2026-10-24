# Backend A doğrulama raporu

Tarih: 22 Ekim 2026. Branch: feature/backend-core. Foundation base: e91fa9ba424df976a6c7f61e1c5e5222f1630493. Son alınan origin/main: f263f1913f7787e1998d2cf9810fb47ef393dc62; foundation henüz main’de olmadığı için PR foundation’a bağımlıdır. Bu görevde kaynak değişiklikleri yalnızca backend/, database/, tests/ içindedir.

## Gerçek sonuçlar

| Kontrol | Sonuç |
| --- | --- |
| Python / MySQL | Python 3.12.14; gerçek MySQL 8.0.46 / InnoDB, READ COMMITTED |
| Varsayılan pytest | **16 passed, 22 skipped, 1 warning**; opt-in MySQL testleri çalışmış sayılmaz |
| İzole MySQL ile tam pytest | **38 passed, 1 warning**, başarısız/atlanmış test yok |
| pip check | No broken requirements found |
| İlk migration | eeea4b5dd1a8; gerçek MySQL’de upgrade head ve alembic check başarılı |
| Migration geri alma | Ayrı avatar_migration_test DB’sinde upgrade → metadata check → downgrade base → tekrar upgrade başarılı |
| Canlı Uvicorn | `/health`, `/health/ready`, `/openapi.json`, korumalı `/v1/lots`, `/v1/stocks`, `/v1/stock-movements` HTTP 200; OpenAPI’de kapanış yolu doğrulandı |
| Gerçek HTTP demo | Ürün/tedarikçi/depo/alış, dış üretim sevki ve kapanışı API üzerinden çalıştı; demo tekrarları aynı operasyon/lot cevabını verdi |

Test komutu (MYSQL_* process ortamında, test veritabanları önceden oluşturulmuşken):

```bash
MYSQL_DATABASE=avatar_core_test AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests -q
```

Test DB’leri üretim verisinden ayrıdır; *_test adı zorunlu, veri silme açıkça belgelidir. Tek uyarı upstream Starlette/anyio BlockingPortal deprecation uyarısıdır.

## Doğrulanan davranışlar

- ET-2026-001 100 kg / 970 EUR + baharat 2 kg / 48 EUR + bağırsak 5 kg / 58 EUR; URT-2026-045; hizmet 467,50 EUR; SUC-2026-045 85 paket.
- Malzeme 1.076,00 EUR, hizmet 467,50 EUR, toplam **1.543,50 EUR**, birim gerçek EKP (6 hane) **18,158824**, gösterim **18,16**. Toplam gösterim birim fiyatıyla yeniden hesaplanmaz.
- Kaynak 3 lot ve çıktı lotu arasında FK tabanlı miktarlı bağlantılar; ham lotların depo ve üretici stoğu 0, mamul stoğu 85. Defter hareketlerinin konum bazlı toplamı bakiyelerle eşleşir.
- Kısmi lotların üç ayrı emirde tüketiminde maliyet artığı korunur; birden çok çıktıda dağıtılan maliyet ve her girdinin bağlantı miktarları toplamı korunur.
- Negatif stok DB CHECK ile reddedilir. İki eşzamanlı 80 kg sevk isteği 100 kg stoktan yalnızca bir kez başarılı olur.
- Aynı idempotency anahtarlı eşzamanlı kapanış yalnızca bir çıktı üretir; farklı gövde 409. Timestamp atlanmış alış replay’i aynı kaydı döndürür.
- Gerçek lot satır kilidi ikinci bağlantının sevkini bekletir. Kapanış emir kilidini beklerken commit edilen sevki READ COMMITTED altında doğru görür.
- Tüketim yazıldıktan sonra geçersiz iade konumunda tüm maliyet/stok/hareket/idempotency yazıları rollback edilir; düzeltilmiş istek aynı anahtarla çalışır.
- Blokeli/tarihi geçmiş lot sevki reddedilir; sevk miktarları tüketim/iade ile tam açıklanır; ağırlık dengesi ve miktar hassasiyeti doğrulanır.
- API anahtarı olmadan iş API’si açılmaz; liste sayfalama ve doğrulama hataları kontrol edildi.

Migration downgrade sırasında MySQL’in FK için kullandığı indeksi erken silme problemi testte bulundu ve tabloyla birlikte indeks kaldırılacak şekilde düzeltildi. Son tam koşuda tüm testler geçti.

## Sınırlar / entegrasyon görevleri

- Parçalama, satış/sevkiyat, recall API’si/raporu ve ML uygulanmadı; bunların uçtan uca testleri yapılmadı. Şema çoktan çoğa lot grafı, bloke lot, generic operasyon türleri ve ters hareket referansını destekler.
- Deadlock/lock timeout için 3 denemeli retry kodu vardır; testler gerçek lock ve stok yarışını doğrular, zorlanmış bir gerçek deadlock senaryosu bu çalışmada çalıştırılmadı.
- Rol bazlı oturum yetkilendirmesi yoktur; API anahtarı yerel güvenilir prototip korumasıdır. Üretim güvenliği tamamlanmış sayılmaz.
- Ortak Compose/dokümanlar diğer ajan alanıdır ve değiştirilmedi. Compose’a AVATAR_API_KEY runtime binding eklenmesi ve ortak API/data-model/README durumlarının güncellenmesi entegrasyon sorumlusunun görevidir. Anahtarsız servis sağlık kontrolünü geçebilir ama iş endpoint’leri 503 kalır.
- Backend Docker image build ve tam Compose stack bu aşamada yeniden doğrulanmadı; önceki container DNS/proxy engeli kayıtlıdır. Çalışan yol MySQL container + host venv/Uvicorn’dur.
- Frontend/Android dosyaları değiştirilmedi ve bu görevde bu bileşenlerin testleri çalıştırılmadı.
