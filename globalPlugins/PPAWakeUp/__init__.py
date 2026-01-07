# __init__.py
# Copyright (C) 2026 'Chai Chaimee'
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import addonHandler
import ui
import subprocess
import os
import winsound
import logging
import time
import wx

# Initialize translation
addonHandler.initTranslation()

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='nvda_plugin.log')

# Global variables for tap detection
_last_tap_time = 0
_tap_count = 0
_triple_tap_threshold = 0.5  # 500ms

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("PPAWakeUp")
    
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
    
    def script_windows_p_tap(self, gesture):
        """Handle Windows+P single, double, and triple tap"""
        global _last_tap_time, _tap_count
        current_time = time.time()
        
        if current_time - _last_tap_time > _triple_tap_threshold:
            _tap_count = 0
        
        _tap_count += 1
        _last_tap_time = current_time
        
        def execute_action():
            global _tap_count
            if _tap_count == 1:
                self._start_tatip()
            elif _tap_count == 2:
                self._open_tatip_option()
            elif _tap_count >= 3:
                self._open_tatip_dictionary()
            
            _tap_count = 0
        
        wx.CallLater(int(_triple_tap_threshold * 1000), execute_action)
    
    script_windows_p_tap.__doc__ = _("Wake up PPA Tatip (single tap), Open options (double tap), Open dictionary (triple tap)")
    script_windows_p_tap.category = scriptCategory

    def _start_tatip(self):
        """Wake up PPA Tatip"""
        try:
            tatip_path = self.find_tatip_path()
            logging.debug(f"tatip_path: {tatip_path}")

            if not tatip_path:
                ui.message(_("Error: windows_tatip.exe not found. Please ensure PPA Tatip is installed."))
                winsound.Beep(500, 500)
                logging.error("windows_tatip.exe not found in expected locations")
                return

            ui.message(_("Wake up"))
            winsound.Beep(100, 100)

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
                # Start tatip without hiding
                subprocess.Popen(
                    [tatip_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logging.debug("windows_tatip.exe started")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                ui.message(_("Error: Failed to start windows_tatip.exe - {error}").format(error=str(e)))
                winsound.Beep(500, 500)
                logging.error(f"Failed to start windows_tatip.exe: {str(e)}")

        except Exception as e:
            ui.message(_("Unexpected error: {error}").format(error=str(e)))
            winsound.Beep(500, 500)
            logging.error(f"Unexpected error in start_tatip: {str(e)}")

    def _open_tatip_option(self):
        """Open PPA Tatip options window"""
        try:
            option_path = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\openoption.exe")
            if not os.path.exists(option_path):
                ui.message(_("Error: openoption.exe not found. Please ensure PPA Tatip is installed."))
                winsound.Beep(500, 500)
                logging.error(f"openoption.exe not found at: {option_path}")
                return

            ui.message(_("Option"))
            subprocess.Popen(
                [option_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logging.debug("openoption.exe started")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            ui.message(_("Error: Failed to open PPA Tatip options - {error}").format(error=str(e)))
            winsound.Beep(500, 500)
            logging.error(f"Failed to open openoption.exe: {str(e)}")
        except Exception as e:
            ui.message(_("Unexpected error: {error}").format(error=str(e)))
            winsound.Beep(500, 500)
            logging.error(f"Unexpected error in open_tatip_option: {str(e)}")

    def _open_tatip_dictionary(self):
        """Open PPA Tatip dictionary file"""
        try:
            # Get the dictionary file path
            dict_path = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\PPA Tatip\interface\userdict.txt")
            
            if not os.path.exists(dict_path):
                ui.message(_("Error: userdict.txt not found. Please ensure PPA Tatip is installed."))
                winsound.Beep(500, 500)
                logging.error(f"userdict.txt not found at: {dict_path}")
                return
            
            ui.message(_("Dictionary"))
            
            # Open the file with default text editor
            os.startfile(dict_path)
            logging.debug(f"Opened dictionary file: {dict_path}")
            
        except Exception as e:
            ui.message(_("Error: Failed to open dictionary file - {error}").format(error=str(e)))
            winsound.Beep(500, 500)
            logging.error(f"Failed to open dictionary file: {str(e)}")

    # Set gestures
    __gestures = {
        "kb:windows+p": "windows_p_tap",
    }