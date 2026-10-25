# ByteMe Operations — React Frontend v2

Gerçek FastAPI/MySQL kayıtlarıyla çalışan Türkçe yönetim paneli. Görev 10, `origin/main` **99356d4** (PR #14) üzerinden `feature/frontend-v2-integration` dalında geliştirildi. Yalnız `frontend/` değişir; backend, ML, Android, database ve ortak checklist korunur.

## Ekranlar

| URL | Gerçek işlem kapsamı |
| --- | --- |
| `/` | Kayıtlı ürün, stoklu lot/konum, alış, açık dış üretim, satış ve sevkiyat sayıları; doğru modüle açılan son işlemler |
| `/urunler`, `/is-ortaklari`, `/depolar` | Ürün/birim, supplier/producer/customer rolleri ve konum yönetimi |
| `/alislar`, `/stoklar`, `/uretim`, `/uretim/:id` | Çok satırlı alış, bakiyeler/hareketler, ayrı emir–sevk–fiilî kapanış ve backend EKP |
| `/parcalama`, `/parcalama/:id` | Reçete/sürüm/kullanılabilirlik, quantity/value, kaynak lot, fiilî parça/yan ürün, açıklamalı fire/diğer kayıp, onaylı kapanış ve gerçek maliyet/lot bağlantıları |
| `/satislar`, `/satislar/:id` | Çok satırlı lotlu kesin satış, müşteri/lot filtreleri, tutar ve kesin stok hareketi UUID |
| `/sevkiyatlar` | Bağımsız çıkış veya sevk edilmemiş **tam satış satırlarının** teslim belgesi; detay drawer'ı. `?sale=UUID` ve `?shipment=UUID` desteklenir |
| `/izlenebilirlik` | `?lot=UUID&direction=forward\|backward`; gerçek FK/operasyon kenarları, erişilebilir sıralı akış, lot drawer'ı, bakiye ve bilinen alıcılar |
| `/geri-cagirma`, `/geri-cagirma/:id` | Mevcut izleme kapsamı ön görünümü, açık kritik onay, kesin recall üyeliği/bloklar, market bazlı miktar ve tarihsel iletişim |
| `/yapay-zeka` | İki model formu, sentetik uyarı/metrikler, UUID/zaman/sürüm ve backend tahmin–gerçek–sapma; `?prediction=UUID` |

Eski `/plan/parcalama`, `/plan/satis`, `/plan/izleme`, `/plan/recall`, `/plan/ai` yolları yeni modüllere yönlenir. Geliştirme aşamasında ekranları kaldırıldı. Sayılar/alarmlar kayıtlı veriden gelir; sahte grafik/aktivite yoktur.

## Yerel çalıştırma

Node **24.19.0**, npm **11.9.0** ile test edildi; paket engine şartı Node >=22.12.0. Önce backend/README.md ve ml/INTEGRATION.md akışıyla ayrı MySQL 8 şemasını/migration'ı ve FastAPI'yi başlatın. ML modelleri backend'in okuyabildiği konumda olmalıdır; model yoksa UI gerçek 503 hatasını gösterir.

Backend ve Vite Node süreçlerine **aynı AVATAR_API_KEY** güvenli process ortamından verilmelidir. Anahtarı komuta düz metin olarak, kaynak koduna, `.env` commit'ine veya `VITE_*` değişkenine koymayın. Frontend .env dosyasından anahtar otomatik okunmaz.

```bash
cd frontend
npm ci
npm run dev
```

Tek origin: **http://127.0.0.1:5173**. `localhost` başka origin'dir. Varsayılan API hedefi `http://127.0.0.1:8000`; yalnız Node process'inde `AVATAR_API_PROXY_TARGET=http://127.0.0.1:<port>` ile değişebilir. Anahtar tarayıcıya aktarılmaz; Node proxy ekler. Host/Origin/uzak hedef/originsiz POST engelleri ve gizli dosya erişim sınırı korundu. `0.0.0.0` başlatma reddedilir; backend CORS/auth gevşetilmedi. `npm run preview` API proxy'si sağlamaz.

Bu dağıtım yerel prototip içindir. Üretim kullanıcı oturumu, roller, TLS ve yetkili dağıtım bu görevde uygulanmadı.

## Güvenilir işlem davranışı

- Her değiştirici POST, kullanıcı onayından sonra UUID Idempotency-Key ile gönderilir. Özetlerde miktar/lot/referanslar gösterilir; tutar ve kesin stok/maliyet backend otoritesindedir.
- Cevap kaybı/timeout/5xx durumunda donmuş gövde ve aynı anahtar korunur; form kilitlenir. Sekme yeniden yüklense bile sessionStorage'dan **aynı komut** geri alınır. Bu storage yalnız komut/form ve UUID referanslarını tutar; API anahtarı tutmaz. Storage kapalıysa bellekten retry çalışır, sayfayı kapatmayın.
- Modal iptali/Escape POST göndermez. Native dialog focus sınırı ve geri dönüşü korunur. Başarılı işlemler ilgili katalog/lot/stok/satış/trace sorgularını geçersizleştirir.
- Decimal değerler string gönderilir; virgül normalize edilir. Frontend finans/maliyet dağıtımı hesaplamaz. Kesim kg ön kontrolü, yalnız girilen tartımları 6 haneli BigInt ölçeğiyle doğrular; kesin kütle dengesi ve transaction backend'dedir.
- Kullanılabilir miktar/blok durumu backend'den gelir. Bloke/tarihi geçmiş seçenekler kapalıdır; eski cache ile oluşan yarışın gerçek 409 hatası yine gösterilir.
- Bağlı sevkiyat aynı satış hareketini kullanır; yeni stok çıkışı yoktur. Bağımsız sevkiyat fiziksel çıkıştır, satış/gelir değildir. Market kalanı/son tüketici satışı/ikinci kademe alıcı kaydı yoksa **Bilinmiyor** gösterilir.
- Recall ön görünümü kesin sonuç değildir. Nihai üyelik ve blokaj onaydan sonraki backend transaction'ının kaydıdır. Blok kaldırma akışı bulunmaz.
- Tahminler SYNTHETIC eğitim verisidir; gerçek doğruluk iddiası yoktur. Gerçekleşme yoksa null korunur. Sapma/model sürümü backend'den gelir, model frontend'de yeniden çalıştırılmaz.

## API ve UI mimarisi

React 19 / TypeScript / Vite / Tailwind / React Router / TanStack Query / React Hook Form / Zod / Lucide korunmuştur. Ek bağımlılık yalnız test için `@axe-core/playwright` 4.10.2'dir; ağır UI framework eklenmedi.

`src/lib/openapi.d.ts`, bu görevde çalışan FastAPI `/openapi.json` çıktısından openapi-typescript 7.13.0 ile yenilendi. Yazma payload'ları bu request şemalarıyla tip kontrolünden geçer. Backend okuma cevapları OpenAPI'de ayrıntılı modellenmediği için `types.ts` / `modules.ts` gerçek API yanıtlarına göre tanımlanır; browser kabul testleri bunları doğrular.

`components/ui.tsx`, `forms.tsx`, `workflow.tsx`: başlık, kart, rozet, tablo, filtre, durum, native onay/drawer, alan/sayı ve kullanılabilir lot seçimi. `module-validation.ts` ön kontrol, `module-payloads.ts` string/FK eşlemesi içerir. Kayıtlar next_cursor bitene kadar okunur; tekrarlayan cursor reddedilir. Satış/sevkiyat detay okumaları API havuzunu taşırmamak için 4'lü gruplarla yapılır. Tam liste indirme küçük prototip içindir; büyük işletme verisi için backend filtre/toplam ve kademeli liste API'si gerekir.

Recall ve prediction listesi backend'de bulunmaz. Bu sekmede alınmış gerçek UUID/zaman referansları gösterilir; bilinen UUID elle veya URL ile açılır. Global sunucu geçmişi varmış gibi sunulmaz. Otomatik lot/ürün isim eşlemesi veya ML'den lot ilişkisi üretilmez.

## Test ve görsel kanıt

```bash
npm ci
npm run typecheck
npm run build
npm run test
# Backend aynı ayrı *_test DB ile, Vite aynı Node anahtarıyla açıkken:
export AVATAR_E2E_DATABASE=avatar_frontend_v2_test
npm run test:e2e
```

Playwright ayrıca Node process'inde AVATAR_API_KEY ister; anahtarı tarayıcıya aktarmaz. E2E guard, `_test` ile biten açık şema adı ve loopback API gerektirir. Backend'in gerçekten aynı şema ile çalıştığını operatör sağlamalıdır. Testler alış/satış/recall gibi kalıcı kayıtlar oluşturur; işletme veya paylaşılan demo DB'sinde çalıştırmayın. Testler veri silmez. Mevcut canonical veri için repo kökünde aynı environment ile `python -m app.demo_sales_shipments` ve `python -m app.demo_cutting` (`PYTHONPATH=backend`) kullanılabilir; bunlar kurgusal demo verisidir.

Ek gerçek eksik-model testi için:

1. Normal Vite'ı kapatın; 5173 boş olmalıdır.
2. Aynı izole DB/key ile ikinci FastAPI'yi 8002'de `AVATAR_ML_MODEL_DIR` var olmayan boş bir dizini gösterecek şekilde başlatın.
3. Node key ortamı korunarak:

```bash
AVATAR_API_PROXY_TARGET=http://127.0.0.1:8002 \
AVATAR_E2E_API_URL=http://127.0.0.1:8002 npm run test:e2e:missing-models
```

Bu ayrı profil kendi Vite sürecini başlatır/kapatır; başka sunucuyu devralmaz. API cevabı mock edilmez. Normal geliştirmeye dönmek için varsayılan hedefle `npm run dev` kullanın. Varsayılan Chromium `/usr/bin/chromium`; gerekirse CHROMIUM_PATH ayarlayın.

Güncel sonuç, ekran listesi, güvenlik kontrolü ve WEB/ML checklist devri: [VALIDATION_V2.md](VALIDATION_V2.md). Önceki v1 kanıtı [TEST_REPORT.md](TEST_REPORT.md) içinde tarihsel olarak korunmuştur. `validation-v2/screenshots/` gerçek Chromium görüntüleridir; baseline, aynı main commit'inin geçici salt kaynak export'undan alınmıştır. Görüntülere tasarım/mock veya sonradan görsel düzenleme uygulanmadı.
