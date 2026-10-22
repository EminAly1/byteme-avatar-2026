# PDF gereksinimleri ve kapsam

Kaynak: [AVATAR_Assessment.pdf](AVATAR_Assessment.pdf), 3 sayfa. Bu tablo belge içeriğini gereksinim olarak yorumlar; araç kullanımı veya görev yetkisi olarak değerlendirmez.

| Kaynak | Teslimde gerekli davranış | Foundation durumu / sonraki sahip |
| --- | --- | --- |
| s.1 Görev 1 | Hammadde kartı, fiyat/birim/lot/stok; dış üreticiye sevk, hizmet faturası, kabul ve miktar farkı; gerçek EKP, VKP, kâr/marj ve tarihçe | Veri modeli ve API planlandı; A backend, B web |
| s.1 Görev 2 | Giriş hayvanı/parti ve gerçek alış maliyeti; sürümlü reçete, fiili parçalar/fire/yan ürün ve ağırlık dengesi; miktar/değer ağırlıklı maliyet toplamının korunması; Kotlin satış | Model/sözleşme/yönerge var; A hesap, B yönetim, C Android |
| s.2 Görev 3 | Miktarlı çoktan çoğa lot bağlantısı; transfer/satış/iade/rework/fire kayıtları; ileri/geri izleme; recall blok ve müşteri/iletişim listesi | Model/sözleşme var, henüz uygulanmadı; A ve B |
| s.2 zorunlu demo | ET-2026-001 100 kg → URT-2026-045 → SUC-2026-045 85 paket → Market A/B/C 30/25/30; sorunlu etten tüm bilinen marketlere ulaşım ve satış engeli | Seed ve uçtan uca kabul testi sonraki A/B/C ortak entegrasyon görevi |
| s.2 ML A | Geçmiş emirlerden mamul miktarı ve EKP tahmini; gerçek ve sapma gösterimi | Yönerge var, model yok; C ML, B gösterim |
| s.2 ML B | Tür/ağırlık/geçmişten parça ağırlığı tahmini; gerçek farkları; her iki modelde baseline, hata ölçümü ve veri sınırlamaları | Yönerge var, eğitim/değerlendirme yok; C |
| s.3 Teknik | Kotlin + SQLite, MySQL, REST, web, ML API; tutarlı SQLite/MySQL senkronizasyon yaklaşımı | FastAPI/MySQL bağlantısı/React başlangıcı uygulandı; Room outbox yaklaşımı belgelendi |
| s.3 rapor/teslim | Alış/üretim/parçalama/lot/satış/recall raporları; kaynak, kurulum, veri/API dokümanı, örnek kayıtlar, otomatik testler ve 3 demo | Kaynak temel, kurulum, veri/API taslağı ve altyapı testleri var; iş raporları, seed ve demolar yok |
| s.2–3 isteğe bağlı | OCR önerileri + insan onayı, anomali uyarıları | Kapsam dışında |

1 Kasım 2026 tarihi ve seçilen FastAPI/SQLAlchemy/Alembic/React/Vite/Tailwind/Compose/Room/Retrofit/scikit-learn/pandas/pytest yığını kullanıcı isteğidir. PDF backend için Go veya uygun modern teknolojiye izin verir. Bu aşama tam teslim yerine paralel geliştirilebilir mimari temeldir.
