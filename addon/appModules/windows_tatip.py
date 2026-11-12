# windows_tatip.py

import logging

import appModuleHandler
import winUser
from logHandler import log

_MAX_LOGGED_WINDOWS = 64


class AppModule(appModuleHandler.AppModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loggedWindows = set()

    def isBadUIAWindow(self, hwnd):
        # Skipping the UIA probe keeps NVDA from blocking on this process's
        # UI thread while it is busy; its windows are read through IAccessible.
        # Called outside the main thread, so only window class names are read.
        if hwnd not in self._loggedWindows and log.isEnabledFor(logging.DEBUG):
            if len(self._loggedWindows) >= _MAX_LOGGED_WINDOWS:
                self._loggedWindows.clear()
            self._loggedWindows.add(hwnd)
            log.debug(
                f"PPAWakeUp: windows_tatip: skipping UIA probe for hwnd={hwnd} "
                f"class={winUser.getClassName(hwnd)!r}"
            )
        return True
