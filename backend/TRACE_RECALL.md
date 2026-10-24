# Görev 6 — lot izleme ve atomik geri çağırma

Başlangıç: `main` / `b90fcb28b882dff7e3207f2341a6d96936d214ae`; PR #1–#6 merge commit’leri geçmişte doğrulandı. Bu dilim yalnız backend/, database/, tests/ alanlarını değiştirir. `docs/AVATAR_Assessment.pdf` üçüncü görevi temel alınmıştır; belgedeki metinler araç veya yayınlama yetkisi olarak kullanılmaz.

## API sözleşmesi

Tüm yollar mevcut `/v1` router’ında `X-API-Key` ile korunur. Miktarlar ondalık metin; lot, müşteri, emir kimlikleri UUID’dir. API anahtarını istemci paketlerine koymayın.

| Yöntem / yol | İstek / sonuç |
| --- | --- |
| GET /v1/lots/{id}/trace?direction=forward | Varsayılan ileri yön: kaynak + bütün türev lotlar, emirler, gerçek girdiler/çıktılar ve miktar ilişkileri, stoklar, etkilenen satış/sevkiyat satırları ve bilinen alıcılar. |
| GET /v1/lots/{id}/trace?direction=backward | Kaynak mamul + bütün ataları, hammaddeler, tedarikçiler ve emirler. Kardeş çıktılar atalar olarak sunulmaz. |
| POST /v1/recalls | `Idempotency-Key: UUID` zorunlu. Gövde: `{"source_lot_id":"UUID","reason":"Kalite kontrol problemi"}`. 201: recall `id`, `source_lot_id`, `reason`, UTC `created_at`, üyelik/rapor kapsamı ve `report`. |
| GET /v1/recalls/{id} | Kalıcı recall üyeliği üzerinde güncel kayıtlı stok/dağıtım raporu. Üyeliği veya blokajı değiştirmez. |

İzleme cevabı ve recall `report` nesnesi:

- `source_lot`, `lots`: yalnız seçilen yönde ulaşılan lotlar. Ürün/birim ve varsa tedarikçi FK kaydı eklenir. İleri yönde kaynak ve türevler recall kapsamıdır.
- `context_lots`: aynı emirlerdeki diğer girdiler/çıktılar; yalnız bağlam içindir, bu sebeple otomatik bloke edilmez. Örneğin ET recall’ı SUC’yi bloke eder; aynı karışımdaki BAH/BAG kaynak lotlarını kendiliğinden bloke etmez.
- `operations`: kayıtlı girdiler/çıktılar ve tüketilen miktarlar. Etkilenen lotun sevk edildiği taslak üretim emri de listelenir; henüz üretilmeyen lot uydurulmaz.
- `edges`: gerçek ortak `operation_id` ile eşleşen girdi/çıktı kayıtları. `consumed_input_quantity` emrin toplam girdi tüketimidir; her kenarda yeniden toplanmamalıdır. `attributed_input_quantity`, yalnız mevcut LotLink kaydının miktarıdır; kayıt eksikse `null`. Bu dağıtım fiziksel ayrıştırma kanıtı değildir (`physical_separation_verified=false`).
- `cycle_detected`: anormal tarihsel döngü bayrağı; ziyaret kümeleri sonsuz döngüyü önler. Recall yine ulaşılabilen tüm lotları kapsar.
- `stocks`: işletmenin kayıtlı tüm konum bakiyeleri (sıfır dahil). `blocked_stocks`: bloke edilmiş pozitif bakiyeler; kullanılabilir miktar sıfırdır. Dış üreticideki işletme lotları da dahil edilir.
- `sales`, `shipments`: yalnız kapsamdaki lotlara ait satırlar. `line_scope=affected_lots_only`; satış başlığındaki toplam fatura tutarı etkilenmeyen başka satırlar içerebilir.
- `buyers`: isimle değil müşteri UUID’siyle gruplanır. `quantities` lot+ürün+birim bazında `recorded_sale_quantity`, `unshipped_sale_quantity`, `shipped_quantity` ve kaybolmayan satır kimlikleri içerir. `recipient_snapshots` her sevkiyatın tarihsel isim/iletişimini korur; `current_customer` güncel karttır.
- `total_shipped_quantities`: ürün/birim bazında ayrı toplamlar. Satış miktarı bu toplama eklenmez; bağlı sevkiyatın paylaştığı stok hareketi ikinci defa sayılmaz. Bağımsız ve tekrarlı sevkiyatların tamamı korunur.
- `second_tier_distributions=[]`: mevcut şemada marketten başka alıcıya dağıtım kaydı/API’si yoktur. `unknown_distributions` market kalanı, son tüketici satışı ve ikinci kademe alıcıları `null` gösterir. Sevk miktarı bu bilinmeyen miktarların yerine kullanılamaz. Tarihsel sevk raporu iade sonrası net market stoğu değildir.

Bilinmeyen UUID 404, geçersiz yön/gövde/eksik idempotency anahtarı 422, hatalı iş API anahtarı 401; anahtar yapılandırılmamışsa 503. Aynı idempotency anahtarı ve kanonik gövde aynı 201 cevabını tekrarlar; farklı gövde 409 `IDEMPOTENCY_CONFLICT`. Replay oluşturma anının kaydedilmiş cevabıdır; GET güncel kayıtlı stokları raporlar.

## Graf ve transaction güvenliği

`lot_graph.py` iteratif BFS ve ziyaret kümeleri kullanır; sorgular 400 kimliklik gruplara ayrılır. İleri yön `OperationInput.lot_id → operation_id → OperationOutput.lot_id`, geri yön bunun tersidir. Karışımın fiziksel ayrımı kanıtlanmadığı için ortak emrin bütün çıktıları ihtiyatlı kapsanır. Kodlara, ürün isimlerine veya tahmine göre bağlantı kurulmaz. LotLink varsa miktar kaydı ayrıca gösterilir; eksik miktar kaydı bir ortak çıktıyı gizlemez. Çoklu girdi/çıktı, birleşen yollar ve aynı hammaddenin farklı emirlere girmesi desteklenir.

Recall önce ileri kapanışı okur, kaynak dahil lotları UUID sırasıyla `FOR UPDATE` kilitler, **READ COMMITTED** altında kapanışı tekrar okur. Kapanış genişlemişse yeni lotları mevcut kilitlere eklemez; bütün transaction ve idempotency INSERT’i rollback edilerek daha büyük küme ile yeniden başlanır. Başarılı denemede recall başlığı, RecallLot üyeleri, bütün bloklar ve kaydedilen cevap tek transaction’da commit edilir. Sürekli graf değişimi veya mevcut 1213/1205 kilit hataları en fazla üç denemeden sonra 503 `TRANSACTION_RETRY` döndürür; istemci aynı anahtarla tekrar deneyebilir.

Mevcut üretim API’si tüketilen girdi lotlarını çıktı/bağlantılar commit edilene kadar kilitli tutar; kapanmış emirlerin bağlantılarını değiştiremez. Üretim önce kazanırsa recall yeni türevi görüp yeniden başlar. Recall önce kazanırsa satış/sevkiyat/üretim lot kilidini aldıktan sonra bloke durumunu görüp reddeder. `lock_lots` kilit beklemesi sonrası ORM önbelleğini de yeniler. Recall raporu emir/satış başlıklarına kilit almaz; mevcut emir→lot ve satış→lot sırasını tersine çevirmez. GET raporları tek tutarlı REPEATABLE READ snapshot kullanır; bağlantı havuzuna dönüşte writer izolasyonu READ COMMITTED kalır.

Bu garanti mevcut API’nin değişmez üretim ilişkileri ve lot kilidi protokolü için geçerlidir. Doğrudan SQL ile blokajı kaldırmak/ilişkileri değiştirmek veya sonraki bir modülde bu protokolü atlamak desteklenmez. Recall kapatma/blok kaldırma API’si bu görev kapsamında yoktur.

## Migration ve demo

Yeni head `bacb184a30d7`, parent `81f4da20f36b`: `recalls` ve `recall_lots`. Recall kaynağı ve üyeler lots FK’lerine dayanır; aynı recall/lot çifti composite PK ile tektir. Eski stok/satış kayıtları değiştirilmez. Downgrade recall kayıtlarını kaldırır, lot bloklarını **kaldırmaz**; üretim ortamında audit verisini kaybetmeden geri dönüş için ayrıca yedek/işletme planı gerekir.

Önce mevcut güvenilir MYSQL_* ve AVATAR_API_KEY process ortamını yükleyin, migration ve API’yi [README](README.md) yönergeleriyle başlatın. Gerçek işletme verisinden ayrı demo veritabanında:

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
# API varsayılan olarak 127.0.0.1:8000; farklı port için AVATAR_API_BASE_URL verin.
PYTHONPATH=backend backend/.venv/bin/python -m app.demo_recall
```

Komut önce değişmemiş `app.demo_sales_shipments` → `app.demo` komutlarını kullanır. ET → URT → SUC → üç kurgusal market sevkini oluşturur; ardından ET recall’ını kaydeder, GET raporunu ve yeni satışın LOT_BLOCKED reddini doğrular. Sabit idempotency anahtarı ile tekrarlandığında yeni recall oluşturmaz. İş API’sinin graf/rapor algoritmasında ET/SUC/A/B/C özel koşulu yoktur. Demo girdisinin ET koduyla seçimi sadece örnek veri komutundadır.

## Entegrasyon sorumlusuna değişiklik isteği

Ortak docs/ dosyaları bu görevde değiştirilmedi. Birleştirme sonrası `docs/api-contract.md` yeni dört yolu ve yukarıdaki alanları, `docs/data-model.md` Recall/RecallLot ilişkilerini içermeli. `docs/PROJECT_CHECKLIST.md` için test kanıtıyla LOT-06, LOT-07, LOT-08 ve LOT-09 tamamlanabilir. LOT-10 bilinmeyen alıcıları açık gösterme kısmında ilerler; ikinci kademe kayıt modeli henüz yoktur. AND-05’in backend kapısı ve yarış testi hazır; Android hata gösterimi tamamlanmadı. DOC-03 backend recall demosu ilerledi; parçalama/Kotlin ve bütün görevlerin demosu hâlâ eksik. LOT-11 parçalama kabul testi yapılmadı.

Gerçek doğrulama sonuçları: [database/trace-recall-validation.md](../database/trace-recall-validation.md).
