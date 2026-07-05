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
- `Windslock-Linux.tar.gz`
- `Windslock-Linux-Debian.deb`

Triggers:

- Push to `main`
- Manual workflow dispatch
- Published GitHub release

On a published release, the workflow uploads the Windows installer, Windows
portable packages, Linux portable package, and Debian-family Linux package to
the release assets.

Recommended downloads:

- Windows: `Windslock-Setup.exe`
- Windows portable fallback: `Windslock-Windows-OneFile.zip`
- Ubuntu, Linux Mint, Kali, Debian: `Windslock-Linux-Debian.deb`
- Other Linux desktops: `Windslock-Linux.tar.gz`

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

## Signing

Current builds are unsigned.

Future release hardening:

- Windows Authenticode signing
- Checksums for release artifacts
- SBOM generation
- Signed GitHub releases

## Verification

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
