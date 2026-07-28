# __init__.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import addonHandler
import ui
import subprocess
import os
import winsound
import time
import threading
import core
import logHandler
import wx
import gui
import shutil
import speech.speech as speechModule
import globalVars

addonHandler.initTranslation()


class TatipMenu(wx.Frame):
	"""A simple list‑based menu for PPA Tatip dictionary management."""

	def __init__(self, parent, callbackMap, title=_("PPA Tatip – Menu")):
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


def showTatipMenu(parent, callbackMap, title=_("PPA Tatip – Menu")):
	"""Create and show the Tatip menu frame."""
	TatipMenu(parent, callbackMap, title)


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

		self._originalSpeak = speechModule.speak
		speechModule.speak = self._filteredSpeak

	def _filteredSpeak(self, sequence, *args, **kwargs):
		"""Filter speech sequence to remove characters that crash PPA Tatip."""
		filtered = []
		for item in sequence:
			if isinstance(item, str):
				cleaned = ''.join(ch for ch in item if self._isAllowedChar(ch))
				filtered.append(cleaned)
			else:
				filtered.append(item)
		self._originalSpeak(filtered, *args, **kwargs)

	def _isAllowedChar(self, ch):
		"""Return True if character is within allowed Unicode ranges for PPA Tatip."""
		cp = ord(ch)
		if 0x0020 <= cp <= 0x007E:
			return True
		if 0x00A0 <= cp <= 0x00FF:
			return True
		if 0x0E00 <= cp <= 0x0E7F:
			return True
		if 0x2000 <= cp <= 0x206F:
			return True
		return False

	def terminate(self):
		speechModule.speak = self._originalSpeak
		if self._pendingCall:
			self._pendingCall.Stop()
			self._pendingCall = None
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

	def _forceKillTatip(self):
		processName = "windows_tatip.exe"
		try:
			subprocess.run(
				["taskkill", "/f", "/t", "/im", processName],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=2,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			time.sleep(0.5)
		except Exception:
			pass
		if not self._isProcessRunning(processName):
			return True

		try:
			subprocess.run(
				["powershell", "-Command", f"Stop-Process -Name '{processName.replace('.exe','')}' -Force"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=3,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			time.sleep(1.0)
		except Exception:
			pass
		if not self._isProcessRunning(processName):
			return True

		try:
			subprocess.run(
				["wmic", "process", "where", f"name='{processName}'", "delete"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=2,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			time.sleep(0.5)
		except Exception:
			pass
		return not self._isProcessRunning(processName)

	def script_windows_p_tap(self, gesture):
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
		with self._restartLock:
			if self._restartInProgress:
				return
			self._restartInProgress = True
		try:
			def worker():
				try:
					tatipPath = self._findTatipPath()
					if not tatipPath:
						ui.message(_("Error: windows_tatip.exe not found. Please ensure PPA Tatip is installed."))
						winsound.Beep(500, 500)
						logHandler.log.error("windows_tatip.exe not found")
						return

					ui.message(_("Wake up"))
					winsound.Beep(100, 100)

					killed = self._forceKillTatip()
					if not killed:
						logHandler.log.warning("Force kill may not have succeeded, attempting launch anyway")

					subprocess.Popen(
						[tatipPath],
						stdout=subprocess.PIPE,
						stderr=subprocess.PIPE
					)
				except Exception as e:
					ui.message(_("Unexpected error: {error}").format(error=str(e)))
					winsound.Beep(500, 500)
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
					winsound.Beep(500, 500)
					logHandler.log.error("openoption.exe not found")
					return
				ui.message(_("Option"))
				subprocess.Popen([optionPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			except Exception as e:
				ui.message(_("Error: Failed to open PPA Tatip options - {error}").format(error=str(e)))
				winsound.Beep(500, 500)
				logHandler.log.error("openTatipOption error: %s", str(e))

		threading.Thread(target=worker, daemon=True).start()

	def _showMenuFrame(self):
		"""Open the Tatip management menu as a small window."""
		callbackMap = {
			_("Backup Tatip dictionary"): self._backupDictionary,
			_("Restore Tatip dictionary"): self._restoreDictionary,
			_("Open Tatip folder"): self._openTatipFolder,
		}
		try:
			showTatipMenu(gui.mainFrame, callbackMap, title=_("PPA Tatip – Menu"))
		except Exception as e:
			logHandler.log.error("Failed to open Tatip menu: %s", str(e))

	def _getBackupDir(self):
		"""Ensure and return the backup directory path.
		Works with both installed and portable NVDA configurations.
		Uses add-on name 'PPAWakeUp' as folder name.
		"""
		backupDir = os.path.join(globalVars.appArgs.configPath, "ChaiChaimee", "PPAWakeUp")
		os.makedirs(backupDir, exist_ok=True)
		return backupDir

	def _backupDictionary(self):
		def worker():
			try:
				source = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
				if not os.path.exists(source):
					ui.message(_("Error: userdict.txt not found at source location."))
					winsound.Beep(500, 500)
					return

				destDir = self._getBackupDir()
				dest = os.path.join(destDir, "userdict.txt")
				shutil.copy2(source, dest)
				# Double-check that the file was actually written
				if os.path.exists(dest):
					ui.message(_("Backup completed: {dest}").format(dest=dest))
					winsound.Beep(800, 200)  # Success sound
				else:
					ui.message(_("Backup failed: file not written to {dest}").format(dest=dest))
					winsound.Beep(500, 500)
			except Exception as e:
				ui.message(_("Backup failed: {error}").format(error=str(e)))
				winsound.Beep(500, 500)
				logHandler.log.error("Backup error: %s", str(e))

		threading.Thread(target=worker, daemon=True).start()

	def _restoreDictionary(self):
		def worker():
			try:
				source = os.path.join(self._getBackupDir(), "userdict.txt")
				if not os.path.exists(source):
					ui.message(_("Error: No backup file found. Please perform a backup first."))
					winsound.Beep(500, 500)
					return

				target = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
				shutil.copy2(source, target)
				ui.message(_("Dictionary restored. Reloading PPA Tatip..."))
				winsound.Beep(800, 200)

				self._startTatip()
			except Exception as e:
				ui.message(_("Restore failed: {error}").format(error=str(e)))
				winsound.Beep(500, 500)
				logHandler.log.error("Restore error: %s", str(e))

		threading.Thread(target=worker, daemon=True).start()

	def _openTatipFolder(self):
		def worker():
			try:
				folderPath = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface")
				if not os.path.isdir(folderPath):
					ui.message(_("Error: Tatip folder not found."))
					winsound.Beep(500, 500)
					return
				os.startfile(folderPath)
				ui.message(_("Tatip folder opened"))
			except Exception as e:
				ui.message(_("Failed to open folder: {error}").format(error=str(e)))
				winsound.Beep(500, 500)
				logHandler.log.error("OpenTatipFolder error: %s", str(e))

		threading.Thread(target=worker, daemon=True).start()

	__gestures = {
		"kb:windows+p": "windows_p_tap",
	}