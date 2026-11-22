/* ==========================================================================
   BTBridge Web Uygulaması — Çift Dil (TR/EN), Canlı Köprü Demoları & Release URL
   ========================================================================== */

(function () {
    "use strict";

    var RELEASE_CONFIG = {
        defaultGithubRepo: "BtbBridge/btbridge"
    };

    var LANG_STORAGE_KEY = "btbridge_web_lang";
    var currentLang = "tr";
    var toastTimer = null;

    var I18N = {
        tr: {
            page_title: "BTBridge — Windows PC'den Android'e Ultra Düşük Gecikmeli Ses Köprüsü",
            nav_routing: "Akıllı Yönlendirme",
            nav_features: "Özellikler",
            nav_setup: "Kurulum",
            nav_download: "İndir",
            nav_faq: "SSS",
            nav_cta: "Hemen İndir",
            mobile_lang_label: "Dil / Language",
            hero_badge: "USB ADB Reverse & Yerel Wi-Fi Ses Köprüsü",
            hero_title_1: "Windows Sesini Telefona &",
            hero_title_2: "Bluetooth Kulaklığa Köprüle",
            hero_subtitle: "PC'nizde Bluetooth donanımı olmasa bile oyun, film ve sistem seslerini <strong>48 kHz stereo</strong> kalitesiyle Android telefonunuza aktarın; telefonunuzdaki Bluetooth kulaklıktan sıfıra yakın gecikmeyle dinleyin.",
            hero_btn_win: "Windows Kurulumunu İndir (54.6 MB)",
            hero_btn_apk: "Android APK İndir (15.6 MB)",
            trust_win: "Windows 10 / 11 (64-bit)",
            trust_nopy: "Python / JDK Gerektirmez",
            trust_oss: "GPL-3.0 Açık Kaynak • TR / EN",
            demo_win_title: "BTBridge — USB & Wi-Fi Ses Köprüsü",
            demo_pc_heading: "BTBridge Masaüstü Sunucusu",
            demo_pc_sub: "WASAPI Loopback • Akıllı Ses Yönlendirme",
            demo_rtt_lbl: "Gecikme (RTT)",
            demo_rate_lbl: "Veri Hızı",
            demo_client_lbl: "Bağlı Cihaz",
            demo_mode_wifi: "Yerel Wi-Fi",
            demo_vu_lbl: "Canlı Ses Seviyesi",
            demo_bt_meta: "Bluetooth A2DP • Aktif",
            demo_engine_lbl: "Ses Motoru",
            demo_status_active: "● Yayın Aktif",
            demo_status_ready: "● Hazır",
            demo_toggle_stop: "Yayını Durdur",
            demo_toggle_start: "Yayını Başlat",
            demo_phone_conn: "Bağlandı",
            demo_phone_wait: "Bekleniyor",
            demo_phone_disc: "Bağlantıyı Kes",
            demo_phone_usb: "USB ile Bağlan",
            demo_phone_wifi: "Wi-Fi ile Bağlan",
            demo_taskbar_active: "Aktif Çıkış: Sanal / HDMI Kanal",
            demo_taskbar_vol_active: "PC Sessiz • Yayın Aktif",
            demo_taskbar_restored: "Orijinal Çıkışa Döndü: Hoparlör (USB)",
            demo_taskbar_vol_restored: "Ses: %100",
            demo_bridge_usb: "TCP 50005<br>PCM Akışı",
            demo_bridge_wifi: "UDP FEC<br>ADPCM 4:1",
            demo_bridge_idle: "Beklemede<br>Akış Yok",
            demo_waiting: "Bekleniyor",
            m1_label: "USB Modu Gecikmesi",
            m1_desc: "ADB Reverse + TCP_NODELAY ile kablo üzerinden anlık iletim.",
            m2_label: "Kayıpsız Stereo PCM",
            m2_desc: "1536 kbps ham ses; oyun, sinema ve müzikte sıfır sıkıştırma kaybı.",
            m3_val: "Akıllı İzolasyon",
            m3_label: "Sadece Kulaklıkta Ses",
            m3_desc: "Yayın başlayınca PC çıkışı sessizleşir, bitince otomatik eski çıkışa döner.",
            m4_label: "Wi-Fi Paket Kurtarma",
            m4_desc: "Kablosuz ağdaki paket kayıplarını UDP FEC ile anında onarır.",
            route_eyebrow: "Akıllı Ses Yönlendirme",
            route_title: "Sadece Kulaklığında Ses — PC Hoparlörü Sessiz Kalır",
            route_desc: "Yayın başladığında bilgisayar hoparlörünüzden veya kablolu kulaklığınızdan çift ses gelmez. BTBridge, sistem ses düzeyinizi bozmadan akışı arka planda sanal/sessiz bir kanala taşır ve işiniz bitince eski çıkışa döner.",
            route_old_tag: "Klasik Araçlar",
            route_old_title: "Çift Ses veya Sistem Susturma",
            route_old_desc: "Ses ya hem bilgisayardan hem telefondan aynı anda yankı yapar ya da Windows sistem sesi kapatıldığı için mikser ayarlarınız bozulur.",
            route_old_dev: "Hoparlör (USB)",
            route_old_state: "✕ Sistem Sesi Kesildi",
            route_new_tag: "BTBridge Akıllı Yönlendirme",
            route_new_title: "Temiz İzolasyon, Otomatik Geri Dönüş",
            route_new_desc: "BTBridge varsayılan ses çıkışını geçici olarak sanal sürücüye veya HDMI/Monitör çıkışına alır. PC çıkışı tamamen sessiz kalırken telefonunuzdan tam ses akar.",
            route_new_dev: "Sanal / HDMI Çıkışı",
            route_new_state: "● İzole Yayın • %100",
            rs1_title: "Otomatik Çıkış Taraması",
            rs1_desc: "Önce VB-Cable / Virtual Audio / Voicemeeter gibi sanal sürücüleri, yoksa Monitör/HDMI çıkışlarını seçer.",
            rs2_title: "Bozulmayan Ses Mikseri",
            rs2_desc: "Windows ses düzeyiniz kapatılmadan korunur; WASAPI Loopback sesi sessiz kanaldan kayıpsız yakalar.",
            rs3_title: "Kusursuz Geri Dönüş",
            rs3_desc: "Yayını durdurduğunuzda veya uygulamayı kapattığınızda Windows önceki varsayılan cihazınıza otomatik döner.",
            vbcable_tip: "<strong>Dizüstü Bilgisayar İpucu:</strong> Monitör/HDMI ses çıkışı olmayan tek hoparlörlü bir laptop kullanıyorsanız, ücretsiz <code>VB-Audio Virtual Cable</code> kurmanız yeterlidir — BTBridge bunu otomatik algılayıp seçer.",
            feat_eyebrow: "Mühendislik Detayları",
            feat_title: "Her Katmanda Düşük Gecikme İçin Tasarlandı",
            feat_desc: "Windows çekirdeğinden Android ses çıkışına kadar gereksiz tamponlama ve kodlama yükü olmadan doğrudan iletim.",
            f1_title: "10 ms WASAPI Loopback",
            f1_desc: "PyAudioWPatch tabanlı yakalama motoru 48 kHz stereo sesi 10 ms'lik (1920 byte) paketler halinde gecikmesiz yakalar.",
            f2_title: "Wi-Fi'da ADPCM + UDP FEC",
            f2_desc: "Kablosuz modda 4:1 IMA-ADPCM sıkıştırma ve ileri hata düzeltme (FEC) ile ağ dalgalanmalarında bile ses kopmasını önler.",
            f3_title: "Kotlin Low-Latency AudioTrack",
            f3_desc: "Android istemci, URGENT_AUDIO iş parçacığı önceliği, uyarlanabilir JitterBuffer ve 3 ms klik önleyici yumuşak geçiş kullanır.",
            f4_title: "Sistem Tepsisi & Arka Plan",
            f4_desc: "Pencere kapatıldığında tepsiye küçülür. Android'de ise Foreground Service sayesinde ekran kapalıyken bile kesintisiz çalar.",
            f5_title: "Tek Tıkla APK Kurulumu",
            f5_desc: "Kurulum paketi ADB araçlarını ve BTBridge.apk dosyasını içinde taşır; arayüzden tek tıkla telefona yükleyebilirsiniz.",
            f6_title: "Çift Dil (TR / EN) & Canlı VU",
            f6_desc: "Kurulum sihirbazından masaüstü ve Android uygulamasına kadar tam Türkçe ve İngilizce destek; anlık RTT ve VU takibi.",
            cmp_eyebrow: "Karşılaştırma",
            cmp_title: "Alternatiflere Göre Nerede Duruyor?",
            th_feat: "Özellik",
            th_usb: "BTBridge (USB)",
            th_wifi: "BTBridge (Wi-Fi)",
            th_dongle: "USB Bluetooth Dongle",
            th_other: "Klasik Ses Uygulamaları",
            tr_lat: "Aktarım Gecikmesi",
            tr_lat_usb: "< 10 ms (Anlık)",
            tr_qual: "Ses Kalitesi",
            tr_qual_usb: "48 kHz Kayıpsız PCM",
            tr_qual_dongle: "SBC / AAC Sıkıştırma",
            tr_qual_other: "Değişken",
            tr_iso: "Otomatik PC Ses İzolasyonu",
            tr_iso_btb: "Otomatik (Sanal / HDMI)",
            tr_iso_btb2: "Otomatik (Sanal / HDMI)",
            tr_iso_dongle: "Gerekmez",
            tr_iso_other: "Manuel / Yankı Yapar",
            tr_cost: "Ek Donanım Maliyeti",
            tr_cost_usb: "0 TL (Mevcut USB Kablo)",
            tr_cost_wifi: "0 TL (Kablosuz)",
            tr_cost_dongle: "Dongle Gerekli",
            tr_cost_other: "0 TL",
            tr_adb: "Tek Tıkla ADB APK Kurulumu",
            tr_adb_yes: "Dahili",
            tr_adb_yes2: "Dahili",
            tr_adb_na: "Uygulanamaz",
            tr_adb_man: "Manuel",
            setup_eyebrow: "Hızlı Başlangıç",
            setup_title: "2 Dakikada Köprüyü Kurun",
            setup_desc: "İster sıfır gecikmeli USB kablo, ister kablosuz Yerel Wi-Fi modunu seçin.",
            tab_usb: "USB Kablo (Önerilen)",
            tab_wifi: "Yerel Wi-Fi",
            dl_eyebrow: "Doğrulanmış Sürümler • v1.1.0",
            dl_title: "İndirme Merkezi",
            dl_desc: "Tüm kurulum paketleri yerel testlerden geçirilmiş ve SHA-256 doğrulama özetleriyle sunulmuştur.",
            win_spec_1: "Türkçe / English dil seçimli Inno Setup kurulum sihirbazı",
            win_spec_2: "ADB araçları ve BTBridge.apk paketi kurulum içinde gömülü",
            win_spec_3: "Python veya harici runtime kurulumu gerektirmez",
            copy_btn: "Kopyala",
            copied_btn: "Kopyalandı",
            copy_toast: "SHA-256 doğrulama özeti panoya kopyalandı.",
            win_dl_btn: "BTBridge_Setup.exe İndir (54.6 MB)",
            win_port_btn: "Taşınabilir Tekil EXE İndir — BTBridge.exe (35.1 MB)",
            apk_sub: "Android 8.0+ (API 26+) • v1.1.0",
            apk_spec_1: "İlk açılışta Türkçe / English dil seçimi + anlık TR/EN geçişi",
            apk_spec_2: "Low-Latency AudioTrack, JitterBuffer + Bluetooth A2DP takipçisi",
            apk_spec_3: "Foreground Service ile ekran kilitliyken bile kesintisiz ses",
            apk_dl_btn: "BTBridge.apk İndir (15.6 MB)",
            apk_note: "İsterseniz PC uygulaması içinden tek tıkla telefona kurabilirsiniz",
            faq_eyebrow: "Sıkça Sorulan Sorular",
            faq_title: "Merak Edilenler",
            q1: "Bilgisayarımda Bluetooth alıcısı yoksa çalışır mı?",
            a1: "Evet! BTBridge tam olarak bunun için geliştirilmiştir. Ses PC'nizden telefonunuza USB kablo veya Wi-Fi üzerinden aktarılır; Bluetooth kulaklığınız ise telefonunuza bağlı kalır.",
            q2: "Yayın başladığında PC hoparlöründen veya kulaklığından ses gelmeye devam eder mi?",
            a2: "Hayır. BTBridge yayın başladığında Windows ses düzeyinizi kapatmadan varsayılan çıkışı geçici olarak sanal sürücüye (VB-Cable vb.) veya Monitör/HDMI çıkışına yönlendirir. Yayını durdurduğunuzda eski çıkışınıza otomatik olarak geri döner.",
            q3: "Dizüstü bilgisayarımda sadece tek hoparlör görünüyor, ne yapmalıyım?",
            a3: "Ücretsiz VB-Audio Virtual Cable sürücüsünü yüklemeniz yeterlidir. BTBridge kurulu sanal sürücüyü öncelikli olarak algılar ve ses çıkışını otomatik oraya yönlendirir.",
            q4: "USB ve Wi-Fi modları arasındaki temel fark nedir?",
            a4: "USB (ADB Reverse) modu 1536 kbps kayıpsız 48 kHz PCM kullanır ve <10 ms gecikme sunar. Yerel Wi-Fi modu ise kablo gerektirmez, bant genişliğini verimli kullanmak için 4:1 IMA-ADPCM sıkıştırma ve paket kaybını önleyen UDP FEC protokolü ile çalışır.",
            q5: "Python veya Android Studio kurmam gerekiyor mu?",
            a5: "Hayır. Windows kurulum sihirbazı (BTBridge_Setup.exe) gerekli tüm kütüphaneleri, ADB araçlarını ve Android APK'sını tek paket halinde sunar.",
            footer_brand: "BTBridge v1.1.0 • Windows PC → Android Düşük Gecikmeli Ses Köprüsü",
            footer_license: "GPL-3.0 Lisans",
            setup_steps: {
                usb: [
                    {
                        title: "USB Hata Ayıklamayı Açın",
                        desc: "Android telefonunuzda Geliştirici Seçenekleri'nden USB Hata Ayıklama'yı açıp kabloyla PC'ye bağlayın ve ekrandaki izni onaylayın."
                    },
                    {
                        title: "Telefona APK Kur & Yayını Başlat",
                        desc: "Windows'ta BTBridge'i açıp \"Telefona APK Kur\"a basın, ardından \"Yayını Başlat\" butonuna tıklayın (PC sesi sessiz kanala yönlenir)."
                    },
                    {
                        title: "USB ile Bağlan'a Dokunun",
                        desc: "Bluetooth kulaklığınızı telefona bağlayın ve Android uygulamasında \"USB ile Bağlan\"a dokunun. Ses anında kulaklığınızda!"
                    }
                ],
                wifi: [
                    {
                        title: "Aynı Wi-Fi Ağına Bağlanın",
                        desc: "Bilgisayarınızın ve Android telefonunuzun aynı yerel Wi-Fi (veya telefon hotspot) ağına bağlı olduğundan emin olun."
                    },
                    {
                        title: "Yerel Wi-Fi Modunu Başlatın",
                        desc: "BTBridge PC uygulamasında \"Yerel Wi-Fi\" sekmesini seçip \"Yayını Başlat\"a basın ve ekranda görünen yerel IP adresini okuyun."
                    },
                    {
                        title: "Wi-Fi ile Bağlan'a Dokunun",
                        desc: "Telefonunuzdaki BTBridge uygulamasına PC'nin yerel IP adresini yazıp \"Wi-Fi ile Bağlan\"a dokunun. ADPCM + UDP FEC ile kablosuz dinleyin!"
                    }
                ]
            }
        },
        en: {
            page_title: "BTBridge — Ultra-Low Latency Windows PC to Android Audio Bridge",
            nav_routing: "Smart Routing",
            nav_features: "Features",
            nav_setup: "Setup",
            nav_download: "Download",
            nav_faq: "FAQ",
            nav_cta: "Download",
            mobile_lang_label: "Language / Dil",
            hero_badge: "USB ADB Reverse & Local Wi-Fi Audio Bridge",
            hero_title_1: "Stream Windows Audio to Your",
            hero_title_2: "Phone & Bluetooth Headphones",
            hero_subtitle: "Even if your PC has no Bluetooth adapter, stream games, movies, and system audio in <strong>48 kHz stereo</strong> to your Android phone and listen through your Bluetooth headphones with near-zero latency.",
            hero_btn_win: "Download Windows Installer (54.6 MB)",
            hero_btn_apk: "Download Android APK (15.6 MB)",
            trust_win: "Windows 10 / 11 (64-bit)",
            trust_nopy: "No Python / JDK Required",
            trust_oss: "GPL-3.0 Open Source • TR / EN",
            demo_win_title: "BTBridge — USB & Wi-Fi Audio Bridge",
            demo_pc_heading: "BTBridge Desktop Server",
            demo_pc_sub: "WASAPI Loopback • Smart Audio Routing",
            demo_rtt_lbl: "Latency (RTT)",
            demo_rate_lbl: "Bitrate",
            demo_client_lbl: "Connected Device",
            demo_mode_wifi: "Local Wi-Fi",
            demo_vu_lbl: "Live Audio Level",
            demo_bt_meta: "Bluetooth A2DP • Active",
            demo_engine_lbl: "Audio Engine",
            demo_status_active: "● Streaming",
            demo_status_ready: "● Ready",
            demo_toggle_stop: "Stop Streaming",
            demo_toggle_start: "Start Streaming",
            demo_phone_conn: "Connected",
            demo_phone_wait: "Waiting",
            demo_phone_disc: "Disconnect",
            demo_phone_usb: "Connect via USB",
            demo_phone_wifi: "Connect via Wi-Fi",
            demo_taskbar_active: "Active Sink: Virtual / HDMI Channel",
            demo_taskbar_vol_active: "PC Silent • Streaming",
            demo_taskbar_restored: "Restored Output: Speakers (USB)",
            demo_taskbar_vol_restored: "Volume: 100%",
            demo_bridge_usb: "TCP 50005<br>PCM Stream",
            demo_bridge_wifi: "UDP FEC<br>ADPCM 4:1",
            demo_bridge_idle: "Standby<br>No Stream",
            demo_waiting: "Waiting",
            m1_label: "USB Mode Latency",
            m1_desc: "Instant wired transmission via ADB Reverse + TCP_NODELAY.",
            m2_label: "Lossless Stereo PCM",
            m2_desc: "1536 kbps raw audio; zero compression loss for games, movies, and music.",
            m3_val: "Smart Isolation",
            m3_label: "Headphones-Only Output",
            m3_desc: "PC output stays silent during streaming and automatically restores on stop.",
            m4_label: "Wi-Fi Packet Recovery",
            m4_desc: "Recovers dropped wireless packets on the fly using UDP FEC.",
            route_eyebrow: "Smart Audio Routing",
            route_title: "Audio Only in Your Headphones — PC Speakers Stay Quiet",
            route_desc: "No double echo from your PC speakers or wired headset while streaming. BTBridge moves Windows output to a silent/virtual channel without altering your volume mixer and restores it automatically when done.",
            route_old_tag: "Traditional Tools",
            route_old_title: "Double Audio or Broken Mixer",
            route_old_desc: "Audio either echoes from both PC and phone at once, or force-muting Windows disrupts your system volume controls.",
            route_old_dev: "Speakers (USB)",
            route_old_state: "✕ System Muted",
            route_new_tag: "BTBridge Smart Routing",
            route_new_title: "Clean Isolation, Automatic Restore",
            route_new_desc: "BTBridge temporarily switches the default render endpoint to a virtual cable or HDMI/Monitor sink. Your PC remains silent while full audio streams to your phone.",
            route_new_dev: "Virtual / HDMI Output",
            route_new_state: "● Isolated Stream • 100%",
            rs1_title: "Automatic Sink Discovery",
            rs1_desc: "Prioritizes virtual drivers (VB-Cable, Virtual Audio, Voicemeeter) and falls back to Monitor/HDMI sinks.",
            rs2_title: "Intact Volume Mixer",
            rs2_desc: "Your Windows volume level stays untouched while WASAPI Loopback captures clean audio from the silent sink.",
            rs3_title: "Seamless Restore",
            rs3_desc: "Stopping the stream or closing the app immediately restores your previous Windows audio output.",
            vbcable_tip: "<strong>Laptop Tip:</strong> If your laptop only has a single built-in speaker with no HDMI monitor audio, install the free <code>VB-Audio Virtual Cable</code> driver — BTBridge automatically detects and routes through it.",
            feat_eyebrow: "Engineering Details",
            feat_title: "Built for Low Latency at Every Layer",
            feat_desc: "Direct streaming from Windows Core Audio to Android AudioTrack without bloated buffers or unnecessary transcoding.",
            f1_title: "10 ms WASAPI Loopback",
            f1_desc: "PyAudioWPatch capture engine grabs 48 kHz stereo PCM in 10 ms (1920-byte) frames with minimal jitter.",
            f2_title: "ADPCM + UDP FEC on Wi-Fi",
            f2_desc: "4:1 IMA-ADPCM compression paired with UDP Forward Error Correction prevents dropouts on noisy wireless networks.",
            f3_title: "Kotlin Low-Latency AudioTrack",
            f3_desc: "Android client runs with URGENT_AUDIO priority, an adaptive JitterBuffer, and 3 ms click-free smooth joins.",
            f4_title: "System Tray & Background",
            f4_desc: "Minimizes cleanly to the Windows tray. On Android, a Foreground Service keeps audio playing even with the screen off.",
            f5_title: "One-Click APK Installer",
            f5_desc: "Platform-tools ADB and BTBridge.apk come bundled — install the Android app straight from the desktop UI.",
            f6_title: "Bilingual (TR / EN) & Live VU",
            f6_desc: "Full Turkish and English support across the setup wizard, desktop app, and Android client with real-time RTT & VU meters.",
            cmp_eyebrow: "Comparison",
            cmp_title: "How Does BTBridge Compare?",
            th_feat: "Feature",
            th_usb: "BTBridge (USB)",
            th_wifi: "BTBridge (Wi-Fi)",
            th_dongle: "USB Bluetooth Dongle",
            th_other: "Generic Audio Apps",
            tr_lat: "Streaming Latency",
            tr_lat_usb: "< 10 ms (Instant)",
            tr_qual: "Audio Quality",
            tr_qual_usb: "48 kHz Lossless PCM",
            tr_qual_dongle: "SBC / AAC Compression",
            tr_qual_other: "Variable",
            tr_iso: "Automatic PC Audio Isolation",
            tr_iso_btb: "Auto (Virtual / HDMI)",
            tr_iso_btb2: "Auto (Virtual / HDMI)",
            tr_iso_dongle: "N/A",
            tr_iso_other: "Manual / Echoes",
            tr_cost: "Extra Hardware Cost",
            tr_cost_usb: "$0 (Existing USB Cable)",
            tr_cost_wifi: "$0 (Wireless)",
            tr_cost_dongle: "Requires Dongle",
            tr_cost_other: "$0",
            tr_adb: "One-Click ADB APK Install",
            tr_adb_yes: "Built-in",
            tr_adb_yes2: "Built-in",
            tr_adb_na: "N/A",
            tr_adb_man: "Manual",
            setup_eyebrow: "Quick Start",
            setup_title: "Set Up the Bridge in 2 Minutes",
            setup_desc: "Choose zero-latency wired USB mode or cable-free Local Wi-Fi.",
            tab_usb: "USB Cable (Recommended)",
            tab_wifi: "Local Wi-Fi",
            dl_eyebrow: "Verified Releases • v1.1.0",
            dl_title: "Download Center",
            dl_desc: "All builds are verified with unit/smoke tests and shipped with SHA-256 checksums.",
            win_spec_1: "Bilingual (English / Turkish) Inno Setup installation wizard",
            win_spec_2: "Bundled ADB platform-tools and BTBridge.apk included",
            win_spec_3: "Zero external Python or runtime dependencies",
            copy_btn: "Copy",
            copied_btn: "Copied",
            copy_toast: "SHA-256 checksum copied to clipboard.",
            win_dl_btn: "Download BTBridge_Setup.exe (54.6 MB)",
            win_port_btn: "Download Portable Single EXE — BTBridge.exe (35.1 MB)",
            apk_sub: "Android 8.0+ (API 26+) • v1.1.0",
            apk_spec_1: "First-launch language prompt (EN / TR) + instant header switcher",
            apk_spec_2: "Low-Latency AudioTrack, JitterBuffer + Bluetooth A2DP monitor",
            apk_spec_3: "Foreground Service keeps playback uninterrupted with screen locked",
            apk_dl_btn: "Download BTBridge.apk (15.6 MB)",
            apk_note: "Or install directly via USB using the PC app's one-click button",
            faq_eyebrow: "Frequently Asked Questions",
            faq_title: "Common Questions",
            q1: "Does it work if my PC has no Bluetooth hardware?",
            a1: "Yes! That is the exact problem BTBridge solves. Audio streams from your PC to your phone via USB or Wi-Fi, while your Bluetooth headphones remain paired to your phone.",
            q2: "Will sound still come out of my PC speakers while streaming?",
            a2: "No. BTBridge routes Windows audio to a silent virtual or HDMI/Monitor sink without altering your volume controls, and automatically restores your previous output when you stop streaming.",
            q3: "My laptop only shows a single built-in speaker. What should I do?",
            a3: "Simply install the free VB-Audio Virtual Cable driver. BTBridge automatically detects virtual sinks and prioritizes them for silent routing.",
            q4: "What is the main difference between USB and Wi-Fi modes?",
            a4: "USB (ADB Reverse) streams uncompressed 48 kHz 1536 kbps PCM with <10 ms latency. Local Wi-Fi requires no cable and uses 4:1 IMA-ADPCM compression plus UDP FEC packet recovery.",
            q5: "Do I need to install Python or Android Studio?",
            a5: "No. BTBridge_Setup.exe bundles everything needed — including the desktop app, ADB tools, and BTBridge.apk.",
            footer_brand: "BTBridge v1.1.0 • Windows PC → Android Low-Latency Audio Bridge",
            footer_license: "GPL-3.0 License",
            setup_steps: {
                usb: [
                    {
                        title: "Enable USB Debugging",
                        desc: "Turn on USB Debugging under Developer Options on your Android phone, plug it into your PC, and accept the prompt."
                    },
                    {
                        title: "Install APK & Start Streaming",
                        desc: "Open BTBridge on Windows, click \"Install APK to Phone\", then click \"Start Streaming\" (PC output is routed silently)."
                    },
                    {
                        title: "Tap Connect via USB",
                        desc: "Connect your Bluetooth headphones to your phone and tap \"Connect via USB\" in the Android app. Enjoy instant audio!"
                    }
                ],
                wifi: [
                    {
                        title: "Join the Same Wi-Fi Network",
                        desc: "Ensure both your Windows PC and Android phone are connected to the same local Wi-Fi network (or mobile hotspot)."
                    },
                    {
                        title: "Start Local Wi-Fi Mode",
                        desc: "Select \"Local Wi-Fi\" in BTBridge on PC, click \"Start Streaming\", and note the local IP address shown."
                    },
                    {
                        title: "Tap Connect via Wi-Fi",
                        desc: "Enter your PC's local IP in the BTBridge Android app and tap \"Connect via Wi-Fi\" for wireless ADPCM + UDP FEC audio."
                    }
                ]
            }
        }
    };

    var activeSetupTab = "usb";
    var bridgeState = {
        mode: "usb",
        streaming: true,
        leftVal: 66,
        rightVal: 58,
        phase: 0
    };
    var renderBridgeStateFn = null;
    var renderSetupStepsFn = null;

    function detectInitialLanguage() {
        try {
            var saved = window.localStorage.getItem(LANG_STORAGE_KEY);
            if (saved === "tr" || saved === "en") return saved;
        } catch (_e) {
            // ignore
        }
        var navLang = (navigator.language || navigator.userLanguage || "tr").toLowerCase();
        return navLang.indexOf("tr") === 0 ? "tr" : "en";
    }

    function t(key) {
        var dict = I18N[currentLang] || I18N.tr;
        return dict[key] !== undefined ? dict[key] : (I18N.tr[key] || key);
    }

    function applyLanguage(lang, persist) {
        currentLang = lang === "en" ? "en" : "tr";
        if (persist) {
            try {
                window.localStorage.setItem(LANG_STORAGE_KEY, currentLang);
            } catch (_e) {
                // ignore
            }
        }

        document.documentElement.lang = currentLang;
        document.title = t("page_title");

        document.querySelectorAll("[data-lang-btn]").forEach(function (btn) {
            var bLang = btn.getAttribute("data-lang-btn");
            btn.classList.toggle("is-active", bLang === currentLang);
        });

        document.querySelectorAll("[data-i18n]").forEach(function (el) {
            var key = el.getAttribute("data-i18n");
            if (key) {
                el.textContent = t(key);
            }
        });

        document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
            var key = el.getAttribute("data-i18n-html");
            if (key) {
                el.innerHTML = t(key);
            }
        });

        if (renderBridgeStateFn) renderBridgeStateFn();
        if (renderSetupStepsFn) renderSetupStepsFn(activeSetupTab);
    }

    function showToast(message) {
        var el = document.getElementById("toast");
        if (!el) return;
        el.textContent = message;
        el.classList.add("is-visible");
        if (toastTimer) {
            clearTimeout(toastTimer);
        }
        toastTimer = setTimeout(function () {
            el.classList.remove("is-visible");
        }, 2800);
    }

    // 1. Akıllı İndirme / GitHub Release URL Çözücü
    function resolveEnvironmentUrls() {
        var host = window.location.hostname || "";
        var proto = window.location.protocol || "";
        var pathParts = (window.location.pathname || "").split("/").filter(Boolean);

        var isLocal = proto === "file:" || host === "localhost" || host === "127.0.0.1" || host === "";
        var repoSlug = RELEASE_CONFIG.defaultGithubRepo;

        if (host.endsWith(".github.io")) {
            var owner = host.replace(".github.io", "");
            var repo = pathParts.length > 0 ? pathParts[0] : owner + ".github.io";
            repoSlug = owner + "/" + repo;
        }

        var repoUrl = "https://github.com/" + repoSlug;
        document.querySelectorAll("[data-repo-link]").forEach(function (link) {
            link.setAttribute("href", repoUrl);
        });
        document.querySelectorAll("[data-license-link]").forEach(function (link) {
            link.setAttribute("href", repoUrl + "/blob/main/LICENSE");
        });

        document.querySelectorAll("[data-asset]").forEach(function (link) {
            var asset = link.getAttribute("data-asset");
            if (!asset) return;
            if (isLocal) {
                link.setAttribute("href", "../" + asset);
                link.setAttribute("download", asset);
            } else {
                link.setAttribute("href", repoUrl + "/releases/latest/download/" + asset);
                link.removeAttribute("download");
            }
        });
    }

    // 2. Hero Canlı Köprü Önizlemesi
    function initLiveBridgeDemo() {
        var btnUsb = document.getElementById("demoModeUsb");
        var btnWifi = document.getElementById("demoModeWifi");
        var btnToggle = document.getElementById("demoToggleBtn");
        var toggleText = document.getElementById("demoToggleText");
        var statusBadge = document.getElementById("demoStatusBadge");
        var elRtt = document.getElementById("demoRtt");
        var elBitrate = document.getElementById("demoBitrate");
        var elClient = document.getElementById("demoClient");
        var elCodec = document.getElementById("demoCodecLabel");
        var elBridge = document.getElementById("demoBridge");
        var elBridgeBadge = document.getElementById("demoBridgeBadge");
        var elPhoneBadge = document.getElementById("demoPhoneBadge");
        var elPhoneBtn = document.getElementById("demoPhoneBtn");
        var elJitter = document.getElementById("demoJitter");
        var elTaskbarRoute = document.getElementById("demoTaskbarRoute");
        var elTaskbarVol = document.getElementById("demoTaskbarVol");
        var vuL = document.getElementById("vuBarL");
        var vuR = document.getElementById("vuBarR");

        if (!btnUsb || !btnWifi || !btnToggle) return;

        var prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        function renderState() {
            var isUsb = bridgeState.mode === "usb";

            btnUsb.classList.toggle("is-active", isUsb);
            btnUsb.setAttribute("aria-selected", String(isUsb));
            btnWifi.classList.toggle("is-active", !isUsb);
            btnWifi.classList.toggle("is-wifi", !isUsb);
            btnWifi.setAttribute("aria-selected", String(!isUsb));

            if (bridgeState.streaming) {
                statusBadge.textContent = t("demo_status_active");
                statusBadge.classList.remove("is-stopped");
                btnToggle.classList.remove("is-start");
                toggleText.textContent = t("demo_toggle_stop");

                elBridge.classList.remove("is-paused");
                elBridge.classList.toggle("is-wifi", !isUsb);

                elPhoneBadge.textContent = t("demo_phone_conn");
                elPhoneBadge.classList.remove("is-idle");
                elPhoneBtn.textContent = t("demo_phone_disc");
                elPhoneBtn.classList.remove("is-idle");

                elTaskbarRoute.textContent = t("demo_taskbar_active");
                elTaskbarVol.textContent = t("demo_taskbar_vol_active");

                if (isUsb) {
                    elRtt.textContent = "4.2 ms";
                    elBitrate.textContent = "1536 kbps";
                    elClient.textContent = "127.0.0.1:50005";
                    elCodec.textContent = "48 kHz Stereo PCM";
                    elBridgeBadge.innerHTML = t("demo_bridge_usb");
                    elJitter.textContent = "12 ms";
                } else {
                    elRtt.textContent = "16.8 ms";
                    elBitrate.textContent = "388 kbps";
                    elClient.textContent = "192.168.1.42:50005";
                    elCodec.textContent = "ADPCM + UDP FEC";
                    elBridgeBadge.innerHTML = t("demo_bridge_wifi");
                    elJitter.textContent = "24 ms";
                }
            } else {
                statusBadge.textContent = t("demo_status_ready");
                statusBadge.classList.add("is-stopped");
                btnToggle.classList.add("is-start");
                toggleText.textContent = t("demo_toggle_start");

                elBridge.classList.add("is-paused");
                elBridgeBadge.innerHTML = t("demo_bridge_idle");

                elPhoneBadge.textContent = t("demo_phone_wait");
                elPhoneBadge.classList.add("is-idle");
                elPhoneBtn.textContent = isUsb ? t("demo_phone_usb") : t("demo_phone_wifi");
                elPhoneBtn.classList.add("is-idle");

                elTaskbarRoute.textContent = t("demo_taskbar_restored");
                elTaskbarVol.textContent = t("demo_taskbar_vol_restored");

                elRtt.textContent = "-- ms";
                elBitrate.textContent = "0 kbps";
                elClient.textContent = t("demo_waiting");
            }
        }

        renderBridgeStateFn = renderState;

        btnUsb.addEventListener("click", function () {
            bridgeState.mode = "usb";
            renderState();
        });

        btnWifi.addEventListener("click", function () {
            bridgeState.mode = "wifi";
            renderState();
        });

        btnToggle.addEventListener("click", function () {
            bridgeState.streaming = !bridgeState.streaming;
            renderState();
        });

        function animateVu() {
            if (prefersReducedMotion) {
                vuL.style.width = bridgeState.streaming ? "64%" : "0%";
                vuR.style.width = bridgeState.streaming ? "58%" : "0%";
            } else {
                bridgeState.phase += 0.085;
                if (bridgeState.streaming) {
                    var targetL = 54 + Math.sin(bridgeState.phase) * 18 + Math.sin(bridgeState.phase * 2.3) * 12;
                    var targetR = 50 + Math.cos(bridgeState.phase * 0.92) * 18 + Math.sin(bridgeState.phase * 1.9) * 13;
                    bridgeState.leftVal += (targetL - bridgeState.leftVal) * 0.25;
                    bridgeState.rightVal += (targetR - bridgeState.rightVal) * 0.25;
                } else {
                    bridgeState.leftVal += (0 - bridgeState.leftVal) * 0.16;
                    bridgeState.rightVal += (0 - bridgeState.rightVal) * 0.16;
                }
                vuL.style.width = Math.max(0, Math.min(96, bridgeState.leftVal)).toFixed(1) + "%";
                vuR.style.width = Math.max(0, Math.min(96, bridgeState.rightVal)).toFixed(1) + "%";
            }
            window.requestAnimationFrame(animateVu);
        }

        setInterval(function () {
            if (!bridgeState.streaming) return;
            if (bridgeState.mode === "usb") {
                elRtt.textContent = (3.9 + Math.random() * 0.7).toFixed(1) + " ms";
            } else {
                elRtt.textContent = (14.5 + Math.random() * 4.7).toFixed(1) + " ms";
            }
        }, 1200);

        renderState();
        window.requestAnimationFrame(animateVu);
    }

    // 3. Kurulum Adımları Sekme Geçişi
    function initSetupTabs() {
        var tabBtns = document.querySelectorAll("[data-setup-tab]");
        var t1 = document.getElementById("stepTitle1");
        var d1 = document.getElementById("stepDesc1");
        var t2 = document.getElementById("stepTitle2");
        var d2 = document.getElementById("stepDesc2");
        var t3 = document.getElementById("stepTitle3");
        var d3 = document.getElementById("stepDesc3");

        if (!tabBtns.length || !t1) return;

        function renderSteps(key) {
            activeSetupTab = key === "wifi" ? "wifi" : "usb";
            var dict = I18N[currentLang] || I18N.tr;
            var steps = dict.setup_steps[activeSetupTab];
            if (!steps) return;

            tabBtns.forEach(function (b) {
                var active = b.getAttribute("data-setup-tab") === activeSetupTab;
                b.classList.toggle("is-active", active);
                b.setAttribute("aria-selected", String(active));
            });

            t1.textContent = steps[0].title;
            d1.textContent = steps[0].desc;
            t2.textContent = steps[1].title;
            d2.textContent = steps[1].desc;
            t3.textContent = steps[2].title;
            d3.textContent = steps[2].desc;
        }

        renderSetupStepsFn = renderSteps;

        tabBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                renderSteps(btn.getAttribute("data-setup-tab"));
            });
        });
    }

    // 4. Tek Tıkla SHA-256 Kopyalama
    function initHashCopyButtons() {
        document.querySelectorAll("[data-copy-hash]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var hash = btn.getAttribute("data-copy-hash") || "";
                if (!hash) return;

                function onCopied() {
                    btn.textContent = t("copied_btn");
                    showToast(t("copy_toast"));
                    setTimeout(function () {
                        btn.textContent = t("copy_btn");
                    }, 1800);
                }

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(hash).then(onCopied).catch(function () {
                        fallbackCopy(hash);
                        onCopied();
                    });
                } else {
                    fallbackCopy(hash);
                    onCopied();
                }
            });
        });
    }

    function fallbackCopy(text) {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {
            document.execCommand("copy");
        } catch (_err) {
            // ignore
        }
        document.body.removeChild(ta);
    }

    // 5. Mobil Menü, Dil Geçişi, SSS Akordeon & Scroll Reveal
    function initLanguageSwitchers() {
        document.querySelectorAll("[data-lang-btn]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var chosen = btn.getAttribute("data-lang-btn");
                if (chosen) {
                    applyLanguage(chosen, true);
                }
            });
        });
    }

    function initNavigationAndFaq() {
        var menuBtn = document.getElementById("menuToggle");
        var drawer = document.getElementById("mobileDrawer");

        if (menuBtn && drawer) {
            menuBtn.addEventListener("click", function () {
                var isOpen = drawer.classList.toggle("is-open");
                menuBtn.setAttribute("aria-expanded", String(isOpen));
            });

            drawer.querySelectorAll("a").forEach(function (a) {
                a.addEventListener("click", function () {
                    drawer.classList.remove("is-open");
                    menuBtn.setAttribute("aria-expanded", "false");
                });
            });
        }

        var faqItems = document.querySelectorAll(".faq-item");
        faqItems.forEach(function (item) {
            var qBtn = item.querySelector(".faq-q");
            if (!qBtn) return;
            qBtn.addEventListener("click", function () {
                var willOpen = !item.classList.contains("is-open");
                faqItems.forEach(function (other) {
                    other.classList.remove("is-open");
                    var oBtn = other.querySelector(".faq-q");
                    if (oBtn) oBtn.setAttribute("aria-expanded", "false");
                });
                if (willOpen) {
                    item.classList.add("is-open");
                    qBtn.setAttribute("aria-expanded", "true");
                }
            });
        });
    }

    function initScrollReveal() {
        document.documentElement.classList.add("js-ready");
        var reveals = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
        if (!reveals.length) return;

        function checkVisible() {
            var vh = window.innerHeight || document.documentElement.clientHeight || 800;
            reveals = reveals.filter(function (el) {
                var rect = el.getBoundingClientRect();
                if (rect.top <= vh + 120) {
                    el.classList.add("is-visible");
                    return false;
                }
                return true;
            });
        }

        if ("IntersectionObserver" in window) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.0, rootMargin: "120px 0px" });

            reveals.forEach(function (el) {
                observer.observe(el);
            });
        }

        window.addEventListener("scroll", checkVisible, { passive: true });
        window.addEventListener("resize", checkVisible, { passive: true });
        checkVisible();
    }

    document.addEventListener("DOMContentLoaded", function () {
        resolveEnvironmentUrls();
        initLiveBridgeDemo();
        initSetupTabs();
        initHashCopyButtons();
        initLanguageSwitchers();
        initNavigationAndFaq();
        initScrollReveal();
        applyLanguage(detectInitialLanguage(), false);
    });
})();
