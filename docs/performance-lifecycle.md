# Desktop lifecycle and resource improvements

This fork review groups the Dropbox, plugin reload, application shutdown, service-budget, and reactive-wallpaper fixes. It also provides an explicit optional polling profile. The bootloader, disk encryption, display refresh rate, GPU driver settings, and application residency are unchanged.

## Dropbox ownership and inventory

Status polling does not walk the sync directory. The inventory loads when the panel opens, is cached for five minutes, and supports explicit refresh. Status generations prevent an older observation from reversing a pending pause/resume request. The scanner uses directory-entry metadata and retains only the newest requested file rows.

`omarchy-dropbox.service` owns the daemon even after its launcher exits. A stop requests Dropbox's supported graceful exit and waits for its process before systemd cleans up leftovers. The service source follows the existing `default/systemd/user/*.service` packaging layout; its stop helper uses the session's canonical `OMARCHY_PATH` rather than a hard-coded checkout.

`omarchy setup dropbox` prepares the unit and autostart, adopts an unmanaged daemon after a graceful stop, and starts syncing. Installation calls this setup automatically. The upgrade migration uses `--migrate` to preserve a stopped daemon and an absent/disabled autostart entry. Existing desktop action commands and other desktop-entry settings are preserved. Source checkouts without the matching settings package can install a user-unit copy through the same setup command.

## Reload correctness

The old cache-clearing function was unavailable in the installed QML runtime. Relevant plugin edits now use a debounced, guarded shell restart. Generated directories and files are excluded from the recursive watcher and its event filter. Restart is deferred while the session is locked, and the canonical restart command checks the lock again before terminating the old shell.

This remains a full shell restart, including unrelated plugin instances. Isolated per-plugin reload is future work. An edit made exclusively to an ignored build output requires an explicit shell restart. Configuration-only edits retain their existing reload behavior.

## Application exit and service budgets

Shutdown, reboot, and logout run through one transient user service. It batches window-close requests, watches for newly created save dialogs, and only then requests the system action. Preparation aborts after 30 seconds if windows remain. `omarchy shutdown --cancel` cancels pending preparation; the reboot and logout commands accept the same flag. Normal logind inhibitors are preserved. Window closure cannot prove every application has flushed its internal work; systemd still owns background-service teardown.

The 1Password autostart service uses `KillMode=mixed` so its helpers remain available during the main process's shutdown hooks. A runtime regression test moves a synthetic application's main process into a separate scope, reproducing the observed Electron process arrangement. Stopping its service and scope together fails with the old kill mode and succeeds with the new one.

The default user-service stop ceiling is 15 seconds, Voxtype has 10 seconds, 1Password has 15 seconds, and Dropbox has 20 seconds. The outer user-manager ceiling is 360 seconds, accommodating OpenClaw's existing explicit 330-second budget plus margin. These values are ceilings, not normal shutdown sleeps. The long OpenClaw allowance is preserved deliberately; the parent budget and optional-plugin policy should be reviewed before an upstream submission. The lexically last parent override also takes precedence over legacy `faster-shutdown.conf` drop-ins.

System settings ship via the normal `etc/` settings-package sources. Build the matching `omarchy-settings` package when testing those defaults from source. The migration reloads/reexecutes the user manager; it does not restart the shell or terminate 1Password.

## Wallpaper and optional telemetry

The reactive-background support from the existing Circuit City work is included as a prerequisite for its performance fixes, with its sidecar and example image. New upstream video-background handling remains intact. Reactive activity emits changes or a ten-second heartbeat, avoids reassigning unchanged values, and uses 450 ms transitions instead of overlapping 1.8-second transitions. Playback respects the existing lock/screensaver/power-saver gates and per-monitor fullscreen/DPMS state. A five-second monitor refresh covers state without a dedicated property. `omarchy-shell background-activity status` reports playback diagnostics without exposing session contents.

`omarchy setup performance` changes only an already configured `ryanyogan.omatop` widget to a five-second closed-panel refresh interval, retaining its fast open-panel cadence and other settings. It creates a backup and does not add or install third-party widgets. This is explicit user configuration, not an automatic migration.

## Validation and remaining review

Focused tests cover Dropbox state races during inventory, closed-panel polling, inventory totals and symlinks, plugin watcher filtering, save-dialog and rejected-power handling, split-scope termination, paused-daemon migration, desktop-entry preservation, and optional-profile idempotence. Existing manifest, command-style, background-activity, and CLI tests are also run.

On the development desktop, the earlier applied fixes completed a Dropbox stop/resume round trip and reached “Up to date.” A real nested-component edit loaded its new code after automatic restart, while a cache artifact did not trigger a restart. A full scan fell from approximately 2.8 to 1.3 seconds for roughly 469,000 files; Omatop's sampled CPU fell from approximately 0.73% to 0.13% of one logical CPU. These are local observations, not hardware-independent guarantees. Browser activity and application residency changed during GPU sampling, so no whole-desktop GPU or memory saving is claimed.

Actual power-off duration, the real 1Password exit during shutdown, a disposable graphical shutdown suite, and long-run reload endurance remain to be verified before upstreaming. This source review preserves the newer upstream baseline; it does not publish the development machine's installed-tree snapshot, package archive, personal configuration, screenshots, session logs, or raw audit artifacts.
