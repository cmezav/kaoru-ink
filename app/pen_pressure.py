"""Best-effort actual stylus pressure from a Wintab tablet driver on Windows.

Wintab is optional. Not every Windows Ink tablet offers it, and some drivers
reserve packets for the foreground drawing program. In those situations Kaoru
Ink falls back to movement-based *estimated intensity*, never falsely claiming
that mouse motion is physical pen pressure.
"""
import os
import threading


class WintabPressureMonitor:
    def __init__(self,callback):
        self.callback=callback
        self.thread=None
        self.hwnd=None
        self.running=False
        self.error=None

    def start(self):
        if os.name!='nt':return False
        self.thread=threading.Thread(target=self._run,name='Kaoru-Wintab',daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if self.hwnd:
            try:
                import ctypes
                ctypes.windll.user32.PostMessageW(self.hwnd,0x0010,0,0)
            except Exception:pass
        if self.thread and self.thread.is_alive():self.thread.join(timeout=.6)

    def _run(self):
        import ctypes
        from ctypes import wintypes
        try:
            wintab=ctypes.WinDLL('Wintab32.dll')
            user32=ctypes.WinDLL('user32.dll')
            kernel32=ctypes.WinDLL('kernel32.dll')

            class LOGCONTEXTA(ctypes.Structure):
                _fields_=[('lcName',ctypes.c_char*40),('lcOptions',wintypes.UINT),
                    ('lcStatus',wintypes.UINT),('lcLocks',wintypes.UINT),
                    ('lcMsgBase',wintypes.UINT),('lcDevice',wintypes.UINT),
                    ('lcPktRate',wintypes.UINT),('lcPktData',wintypes.DWORD),
                    ('lcPktMode',wintypes.DWORD),('lcMoveMask',wintypes.DWORD),
                    ('lcBtnDnMask',wintypes.DWORD),('lcBtnUpMask',wintypes.DWORD),
                    ('lcInOrgX',wintypes.LONG),('lcInOrgY',wintypes.LONG),('lcInOrgZ',wintypes.LONG),
                    ('lcInExtX',wintypes.LONG),('lcInExtY',wintypes.LONG),('lcInExtZ',wintypes.LONG),
                    ('lcOutOrgX',wintypes.LONG),('lcOutOrgY',wintypes.LONG),('lcOutOrgZ',wintypes.LONG),
                    ('lcOutExtX',wintypes.LONG),('lcOutExtY',wintypes.LONG),('lcOutExtZ',wintypes.LONG),
                    ('lcSensX',wintypes.DWORD),('lcSensY',wintypes.DWORD),('lcSensZ',wintypes.DWORD),
                    ('lcSysMode',wintypes.BOOL),('lcSysOrgX',ctypes.c_int),('lcSysOrgY',ctypes.c_int),
                    ('lcSysExtX',ctypes.c_int),('lcSysExtY',ctypes.c_int),
                    ('lcSysSensX',wintypes.DWORD),('lcSysSensY',wintypes.DWORD)]
            class AXIS(ctypes.Structure):
                _fields_=[('min',wintypes.LONG),('max',wintypes.LONG),
                          ('units',wintypes.UINT),('resolution',wintypes.DWORD)]
            class PACKET(ctypes.Structure):
                _fields_=[('x',wintypes.LONG),('y',wintypes.LONG),('pressure',wintypes.UINT)]
            lc=LOGCONTEXTA()
            wintab.WTInfoA.argtypes=[wintypes.UINT,wintypes.UINT,ctypes.c_void_p]
            wintab.WTInfoA.restype=wintypes.UINT
            if not wintab.WTInfoA(4,0,ctypes.byref(lc)):
                raise RuntimeError('Wintab context not offered')
            ax=AXIS()
            if not wintab.WTInfoA(100+lc.lcDevice,12,ctypes.byref(ax)) or ax.max<=ax.min:
                raise RuntimeError('No normal-pressure axis')
            lc.lcOptions|=0x0004  # CXO_MESSAGES
            # Include XY so Wintab sends updates when pressure stays constant.
            lc.lcPktData=0x0080|0x0100|0x0400
            lc.lcPktMode=0
            lc.lcMoveMask=lc.lcPktData
            lc.lcMsgBase=0x7900
            wtpacket=wintab.WTPacket
            wtpacket.argtypes=[wintypes.HANDLE,wintypes.UINT,ctypes.c_void_p]
            wtpacket.restype=wintypes.BOOL
            wndproc_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
            user32.DefWindowProcW.restype=ctypes.c_ssize_t
            user32.DefWindowProcW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            @wndproc_type
            def wndproc(hwnd,msg,wparam,lparam):
                if msg==lc.lcMsgBase:
                    packet=PACKET()
                    if wtpacket(wintypes.HANDLE(lparam),wparam,ctypes.byref(packet)):
                        pressure=(float(packet.pressure)-ax.min)/(ax.max-ax.min)
                        self.callback(max(0.,min(1.,pressure)))
                    return 0
                if msg==0x0010:
                    user32.DestroyWindow(hwnd);return 0
                if msg==0x0002:
                    user32.PostQuitMessage(0);return 0
                return user32.DefWindowProcW(hwnd,msg,wparam,lparam)
            class WNDCLASSW(ctypes.Structure):
                _fields_=[('style',wintypes.UINT),('lpfnWndProc',wndproc_type),
                    ('cbClsExtra',ctypes.c_int),('cbWndExtra',ctypes.c_int),
                    ('hInstance',wintypes.HINSTANCE),('hIcon',wintypes.HICON),
                    ('hCursor',wintypes.HCURSOR),('hbrBackground',wintypes.HBRUSH),
                    ('lpszMenuName',wintypes.LPCWSTR),('lpszClassName',wintypes.LPCWSTR)]
            kernel32.GetModuleHandleW.argtypes=[wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype=wintypes.HMODULE
            name='KaoruInkPressureReceiver_'+str(os.getpid())
            cls=WNDCLASSW()
            cls.lpfnWndProc=wndproc
            cls.lpszClassName=name
            cls.hInstance=kernel32.GetModuleHandleW(None)
            if not user32.RegisterClassW(ctypes.byref(cls)):
                raise RuntimeError('Could not register hidden Wintab window')
            user32.CreateWindowExW.restype=wintypes.HWND
            user32.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,
                wintypes.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,
                wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
            hwnd=user32.CreateWindowExW(0,name,'Kaoru Ink pressure receiver',0,0,0,0,0,None,None,cls.hInstance,None)
            if not hwnd:raise RuntimeError('Could not create hidden Wintab window')
            self.hwnd=hwnd
            wintab.WTOpenA.argtypes=[wintypes.HWND,ctypes.POINTER(LOGCONTEXTA),wintypes.BOOL]
            wintab.WTOpenA.restype=wintypes.HANDLE
            ctx=wintab.WTOpenA(hwnd,ctypes.byref(lc),True)
            if not ctx:raise RuntimeError('Wintab driver declined a listening context')
            self.running=True
            msg=wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg),None,0,0)>0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            wintab.WTClose.argtypes=[wintypes.HANDLE]
            wintab.WTClose(ctx)
            self.running=False;self.hwnd=None
            user32.UnregisterClassW(name,cls.hInstance)
        except Exception as exc:
            self.error=str(exc)
            self.running=False;self.hwnd=None
