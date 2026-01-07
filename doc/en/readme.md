# PPAWakeUp

![NVDA Logo](https://www.nvaccess.org/files/nvda/documentation/userGuide/images/nvda.ico)

**Quick PPA Tatip control with smart tap gestures**

---

**Author:** chai chaimee  
**Repository:** [https://github.com/chaichaimee/PPAWakeUp](https://github.com/chaichaimee/PPAWakeUp)

---

## Description

**PPAWakeUp** is a streamlined NVDA add-on designed to provide quick access to PPA Tatip Thai speech synthesizer functions using a single hotkey with multiple tap combinations.

With just the **Windows+P** key combination, you can perform three essential functions depending on how many times you tap — keeping your workflow fast and interruption-free.

## Hot Keys

Single hotkey — multiple actions based on tap count:

- **Windows+P** (Single tap)  
  → **Wake up PPA Tatip**  
  Restarts the `windows_tatip.exe` process to ensure the synthesizer is running properly

- **Windows+P** (Double tap)  
  → **Open PPA Tatip Options**  
  Launches the configuration window (`openoption.exe`) for adjusting synthesizer settings

- **Windows+P** (Triple tap)  
  → **Open Tatip Dictionary File**  
  Opens the `userdict.txt` file for quick dictionary editing

> **Tip:**  
> Tap the keys in quick succession (similar to double-click timing).  
> The add-on detects 1, 2, or 3 taps within a short time window.

## Why Use PPAWakeUp?

This add-on is specially created for users who rely on the **PPA Tatip** Thai synthesizer.

It provides the most frequently used functions with a clean, minimalist approach — no extra commands cluttering your NVDA.

The tap-based interface is fast, intuitive, and efficient — perfect for daily use.

## Technical Details

- Hotkey: `Windows+P` (with tap detection)
- Supported gestures: 1 tap • 2 taps • 3 taps
- Actions:
  - Restart synthesizer
  - Open settings
  - Open user dictionary
- Minimal resource usage
- Designed specifically for PPA Tatip Thai speech engine

> **Note**  
> This add-on requires the PPA Tatip synthesizer to be installed on your system.

---

Made with ♡ for the Thai NVDA community