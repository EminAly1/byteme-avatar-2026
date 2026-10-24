# Görev 7 — gerçek MySQL ve HTTP doğrulama

Kanıt tarihi: 24 Ekim 2026. Başlangıç `main` SHA `e8c690d` (PR #1–#8 merge commit’leri doğrulandı). Branch: feature/lamb-cutting. Çalışma başlangıcında Git ağacı temizdi; önceki dosyalar ve bütün 100 test dosyaları/assertion’ları korundu. Değişiklik alanı yalnız backend/, database/, tests/.

## Ortam ve sonuç

Bu görev için yeni Docker mysql:8.0 konteyneri ve yeni volume oluşturuldu; SQL’den doğrulanan sürüm **8.0.46**, InnoDB. Python 3.12 / mevcut backend/.venv. İşletme verisi kullanılmadı. Rastgele credentials yalnız /tmp içinde mode 0600 ortam dosyalarında; Git’te veya test raporunda yoktur.

- Başlangıç: avatar_cutting_test üzerinde **100 passed**, 0 failed/0 skipped, 13.27 s.
- Son sürüm: temiz avatar_cutting_final_test ve ayrı avatar_migration_test üzerinde **131 passed**, 0 failed/0 skipped, 20.62 s.
- Eski 100 + yeni **31** (30 cutting kabul testi, 1 cutting migration testi). Toplam **115 gerçek MySQL testi + 16 DB gerektirmeyen test**. Gerçek MySQL yarışları SQLite ile ikame edilmedi.
- Tek uyarı mevcut Starlette/AnyIO BlockingPortal deprecation uyarısıdır.
- Geliştirme sırasında reçete listeleme serializer imzası hatası bulundu ve özel cursor/list endpoint’i ile düzeltildi (ilk koşu 22 passed / 1 failed). Ürün species alanı sonradan eklenince henüz commit edilmemiş migration’ın önceki taslağı geçici migration şemasında uygulanmış kaldı; dört migration testi bu eski şemada başarısız oldu. Yalnız izole avatar_migration_test sıfırlandı, son zincir temiz şemalarda baştan uygulandı; yukarıdaki 131 testlik son koşuda hata yoktur. Önceki yayımlanmış migration dosyaları değiştirilmedi.

Tekrarlama (MYSQL_* ve AVATAR_API_KEY güvenli process ortamından):

```bash
MYSQL_DATABASE=avatar_cutting_final_test AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 \
  backend/.venv/bin/python -m pytest tests -q
```

Bu testler açıkça seçilen *_test şemasını temizler; avatar_migration_test ayrıca upgrade/downgrade için yönetici tarafından hazırlanmalıdır. Demo avatar_cutting_final_demo_test’te tutuldu; test temizliği demo verisini silmedi. Geliştirme aşamasının önceki geçici test/demo şemaları da yalnız *_test adlarıyla aynı izole instance’ta bırakıldı.

## Kabul kanıtları

- Tür=Kuzu, alış tarihi/tedarikçi/lot/konum; 25 kg × 11.50 EUR/kg = 287.50 EUR. Birim fiyatla çelişen 351 EUR toplam 422 ile reddedilir. Birim fiyat verilmediğinde doğrulanmış toplam bedel korunur, sessiz dönüşüm yapılmaz.
- Dış üreticiye sevk olmadan depo içi kesim; 5 ayrı parça lotu, giriş/çıkış hareketleri, OperationInput/Output ve LotLink FK’leri.
- 25 = 22 + açıkça girilmiş 3 kg fire; eksik/boş açıklama, yanlış miktar veya stok kaydı atlayan byproduct farkı reddedilir. Diğer açıklanmış kayıp ve stoklanan açıklamalı yan ürün senaryosu da test edildi (22+2+1=25).
- quantity ve value formülleri bağımsız oran hesabıyla doğrulandı (en fazla 1 mikro EUR dağıtım farkı); bütün parça maliyetleri toplamı tam 287.500000. Pozitif referans zorunluluğu, sıfır/negatif/eksik anahtar ve yanlış ürün/birim reddi test edildi.
- Yeni reçete sürümü veya önceki sürümün kullanılabilirliğinin değiştirilmesi geçmiş snapshot’ı/maliyeti değiştirmez. Tür uyuşmazlığı reddedilir. Pasif reçete ile taslak/kapanış yoktur; cursor listeleri ve endpoint tür sınırı testlidir.
- Kısmi iki kesimde kaynak lotun toplam maliyeti tam korunur, aynı fiili dağıtım aynı ürün maliyetlerini verir. Tam tüketilmiş kuzu ikinci kez kesilemez; iki eşzamanlı kesimden yalnız biri kapanır.
- Aynı Idempotency-Key ile kapanış tekrarında yeni lot/hareket oluşmaz; değişen gövde 409. Kapanmış kesime yeni anahtarla ikinci kapanış reddedilir.
- Girdi tüketildikten sonra çıktı hareketine **enjekte edilmiş** hata, maliyet/bakiye/lot/girdi/çıktı/bağlantı/fark/idempotency kayıtlarını tamamen rollback eder; aynı anahtar düzeltildikten sonra çalışır. Bu, gerçek ağ/DB kesintisi testi değildir.
- Parça lotundan 1 kg kesin satış ve replay: merkezî stoktan tam bir kez düşüm ve tek StockMovement FK’si.
- Kaynak kuzudan bütün parça lotlarına ileri izleme, parçadan kaynağa geri izleme; kuzu recall’ında bütün parçaların bloklanması, alıcı kaydı ve yeni parça satışının reddi.
- Blokeli, tarihi geçmiş, karantinadaki veya reçeteye uymayan kaynakların reddi.
- Recall/kesim yarışında **her iki kazanan sırası**: gerçek MySQL lot kilidi, SQL event ve Future timeout ile bekleme doğrulandı. Recall önce commit ederse kesim LOT_BLOCKED; kesim önce commit ederse recall eski kapanışı bırakıp tüm transaction’ı yeniden başlatır (iki deneme), kaynak+5 yeni lotu bloke eder.
- Migration: v3 → v4 → v3 → v4; önceki lot maliyeti, bakiye, hareket, operasyon ve recall üyeliği/blokları korunur. Önceki tam base/head metadata check/downgrade ve satış/recall migration testleri de son 131 koşusunda geçti. Yeni head fa8791f3cf0e, parent bacb184a30d7.

## Gerçek HTTP demo

Son şemalı Uvicorn 127.0.0.1:8008 ve ayrı avatar_cutting_final_demo_test kullanıldı. `/health` ve `/health/ready` HTTP 200. `alembic upgrade head` ve `alembic check` başarılı, metadata farkı yok.

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8008 PYTHONPATH=backend \
  backend/.venv/bin/python -m app.demo_cutting
```

İki kez çalıştırıldı; JSON çıktıları birebir eşit ve veritabanı sayıları doğrulandı: **2 Receipt, 2 RecipeVersion, 2 Operation, 2 OperationInput, 10 OperationOutput, 12 Lot, 10 LotLink, 2 OperationDifference, 1 Sale, 15 StockMovement**. İki yöntem için iki ayrı 25 kg lot kullanılır; aynı kuzu iki kez tüketilmez. Her lot 287.50 EUR’dur; her kesim 22 kg parça + 3 kg açıkça kurgusal normal fire üretir.

Aşağıdaki tek tek ağırlıklar ve referanslar **PDF’den alınmamıştır**; demo girdisidir. PDF yalnız 22 kg toplamı verir. Gösterilen mikro dağıtım artıklarının sırası kalıcı ürün UUID+lot koduna dayanır.

| Kurgusal parça | kg | Referans EUR/kg | quantity maliyet EUR | value maliyet EUR |
| --- | ---: | ---: | ---: | ---: |
| But | 6 | 20.00 | 78.409091 | 95.303867 |
| Omuz | 4 | 14.00 | 52.272728 | 44.475138 |
| Sırt | 4 | 24.00 | 52.272727 | 76.243094 |
| Kaburga | 5 | 12.00 | 65.340909 | 47.651934 |
| Kıyma | 3 | 10.00 | 39.204545 | 23.825967 |
| **Toplam** | **22** | | **287.500000** | **287.500000** |

But lotundan 1.000000 kg test satıldı, bakiye 5.000000 kg kaldı. İleri trace 6 lot (kaynak+5 parça), geri trace 2 lot (parça+kaynak). İkinci demo yeni alış/kesim/lot/satış/hareket oluşturmadı; maliyetler değişmedi. HTTP demosu recall oluşturmaz; recall entegrasyonu ve iki yarış sırası yukarıdaki gerçek MySQL kabul testlerinde doğrulandı.

## Kalan kapsam ve belge devri

Android/Kotlin satışı, web kesim ekranı, ML, tam Docker Compose kurulumu ve üretim ölçeğinde yük testi bu görevde geliştirilmedi/test edilmedi. Gerçek işletme alış belgesi veya 3 kg fark sınıfı için insan onayı yoktur; demo sınıfı gerçek işletmeye uygulanmış karar değildir. Kesime ek hizmet maliyeti, blok kaldırma ve başka yan ürün maliyet politikaları bu sürümde yoktur.

[Backend sözleşmesi/politika v1](../backend/CUTTING.md). Ortak docs/PROJECT_CHECKLIST.md değiştirilmedi. KUZ-01/02/03/04 için backend tamamlanma kanıtı; LOT-11 için gerçek cutting ileri/geri/recall kanıtı hazır. KUZ-05’in Kotlin kısmı, KUZ-06’nın işletme onayı, WEB-05/DOC-03/TST-05’in kalan modülleri tamamlanmış gösterilmemeli. Entegrasyon sorumlusu ortak ER/API/varsayım belgelerini yeni sözleşmeyle güncellemelidir.
