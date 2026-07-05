# Build And Release Guide

Windslock can be built locally on Windows and automatically on GitHub Actions
for Windows and Linux.

## GitHub Actions

Workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/desktop-builds.yml`

Artifacts:

- `Windslock-Setup.exe`
- `Windslock-Windows.zip`
- `Windslock-Windows-OneFile.zip`
- `Windslock-Windows-SHA256SUMS.txt`
- `Windslock-Linux.tar.gz`
- `Windslock-Linux-Debian.deb`
- `Windslock-Linux-SHA256SUMS.txt`
- Linux `.asc` signatures when GPG signing is configured

Triggers:

- Push to `main`
- Manual workflow dispatch
- Published GitHub release

On a published release, the workflow uploads the Windows installer, Windows
portable packages, Linux portable package, Debian-family Linux package,
checksums, and optional signatures to the release assets.

Recommended downloads:

- Windows: `Windslock-Setup.exe`
- Windows portable fallback: `Windslock-Windows-OneFile.zip`
- Ubuntu, Linux Mint, Kali, Debian: `Windslock-Linux-Debian.deb`
- Other Linux desktops: `Windslock-Linux.tar.gz`

## Code Signing

See [Code Signing Guide](CODE_SIGNING.md) for the full setup.

Windows Authenticode signing is automatic when these GitHub Actions secrets are
configured:

- `WINDOWS_SIGNING_CERT_BASE64`
- `WINDOWS_SIGNING_CERT_PASSWORD`
- `WINDOWS_TIMESTAMP_URL` optional

Linux detached GPG signatures are automatic when these secrets are configured:

- `RELEASE_GPG_PRIVATE_KEY`
- `RELEASE_GPG_PASSPHRASE`

If signing secrets are missing, the build still succeeds and releases unsigned
artifacts with SHA-256 checksum files. Signed Windows builds still may show
SmartScreen warnings until the certificate builds reputation.

## Windows Local Build

From `D:\Windslock\files`:

```powershell
.\build_portable_exe.bat
```

Outputs:

```text
dist\Windslock\Windslock.exe
dist\WindslockTray\WindslockTray.exe
dist\WindslockProxy\WindslockProxy.exe
dist\installer\Windslock-Setup.exe
dist-onefile\Windslock.exe
```

Recommended package shape:

```text
Windslock-Windows.zip
  Windslock.exe
  WindslockTray\
  WindslockProxy\
  assets\
  docs\
  run_windslock.bat
  run_tray.bat
  run_proxy.bat
  install_startup_task.bat
  uninstall_startup_task.bat
  open_proxy_cert_help.bat
  README.md
```

## Linux Build

Linux builds run in GitHub Actions on Ubuntu. The build script is:

```bash
bash scripts/build_linux_app.sh
bash scripts/build_linux_deb.sh
```

Outputs:

```text
dist/Windslock-Linux.tar.gz
dist/Windslock-Linux-Debian.deb
dist/Windslock-Linux-SHA256SUMS.txt
```

`Windslock-Linux-Debian.deb` is for Debian-family x64 desktops: Ubuntu, Linux
Mint, Kali, Debian, and close derivatives.

Package shape:

```text
Windslock-Linux/
  Windslock/
  WindslockTray/
  WindslockProxy/
  assets/
  docs/
  packaging/linux/
  run_windslock.sh
  run_tray.sh
  run_proxy.sh
  README.md
```

Install for current Linux user:

```bash
tar -xzf Windslock-Linux.tar.gz
cd Windslock-Linux
bash packaging/linux/install_linux_user.sh
```

Install the Debian-family package:

```bash
sudo apt install ./Windslock-Linux-Debian.deb
windslock
```

Uninstall:

```bash
bash packaging/linux/uninstall_linux_user.sh
```

## Verification

Verify Windows checksums:

```powershell
Get-FileHash .\Windslock-Setup.exe -Algorithm SHA256
Get-Content .\Windslock-Windows-SHA256SUMS.txt
```

Verify Linux checksums:

```bash
sha256sum -c Windslock-Linux-SHA256SUMS.txt
```

Verify a Windows signature when signing is configured:

```powershell
Get-AuthenticodeSignature .\Windslock-Setup.exe
```

Verify a Linux detached signature when GPG signing is configured:

```bash
gpg --verify Windslock-Linux-Debian.deb.asc Windslock-Linux-Debian.deb
```

## Runtime Notes

Windows:

- `Windslock.exe` opens the GUI.
- `WindslockTray.exe` starts the tray controller.
- `WindslockProxy.exe` starts mitmproxy for path-level URL blocking.
- `install_startup_task.bat` installs tray startup through Task Scheduler.

Linux:

- `run_windslock.sh` opens the GUI.
- `run_tray.sh` starts the tray controller.
- `run_proxy.sh` starts path-level proxy blocking.
- `install_linux_user.sh` installs launchers and desktop entries for the current user.

## Windows Python DLL Error

If Windows shows an error like:

```text
Failed to load Python DLL
python312.dll
```

the app was probably launched without the PyInstaller `_internal` folder. This
happens when only `Windslock.exe` is copied out of `dist\Windslock`.

Use one of these fixes:

1. Keep and run the full `Windslock-Windows.zip` folder contents together.
2. Run `dist\Windslock\run_windslock.bat`, not a copied standalone EXE.
3. Use the one-file artifact: `Windslock-Windows-OneFile.zip`.

The one-file artifact contains:

```text
Windslock.exe
WindslockTray.exe
WindslockEnforcer.exe
WindslockProxy.exe
```

Those EXEs do not need a visible `_internal` folder.

## Release Hardening Status

Implemented:

- Optional Windows Authenticode signing
- Optional Linux detached GPG signatures
- SHA-256 checksum files
- Automatic latest-main prerelease publishing

Still future work:

- Paid trusted Windows certificate provisioning
- Windows SmartScreen reputation building
- SBOM generation
- Public apt repository signing for Linux package repositories

## Local Test Checks

Before releasing:

```powershell
D:\Windslock\files\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
D:\Windslock\files\.venv\Scripts\python.exe -B -c "import gui, tray_app, proxy_runner; print('imports ok')"
```

Manual checks:

- GUI launches.
- Tray launches.
- Windows EXE opens without console.
- Proxy starts and opens mitmproxy web UI.
- Hosts rollback works.
- Folder lock/unlock works on disposable folder.
