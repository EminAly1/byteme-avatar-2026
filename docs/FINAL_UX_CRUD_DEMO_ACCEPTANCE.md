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
