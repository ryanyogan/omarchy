"""Exercise main-process-first termination with helpers in a different cgroup."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

if len(sys.argv) > 1:
  child = subprocess.Popen(['sleep', '60'])
  def stop(signum, frame):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(0.3)
    helpers_alive = child.poll() is None
    if helpers_alive:
      child.terminate()
    child.wait()
    Path(sys.argv[2]).write_text(str(helpers_alive))
    sys.exit(0 if helpers_alive else 1)
  signal.signal(signal.SIGTERM, stop)
  Path(sys.argv[1]).write_text(str(os.getpid()))
  while True:
    time.sleep(1)

if subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True).returncode:
  print('ok - user manager unavailable; skipping split-scope runtime test')
  sys.exit(0)

with tempfile.TemporaryDirectory() as tmp:
  root = Path(tmp)
  for mode in ('control-group', 'mixed'):
    unit = 'omarchy-stop-test-' + uuid.uuid4().hex
    pidfile, result = root/(mode+'.pid'), root/(mode+'.result')
    units = [unit+'.service', unit+'.scope']
    try:
      subprocess.run(['systemd-run', '--user', '--quiet', '--unit='+unit, '--property=Type=exec', '--property=ExitType=cgroup', '--property=KillMode='+mode, '--property=TimeoutStopSec=4', sys.executable, __file__, str(pidfile), str(result)], check=True, timeout=10)
      for _ in range(50):
        if pidfile.exists():
          break
        time.sleep(0.1)
      pid = pidfile.read_text()
      subprocess.run(['busctl', '--user', 'call', 'org.freedesktop.systemd1', '/org/freedesktop/systemd1', 'org.freedesktop.systemd1.Manager', 'StartTransientUnit', 'ssa(sv)a(sa(sv))', units[1], 'fail', '1', 'PIDs', 'au', '1', pid, '0'], check=True, capture_output=True, timeout=10)
      subprocess.run(['systemctl', '--user', 'stop', *units], check=True, timeout=10)
      assert result.read_text() == str(mode == 'mixed'), mode
      print('ok - split-scope stop behavior: ' + mode)
    finally:
      subprocess.run(['systemctl', '--user', 'stop', *units], capture_output=True, timeout=10)
      subprocess.run(['systemctl', '--user', 'reset-failed', *units], capture_output=True, timeout=10)
