package com.btbridge.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.os.Process
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.btbridge.app.R
import com.btbridge.app.audio.JitterBuffer
import com.btbridge.app.audio.JitterProfile
import com.btbridge.app.audio.LowLatencyAudioPlayer
import com.btbridge.app.protocol.BridgeProtocol
import com.btbridge.app.protocol.ImaAdpcmDecoder
import com.btbridge.app.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.BufferedInputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.atomic.AtomicLong

class AudioBridgeService : Service() {

    companion object {
        const val ACTION_START = "com.btbridge.app.action.START"
        const val ACTION_STOP = "com.btbridge.app.action.STOP"
        const val ACTION_SET_PROFILE = "com.btbridge.app.action.SET_PROFILE"

        const val EXTRA_HOST = "extra_host"
        const val EXTRA_PORT = "extra_port"
        const val EXTRA_MODE = "extra_mode"
        const val EXTRA_PROFILE_ID = "extra_profile_id"

        private const val CHANNEL_ID = "btbridge_playback_channel"
        private const val NOTIFICATION_ID = 1001

        fun startBridge(
            context: Context,
            mode: ConnectionMode,
            host: String,
            port: Int,
            profile: JitterProfile,
        ) {
            val intent = Intent(context, AudioBridgeService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_MODE, mode.name)
                putExtra(EXTRA_HOST, host)
                putExtra(EXTRA_PORT, port)
                putExtra(EXTRA_PROFILE_ID, profile.id)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stopBridge(context: Context) {
            val intent = Intent(context, AudioBridgeService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }

        fun setProfile(context: Context, profile: JitterProfile) {
            val intent = Intent(context, AudioBridgeService::class.java).apply {
                action = ACTION_SET_PROFILE
                putExtra(EXTRA_PROFILE_ID, profile.id)
            }
            context.startService(intent)
        }
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var jitterBuffer: JitterBuffer
    private lateinit var audioPlayer: LowLatencyAudioPlayer
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    private var connectionJob: Job? = null

    @Volatile
    private var activeSocket: Socket? = null

    @Volatile
    private var activeUdpSocket: DatagramSocket? = null

    @Volatile
    private var shouldRun: Boolean = false

    override fun onCreate() {
        super.onCreate()
        BridgeStateRepository.loadPreferences(this)
        jitterBuffer = JitterBuffer(BridgeStateRepository.state.value.jitterProfile)
        audioPlayer = LowLatencyAudioPlayer(jitterBuffer)
        createNotificationChannel()

        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BTBridge:AudioWakeLock").apply {
            setReferenceCounted(false)
        }

        val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        if (wm != null) {
            val lockMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                WifiManager.WIFI_MODE_FULL_LOW_LATENCY
            } else {
                @Suppress("DEPRECATION")
                WifiManager.WIFI_MODE_FULL_HIGH_PERF
            }
            wifiLock = wm.createWifiLock(lockMode, "BTBridge:WifiLowLatency").apply {
                setReferenceCounted(false)
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopAllAndFinish()
                return START_NOT_STICKY
            }

            ACTION_SET_PROFILE -> {
                val profile = JitterProfile.fromId(intent.getStringExtra(EXTRA_PROFILE_ID))
                jitterBuffer.setProfile(profile)
                BridgeStateRepository.updateJitterProfile(this, profile)
                return START_STICKY
            }

            ACTION_START, null -> {
                val modeName = intent?.getStringExtra(EXTRA_MODE) ?: ConnectionMode.USB.name
                val mode = runCatching { ConnectionMode.valueOf(modeName) }.getOrDefault(ConnectionMode.USB)
                val host = intent?.getStringExtra(EXTRA_HOST)?.trim().orEmpty().ifEmpty { "127.0.0.1" }
                val port = intent?.getIntExtra(EXTRA_PORT, BridgeProtocol.DEFAULT_PORT)
                    ?: BridgeProtocol.DEFAULT_PORT
                val profile = JitterProfile.fromId(
                    intent?.getStringExtra(EXTRA_PROFILE_ID)
                        ?: BridgeStateRepository.state.value.jitterProfile.id,
                )

                jitterBuffer.setNetworkMode(mode == ConnectionMode.WIFI)
                jitterBuffer.setProfile(profile)
                BridgeStateRepository.updateJitterProfile(this, profile)
                startForegroundCompat("Bağlantı başlatılıyor ($host:$port)...")

                if (wakeLock?.isHeld == false) {
                    wakeLock?.acquire(12 * 60 * 60 * 1000L)
                }
                if (mode == ConnectionMode.WIFI) {
                    if (wifiLock?.isHeld == false) {
                        runCatching { wifiLock?.acquire() }
                    }
                } else {
                    if (wifiLock?.isHeld == true) {
                        runCatching { wifiLock?.release() }
                    }
                }

                audioPlayer.start()
                shouldRun = true
                connectionJob?.cancel()
                closeActiveSockets()
                connectionJob = serviceScope.launch {
                    runConnectionLoop(mode, host, port)
                }
                return START_STICKY
            }

            else -> return START_NOT_STICKY
        }
    }

    private suspend fun runConnectionLoop(mode: ConnectionMode, host: String, port: Int) {
        var firstAttempt = true
        var backoffMs = 300L
        while (shouldRun && serviceScope.isActive) {
            val status = if (firstAttempt) ConnectionStatus.CONNECTING else ConnectionStatus.RECONNECTING
            val msg = if (firstAttempt) {
                "Sunucuya bağlanılıyor ($host:$port)..."
            } else {
                "Yeniden bağlanılıyor ($host:$port)..."
            }
            BridgeStateRepository.updateStatus(status, mode, msg)
            updateNotification(msg)
            firstAttempt = false

            val sessionStart = SystemClock.elapsedRealtime()
            try {
                streamSession(mode, host, port)
            } catch (_: Throwable) {
                // Yeniden bağlanma döngüsü hata sonrası otomatik devam eder
            } finally {
                jitterBuffer.clear()
                closeActiveSockets()
            }

            val sessionDuration = SystemClock.elapsedRealtime() - sessionStart
            backoffMs = if (sessionDuration > 3000L) {
                300L
            } else {
                (backoffMs * 2L).coerceAtMost(1200L)
            }

            if (shouldRun) {
                delay(backoffMs)
            }
        }
    }

    private suspend fun streamSession(mode: ConnectionMode, host: String, port: Int) {
        runCatching { Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO) }

        val socket = Socket()
        activeSocket = socket
        socket.tcpNoDelay = true
        socket.keepAlive = true
        runCatching { socket.trafficClass = 0xB8 } // DSCP EF (Voice)
        socket.receiveBufferSize = if (mode == ConnectionMode.WIFI) 131072 else 65536
        socket.sendBufferSize = 32768
        socket.soTimeout = 10000
        socket.connect(InetSocketAddress(host, port), 3000)

        val modeLabel = if (mode == ConnectionMode.USB) "USB Köprüsü" else "Wi-Fi TCP+ADPCM ($host)"
        BridgeStateRepository.updateStatus(ConnectionStatus.CONNECTED, mode, "Bağlı • $modeLabel")
        updateNotification("Bağlı • $modeLabel")

        val input = BufferedInputStream(socket.getInputStream(), 16384)
        val output = socket.getOutputStream()
        val controlChannel = Channel<ByteArray>(
            capacity = 32,
            onBufferOverflow = BufferOverflow.DROP_OLDEST,
        )

        val writerJob = serviceScope.launch {
            try {
                for (pkt in controlChannel) {
                    if (!shouldRun || socket.isClosed) break
                    output.write(pkt)
                    output.flush()
                }
            } catch (_: Throwable) {
                closeActiveSockets()
            }
        }

        val pingJob = serviceScope.launch {
            var pingSeq = 0L
            while (isActive && shouldRun && !socket.isClosed) {
                pingSeq = (pingSeq + 1L) and 0xFFFFFFFFL
                val now = SystemClock.elapsedRealtime()
                val pingBuf = ByteArray(BridgeProtocol.HEADER_SIZE)
                BridgeProtocol.encodeHeader(pingBuf, BridgeProtocol.TYPE_PING, pingSeq, now, 0)
                controlChannel.trySend(pingBuf)
                delay(1000L)
            }
        }

        val udpBytesAccum = AtomicLong(0L)
        var udpJob: Job? = null
        if (mode == ConnectionMode.WIFI) {
            udpJob = launchWifiUdpReceiver(host, port, socket, udpBytesAccum)
        }

        val headerBuf = ByteArray(BridgeProtocol.HEADER_SIZE)
        val payloadBuf = ByteArray(BridgeProtocol.MAX_PAYLOAD_LEN)
        val pcmDecodeBuf = ByteArray(BridgeProtocol.FRAME_BYTES)
        val header = BridgeProtocol.PacketHeader()

        var tcpBytesInWindow = 0L
        var windowStartMs = SystemClock.elapsedRealtime()

        try {
            while (shouldRun && !socket.isClosed) {
                BridgeProtocol.readFully(input, headerBuf, BridgeProtocol.HEADER_SIZE)

                if (!BridgeProtocol.decodeHeader(headerBuf, header)) {
                    throw IllegalStateException("Geçersiz protokol başlığı")
                }

                if (header.payloadLen > 0) {
                    BridgeProtocol.readFully(input, payloadBuf, header.payloadLen)
                }

                when (header.type) {
                    BridgeProtocol.TYPE_AUDIO -> {
                        jitterBuffer.write(payloadBuf, 0, header.payloadLen)
                        tcpBytesInWindow += (BridgeProtocol.HEADER_SIZE + header.payloadLen).toLong()
                    }

                    BridgeProtocol.TYPE_AUDIO_ADPCM -> {
                        if (header.payloadLen == BridgeProtocol.ADPCM_FRAME_BYTES &&
                            ImaAdpcmDecoder.decodeFrame(payloadBuf, 0, pcmDecodeBuf)
                        ) {
                            jitterBuffer.write(pcmDecodeBuf, 0, BridgeProtocol.FRAME_BYTES)
                        }
                        tcpBytesInWindow += (BridgeProtocol.HEADER_SIZE + header.payloadLen).toLong()
                    }

                    BridgeProtocol.TYPE_PING -> {
                        val pongBuf = ByteArray(BridgeProtocol.HEADER_SIZE)
                        BridgeProtocol.encodeHeader(
                            pongBuf,
                            BridgeProtocol.TYPE_PONG,
                            header.seq,
                            header.timestampMs,
                            0,
                        )
                        controlChannel.trySend(pongBuf)
                    }

                    BridgeProtocol.TYPE_PONG -> {
                        val rtt = (SystemClock.elapsedRealtime() - header.timestampMs).coerceAtLeast(0L)
                        BridgeStateRepository.updateTelemetry(
                            latencyMs = rtt,
                            bufferFillMs = jitterBuffer.bufferedMs(),
                        )
                    }
                }

                val nowMs = SystemClock.elapsedRealtime()
                val elapsed = nowMs - windowStartMs
                if (elapsed >= 1000L) {
                    val totalBytes = tcpBytesInWindow + udpBytesAccum.getAndSet(0L)
                    val kbps = ((totalBytes * 8.0) / elapsed).toInt()
                    val fillMs = jitterBuffer.bufferedMs()
                    BridgeStateRepository.updateTelemetry(
                        bitrateKbps = kbps,
                        bufferFillMs = fillMs,
                    )
                    tcpBytesInWindow = 0L
                    windowStartMs = nowMs
                }
            }
        } finally {
            udpJob?.cancel()
            pingJob.cancel()
            controlChannel.close()
            writerJob.cancel()
        }
    }

    private fun launchWifiUdpReceiver(
        host: String,
        port: Int,
        tcpSocket: Socket,
        udpBytesAccum: AtomicLong,
    ): Job = serviceScope.launch {
        runCatching { Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO) }
        val udpSocket = DatagramSocket()
        activeUdpSocket = udpSocket
        runCatching {
            udpSocket.receiveBufferSize = 131072
            udpSocket.trafficClass = 0xB8
            udpSocket.soTimeout = 1500
        }

        val remoteAddr = InetSocketAddress(host, port)
        val helloJob = launch {
            val helloBuf = ByteArray(BridgeProtocol.HEADER_SIZE)
            var helloSeq = 0L
            while (isActive && shouldRun && !tcpSocket.isClosed && !udpSocket.isClosed) {
                helloSeq = (helloSeq + 1L) and 0xFFFFFFFFL
                BridgeProtocol.encodeHeader(
                    helloBuf,
                    BridgeProtocol.TYPE_UDP_HELLO,
                    helloSeq,
                    SystemClock.elapsedRealtime(),
                    0,
                )
                runCatching {
                    udpSocket.send(DatagramPacket(helloBuf, helloBuf.size, remoteAddr))
                }
                val nextDelay = if (helloSeq <= 3L) 100L else 2000L
                delay(nextDelay)
            }
        }

        val rxBuf = ByteArray(BridgeProtocol.HEADER_SIZE + BridgeProtocol.MAX_PAYLOAD_LEN)
        val rxPacket = DatagramPacket(rxBuf, rxBuf.size)
        val hdr = BridgeProtocol.PacketHeader()
        val pcmBuf = ByteArray(BridgeProtocol.FRAME_BYTES)
        var lastUdpSeq = -1L
        var udpActiveAnnounced = false

        try {
            while (isActive && shouldRun && !tcpSocket.isClosed && !udpSocket.isClosed) {
                try {
                    udpSocket.receive(rxPacket)
                } catch (_: SocketTimeoutException) {
                    continue
                }
                val len = rxPacket.length
                if (len < BridgeProtocol.HEADER_SIZE) continue
                if (!BridgeProtocol.decodeHeader(rxBuf, hdr)) continue
                if (len < BridgeProtocol.HEADER_SIZE + hdr.payloadLen) continue

                val seq = hdr.seq
                if (hdr.type == BridgeProtocol.TYPE_AUDIO_ADPCM_FEC &&
                    hdr.payloadLen == BridgeProtocol.ADPCM_FEC_BYTES
                ) {
                    if (lastUdpSeq >= 0L && seq <= lastUdpSeq) {
                        continue
                    }
                    // Tek paket kaybında (seq == lastUdpSeq + 2) önceki yedek kareyi öne alıp kurtar
                    if (lastUdpSeq >= 0L && seq >= lastUdpSeq + 2L) {
                        val prevOffset = BridgeProtocol.HEADER_SIZE + BridgeProtocol.ADPCM_FRAME_BYTES
                        if (ImaAdpcmDecoder.decodeFrame(rxBuf, prevOffset, pcmBuf)) {
                            jitterBuffer.write(pcmBuf, 0, BridgeProtocol.FRAME_BYTES)
                        }
                    }
                    if (ImaAdpcmDecoder.decodeFrame(rxBuf, BridgeProtocol.HEADER_SIZE, pcmBuf)) {
                        jitterBuffer.write(pcmBuf, 0, BridgeProtocol.FRAME_BYTES)
                    }
                    lastUdpSeq = seq
                    udpBytesAccum.addAndGet(len.toLong())
                } else if (hdr.type == BridgeProtocol.TYPE_AUDIO_ADPCM &&
                    hdr.payloadLen == BridgeProtocol.ADPCM_FRAME_BYTES
                ) {
                    if (lastUdpSeq >= 0L && seq <= lastUdpSeq) {
                        continue
                    }
                    if (ImaAdpcmDecoder.decodeFrame(rxBuf, BridgeProtocol.HEADER_SIZE, pcmBuf)) {
                        jitterBuffer.write(pcmBuf, 0, BridgeProtocol.FRAME_BYTES)
                    }
                    lastUdpSeq = seq
                    udpBytesAccum.addAndGet(len.toLong())
                } else {
                    continue
                }

                if (!udpActiveAnnounced) {
                    udpActiveAnnounced = true
                    BridgeStateRepository.updateStatus(
                        ConnectionStatus.CONNECTED,
                        ConnectionMode.WIFI,
                        "Bağlı • Wi-Fi UDP+FEC (ADPCM)",
                    )
                }
            }
        } catch (_: Throwable) {
            // Soket kapanınca temiz çıkış
        } finally {
            helloJob.cancel()
            if (activeUdpSocket === udpSocket) {
                activeUdpSocket = null
            }
            runCatching { udpSocket.close() }
        }
    }

    private fun closeActiveSockets() {
        val sock = activeSocket
        activeSocket = null
        if (sock != null) {
            runCatching { sock.close() }
        }
        val udpSock = activeUdpSocket
        activeUdpSocket = null
        if (udpSock != null) {
            runCatching { udpSock.close() }
        }
    }

    private fun stopAllAndFinish() {
        shouldRun = false
        connectionJob?.cancel()
        connectionJob = null
        closeActiveSockets()
        audioPlayer.stop()
        jitterBuffer.clear()
        if (wifiLock?.isHeld == true) {
            runCatching { wifiLock?.release() }
        }
        BridgeStateRepository.updateStatus(
            ConnectionStatus.DISCONNECTED,
            statusMessage = "Bağlantı durduruldu",
        )
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun startForegroundCompat(contentText: String) {
        val notification = buildNotification(contentText)
        val fgType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
        } else {
            0
        }
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, fgType)
    }

    private fun updateNotification(contentText: String) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIFICATION_ID, buildNotification(contentText))
    }

    private fun buildNotification(contentText: String): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val openPendingIntent = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val stopIntent = Intent(this, AudioBridgeService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this,
            1,
            stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("BTBridge Ses Köprüsü")
            .setContentText(contentText)
            .setContentIntent(openPendingIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .addAction(0, "Durdur", stopPendingIntent)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "BTBridge Ses Akışı",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "PC'den telefona canlı ses akışı durumu"
                setShowBadge(false)
            }
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        shouldRun = false
        connectionJob?.cancel()
        closeActiveSockets()
        audioPlayer.stop()
        serviceScope.cancel()
        if (wifiLock?.isHeld == true) {
            runCatching { wifiLock?.release() }
        }
        if (wakeLock?.isHeld == true) {
            runCatching { wakeLock?.release() }
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
