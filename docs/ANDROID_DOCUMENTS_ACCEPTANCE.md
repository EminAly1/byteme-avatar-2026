# Android belgeler — Görev 25

31 Ekim 2026, Europe/Istanbul. Branch `feature/android-documents-final`.
Başlangıç `4ace298` — PR #41'in main'e merge edildiği Git geçmişi ve
`ce26268` ancestor kontrolüyle doğrulandı.

## İlk çalışan aşama

Ana Sayfa ve onaylı satış kartlarından **Belgeler** ekranına ulaşılır; beş alt
sekme korunur. Gerçek `GET /v1/document-drafts/sales/{sale_id}` sözleşmesi
backend `document_api.py` ve `document_drafts.py` kaynaklarından alınmıştır.
Müşteri, lot, miktar, birim fiyat, orijinal/düzeltilmiş tutarlar ve kaynak durum
salt okunurdur. İade ve sevkiyat bağlantıları sunucudan okunur.

Proforma/Satış Özeti seçimi ile ayrı geçici alan düzenleme ekranı vardır.
Yalnız backend DraftFields allowlist'i düzenlenebilir: başlık, açıklama, satıcı
beyanı, iletişim, belge tarihi, ödeme/teslimat açıklamaları, not, referans ve demo
etiketi. Karakter/tarih/kontrol karakteri sınırları backend ile eşleşir.
Kaynak satış/stock için setter veya komut eklenmedi; sunucu taslak arşivi yoktur.

İlk aşama commit/push, PDF işlevleri eklenmeden yapılır. Son aşama bu raporu
PDF kabul sonuçlarıyla günceller. PDF önizleme/kaydetme/paylaşma ilk aşamada
henüz uygulanmamıştır; bu aşama PDF kabulü değildir.

## Güvenlik ve sınırlar

Room/outbox/frozen key-body, Keystore, satış idempotency, paket adı ve ikon
korunur. Belge repository'sinin DAO veya kesin satış/stok komutu bağımlılığı
yoktur. Endpoint değişiminde eski kaynak temizlenir. Okuma hatası son kaynağı
güncel diye sunmaz. API anahtarı yalnız mevcut korumalı HTTP istemcisindedir.

Önceki APK imza uyuşmazlığını aşmak için uninstall, pm clear, Room silme veya
imza güvenliğini düşürme yapılmaz. API28/35 cihaz testi için emülatör kurulmaz.
Fiziksel cihaz ve eski kurulum üzerinde veri koruyan yükseltme doğrulanmadı.

## İlk aşama doğrulaması

`testDebugUnitTest lintDebug assembleDebug` kabul kapısı çalıştırılır. Kontrollü
JSON fixture gerçek backend şemasını temsil eder; canlı MySQL kabulü sayılmaz.
Test belgeyi okuma ve geçici taslağı düzenleme sonrasında gerçek Room SQLite
stok/satış/taslak/outbox kayıtlarını ve frozen body/key'i karşılaştırır.
Sonuçlar commit öncesi aşağıya kaydedilir.

İlk aşama sonucu: **26/26 host test, 0 atlama; lint 0 bulgu; debug APK build başarılı**. API28/35 cihaz testi yapılmadı.
