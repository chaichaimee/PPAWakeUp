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

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("PPAWakeUp")

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._lastTapTime = 0.0
		self._tapCount = 0
		self._tapThreshold = 0.5
		self._pendingCall = None

	def _findTatipPath(self):
		primary = os.path.expandvars(r"%LocalAppData%\Programs\PPA Tatip\interface\windows_tatip.exe")
		if os.path.exists(primary):
			return primary
		for base in [r"C:\Program Files", r"C:\Program Files (x86)"]:
			candidate = os.path.join(base, "PPA Tatip", "interface", "windows_tatip.exe")
			if os.path.exists(candidate):
				return candidate
		return None

	def script_windows_p_tap(self, gesture):
		now = time.time()
		if now - self._lastTapTime > self._tapThreshold:
			self._tapCount = 0
		self._tapCount += 1
		self._lastTapTime = now

		if self._pendingCall:
			self._pendingCall.Stop()
			self._pendingCall = None

		self._pendingCall = core.callLater(
			int(self._tapThreshold * 1000),
			self._executeTapAction
		)

	script_windows_p_tap.__doc__ = _("Wake up PPA Tatip (single tap), Open options (double tap), Open dictionary (triple tap)")
	script_windows_p_tap.category = scriptCategory

	def _executeTapAction(self):
		self._pendingCall = None
		if self._tapCount == 1:
			self._startTatip()
		elif self._tapCount == 2:
			self._openTatipOption()
		elif self._tapCount >= 3:
			self._openTatipDictionary()
		self._tapCount = 0

	def _forceKillTatip(self):
		"""Try multiple methods to force-kill windows_tatip.exe. Returns True if process is no longer running."""
		processName = "windows_tatip.exe"
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

		# Wait a moment for cleanup
		time.sleep(0.5)

		# Check if process still exists
		try:
			checkResult = subprocess.run(
				["tasklist", "/fi", f"IMAGENAME eq {processName}", "/nh"],
				capture_output=True,
				text=True,
				timeout=2,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			if processName.lower() not in checkResult.stdout.lower():
				return True
		except Exception:
			pass

		# Process still running, try alternative kill commands
		killMethods = [
			["taskkill", "/f", "/im", processName],
			["tskill", processName],
			["wmic", "process", "where", f"name='{processName}'", "delete"],
		]
		for method in killMethods:
			try:
				subprocess.run(
					method,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					timeout=2,
					creationflags=subprocess.CREATE_NO_WINDOW
				)
				time.sleep(0.3)
				# Re-check
				checkResult = subprocess.run(
					["tasklist", "/fi", f"IMAGENAME eq {processName}", "/nh"],
					capture_output=True,
					text=True,
					timeout=2,
					creationflags=subprocess.CREATE_NO_WINDOW
				)
				if processName.lower() not in checkResult.stdout.lower():
					return True
			except Exception:
				continue

		# Final check
		try:
			finalCheck = subprocess.run(
				["tasklist", "/fi", f"IMAGENAME eq {processName}", "/nh"],
				capture_output=True,
				text=True,
				timeout=2,
				creationflags=subprocess.CREATE_NO_WINDOW
			)
			return processName.lower() not in finalCheck.stdout.lower()
		except Exception:
			return False

	def _startTatip(self):
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

		threading.Thread(target=worker, daemon=True).start()

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

	def _openTatipDictionary(self):
		def worker():
			try:
				dictPath = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
				if not os.path.exists(dictPath):
					ui.message(_("Error: userdict.txt not found. Please ensure PPA Tatip is installed."))
					winsound.Beep(500, 500)
					logHandler.log.error("userdict.txt not found")
					return
				ui.message(_("Dictionary"))
				os.startfile(dictPath)
			except Exception as e:
				ui.message(_("Error: Failed to open dictionary file - {error}").format(error=str(e)))
				winsound.Beep(500, 500)
				logHandler.log.error("openTatipDictionary error: %s", str(e))

		threading.Thread(target=worker, daemon=True).start()

	__gestures = {
		"kb:windows+p": "windows_p_tap",
	}