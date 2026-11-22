# BTBridge İkili Ses ve Kontrol Protokolü (v1)

BTBridge, Windows PC (`pc-server`) ile Android istemci (`android-client`) arasında minimum gecikmeli canlı ses akışı ve RTT ölçümü için tasarlanmış basit, sabit başlıklı bir TCP ikili protokolü kullanır.

---

## 1. Ses Biçimi (PCM)

| Parametre | Değer |
| :--- | :--- |
| Örnekleme Hızı (Sample Rate) | `48000 Hz` |
| Örnek Çözünürlüğü (Bit Depth) | `16-bit Signed PCM` |
| Kanal Sayısı | `2` (Stereo, interleaved: `L0, R0, L1, R1, ...`) |
| Bayt Sırası (Audio Payload) | `Little-Endian` (`<i2`) |
| Kare Süresi (Frame Duration) | `10 ms` |
| Kare Başına Stereo Örnek | `480` stereo kare (`960` toplam kanal örneği) |
| Ham Ses Yükü (Payload) | `1920 byte` (`480 * 2 * 2 byte`) |
| Ham Ses Bit Hızı | `1536 kbps` (~`1550 kbps` 17 byte başlık dahil) |

---

## 2. Taşıma ve Bağlantı Modları

- **Protokol:** TCP
- **Varsayılan Port:** `50005`
- **Soket Seçenekleri:**
  - `TCP_NODELAY = true` (Nagle algoritması her iki uçta da kesinlikle kapalıdır).
  - Tamponlama gecikmesini (bufferbloat) önlemek için sınırlı `SO_SNDBUF` / `SO_RCVBUF` (`32768 byte`).
- **Bağlantı Modları:**
  1. **Birincil Mod — USB (ADB Reverse):**
     - PC uygulaması `adb reverse tcp:50005 tcp:50005` komutunu çalıştırır ve `127.0.0.1:50005` adresini dinler.
     - Android istemcisi doğrudan `127.0.0.1:50005` adresine bağlanır; trafik USB kablosu üzerinden sıfıra yakın gecikmeyle akar.
  2. **İkincil Mod — Yerel Wi-Fi:**
     - PC uygulaması `0.0.0.0:50005` adresini dinler.
     - Android istemcisi kullanıcının girdiği `<PC_YEREL_IP>:50005` adresine bağlanır.

---

## 3. Paket Çerçeveleme (17-Byte Header + Payload)

Tüm paket başlık alanları **Big-Endian (Network Byte Order)** düzenindedir. Python `struct` formatı: `">HBIQH"` (`17 byte`).

| Ofset (Byte) | Uzunluk | Tip | Alan | Açıklama |
| :--- | :--- | :--- | :--- | :--- |
| `0..1` | 2 Byte | `uint16` | `Magic` | Sabit `0xB7B7` paket imzası |
| `2` | 1 Byte | `uint8` | `Type` | `1 = Audio PCM`, `2 = Ping`, `3 = Pong`, `4 = Audio ADPCM`, `5 = UDP Hello`, `6 = Audio ADPCM FEC` |
| `3..6` | 4 Byte | `uint32` | `Seq` | Artan paket sıra numarası |
| `7..14` | 8 Byte | `uint64` | `TimestampMs` | Gönderenin monotonik saati (ms) |
| `15..16` | 2 Byte | `uint16` | `PayloadLen` | Yük uzunluğu (`Audio=1920`, `ADPCM=486`, `ADPCM_FEC=972`, `Ping/Pong/Hello=0`) |
| `17..` | `PayloadLen` | `bytes` | `Payload` | Ses yükü veya kontrol için boş |

### Wi-Fi Sıkıştırılmış Ses ve UDP FEC Ekleri

- **Type `4` (`MSG_AUDIO_ADPCM`, `486 byte`):**
  - `0..5`: `<hBhB` (Little-Endian) -> `pred_L (int16)`, `idx_L (uint8)`, `pred_R (int16)`, `idx_R (uint8)`
  - `6..245`: `240 byte` Sol kanal IMA ADPCM (480 örnek, byte başına yüksek nibble önce)
  - `246..485`: `240 byte` Sağ kanal IMA ADPCM (480 örnek)
- **Type `5` (`MSG_UDP_HELLO`, `0 byte`):** Android istemcisinin Wi-Fi modunda UDP `50005` portunu kaydettirmek ve canlı tutmak için gönderdiği paket.
- **Type `6` (`MSG_AUDIO_ADPCM_FEC`, `972 byte`):** `486B` mevcut kare (`Seq`) + `486B` bir önceki kare (`Seq - 1`). Tekil UDP paket kayıplarını ek gecikme olmadan onarır.

---

## 4. Simetrik Ping/Pong Gidiş-Dönüş Gecikmesi (RTT) Ölçümü

Saat kaymasından (clock skew) bağımsız gerçek gidiş-dönüş gecikmesini ölçmek için her iki uç da kendi monotonik saatini kullanır:

1. Gönderen taraf her `1000 ms`'de bir `Type = 2 (Ping)`, `PayloadLen = 0` ve kendi `TimestampMs` değerini içeren bir paket gönderir.
2. Alıcı taraf `Ping` paketini aldığı anda aynı `Seq` ve `TimestampMs` değerlerini koruyarak `Type = 3 (Pong)`, `PayloadLen = 0` yanıtını gönderir.
3. İlk gönderen taraf `Pong` paketini aldığında kendi güncel monotonik saatinden paketteki `TimestampMs` değerini çıkararak gecikmeyi hesaplar:
   ```text
   RTT_ms = localNowMonotonicMs - pong.TimestampMs
   ```
4. Hesaplanan `RTT_ms` değeri hem PC hem de Android arayüzünde canlı olarak gösterilir.
