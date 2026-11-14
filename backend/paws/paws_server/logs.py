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
from datetime import datetime, timezone

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


# The lines of an entry that tell something went wrong, or a restart:
# words written by the firmware (see its console messages)
PROBLEMS = ("not responding", "timed out", "cannot ", "not mounted",
            "NOT stored", "not answering", "not reachable", "too long",
            "restart:")
# The answer of the server to an upload, such as "server answered 400"
ANSWER = re.compile(r"server answered (\d+)")
# The time of an entry, in its first line
ENTRY_TIME = re.compile(r"^=== (\S+) ===$")
# Before this date, the time of an entry is the one of a clock that was
# not set (2000-01-01, or 1970-01-01)
VALID_SINCE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def read_tail(path, size):
    """The last size bytes of a log, cut at the start of an entry, or ""
    if the file does not exist. The log grows by about 30 KB a day: its
    end is enough for the last days, without reading months of it."""
    try:
        with open(path, "rb") as log:
            log.seek(0, 2)
            start = max(0, log.tell() - size)
            log.seek(start)
            text = log.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    if start == 0:
        return text  # the whole log
    # The first entry is cut: start at the next one, or nothing
    entry = text.find("\n=== ")
    return "" if entry < 0 else text[entry + 1:]


def problems(text):
    """The lines of a log that tell a problem, oldest first, as (time,
    clock_set, line). time is the time of their entry, in UTC; for an
    entry written while the clock was not set, the time of the entry
    before it, and clock_set is False.

    The log holds about a hundred entries a day: the time of an entry is
    only read when one of its lines tells a problem, since reading a date
    is slow on the small computer of the server.
    """
    found = []
    last_time = None   # the time of the last entry with a set clock
    last_text = None   # its text, read only when needed
    clock_set = False
    for line in text.splitlines():
        line = line.strip()
        match = ENTRY_TIME.match(line)
        if match:
            # Before 2020: the time of a clock that was not set
            clock_set = match.group(1)[:4] >= str(VALID_SINCE.year)
            if clock_set:
                last_text, last_time = match.group(1), None
            continue
        answer = ANSWER.search(line)
        bad_answer = answer and not answer.group(1).startswith("2")
        if not (bad_answer or any(word in line for word in PROBLEMS)):
            continue
        if last_time is None and last_text is not None:
            try:
                last_time = datetime.strptime(
                    last_text, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=timezone.utc)
            except ValueError:
                last_text = None
        found.append((last_time, clock_set, line))
    return found
