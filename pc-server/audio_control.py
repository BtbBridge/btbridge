"""Pure-ctypes Windows Core Audio (MMDevice / IAudioEndpointVolume / IPolicyConfig) kontrol modülü."""

from __future__ import annotations

import atexit
import ctypes
from ctypes import POINTER, Structure, byref, c_float, c_int, c_uint16, c_uint32, c_uint64, c_void_p, c_wchar_p
from dataclasses import dataclass
from typing import Optional
import uuid

# Varsayılan strateji: Görev çubuğunda kırmızı çarpı / mute çıkarmamak için
# dahili hoparlör / USB kulaklık yerine sessiz/sanal çıkışa (HDMI, Monitor, VB-Cable, Virtual Audio) yönlendirme.
DEFAULT_SILENCE_STRATEGY = "route_silent"

_COINIT_MULTITHREADED = 0x0
_CLSCTX_ALL = 23
_E_RENDER = 0
_E_CONSOLE = 0
_E_MULTIMEDIA = 1
_E_COMMUNICATIONS = 2
_DEVICE_STATE_ACTIVE = 1
_STGM_READ = 0
_VT_LPWSTR = 31

_ENDPOINT_HARDWARE_SUPPORT_VOLUME = 0x1
_ENDPOINT_HARDWARE_SUPPORT_MUTE = 0x2

_ole32 = ctypes.OleDLL("ole32")


class _GUID(Structure):
    _fields_ = [
        ("Data1", c_uint32),
        ("Data2", c_uint16),
        ("Data3", c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, value: str) -> "_GUID":
        u = uuid.UUID(value)
        b = u.bytes_le
        data4 = (ctypes.c_ubyte * 8)(*b[8:16])
        return cls(
            int.from_bytes(b[0:4], "little"),
            int.from_bytes(b[4:6], "little"),
            int.from_bytes(b[6:8], "little"),
            data4,
        )


class _PROPERTYKEY(Structure):
    _fields_ = [
        ("fmtid", _GUID),
        ("pid", c_uint32),
    ]


class _PROPVARIANT(Structure):
    _fields_ = [
        ("vt", c_uint16),
        ("wReserved1", c_uint16),
        ("wReserved2", c_uint16),
        ("wReserved3", c_uint16),
        ("val", c_void_p),
        ("pad", c_uint64),
    ]


_CLSID_MMDeviceEnumerator = _GUID.from_uuid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
_IID_IMMDeviceEnumerator = _GUID.from_uuid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
_IID_IAudioEndpointVolume = _GUID.from_uuid("{5CDF2C82-841E-4546-9722-0CF74078229A}")
_CLSID_CPolicyConfigClient = _GUID.from_uuid("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")
_IID_IPolicyConfig = _GUID.from_uuid("{F8679F50-850A-41CF-9C72-430F290290C8}")
_PKEY_Device_FriendlyName = _PROPERTYKEY(
    _GUID.from_uuid("{A45C254E-DF1C-4EFD-8020-67D146A850E0}"),
    14,
)
_GUID_NULL = _GUID()

_ole32.CoInitializeEx.argtypes = [c_void_p, c_uint32]
_ole32.CoInitializeEx.restype = ctypes.c_long
_ole32.CoCreateInstance.argtypes = [
    POINTER(_GUID),
    c_void_p,
    c_uint32,
    POINTER(_GUID),
    POINTER(c_void_p),
]
_ole32.CoCreateInstance.restype = ctypes.c_long
_ole32.CoTaskMemFree.argtypes = [c_void_p]
_ole32.CoTaskMemFree.restype = None
_ole32.PropVariantClear.argtypes = [POINTER(_PROPVARIANT)]
_ole32.PropVariantClear.restype = ctypes.c_long


def _ensure_com() -> None:
    # S_OK (0), S_FALSE (1), veya RPC_E_CHANGED_MODE (-2147417850) kabul edilir
    hr = _ole32.CoInitializeEx(None, _COINIT_MULTITHREADED)
    if hr < 0 and hr != -2147417850:
        raise OSError(f"CoInitializeEx failed with HRESULT=0x{hr & 0xFFFFFFFF:08X}")


def _vtbl(ptr: c_void_p) -> POINTER(c_void_p):
    return ctypes.cast(ctypes.cast(ptr, POINTER(c_void_p)).contents, POINTER(c_void_p))


def _release(ptr: Optional[c_void_p]) -> None:
    if ptr and ptr.value:
        fn = ctypes.WINFUNCTYPE(c_uint32, c_void_p)(_vtbl(ptr)[2])
        fn(ptr)


def _create_enumerator() -> c_void_p:
    _ensure_com()
    ptr = c_void_p()
    hr = _ole32.CoCreateInstance(
        byref(_CLSID_MMDeviceEnumerator),
        None,
        _CLSCTX_ALL,
        byref(_IID_IMMDeviceEnumerator),
        byref(ptr),
    )
    if hr < 0 or not ptr.value:
        raise OSError(f"CoCreateInstance(MMDeviceEnumerator) failed: 0x{hr & 0xFFFFFFFF:08X}")
    return ptr


def _get_device_by_id(device_id: str) -> c_void_p:
    enum_ptr = _create_enumerator()
    try:
        # IMMDeviceEnumerator::GetDevice slot 5
        get_device = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_wchar_p, POINTER(c_void_p))(
            _vtbl(enum_ptr)[5]
        )
        dev_ptr = c_void_p()
        hr = get_device(enum_ptr, device_id, byref(dev_ptr))
        if hr < 0 or not dev_ptr.value:
            raise OSError(f"GetDevice({device_id}) failed: 0x{hr & 0xFFFFFFFF:08X}")
        return dev_ptr
    finally:
        _release(enum_ptr)


def _get_device_id(dev_ptr: c_void_p) -> str:
    # IMMDevice::GetId slot 5
    get_id = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(c_void_p))(_vtbl(dev_ptr)[5])
    raw_str = c_void_p()
    hr = get_id(dev_ptr, byref(raw_str))
    if hr < 0:
        raise OSError(f"IMMDevice::GetId failed: 0x{hr & 0xFFFFFFFF:08X}")
    try:
        return ctypes.wstring_at(raw_str.value) if raw_str.value else ""
    finally:
        if raw_str.value:
            _ole32.CoTaskMemFree(raw_str)


def _get_friendly_name(dev_ptr: c_void_p) -> str:
    # IMMDevice::OpenPropertyStore slot 4
    open_props = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_uint32, POINTER(c_void_p))(
        _vtbl(dev_ptr)[4]
    )
    props_ptr = c_void_p()
    hr = open_props(dev_ptr, _STGM_READ, byref(props_ptr))
    if hr < 0 or not props_ptr.value:
        return ""
    try:
        # IPropertyStore::GetValue slot 5
        get_value = ctypes.WINFUNCTYPE(
            ctypes.c_long, c_void_p, POINTER(_PROPERTYKEY), POINTER(_PROPVARIANT)
        )(_vtbl(props_ptr)[5])
        pv = _PROPVARIANT()
        hr = get_value(props_ptr, byref(_PKEY_Device_FriendlyName), byref(pv))
        if hr < 0:
            return ""
        try:
            if pv.vt == _VT_LPWSTR and pv.val:
                return ctypes.wstring_at(pv.val)
            return ""
        finally:
            _ole32.PropVariantClear(byref(pv))
    finally:
        _release(props_ptr)


def _activate_endpoint_volume(dev_ptr: c_void_p) -> c_void_p:
    # IMMDevice::Activate slot 3
    activate = ctypes.WINFUNCTYPE(
        ctypes.c_long, c_void_p, POINTER(_GUID), c_uint32, c_void_p, POINTER(c_void_p)
    )(_vtbl(dev_ptr)[3])
    vol_ptr = c_void_p()
    hr = activate(dev_ptr, byref(_IID_IAudioEndpointVolume), _CLSCTX_ALL, None, byref(vol_ptr))
    if hr < 0 or not vol_ptr.value:
        raise OSError(f"Activate(IAudioEndpointVolume) failed: 0x{hr & 0xFFFFFFFF:08X}")
    return vol_ptr


@dataclass(frozen=True, slots=True)
class RenderEndpoint:
    """Aktif Windows ses çıkış ucu bilgisi."""

    device_id: str
    friendly_name: str
    hw_volume: bool
    hw_mute: bool
    is_default: bool


def get_default_render_endpoint_id() -> Optional[str]:
    """Varsayılan Windows ses çıkış cihazının MMDevice ID'sini döndürür."""
    enum_ptr = _create_enumerator()
    try:
        # IMMDeviceEnumerator::GetDefaultAudioEndpoint slot 4
        get_def = ctypes.WINFUNCTYPE(
            ctypes.c_long, c_void_p, c_int, c_int, POINTER(c_void_p)
        )(_vtbl(enum_ptr)[4])
        dev_ptr = c_void_p()
        hr = get_def(enum_ptr, _E_RENDER, _E_CONSOLE, byref(dev_ptr))
        if hr < 0 or not dev_ptr.value:
            return None
        try:
            return _get_device_id(dev_ptr)
        finally:
            _release(dev_ptr)
    finally:
        _release(enum_ptr)


def list_render_endpoints() -> list[RenderEndpoint]:
    """Sistemdeki tüm aktif Windows ses çıkış cihazlarını listeler."""
    default_id = get_default_render_endpoint_id()
    enum_ptr = _create_enumerator()
    endpoints: list[RenderEndpoint] = []
    try:
        # IMMDeviceEnumerator::EnumAudioEndpoints slot 3
        enum_ep = ctypes.WINFUNCTYPE(
            ctypes.c_long, c_void_p, c_int, c_uint32, POINTER(c_void_p)
        )(_vtbl(enum_ptr)[3])
        col_ptr = c_void_p()
        hr = enum_ep(enum_ptr, _E_RENDER, _DEVICE_STATE_ACTIVE, byref(col_ptr))
        if hr < 0 or not col_ptr.value:
            return []
        try:
            # IMMDeviceCollection::GetCount slot 3, Item slot 4
            get_count = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(c_uint32))(
                _vtbl(col_ptr)[3]
            )
            get_item = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_uint32, POINTER(c_void_p))(
                _vtbl(col_ptr)[4]
            )
            count = c_uint32(0)
            if get_count(col_ptr, byref(count)) < 0:
                return []

            for idx in range(count.value):
                dev_ptr = c_void_p()
                if get_item(col_ptr, idx, byref(dev_ptr)) < 0 or not dev_ptr.value:
                    continue
                try:
                    dev_id = _get_device_id(dev_ptr)
                    name = _get_friendly_name(dev_ptr)
                    hw_vol = False
                    hw_mute = False
                    try:
                        vol_ptr = _activate_endpoint_volume(dev_ptr)
                        try:
                            # IAudioEndpointVolume::QueryHardwareSupport slot 19
                            q_hw = ctypes.WINFUNCTYPE(
                                ctypes.c_long, c_void_p, POINTER(c_uint32)
                            )(_vtbl(vol_ptr)[19])
                            mask = c_uint32(0)
                            if q_hw(vol_ptr, byref(mask)) >= 0:
                                hw_vol = bool(mask.value & _ENDPOINT_HARDWARE_SUPPORT_VOLUME)
                                hw_mute = bool(mask.value & _ENDPOINT_HARDWARE_SUPPORT_MUTE)
                        finally:
                            _release(vol_ptr)
                    except OSError:
                        pass

                    endpoints.append(
                        RenderEndpoint(
                            device_id=dev_id,
                            friendly_name=name,
                            hw_volume=hw_vol,
                            hw_mute=hw_mute,
                            is_default=(default_id == dev_id),
                        )
                    )
                finally:
                    _release(dev_ptr)
        finally:
            _release(col_ptr)
    finally:
        _release(enum_ptr)
    return endpoints


def get_endpoint_mute(device_id: str) -> bool:
    """Belirtilen cihazın sessize alınma (mute) durumunu döndürür."""
    dev_ptr = _get_device_by_id(device_id)
    try:
        vol_ptr = _activate_endpoint_volume(dev_ptr)
        try:
            # IAudioEndpointVolume::GetMute slot 15
            fn = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(c_int))(_vtbl(vol_ptr)[15])
            muted = c_int(0)
            hr = fn(vol_ptr, byref(muted))
            if hr < 0:
                raise OSError(f"GetMute failed: 0x{hr & 0xFFFFFFFF:08X}")
            return bool(muted.value)
        finally:
            _release(vol_ptr)
    finally:
        _release(dev_ptr)


def set_endpoint_mute(device_id: str, mute: bool) -> bool:
    """Belirtilen cihazı sessize alır veya sesini açar."""
    dev_ptr = _get_device_by_id(device_id)
    try:
        vol_ptr = _activate_endpoint_volume(dev_ptr)
        try:
            # IAudioEndpointVolume::SetMute slot 14
            fn = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_int, POINTER(_GUID))(
                _vtbl(vol_ptr)[14]
            )
            hr = fn(vol_ptr, 1 if mute else 0, byref(_GUID_NULL))
            return hr >= 0
        finally:
            _release(vol_ptr)
    finally:
        _release(dev_ptr)


def get_endpoint_volume(device_id: str) -> float:
    """Belirtilen cihazın ana ses seviyesini [0.0, 1.0] aralığında döndürür."""
    dev_ptr = _get_device_by_id(device_id)
    try:
        vol_ptr = _activate_endpoint_volume(dev_ptr)
        try:
            # IAudioEndpointVolume::GetMasterVolumeLevelScalar slot 9
            fn = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(c_float))(_vtbl(vol_ptr)[9])
            level = c_float(0.0)
            hr = fn(vol_ptr, byref(level))
            if hr < 0:
                raise OSError(f"GetMasterVolumeLevelScalar failed: 0x{hr & 0xFFFFFFFF:08X}")
            return float(level.value)
        finally:
            _release(vol_ptr)
    finally:
        _release(dev_ptr)


def set_endpoint_volume(device_id: str, scalar: float) -> bool:
    """Belirtilen cihazın ana ses seviyesini [0.0, 1.0] aralığında ayarlar."""
    clamped = max(0.0, min(1.0, float(scalar)))
    dev_ptr = _get_device_by_id(device_id)
    try:
        vol_ptr = _activate_endpoint_volume(dev_ptr)
        try:
            # IAudioEndpointVolume::SetMasterVolumeLevelScalar slot 7
            fn = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_float, POINTER(_GUID))(
                _vtbl(vol_ptr)[7]
            )
            hr = fn(vol_ptr, c_float(clamped), byref(_GUID_NULL))
            return hr >= 0
        finally:
            _release(vol_ptr)
    finally:
        _release(dev_ptr)


def set_default_render_endpoint(device_id: str) -> bool:
    """Windows varsayılan ses çıkış cihazını tüm roller için değiştirir."""
    _ensure_com()
    policy_ptr = c_void_p()
    hr = _ole32.CoCreateInstance(
        byref(_CLSID_CPolicyConfigClient),
        None,
        _CLSCTX_ALL,
        byref(_IID_IPolicyConfig),
        byref(policy_ptr),
    )
    if hr < 0 or not policy_ptr.value:
        return False
    try:
        # IPolicyConfig::SetDefaultEndpoint slot 13
        fn = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_wchar_p, c_int)(_vtbl(policy_ptr)[13])
        ok = True
        for role in (_E_CONSOLE, _E_MULTIMEDIA, _E_COMMUNICATIONS):
            res = fn(policy_ptr, device_id, role)
            if res < 0:
                ok = False
        return ok
    finally:
        _release(policy_ptr)


def find_endpoint_for_loopback_name(
    loopback_name: str,
    endpoints: Optional[list[RenderEndpoint]] = None,
) -> Optional[RenderEndpoint]:
    """WASAPI Loopback cihaz adına karşılık gelen render endpoint'i bulur."""
    items = endpoints if endpoints is not None else list_render_endpoints()
    cleaned = loopback_name.removesuffix(" [Loopback]").strip().lower()
    if not cleaned:
        return None
    for ep in items:
        if ep.friendly_name.strip().lower() == cleaned:
            return ep
    for ep in items:
        name_low = ep.friendly_name.strip().lower()
        if cleaned in name_low or name_low in cleaned:
            return ep
    return None


def find_silent_sink_endpoint(
    exclude_id: Optional[str] = None,
    endpoints: Optional[list[RenderEndpoint]] = None,
) -> Optional[RenderEndpoint]:
    """Kulaklık/dahili hoparlör dışındaki sessiz veya sanal ses çıkış cihazını bulur.

    Öncelik sırası:
    1. Sanal ses sürücüleri (VB-Audio, Cable, Virtual Audio, Voicemeeter, Null vb.)
    2. Ekran / Monitör / GPU dijital ses çıkışları (NVIDIA, AMD, HDMI, DisplayPort, Monitör)
    3. Exclude_id dışındaki herhangi bir aktif ikincil çıkış
    """
    items = endpoints if endpoints is not None else list_render_endpoints()
    candidates = [ep for ep in items if ep.device_id != exclude_id]
    if not candidates:
        return None

    # 1. Öncelik: Sanal ses sürücüleri
    virtual_keywords = ("cable", "vb-audio", "virtual", "voicemeeter", "vac", "null", "line 1", "line 2")
    for ep in candidates:
        low = ep.friendly_name.lower()
        if any(kw in low for kw in virtual_keywords):
            return ep

    # 2. Öncelik: Monitör / HDMI / Ekran kartı çıkışları
    monitor_keywords = ("nvidia", "amd", "hdmi", "displayport", "display", "monitor", "ls27", "tv", "dg30")
    for ep in candidates:
        low = ep.friendly_name.lower()
        if any(kw in low for kw in monitor_keywords):
            return ep

    return candidates[0]


class LocalAudioSilencer:
    """Yayın sırasında PC hoparlörünü/kulaklığını susturur ve bitince otomatik geri yükler."""

    def __init__(self) -> None:
        self._active_mode: Optional[str] = None
        self._target_endpoint_id: Optional[str] = None
        self._prev_mute: Optional[bool] = None
        self._prev_volume: Optional[float] = None
        self._prev_default_id: Optional[str] = None
        self._atexit_registered = False

    @property
    def is_active(self) -> bool:
        return self._active_mode is not None

    @property
    def active_mode(self) -> Optional[str]:
        return self._active_mode

    def _register_atexit(self) -> None:
        if not self._atexit_registered:
            atexit.register(self.restore)
            self._atexit_registered = True

    def activate_hardware_mute(self, endpoint_id: str) -> bool:
        self.restore()
        prev_mute = get_endpoint_mute(endpoint_id)
        if not set_endpoint_mute(endpoint_id, True):
            return False
        self._active_mode = "hardware_mute"
        self._target_endpoint_id = endpoint_id
        self._prev_mute = prev_mute
        self._register_atexit()
        return True

    def activate_hardware_zero_vol(self, endpoint_id: str) -> bool:
        self.restore()
        prev_vol = get_endpoint_volume(endpoint_id)
        if not set_endpoint_volume(endpoint_id, 0.0):
            return False
        self._active_mode = "hardware_zero_vol"
        self._target_endpoint_id = endpoint_id
        self._prev_volume = prev_vol
        self._register_atexit()
        return True

    def activate_silent_route(self, silent_endpoint_id: str) -> bool:
        self.restore()
        prev_default = get_default_render_endpoint_id()
        if not prev_default or prev_default == silent_endpoint_id:
            return False
        if not set_default_render_endpoint(silent_endpoint_id):
            return False
        self._active_mode = "route_silent"
        self._target_endpoint_id = silent_endpoint_id
        self._prev_default_id = prev_default
        self._register_atexit()
        return True

    def restore(self) -> Optional[str]:
        """Susturma öncesi PC ses durumunu güvenli biçimde geri yükler."""
        mode = self._active_mode
        if mode is None:
            return None

        target_id = self._target_endpoint_id
        prev_mute = self._prev_mute
        prev_vol = self._prev_volume
        prev_default = self._prev_default_id

        self._active_mode = None
        self._target_endpoint_id = None
        self._prev_mute = None
        self._prev_volume = None
        self._prev_default_id = None

        try:
            if mode == "hardware_mute" and target_id is not None and prev_mute is not None:
                set_endpoint_mute(target_id, prev_mute)
            elif mode == "hardware_zero_vol" and target_id is not None and prev_vol is not None:
                set_endpoint_volume(target_id, prev_vol)
            elif mode == "route_silent" and prev_default is not None:
                set_default_render_endpoint(prev_default)
        except Exception:
            pass
        return mode
