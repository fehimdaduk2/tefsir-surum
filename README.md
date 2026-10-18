# Tefsir & Hadis Kütüphanesi — sürüm bilgisi ve kurulum dosyası

- `surum.json`: son sürümün numarası, tarihi, yenilikleri, sürüm geçmişi ve kurulum dosyasının adresiyle SHA-256 sağlama toplamı. Program açılışta (günde en çok bir kez) bu dosyayı okuyarak yeni sürüm çıkıp çıkmadığına bakar.
- `Kurulum.exe`: son sürümün kurulum programı. Program, kullanıcı **Güncellemeler › Şimdi güncelle**'ye basınca bu dosyayı indirir, sağlama toplamını doğrular ve kurar. Elle indirilip çalıştırılarak da kurulabilir: yanında veri dosyası yoksa kurulum, gerekenleri `veri/` klasöründen kendisi indirir.
- `veri/`: kurulumun indirdiği veri dosyaları (`Tefsir-Veri-1..6.zip`; isteğe bağlı `Tefsir-Paket-Serh.zip`, `Tefsir-Paket-Lugat.zip`). Telif hakkı koruması altındaki eserlerin metinleri bu dosyalarda yoktur. Adresleri ve sağlama toplamları `surum.json` içindeki `veri` bölümündedir.
