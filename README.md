
PPAWakeUp Add-on for NVDA  
Summary  

PPAWakeUp is a powerful NVDA add-on designed to enhance accessibility by providing quick and efficient commands to control the PPA Tatip synthesizer, adjust NVDA speech volume, and manage Windows system operations, all without moving your hands from the keyboard.  
Description  

The PPAWakeUp add-on empowers NVDA users with seamless control over the PPA Tatip synthesizer and essential system functions. With a single keystroke, you can instantly restart the PPA Tatip process to ensure uninterrupted speech synthesis, open the PPA Tatip options window to configure settings or edit the pronunciation dictionary, adjust NVDA's speech volume quickly, or even restart or shut down Windows with ease. This add-on is designed for efficiency, accessibility, and minimal effort, making it an essential tool for users relying on the PPA Tatip synthesizer.
Features and Keybindings  

    Wake Up PPA Tatip (kb:windows+p): Instantly restarts the windows_tatip.exe process, ensuring the PPA Tatip synthesizer resumes operation immediately if it encounters issues.  
    Open PPA Tatip Options (kb:windows+alt+p): Opens the PPA Tatip options window (openoption.exe) for quick access to configuration settings and the pronunciation dictionary, allowing rapid customization of speech output.  
    Increase NVDA Volume (kb:nvda+shift+pageup): Increases the NVDA speech volume by 5% with each press, providing precise and rapid control over speech output loudness.  
    Decrease NVDA Volume (kb:nvda+shift+pagedown): Decreases the NVDA speech volume by 5% with each press, allowing fine-tuned adjustments for optimal listening comfort.  
    Restart Windows (kb:alt+windows+r): Executes a forced restart of Windows using nircmd.exe, enabling quick system reboots without navigating menus.  
    Shutdown Windows (kb:alt+windows+s): Performs a forced shutdown of Windows using nircmd.exe, streamlining the process with a single keystroke.  

Why Use PPAWakeUp?  

This add-on is tailored for users who rely on the PPA Tatip synthesizer, offering unmatched convenience in managing speech synthesis and system operations. Whether you need to revive the synthesizer, tweak its settings, adjust NVDA's volume, or manage your system, PPAWakeUp keeps your hands on the keyboard and your workflow uninterrupted.
Technical Details

    Name: PPAWakeUp
    Author: 'chai chaimee
    Version: 2025.3
    Minimum NVDA Version: 2022.4
    Last Tested NVDA Version: 2025.1
    GitHub Repository: https://github.com/chaichaimee/PPAWakeUp
    Update Channel: None

Installation

Download the add-on from the GitHub repository and install it via NVDA's Add-on Manager. Ensure that PPA Tatip is installed on your system for full functionality.
Notes

    The add-on requires nircmd.exe for restart and shutdown commands, which should be included in the add-on's directory.
    Ensure that windows_tatip.exe and openoption.exe are located in the specified paths for the "Wake up" and "PPA Tatip Options" commands to work.
    Logs are saved to nvda_plugin.log for debugging purposes.

Contact

For issues, suggestions, or contributions, visit the GitHub repository or contact the author, chai chaimee.
