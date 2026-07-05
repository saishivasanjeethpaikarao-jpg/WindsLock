"""Windslock desktop UI."""

from __future__ import annotations

import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk

import app_blocker
import audit_log
import brand
import config as cfg
from database import EncryptedDatabase
import focus_manager
import folder_locker
import override_manager
import runtime_control
import site_blocker
import startup
import tamper
import url_rule_engine


APP_TITLE = brand.APP_NAME


class SetupDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Create a master password").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(master, text="Password").grid(row=1, column=0, sticky="w")
        ttk.Label(master, text="Confirm").grid(row=2, column=0, sticky="w")
        self.password = ttk.Entry(master, show="*", width=32)
        self.confirm = ttk.Entry(master, show="*", width=32)
        self.password.grid(row=1, column=1, padx=(8, 0), pady=3)
        self.confirm.grid(row=2, column=1, padx=(8, 0), pady=3)
        return self.password

    def validate(self):
        password = self.password.get()
        if password != self.confirm.get():
            messagebox.showerror(APP_TITLE, "Passwords do not match.", parent=self)
            return False
        if len(password) < 8:
            messagebox.showerror(APP_TITLE, "Use at least 8 characters.", parent=self)
            return False
        self.result = password
        return True


class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Unlock Windslock").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(master, text="Password").grid(row=1, column=0, sticky="w")
        self.password = ttk.Entry(master, show="*", width=32)
        self.password.grid(row=1, column=1, padx=(8, 0), pady=3)
        return self.password

    def buttonbox(self):
        box = ctk.CTkFrame(self)
        ctk.CTkButton(box, text="Unlock", command=self.ok).pack(side="left", padx=4)
        ctk.CTkButton(box, text="Recovery", command=self.recovery).pack(side="left", padx=4)
        ctk.CTkButton(box, text="Cancel", command=self.cancel).pack(side="left", padx=4)
        box.pack(pady=10)

    def validate(self):
        password = self.password.get()
        if cfg.verify_password(password):
            self.result = password
            return True
        messagebox.showerror(APP_TITLE, "Wrong password.", parent=self)
        return False

    def recovery(self):
        code = simpledialog.askstring(APP_TITLE, "Recovery code", show="*", parent=self)
        if not code:
            return
        new_password = simpledialog.askstring(APP_TITLE, "New password", show="*", parent=self)
        confirm = simpledialog.askstring(APP_TITLE, "Confirm new password", show="*", parent=self)
        if not new_password or new_password != confirm:
            messagebox.showerror(APP_TITLE, "Passwords do not match.", parent=self)
            return
        try:
            codes = cfg.reset_password_with_recovery(code, new_password)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Recovery failed:\n{exc}", parent=self)
            return
        RecoveryCodesWindow(self, codes)
        self.result = new_password
        self.destroy()


class RecoveryCodesWindow(tk.Toplevel):
    def __init__(self, parent, codes: list[str]):
        super().__init__(parent)
        self.title("Recovery Codes")
        self.resizable(False, False)
        self.transient(parent)
        ctk.CTkLabel(self, text="Store these recovery codes somewhere safe.").pack(anchor="w", padx=16, pady=(14, 8))
        text = tk.Text(self, width=34, height=9, wrap="none")
        text.pack(padx=16)
        text.insert("1.0", "\n".join(codes))
        text.configure(state="disabled")
        ctk.CTkButton(self, text="I saved them", command=self.destroy).pack(pady=14)
        self.grab_set()


class WindslockApp(ctk.CTk):
    def __init__(self, password: str):
        super().__init__()
        ctk.set_appearance_mode('System')
        ctk.set_default_color_theme('blue')
        self.password = password
        self.title(f"{brand.APP_NAME} - {brand.APP_TAGLINE}")
        self.geometry("980x640")
        self.minsize(860, 560)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_background)
        self._set_window_icon()

        self.status_var = ctk.StringVar()
        self.logo_image = None
        self._build()
        self.refresh_all()
        self.after(5000, self.refresh_status)

    def _build(self):
        root = ctk.CTkFrame(self)
        root.pack(fill="both", expand=True)

        top = ctk.CTkFrame(root)
        top.pack(fill="x", pady=(0, 10))
        if brand.logo_png().exists():
            self.logo_image = tk.PhotoImage(file=str(brand.logo_png())).subsample(4, 4)
            ctk.CTkLabel(top, image=self.logo_image).pack(side="left", padx=(0, 12))
        title_block = ctk.CTkFrame(top)
        title_block.pack(side="left")
        ctk.CTkLabel(title_block, text=brand.APP_NAME, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_block, text=brand.APP_TAGLINE, text_color="#334155").pack(anchor="w")
        ctk.CTkLabel(top, textvariable=self.status_var).pack(side="right")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self._build_dashboard()
        self._build_focus()
        self._build_apps()
        self._build_sites()
        self._build_folders()
        self._build_overrides()
        self._build_history()
        self._build_settings()

    def _tab(self, name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(frame, text=name)
        return frame

    def _set_window_icon(self):
        try:
            if brand.icon_ico().exists():
                self.iconbitmap(str(brand.icon_ico()))
        except Exception:
            pass

    def _build_dashboard(self):
        tab = self._tab("Dashboard")
        self.summary = tk.Text(tab, height=16, wrap="word")
        self.summary.pack(fill="both", expand=True)
        actions = ctk.CTkFrame(tab)
        actions.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(actions, text="Start background", command=self.enable_background).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Stop background", command=self.disable_background).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Refresh", command=self.refresh_all).pack(side="left")

    def _build_focus(self):
        tab = self._tab("Focus")

        presets = ctk.CTkFrame(tab)
        presets.pack(fill="x")
        self.preset_choice = ttk.Combobox(presets, values=tuple(focus_manager.PRESETS.keys()), state="readonly")
        self.preset_choice.set("Deep Work")
        self.preset_choice.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(presets, text="Apply preset", command=self.apply_preset).pack(side="left")

        session = ctk.CTkFrame(tab)
        session.pack(fill="x", pady=(12, 0))
        self.focus_minutes = ttk.Spinbox(session, from_=1, to=480, width=8)
        self.focus_minutes.set("90")
        self.focus_minutes.pack(side="left", padx=(0, 8))
        ctk.CTkButton(session, text="Start session", command=self.start_focus_session).pack(side="left", padx=(0, 8))
        ctk.CTkButton(session, text="Stop session", command=self.stop_focus_session).pack(side="left")

        schedule_mode = ctk.CTkFrame(tab)
        schedule_mode.pack(fill="x", pady=(12, 0))
        self.schedule_only_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            schedule_mode,
            text="Only enforce during focus sessions or schedules",
            variable=self.schedule_only_var,
            command=self.save_schedule_only_mode,
        ).pack(anchor="w")

        form = ctk.CTkFrame(tab)
        form.pack(fill="x", pady=(12, 0))
        self.schedule_name = ctk.CTkEntry(form, width=180)
        self.schedule_name.insert(0, "Work")
        self.schedule_name.grid(row=0, column=0, padx=(0, 8))
        self.schedule_start = ctk.CTkEntry(form, width=80)
        self.schedule_start.insert(0, "09:00")
        self.schedule_start.grid(row=0, column=1, padx=(0, 8))
        self.schedule_end = ctk.CTkEntry(form, width=80)
        self.schedule_end.insert(0, "17:00")
        self.schedule_end.grid(row=0, column=2, padx=(0, 8))
        self.day_vars = []
        days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        days_frame = ctk.CTkFrame(form)
        days_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        for index, label in enumerate(days):
            var = ctk.BooleanVar(value=index < 5)
            self.day_vars.append(var)
            ctk.CTkCheckBox(days_frame, text=label, variable=var).pack(side="left", padx=(0, 6))
        ctk.CTkButton(form, text="Add schedule", command=self.add_schedule).grid(row=0, column=3)

        self.schedule_tree = ttk.Treeview(tab, columns=("name", "days", "start", "end"), show="headings", height=7)
        for name, width in (("name", 160), ("days", 260), ("start", 90), ("end", 90)):
            self.schedule_tree.heading(name, text=name.title())
            self.schedule_tree.column(name, width=width)
        self.schedule_tree.pack(fill="both", expand=True, pady=12)
        ctk.CTkButton(tab, text="Remove selected schedule", command=self.remove_schedule).pack(anchor="e")

    def _build_apps(self):
        tab = self._tab("Apps")
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        self.app_entry = ctk.CTkEntry(form)
        self.app_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(form, text="Browse", command=self.pick_app).pack(side="left", padx=(0, 8))
        ctk.CTkButton(form, text="Running apps", command=self.choose_running_app).pack(side="left", padx=(0, 8))
        ctk.CTkButton(form, text="Add", command=self.add_app).pack(side="left")

        self.apps_tree = ttk.Treeview(tab, columns=("mode", "value"), show="headings", height=14)
        self.apps_tree.heading("mode", text="Mode")
        self.apps_tree.heading("value", text="Name or path")
        self.apps_tree.column("mode", width=90, stretch=False)
        self.apps_tree.pack(fill="both", expand=True, pady=10)
        ctk.CTkButton(tab, text="Remove selected", command=self.remove_app).pack(anchor="e")

    def _build_sites(self):
        tab = self._tab("Websites")
        ctk.CTkLabel(tab, text="Whole-domain blocks use the Windows hosts file.").pack(anchor="w")
        form = ctk.CTkFrame(tab)
        form.pack(fill="x", pady=(6, 0))
        self.site_entry = ctk.CTkEntry(form)
        self.site_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(form, text="Add domain", command=self.add_site).pack(side="left")

        self.sites_list = tk.Listbox(tab, height=14)
        self.sites_list.pack(fill="both", expand=True, pady=10)
        buttons = ctk.CTkFrame(tab)
        buttons.pack(fill="x")
        ctk.CTkButton(buttons, text="Remove selected", command=self.remove_site).pack(side="left")
        ctk.CTkButton(buttons, text="Apply hosts block", command=self.apply_hosts).pack(side="right")
        ctk.CTkButton(buttons, text="Rollback hosts entries", command=self.rollback_hosts).pack(side="right", padx=(0, 8))

        ttk.Separator(tab).pack(fill="x", pady=12)
        ctk.CTkLabel(tab, text="Path-level blocks require the local mitmproxy addon.").pack(anchor="w")
        path_form = ctk.CTkFrame(tab)
        path_form.pack(fill="x", pady=(6, 0))
        self.path_domain_entry = ctk.CTkEntry(path_form, width=280)
        self.path_domain_entry.pack(side="left", padx=(0, 8))
        self.path_domain_entry.insert(0, "youtube.com")
        self.path_prefix_entry = ctk.CTkEntry(path_form, width=240)
        self.path_prefix_entry.pack(side="left", padx=(0, 8))
        self.path_prefix_entry.insert(0, "/shorts")
        ctk.CTkButton(path_form, text="Add path rule", command=self.add_path_rule).pack(side="left")

        self.path_tree = ttk.Treeview(tab, columns=("domain", "path"), show="headings", height=6)
        self.path_tree.heading("domain", text="Domain")
        self.path_tree.heading("path", text="Blocked path")
        self.path_tree.pack(fill="both", expand=True, pady=10)
        path_buttons = ctk.CTkFrame(tab)
        path_buttons.pack(fill="x")
        ctk.CTkButton(path_buttons, text="Remove selected path", command=self.remove_path_rule).pack(side="left")

    def _build_folders(self):
        tab = self._tab("Folders")
        buttons = ctk.CTkFrame(tab)
        buttons.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(buttons, text="Lock folder", command=self.lock_folder).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Unlock .locked file", command=self.unlock_folder).pack(side="left")
        self.folders_tree = ttk.Treeview(tab, columns=("original", "locked"), show="headings", height=14)
        self.folders_tree.heading("original", text="Original folder")
        self.folders_tree.heading("locked", text="Locked file")
        self.folders_tree.pack(fill="both", expand=True)

    def _build_overrides(self):
        tab = self._tab("Overrides")
        settings = ctk.CTkFrame(tab)
        settings.pack(fill="x")
        ctk.CTkLabel(settings).grid(row=0, column=0, sticky="w")
        self.override_phrase = ctk.CTkEntry(settings)
        self.override_phrase.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)
        ctk.CTkLabel(settings, text="Cooldown minutes").grid(row=1, column=0, sticky="w")
        self.override_cooldown = ttk.Spinbox(settings, from_=0, to=240, width=8)
        self.override_cooldown.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=3)
        ctk.CTkLabel(settings, text="Unlock window minutes").grid(row=2, column=0, sticky="w")
        self.override_window = ttk.Spinbox(settings, from_=1, to=240, width=8)
        self.override_window.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=3)
        settings.columnconfigure(1, weight=1)
        ctk.CTkButton(settings, text="Save override settings", command=self.save_override_settings).grid(row=3, column=1, sticky="e", pady=(8, 0))

        request = ctk.CTkFrame(tab)
        request.pack(fill="x", pady=(12, 0))
        self.override_type = ttk.Combobox(request, values=("app", "site", "url_path", "folder"), state="readonly", width=12)
        self.override_type.set("app")
        self.override_type.grid(row=0, column=0, padx=(0, 8))
        self.override_target = ctk.CTkEntry(request)
        self.override_target.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.override_phrase_attempt = ctk.CTkEntry(request)
        self.override_phrase_attempt.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        ctk.CTkButton(request, text="Request", command=self.request_override).grid(row=0, column=3)
        request.columnconfigure(1, weight=1)
        request.columnconfigure(2, weight=1)

        self.override_tree = ttk.Treeview(tab, columns=("status", "type", "target", "requested", "ready", "expires"), show="headings")
        for name, width in (("status", 90), ("type", 80), ("target", 260), ("requested", 155), ("ready", 155), ("expires", 155)):
            self.override_tree.heading(name, text=name.title())
            self.override_tree.column(name, width=width)
        self.override_tree.pack(fill="both", expand=True, pady=12)
        ctk.CTkButton(tab, text="Refresh", command=self.refresh_overrides).pack(anchor="e")

    def _build_history(self):
        tab = self._tab("History")
        self.history_tree = ttk.Treeview(tab, columns=("time", "type", "action", "target", "detail"), show="headings")
        for name, width in (("time", 165), ("type", 90), ("action", 110), ("target", 280), ("detail", 220)):
            self.history_tree.heading(name, text=name.title())
            self.history_tree.column(name, width=width)
        self.history_tree.pack(fill="both", expand=True)
        ctk.CTkButton(tab, text="Refresh", command=self.refresh_history).pack(anchor="e", pady=(10, 0))

    def _build_settings(self):
        tab = self._tab("Settings")
        ctk.CTkButton(tab, text="Enable start with Windows", command=self.enable_startup).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Disable start with Windows", command=self.disable_startup).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Install pro startup task", command=self.install_startup_task).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Remove pro startup task", command=self.remove_startup_task).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Harden config folder ACL", command=self.harden_acl).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Change master password", command=self.change_password).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Show app data folder", command=self.show_appdata).pack(anchor="w", pady=4)
        ctk.CTkButton(tab, text="Exit app", command=self.destroy).pack(anchor="w", pady=(18, 4))

    def refresh_all(self):
        self.refresh_status()
        self.refresh_focus()
        self.refresh_apps()
        self.refresh_sites()
        self.refresh_folders()
        self.refresh_overrides()
        self.refresh_history()
        self.refresh_summary()

    def refresh_status(self):
        running = runtime_control.is_enforcer_running()
        config = self._load()
        self.status_var.set(
            f"Background: {'running' if running else 'stopped'} | "
            f"Startup: {'on' if config['settings'].get('run_on_startup') else 'off'} | "
            f"Hosts: {'applied' if config['settings'].get('website_hosts_applied') else 'not applied'}"
        )
        self.after(5000, self.refresh_status)

    def refresh_summary(self):
        config = self._load()
        lines = [
            "Status",
            f"  Background enforcement: {'running' if runtime_control.is_enforcer_running() else 'stopped'}",
            f"  Start with Windows: {'enabled' if config['settings'].get('run_on_startup') else 'disabled'}",
            f"  Website hosts block: {'applied' if config['settings'].get('website_hosts_applied') else 'not applied'}",
            f"  Schedule-only mode: {'enabled' if config['settings'].get('schedule_only_mode') else 'disabled'}",
            f"  Focus session until: {config['settings'].get('focus_session_until') or 'not active'}",
            "",
            "Rules",
            f"  App locks: {len(config['locked_apps'])}",
            f"  Website blocks: {len(config['blocked_sites'])}",
            f"  Path-level web blocks: {len(config['blocked_url_paths'])}",
            f"  Locked folders: {len(config['locked_folders'])}",
            f"  Override requests: {len(config['override_requests'])}",
            f"  Focus schedules: {len(config['focus_schedules'])}",
            "",
            "Security note",
            "  Windslock protects against casual use and accidental bypass.",
            "  A Windows administrator can still stop or modify user-level enforcement.",
        ]
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", "\n".join(lines))
        self.summary.configure(state="disabled")

    def refresh_apps(self):
        self.apps_tree.delete(*self.apps_tree.get_children())
        for rule in app_blocker.list_locked_apps(self.password):
            self.apps_tree.insert("", "end", values=(rule["mode"], rule["value"]))

    def refresh_focus(self):
        config = self._load()
        self.schedule_only_var.set(bool(config["settings"].get("schedule_only_mode", False)))
        self.schedule_tree.delete(*self.schedule_tree.get_children())
        for index, schedule in enumerate(config.get("focus_schedules", [])):
            days = ", ".join(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[day] for day in schedule["days"])
            self.schedule_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(schedule["name"], days, schedule["start"], schedule["end"]),
            )

    def refresh_sites(self):
        self.sites_list.delete(0, "end")
        for site in site_blocker.list_blocked_sites(self.password):
            self.sites_list.insert("end", site)
        self.path_tree.delete(*self.path_tree.get_children())
        for rule in url_rule_engine.list_path_rules(self.password):
            self.path_tree.insert("", "end", values=(rule["domain"], rule["path_prefix"]))

    def refresh_folders(self):
        self.folders_tree.delete(*self.folders_tree.get_children())
        for folder in self._load()["locked_folders"]:
            self.folders_tree.insert("", "end", values=(folder["original_path"], folder["locked_path"]))

    def refresh_overrides(self):
        config = self._load()
        settings = config["settings"]
        self.override_phrase.delete(0, "end")
        self.override_phrase.insert(0, settings.get("override_phrase", ""))
        self.override_cooldown.delete(0, "end")
        self.override_cooldown.insert(0, str(settings.get("override_cooldown_minutes", 5)))
        self.override_window.delete(0, "end")
        self.override_window.insert(0, str(settings.get("override_window_minutes", 10)))
        self.override_tree.delete(*self.override_tree.get_children())
        for item in override_manager.list_overrides(self.password)[-200:]:
            self.override_tree.insert(
                "",
                "end",
                values=(
                    item.get("status", ""),
                    item.get("target_type", ""),
                    item.get("target", ""),
                    item.get("requested_at", ""),
                    item.get("ready_at", ""),
                    item.get("expires_at", ""),
                ),
            )

    def refresh_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for event in audit_log.list_events(self.password, limit=200):
            self.history_tree.insert(
                "",
                "end",
                values=(
                    event.get("timestamp", ""),
                    event.get("type", ""),
                    event.get("action", ""),
                    event.get("target", ""),
                    event.get("detail", ""),
                ),
            )

    def _load(self):
        return EncryptedDatabase(self.password)._data

    def _run(self, title: str, fn, refresh=True):
        try:
            result = fn()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"{title} failed:\n{exc}", parent=self)
            return None
        if refresh:
            self.refresh_all()
        return result

    def pick_app(self):
        path = filedialog.askopenfilename(title="Choose executable", filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.app_entry.delete(0, "end")
            self.app_entry.insert(0, path)

    def choose_running_app(self):
        try:
            names = app_blocker.list_running_processes()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not list running apps:\n{exc}", parent=self)
            return
        picker = tk.Toplevel(self)
        picker.title("Running Apps")
        picker.geometry("360x420")
        listbox = tk.Listbox(picker)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for name in names:
            listbox.insert("end", name)

        def use_selected():
            selection = listbox.curselection()
            if selection:
                self.app_entry.delete(0, "end")
                self.app_entry.insert(0, listbox.get(selection[0]))
                picker.destroy()

        ctk.CTkButton(picker, text="Use selected", command=use_selected).pack(pady=(0, 10))

    def add_app(self):
        value = self.app_entry.get().strip()
        if value:
            self._run("Add app", lambda: app_blocker.add_locked_app(value, self.password))
            self.app_entry.delete(0, "end")

    def remove_app(self):
        item = self.apps_tree.focus()
        if not item:
            return
        _, value = self.apps_tree.item(item, "values")
        self._run("Remove app", lambda: app_blocker.remove_locked_app(value, self.password))

    def add_site(self):
        value = self.site_entry.get().strip()
        if value:
            self._run("Add site", lambda: site_blocker.add_blocked_site(value, self.password))
            self.site_entry.delete(0, "end")

    def remove_site(self):
        selection = self.sites_list.curselection()
        if selection:
            value = self.sites_list.get(selection[0])
            self._run("Remove site", lambda: site_blocker.remove_blocked_site(value, self.password))

    def add_path_rule(self):
        domain = self.path_domain_entry.get().strip()
        path_prefix = self.path_prefix_entry.get().strip()
        if domain and path_prefix:
            self._run("Add path rule", lambda: url_rule_engine.add_path_rule(domain, path_prefix, self.password))

    def remove_path_rule(self):
        item = self.path_tree.focus()
        if not item:
            return
        domain, path_prefix = self.path_tree.item(item, "values")
        self._run("Remove path rule", lambda: url_rule_engine.remove_path_rule(domain, path_prefix, self.password))

    def apply_hosts(self):
        self._run("Apply hosts block", lambda: site_blocker.apply_hosts_block(self.password))

    def rollback_hosts(self):
        self._run("Rollback hosts block", lambda: site_blocker.rollback_hosts_block())

    def lock_folder(self):
        path = filedialog.askdirectory(title="Choose folder to lock")
        if not path:
            return
        if not messagebox.askyesno(APP_TITLE, "Lock this folder into an encrypted .locked file?", parent=self):
            return
        self._run_async("Lock folder", lambda: folder_locker.lock_folder(path, self.password))

    def unlock_folder(self):
        path = filedialog.askopenfilename(title="Choose .locked file", filetypes=[("Locked folders", "*.locked"), ("All files", "*.*")])
        if path:
            self._run_async("Unlock folder", lambda: folder_locker.unlock_folder(path, self.password))

    def _run_async(self, title: str, fn):
        self.status_var.set(f"{title}...")

        def worker():
            try:
                result = fn()
                self.after(0, lambda: self._async_done(title, result))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror(APP_TITLE, f"{title} failed:\n{exc}", parent=self))
                self.after(0, self.refresh_all)

        threading.Thread(target=worker, daemon=True).start()

    def _async_done(self, title: str, result):
        messagebox.showinfo(APP_TITLE, f"{title} complete:\n{result}", parent=self)
        self.refresh_all()

    def enable_background(self):
        self._run("Enable background", lambda: (cfg.enable_background_unlock(self.password), runtime_control.start_enforcer()))

    def disable_background(self):
        self._run("Disable background", lambda: (cfg.disable_background_unlock(self.password), runtime_control.stop_enforcer()))

    def enable_startup(self):
        self._run("Enable startup", lambda: startup.enable_startup(self.password))

    def disable_startup(self):
        self._run("Disable startup", lambda: startup.disable_startup(self.password))

    def install_startup_task(self):
        self._run("Install startup task", lambda: startup.install_scheduled_task(self.password, launch_tray=True))

    def remove_startup_task(self):
        self._run("Remove startup task", lambda: startup.uninstall_scheduled_task(self.password))

    def harden_acl(self):
        self._run("Harden ACL", lambda: tamper.harden_config_acl(self.password))

    def apply_preset(self):
        name = self.preset_choice.get()
        if messagebox.askyesno(APP_TITLE, f"Apply the {name} preset rules?", parent=self):
            self._run("Apply preset", lambda: focus_manager.apply_preset(self.password, name))

    def start_focus_session(self):
        self._run("Start focus session", lambda: focus_manager.start_focus_session(self.password, int(self.focus_minutes.get())))

    def stop_focus_session(self):
        self._run("Stop focus session", lambda: focus_manager.stop_focus_session(self.password))

    def save_schedule_only_mode(self):
        self._run(
            "Save schedule-only mode",
            lambda: focus_manager.set_schedule_only_mode(self.password, self.schedule_only_var.get()),
        )

    def add_schedule(self):
        days = [index for index, var in enumerate(self.day_vars) if var.get()]
        self._run(
            "Add schedule",
            lambda: focus_manager.add_schedule(
                self.password,
                self.schedule_name.get(),
                days,
                self.schedule_start.get(),
                self.schedule_end.get(),
            ),
        )

    def remove_schedule(self):
        item = self.schedule_tree.focus()
        if item:
            self._run("Remove schedule", lambda: focus_manager.remove_schedule(self.password, int(item)))

    def save_override_settings(self):
        self._run(
            "Save override settings",
            lambda: override_manager.update_settings(
                self.password,
                self.override_phrase.get(),
                int(self.override_cooldown.get()),
                int(self.override_window.get()),
            ),
        )

    def request_override(self):
        target_type = self.override_type.get()
        target = self.override_target.get().strip()
        phrase = self.override_phrase_attempt.get()
        if target:
            result = self._run(
                "Request override",
                lambda: override_manager.request_override(self.password, target_type, target, phrase),
            )
            if result:
                messagebox.showinfo(APP_TITLE, f"Override status: {result['status']}", parent=self)

    def change_password(self):
        old = simpledialog.askstring(APP_TITLE, "Current password", show="*", parent=self)
        if not old:
            return
        new = simpledialog.askstring(APP_TITLE, "New password", show="*", parent=self)
        confirm = simpledialog.askstring(APP_TITLE, "Confirm new password", show="*", parent=self)
        if not new or new != confirm:
            messagebox.showerror(APP_TITLE, "Passwords do not match.", parent=self)
            return
        codes = self._run("Change password", lambda: cfg.change_master_password(old, new), refresh=False)
        if codes:
            self.password = new
            RecoveryCodesWindow(self, codes)
            self.refresh_all()

    def show_appdata(self):
        messagebox.showinfo(APP_TITLE, str(cfg.get_app_dir()), parent=self)

    def hide_to_background(self):
        self.destroy()


def open_app() -> None:
    root = ctk.CTk()
    root.withdraw()
    if not cfg.master_password_is_set():
        dialog = SetupDialog(root)
        if not dialog.result:
            root.destroy()
            return
        try:
            codes = cfg.set_master_password(dialog.result)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Setup failed:\n{exc}", parent=root)
            root.destroy()
            return
        RecoveryCodesWindow(root, codes).wait_window()

    dialog = LoginDialog(root)
    if not dialog.result:
        root.destroy()
        return
    root.destroy()
    app = WindslockApp(dialog.result)
    app.mainloop()


if __name__ == "__main__":
    open_app()
