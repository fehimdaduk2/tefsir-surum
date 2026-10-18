# Tefsir & Hadis Kütüphanesi — sürüm bilgisi ve kurulum dosyası

- `surum.json`: son sürümün numarası, tarihi, yenilikleri, sürüm geçmişi ve kurulum dosyasının adresiyle SHA-256 sağlama toplamı. Program açılışta (günde en çok bir kez) bu dosyayı okuyarak yeni sürüm çıkıp çıkmadığına bakar.
- **Kurulum ve Mac/Linux paketleri** [Releases](https://github.com/fehimdaduk2/tefsir-surum/releases)'ta yayımlanır (`.github/workflows/yayin.yml`: `yayin` dalına gönderilen dosyalardan sürümü oluşturur, sonra dalı siler; etiket `main`'e bağlanır). `surum.json` › `kurulum` ve `diger` sürüme bağlı adresleri, `sha256` sağlama toplamını taşır. Program **Güncellemeler › Şimdi güncelle**'de kurulumu oradan indirip doğrular. Elle indirilen kurulum, yanında veri yoksa gerekenleri `veri/` klasöründen indirir.
- `veri/`: kurulumun indirdiği veri dosyaları (`Tefsir-Veri-1..6.zip`; isteğe bağlı `Tefsir-Paket-Serh.zip`, `Tefsir-Paket-Lugat.zip`). Telif hakkı koruması altındaki eserlerin metinleri bu dosyalarda yoktur. Adresleri ve sağlama toplamları `surum.json` içindeki `veri` bölümündedir.
- `docs/`: tanıtım ve indirme sayfası (GitHub Pages: Settings › Pages › Branch `main`, klasör `/docs`).
- `ekler/`: ek paketler (`Tefsir-Ek-*.zip`). Kurulu programlar `surum.json` › `ekler` listesindekileri arka planda indirir; listeden çıkan paket bilgisayarlardan silinir.
