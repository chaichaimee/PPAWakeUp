![NVDA Logo](https://www.nvaccess.org/files/nvda/documentation/userGuide/images/nvda.ico)

# PPAWakeUp

Keep PPA Tatip awake, quiet, and crash-free, right from Windows+P.

**author:** chai chaimee  
**url:** https://github.com/chaichaimee/PPAWakeUp

## Introduction

PPAWakeUp is an NVDA add-on built to keep the third-party screen reading engine PPA Tatip running smoothly alongside NVDA.

PPA Tatip is known to silently stop working under certain conditions, such as when it is asked to speak certain Asian-language characters, or when a file dialog's action button (Open, OK, Save, Yes) receives focus right after the dialog appears. PPAWakeUp watches for these situations and steps in automatically, and it also gives you a single, familiar key press, Windows+P, to force-kill and relaunch PPA Tatip whenever it needs a fresh start.

Beyond crash recovery, the add-on bundles a small menu for everyday PPA Tatip maintenance: opening its options window, backing up and restoring your custom dictionary, and jumping straight to its installation folder.

### Hot Keys

**Windows+P**  
Single Tap : Wake up PPA Tatip (force-kill and relaunch it)  
Double Tap : Open PPA Tatip options  
Triple Tap : Open the PPA Tatip management menu  

PPAWakeUp counts how many times you press Windows+P in quick succession (within half a second of each press). It waits briefly after your last tap to see if another one is coming, then runs the action for the final tap count: one tap wakes PPA Tatip up, two taps opens its options window, and three or more taps opens the management menu.

> **Note:** This gesture is intercepted at a low level so that, whichever tap count you use, NVDA also forces the Windows key back up afterwards. This prevents Windows from thinking the key is still held down, which would otherwise block you from typing the letter "p" until you restart.

## Features

### Wake Up PPA Tatip (Single Tap)

A single Windows+P press force-kills any running copy of PPA Tatip and starts a fresh one. This is the main recovery action for when PPA Tatip has crashed or stopped responding.

Step by step, when you single-tap Windows+P:

1. NVDA announces "Wake up" and plays a short low beep.
2. The add-on locates windows_tatip.exe, checking the standard Local AppData install path first, then Program Files and Program Files (x86) as fallbacks.
3. If the executable cannot be found anywhere, you hear an error message and an alert beep, and the attempt stops.
4. The add-on tries to force-kill any existing PPA Tatip process, first with taskkill, then, if that does not confirm the process is gone, with PowerShell's Stop-Process, and finally with wmic as a last resort.
5. PPA Tatip is relaunched. The add-on then polls to confirm the process actually appears in the running task list, waiting up to about 2.5 seconds per attempt.
6. If the relaunch does not confirm within that time, the add-on retries automatically (up to three attempts in total by default, or only one attempt if automatic retry has been turned off in settings).
7. If PPA Tatip still has not confirmed after all attempts, you hear a message asking you to try Windows+P again, along with an alert beep.

If you have just successfully woken PPA Tatip up within the last 3 seconds, pressing Windows+P again is treated as unnecessary: NVDA tells you PPA Tatip is already awake and plays a short beep, rather than killing a process that only just finished starting.

All of this work happens on a background thread, so NVDA itself never freezes while PPA Tatip is being restarted, and repeated presses while a wake-up is already underway are answered with a "please wait" message instead of starting a second attempt.

### Open PPA Tatip Options (Double Tap)

Double-tapping Windows+P looks for openoption.exe inside PPA Tatip's interface folder under your user profile and launches it, announcing "Option" as it does. If the file cannot be found, you hear an error message and an alert beep.

### PPA Tatip Management Menu (Triple Tap)

Triple-tapping Windows+P opens a small floating list-box window with four choices: Tatip reader setting, Backup Tatip dictionary, Restore Tatip dictionary, and Open Tatip folder.

The menu window can be operated entirely from the keyboard: press Enter to activate the highlighted item, or Escape to close the menu without choosing anything. It also closes itself automatically if left untouched for 15 seconds, and that timeout resets every time you press a key inside it.

### Tatip Reader Setting Dialog

Opened from the management menu, this dialog offers three checkboxes that control the add-on's protective behaviors:

- Skip Chinese, Japanese and Korean characters when speaking
- Protect against crash when focusing Open/OK/Save buttons in dialogs
- Automatically retry wake up if PPA Tatip does not start

All three options are enabled by default. Choices are saved as soon as you click OK, and are reloaded automatically the next time NVDA starts.

### Automatic Speech Filtering for Problem Characters

PPAWakeUp installs itself in front of NVDA's own speech output. When the "Skip Chinese, Japanese and Korean characters when speaking" setting is enabled, every piece of text NVDA is about to speak is checked character by character against a large table of Unicode ranges known to make PPA Tatip stop working, covering CJK ideographs, Hiragana, Katakana, Hangul, Bopomofo, and several related scripts.

Any matching characters are silently removed before the text reaches PPA Tatip. If filtering happens to strip a plain-text announcement down to nothing at all, the add-on drops that announcement entirely rather than sending PPA Tatip an empty message. Should the filtering process itself ever fail for any reason, the add-on falls back to speaking the original, unfiltered text so that NVDA never goes silent because of this feature.

When NVDA shuts the add-on down, it restores NVDA's original speech function, unless another add-on has since layered its own patch on top, in which case PPAWakeUp leaves that patch alone so it is not accidentally erased.

### Dialog Button Crash Protection

When the "Protect against crash when focusing Open/OK/Save buttons in dialogs" setting is enabled, the add-on watches every object that gains focus. If a button with the name Open, OK, Save, or Yes (in English or Thai) receives focus, a 1.5 second watchdog timer starts.

When that timer fires, the add-on checks whether the PPA Tatip process is still running. If it has disappeared, the add-on concludes it crashed as a result of that button being focused and automatically starts the same wake-up sequence used by the single-tap Windows+P gesture, without any action needed from you.

### Backup Tatip Dictionary

Copies PPA Tatip's userdict.txt from its interface folder into a dedicated backup location inside your NVDA configuration folder. You hear a confirmation message with the destination path and a success beep, or an error message and alert beep if the source file cannot be found or the copy fails.

### Restore Tatip Dictionary

Copies the previously backed-up userdict.txt back into PPA Tatip's interface folder, then automatically triggers the same wake-up sequence as a single Windows+P tap so PPA Tatip reloads with the restored dictionary. If no backup file exists yet, you are told to perform a backup first.

### Open Tatip Folder

Opens PPA Tatip's interface folder directly in File Explorer, announcing "Tatip folder opened" on success, or an error message if the folder cannot be found.

### Settings Storage

All three checkbox settings are stored as JSON in a settings.json file, inside a ChaiChaimee\PPAWakeUp subfolder of your NVDA configuration directory. If the file is missing or cannot be read, the add-on falls back to its defaults (all three protections enabled) without interrupting startup.

## Support Me

If this tool has made your life easier, consider fueling the next update with a small donation.

[![Support me](https://img.shields.io/badge/Donate-Support%20Me-blue?style=for-the-badge&logo=stripe)](https://buy.stripe.com/dRm9AU1xQ3Ds22N6VK1VK01)

Your support means the world. Let's build something great together

---

&copy; 2026 Chai Chaimee NVDA Add-on Released under GNU GPL