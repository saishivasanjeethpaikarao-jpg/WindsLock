# Code Signing Guide

Windslock release builds support optional signing. The workflow stays safe when
secrets are missing: it still builds releases, but skips signing and publishes
checksums.

## Windows Authenticode Signing

Windows signing requires a trusted code-signing certificate from a certificate
authority. For best SmartScreen reputation over time, use an EV or OV code
signing certificate issued to the publisher.

GitHub repository secrets:

- `WINDOWS_SIGNING_CERT_BASE64`: Base64 text of the `.pfx` certificate.
- `WINDOWS_SIGNING_CERT_PASSWORD`: Password for the `.pfx` certificate.
- `WINDOWS_TIMESTAMP_URL`: Optional timestamp server. Defaults to `http://timestamp.digicert.com`.

Create the base64 value on Windows:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\certificate.pfx")) | Set-Clipboard
```

Then add it in GitHub:

```text
Repository -> Settings -> Secrets and variables -> Actions -> New repository secret
```

What gets signed:

- `dist\Windslock\Windslock.exe`
- `dist\WindslockTray\WindslockTray.exe`
- `dist\WindslockEnforcer\WindslockEnforcer.exe`
- `dist\WindslockProxy\WindslockProxy.exe`
- one-file Windows EXEs
- `Windslock-Setup.exe`

The workflow verifies each signature with `signtool verify` after signing.

## Linux Release Signatures

Linux desktop files are not Authenticode-signed. The workflow supports detached
GPG signatures for release artifacts.

GitHub repository secrets:

- `RELEASE_GPG_PRIVATE_KEY`: ASCII-armored private key.
- `RELEASE_GPG_PASSPHRASE`: Passphrase for the private key. Leave empty only if the key is unprotected.

Export an armored private key:

```bash
gpg --armor --export-secret-keys YOUR_KEY_ID
```

What gets signed:

- `Windslock-Linux.tar.gz`
- `Windslock-Linux-Debian.deb`
- `Windslock-Linux-SHA256SUMS.txt`

The release includes `.asc` detached signatures only when `RELEASE_GPG_PRIVATE_KEY`
is configured.

## Checksums

Every desktop release includes checksum files even when signing is not configured:

- `Windslock-Windows-SHA256SUMS.txt`
- `Windslock-Linux-SHA256SUMS.txt`

Verify on Windows:

```powershell
Get-FileHash .\Windslock-Setup.exe -Algorithm SHA256
```

Verify on Linux:

```bash
sha256sum -c Windslock-Linux-SHA256SUMS.txt
```

## Limits

- Signing does not make Windslock unbypassable. It proves who built the file and
  helps Windows trust the installer over time.
- A new certificate may still trigger SmartScreen warnings until reputation is built.
- Keep `.pfx` files and private GPG keys out of the repository. Store them only
  as GitHub Actions secrets or in a secure local vault.
