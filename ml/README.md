# Zorunlu AI — üretim/EKP ve kuzu parçalama v2

İki Ridge modeli yeniden eğitildi. **Her model 3.000, toplam 6.000 SYNTHETIC kayıt; gerçek tarihsel satır 0.** Bu modeller karar desteğidir; kesin stok, satış, maliyet veya lot ilişkisi oluşturmaz.

## Tekrar üretme

Repo kökünde Python 3.12 ve pinli bağımlılıklar:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt -r ml/requirements.txt
backend/.venv/bin/python -m ml.training.train \
  --seed 20261029 --count 3000 --trained-at 2026-10-29T00:00:00+00:00
backend/.venv/bin/python -m ml.scripts.predict_examples
backend/.venv/bin/python -m pytest ml/tests -q
```

Eğitim offline çalışır; API istekleri eğitim yapmaz. `--data`, `--models`, `--evaluation` ayrı çıktı dizinleri alır. Varsayılanlar depodaki v2 dosyalarını yeniler; çalışan worker'ın cache'i kendiliğinden yenilenmez. Sabit veri/seed/ortam/zaman aynı JSON ve SHA256 dosyalarını üretir. Gerçek özel veri repo dışında veya ignored `ml/artifacts/` altında tutulmalı; bu sentetik veri havuzuna eklenmemelidir.

API çıkarımı sklearn/pandas gerektirmez: sınırlı boyutlu, doğrulanmış JSON katsayıları standart Python ile yüklenir. Dockerfile güncel iki JSON/sha256 çiftini imaja kopyalar; Compose `AVATAR_ML_MODEL_DIR=/app/ml/models` ayarlar. Ayrıntılar [INTEGRATION](INTEGRATION.md).

## Kapsam, veri ve seçim

- Üretim: **5–300 kg et**, iki et türü, üç **kurgusal** üretici profili, **0,25–2 kg/paket**, farklı malzeme fiyatları ve hizmet ön teklifleri. Baharat etin %1–4’ü; kılıf %2–8’i. [Tam sınırlar ve model kartı](MODEL_CARD_PRODUCTION.md).
- Kesim: **5–80 kg**, yalnız Kuzu ve beş pozitif parça; toplam giriş miktarını aşmaz. [Model kartı](MODEL_CARD_CUTTING.md).
- Her model 1.800 train / 600 validation / 600 test. Tarihler, profiller ve süreç etkileri kurgusaldır; aynı işlem farklı splitlere bölünmez. [Manifest](data/manifest.json), [üretici](data/generate.py), [eğitim](training/train.py).
- Ön işleme yalnız train'e fit edilir. Alpha 0,1/1/10 yalnız validation'da seçilir; test seçime veya fit'e katılmaz. Üretim alpha=1, kesim alpha=0,1. Kabul kapısı validation'da train-mean baseline'dan düşük normalize RMSE'dir.

**V2 her hedefte iyileşme değildir.** Eski sabit v1 testinde gerileme vardır; yeni ortak kapsamda da üretim toplam maliyet RMSE'si biraz kötüdür. V2 genişletilmiş sentetik prototip için etkinleştirildi; genel gerçek doğruluk artışı veya üretim terfisi onaylanmadı. Aynı satırlarda üç yöntem ve farklı test popülasyonları [değerlendirme raporunda](EVALUATION_REPORT.md) ayrı gösterilir. Test sonucunu iyileştirmek için simülatör/hedef/alpha yeniden ayarlanmadı.

## Tahmin ekranı ve güvenli kullanım

`/yapay-zeka` üretim/EKP ve kuzu parçalama formlarını içerir. Aralık/yardım metni/alan doğrulaması ve sayısal örnekler `/v1/predictions/models` metadata'sından gelir. Örnek düğmeleri gerçek ürün/reçete UUID'si uydurmaz; kesimde kullanıcı beş gerçek ürünü seçer. İşleme bağlı tahmin yalnız başlamadan kaydedilir. Model sonucu, tarihi, sürümü, SYNTHETIC etiketi ve kesin gerçekleşme/sapma ayrı gösterilir.

Kayıtlı tahmin GET'i mevcut modeli çağırmaz. Yeni model veya dosyasının yokluğu eski sonucu değiştirmez. Aynı scope/key/body orijinal cevabı döndürür; belirsiz yanıtta yeni key üretilmez. Sınır dışı/fiziksel olarak olanaksız girişler reddedilir. V2 fiziksel olarak geçersiz ham çıkarımı sessizce kırpıp güvenilir tahmin diye yayımlamaz.

- [Model v2 kabulü ve test kanıtları](../docs/AI_MODEL_V2_ACCEPTANCE.md)
- [Makine okunur metrikler / ayrık ID'ler](evaluation/metrics.json)
- [Korunan v1 artefaktları / 600 satırlık eski manifest / 120+120 sabit test](evaluation/v1/)
- [Tarihsel Görev 09 testleri](reports/full-tests.txt) ve [eski demo](reports/demo.json): v1 kanıtıdır; v2 sonucu olarak kullanılmaz.

Ortak checklist, Android, belge merkezi/PDF, geri çağırma kodu ve genel tema bu görevde değiştirilmedi. Gerçek işletme verisi, kalibre belirsizlik ve dış doğrulama hâlâ gereklidir.
