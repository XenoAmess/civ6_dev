"""Read visible ETW sessions; this module defines no session-control API.

Primary contracts:
https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-queryalltracesw
https://learn.microsoft.com/en-us/windows/win32/etw/event-trace-properties
QueryAllTraces does not return private logging sessions. Caller permissions
also limit visibility. Do not infer that every possible logger is absent.
"""
import ctypes as C
import os


class Guid(C.Structure):
    _fields_ = [("Data1", C.c_uint32), ("Data2", C.c_uint16),
                ("Data3", C.c_uint16), ("Data4", C.c_uint8 * 8)]


class Wnode(C.Structure):
    _fields_ = [("BufferSize", C.c_uint32), ("ProviderId", C.c_uint32),
                ("HistoricalContext", C.c_uint64), ("TimeStamp", C.c_int64),
                ("Guid", Guid), ("ClientContext", C.c_uint32), ("Flags", C.c_uint32)]


class Properties(C.Structure):
    _fields_ = [("Wnode", Wnode)] + [(name, C.c_uint32) for name in (
        "BufferSize", "MinimumBuffers", "MaximumBuffers", "MaximumFileSize",
        "LogFileMode", "FlushTimer", "EnableFlags", "AgeLimit", "NumberOfBuffers",
        "FreeBuffers", "EventsLost", "BuffersWritten", "LogBuffersLost",
        "RealTimeBuffersLost")] + [("LoggerThreadId", C.c_void_p),
        ("LogFileNameOffset", C.c_uint32), ("LoggerNameOffset", C.c_uint32)]


def _name(buffer, offset):
    size = C.sizeof(buffer)
    if type(offset) is not int or offset < C.sizeof(Properties) or offset % 2 or offset + 2 > size:
        raise ValueError("Unknown logger-name offset")
    raw = bytes(buffer)[offset:]
    for i in range(0, min(len(raw), 2050), 2):
        if raw[i:i + 2] == b"\0\0":
            text = raw[:i].decode("utf-16-le", errors="strict")
            if not text or len(text) > 1024 or any(ord(c) < 32 for c in text):
                raise ValueError("Unknown logger-name contents")
            return text
    raise ValueError("Unterminated or oversized logger name")


def query_all(api=None):
    """Return only queried properties, or fail without starting/stopping a trace."""
    if C.sizeof(C.c_void_p) != 8 or C.sizeof(Wnode) != 48 or C.sizeof(Properties) != 120:
        raise RuntimeError("Unsupported ETW property ABI")
    pointer = C.POINTER(Properties)
    if api is None:
        if os.name != "nt":
            raise RuntimeError("Native ETW query requires Windows")
        api = C.WinDLL("advapi32", use_last_error=True).QueryAllTracesW
        api.argtypes = [C.POINTER(pointer), C.c_uint32, C.POINTER(C.c_uint32)]
        api.restype = C.c_uint32
    capacity = 64
    for _ in range(5):
        buffers = [C.create_string_buffer(C.sizeof(Properties) + 4100) for _ in range(capacity)]
        array = (pointer * capacity)()
        for i, buffer in enumerate(buffers):
            p = Properties.from_buffer(buffer)
            p.Wnode.BufferSize = C.sizeof(buffer)
            p.LoggerNameOffset = C.sizeof(Properties)
            p.LogFileNameOffset = C.sizeof(Properties) + 2050
            array[i] = C.cast(buffer, pointer)
        count = C.c_uint32()
        status = api(array, capacity, C.byref(count))
        if status == 234:  # ERROR_MORE_DATA: no partial result is adopted.
            if not capacity < count.value <= 1024:
                raise ValueError("Unknown ETW capacity requirement")
            capacity = count.value
            continue
        if status != 0:
            raise OSError(status, "QueryAllTracesW failed")
        if count.value > capacity:
            raise ValueError("ETW count exceeds supplied capacity")
        rows, seen = [], set()
        for i in range(count.value):
            p = Properties.from_buffer(buffers[i])
            name = _name(buffers[i], p.LoggerNameOffset)
            if name.casefold() in seen:
                raise ValueError("Duplicate ETW logger name")
            seen.add(name.casefold())
            rows.append({"name": name, "log_file_mode": p.LogFileMode,
                         "enable_flags": p.EnableFlags, "client_context": p.Wnode.ClientContext,
                         "events_lost": p.EventsLost, "log_buffers_lost": p.LogBuffersLost,
                         "realtime_buffers_lost": p.RealTimeBuffersLost,
                         "buffers_written": p.BuffersWritten, "number_of_buffers": p.NumberOfBuffers})
        return rows
    raise ValueError("ETW inventory changed beyond bounded query attempts")


def wpr_conflicts(rows, own_instance=None):
    if not isinstance(rows, list) or len(rows) > 1024:
        raise ValueError("Unknown ETW inventory")
    if own_instance is not None and (not isinstance(own_instance, str) or not own_instance):
        raise ValueError("Unknown own instance")
    seen, conflicts = set(), []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"]:
            raise ValueError("Unknown ETW session")
        name = row["name"]
        if name.casefold() in seen:
            raise ValueError("Duplicate ETW session")
        seen.add(name.casefold())
        if "wpr" in name.casefold() or "windows performance recorder" in name.casefold():
            if own_instance is None or own_instance.casefold() not in name.casefold():
                conflicts.append(name)
    return conflicts
