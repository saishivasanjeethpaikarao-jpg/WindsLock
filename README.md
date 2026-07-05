# Windslock

![Windslock logo](assets/windslock_logo.png)

Windslock is a professional Windows focus-security app for locking distracting
apps, websites, URL paths, and private folders. It includes a branded desktop
UI, tray controller, optional CLI, background enforcer, recovery flow, and pro
startup tooling.

## Documentation

- [Brand Guide](docs/BRAND_GUIDE.md)
- [Mind Maps](docs/MIND_MAPS.md)
- [Workflows](docs/WORKFLOWS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Windows And Linux Plan](docs/CROSS_PLATFORM_PLAN.md)
- [Build And Release Guide](docs/BUILD_RELEASES.md)
- [Roadmap](docs/ROADMAP.md)

## What Works

- Locks desktop apps by process name, such as `steam.exe`, or by full executable path.
- Blocks websites by domain through reversible Windows hosts-file entries.
- Blocks URL path prefixes through the mitmproxy addon, for cases like
  `youtube.com/shorts` while keeping normal YouTube pages available.
- Supports friction-based temporary overrides: exact phrase, cooldown, limited
  unlock window, automatic re-lock, and full logging.
- Locks folders into encrypted `.locked` archives and restores them with the master password.
- Stores settings in encrypted local config under `%APPDATA%\Windslock`.
- Uses password-derived key wrapping, password verification hashes, and one-time recovery codes.
- Can store the config data key with Windows DPAPI for background enforcement without storing the password.
- Can start background enforcement when the current Windows user signs in.
- Keeps encrypted audit history of app and folder block/unlock events.
- Provides a Tkinter desktop UI for managing rules, folders, background mode,
  startup, recovery, and history.
- Includes one-click focus presets, timed focus sessions, schedule-only mode,
  weekly schedules, and a running-app picker.
- Includes a tray controller, pro startup task scripts, and optional portable
  EXE build script.

## Setup

Install Python 3.11+ and dependencies:

```powershell
cd D:\Windslock\files
py -m pip install -r requirements.txt
run_windslock.bat
```

If `py` is not available, use your Python executable:

```powershell
python -m pip install -r requirements.txt
python main.py
```

On first run, Windslock creates a master password and prints emergency recovery
codes. Store those codes outside the app folder.

## Usage

Run the desktop app:

```powershell
D:\Windslock\files\run_windslock.bat
```

Run the pro launcher with tray + UI:

```powershell
D:\Windslock\files\run_windslock_pro.bat
```

Run only the tray controller:

```powershell
D:\Windslock\files\run_tray.bat
```

Run as administrator when applying website blocks to the real Windows hosts file:

```powershell
D:\Windslock\files\run_windslock_admin.bat
```

Run the older command-line menu:

```powershell
D:\Windslock\files\run_cli.bat
```

## Pro Startup And Tray

The tray controller gives quick access to:

- Open Windslock
- Start/stop enforcement
- Start the path-level proxy
- Open mitmproxy certificate help

For more reliable startup than the registry Run key, install the scheduled task:

```powershell
D:\Windslock\files\install_startup_task.bat
```

Run it as administrator if you want Windows to create the task with highest
privileges. Remove it with:

```powershell
D:\Windslock\files\uninstall_startup_task.bat
```

Why Task Scheduler instead of a LocalSystem service: Windslock uses current-user
DPAPI so the background enforcer can read the encrypted config without storing
your password. A LocalSystem service would not automatically have access to that
current-user DPAPI secret. A true service design would need a separate service
credential/key handoff and installer flow.

## Portable EXE Build

Build local portable executables with:

```powershell
D:\Windslock\files\build_portable_exe.bat
```

Outputs:

```text
D:\Windslock\files\dist\Windslock\Windslock.exe
D:\Windslock\files\dist\WindslockTray\WindslockTray.exe
```

Common actions:

- Add an app rule with an executable name like `notepad.exe` or a full path like `C:\Games\App\game.exe`.
- Add a website rule with a domain like `youtube.com`.
- Add a path-level website rule with a domain and path prefix, such as
  `youtube.com` plus `/shorts`.
- Apply website rules to the hosts file from an elevated terminal.
- Run `run_proxy.bat` when you need path-level website blocking.
- Apply a Focus preset if you want useful defaults without building every rule
  by hand.
- Use a timed Focus session for temporary strict enforcement.
- Enable schedule-only mode when you want blocking only during focus sessions or
  weekly schedule windows.
- Enable background enforcement after signing in.
- Enable start with Windows if you want the enforcer to start on login.
- Use the history option to review recent blocked attempts.

## Website Blocking And Rollback

Website blocking uses the Windows hosts file:

`C:\Windows\System32\drivers\etc\hosts`

Windslock writes only between these markers:

```text
# BEGIN WINDSLOCK BLOCKS
# END WINDSLOCK BLOCKS
```

Rollback removes only that marked section. Applying or rolling back the real
hosts file usually requires an elevated terminal.

## Path-Level Website Blocking

Hosts-file blocking cannot see URL paths. It can block `youtube.com`, but not
only `youtube.com/shorts`. For path-level rules, Windslock includes a mitmproxy
addon:

```powershell
D:\Windslock\files\run_proxy.bat
```

Then configure the browser or Windows proxy settings to use:

```text
HTTP proxy:  127.0.0.1
Port:        8080
```

For HTTPS websites, install mitmproxy's local certificate once:

```powershell
D:\Windslock\files\open_proxy_cert_help.bat
```

That opens `http://mitm.it` while the proxy is running. Follow the Windows cert
install steps from mitmproxy. This is required because HTTPS hides the URL path
from normal DNS/hosts blocking.

Path-level rules are managed in the Websites tab. Examples:

- `youtube.com` + `/shorts`
- `instagram.com` + `/reels`
- `reddit.com` + `/r/all`

Limits:

- Apps or browsers that bypass the configured proxy will bypass path-level rules.
- Certificate pinning may prevent inspection for some apps.
- Do not install the mitmproxy certificate unless you understand that the local
  proxy can inspect HTTPS traffic while it is active.

## Temporary Overrides

Overrides are intentionally friction-based:

1. Request an override for an app, site, URL path, or folder target.
2. Type the exact commitment phrase. A mismatch is denied immediately and logged.
3. If the phrase is correct, the cooldown starts. Default: 5 minutes.
4. After cooldown, the target unlocks for a limited window. Default: 10 minutes.
5. When the window ends, Windslock automatically re-locks and logs the event.

The phrase and timers are managed in the Overrides tab. The default phrase is:

```text
I understand this is temporary and I will return to focus
```

For app overrides, use the same target shown in the app lock table, such as
`notepad.exe` or the full normalized executable path. For whole-site overrides,
use the domain, such as `youtube.com`. For URL path overrides, use
`domain/path`, such as `youtube.com/shorts`.

## Focus Presets And Schedules

The Focus tab adds user-friendly workflows on top of raw blocking rules:

- Presets: `Deep Work`, `Study Mode`, and `Social Detox` add common distracting
  apps, domains, and path-level rules.
- Timed focus sessions: set a duration, start the session, and Windslock logs it.
- Schedule-only mode: when enabled, rules enforce only during an active focus
  session or a matching weekly schedule.
- Weekly schedules: create windows like Monday-Friday 09:00-17:00.
- Running-app picker: choose a currently running process instead of guessing the
  exact `.exe` name.

By default, Windslock still enforces all rules all the time. Schedule-only mode
is opt-in.

## Folder Locking

Folder locking encrypts a zip archive into `<folder>.locked`, verifies that the
encrypted archive can be decrypted and read, then removes the original folder.
Unlocking restores the folder and removes the `.locked` file.

Safety notes:

- Do not lock system folders, app-data folders, drive roots, or folders you do not own.
- Keep backups of important data. Encryption is real; losing both the password and recovery codes can make locked folders unrecoverable.
- The unlock path is checked against zip path traversal.

## Background Enforcement

Background enforcement is a normal user-session Python process, not a Windows
kernel driver or enterprise AppLocker policy. It polls running processes and
kills matches. When enabled, it stores only the encrypted config data key through
Windows DPAPI for the current user.

Limits:

- An administrator can stop the process, edit startup settings, change hosts-file entries, delete app files, or run tools from another account.
- A fast-launching app may appear briefly before the next polling cycle kills it.
- Strong anti-tamper needs a signed Windows service, installer, service recovery settings, and admin-managed policy.

## Tamper Resistance

Current protections are basic:

- Config is encrypted.
- Background unlock uses DPAPI for the current Windows user.
- Optional ACL hardening restricts the config folder to the current user, Administrators, and SYSTEM.
- Startup registration can restart enforcement at login.

This does not prevent a local administrator from bypassing Windslock.

## Emergency Recovery

If you forget the master password:

1. Run `py main.py`.
2. Fail login or choose the recovery prompt.
3. Enter one recovery code.
4. Set a new master password.
5. Save the newly printed recovery codes.

Recovery codes are one-time because resetting the password rotates all codes.

## Testing

Automated tests use temporary app data and do not touch your real config:

```powershell
cd D:\Windslock\files
py -m unittest discover -s tests -v
```

Manual Windows tests:

1. First-run setup: delete or move `%APPDATA%\Windslock` only if you intentionally want a fresh test profile, then run `run_windslock.bat` and confirm recovery codes appear.
2. UI smoke test: open every tab, add/remove one harmless app rule and one harmless domain rule.
3. Focus preset: apply `Deep Work`, confirm apps/sites/path rules appear.
4. Focus session: enable schedule-only mode, start a short session, and confirm rules enforce only during that session.
5. App blocking: add `notepad.exe`, start background enforcement, open Notepad, and confirm it is killed and logged.
6. Path blocking: add the full path of a harmless test executable and confirm only that path is blocked.
7. Website blocking: run `run_windslock_admin.bat`, add `example.com`, apply hosts entries, confirm the marked block appears in hosts, then roll it back.
8. Path-level blocking: add `youtube.com` + `/shorts`, run `run_proxy.bat`, configure proxy/cert, and confirm `/shorts` is blocked while normal YouTube pages still load.
9. Override denial: request an override with the wrong phrase and confirm it is denied and logged.
10. Override activation: request with the correct phrase, confirm it stays locked during cooldown, unlocks after cooldown, and re-locks after the window.
11. Folder locking: create a disposable test folder, lock it, confirm `.locked` exists and the folder is removed, then unlock it and verify files return.
12. Background enforcement: enable background enforcement, close the UI, launch a blocked app, and confirm it is still killed.
13. Start with Windows: enable startup, sign out/in, and confirm `enforcer.py` starts for your user.
14. Recovery: use a test profile, reset with a recovery code, confirm the old password and old recovery code no longer work.

## Project Notes

The active top-level files are in `D:\Windslock\files`. The nested
`D:\Windslock\files\files` folder appears to be an older duplicate and is left
in place intentionally.
