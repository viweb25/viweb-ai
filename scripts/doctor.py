"""Read-only prerequisite checks; does not install tools or print secrets."""

import shutil
import subprocess
import sys

failed = False
for tool, args in [
    ("git", ["--version"]),
    ("docker", ["compose", "version"]),
    ("node", ["--version"]),
    ("npm", ["--version"]),
    ("uv", ["--version"]),
]:
    if not shutil.which(tool):
        print(f"MISSING: {tool}")
        failed = True
        continue
    result = subprocess.run([tool, *args], capture_output=True, text=True)
    print(f"{tool}: {(result.stdout or result.stderr).strip()}")
    failed |= result.returncode != 0
    if tool == "node" and result.returncode == 0:
        major = int(result.stdout.strip().lstrip("v").split(".")[0])
        if major != 22:
            print("Use nvm install && nvm use (Node 22 required).")
            failed = True
print("Python 3.11 is selected by uv from .python-version; the system interpreter may differ.")
sys.exit(1 if failed else 0)
