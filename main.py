"""CLI entry point for Windslock."""

from __future__ import annotations

import getpass
from pathlib import Path
import sys

import app_blocker
import audit_log
import config as cfg
from database import EncryptedDatabase
import folder_locker
import site_blocker
import startup
import tamper
import runtime_control


def prompt_password(prompt: str = "Password: ") -> str:
    return getpass.getpass(prompt)


def print_recovery_codes(codes: list[str]) -> None:
    print("\nEmergency recovery codes. Store these somewhere safe now.")
    print("Each code can reset your password once; new codes are created after reset.\n")
    for code in codes:
        print(f"  {code}")
    print("")


def first_time_setup() -> None:
    print("No master password set yet. Let's create one.")
    while True:
        pw1 = prompt_password("Set master password (8+ chars): ")
        pw2 = prompt_password("Confirm master password: ")
        if pw1 != pw2:
            print("Passwords do not match.\n")
            continue
        try:
            codes = cfg.set_master_password(pw1)
            print_recovery_codes(codes)
            print("Master password set.\n")
            return
        except ValueError as exc:
            print(f"{exc}\n")


def login() -> str:
    for _ in range(3):
        pw = prompt_password("Master password: ")
        if cfg.verify_password(pw):
            return pw
        print("Wrong password.\n")
    print("Too many failed attempts.")
    if input("Use an emergency recovery code to reset the password? [y/N]: ").strip().lower() == "y":
        code = prompt_password("Recovery code: ")
        new_pw = prompt_password("New master password (8+ chars): ")
        confirm = prompt_password("Confirm new master password: ")
        if new_pw != confirm:
            print("Passwords do not match.")
            sys.exit(1)
        try:
            codes = cfg.reset_password_with_recovery(code, new_pw)
            print_recovery_codes(codes)
            return new_pw
        except Exception as exc:
            print(f"Recovery failed: {exc}")
    sys.exit(1)


def start_background_now() -> None:
    runtime_control.start_enforcer()


def print_rules(password: str) -> None:
    config = EncryptedDatabase(password)._data
    print("\nLocked apps:")
    for rule in config["locked_apps"] or []:
        print(f"  {rule['mode']}: {rule['value']}")
    if not config["locked_apps"]:
        print("  none")

    print("\nBlocked sites:")
    for site in config["blocked_sites"] or []:
        print(f"  {site}")
    if not config["blocked_sites"]:
        print("  none")

    print("\nLocked folders:")
    for folder in config["locked_folders"] or []:
        print(f"  {folder['original_path']} -> {folder['locked_path']}")
    if not config["locked_folders"]:
        print("  none")


def menu(password: str) -> None:
    while True:
        print(
            """
--- Windslock ---
1) Lock a folder
2) Unlock a folder
3) Add app lock by name/path
4) Remove app lock
5) Add website block
6) Remove website block
7) Apply website blocks to hosts file
8) Roll back Windslock hosts entries
9) List rules
10) See currently running app names
11) Run app enforcement in this window
12) Enable background enforcement for this Windows user
13) Disable background enforcement
14) Enable start with Windows
15) Disable start with Windows
16) Harden config folder ACL
17) Show recent blocked-attempt history
18) Change master password
19) Exit
"""
        )
        choice = input("Choose: ").strip()

        try:
            if choice == "1":
                path = input("Folder path to lock: ").strip().strip('"')
                print(f"Locked -> {folder_locker.lock_folder(path, password)}")

            elif choice == "2":
                path = input(".locked file path: ").strip().strip('"')
                print(f"Unlocked -> {folder_locker.unlock_folder(path, password)}")

            elif choice == "3":
                app = input("Process name or full exe path: ").strip()
                app_blocker.add_locked_app(app, password)
                print(f"Locked app rule added: {app}")

            elif choice == "4":
                app = input("Process name or full exe path to remove: ").strip()
                app_blocker.remove_locked_app(app, password)
                print(f"Removed app rule: {app}")

            elif choice == "5":
                domain = input("Domain to block (example.com): ").strip()
                site_blocker.add_blocked_site(domain, password)
                print(f"Blocked site rule added: {domain}")

            elif choice == "6":
                domain = input("Domain to remove: ").strip()
                site_blocker.remove_blocked_site(domain, password)
                print(f"Removed site rule: {domain}")

            elif choice == "7":
                path = site_blocker.apply_hosts_block(password)
                print(f"Applied hosts entries at {path}. This may require an elevated terminal.")

            elif choice == "8":
                path = site_blocker.rollback_hosts_block()
                print(f"Removed only Windslock-managed hosts entries from {path}.")

            elif choice == "9":
                print_rules(password)

            elif choice == "10":
                for name in app_blocker.list_running_processes():
                    print(f"  {name}")

            elif choice == "11":
                app_blocker.start_watching(password)

            elif choice == "12":
                cfg.enable_background_unlock(password)
                start_background_now()
                print("Background enforcement enabled and started for this Windows user.")

            elif choice == "13":
                cfg.disable_background_unlock(password)
                runtime_control.stop_enforcer()
                print("Background enforcement disabled.")

            elif choice == "14":
                startup.enable_startup(password)
                print("Start with Windows enabled.")

            elif choice == "15":
                startup.disable_startup(password)
                print("Start with Windows disabled.")

            elif choice == "16":
                print(tamper.harden_config_acl(password))
                print("Config folder ACL hardened for casual tamper resistance.")

            elif choice == "17":
                for event in audit_log.list_events(password):
                    print(
                        f"{event['timestamp']}  {event['type']}  {event['action']}  "
                        f"{event['target']}  {event.get('detail', '')}"
                    )

            elif choice == "18":
                old = prompt_password("Current password: ")
                new = prompt_password("New password (8+ chars): ")
                confirm = prompt_password("Confirm new password: ")
                if new != confirm:
                    print("Passwords do not match.")
                    continue
                codes = cfg.change_master_password(old, new)
                password = new
                print_recovery_codes(codes)
                print("Password changed.")

            elif choice == "19":
                print("Bye.")
                break

            else:
                print("Invalid choice.")
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    if not cfg.master_password_is_set():
        if cfg.get_legacy_salt_path().exists():
            pw = login()
            codes = cfg.migrate_legacy_store(pw)
            if codes:
                print_recovery_codes(codes)
            menu(pw)
        else:
            first_time_setup()
            menu(login())
    else:
        menu(login())
