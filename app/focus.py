"""Check whether the foreground window is the actual Clip Studio Paint editor."""
import ctypes
import os
from ctypes import wintypes

if os.name == 'nt':
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def foreground_paint():
    """Uses foreground editor process name or explicit editor window title.

    CLIP STUDIO launcher alone is intentionally not sufficient.
    Not a per-monitor test: 'on screen in front' means foreground window.
    """
    if os.name != 'nt':
        return False
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    title = buf.value.lower()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process = ''
    if pid.value:
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if handle:
            try:
                path = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(path))
                if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                    process = os.path.basename(path.value).lower().replace('_','').replace(' ','')
                    if 'clipstudiopaint' in process:
                        return True
            finally:
                kernel32.CloseHandle(handle)
    # Don't trust a window title alone: a browser tab can contain that text.
    return process in ('csp.exe', 'clipstudio.exe') and 'clip studio paint' in title
