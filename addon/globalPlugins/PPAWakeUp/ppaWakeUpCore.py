# ppaWakeUpCore.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import addonHandler
import ui
import subprocess
import os
import ctypes
import tones
import time
import threading
import core
import logHandler
import wx
import gui
import shutil
import json
import controlTypes
import speech.speech as speechModule
import globalVars


# Unicode range of characters that may cause PPA Tatip to stop working
# Covers CJK Unified Ideographs, Hiragana, Katakana, Hangul and more
_FORBIDDEN_RANGES = [
    (0x2E80, 0x2EFF),   # CJK Radicals Supplement
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0x3040, 0x309F),   # Hiragana
    (0x30A0, 0x30FF),   # Katakana
    (0x3100, 0x312F),   # Bopomofo
    (0x3130, 0x318F),   # Hangul Compatibility Jamo
    (0x3190, 0x319F),   # Kanbun
    (0x31C0, 0x31EF),   # CJK Strokes
    (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
    (0x3200, 0x32FF),   # Enclosed CJK Letters and Months
    (0x3300, 0x33FF),   # CJK Compatibility
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0xA000, 0xA4CF),   # Yi Syllables / Yi Radicals
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0xD7B0, 0xD7FF),   # Hangul Jamo Extended-B
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0xFE30, 0xFE4F),   # CJK Compatibility Forms
    (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms (Except for the part that is ASCII?)
    # Other sessions may be added if additional problems are discovered
]

# Settings storage location and defaults
_SETTINGS_SUBFOLDER = os.path.join("ChaiChaimee", "PPAWakeUp")
_SETTINGS_FILE_NAME = "settings.json"

_DEFAULT_SETTINGS = {
    "skipCjkCharacters": True,
    "protectDialogButtonCrash": True,
    "autoRetryWakeUp": True,
}

# Labels of dialog action buttons (Open/OK/Save/Yes) known to trigger a silent
# PPA Tatip crash when focused right after a file-picker dialog appears.
# Thai equivalents are stored as escape sequences to keep this file ASCII-only.
_DIALOG_ACTION_BUTTON_LABELS = {
    "ok",
    "open",
    "save",
    "yes",
    "\u0e15\u0e01\u0e25\u0e07",     # confirm / OK
    "\u0e40\u0e1b\u0e34\u0e14",     # open
    "\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01",  # save
    "\u0e43\u0e0a\u0e48",           # yes
}

_DIALOG_WATCHDOG_DELAY_MS = 1500
_TATIP_PROCESS_NAME = "windows_tatip.exe"

# Minimum time after a confirmed-successful launch before a new windows+p
# press is allowed to force-kill and relaunch Tatip again. Without this,
# a user re-pressing windows+p while impatient can kill a Tatip process
# that only just finished starting, producing a self-defeating retry loop.
_RESTART_COOLDOWN_SEC = 3.0

# Per-attempt time allowed for the relaunched process to confirm as
# running before this attempt is considered failed and retried. Too short
# a timeout was observed causing premature retries against this older,
# slower-to-register application.
_LAUNCH_CONFIRM_TIMEOUT_SEC = 2.5

# Used to force-release the Windows modifier key immediately after the
# windows+p gesture fires. Windows can otherwise be left believing the
# key is still physically held, which routes every subsequent "p" press
# to the shell's Project switcher instead of the focused application.
_VK_LWIN = 0x5B
_VK_RWIN = 0x5C
_KEYEVENTF_KEYUP = 0x0002


def _forceReleaseWindowsModifier():
    """Synthesize a key-up for both Windows keys via the raw Win32 API.

    NVDA's low-level keyboard hook consumes the windows+p combination so
    the shell never sees a matched chord, but the standalone key-down for
    the Windows key can still reach the OS's own modifier tracking ahead
    of that match. If the corresponding key-up is ever swallowed instead
    of forwarded, Windows keeps treating the key as held, and the user
    loses the ability to type the letter "p" until a reboot. Sending an
    explicit synthetic key-up here clears that state unconditionally,
    regardless of what the hook already did with the real event.
    """
    ctypes.windll.user32.keybd_event(_VK_LWIN, 0, _KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(_VK_RWIN, 0, _KEYEVENTF_KEYUP, 0)


def _beep(pitch, durationMs):
    """Play a short feedback tone through NVDA's own tones.beep.

    winsound.Beep bypasses tones.beep entirely, which silently breaks any
    other installed add-on's global panning/volume monkeypatch on that
    function. Marshaled through wx.CallAfter so it is safe to call from
    the background worker threads used throughout this module.
    """
    wx.CallAfter(tones.beep, pitch, durationMs)


class TatipMenu(wx.Frame):
    """A simple list-based menu for PPA Tatip dictionary management."""

    def __init__(self, parent, callbackMap, title=_("PPA Tatip \u2013 Menu")):
        super().__init__(
            parent,
            title=title,
            size=(400, 250),
            style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP | wx.FRAME_FLOAT_ON_PARENT
        )
        self._callbackMap = callbackMap
        self._labels = list(callbackMap.keys())

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._listbox = wx.ListBox(panel, choices=self._labels, style=wx.LB_SINGLE)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self._listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._onActivate)
        self._listbox.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._onTimeout, self._timer)
        self._timer.Start(15000)

        self.Bind(wx.EVT_CLOSE, self._onClose)
        self.CentreOnScreen()
        self.Show()
        self.Raise()
        self._listbox.SetFocus()
        if self._listbox.GetCount() > 0:
            self._listbox.SetSelection(0)

    def _onCharHook(self, event):
        self._timer.Start(15000)
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN:
            self._onActivate(None)
        elif key == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()

    def _onActivate(self, event):
        sel = self._listbox.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        label = self._labels[sel]
        callback = self._callbackMap.get(label)
        if callback:
            self.Close()
            wx.CallAfter(callback)

    def _onTimeout(self, event):
        self.Close()

    def _onClose(self, event):
        self._timer.Stop()
        self.Destroy()


def showTatipMenu(parent, callbackMap, title=_("PPA Tatip \u2013 Menu")):
    """Create and show the Tatip menu frame."""
    TatipMenu(parent, callbackMap, title)


class TatipSettingsDialog(wx.Dialog):
    """Settings window for PPA Tatip crash-prevention options."""

    def __init__(self, parent, currentSettings, onSave, title=_("Tatip Reader Setting")):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP
        )
        self._onSave = onSave

        panel = wx.Panel(self)
        outerSizer = wx.BoxSizer(wx.VERTICAL)
        helper = gui.guiHelper.BoxSizerHelper(panel, orientation=wx.VERTICAL)

        self._skipCjkCheckbox = helper.addItem(
            wx.CheckBox(
                panel,
                label=_("Skip Chinese, Japanese and Korean characters when speaking")
            )
        )
        self._skipCjkCheckbox.SetValue(currentSettings.get("skipCjkCharacters", True))

        self._protectDialogCheckbox = helper.addItem(
            wx.CheckBox(
                panel,
                label=_("Protect against crash when focusing Open/OK/Save buttons in dialogs")
            )
        )
        self._protectDialogCheckbox.SetValue(currentSettings.get("protectDialogButtonCrash", True))

        self._autoRetryCheckbox = helper.addItem(
            wx.CheckBox(
                panel,
                label=_("Automatically retry wake up if PPA Tatip does not start")
            )
        )
        self._autoRetryCheckbox.SetValue(currentSettings.get("autoRetryWakeUp", True))

        buttonSizer = wx.StdDialogButtonSizer()
        okButton = wx.Button(panel, wx.ID_OK)
        okButton.SetDefault()
        cancelButton = wx.Button(panel, wx.ID_CANCEL)
        buttonSizer.AddButton(okButton)
        buttonSizer.AddButton(cancelButton)
        buttonSizer.Realize()
        helper.addItem(buttonSizer)

        panel.SetSizer(helper.sizer)
        outerSizer.Add(panel, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(outerSizer)

        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self._onCancel)

        self.CentreOnScreen()
        self._skipCjkCheckbox.SetFocus()

    def _onOk(self, event):
        updatedSettings = {
            "skipCjkCharacters": self._skipCjkCheckbox.GetValue(),
            "protectDialogButtonCrash": self._protectDialogCheckbox.GetValue(),
            "autoRetryWakeUp": self._autoRetryCheckbox.GetValue(),
        }
        if self._onSave:
            self._onSave(updatedSettings)
        gui.mainFrame.postPopup()
        self.Destroy()

    def _onCancel(self, event):
        gui.mainFrame.postPopup()
        self.Destroy()


def showTatipSettingsDialog(parent, currentSettings, onSave):
    """Create and show the Tatip settings dialog."""
    dialog = TatipSettingsDialog(parent, currentSettings, onSave)
    gui.mainFrame.prePopup()
    dialog.Show()
    dialog.Raise()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("PPAWakeUp")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lastTapTime = 0.0
        self._tapCount = 0
        self._tapThreshold = 0.5
        self._pendingCall = None
        self._restartInProgress = False
        self._restartLock = threading.Lock()
        self._lastSuccessfulStartTime = 0.0
        self._dialogWatchdogCall = None

        self._settings = self._loadSettings()

        self._originalSpeak = speechModule.speak
        speechModule.speak = self._filteredSpeak

    def _getSettingsPath(self):
        settingsDir = os.path.join(globalVars.appArgs.configPath, *_SETTINGS_SUBFOLDER.split(os.sep))
        return os.path.join(settingsDir, _SETTINGS_FILE_NAME)

    def _loadSettings(self):
        settingsPath = self._getSettingsPath()
        mergedSettings = dict(_DEFAULT_SETTINGS)
        try:
            if os.path.exists(settingsPath):
                with open(settingsPath, "r", encoding="utf-8") as settingsFile:
                    storedSettings = json.load(settingsFile)
                if isinstance(storedSettings, dict):
                    mergedSettings.update(storedSettings)
        except (OSError, ValueError) as e:
            logHandler.log.debug(f"Failed to load PPAWakeUp settings, using defaults: {e}")
        return mergedSettings

    def _saveSettings(self, updatedSettings):
        self._settings = updatedSettings
        settingsPath = self._getSettingsPath()
        try:
            os.makedirs(os.path.dirname(settingsPath), exist_ok=True)
            with open(settingsPath, "w", encoding="utf-8") as settingsFile:
                json.dump(self._settings, settingsFile, indent=2)
        except OSError as e:
            logHandler.log.error(f"Failed to save PPAWakeUp settings: {e}")

    def _filteredSpeak(self, sequence, *args, **kwargs):
        """Filter speech sequence to remove characters that crash PPA Tatip."""
        if not self._settings.get("skipCjkCharacters", True):
            self._originalSpeak(sequence, *args, **kwargs)
            return

        try:
            filtered = []
            for item in sequence:
                if isinstance(item, str):
                    # Keep only characters that are not within the forbidden range
                    cleaned = ''.join(ch for ch in item if not self._isCharBlockedForTatip(ch))
                    filtered.append(cleaned)
                else:
                    filtered.append(item)
        except Exception as e:
            # A failure in filtering must never take NVDA's entire speech
            # output down with it; fall back to speaking the sequence
            # unfiltered rather than leaving the user with total silence.
            logHandler.log.error(f"PPAWakeUp speech filter failed, speaking unfiltered: {e}")
            self._originalSpeak(sequence, *args, **kwargs)
            return

        # If filtering stripped every character out of a plain-text-only
        # sequence, there is nothing left worth sending downstream. PPA
        # Tatip's own file-based synth protocol still receives an
        # empty-text payload in this case (confirmed against its own
        # sapi_input.txt), so sending it serves no purpose and only risks
        # feeding Tatip a degenerate request.
        if filtered and all(isinstance(item, str) for item in filtered):
            if not ''.join(filtered).strip():
                return

        self._originalSpeak(filtered, *args, **kwargs)

    @staticmethod
    def _isCharBlockedForTatip(ch):
        """Return True if the character falls within any forbidden Unicode range."""
        cp = ord(ch)
        for low, high in _FORBIDDEN_RANGES:
            if low <= cp <= high:
                return True
        return False

    def terminate(self):
        if speechModule.speak is self._filteredSpeak:
            speechModule.speak = self._originalSpeak
        else:
            # Another add-on has patched speech.speak on top of ours since
            # load. Forcibly restoring here would silently erase that
            # add-on's active patch instead of unwinding cleanly, which is
            # a known cause of NVDA speech going completely silent after a
            # plugin reload. Leave it in place; whichever add-on patched
            # last is responsible for restoring the layer beneath it.
            logHandler.log.debug(
                "PPAWakeUp: speech.speak was patched by another add-on after ours; leaving it in place"
            )
        if self._pendingCall:
            self._pendingCall.Stop()
            self._pendingCall = None
        if self._dialogWatchdogCall:
            self._dialogWatchdogCall.Stop()
            self._dialogWatchdogCall = None
        super().terminate()

    def _findTatipPath(self):
        primary = os.path.expandvars(r"%LocalAppData%\Programs\PPA Tatip\interface\windows_tatip.exe")
        if os.path.exists(primary):
            return primary
        for base in [r"C:\Program Files", r"C:\Program Files (x86)"]:
            candidate = os.path.join(base, "PPA Tatip", "interface", "windows_tatip.exe")
            if os.path.exists(candidate):
                return candidate
        return None

    def _isProcessRunning(self, processName):
        try:
            result = subprocess.run(
                ["tasklist", "/fi", f"IMAGENAME eq {processName}", "/nh"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return processName.lower() in result.stdout.lower()
        except Exception:
            return True

    def _pollUntil(self, conditionFunc, timeoutSec, intervalSec):
        """Repeatedly evaluate conditionFunc until it returns True or the timeout elapses."""
        deadline = time.time() + timeoutSec
        while time.time() < deadline:
            if conditionFunc():
                return True
            time.sleep(intervalSec)
        return conditionFunc()

    def _forceKillTatip(self):
        processName = _TATIP_PROCESS_NAME
        try:
            subprocess.run(
                ["taskkill", "/f", "/t", "/im", processName],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass
        if self._pollUntil(lambda: not self._isProcessRunning(processName), timeoutSec=0.8, intervalSec=0.1):
            return True

        try:
            subprocess.run(
                ["powershell", "-Command", f"Stop-Process -Name '{processName.replace('.exe','')}' -Force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass
        if self._pollUntil(lambda: not self._isProcessRunning(processName), timeoutSec=1.0, intervalSec=0.15):
            return True

        try:
            subprocess.run(
                ["wmic", "process", "where", f"name='{processName}'", "delete"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass
        return self._pollUntil(lambda: not self._isProcessRunning(processName), timeoutSec=0.6, intervalSec=0.1)

    def script_windows_p_tap(self, gesture):
        _forceReleaseWindowsModifier()

        now = time.time()
        if now - self._lastTapTime > self._tapThreshold:
            self._tapCount = 0
        self._tapCount += 1
        self._lastTapTime = now

        if self._pendingCall:
            self._pendingCall.Stop()
            self._pendingCall = None

        self._pendingCall = wx.CallLater(
            int(self._tapThreshold * 1000),
            self._executeTapAction
        )

    script_windows_p_tap.__doc__ = _("Wake up PPA Tatip (single tap), Open options (double tap), Open menu (triple tap)")
    script_windows_p_tap.category = scriptCategory

    def _executeTapAction(self):
        self._pendingCall = None
        if self._tapCount == 1:
            self._startTatip()
        elif self._tapCount == 2:
            self._openTatipOption()
        elif self._tapCount >= 3:
            self._showMenuFrame()
        self._tapCount = 0

    def _startTatip(self):
        # Repeated windows+p presses within a few seconds of a launch that
        # already confirmed running were observed force-killing a Tatip
        # process that had only just finished starting, producing a
        # self-defeating retry spiral instead of a recovery. If the last
        # launch succeeded very recently, skip the kill/relaunch entirely.
        if time.time() - self._lastSuccessfulStartTime < _RESTART_COOLDOWN_SEC:
            ui.message(_("PPA Tatip is already awake"))
            _beep(200, 100)
            return

        with self._restartLock:
            if self._restartInProgress:
                ui.message(_("Already trying to wake up PPA Tatip, please wait"))
                return
            self._restartInProgress = True
        try:
            def worker():
                try:
                    tatipPath = self._findTatipPath()
                    if not tatipPath:
                        ui.message(_("Error: windows_tatip.exe not found. Please ensure PPA Tatip is installed."))
                        _beep(500, 500)
                        logHandler.log.error("windows_tatip.exe not found")
                        return

                    ui.message(_("Wake up"))
                    _beep(100, 100)

                    killed = self._forceKillTatip()
                    if not killed:
                        logHandler.log.warning("Force kill may not have succeeded, attempting launch anyway")

                    processName = _TATIP_PROCESS_NAME
                    maxAttempts = 3 if self._settings.get("autoRetryWakeUp", True) else 1
                    launched = False
                    for attempt in range(1, maxAttempts + 1):
                        subprocess.Popen(
                            [tatipPath],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        if self._pollUntil(lambda: self._isProcessRunning(processName), timeoutSec=_LAUNCH_CONFIRM_TIMEOUT_SEC, intervalSec=0.15):
                            launched = True
                            self._lastSuccessfulStartTime = time.time()
                            break
                        logHandler.log.warning(f"PPA Tatip launch attempt {attempt} did not confirm running, retrying")

                    if not launched:
                        ui.message(_("PPA Tatip did not confirm startup. Please try Windows+P again."))
                        _beep(400, 300)
                except Exception as e:
                    ui.message(_("Unexpected error: {error}").format(error=str(e)))
                    _beep(500, 500)
                    logHandler.log.error("startTatip error: %s", str(e))
                finally:
                    with self._restartLock:
                        self._restartInProgress = False

            threading.Thread(target=worker, daemon=True).start()
        except Exception:
            with self._restartLock:
                self._restartInProgress = False

    def _openTatipOption(self):
        def worker():
            try:
                optionPath = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\openoption.exe")
                if not os.path.exists(optionPath):
                    ui.message(_("Error: openoption.exe not found. Please ensure PPA Tatip is installed."))
                    _beep(500, 500)
                    logHandler.log.error("openoption.exe not found")
                    return
                ui.message(_("Option"))
                subprocess.Popen([optionPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                ui.message(_("Error: Failed to open PPA Tatip options - {error}").format(error=str(e)))
                _beep(500, 500)
                logHandler.log.error("openTatipOption error: %s", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _showMenuFrame(self):
        """Open the Tatip management menu as a small window."""
        callbackMap = {
            _("Tatip reader setting"): self._showSettingsDialog,
            _("Backup Tatip dictionary"): self._backupDictionary,
            _("Restore Tatip dictionary"): self._restoreDictionary,
            _("Open Tatip folder"): self._openTatipFolder,
        }
        try:
            showTatipMenu(gui.mainFrame, callbackMap, title=_("PPA Tatip \u2013 Menu"))
        except Exception as e:
            logHandler.log.error("Failed to open Tatip menu: %s", str(e))

    def _showSettingsDialog(self):
        """Open the Tatip reader setting window."""
        try:
            showTatipSettingsDialog(gui.mainFrame, self._settings, self._saveSettings)
        except Exception as e:
            logHandler.log.error("Failed to open Tatip settings dialog: %s", str(e))

    def _getBackupDir(self):
        backupDir = os.path.join(globalVars.appArgs.configPath, "ChaiChaimee", "PPAWakeUp")
        os.makedirs(backupDir, exist_ok=True)
        return backupDir

    def _backupDictionary(self):
        def worker():
            try:
                source = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
                if not os.path.exists(source):
                    ui.message(_("Error: userdict.txt not found at source location."))
                    _beep(500, 500)
                    return

                destDir = self._getBackupDir()
                dest = os.path.join(destDir, "userdict.txt")
                shutil.copy2(source, dest)
                if os.path.exists(dest):
                    ui.message(_("Backup completed: {dest}").format(dest=dest))
                    _beep(800, 200)
                else:
                    ui.message(_("Backup failed: file not written to {dest}").format(dest=dest))
                    _beep(500, 500)
            except Exception as e:
                ui.message(_("Backup failed: {error}").format(error=str(e)))
                _beep(500, 500)
                logHandler.log.error("Backup error: %s", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _restoreDictionary(self):
        def worker():
            try:
                source = os.path.join(self._getBackupDir(), "userdict.txt")
                if not os.path.exists(source):
                    ui.message(_("Error: No backup file found. Please perform a backup first."))
                    _beep(500, 500)
                    return

                target = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
                shutil.copy2(source, target)
                ui.message(_("Dictionary restored. Reloading PPA Tatip..."))
                _beep(800, 200)

                self._startTatip()
            except Exception as e:
                ui.message(_("Restore failed: {error}").format(error=str(e)))
                _beep(500, 500)
                logHandler.log.error("Restore error: %s", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _openTatipFolder(self):
        def worker():
            try:
                folderPath = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface")
                if not os.path.isdir(folderPath):
                    ui.message(_("Error: Tatip folder not found."))
                    _beep(500, 500)
                    return
                os.startfile(folderPath)
                ui.message(_("Tatip folder opened"))
            except Exception as e:
                ui.message(_("Failed to open folder: {error}").format(error=str(e)))
                _beep(500, 500)
                logHandler.log.error("OpenTatipFolder error: %s", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _isDialogActionButton(self, obj):
        try:
            if obj is None or obj.role != controlTypes.Role.BUTTON:
                return False
            name = getattr(obj, "name", None)
            if not name:
                return False
            return name.strip().lower() in _DIALOG_ACTION_BUTTON_LABELS
        except Exception:
            return False

    def _scheduleDialogWatchdog(self):
        """Verify PPA Tatip survives a short window after a risky button focus event."""
        if self._dialogWatchdogCall:
            self._dialogWatchdogCall.Stop()
        self._dialogWatchdogCall = wx.CallLater(
            _DIALOG_WATCHDOG_DELAY_MS,
            self._checkDialogWatchdog
        )

    def _checkDialogWatchdog(self):
        self._dialogWatchdogCall = None

        def worker():
            if not self._isProcessRunning(_TATIP_PROCESS_NAME):
                logHandler.log.warning("PPA Tatip crash detected after dialog button focus, restarting")
                self._startTatip()

        threading.Thread(target=worker, daemon=True).start()

    def event_gainFocus(self, obj, nextHandler):
        if self._settings.get("protectDialogButtonCrash", True) and self._isDialogActionButton(obj):
            self._scheduleDialogWatchdog()
        nextHandler()

    __gestures = {
        "kb:windows+p": "windows_p_tap",
    }
