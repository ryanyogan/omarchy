"""Prepare a session exit without racing application save dialogs."""
import argparse
import json
import re
import subprocess
import sys
import time


def run(*args, **kwargs):
  return subprocess.run(args, text=True, capture_output=True, timeout=5, **kwargs)


def windows():
  result = run('hyprctl', 'clients', '-j')
  if result.returncode:
    raise RuntimeError('Cannot read application windows')
  clients = json.loads(result.stdout)
  if not isinstance(clients, list):
    raise RuntimeError('Invalid compositor response')
  return [c for c in clients if c.get('mapped', True)]


def notify(message):
  run('omarchy-notification-send', 'Session exit', message)


def prepare(action, deadline_seconds=30):
  started = time.monotonic()
  clients = windows()
  requests = []
  for client in clients:
    address = client.get('address', '')
    if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
      raise RuntimeError('Invalid application window address')
    requests.append('dispatch hl.dsp.window.close({ window = "address:' + address + '" })')
  if requests:
    result = run('hyprctl', '--batch', '; '.join(requests))
    responses = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode or responses != ['ok'] * len(requests):
      raise RuntimeError('Could not request application closure')

  # Watch all mapped windows, including save dialogs created after close was
  # requested. Two empty observations allow a delayed dialog to become mapped.
  empty_since = None
  while True:
    remaining = windows()
    now = time.monotonic()
    if remaining:
      empty_since = None
      if now - started >= deadline_seconds:
        raise RuntimeError('Cancelled: applications are still open. Save or close them, then try again.')
    else:
      if empty_since is None:
        empty_since = now
      if now - empty_since >= 0.5:
        break
    time.sleep(0.2)
  print(f'{action}: application windows closed in {time.monotonic() - started:.2f}s', flush=True)

  # Preserve logind inhibitors and systemd's normal service shutdown. There is
  # no independent power-off timer and no forced kill when a dialog remains.
  command = ('uwsm', 'stop') if action == 'logout' else ('systemctl', 'poweroff' if action == 'shutdown' else 'reboot', '--no-wall')
  result = run(*command)
  if result.returncode:
    raise RuntimeError(result.stderr.strip() or 'Session exit was rejected')
  if action != 'logout':
    run('omarchy-state', 'clear', 're*-required')


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('action', choices=['shutdown', 'reboot', 'logout'])
  parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('--cancel', action='store_true', help='cancel pending application closure')
  args = parser.parse_args()
  try:
    if args.cancel:
      result = run('systemctl', '--user', 'stop', 'omarchy-session-end.service')
      return result.returncode
    if args.worker:
      prepare(args.action)
      return 0
    result = run('systemd-run', '--user', '--collect', '--quiet',
      '--unit=omarchy-session-end', '--description=Close applications before session exit',
      '--property=Type=exec', '--property=TimeoutStopSec=5s',
      sys.executable, __file__, args.action, '--worker')
    if result.returncode:
      raise RuntimeError(result.stderr.strip() or 'Could not start session exit')
    return 0
  except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
    print(str(error), file=sys.stderr, flush=True)
    try:
      notify(str(error))
    except (OSError, subprocess.TimeoutExpired):
      pass
    return 1


if __name__ == '__main__':
  sys.exit(main())
