# Tefsir Kütüphanesi — sürüm bilgisi ve kurulum dosyası

- `surum.json`: son sürümün numarası, tarihi, yenilikleri, sürüm geçmişi ve kurulum dosyasının adresiyle SHA-256 sağlama toplamı. Program açılışta (günde en çok bir kez) bu dosyayı okuyarak yeni sürüm çıkıp çıkmadığına bakar.
- `Kurulum.exe`: son sürümün kurulum programı. Program, kullanıcı **Güncellemeler › Şimdi güncelle**'ye basınca bu dosyayı indirir, sağlama toplamını doğrular ve kurar. Elle indirilip çalıştırılarak da kurulabilir (veri dosyaları `Tefsir-Veri-*.zip` aynı klasörde olmalı ya da program zaten kurulu olmalı).
