# tatipDictionaryDriver.py

"""Lets PPA Tatip itself add words to its dictionary so that Tatip generates the pronunciation code.

The steps are the ones done by hand in Tatip: open the options window, press
Dictionary, press Add, type the word and the reading, press OK, and finally
press OK in the dictionary window, which makes Tatip save userdict.txt.
Everything runs on a worker thread; each step waits for the next Tatip window
and stops with a DriverError, and a window dump in the NVDA log, when the
expected window or control is not found.
"""

import time

import addonHandler

from . import tatipWindowDump as windowTools

addonHandler.initTranslation()

_DICTIONARY_WINDOW_CLASS = "Tchkdic"
_WORD_WINDOW_CLASS = "Tworddlg"
_BUTTON_CLASS = "TButton"
_THAI_ANSI_CODE_PAGE = 874
_OPTION_WAIT_SEC = 10.0
_WINDOW_WAIT_SEC = 6.0
_CLOSE_WAIT_SEC = 8.0
_POLL_INTERVAL_SEC = 0.1
_SETTLE_SEC = 0.2


class DriverError(Exception):
    """A step of the automated Tatip flow could not be completed; the message is for the user."""


def _waitFor(getResult, timeoutSec):
    deadline = time.monotonic() + timeoutSec
    while True:
        result = getResult()
        if result:
            return result
        if time.monotonic() >= deadline:
            return None
        time.sleep(_POLL_INTERVAL_SEC)


def _normalizeCaption(captionText):
    return captionText.replace("&", "").strip().lower()


def _findButton(parentHandle, caption):
    for childHandle in windowTools.getDescendantWindows(parentHandle):
        if windowTools.getWindowClass(childHandle) != _BUTTON_CLASS:
            continue
        if _normalizeCaption(windowTools.getWindowText(childHandle)) == caption:
            return childHandle
    return 0


def _firstVisibleWindow(className):
    windowHandles = windowTools.findVisibleTatipWindows(className)
    return windowHandles[0] if windowHandles else 0


def _findOptionWindowWithDictionaryButton():
    for topLevelHandle in windowTools.findVisibleTatipWindows():
        buttonHandle = _findButton(topLevelHandle, "dictionary")
        if buttonHandle:
            return topLevelHandle, buttonHandle
    return None


def _clickAndWaitClosed(windowHandle, buttonCaption, stepDescription):
    buttonHandle = _findButton(windowHandle, buttonCaption)
    if not buttonHandle:
        # Translators: {step} describes the step of the automated Tatip flow that failed.
        raise DriverError(_("PPA Tatip window changed: button not found while {step}").format(step=stepDescription))
    windowTools.clickButton(buttonHandle)
    closed = _waitFor(
        lambda: not windowTools.isWindowAlive(windowHandle) or not windowTools.isWindowVisible(windowHandle),
        _CLOSE_WAIT_SEC,
    )
    if not closed:
        # Translators: {step} describes the step of the automated Tatip flow that failed.
        raise DriverError(_("PPA Tatip did not respond while {step}").format(step=stepDescription))


def _fillWordWindow(wordWindow, pattern, reading):
    editHandles = [
        childHandle for childHandle in windowTools.getDescendantWindows(wordWindow)
        if "edit" in windowTools.getWindowClass(childHandle).lower()
    ]
    if len(editHandles) != 2:
        # Translators: {count} is the number of edit boxes found in the Tatip word window.
        raise DriverError(_("PPA Tatip word window has {count} edit boxes instead of 2").format(count=len(editHandles)))
    editHandles.sort(key=windowTools.getWindowTopLeft)
    for editHandle, wantedText in zip(editHandles, (pattern, reading)):
        if not windowTools.setWindowText(editHandle, wantedText):
            # Translators: Reported when PPA Tatip does not accept text typed by the add-on.
            raise DriverError(_("PPA Tatip did not accept the text"))
        if windowTools.getWindowText(editHandle) != wantedText:
            # Translators: Reported when the text read back from Tatip differs from what was sent.
            raise DriverError(_("PPA Tatip changed the text that was entered"))


def _cancelWordWindow():
    wordWindow = _firstVisibleWindow(_WORD_WINDOW_CLASS)
    if not wordWindow:
        return
    cancelButton = _findButton(wordWindow, "cancel")
    if cancelButton:
        windowTools.clickButton(cancelButton)


def addWords(words, launchOptions):
    """Adds (pattern, reading) pairs through PPA Tatip's own dictionary window.

    launchOptions starts openoption.exe. Raises DriverError with a user-facing message.
    """
    if windowTools.getAnsiCodePage() != _THAI_ANSI_CODE_PAGE:
        # Translators: Reported when Windows is not set to the Thai code page for non-Unicode programs.
        raise DriverError(_("Windows must use the Thai language for non-Unicode programs to send words to PPA Tatip"))
    if not windowTools.findTatipWindows():
        # Translators: Reported when PPA Tatip is not running.
        raise DriverError(_("PPA Tatip is not running. Press Windows+P to wake it up first"))
    if _firstVisibleWindow(_DICTIONARY_WINDOW_CLASS) or _firstVisibleWindow(_WORD_WINDOW_CLASS):
        # Translators: Reported when the Tatip dictionary window is already open.
        raise DriverError(_("Close the PPA Tatip dictionary window first"))
    try:
        launchOptions()
        optionFound = _waitFor(_findOptionWindowWithDictionaryButton, _OPTION_WAIT_SEC)
        if not optionFound:
            # Translators: Reported when the PPA Tatip options window did not appear.
            raise DriverError(_("The PPA Tatip options window did not appear"))
        optionWindow, dictionaryButton = optionFound
        windowTools.clickButton(dictionaryButton)
        dictionaryWindow = _waitFor(lambda: _firstVisibleWindow(_DICTIONARY_WINDOW_CLASS), _WINDOW_WAIT_SEC)
        if not dictionaryWindow:
            # Translators: Reported when the PPA Tatip dictionary window did not appear.
            raise DriverError(_("The PPA Tatip dictionary window did not appear"))
        for pattern, reading in words:
            addButton = _findButton(dictionaryWindow, "add")
            if not addButton:
                # Translators: Reported when a button of the Tatip dictionary window is missing.
                raise DriverError(_("PPA Tatip window changed: the Add button was not found"))
            windowTools.clickButton(addButton)
            wordWindow = _waitFor(lambda: _firstVisibleWindow(_WORD_WINDOW_CLASS), _WINDOW_WAIT_SEC)
            if not wordWindow:
                # Translators: Reported when the PPA Tatip word window did not appear.
                raise DriverError(_("The PPA Tatip word window did not appear"))
            _fillWordWindow(wordWindow, pattern, reading)
            # Translators: Step names used in error messages of the automated Tatip flow.
            _clickAndWaitClosed(wordWindow, "ok", _("confirming a word"))
            time.sleep(_SETTLE_SEC)
        _clickAndWaitClosed(dictionaryWindow, "ok", _("saving the dictionary"))
        if windowTools.isWindowAlive(optionWindow) and windowTools.isWindowVisible(optionWindow):
            _clickAndWaitClosed(optionWindow, "ok", _("closing the options window"))
    except DriverError:
        _cancelWordWindow()
        raise
