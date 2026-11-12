# tatipWindowDump.py

"""Read-only diagnostic: records the window tree of every running windows_tatip.exe window.

Nothing is clicked, typed or changed in PPA Tatip. The result shows the window
classes, captions and list contents of Tatip's own dictionary windows so that
a later version can hand words to Tatip instead of generating codes itself.
"""

import ctypes
import os
import time
from ctypes import wintypes

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_WM_GETTEXT = 0x000D
_WM_GETTEXTLENGTH = 0x000E
_LB_GETCURSEL = 0x0188
_LB_GETTEXT = 0x0189
_LB_GETTEXTLEN = 0x018A
_LB_GETCOUNT = 0x018B
_GWL_STYLE = -16
_GWL_ID = -12
_GW_HWNDNEXT = 2
_GW_CHILD = 5
_GW_OWNER = 4
_WM_SETTEXT = 0x000C
_BM_CLICK = 0x00F5
_SMTO_ABORTIFHUNG = 0x0002
_SEND_TIMEOUT_MS = 300
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_TATIP_IMAGE_NAME = "windows_tatip.exe"
_MAX_DEPTH = 10
_MAX_NODES = 800
_MAX_TEXT_BYTES = 4000
_LISTBOX_HEAD_ITEMS = 40
_LISTBOX_TAIL_ITEMS = 10
_TEXT_ENCODING = "cp874"

_user32.SendMessageTimeoutA.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t),
]
_user32.SendMessageTimeoutA.restype = ctypes.c_ssize_t
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetWindow.restype = wintypes.HWND
_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = ctypes.c_long
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowEnabled.argtypes = [wintypes.HWND]
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
]

_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.IsWindow.argtypes = [wintypes.HWND]
_kernel32.GetACP.restype = wintypes.UINT

_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_EnumWindowsProc, wintypes.LPARAM]


def _sendMessage(hwnd, message, wParam=0, lParam=0):
    """Returns (succeeded, result); a hung target cannot block the caller longer than the timeout."""
    result = ctypes.c_size_t(0)
    sent = _user32.SendMessageTimeoutA(
        hwnd, message, wParam, lParam, _SMTO_ABORTIFHUNG, _SEND_TIMEOUT_MS, ctypes.byref(result)
    )
    return bool(sent), result.value


def _decodeBytes(rawBytes):
    return rawBytes.split(b"\x00", 1)[0].decode(_TEXT_ENCODING, errors="replace")


def _getWindowText(hwnd):
    sent, textLength = _sendMessage(hwnd, _WM_GETTEXTLENGTH)
    if not sent:
        return "<no reply>"
    textLength = min(textLength, _MAX_TEXT_BYTES)
    if textLength <= 0:
        return ""
    buffer = ctypes.create_string_buffer(textLength + 2)
    sent, _copied = _sendMessage(hwnd, _WM_GETTEXT, textLength + 1, ctypes.addressof(buffer))
    return _decodeBytes(buffer.raw) if sent else "<no reply>"


def _getClassName(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _getProcessImageName(processId):
    processHandle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, processId)
    if not processHandle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if not _kernel32.QueryFullProcessImageNameW(processHandle, 0, buffer, ctypes.byref(size)):
            return ""
        return os.path.basename(buffer.value).lower()
    finally:
        _kernel32.CloseHandle(processHandle)


def _findTatipTopLevelWindows():
    imageNameByProcess = {}
    tatipWindows = []

    @_EnumWindowsProc
    def collectWindow(hwnd, _lParam):
        processId = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(processId))
        if processId.value not in imageNameByProcess:
            imageNameByProcess[processId.value] = _getProcessImageName(processId.value)
        if imageNameByProcess[processId.value] == _TATIP_IMAGE_NAME:
            tatipWindows.append(hwnd)
        return True

    _user32.EnumWindows(collectWindow, 0)
    return tatipWindows


def _describeListBox(hwnd, indent):
    lines = []
    sent, itemCount = _sendMessage(hwnd, _LB_GETCOUNT)
    if not sent or itemCount > 0x7FFFFFFF:
        return [f"{indent}  list: <no reply>"]
    _sent, selection = _sendMessage(hwnd, _LB_GETCURSEL)
    selectedIndex = selection if selection < 0x7FFFFFFF else -1
    lines.append(f"{indent}  list: count={itemCount} selected={selectedIndex}")
    wantedIndices = list(range(min(itemCount, _LISTBOX_HEAD_ITEMS)))
    wantedIndices += [
        itemIndex for itemIndex in range(max(itemCount - _LISTBOX_TAIL_ITEMS, _LISTBOX_HEAD_ITEMS), itemCount)
    ]
    for itemIndex in wantedIndices:
        sent, textLength = _sendMessage(hwnd, _LB_GETTEXTLEN, itemIndex)
        if not sent or textLength > _MAX_TEXT_BYTES:
            lines.append(f"{indent}  [{itemIndex}] <unreadable>")
            continue
        buffer = ctypes.create_string_buffer(textLength + 2)
        sent, _copied = _sendMessage(hwnd, _LB_GETTEXT, itemIndex, ctypes.addressof(buffer))
        lines.append(f"{indent}  [{itemIndex}] {_decodeBytes(buffer.raw) if sent else '<unreadable>'!r}")
    return lines


def _describeWindow(hwnd, depth, nodeBudget):
    indent = "  " * depth
    className = _getClassName(hwnd)
    rect = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    processId = wintypes.DWORD(0)
    threadId = _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(processId))
    owner = _user32.GetWindow(hwnd, _GW_OWNER) or 0
    lines = [
        f"{indent}hwnd=0x{hwnd:X} class={className!r} text={_getWindowText(hwnd)!r} "
        f"id={_user32.GetWindowLongW(hwnd, _GWL_ID)} style=0x{_user32.GetWindowLongW(hwnd, _GWL_STYLE) & 0xFFFFFFFF:08X} "
        f"visible={bool(_user32.IsWindowVisible(hwnd))} enabled={bool(_user32.IsWindowEnabled(hwnd))} "
        f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) pid={processId.value} tid={threadId} "
        f"owner=0x{owner:X}"
    ]
    if "listbox" in className.lower():
        lines.extend(_describeListBox(hwnd, indent))
    if depth >= _MAX_DEPTH:
        return lines
    childHandle = _user32.GetWindow(hwnd, _GW_CHILD)
    while childHandle and nodeBudget[0] > 0:
        nodeBudget[0] -= 1
        lines.extend(_describeWindow(childHandle, depth + 1, nodeBudget))
        childHandle = _user32.GetWindow(childHandle, _GW_HWNDNEXT)
    return lines


def dumpTatipWindows(outputPath):
    """Writes the window tree to outputPath and returns (text, topLevelWindowCount). Raises OSError on write failure."""
    topLevelWindows = _findTatipTopLevelWindows()
    lines = [
        f"PPAWakeUp Tatip window dump {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"top-level {_TATIP_IMAGE_NAME} windows: {len(topLevelWindows)}",
        "",
    ]
    nodeBudget = [_MAX_NODES]
    for topLevelHandle in topLevelWindows:
        lines.extend(_describeWindow(topLevelHandle, 0, nodeBudget))
        lines.append("")
    dumpText = "\r\n".join(lines)
    outputDir = os.path.dirname(outputPath)
    if outputDir:
        os.makedirs(outputDir, exist_ok=True)
    with open(outputPath, "w", encoding="utf-8", newline="") as dumpFile:
        dumpFile.write(dumpText)
    return dumpText, len(topLevelWindows)


# Public helpers used by tatipDictionaryDriver.

def getAnsiCodePage():
    return _kernel32.GetACP()


def findTatipWindows():
    """All top-level windows of windows_tatip.exe, visible or not."""
    return _findTatipTopLevelWindows()


def findVisibleTatipWindows(className=None):
    return [
        windowHandle for windowHandle in _findTatipTopLevelWindows()
        if _user32.IsWindowVisible(windowHandle) and (className is None or _getClassName(windowHandle) == className)
    ]


def getWindowClass(hwnd):
    return _getClassName(hwnd)


def getWindowText(hwnd):
    return _getWindowText(hwnd)


def isWindowAlive(hwnd):
    return bool(_user32.IsWindow(hwnd))


def isWindowVisible(hwnd):
    return bool(_user32.IsWindowVisible(hwnd))


def getWindowTopLeft(hwnd):
    rect = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.top, rect.left)


def getDescendantWindows(hwnd):
    descendants = []

    def collect(parentHandle, depth):
        childHandle = _user32.GetWindow(parentHandle, _GW_CHILD)
        while childHandle and len(descendants) < _MAX_NODES:
            descendants.append(childHandle)
            if depth < _MAX_DEPTH:
                collect(childHandle, depth + 1)
            childHandle = _user32.GetWindow(childHandle, _GW_HWNDNEXT)

    collect(hwnd, 0)
    return descendants


def setWindowText(hwnd, text):
    """Sets the text of an ANSI window using the Thai code page. Returns True when the window replied."""
    buffer = ctypes.create_string_buffer(text.encode(_TEXT_ENCODING))
    sent, _result = _sendMessage(hwnd, _WM_SETTEXT, 0, ctypes.addressof(buffer))
    return sent


def clickButton(hwnd):
    """Posts a click so a button that opens a modal window does not block the caller."""
    return bool(_user32.PostMessageW(hwnd, _BM_CLICK, 0, 0))
