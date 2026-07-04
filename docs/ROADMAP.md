# Windslock Roadmap

This roadmap keeps Windslock focused on real user problems.

## Product Principles

1. Protect focus without trapping the user.
2. Make bypass possible but intentionally inconvenient.
3. Prefer reversible changes over permanent system modification.
4. Keep recovery paths clear.
5. Be honest about admin/root bypass.
6. Make daily use easier than manual self-control.

## Current Version

Current capabilities:

- Branded Windows desktop UI
- App locking by name/path
- Website domain blocking
- URL path blocking through mitmproxy
- Folder encryption lock
- Focus presets
- Focus sessions
- Weekly schedules
- Friction-based override
- Encrypted audit history
- Tray controller
- Task Scheduler startup
- Portable EXE build script

## Near-Term Improvements

### 1. Installer Experience

Deliverables:

- Inno Setup installer
- Start Menu shortcut
- Desktop shortcut
- Tray autostart option
- Clean uninstaller

Why:

Users should not need to understand Python, virtual environments, or batch files.

### 2. Better Dashboard

Deliverables:

- “Protected now” status
- Active focus session countdown
- Active override countdown
- Last blocked attempt
- Hosts/proxy health checks

Why:

Users need confidence that Windslock is actually working.

### 3. Linux MVP

Deliverables:

- Linux secure store adapter
- Linux hosts adapter
- systemd user service
- Linux tray launch
- AppImage build

Why:

The core product is useful on Linux if OS-specific integrations are clean.

### 4. Health Checks

Deliverables:

- Background enforcer status
- Hosts-file applied status
- Proxy running status
- Certificate setup checklist
- Startup task status

Why:

Blocking apps fail quietly if setup is wrong. Health checks make problems visible.

## Mid-Term Improvements

### 1. Policy Profiles

Examples:

- Work
- Study
- Sleep
- Weekend
- Social detox

Each profile controls:

- App rules
- Domain rules
- Path rules
- Schedule
- Override timers

### 2. Import/Export Rules

Deliverables:

- Export encrypted backup
- Import backup
- Export plain rule template without secrets

Why:

Users need migration and backup without leaking passwords.

### 3. Stronger Windows Integration

Deliverables:

- Installer
- Signed binaries
- Optional Windows service
- Service key handoff design

Why:

User-level enforcement is good for personal focus. A service improves resilience.

## Long-Term Ideas

- Browser extension companion for path-level blocking without full HTTPS proxy.
- Family/shared-device mode with separate admin password.
- Cloud-free sync via encrypted local file.
- Pomodoro and session analytics.
- AI-assisted rule suggestions from blocked history.
- Per-app override timers.

## What Not To Build Yet

Avoid these until core stability is excellent:

- Cloud accounts
- Remote monitoring
- Social leaderboard
- Aggressive anti-admin tricks
- Unremovable lock modes

These features increase risk and reduce trust.

## Release Tracks

### Windslock Personal

For individual focus:

- User-level enforcer
- Tray
- Presets
- Overrides
- Folder locking

### Windslock Pro

For serious local setup:

- Installer
- Startup task
- Health checks
- Portable EXE
- Advanced schedules

### Windslock Managed

Future idea only:

- Admin policy
- Signed service
- Central configuration
- Enterprise logging

This requires a different security model.
