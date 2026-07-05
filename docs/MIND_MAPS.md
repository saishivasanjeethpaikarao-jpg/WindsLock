# Windslock Mind Maps & Architecture Diagrams

These Mermaid.js diagrams outline the high-level architecture, database flows, and security measures of the application.

## Pro UI Flow & Architecture
```mermaid
graph TD
    UI[Windslock UI (CustomTkinter)]
    UI --> DB[EncryptedDatabase]
    UI --> Control[Enforcement Control]
    UI --> Overrides[Override / Friction Manager]
    UI --> Proxy[Path-Level Proxy]

    Control --> Enforcer[Background Enforcer]
    Enforcer --> Process[Process Watcher]
    Enforcer --> DB
```

## Security & Database Architecture
```mermaid
graph TD
    Password[Master Password] --> PBKDF2
    PBKDF2 --> DataKey[Unlock Master Data Key]

    Recovery[Recovery Codes] --> PBKDF2_2[PBKDF2 Verification]
    PBKDF2_2 --> DataKey

    Linux[Linux Keyring] --> DataKey
    Windows[Windows DPAPI] --> DataKey

    DataKey --> DB[Encrypted JSON Data File]
    DB --> Engine[Windslock Engine Rules]
```
