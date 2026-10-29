# Geri çağırma inceleme sözleşmesi — Görev 21

Web, mevcut `POST /v1/recalls` motorunu üç aşamalı incelemeyle kullanır. Yeni tablo veya migration yoktur. `lot_graph`, transaction yürütücüsü, stok defteri ve mevcut demo komutları korunur.

## Salt okunur önizleme

`GET /v1/recalls/preview?source_lot_id=<UUID>` mevcut `X-API-Key` kimlik doğrulamasını gerektirir. REPEATABLE READ snapshot'ında ileri gerçek FK grafını okur; cevap:

```json
{
  "preview_fingerprint": "recall-v1:<64 küçük harf hex SHA256>",
  "report": { "source_lot": "...", "lots": [], "stocks": [], "buyers": [], "second_tier_distributions": [] }
}
```

Burada `report`, mevcut tam trace raporudur; yukarıdaki gösterim kısaltılmıştır. İdempotency veya domain kaydı oluşturulmaz. İz, sıralı JSON raporunun SHA256 değeridir; kaynak kimliği/kodu/blokajı, ilişkiler, stok konumları/miktarları, satış/sevk ve kayıtlı ikinci kademe kanıtı kapsama dahildir. Süre sınırı veya yapay bekleme yoktur.

## İncelenmiş kesin komut

UUID `Idempotency-Key` ve mevcut API anahtarıyla `POST /v1/recalls`:

```json
{
  "source_lot_id": "00000000-0000-4000-8000-000000000001",
  "reason": "KURGUSAL kalite kontrol gerekçesi",
  "preview_fingerprint": "recall-v1:<GET cevabındaki gerçek değer>",
  "confirmation_lot_code": "ET-2026-001"
}
```

- Gerekçe kırpıldıktan sonra 1–500 karakter olmalıdır. İnceleme izi ile kod birlikte gelmelidir; bozuk/eksik çift 422 döner.
- Motor önce mevcut ileri kapsamı bulur, lotları UUID sırasıyla `FOR UPDATE` kilitler, grafı tekrar okur. Lot kümesi genişlediyse tüm transaction bırakılarak mevcut en fazla üç denemelik protokol korunur; sıra dışı ek lot kilidi alınmaz.
- Lot kodu kilitli kaynakla eşleşmezse **409 RECALL_SOURCE_MISMATCH**. Kilitler alındıktan sonraki rapor izi farklıysa **409 RECALL_PREVIEW_STALE**. İkisinde de yeni recall, üyelik, blokaj veya idempotency kaydı kalmaz. Kullanıcı kaynağı ve güncel kapsamı yeniden incelemelidir.
- Başarılı komut tek transaction'da Recall, RecallLot ve monoton lot blokajını kaydeder. Stok miktarı, maliyet ve geçmiş hareketler değiştirilmez. Başarısız render/transaction kısmi blokaj bırakmaz.
- Aynı scope/key/canonical body, ilk **201** cevabını tekrar döndürür. Önizleme izi başarıdan sonra eski olsa bile kayıtlı cevabın replay'i yeni graf kontrolünden önce yapılır. Aynı key ile farklı içerik **409 IDEMPOTENCY_CONFLICT** döner.
- Yanıt kayıpsa veya 5xx ise **aynı key ve body** korunur. Yeni iz, kaynak, gerekçe veya key ile yeniden komut üretilmez. Kesin 4xx reddinden sonra yeni inceleme yapılabilir.

## Geriye uyumluluk ve güvenlik sınırı

Önceki `{source_lot_id, reason}` çağrıları desteklenir. İki yeni alan da yok/null ise route eski RecallCreate payload'ını kullanır; böylece önceki saklı idempotency hash'leri değişmez. Eski komutlar mevcut kilit/graf/atomiklik denetimlerini kullanmaya devam eder, yeni inceleme izi denetimini kullanmaz. Yeni web komutları her iki alanı da gönderir. Eski belirsiz komutlar aynı özgün gövdeyle kurtarılır.

Bu bilinçli uyumluluk nedeniyle inceleme adımları bütün API istemcilerine zorunlu bir yetki politikası değildir. SHA256 izi imzalı yetki belgesi değildir; lot kodunu yazmak kimlik doğrulama veya ikinci kişi onayı değildir. Ortak X-API-Key sisteminde kullanıcı hesabı, rol, yönetici ayrımı ve kişi bazlı denetim izi yoktur. İnternete açık üretim güvenliği iddiası yoktur.

Zaten bloke lotlar önizlemede belirtilir; yeni recall bunları serbest bırakmaz. Sil/geri al yolu eklenmedi. İlk/ikinci kademe kayıtları yalnız gerçek DB ilişkilerinden gelir; market fiziksel stokları ve tüketici satışları bilinmiyor olarak kalır. Otomatik e-posta/bildirim yoktur.

## Doğrulama

[Gerçek MySQL inceleme testleri](../tests/test_recall_review_mysql.py), [mevcut graf/kilit regresyonları](../tests/test_trace_recall_mysql.py), [React kontrolleri](../frontend/tests/recall.test.tsx) ve [gerçek Chromium kabulü](../frontend/tests/browser/recall-safety.spec.ts). Sonuçlar [kabul raporunda](../docs/RECALL_SAFETY_ACCEPTANCE.md) kayıtlıdır. Yıkıcı testler yalnız ayrı `*_test` şemasında çalıştırılır.
