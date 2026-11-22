/* ==========================================================================
   BTBridge Web Uygulaması — Etkileşim, Canlı Köprü Simülasyonu & Release Bağlantısı
   ========================================================================== */

(function () {
    "use strict";

    var RELEASE_CONFIG = {
        defaultGithubRepo: "BtbBridge/btbridge"
    };

    var toastTimer = null;

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
        var repoLinks = document.querySelectorAll("[data-repo-link]");
        repoLinks.forEach(function (link) {
            link.setAttribute("href", repoUrl);
        });

        var assetLinks = document.querySelectorAll("[data-asset]");
        assetLinks.forEach(function (link) {
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

        var state = {
            mode: "usb",
            streaming: true,
            leftVal: 66,
            rightVal: 58,
            phase: 0
        };

        var prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        function renderState() {
            var isUsb = state.mode === "usb";

            btnUsb.classList.toggle("is-active", isUsb);
            btnUsb.setAttribute("aria-selected", String(isUsb));
            btnWifi.classList.toggle("is-active", !isUsb);
            btnWifi.classList.toggle("is-wifi", !isUsb);
            btnWifi.setAttribute("aria-selected", String(!isUsb));

            if (state.streaming) {
                statusBadge.textContent = "● Yayın Aktif";
                statusBadge.classList.remove("is-stopped");
                btnToggle.classList.remove("is-start");
                toggleText.textContent = "Yayını Durdur";

                elBridge.classList.remove("is-paused");
                elBridge.classList.toggle("is-wifi", !isUsb);

                elPhoneBadge.textContent = "Bağlandı";
                elPhoneBadge.classList.remove("is-idle");
                elPhoneBtn.textContent = "Bağlantıyı Kes";
                elPhoneBtn.classList.remove("is-idle");

                elTaskbarRoute.textContent = "Aktif Çıkış: Sanal / HDMI Kanal";
                elTaskbarVol.textContent = "PC Sessiz • Yayın Aktif";

                if (isUsb) {
                    elRtt.textContent = "4.2 ms";
                    elBitrate.textContent = "1536 kbps";
                    elClient.textContent = "127.0.0.1:50005";
                    elCodec.textContent = "48 kHz Stereo PCM";
                    elBridgeBadge.innerHTML = "TCP 50005<br>PCM Akışı";
                    elJitter.textContent = "12 ms";
                } else {
                    elRtt.textContent = "16.8 ms";
                    elBitrate.textContent = "388 kbps";
                    elClient.textContent = "192.168.1.42:50005";
                    elCodec.textContent = "ADPCM + UDP FEC";
                    elBridgeBadge.innerHTML = "UDP FEC<br>ADPCM 4:1";
                    elJitter.textContent = "24 ms";
                }
            } else {
                statusBadge.textContent = "● Hazır";
                statusBadge.classList.add("is-stopped");
                btnToggle.classList.add("is-start");
                toggleText.textContent = "Yayını Başlat";

                elBridge.classList.add("is-paused");
                elBridgeBadge.innerHTML = "Beklemede<br>Akış Yok";

                elPhoneBadge.textContent = "Bekleniyor";
                elPhoneBadge.classList.add("is-idle");
                elPhoneBtn.textContent = isUsb ? "USB ile Bağlan" : "Wi-Fi ile Bağlan";
                elPhoneBtn.classList.add("is-idle");

                elTaskbarRoute.textContent = "Orijinal Çıkışa Döndü: Hoparlör (USB)";
                elTaskbarVol.textContent = "Ses: %100";

                elRtt.textContent = "-- ms";
                elBitrate.textContent = "0 kbps";
                elClient.textContent = "Bekleniyor";
            }
        }

        btnUsb.addEventListener("click", function () {
            state.mode = "usb";
            renderState();
        });

        btnWifi.addEventListener("click", function () {
            state.mode = "wifi";
            renderState();
        });

        btnToggle.addEventListener("click", function () {
            state.streaming = !state.streaming;
            renderState();
        });

        // 60 FPS Stereo VU Metre Animasyonu
        function animateVu() {
            if (prefersReducedMotion) {
                vuL.style.width = state.streaming ? "64%" : "0%";
                vuR.style.width = state.streaming ? "58%" : "0%";
            } else {
                state.phase += 0.085;
                if (state.streaming) {
                    var targetL = 54 + Math.sin(state.phase) * 18 + Math.sin(state.phase * 2.3) * 12;
                    var targetR = 50 + Math.cos(state.phase * 0.92) * 18 + Math.sin(state.phase * 1.9) * 13;
                    state.leftVal += (targetL - state.leftVal) * 0.25;
                    state.rightVal += (targetR - state.rightVal) * 0.25;
                } else {
                    state.leftVal += (0 - state.leftVal) * 0.16;
                    state.rightVal += (0 - state.rightVal) * 0.16;
                }
                vuL.style.width = Math.max(0, Math.min(96, state.leftVal)).toFixed(1) + "%";
                vuR.style.width = Math.max(0, Math.min(96, state.rightVal)).toFixed(1) + "%";
            }
            window.requestAnimationFrame(animateVu);
        }

        // Her 1.2 saniyede gerçekçi küçük RTT dalgalanması
        setInterval(function () {
            if (!state.streaming) return;
            if (state.mode === "usb") {
                var usbRtt = (3.9 + Math.random() * 0.7).toFixed(1);
                elRtt.textContent = usbRtt + " ms";
            } else {
                var wifiRtt = (14.5 + Math.random() * 4.7).toFixed(1);
                elRtt.textContent = wifiRtt + " ms";
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

        var copyMap = {
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
        };

        tabBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var key = btn.getAttribute("data-setup-tab");
                var steps = copyMap[key];
                if (!steps) return;

                tabBtns.forEach(function (b) {
                    var active = b === btn;
                    b.classList.toggle("is-active", active);
                    b.setAttribute("aria-selected", String(active));
                });

                t1.textContent = steps[0].title;
                d1.textContent = steps[0].desc;
                t2.textContent = steps[1].title;
                d2.textContent = steps[1].desc;
                t3.textContent = steps[2].title;
                d3.textContent = steps[2].desc;
            });
        });
    }

    // 4. Tek Tıkla SHA-256 Kopyalama
    function initHashCopyButtons() {
        var buttons = document.querySelectorAll("[data-copy-hash]");
        buttons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var hash = btn.getAttribute("data-copy-hash") || "";
                if (!hash) return;

                function onCopied() {
                    var orig = btn.textContent;
                    btn.textContent = "Kopyalandı";
                    showToast("SHA-256 doğrulama özeti panoya kopyalandı.");
                    setTimeout(function () {
                        btn.textContent = orig;
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

    // 5. Mobil Menü, SSS Akordeon & Scroll Reveal
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
        initNavigationAndFaq();
        initScrollReveal();
    });
})();
