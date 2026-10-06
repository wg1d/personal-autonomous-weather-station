"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/logs.py

Description:
The log of the station, kept by the server in station.log. The station
writes one entry per wake-up, starting with a line holding its time:

    === 2026-10-04T15:25:00Z ===
    PAWS firmware v0.7.0 (bench periods)
    -> BOOT
    ...

The station sends the new lines at each upload (append()). The log
downloaded from its maintenance page holds entries already sent: merge()
only adds those whose first line is not in station.log yet.

Dependencies: Python standard library.
"""

import re

# The first line of an entry of the log
ENTRY_START = re.compile(r"^=== .+ ===$")


def append(path, text):
    """Appends lines sent by the station to the log; returns their number."""
    if text and not text.endswith("\n"):
        text += "\n"
    with open(path, "a", encoding="utf-8") as log:
        log.write(text)
    return text.count("\n")


def split_entries(text):
    """Cuts a log into entries, each starting with its first line.

    Lines before the first entry, if any, form an entry of their own,
    without a first line of time.
    """
    entries = []
    for line in text.splitlines(keepends=True):
        if ENTRY_START.match(line.strip()) or not entries:
            entries.append(line)
        else:
            entries[-1] += line
    return entries


def merge(path, text):
    """Adds the entries of a log that station.log does not hold yet.

    An entry is already held when its first line, which holds its time,
    is in station.log. Returns (entries read, entries added).
    """
    try:
        with open(path, encoding="utf-8") as log:
            known = {line.strip() for line in log
                     if ENTRY_START.match(line.strip())}
    except FileNotFoundError:
        known = set()
    entries = split_entries(text)
    new = [entry for entry in entries
           if entry.splitlines()[0].strip() not in known]
    if new:
        append(path, "".join(new))
    return len(entries), len(new)
