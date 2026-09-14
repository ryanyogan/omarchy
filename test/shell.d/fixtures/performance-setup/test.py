import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ['ROOT'])

class Setup(unittest.TestCase):
  def run_setup(self, running, managed=False, desktop=None, mode='--migrate'):
    with tempfile.TemporaryDirectory() as tmp:
      home = Path(tmp); mocks = home / 'bin'; mocks.mkdir()
      scripts = {
        'dropbox-cli': '#!/bin/bash\nexit "$TEST_RUNNING"\n',
        'systemctl': '''#!/bin/bash
printf '%s\\n' "$*" >> "$HOME/calls"
case "$*" in
  *'show omarchy-dropbox.service'*) echo not-found ;;
  *'is-active'*) [[ $TEST_MANAGED == 1 ]] ;;
esac
''',
        'omarchy-dropbox-stop': '#!/bin/bash\necho graceful-stop >> "$HOME/calls"\n',
      }
      for name, script in scripts.items():
        p = mocks / name; p.write_text(script); p.chmod(0o755)
      entry = home / '.config/autostart/dropbox.desktop'
      if desktop is not None:
        entry.parent.mkdir(parents=True); entry.write_text(desktop)
      env = dict(os.environ, HOME=tmp, OMARCHY_PATH=str(ROOT), PATH=str(mocks)+':'+os.environ['PATH'], TEST_RUNNING=str(int(running)), TEST_MANAGED=str(int(managed)))
      subprocess.run([str(ROOT/'bin/omarchy-setup-dropbox'), *([mode] if mode else [])], env=env, check=True)
      return (home/'calls').read_text(), entry.read_text() if entry.exists() else None
  def test_paused_migration_preserves_no_autostart(self):
    calls, desktop = self.run_setup(False)
    self.assertNotIn('start omarchy-dropbox.service',calls)
    self.assertIsNone(desktop)
  def test_adoption_stops_legacy_before_start(self):
    calls, desktop = self.run_setup(True)
    self.assertLess(calls.index('graceful-stop'),calls.index('start omarchy-dropbox.service'))
    self.assertIsNone(desktop)
  def test_preserves_hidden_and_desktop_actions(self):
    calls, desktop = self.run_setup(False, desktop='[Desktop Entry]\nName=Dropbox\nHidden=true\nExec=dropbox\n\n[Desktop Action Test]\nExec=unchanged\n')
    self.assertIn('Hidden=true',desktop)
    self.assertIn('Exec=systemctl --user start omarchy-dropbox.service',desktop)
    self.assertIn('Exec=unchanged',desktop)
    self.assertNotIn('start omarchy-dropbox.service',calls)
  def test_already_managed_does_not_stop(self):
    calls, _ = self.run_setup(True, managed=True)
    self.assertNotIn('graceful-stop',calls)
  def test_install_creates_autostart(self):
    calls, desktop = self.run_setup(False, mode='')
    self.assertIn('start omarchy-dropbox.service',calls)
    self.assertIn('Exec=systemctl --user start omarchy-dropbox.service',desktop)
  def test_optional_profile_preserves_other_widgets(self):
    with tempfile.TemporaryDirectory() as tmp:
      home=Path(tmp); config=home/'.config/omarchy/shell.json';config.parent.mkdir(parents=True)
      original={'bar':{'layout':{'right':[{'id':'other','refreshSeconds':1},{'id':'ryanyogan.omatop','notify':True}]}}}
      config.write_text(json.dumps(original));mocks=home/'bin';mocks.mkdir()
      shell=mocks/'omarchy-shell';shell.write_text('#!/bin/bash\nexit 0\n');shell.chmod(0o755)
      env=dict(os.environ,HOME=tmp,PATH=str(mocks)+':'+os.environ['PATH'])
      for _ in range(2):subprocess.run([str(ROOT/'bin/omarchy-setup-performance')],env=env,check=True)
      changed=json.loads(config.read_text())['bar']['layout']['right']
      self.assertEqual(changed[0],original['bar']['layout']['right'][0])
      self.assertEqual(changed[1],{'id':'ryanyogan.omatop','notify':True,'refreshSeconds':5})
      self.assertEqual(json.loads(config.with_name('shell.json.before-performance').read_text()),original)

unittest.main()
