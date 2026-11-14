# tatipVoiceSettings.py

"""Backup and restore of the PPA Tatip voice option settings kept in NVDA's configuration.

The settings live in the speech section of the base configuration profile
(nvda.ini), one subsection per synthesizer. NVDA writes its in-memory
configuration back to nvda.ini when it exits, so a restore has to change the
in-memory profile and save it; editing nvda.ini on disk alone would be
overwritten by NVDA on the restart that follows. All functions that touch
NVDA's configuration must be called on the main thread.
"""

import copy
import json
import os
import shutil
import sys

import addonHandler
import config

addonHandler.initTranslation()

VOICE_SECTION_NAMES = ("sapi5", "ibmeci", "espeak")
BACKUP_FILE_NAME = "tatipVoiceSettings.json"
_SPEECH_SECTION_NAME = "speech"
# PPA Tatip is a 32-bit SAPI5 voice. A 64-bit NVDA reaches it through the
# sapi5_32 synthesizer, so its settings live in that section instead of sapi5.
# Backup files always use the sapi5 name, which keeps them usable on both.
_TATIP_SAPI5_NAME = "sapi5"
_TATIP_SAPI5_NAME_64BIT = "sapi5_32"
_FORMAT_VERSION = 1

_DEFAULT_VOICE_SETTINGS = {
    "sapi5": {
        "voice": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\PPATatip",
        "volume": 40,
        "rate": 70,
        "pitch": 50,
        "rateBoost": False,
        "useWasapi": True,
        "useSpellingFunctionality": False,
    },
    "ibmeci": {
        "voice": "65536",
        "variant": "1",
        "pitch": 65,
        "inflection": 30,
        "volume": 55,
        "rgh": 0,
        "bth": 0,
        "rate": 10,
    },
    "espeak": {
        "voice": "th",
        "variant": "max",
        "rate": 30,
        "rateBoost": False,
        "pitch": 40,
        "inflection": 75,
        "volume": 70,
    },
}


class VoiceSettingsError(Exception):
    pass


def getBackupPath(backupDir):
    return os.path.join(backupDir, BACKUP_FILE_NAME)


def getDefaultVoiceSettings():
    return copy.deepcopy(_DEFAULT_VOICE_SETTINGS)


def _is64BitProcess():
    return sys.maxsize > 2**32


def _getConfigSectionName(sectionName):
    if sectionName == _TATIP_SAPI5_NAME and _is64BitProcess():
        return _TATIP_SAPI5_NAME_64BIT
    return sectionName


def _toPlainDict(section):
    plainValues = {}
    for key in section:
        # dict.__getitem__ skips configobj's string interpolation, which
        # would rewrite values that contain percent or dollar sequences.
        value = dict.__getitem__(section, key)
        plainValues[key] = _toPlainDict(value) if isinstance(value, dict) else value
    return plainValues


def captureVoiceSettings():
    """Return the voice option sections of the base profile as plain dictionaries."""
    speechSection = dict.get(config.conf.profiles[0], _SPEECH_SECTION_NAME)
    if not isinstance(speechSection, dict):
        return {}
    capturedSections = {}
    for sectionName in VOICE_SECTION_NAMES:
        section = dict.get(speechSection, _getConfigSectionName(sectionName))
        if isinstance(section, dict) and section:
            capturedSections[sectionName] = _toPlainDict(section)
    return capturedSections


def writeBackupFile(backupPath, sections):
    payload = {"formatVersion": _FORMAT_VERSION, "speech": sections}
    tempPath = backupPath + ".tmp"
    os.makedirs(os.path.dirname(backupPath), exist_ok=True)
    try:
        with open(tempPath, "w", encoding="utf-8") as tempFile:
            json.dump(payload, tempFile, indent=2)
            tempFile.flush()
            os.fsync(tempFile.fileno())
        if os.path.exists(backupPath):
            shutil.copy2(backupPath, backupPath + ".bak")
        os.replace(tempPath, backupPath)
    except OSError:
        if os.path.exists(tempPath):
            os.remove(tempPath)
        raise


def readBackupFile(backupPath):
    try:
        with open(backupPath, "r", encoding="utf-8") as backupFile:
            payload = json.load(backupFile)
    except ValueError as e:
        raise VoiceSettingsError(_("The backup file is damaged or has an unexpected layout.")) from e
    speechData = payload.get(_SPEECH_SECTION_NAME) if isinstance(payload, dict) else None
    if not isinstance(speechData, dict):
        raise VoiceSettingsError(_("The backup file is damaged or has an unexpected layout."))
    sections = {}
    for sectionName in VOICE_SECTION_NAMES:
        section = speechData.get(sectionName)
        if section is None:
            continue
        if not isinstance(section, dict):
            raise VoiceSettingsError(_("The backup file is damaged or has an unexpected layout."))
        sections[sectionName] = section
    if not sections:
        raise VoiceSettingsError(_("The backup file holds no Tatip voice option setting."))
    return sections


def _mergeValues(targetSection, values):
    for key, value in values.items():
        if not isinstance(value, dict):
            targetSection[key] = value
            continue
        if not isinstance(dict.get(targetSection, key), dict):
            targetSection[key] = {}
        _mergeValues(targetSection[key], value)


def applyVoiceSettings(sections):
    """Write the backed up sections into the in-memory base profile; return the config section names used."""
    baseProfile = config.conf.profiles[0]
    if not isinstance(dict.get(baseProfile, _SPEECH_SECTION_NAME), dict):
        baseProfile[_SPEECH_SECTION_NAME] = {}
    speechSection = baseProfile[_SPEECH_SECTION_NAME]
    appliedNames = []
    for sectionName, values in sections.items():
        configSectionName = _getConfigSectionName(sectionName)
        if not isinstance(dict.get(speechSection, configSectionName), dict):
            speechSection[configSectionName] = {}
        _mergeValues(speechSection[configSectionName], values)
        appliedNames.append(configSectionName)
    return appliedNames
