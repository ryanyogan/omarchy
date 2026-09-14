"""Ask Dropbox to flush and exit, then wait before systemd kills leftovers."""
import os
from pathlib import Path
import select
import subprocess
import sys

def main():
  try:
    pid = int((Path.home() / '.dropbox/dropbox.pid').read_text())
    descriptor = os.pidfd_open(pid)
  except (ValueError, OSError):
    return 0
  try:
    if 'dropbox' not in Path(f'/proc/{pid}/cmdline').read_text().lower():
      return 0
    subprocess.run(['dropbox-cli', 'stop'], timeout=5, check=True)
    if not select.select([descriptor], [], [], 12)[0]:
      print('Dropbox has not finished exiting', file=sys.stderr)
      return 1
    return 0
  except (OSError, subprocess.SubprocessError) as error:
    print(str(error), file=sys.stderr)
    return 1
  finally:
    os.close(descriptor)

if __name__ == '__main__':
  sys.exit(main())
