"""
Project: Personal Autonomous Weather Station
File: version.py

Description:
Prints the build flag that gives its version to the firmware, computed
by Git: the last version tag, for example "v0.7.0", followed by the
number of commits and the commit since that tag when the firmware is
built from a later commit (for example "v0.7.0-3-g1a2b3c4"), and by
"-dirty" when files were changed without a commit. Called by
platformio.ini at each build.

Dependencies: Git.
"""

import subprocess

try:
    version = subprocess.check_output(
        ["git", "describe", "--tags", "--always", "--dirty"],
        text=True, stderr=subprocess.DEVNULL).strip()
except (OSError, subprocess.CalledProcessError):
    version = "unknown"

print(f'-D PAWS_VERSION=\\"{version}\\"')
