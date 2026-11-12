# userDictEditor.py

import os
import re
import shutil

import addonHandler
import core
import gui
import gui.guiHelper
import logHandler
import tones
import ui
import wx

addonHandler.initTranslation()

_USERDICT_FILE_NAME = "userdict.txt"
_BACKUP_FILE_NAME = "userdict_before_edit.txt"
_FIELD_COUNT = 8
_QUOTED_FIELD_RE = re.compile(r'"([^"]*)"')
_LINE_BREAK_RE = re.compile(r"\r\n|\n|\r")
_PARENTHESIS_TOKEN_RE = re.compile(r"\(([^()]*)\)")
# Marker words PPA Tatip's own dictionary editor documents for use inside
# parentheses; several may share one pair of parentheses, e.g. (half three).
_ALLOWED_MARKERS = frozenset((
    "half", "short", "long",
    "samun", "ake", "tho", "three", "jutthawa",
    "-d", "-f", "-k", "-l", "-s", "-sh", "-t",
    "+s", "+es", "+ed",
))
_DEFAULT_TAIL_FIELDS = ("", "", "1", "", "", "")
_DEFAULT_ENCODING = "cp874"
_SEARCH_ANNOUNCE_DELAY_MS = 700


def findUserDictPath():
    searchRoots = []
    localAppData = os.environ.get("LocalAppData")
    if localAppData:
        searchRoots.append(os.path.join(localAppData, "Programs"))
    for programFilesVar in ("ProgramFiles", "ProgramFiles(x86)"):
        programFilesDir = os.environ.get(programFilesVar)
        if programFilesDir:
            searchRoots.append(programFilesDir)
    for rootDir in searchRoots:
        candidate = os.path.join(rootDir, "PPA Tatip", "interface", _USERDICT_FILE_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


class DictEntry:
    """One line of userdict.txt.

    A parsed entry holds the pattern, the readable pronunciation text (the part
    of the replacement before the first colon), the pronunciation code made by
    PPA Tatip (the part after it) and the six trailing quoted fields, which are
    written back exactly as they were read. A line that does not match the expected
    eight-field layout keeps rawLine and is written back unchanged.
    """

    def __init__(self, pattern="", reading="", code="", tailFields=_DEFAULT_TAIL_FIELDS, rawLine=None):
        self.pattern = pattern
        self.reading = reading
        self.code = code
        self.tailFields = tuple(tailFields)
        self.rawLine = rawLine

    @property
    def isEditable(self):
        return self.rawLine is None

    @property
    def needsTatipCode(self):
        """True for a word with a reading but no pronunciation code; only PPA Tatip can generate the code."""
        return self.rawLine is None and bool(self.reading) and not self.code

    def toLine(self):
        if self.rawLine is not None:
            return self.rawLine
        fields = (self.pattern, f"{self.reading}:{self.code}") + self.tailFields
        return " ".join(f'"{fieldText}"' for fieldText in fields)


def _entryFromLine(line):
    fields = _QUOTED_FIELD_RE.findall(line)
    if len(fields) != _FIELD_COUNT:
        return DictEntry(rawLine=line)
    if " ".join(f'"{fieldText}"' for fieldText in fields) != line:
        return DictEntry(rawLine=line)
    reading, colon, code = fields[1].partition(":")
    if not colon or not fields[0]:
        return DictEntry(rawLine=line)
    return DictEntry(fields[0], reading, code, fields[2:])


def _decodeDictionaryBytes(rawBytes):
    try:
        text = rawBytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return rawBytes.decode(_DEFAULT_ENCODING), _DEFAULT_ENCODING
    if rawBytes.startswith(b"\xef\xbb\xbf"):
        return text, "utf-8-sig"
    if text.isascii():
        return text, _DEFAULT_ENCODING
    return text, "utf-8"


def readUserDict(filePath):
    """Returns (entries, encoding). Raises OSError or UnicodeDecodeError."""
    with open(filePath, "rb") as dictFile:
        rawBytes = dictFile.read()
    text, encoding = _decodeDictionaryBytes(rawBytes)
    lines = _LINE_BREAK_RE.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return [_entryFromLine(line) for line in lines], encoding


def writeUserDict(filePath, entries, encoding, backupDir):
    """Replaces the file atomically after keeping a copy of the previous version.

    Raises OSError, or UnicodeEncodeError when an entry holds a character the
    file encoding cannot store; in both cases the original file is untouched.
    """
    lines = [entry.toLine() for entry in entries]
    payload = ("\r\n".join(lines) + "\r\n").encode(encoding) if lines else b""
    temporaryPath = filePath + ".tmp"
    try:
        if os.path.isfile(filePath):
            os.makedirs(backupDir, exist_ok=True)
            shutil.copy2(filePath, os.path.join(backupDir, _BACKUP_FILE_NAME))
        with open(temporaryPath, "wb") as dictFile:
            dictFile.write(payload)
            dictFile.flush()
            os.fsync(dictFile.fileno())
        os.replace(temporaryPath, filePath)
    except OSError:
        if os.path.isfile(temporaryPath):
            try:
                os.remove(temporaryPath)
            except OSError:
                logHandler.log.debugWarning(f"PPAWakeUp: could not remove {temporaryPath}", exc_info=True)
        raise


def validateEntryFields(pattern, reading, encoding):
    """Returns (errorMessage, focusFieldName). Both are None when the fields are valid."""
    for fieldName, fieldText in (("pattern", pattern), ("reading", reading)):
        if '"' in fieldText or "\r" in fieldText or "\n" in fieldText:
            # Translators: Reported when a dictionary field contains a double quote or a line break.
            return _("The text must not contain double quotes or line breaks"), fieldName
    if ":" in reading:
        # Translators: Reported when the reading contains a colon.
        return _("The reading must not contain a colon"), "reading"
    if not pattern.strip():
        # Translators: Reported when the pattern field is empty.
        return _("The pattern must not be empty"), "pattern"
    if not reading.strip():
        # Translators: Reported when the reading field is empty.
        return _("The reading must not be empty"), "reading"
    remainder = _PARENTHESIS_TOKEN_RE.sub("", reading)
    if "(" in remainder or ")" in remainder:
        # Translators: Reported when the reading has an unmatched parenthesis.
        return _("The reading has an unmatched parenthesis"), "reading"
    for markerGroup in _PARENTHESIS_TOKEN_RE.findall(reading):
        markerWords = markerGroup.split()
        if markerWords and all(markerWord in _ALLOWED_MARKERS for markerWord in markerWords):
            continue
        # Translators: {marker} is the text found between parentheses in the reading.
        return _("Unknown marker ({marker}). Allowed words: half, short, long, samun, ake, tho, three, "
                 "jutthawa, -d, -f, -k, -l, -s, -sh, -t, +s, +es, +ed").format(marker=markerGroup), "reading"
    for fieldName, fieldText in (("pattern", pattern), ("reading", reading)):
        try:
            fieldText.encode(encoding)
        except UnicodeEncodeError:
            # Translators: Reported when a character cannot be stored in the dictionary file.
            return _("The text contains a character that cannot be saved in the dictionary file"), fieldName
    return None, None


def findWordsMissingCode(filePath, words):
    """Returns the patterns of (pattern, reading) pairs that the file does not hold with a pronunciation code."""
    entries, _encoding = readUserDict(filePath)
    storedWords = {(entry.pattern, entry.reading) for entry in entries if entry.isEditable and entry.code}
    return [pattern for pattern, reading in words if (pattern, reading) not in storedWords]


class EntryEditDialog(wx.Dialog):
    """Add or edit the pattern and the reading of one word; the caller reads resultFields after OK."""

    def __init__(self, parent, title, entry, encoding):
        super().__init__(parent, title=title)
        self._encoding = encoding
        self.resultFields = None

        sizerHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        # Translators: Label of the pattern field (the word as written).
        self._patternEdit = sizerHelper.addLabeledControl(_("&Pattern:"), wx.TextCtrl)
        # Translators: Label of the reading field; the markers set half-tone, short and long vowels.
        self._readingEdit = sizerHelper.addLabeledControl(
            _("&Replacement (reading, markers in parentheses such as (half), (short), (long)):"), wx.TextCtrl
        )
        self._patternEdit.SetValue(entry.pattern)
        self._readingEdit.SetValue(entry.reading)
        sizerHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))

        self.SetSizerAndFit(sizerHelper.sizer)
        self.CentreOnScreen()
        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self._patternEdit.SetFocus()

    def _onOk(self, evt):
        pattern = self._patternEdit.GetValue().strip()
        reading = self._readingEdit.GetValue().strip()
        errorMessage, focusFieldName = validateEntryFields(pattern, reading, self._encoding)
        if errorMessage:
            fieldControls = {"pattern": self._patternEdit, "reading": self._readingEdit}
            # Translators: Title of the message shown when a dictionary entry is not valid.
            gui.messageBox(errorMessage, _("Invalid entry"), wx.OK | wx.ICON_ERROR, self)
            fieldControls[focusFieldName].SetFocus()
            return
        self.resultFields = (pattern, reading)
        self.EndModal(wx.ID_OK)


class UserDictEditorDialog(wx.Dialog):
    """List, search, add, edit and remove the words of userdict.txt.

    Changes stay in memory until Apply or OK. Words that have no pronunciation
    code yet are not written by this add-on: they are handed to PPA Tatip,
    which generates the code and saves the file itself.
    """

    def __init__(self, parent, filePath, backupDir, onApplied, onClosed, sendToTatip):
        # Translators: Title of the Tatip dictionary editor window.
        super().__init__(parent, title=_("PPA Tatip Dictionary Editor"))
        self._filePath = filePath
        self._backupDir = backupDir
        self._onApplied = onApplied
        self._onClosed = onClosed
        self._sendToTatip = sendToTatip
        self._entries, self._encoding = readUserDict(filePath)
        self._visibleIndices = []
        self._isDirty = False
        self._isClosed = False
        self._isBusy = False
        self._closeAfterApply = False
        self._pendingWords = []
        self._movedEntryKey = None
        self._searchAnnounceCall = None

        sizerHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        # Translators: Label of the search box of the Tatip dictionary editor.
        self._searchEdit = sizerHelper.addLabeledControl(_("&Search:"), wx.TextCtrl)
        self._searchEdit.Bind(wx.EVT_TEXT, self._onSearchChanged)
        # Translators: Label of the word list of the Tatip dictionary editor.
        self._listBox = sizerHelper.addLabeledControl(_("Dictionary &words"), wx.ListBox, style=wx.LB_SINGLE)
        # Translators: Label of the field holding the line the selected word is moved to when Apply or OK is pressed.
        self._moveEdit = sizerHelper.addLabeledControl(_("&Move to line:"), wx.TextCtrl)

        actionRow = wx.BoxSizer(wx.HORIZONTAL)
        # Translators: Buttons of the Tatip dictionary editor.
        self._addButton = wx.Button(self, label=_("&Add"))
        self._editButton = wx.Button(self, label=_("&Edit"))
        self._removeButton = wx.Button(self, label=_("&Remove"))
        for actionButton in (self._addButton, self._editButton, self._removeButton):
            actionRow.Add(actionButton, border=5, flag=wx.RIGHT)
        sizerHelper.addItem(actionRow)

        # A plain row keeps the tab order Apply, OK, Cancel; the standard
        # dialog button sizer reorders buttons per platform and put Apply last.
        dismissRow = wx.BoxSizer(wx.HORIZONTAL)
        self._applyButton = wx.Button(self, wx.ID_APPLY)
        self._okButton = wx.Button(self, wx.ID_OK)
        self._okButton.SetDefault()
        cancelButton = wx.Button(self, wx.ID_CANCEL)
        for dismissButton in (self._applyButton, self._okButton, cancelButton):
            dismissRow.Add(dismissButton, border=5, flag=wx.RIGHT)
        sizerHelper.addItem(dismissRow, flag=wx.ALIGN_RIGHT)

        self.SetSizerAndFit(sizerHelper.sizer)
        self.CentreOnScreen()

        self._addButton.Bind(wx.EVT_BUTTON, self._onAdd)
        self._editButton.Bind(wx.EVT_BUTTON, self._onEdit)
        self._removeButton.Bind(wx.EVT_BUTTON, self._onRemove)
        self._applyButton.Bind(wx.EVT_BUTTON, self._onApply)
        self.Bind(wx.EVT_BUTTON, self._onOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._onCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self._onCloseEvent)
        self.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

        self._refreshList()
        if self._listBox.GetCount():
            logHandler.log.info(
                f"PPAWakeUp dictionary editor opened: {len(self._entries)} lines, "
                f"first list item {self._listBox.GetString(0)!r}"
            )
        wx.CallAfter(self._listBox.SetFocus)

    def _onCharHook(self, evt):
        keyCode = evt.GetKeyCode()
        if keyCode == wx.WXK_ESCAPE:
            self._requestCancel()
            return
        if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self.FindFocus() is self._listBox:
            self._onEdit(None)
            return
        evt.Skip()

    def _refreshList(self, selectEntryIndex=None):
        searchText = self._searchEdit.GetValue().strip().lower()
        self._visibleIndices = []
        listLabels = []
        for entryIndex, entry in enumerate(self._entries):
            if not entry.isEditable:
                continue
            if searchText and searchText not in f"{entry.pattern} {entry.reading}".lower():
                continue
            self._visibleIndices.append(entryIndex)
            # Same layout as DictionaryDisplayLite (word, reading, then the line); the label is
            # built without a translatable format string so a translation cannot drop the number.
            listLabels.append(f"{entry.pattern}, {entry.reading} {_('line')} {entryIndex + 1}")
        self._listBox.Set(listLabels)
        if not listLabels:
            return
        selectedPosition = 0
        if selectEntryIndex in self._visibleIndices:
            selectedPosition = self._visibleIndices.index(selectEntryIndex)
        self._listBox.SetSelection(selectedPosition)

    def _getSelectedEntryIndex(self):
        listPosition = self._listBox.GetSelection()
        if listPosition == wx.NOT_FOUND or listPosition >= len(self._visibleIndices):
            return None
        return self._visibleIndices[listPosition]

    def _setBusy(self, isBusy):
        self._isBusy = isBusy
        for busyControl in (
            self._addButton, self._editButton, self._removeButton, self._applyButton, self._okButton
        ):
            busyControl.Enable(not isBusy)

    def _reportBusy(self):
        # Translators: Reported when the editor is waiting for PPA Tatip to save the words.
        ui.message(_("Please wait, PPA Tatip is saving the words"))

    def _onSearchChanged(self, evt):
        self._refreshList()
        if self._searchAnnounceCall is not None:
            self._searchAnnounceCall.Stop()
        self._searchAnnounceCall = core.callLater(_SEARCH_ANNOUNCE_DELAY_MS, self._announceResultCount)

    def _announceResultCount(self):
        self._searchAnnounceCall = None
        # Translators: {count} is the number of dictionary words matching the search.
        ui.message(_("{count} results found").format(count=len(self._visibleIndices)))

    def _onAdd(self, evt):
        if self._isBusy:
            self._reportBusy()
            return
        # Translators: Title of the dialog used to add a word to the Tatip dictionary.
        resultFields = self._runEntryDialog(_("Add Tatip dictionary word"), DictEntry())
        if resultFields is None:
            return
        self._entries.append(DictEntry(resultFields[0], resultFields[1]))
        self._isDirty = True
        self._searchEdit.ChangeValue("")
        self._refreshList(selectEntryIndex=len(self._entries) - 1)
        # Translators: Reported after a word is added to the editor list.
        ui.message(_("Word added. Press Apply to save"))

    def _onEdit(self, evt):
        if self._isBusy:
            self._reportBusy()
            return
        entryIndex = self._getSelectedEntryIndex()
        if entryIndex is None:
            # Translators: Reported when Edit is pressed with no word selected.
            ui.message(_("No word is selected"))
            return
        entry = self._entries[entryIndex]
        # Translators: Title of the dialog used to edit a word of the Tatip dictionary.
        resultFields = self._runEntryDialog(_("Edit Tatip dictionary word"), entry)
        if resultFields is None or resultFields == (entry.pattern, entry.reading):
            return
        if resultFields[1] != entry.reading:
            # A new reading needs a new pronunciation code, which only PPA Tatip can make.
            entry.code = ""
        entry.pattern, entry.reading = resultFields
        self._isDirty = True
        self._refreshList(selectEntryIndex=entryIndex)
        # Translators: Reported after a word is changed in the editor list.
        ui.message(_("Word updated. Press Apply to save"))

    def _runEntryDialog(self, title, entry):
        subDialog = EntryEditDialog(self, title, entry, self._encoding)
        try:
            dialogResult = subDialog.ShowModal()
        finally:
            subDialog.Destroy()
        if dialogResult != wx.ID_OK:
            return None
        return subDialog.resultFields

    def _onRemove(self, evt):
        if self._isBusy:
            self._reportBusy()
            return
        entryIndex = self._getSelectedEntryIndex()
        if entryIndex is None:
            # Translators: Reported when Remove is pressed with no word selected.
            ui.message(_("No word is selected"))
            return
        listPosition = self._listBox.GetSelection()
        del self._entries[entryIndex]
        self._isDirty = True
        self._refreshList()
        remainingCount = self._listBox.GetCount()
        if remainingCount:
            self._listBox.SetSelection(min(listPosition, remainingCount - 1))
        # Translators: Reported after a word is removed from the editor list.
        ui.message(_("Word removed. Press Apply to save"))

    def _showError(self, message, title):
        gui.messageBox(message, title, wx.OK | wx.ICON_ERROR, self)

    def _applyMoveRequest(self):
        """Moves the selected word to the line typed in the move field. Returns False when Apply must stop."""
        requestedText = self._moveEdit.GetValue().strip()
        if not requestedText:
            return True
        if not requestedText.isdecimal() or not 1 <= int(requestedText) <= len(self._entries):
            gui.messageBox(
                # Translators: {count} is the number of lines of the dictionary.
                _("Enter a line number from 1 to {count}").format(count=len(self._entries)),
                # Translators: Title of the message shown when the line number to move to is not valid.
                _("Invalid line number"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            self._moveEdit.SetFocus()
            return False
        entryIndex = self._getSelectedEntryIndex()
        if entryIndex is None:
            # Translators: Reported when a line number is typed but no word is selected.
            ui.message(_("No word is selected"))
            self._listBox.SetFocus()
            return False
        targetIndex = int(requestedText) - 1
        self._moveEdit.ChangeValue("")
        if targetIndex == entryIndex:
            return True
        movedEntry = self._entries.pop(entryIndex)
        self._entries.insert(targetIndex, movedEntry)
        self._movedEntryKey = (movedEntry.pattern, movedEntry.reading)
        self._isDirty = True
        self._searchEdit.ChangeValue("")
        self._refreshList(selectEntryIndex=targetIndex)
        # Translators: {line} is the line the selected word was moved to.
        ui.message(_("Moved to line {line}").format(line=targetIndex + 1))
        return True

    def _selectMovedEntry(self):
        movedKey = self._movedEntryKey
        self._movedEntryKey = None
        selectIndex = None
        for entryIndex, entry in enumerate(self._entries):
            if entry.isEditable and (entry.pattern, entry.reading) == movedKey:
                selectIndex = entryIndex
                break
        self._refreshList(selectEntryIndex=selectIndex)

    def _startApply(self):
        """Writes the words that already have a code, then hands the others to PPA Tatip."""
        if not self._applyMoveRequest():
            self._closeAfterApply = False
            return
        pendingEntries = [entry for entry in self._entries if entry.needsTatipCode]
        if not self._isDirty and not pendingEntries:
            # Translators: Reported when Apply is pressed and nothing was changed.
            ui.message(_("No changes to save"))
            if self._closeAfterApply:
                self._closeWindow()
            return
        readyEntries = [entry for entry in self._entries if not entry.needsTatipCode]
        try:
            writeUserDict(self._filePath, readyEntries, self._encoding, self._backupDir)
        except (OSError, UnicodeEncodeError) as writeError:
            logHandler.log.error(f"PPAWakeUp: failed to save {self._filePath}: {writeError}")
            self._closeAfterApply = False
            # Translators: {error} is the reason the dictionary file could not be saved.
            self._showError(_("The dictionary could not be saved: {error}").format(error=str(writeError)),
                            # Translators: Title of the message shown when saving the dictionary failed.
                            _("Save failed"))
            return
        if not pendingEntries:
            self._isDirty = False
            self._selectMovedEntry()
            tones.beep(1500, 100)
            # Translators: Reported after the dictionary file was saved.
            ui.message(_("Dictionary saved"))
            if self._onApplied:
                self._onApplied()
            if self._closeAfterApply:
                self._closeWindow()
            return
        self._pendingWords = [(entry.pattern, entry.reading) for entry in pendingEntries]
        self._setBusy(True)
        # Translators: {count} is the number of words handed to PPA Tatip to generate their pronunciation code.
        ui.message(_("Sending {count} words to PPA Tatip, please wait").format(count=len(self._pendingWords)))
        self._sendToTatip(self._pendingWords, self._onTatipDone)

    def _onTatipDone(self, succeeded, message):
        """Runs on the main thread once PPA Tatip finished or the hand-over failed."""
        if self._isClosed:
            return
        self._setBusy(False)
        self.Raise()
        if succeeded:
            try:
                missingPatterns = findWordsMissingCode(self._filePath, self._pendingWords)
                if not missingPatterns:
                    self._entries, self._encoding = readUserDict(self._filePath)
            except (OSError, UnicodeDecodeError) as readError:
                logHandler.log.error(f"PPAWakeUp: could not verify {self._filePath}: {readError}")
                missingPatterns = [pattern for pattern, _reading in self._pendingWords]
            if not missingPatterns:
                self._isDirty = False
                self._selectMovedEntry()
                tones.beep(1500, 100)
                # Translators: Reported after PPA Tatip saved the new words with their pronunciation code.
                ui.message(_("Dictionary saved by PPA Tatip"))
                # PPA Tatip only reads the new words after it is restarted.
                if self._onApplied:
                    self._onApplied()
                if self._closeAfterApply:
                    self._closeWindow()
                return
            # Translators: {words} lists the words PPA Tatip did not save with a pronunciation code.
            message = _("PPA Tatip did not save these words with a pronunciation code: {words}").format(
                words=", ".join(missingPatterns)
            )
        self._isDirty = True
        self._closeAfterApply = False
        logHandler.log.error(f"PPAWakeUp: hand-over to PPA Tatip failed: {message}")
        # Translators: Title of the message shown when PPA Tatip could not save the new words.
        self._showError(message, _("PPA Tatip did not save the words"))

    def _onApply(self, evt):
        if self._isBusy:
            self._reportBusy()
            return
        self._startApply()

    def _onOk(self, evt):
        if self._isBusy:
            self._reportBusy()
            return
        self._closeAfterApply = True
        self._startApply()

    def _onCancel(self, evt):
        self._requestCancel()

    def _onCloseEvent(self, evt):
        self._requestCancel()

    def _requestCancel(self):
        if self._isBusy:
            self._reportBusy()
            return
        if self._isDirty:
            confirmation = gui.messageBox(
                # Translators: Asked when the editor is closed while it holds unsaved changes.
                _("There are unsaved changes. Close without saving?"),
                # Translators: Title of the confirmation about unsaved changes.
                _("Unsaved changes"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                self,
            )
            if confirmation != wx.YES:
                return
        self._closeWindow()

    def _closeWindow(self):
        if self._isClosed:
            return
        self._isClosed = True
        if self._searchAnnounceCall is not None:
            self._searchAnnounceCall.Stop()
            self._searchAnnounceCall = None
        gui.mainFrame.postPopup()
        if self._onClosed:
            self._onClosed()
        self.Destroy()

    def forceClose(self):
        self._isDirty = False
        self._closeWindow()


def showUserDictEditor(parent, filePath, backupDir, onApplied, onClosed, sendToTatip):
    """Opens the editor and returns it. Raises OSError or UnicodeDecodeError when the file cannot be read.

    sendToTatip(words, onDone) must make PPA Tatip add the (pattern, reading) pairs and later call
    onDone(succeeded, message) on the main thread.
    """
    editorDialog = UserDictEditorDialog(parent, filePath, backupDir, onApplied, onClosed, sendToTatip)
    gui.mainFrame.prePopup()
    editorDialog.Show()
    editorDialog.Raise()
    return editorDialog
