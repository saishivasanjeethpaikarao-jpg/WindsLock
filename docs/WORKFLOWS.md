# Windslock Workflows

This document describes the key user and system workflows.

## First Run

```mermaid
flowchart TD
    A["Open Windslock"] --> B{"Config exists?"}
    B -->|No| C["Create master password"]
    C --> D["Generate encrypted config"]
    D --> E["Show recovery codes"]
    E --> F["User saves recovery codes"]
    B -->|Yes| G["Login"]
    G --> H["Open dashboard"]
```

Success criteria:

- No plaintext password is stored.
- Recovery codes are shown once.
- User reaches dashboard only after setup/login.

## App Lock Workflow

```mermaid
flowchart TD
    A["User opens Apps tab"] --> B{"Known exe?"}
    B -->|Yes| C["Type exe name or path"]
    B -->|No| D["Open running-app picker"]
    D --> E["Select process name"]
    C --> F["Add rule"]
    E --> F
    F --> G["Save encrypted config"]
    G --> H["Background enforcer scans processes"]
    H --> I{"Process matches rule?"}
    I -->|No| H
    I -->|Yes| J{"Active override?"}
    J -->|Yes| H
    J -->|No| K["Kill process"]
    K --> L["Log blocked attempt"]
```

## Website Domain Block Workflow

```mermaid
flowchart TD
    A["User adds domain"] --> B["Save encrypted config"]
    B --> C["Run app as admin"]
    C --> D["Apply hosts block"]
    D --> E["Write Windslock marker section"]
    E --> F["Domain resolves to 0.0.0.0"]
    F --> G["Browser cannot open domain"]
    G --> H["Rollback removes only Windslock section"]
```

Rollback guarantee:

- Windslock only removes content between `BEGIN WINDSLOCK BLOCKS` and `END WINDSLOCK BLOCKS`.

## Path-Level Website Block Workflow

```mermaid
flowchart TD
    A["User adds domain + path prefix"] --> B["Start path-level proxy"]
    B --> C["Configure browser proxy 127.0.0.1:8080"]
    C --> D["Install mitmproxy certificate"]
    D --> E["Browser requests HTTPS URL"]
    E --> F["mitmproxy sees full URL path"]
    F --> G{"Rule matches path prefix?"}
    G -->|No| H["Allow request"]
    G -->|Yes| I{"Active override?"}
    I -->|Yes| H
    I -->|No| J["Return Windslock block page"]
    J --> K["Log blocked URL path"]
```

Important limit:

- HTTPS path blocking requires the local certificate because HTTPS hides URL paths from DNS and hosts-file tools.

## Friction Override Workflow

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Denied: Wrong phrase
    Requested --> Cooldown: Exact phrase
    Denied --> [*]: Logged
    Cooldown --> Active: Cooldown elapsed
    Active --> Expired: Unlock window elapsed
    Expired --> [*]: Re-locked and logged
```

Default timers:

- Cooldown: 5 minutes
- Unlock window: 10 minutes

Every state transition is written to the encrypted audit log.

## Focus Session Workflow

```mermaid
flowchart TD
    A["Apply preset"] --> B["Rules added"]
    B --> C["Enable schedule-only mode?"]
    C -->|No| D["Rules enforce always"]
    C -->|Yes| E["Start session or wait for schedule"]
    E --> F{"Focus active?"}
    F -->|No| G["Rules paused"]
    F -->|Yes| H["Rules enforce"]
    H --> I["Session ends"]
    I --> G
```

## Folder Lock Workflow

```mermaid
flowchart TD
    A["Choose folder"] --> B{"Dangerous path?"}
    B -->|Yes| C["Refuse"]
    B -->|No| D["Zip folder in memory"]
    D --> E["Encrypt archive"]
    E --> F["Write temp locked file"]
    F --> G["Verify decrypt and zip integrity"]
    G -->|Fail| H["Keep original folder"]
    G -->|Pass| I["Move temp to .locked"]
    I --> J["Remove original folder"]
    J --> K["Record locked folder"]
```

## Emergency Recovery Workflow

```mermaid
flowchart TD
    A["User forgets password"] --> B["Open Recovery"]
    B --> C["Enter recovery code"]
    C --> D{"Valid code?"}
    D -->|No| E["Deny"]
    D -->|Yes| F["Set new password"]
    F --> G["Rotate all recovery codes"]
    G --> H["Show new codes"]
    H --> I["Old code no longer works"]
```

## Pro Startup Workflow

```mermaid
flowchart TD
    A["User enables background unlock"] --> B["Store data key with DPAPI"]
    B --> C["Install scheduled task"]
    C --> D["Windows logon"]
    D --> E["Tray starts"]
    E --> F["User starts enforcer or opens UI"]
    F --> G["Enforcer reads DPAPI key"]
    G --> H["Rules enforced"]
```
