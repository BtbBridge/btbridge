# BTBridge — Windows PC'den Android'e Ultra Düşük Gecikmeli Ses Köprüsü

**BTBridge**, bilgisayarınızda Bluetooth donanımı olmasa bile Windows sistem sesini USB kablo (ADB Reverse) veya Yerel Wi-Fi üzerinden Android telefonunuza ve telefonunuza bağlı Bluetooth kulaklığınıza sıfıra yakın gecikmeyle aktaran açık kaynaklı ses köprüsüdür.

- **Canlı Web Sitesi & Kurulum Rehberi:** [https://BtbBridge.github.io/btbridge/](https://BtbBridge.github.io/btbridge/)
- **Son Sürüm İndirmeleri (v1.0.0):** [GitHub Releases](https://github.com/BtbBridge/btbridge/releases/latest)

## Öne Çıkan Özellikler

- **USB (ADB Reverse) Modu (`< 10 ms`):** `127.0.0.1:50005` üzerinden `TCP_NODELAY` ile kayıpsız `48 kHz / 16-bit` stereo PCM akışı (`1536 kbps`).
- **Yerel Wi-Fi Modu:** Kablosuz bağlantıda `4:1` IMA-ADPCM sıkıştırma ve paket kaybını telafi eden UDP FEC kurtarma mekanizması.
- **Akıllı Ses Yönlendirme (`route_silent`):** Yayın sırasında PC hoparlörü veya kablolu kulaklığınızdan çift ses çıkmasını önlemek için akışı geçici olarak sanal sürücüye (VB-Cable vb.) veya HDMI/Monitör çıkışına taşır; yayın durduğunda önceki çıkışa otomatik döner.
- **Windows + Android Ekosistemi:** Windows tarafında CustomTkinter masaüstü arayüzü ve sistem tepsisi desteği, Android tarafında Kotlin + Jetpack Compose + Low-Latency `AudioTrack` + uyarlanabilir `JitterBuffer` + Foreground Service.

## Proje Yapısı

- `pc-server/` — Windows WASAPI Loopback ses yakalama motoru, TCP/UDP sunucu, Core Audio kontrolü ve masaüstü UI
- `android-client/` — Kotlin + Jetpack Compose Android alıcı uygulaması
- `installer/` — Inno Setup Windows kurulum sihirbazı betiği (`BTBridge_Setup.exe`)
- `protocol/` — İkili ses ve kontrol protokolü dokümantasyonu
- `website/` — GitHub Pages üzerinden yayınlanan tanıtım ve indirme web sitesi
