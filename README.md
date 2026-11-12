![NVDA Logo](https://www.nvaccess.org/files/nvda/documentation/userGuide/images/nvda.ico)

# PPAWakeUp

Wake PPA Tatip up whenever it stops, keep it safe from crashes, and manage its dictionary with ease.

**author:** chai chaimee

**url:** https://github.com/chaichaimee/PPAWakeUp

## Introduction

PPAWakeUp keeps the PPA Tatip Thai voice working smoothly with NVDA. When Tatip stops speaking or crashes, one key press restarts it and gets you reading again. The add-on also stops the characters and dialog buttons that are known to freeze Tatip from reaching it, lets you back up and restore your personal dictionary, and includes a full dictionary editor so you can add and correct words without leaving NVDA.

## Hot Keys

**Windows+P**

- Single Tap : Wake up PPA Tatip
- Double Tap : Open the Tatip dictionary editor
- Triple Tap : Open the Tatip menu

## Features

### Wake Up PPA Tatip

Press Windows+P once to restart PPA Tatip. NVDA says "Wake up" and plays a beep, then the add-on closes any running Tatip process, including a stuck one, and starts a fresh copy. It finds Tatip in your local Programs folder or in Program Files.

If Tatip does not start on the first try, the add-on tries again, up to three attempts in total. You can turn this retry off in the Tatip reader setting. If Tatip was only just started successfully and you press the key again, NVDA says "PPA Tatip is already awake" instead of restarting it, so an impatient second press can never kill a Tatip that is still starting. If a restart is already in progress, NVDA asks you to wait.

Different beeps tell you what happened: an error beep when Tatip cannot be found or does not confirm startup, and a higher beep when a backup, restore or dictionary save succeeds.

The add-on also releases the Windows and P keys after the gesture, so Windows does not open its own Project panel on your next press of the letter P.

**Step by step:**

1. Press Windows+P once.
2. Listen for "Wake up" and the beep.
3. Wait a moment while Tatip restarts. Tatip starts speaking again.

### CJK Character Speech Filter

Chinese, Japanese and Korean characters can make PPA Tatip stop working. While this filter is on, the add-on removes those characters from everything NVDA is about to speak. If nothing is left after filtering, that speech is dropped instead of being sent to Tatip. If the filter itself ever fails, NVDA speaks the original text normally so you are never left in silence.

### Dialog Button Crash Protection

Tatip can crash silently when focus lands on the Open, OK, Save or Yes button, or the Thai equivalents, right after a file dialog appears. When one of these buttons receives focus, the add-on checks shortly afterwards that Tatip is still running. If Tatip has disappeared, it is restarted automatically.

### Tatip Menu

Press Windows+P three times to open a small window with a list of actions. Use the arrow keys to choose, Enter to run the action, and Escape to close. The menu closes by itself after a short period without use. The actions are:

- Open Tatip options: starts the PPA Tatip options program.
- Tatip reader setting: opens the settings window described below.
- Backup Tatip dictionary: copies userdict.txt to a safe folder.
- Restore Tatip dictionary: copies your backup back and restarts Tatip.
- Open Tatip folder: opens the PPA Tatip interface folder in Windows Explorer.
- Diagnostics: dump Tatip windows: saves a read-only list of the open Tatip windows to a text file, for troubleshooting. Nothing in Tatip is changed.

### Tatip Reader Setting

This window has three check boxes, and all of them are on by default:

- Skip Chinese, Japanese and Korean characters when speaking.
- Protect against crash when focusing Open/OK/Save buttons in dialogs.
- Automatically retry wake up if PPA Tatip does not start.

Press OK to save your choices, or Cancel to discard them. Your choices are remembered between NVDA sessions.

**Step by step:**

1. Press Windows+P three times.
2. Choose Tatip reader setting and press Enter.
3. Tick or untick the options you want.
4. Press OK.

### Backup and Restore the Dictionary

Backup Tatip dictionary copies your PPA Tatip userdict.txt into a ChaiChaimee, PPAWakeUp folder inside your NVDA configuration folder. NVDA reports the full path when the backup is done. Restore Tatip dictionary copies that backup over the current userdict.txt, says "Dictionary restored. Reloading PPA Tatip", and restarts Tatip so the restored words take effect. If no backup exists yet, NVDA tells you to make one first.

**Step by step:**

1. Press Windows+P three times.
2. Choose Backup Tatip dictionary and press Enter. Wait for the backup confirmation.
3. Later, to go back to that copy, open the menu again, choose Restore Tatip dictionary and press Enter.

### Tatip Dictionary Editor

Press Windows+P twice to open the PPA Tatip Dictionary Editor, which works directly on the Tatip userdict.txt file. The word list shows each entry as the word, its reading, and its line number. Press Enter on a word to edit it.

- Search: type in the Search box to filter the list by word or reading. NVDA announces how many results were found.
- Add: opens a dialog with a Pattern field (the word as written) and a Replacement field (its reading).
- Edit: changes the pattern or the reading of the selected word.
- Remove: deletes the selected word from the list.
- Move to line: type a line number to move the selected word to that line when you press Apply or OK.
- Apply saves your changes and keeps the window open. OK saves and closes. Cancel or Escape closes the window, and asks first if there are unsaved changes.

Changes stay in the editor until you press Apply or OK, and NVDA reminds you of this after every add, edit or remove. Lines of the file that do not follow the standard word layout are left out of the list and are always saved back unchanged.

The reading can contain marker words in parentheses, such as (half), (short) or (long). The allowed markers are half, short, long, samun, ake, tho, three, jutthawa, -d, -f, -k, -l, -s, -sh, -t, +s, +es and +ed, and several can share one pair of parentheses, for example (half three). The editor rejects an entry that is empty, contains a double quote, a line break or a colon in the reading, has unmatched parentheses or an unknown marker, or holds a character the dictionary file cannot store, and puts you back in the field that needs fixing.

### Adding and Changing Words

Every word in the Tatip dictionary needs a pronunciation code, and only PPA Tatip itself can create it. For that reason, new words and words whose reading you changed are handed over to PPA Tatip automatically when you press Apply or OK. The add-on opens the Tatip options window, presses Dictionary and Add, enters each word and its reading, confirms, and finally confirms the dictionary window so that Tatip saves the file itself. NVDA says how many words are being sent and asks you to wait.

Words that already have a pronunciation code, such as ones you only moved, removed, or renamed without changing the reading, are written to the file directly. Before every direct save, the previous file is kept as userdict_before_edit.txt in the backup folder.

When everything has been saved, NVDA says "Dictionary saved" or "Dictionary saved by PPA Tatip" with a beep, and Tatip is restarted so it reads the new words. If Tatip did not save a word, the editor lists the words that failed and keeps your changes so you can try again.

Handing words to Tatip needs three things: Windows must use the Thai language for non-Unicode programs, PPA Tatip must be running (press Windows+P first), and the Tatip dictionary window must not already be open.

**Step by step:**

1. Press Windows+P to make sure PPA Tatip is running.
2. Press Windows+P twice to open the dictionary editor.
3. Choose Add, type the word in Pattern and its reading in Replacement, then press OK.
4. Repeat for any other words. Each one is shown in the list.
5. Press Apply, or OK to save and close.
6. Wait while NVDA reports that the words are being sent to PPA Tatip.
7. Listen for "Dictionary saved by PPA Tatip". Tatip restarts and the new words are ready.

### Reorder Words

Order matters in a dictionary, and the editor lets you place a word on an exact line.

**Step by step:**

1. In the editor, select the word you want to move in the list.
2. Press Tab to reach the Move to line field and type the new line number. It must be between 1 and the number of lines in the file.
3. Press Apply or OK. NVDA says "Moved to line" followed by the number, and the word stays selected.

### Smooth Reading in Tatip Windows

The add-on includes special handling for the PPA Tatip programs, windows_tatip and ttsapp. NVDA does not probe their windows with UI Automation, which prevents NVDA from freezing while Tatip is busy. Their windows are read through the standard accessibility interface instead. This works in the background and needs no setup.

### Changing the Hot Key

The Windows+P gesture appears in NVDA's Input Gestures dialog under the PPAWakeUp category, where you can assign a different key if you prefer.

## Support Me

If this tool has made your life easier, consider fueling the next update with a small donation.

[![Support me](https://img.shields.io/badge/Donate-Support%20Me-blue?style=for-the-badge&logo=stripe)](https://buy.stripe.com/dRm9AU1xQ3Ds22N6VK1VK01)

Your support means the world. Let's build something great together

© 2026 Chai Chaimee NVDA Add-on Released under GNU GPL
