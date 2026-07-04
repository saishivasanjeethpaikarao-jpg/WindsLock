# Windslock Mind Maps

These maps show the product as a complete focus-security system.

## Product Mind Map

```mermaid
mindmap
  root((Windslock))
    Locking
      Desktop apps
        Process name
        Executable path
        Running app picker
      Websites
        Whole domain
        Hosts file
        Rollback markers
      URL paths
        mitmproxy addon
        HTTPS certificate setup
        Path prefixes
      Folders
        Encrypted .locked archive
        Safe extraction
        Wrong-password protection
    Focus
      Presets
        Deep Work
        Study Mode
        Social Detox
      Timed sessions
      Weekly schedules
      Schedule-only mode
    Overrides
      Exact commitment phrase
      Instant denial
      Cooldown
      Limited unlock window
      Auto re-lock
      Audit log
    Security
      Encrypted config
      DPAPI background key
      Recovery codes
      ACL hardening
      Admin-bypass honesty
    Pro UX
      Desktop UI
      Tray controller
      Startup task
      Portable EXE build
      README and docs
```

## User Problem Mind Map

```mermaid
mindmap
  root((User Problems))
    Distraction
      Games
      Social media
      Video shorts
      Infinite feeds
    Privacy
      Sensitive folders
      Shared computer
      Accidental access
    Self-control
      Impulsive unlocks
      Late-night usage
      Study/work windows
    Trust
      Do not lose data
      Do not get locked out
      Clear rollback path
      Honest limits
    Convenience
      No guessing process names
      One-click presets
      Tray status
      Start with Windows
```

## Enforcement Mind Map

```mermaid
mindmap
  root((Enforcement))
    App enforcement
      psutil process scan
      Name match
      Path match
      Kill blocked process
      Log attempt
    Domain enforcement
      Hosts file
      Begin/end markers
      Admin required
      Reapply when override changes
    Path enforcement
      Browser proxy
      mitmproxy addon
      URL parser
      Block response
      Certificate required for HTTPS
    Folder enforcement
      Encrypt folder
      Verify archive
      Remove original
      Restore safely
    State engine
      Config decrypt
      DPAPI service key
      Override processing
      Schedule checks
```

## Trust And Recovery Mind Map

```mermaid
mindmap
  root((Trust))
    Password safety
      No plaintext password
      PBKDF2 verifier
      Encrypted data key envelope
    Local secrets
      Windows DPAPI
      Current-user scope
      Background unlock
    Recovery
      One-time codes
      Password reset
      Code rotation
    Data safety
      Verify before deleting folder
      Rollback hosts entries
      Ignore dangerous folders
      Tests
    Transparency
      Logs
      Security limits
      Admin bypass documented
```

## Platform Expansion Mind Map

```mermaid
mindmap
  root((Cross Platform))
    Windows
      DPAPI
      Task Scheduler
      Hosts file
      Tkinter
      Tray
      PyInstaller
    Linux
      Secret Service or keyring
      systemd user service
      /etc/hosts or nftables
      Desktop files
      AppImage/deb/rpm
      Wayland/X11 differences
    Shared core
      Config schema
      Rule engine
      Override engine
      Focus engine
      Tests
      Docs
```
