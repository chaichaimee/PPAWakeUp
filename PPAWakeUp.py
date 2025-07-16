# Copyright (C) 2025 ['chai chaimee]
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import ui
import subprocess
import os
import winsound
import logging
import synthDriverHandler
import config
import ctypes
import time
import threading
from ctypes import wintypes

# ตั้งค่าการล็อก
logging.basicConfig(level=logging.DEBUG, filename='nvda_plugin.log')

# Set the data structure for Windows API
class LUID(ctypes.Structure):
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG),
    ]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", wintypes.DWORD),
    ]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1),
    ]

SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "PPAWakeUp"

    def find_tatip_path(self):
        """Find the path to windows_tatip.exe"""
        primary_path = os.path.expandvars(r"%LocalAppData%\Programs\PPA Tatip\interface\windows_tatip.exe")
        if os.path.exists(primary_path):
            return primary_path

        for base_dir in [r"C:\Program Files", r"C:\Program Files (x86)"]:
            potential_path = os.path.join(base_dir, "PPA Tatip", "interface", "windows_tatip.exe")
            if os.path.exists(potential_path):
                return potential_path

        return None

    def script_start_tatip(self, gesture):
        """wake up"""
        try:
            tatip_path = self.find_tatip_path()
            logging.debug(f"tatip_path: {tatip_path}")

            if not tatip_path:
                ui.message("Error: windows_tatip.exe not found. Please ensure PPA Tatip is installed.")
                winsound.Beep(500, 500)
                logging.error("windows_tatip.exe not found in expected locations")
                return

            ui.message("Wake up")
            winsound.Beep(100, 100)
            _basePath = os.path.dirname(__file__)
            nircmd_path = os.path.join(_basePath, "nircmd.exe")

            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", "windows_tatip.exe"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=0.3,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logging.debug("Existing windows_tatip process terminated")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                logging.debug("No existing windows_tatip process or taskkill failed")

            try:
                subprocess.run(
                    [nircmd_path, "exec", "hide", tatip_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                logging.debug("windows_tatip.exe started")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                ui.message(f"Error: Failed to start windows_tatip.exe - {str(e)}")
                winsound.Beep(500, 500)
                logging.error(f"Failed to start windows_tatip.exe: {str(e)}")

        except Exception as e:
            ui.message(f"Unexpected error: {str(e)}")
            winsound.Beep(500, 500)
            logging.error(f"Unexpected error in start_tatip: {str(e)}")

    script_start_tatip.__doc__ = _("wake up")
    script_start_tatip.category = scriptCategory

    def script_vol_up(self, gesture):
        """Increase NVDA speech volume by 5%"""
        try:
            synth = synthDriverHandler.getSynth()
            if not synth:
                ui.message("Error: No synthesizer available")
                logging.error("No synthesizer available for volume adjustment")
                return
            current_volume = synth.volume
            new_volume = min(current_volume + 5, 100)
            synth.volume = new_volume
            config.conf["speech"][synth.name]["volume"] = new_volume
            config.conf.save()
            ui.message(f"{new_volume}%")
            logging.debug(f"NVDA volume increased to {new_volume}% and saved")
        except Exception as e:
            ui.message("Error: Failed to increase NVDA volume")
            logging.error(f"Failed to increase NVDA volume: {str(e)}")

    script_vol_up.__doc__ = _("Increase NVDA volume 5%")
    script_vol_up.category = scriptCategory

    def script_vol_down(self, gesture):
        """Decrease NVDA speech volume by 5%"""
        try:
            synth = synthDriverHandler.getSynth()
            if not synth:
                ui.message("Error: No synthesizer available")
                logging.error("No synthesizer available for volume adjustment")
                return
            current_volume = synth.volume
            new_volume = max(current_volume - 5, 0)
            synth.volume = new_volume
            config.conf["speech"][synth.name]["volume"] = new_volume
            config.conf.save()
            ui.message(f"{new_volume}%")
            logging.debug(f"NVDA volume decreased to {new_volume}% and saved")
        except Exception as e:
            ui.message("Error: Failed to decrease NVDA volume")
            logging.error(f"Failed to decrease NVDA volume: {str(e)}")

    script_vol_down.__doc__ = _("Decrease NVDA volume 5%")
    script_vol_down.category = scriptCategory

    def script_open_tatip_option(self, gesture):
        """Open PPA Tatip options window"""
        try:
            option_path = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\openoption.exe")
            if not os.path.exists(option_path):
                ui.message("Error: openoption.exe not found. Please ensure PPA Tatip is installed.")
                winsound.Beep(500, 500)
                logging.error(f"openoption.exe not found at: {option_path}")
                return

            ui.message("option")
            winsound.Beep(100, 100)
            subprocess.run(
                [option_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            logging.debug("openoption.exe started")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            ui.message(f"Error: Failed to open PPA Tatip options - {str(e)}")
            winsound.Beep(500, 500)
            logging.error(f"Failed to open openoption.exe: {str(e)}")
        except Exception as e:
            ui.message(f"Unexpected error: {str(e)}")
            winsound.Beep(500, 500)
            logging.error(f"Unexpected error in open_tatip_option: {str(e)}")

    script_open_tatip_option.__doc__ = _("Open PPA Tatip options window")
    script_open_tatip_option.category = scriptCategory

    # ============ Start function/Re -shut down the machine ============ #
    def _enable_shutdown_privilege(self):
        """Open the right to close the system."""
        try:
            # Opening the process of the process
            token = wintypes.HANDLE()
            if not ctypes.windll.advapi32.OpenProcessToken(
                ctypes.windll.kernel32.GetCurrentProcess(),
                TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                ctypes.byref(token)
            ):
                return False

            # Search Luid for rights
            luid = LUID()
            if not ctypes.windll.advapi32.LookupPrivilegeValueW(
                None,
                SE_SHUTDOWN_NAME,
                ctypes.byref(luid)
            ):
                return False

            # Adjust rights
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

            if not ctypes.windll.advapi32.AdjustTokenPrivileges(
                token,
                False,
                ctypes.byref(tp),
                ctypes.sizeof(tp),
                None,
                None
            ):
                return False

            return True
        except Exception as e:
            logging.error(f"Error enabling shutdown privilege: {str(e)}")
            return False

    def _shutdown_system(self, reboot=False):
        """Close or resort system"""
        try:
            # Custom announcement Windows API
            EWX_SHUTDOWN = 0x00000001
            EWX_REBOOT = 0x00000002
            EWX_FORCEIFHUNG = 0x00000010

            # Requesting the right to close the system
            if not self._enable_shutdown_privilege():
                ui.message("Cannot get shutdown privilege")
                winsound.Beep(500, 500)
                return

# Notify users and wait
            ui.message("Restart" if reboot else "Shutdown")
            
            time.sleep(3)

            # Call Windows API
            flags = (EWX_REBOOT if reboot else EWX_SHUTDOWN) | EWX_FORCEIFHUNG
            if not ctypes.windll.user32.ExitWindowsEx(flags, 0):
                error = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"ExitWindowsEx failed with error {error}")

        except Exception as e:
            ui.message(f"Error: {str(e)}")
            winsound.Beep(500, 500)
            logging.error(f"Shutdown failed: {str(e)}")

    def script_restart(self, gesture):
        """restart"""
        threading.Thread(target=self._shutdown_system, args=(True,)).start()

    def script_shutdown(self, gesture):
        """shutdown"""
        threading.Thread(target=self._shutdown_system, args=(False,)).start()

    # set gesture
    __gestures = {
        "kb:windows+p": "start_tatip",
        "kb:nvda+shift+pageup": "vol_up",
        "kb:nvda+shift+pagedown": "vol_down",
        "kb:alt+windows+r": "restart",
        "kb:alt+windows+s": "shutdown",
        "kb:windows+alt+p": "open_tatip_option",
    }