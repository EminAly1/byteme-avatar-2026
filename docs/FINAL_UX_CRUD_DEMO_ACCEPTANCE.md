# AVATAR — Görev28 kullanıcı deneyimi, ana kayıt ve demo kabulü

31 Ekim 2026. Başlangıç `a7c80bc` / PR #45; branch `feature/final-ux-crud-demo-v1`.
Takip [Issue #39](https://github.com/EminAly1/byteme-avatar-2026/issues/39).

## Aşama1 — Alış ve reçete

- Alış Görüntüle ve yeni kayıt sonrası erişilebilir drawer; gerçek GET yanıtındaki
  satırlar, tedarikçi/depo, lot/birim ve backend Decimal toplamı. Görüntüleme yazmaz.
- Alışta kimlik/miktar-tutar/tarih grupları; ortak20px form ritmi, üstten hizalı
  alanlar,44px silme kontrolü; mobil tek sütun ve tam genişlik drawer.
- Uygun kg parçası yoksa açıklama; gerçek Mamul/Yan ürün kg kartı oluşturma
  kısayolu, korunmuş reçete taslağı ve farklı ürün seçimi/alan yanında tekrar hatası.
- P0 unit15 geçti; dialog düzenlemesinden sonra ilgili3 test tekrar geçti.
  Gerçek API/MySQL ile iki farklı P0 Chromium senaryosu: alış drawer/odak/hizalama
  ve gerçek parça ürünü/reçete oluşturma. İlk koşudaki nested-form ve responsive
  test seçicisi sorunları düzeltildi; son gerçek alış kontrolü390/768/1440px, Escape/odak ve stok değişmezliğiyle geçti.
  Reçete/parça oluşturma gerçek API/MySQL senaryosu da geçti.

Aşama2 ana kayıt CRUD/AI ve Aşama3 katalog/APK/güvenli eşleştirme planı henüz
bu checkpoint'te tamamlandı sayılmaz. Android kaynaklarına dokunulmadı.

## Aşama2 — Ana kayıt ve AI

- Ürün/firma/depo gerçek GET/PATCH/DELETE, onaylı silme ve yenilenen liste.
  Ürün/depo yalnız ad; firma ad/iletişim. Birim/tür/dönüşüm/SKU/roller/konum
  ilişkileri kilitli; ek alan422. Kullanılan kart409 MASTER_IN_USE; arşivleme yok.
- Silme ve JSON referansı oluşturan dar yazma noktaları ebeveyn satır kilidi
  kullanır. InnoDB FK yarışları ve JSON taslak referansları korunur; finansal
  algoritma/model/şema değiştirilmedi. POST/PATCH/DELETE pending alanları ayrı;
  kayıp cevapta method/key/body değişmez.
- Kesin kayıt listelerinde gerçek özet/işlem bağlantıları ve açıklamalı devre dışı
  Düzenle/Sil; reçete sürümü korunur, belge düzenleme yalnız geçici notlardır.
- AI girişi plan/malzeme/maliyet/paket/isteğe bağlı bağlantı kartlarına ayrıldı.
  Sonuç KPI/karşılaştırma ve beş parça çubuğu yalnız backend tahminlerini gösterir.
  6.000 SYNTHETIC/0 gerçek tarihsel veri ve metrik gerilemesi açıkça korunur.
- Gerçek izole MySQL18 hedefli test ve iki rework regresyonu geçti; zorunlu
  1.543,50/18,16 maliyet, FK/idempotency, DELETE–alış ve JSON referansı yarışı dahil.
- Web35 ilgili unit, typecheck/build; iki P1 gerçek Chromium (üç master CRUD/bağlı
  ret ve iki AI V2), P0 iki senaryo regresyonu ve eski AI kayıp-cevap/reload testi geçti.
  İlk3 unit hatası yeni görünüm metni/çift Görüntüle kaynaklıydı; çift eylem
  kaldırıldı ve metin beklentileri güncellendi. Test/assertion silinmedi veya skip edilmedi.
