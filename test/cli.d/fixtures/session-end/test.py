import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

source=Path(__file__).resolve().parents[4]/'default/session-end.py'
spec=importlib.util.spec_from_file_location('session_end',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SessionEnd(unittest.TestCase):
  def scenario(self, sequence, action='shutdown', fail_power=False):
    calls=[]; tick=[0]
    def run(*args, **kwargs):
      calls.append(args)
      if args[:3]==('hyprctl','clients','-j'):
        raise AssertionError('windows should be mocked')
      if args[0]=='systemctl' and fail_power:
        return SimpleNamespace(returncode=1,stdout='',stderr='inhibited')
      count = len(args[-1].split('; ')) if args[:2] == ('hyprctl', '--batch') else 1
      return SimpleNamespace(returncode=0,stdout='ok\n\n' * count,stderr='')
    def sleep(duration): tick[0]+=duration
    def windows():
      if len(sequence)>1: return sequence.pop(0)
      return sequence[0]
    with patch.object(module,'windows',side_effect=windows), patch.object(module,'run',side_effect=run), patch.object(module.time,'monotonic',side_effect=lambda:tick[0]), patch.object(module.time,'sleep',side_effect=sleep):
      try: module.prepare(action,deadline_seconds=2)
      except RuntimeError as error: return calls, str(error)
    return calls, None
  def test_clean_close(self):
    calls,error=self.scenario([[{'address':'0x1'}],[]])
    self.assertIsNone(error)
    self.assertLess(next(i for i,c in enumerate(calls) if c[0]=='hyprctl'),next(i for i,c in enumerate(calls) if c[0]=='systemctl'))
  def test_new_save_dialog_blocks_shutdown(self):
    calls,error=self.scenario([[{'address':'0x1'}],[],[{'address':'0x2'}]])
    self.assertIn('applications are still open',error)
    self.assertFalse(any(c[0] in ('systemctl','omarchy-state') for c in calls))
  def test_multiple_windows_batch(self):
    calls,error=self.scenario([[{'address':'0x1'},{'address':'0x2'}],[]])
    self.assertIsNone(error)
    self.assertEqual(sum(c[:2]==('hyprctl','--batch') for c in calls),1)
  def test_rejected_power_preserves_state(self):
    calls,error=self.scenario([[]],fail_power=True)
    self.assertEqual(error,'inhibited')
    self.assertFalse(any(c[0]=='omarchy-state' for c in calls))
  def test_logout_uses_uwsm(self):
    calls,error=self.scenario([[]],action='logout')
    self.assertIsNone(error);self.assertIn(('uwsm','stop'),calls)
    self.assertFalse(any(c[0]=='systemctl' for c in calls))
  def test_invalid_address_cannot_dispatch(self):
    calls,error=self.scenario([[{'address':'0x1; exec bad'}]])
    self.assertIsNotNone(error);self.assertEqual(calls,[])

unittest.main()
