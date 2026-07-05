# Windslock Pro

![Windslock logo](assets/windslock_logo.png)

Windslock is a professional Windows focus-security app for locking distracting
apps, websites, URL paths, and private folders. It includes a branded desktop
UI, tray controller, optional CLI, background enforcer, recovery flow, and pro
startup tooling.

## Features

- **Premium desktop UI**: Branded control-center layout with status cards, focused tabs, polished actions, and clearer diagnostics.
- **Cross-Platform Security**: Protection and tamper-proof DB storage using Windows DPAPI or Linux Keyring.
- **Application Locking**: Block desktop apps dynamically by process name or full path.
- **Strict app lock mode**: By default, matched apps are stopped immediately. You can switch to detect/log mode from the Lock Apps tab.
- **Password unlock**: Re-enter the master password to temporarily unlock a selected app for the configured window.
- **Advanced advanced path-level Website Blocking**: Powered by a robust MITM proxy, restrict access to specific paths (e.g., `youtube.com/shorts`) without blocking the whole domain.
- **Folder Encryption**: AES-level encryption secures local folders from prying eyes.
- **Robust Database**: Features a zero-leakage `EncryptedDatabase` architecture leveraging Fernet encryption for full DB security.

## What Windslock Can Do

| Area | What works now | Important limit |
| --- | --- | --- |
| App locking | Locks by `.exe` name or full executable path. Strict mode stops matching apps immediately. | User-level enforcement can be stopped by a Windows administrator. |
| Website blocking | Blocks whole domains through reversible Windows Windows website-blocking entries. | Requires administrator rights to edit the real Windows website-blocking file. Browser Secure DNS can bypass or confuse testing. |
| URL path blocking | Blocks paths like `/shorts` or `/reels` through the advanced local proxy addon. | HTTPS path inspection requires a one-time local certificate install and browser proxy setup. |
| Folder locking | Encrypts a folder into a `.locked` file and restores it during unlock. | Keep backups; losing both password and recovery codes can make encrypted folders unrecoverable. |
| Unlock/recovery | Supports master password, emergency recovery codes, timed phrase overrides, and password unlock for selected apps. | Recovery codes must be saved outside the app folder. |
| Background mode | Keeps app enforcement active after the UI is closed. | A true enterprise-grade service would require a signed Windows service and installer flow. |

## App Tour

- **Home**: Shows the protection, startup, hosts status, rule count, and a compact system snapshot.
- **Focus**: Applies preset rule sets, starts timed focus sessions, and manages weekly schedules.
- **Lock Apps**: Adds app rules, picks from running processes, tests selected rules, toggles strict mode, and password-unlocks a selected app.
- **Block Websites**: Adds domain blocks, applies or rolls back hosts entries, checks Windows permission/status, and manages URL path rules.
- **Lock Folders**: Locks folders into encrypted `.locked` files and unlocks them when needed.
- **Temporary Unlock**: Manages the unlock phrase, cooldown timer, unlock window, and override request history.
- **History**: Shows recent blocked attempts, override actions, hosts events, and security changes.
- **Settings**: Manages Windows startup, stronger startup, password changes, and the app data folder.


## Simple Guide

Windslock has four main jobs:

1. **Lock apps**: choose an app like `chrome.exe`, `codex.exe`, or `notepad.exe`. When protection is on, Windslock closes that app when someone opens it.
2. **Block websites**: add a domain like `youtube.com` or `instagram.com`, then turn web blocking on.
3. **Lock folders**: choose a private folder and Windslock turns it into an encrypted `.locked` file.
4. **Temporary unlock**: unlock something for a short time with your password or the unlock phrase.

For most users, the normal flow is:

1. Open Windslock.
2. Add apps or websites.
3. Press **Turn protection on**.
4. Keep **Close locked apps immediately** checked.
5. Use **History** to see what was blocked.

Some features need administrator permission because Windows protects them:

- Website blocking needs admin when turning it on or off.
- Stronger startup needs admin. Normal startup works without admin.
- A Windows administrator can still bypass user-level protection.

## Documentation

- [Mind Maps & Architecture](docs/MIND_MAPS.md)
- [Brand Guide](docs/BRAND_GUIDE.md)
- [Workflows](docs/WORKFLOWS.md)
- [Windows And Linux Plan](docs/CROSS_PLATFORM_PLAN.md)
- [Build And Release Guide](docs/BUILD_RELEASES.md)
- [Code Signing Guide](docs/CODE_SIGNING.md)
- [Roadmap](docs/ROADMAP.md)

## Downloads

Latest desktop builds are published at the `latest-main` release:

- Windows installer: `Windslock-Setup.exe`
- Windows portable: `Windslock-Windows-OneFile.zip`
- Ubuntu, Linux Mint, Kali, Debian: `Windslock-Linux-Debian.deb`
- Other Linux desktops: `Windslock-Linux.tar.gz`

Release builds include SHA-256 checksums. Windows Authenticode signing and Linux
GPG signatures are automatic when the repository signing secrets are configured.

If a Windows EXE says it cannot load `python312.dll`, see the
[Windows Python DLL Error](docs/BUILD_RELEASES.md#windows-python-dll-error)
section.

## Setup

### Recommended Windows Install

1. Download `Windslock-Setup.exe` from the latest release.
2. Install and open Windslock.
3. Create a master password.
4. Save the emergency recovery codes outside the app folder.
5. Open **Lock Apps**, add a harmless test app such as `notepad.exe`, and keep **Close locked apps immediately** enabled.
6. Press **Start protection** or **Turn protection on**.
7. Open Notepad to confirm it is closed by Windslock.

For website blocking, run Windslock as administrator before pressing
**Turn web blocking on** in the Block Websites tab.

### Source Setup

Install Python 3.11+ and dependencies:

```powershell
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
run_windslock.bat
```

Run the pro launcher with tray + UI:

```powershell
run_windslock_pro.bat
```

Run only the tray controller:

```powershell
run_tray.bat
```

Run as administrator when applying website blocks to the real Windows Windows website-blocking file:

```powershell
run_windslock_admin.bat
```

Run the older command-line menu:

```powershell
run_cli.bat
```

## Pro Startup And Tray

The tray controller gives quick access to:

- Open Windslock
- Start/stop enforcement
- Start the advanced path-level proxy
- Open advanced local proxy certificate help

For more reliable startup than the registry Run key, install the scheduled task:

```powershell
install_startup_task.bat
```

Run it as administrator if you want Windows to create the task with highest
privileges. Remove it with:

```powershell
uninstall_startup_task.bat
```

Why Task Scheduler instead of a LocalSystem service: Windslock uses current-user
DPAPI so the background enforcer can read the encrypted config without storing
your password. A LocalSystem service would not automatically have access to that
current-user DPAPI secret. A true service design would need a separate service
credential/key handoff and installer flow.

## Portable EXE Build

Build local portable executables with:

```powershell
build_portable_exe.bat
```

Outputs:

```text
dist\Windslock\Windslock.exe
dist\WindslockTray\WindslockTray.exe
```

Common actions:

- Add an app rule with an executable name like `notepad.exe` or a full path like `C:\Games\App\game.exe`.
- Add a website rule with a domain like `youtube.com`.
- Add a advanced path-level website rule with a domain and path prefix, such as
  `youtube.com` plus `/shorts`.
- Apply website rules to the Windows website-blocking file from an elevated terminal.
- Run `run_proxy.bat` when you need advanced path-level website blocking.
- Apply a Focus preset if you want useful defaults without building every rule
  by hand.
- Use a timed Focus session for temporary strict enforcement.
- Enable schedule-only mode when you want blocking only during focus sessions or
  weekly schedule windows.
- Enable protection after signing in.
- Enable start with Windows if you want the enforcer to start on login.
- Use the history option to review recent blocked attempts.

## App Locking Details

App locks are stored as normalized rules:

- `name`: process name such as `codex.exe`, `notepad.exe`, or `chrome.exe`.
- `path`: full executable path such as `C:\Program Files\App\App.exe`.

Strict mode is enabled by default. When the background protection sees a
matching process, it stops it and records the attempt in History. Detect/log mode
is available for testing, but it does not block the app.

For the most reliable app locks:

1. Use **Running apps** to select the exact process.
2. Keep **Close locked apps immediately** checked.
3. Press **Start protection** after adding rules.
4. Use **Test selected** to confirm the rule matches a running process.
5. Enable **Start with Windows** for normal startup, or use **Stronger startup** when running as administrator.

## Website Blocking And Rollback

Website blocking uses the Windows Windows website-blocking file:

`C:\Windows\System32\drivers\etc\hosts`

Windslock writes only between these markers:

```text
# BEGIN WINDSLOCK BLOCKS
# END WINDSLOCK BLOCKS
```

Rollback removes only that marked section. Applying or rolling back the real
Windows website-blocking file usually requires an elevated terminal.

For Chrome, Edge, Brave, and other Chromium browsers:

- Run Windslock as administrator before pressing **Turn web blocking on**.
- Restart the browser after applying rules.
- If a blocked domain still opens, turn off the browser's Secure DNS / DNS-over-HTTPS setting, then apply again.
- Whole-domain blocks now write IPv4 and IPv6 entries for the domain plus common `www.` and `m.` variants.
- Hosts-file blocking cannot wildcard every possible subdomain. Add specific subdomains when needed.

The Block Websites tab includes a **Check** button that shows whether Windslock can
write the Windows website-blocking file and whether the saved rules are present.

## Path-Level Website Blocking

Hosts-file blocking cannot see URL paths. It can block `youtube.com`, but not
only `youtube.com/shorts`. For advanced path-level rules, Windslock includes a advanced local proxy
addon:

```powershell
run_proxy.bat
```

Then configure the browser or Windows proxy settings to use:

```text
HTTP proxy:  127.0.0.1
Port:        8080
```

For HTTPS websites, install advanced local proxy's local certificate once:

```powershell
open_proxy_cert_help.bat
```

That opens `http://mitm.it` while the proxy is running. Follow the Windows cert
install steps from advanced local proxy. This is required because HTTPS hides the URL path
from normal website blocking.

Advanced advanced path-level rules are managed in the Block Websites tab. Examples:

- `youtube.com` + `/shorts`
- `instagram.com` + `/reels`
- `reddit.com` + `/r/all`

Limits:

- Lock Apps or browsers that bypass the configured proxy will bypass advanced path-level rules.
- Certificate pinning may prevent inspection for some apps.
- Do not install the advanced local proxy certificate unless you understand that the local
  proxy can inspect HTTPS traffic while it is active.

## Temporary Temporary Unlock

Temporary Unlock are intentionally friction-based:

1. Request an override for an app, site, URL path, or folder target.
2. Type the exact unlock phrase. A mismatch is denied immediately and logged.
3. If the phrase is correct, the cooldown starts. Default: 5 minutes.
4. After cooldown, the target unlocks for a limited window. Default: 10 minutes.
5. When the window ends, Windslock automatically re-locks and logs the event.

The phrase and timers are managed in the Temporary Unlock tab. The default phrase is:

```text
I understand this is temporary and I will return to focus
```

For app overrides, use the same target shown in the app lock table, such as
`notepad.exe` or the full normalized executable path. For whole-site overrides,
use the domain, such as `youtube.com`. For URL path overrides, use
`domain/path`, such as `youtube.com/shorts`.

The Lock Apps tab also has **Password unlock selected**. It asks for the master
password again, creates an immediate timed app override, logs the action, and
auto re-locks when the window expires. The default window is 10 minutes.

## Focus Presets And Schedules

The Focus tab adds user-friendly workflows on top of raw blocking rules:

- Presets: `Deep Work`, `Study Mode`, and `Social Detox` add common distracting
  apps, domains, and advanced path-level rules.
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

Protection is a normal user-session Python process, not a Windows
kernel driver or enterprise AppLocker policy. It polls running processes and
kills matches. When enabled, it stores only the encrypted config data key through
Windows DPAPI or Linux Keyring for the current user.

Limits:

- An administrator can stop the process, edit startup settings, change Windows website-blocking entries, delete app files, or run tools from another account.
- A fast-launching app may appear briefly before the next polling cycle kills it.
- Strong anti-tamper needs a signed Windows service, installer, service recovery settings, and admin-managed policy.

## Tamper Resistance

Current protections are basic:

- Config is encrypted via `EncryptedDatabase`.
- Background unlock uses OS secure store (DPAPI/Keyring).
- **Protect settings folder** restricts the app settings folder to the current user, Administrators, and SYSTEM.
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
py -m unittest discover -s tests -v
```

Manual tests can be run safely using dummy profiles.
