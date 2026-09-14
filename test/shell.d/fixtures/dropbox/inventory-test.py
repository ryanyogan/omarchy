import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

source = Path(os.environ['ROOT']) / 'shell/plugins/panels/dropbox/status.py'
spec = importlib.util.spec_from_file_location('dropbox_status', source)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)
with tempfile.TemporaryDirectory() as tmp:
  root = Path(tmp)
  (root / 'nested').mkdir()
  for n in range(10):
    file = root / 'nested' / str(n)
    file.write_bytes(b'x' * n)
    os.utime(file, (n, n))
  (root / 'loop').symlink_to(root, target_is_directory=True)
  (root / 'alias').symlink_to(root / 'nested' / '9')
  total, rows = status.scan_dropbox(root, 3)
  assert total == 45 and [r['name'] for r in rows] == ['9', '8', '7']
  assert all(r['folder'] == 'nested' for r in rows)
  with patch.object(status, 'read_info', return_value={'personal': {'path': tmp}}), \
       patch.object(status, 'command_output', return_value=(0, 'Up to date')), \
       patch.object(status, 'scan_dropbox', side_effect=AssertionError('unexpected inventory')), \
       patch('sys.argv', ['status.py', '--quick']), contextlib.redirect_stdout(io.StringIO()) as output:
    status.main()
    assert json.loads(output.getvalue())['files'] == []
print('ok - inventory totals, newest files, symlinks, and quick path')
