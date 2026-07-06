"""Windslock desktop UI."""

from __future__ import annotations

import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from PIL import Image

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
WINDOW_BG = ("#F5F7FA", "#0B1120")
PANEL_BG = ("#FFFFFF", "#111827")
PANEL_ALT = ("#EEF2F7", "#1F2937")
BORDER = ("#D8DEE9", "#243244")
TEXT_MUTED = ("#475569", "#94A3B8")
TEXT_MAIN = ("#0F172A", "#E5E7EB")
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
SUCCESS = "#16A34A"
DANGER = "#DC2626"
WARNING = "#D97706"


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
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_background)
        self._set_window_icon()
        self._install_styles()

        self.status_var = ctk.StringVar()
        self.app_lock_status_var = ctk.StringVar()
        self.site_lock_status_var = ctk.StringVar()
        self.background_metric_var = ctk.StringVar()
        self.startup_metric_var = ctk.StringVar()
        self.hosts_metric_var = ctk.StringVar()
        self.rules_metric_var = ctk.StringVar()
        self._status_after_id = None
        self.logo_image = None
        self._build()
        self.refresh_all()

    def _build(self):
        root = ctk.CTkFrame(self, fg_color=WINDOW_BG, corner_radius=0)
        root.pack(fill="both", expand=True, padx=18, pady=18)

        top = ctk.CTkFrame(root, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=14)
        top.pack(fill="x", pady=(0, 14))
        if brand.logo_png().exists():
            self.logo_image = ctk.CTkImage(Image.open(brand.logo_png()), size=(48, 48))
            ctk.CTkLabel(top, image=self.logo_image, text="").pack(side="left", padx=(16, 12), pady=14)
        title_block = ctk.CTkFrame(top, fg_color="transparent")
        title_block.pack(side="left", pady=14)
        ctk.CTkLabel(title_block, text=brand.APP_NAME, font=("Segoe UI", 24, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_block, text=brand.APP_TAGLINE, text_color=TEXT_MUTED).pack(anchor="w")
        status_pill = ctk.CTkFrame(top, fg_color=PANEL_ALT, corner_radius=999)
        status_pill.pack(side="right", padx=16, pady=18)
        ctk.CTkLabel(status_pill, textvariable=self.status_var, text_color=TEXT_MAIN).pack(padx=14, pady=7)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self._build_home()
        self._build_focus()
        self._build_apps()
        self._build_sites()
        self._build_folders()
        self._build_overrides()
        self._build_history()
        self._build_settings()

    def _tab(self, name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.notebook, fg_color=WINDOW_BG, corner_radius=0)
        self.notebook.add(frame, text=name)
        return frame

    def _set_window_icon(self):
        try:
            if brand.icon_ico().exists():
                self.iconbitmap(str(brand.icon_ico()))
        except Exception:
            pass

    def _install_styles(self):
        self.configure(fg_color=WINDOW_BG)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background="#F5F7FA", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
            background="#E2E8F0",
            foreground="#334155",
        )
        style.map("TNotebook.Tab", background=[("selected", "#FFFFFF")], foreground=[("selected", "#0F172A")])
        style.configure(
            "Treeview",
            rowheight=30,
            borderwidth=0,
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#0F172A",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            padding=(8, 8),
            background="#E2E8F0",
            foreground="#0F172A",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#0F172A")])

    def _button(self, parent, text: str, command, variant: str = "primary", width: int | None = None):
        colors = {
            "primary": (ACCENT, ACCENT_HOVER, "#FFFFFF"),
            "success": (SUCCESS, "#15803D", "#FFFFFF"),
            "danger": (DANGER, "#B91C1C", "#FFFFFF"),
            "muted": ("#E2E8F0", "#CBD5E1", "#0F172A"),
        }
        fg, hover, text_color = colors.get(variant, colors["primary"])
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width or 140,
            height=36,
            corner_radius=8,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            font=("Segoe UI", 10, "bold"),
        )

    def _card(self, parent, **pack_options):
        frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        frame.pack(**pack_options)
        return frame

    def _metric_card(self, parent, title: str, variable: ctk.StringVar, accent: str):
        card = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        ctk.CTkFrame(card, width=4, fg_color=accent, corner_radius=999).pack(side="left", fill="y", padx=(0, 10))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=12)
        ctk.CTkLabel(body, text=title, text_color=TEXT_MUTED, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ctk.CTkLabel(body, textvariable=variable, text_color=TEXT_MAIN, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(4, 0))
        return card

    def _build_home(self):
        tab = self._tab("Home")
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(header, text="Protection Center", font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self._button(header, "Refresh", self.refresh_all, "muted", width=110).pack(side="right")

        metrics = ctk.CTkFrame(tab, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 12))
        for column in range(4):
            metrics.columnconfigure(column, weight=1, uniform="metrics")
        cards = (
            self._metric_card(metrics, "Protection", self.background_metric_var, SUCCESS),
            self._metric_card(metrics, "Starts With PC", self.startup_metric_var, ACCENT),
            self._metric_card(metrics, "Web Blocking", self.hosts_metric_var, WARNING),
            self._metric_card(metrics, "Locks Added", self.rules_metric_var, "#7C3AED"),
        )
        for column, card in enumerate(cards):
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0 if column == 3 else 6))

        summary_card = self._card(tab, fill="both", expand=True)
        ctk.CTkLabel(summary_card, text="What is active", font=("Segoe UI", 15, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=14, pady=(12, 6))
        self.summary = tk.Text(
            summary_card,
            height=16,
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            font=("Cascadia Mono", 10),
        )
        self.summary.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.pack(fill="x", pady=(12, 0))
        self._button(actions, "Turn protection on", self.enable_background, "success").pack(side="left", padx=(0, 8))
        self._button(actions, "Turn protection off", self.disable_background, "danger").pack(side="left", padx=(0, 8))
        self._button(actions, "Open app data", self.show_appdata, "muted").pack(side="left")

    def _build_focus(self):
        tab = self._tab("Focus Time")

        presets = self._card(tab, fill="x", pady=(4, 0))
        self.preset_choice = ttk.Combobox(presets, values=tuple(focus_manager.PRESETS.keys()), state="readonly")
        self.preset_choice.set("Deep Work")
        self.preset_choice.pack(side="left", fill="x", expand=True, padx=12, pady=12)
        self._button(presets, "Apply preset", self.apply_preset).pack(side="left", padx=(0, 12), pady=12)

        session = self._card(tab, fill="x", pady=(12, 0))
        self.focus_minutes = ttk.Spinbox(session, from_=1, to=480, width=8)
        self.focus_minutes.set("90")
        ctk.CTkLabel(session, text="Minutes", text_color=TEXT_MUTED).pack(side="left", padx=(12, 8), pady=12)
        self.focus_minutes.pack(side="left", padx=(0, 8))
        self._button(session, "Start session", self.start_focus_session, "success").pack(side="left", padx=(0, 8), pady=12)
        self._button(session, "Stop session", self.stop_focus_session, "danger").pack(side="left", pady=12)

        schedule_mode = ctk.CTkFrame(tab, fg_color="transparent")
        schedule_mode.pack(fill="x", pady=(12, 0))
        self.schedule_only_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            schedule_mode,
            text="Only block during focus time or schedules",
            variable=self.schedule_only_var,
            command=self.save_schedule_only_mode,
        ).pack(anchor="w")

        form = self._card(tab, fill="x", pady=(12, 0))
        self.schedule_name = ctk.CTkEntry(form, width=180, height=34)
        self.schedule_name.insert(0, "Work")
        self.schedule_name.grid(row=0, column=0, padx=(12, 8), pady=(12, 0))
        self.schedule_start = ctk.CTkEntry(form, width=80, height=34)
        self.schedule_start.insert(0, "09:00")
        self.schedule_start.grid(row=0, column=1, padx=(0, 8), pady=(12, 0))
        self.schedule_end = ctk.CTkEntry(form, width=80, height=34)
        self.schedule_end.insert(0, "17:00")
        self.schedule_end.grid(row=0, column=2, padx=(0, 8), pady=(12, 0))
        self.day_vars = []
        days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        days_frame = ctk.CTkFrame(form, fg_color="transparent")
        days_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 12))
        for index, label in enumerate(days):
            var = ctk.BooleanVar(value=index < 5)
            self.day_vars.append(var)
            ctk.CTkCheckBox(days_frame, text=label, variable=var).pack(side="left", padx=(0, 6))
        self._button(form, "Add schedule", self.add_schedule, width=130).grid(row=0, column=3, padx=(0, 12), pady=(12, 0))

        self.schedule_tree = ttk.Treeview(tab, columns=("name", "days", "start", "end"), show="headings", height=7)
        for name, width in (("name", 160), ("days", 260), ("start", 90), ("end", 90)):
            self.schedule_tree.heading(name, text=name.title())
            self.schedule_tree.column(name, width=width)
        self.schedule_tree.pack(fill="both", expand=True, pady=12)
        self._button(tab, "Remove selected schedule", self.remove_schedule, "danger", width=190).pack(anchor="e")

    def _build_apps(self):
        tab = self._tab("Lock Apps")
        status = ctk.CTkFrame(tab, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        status.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(status, textvariable=self.app_lock_status_var, anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=10)
        self._button(status, "Turn on", self.enable_background, "success").pack(side="right", padx=12, pady=10)

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x")
        self.app_entry = ctk.CTkEntry(form, height=36, placeholder_text="Example: chrome.exe or choose Browse")
        self.app_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._button(form, "Browse", self.pick_app, "muted", width=100).pack(side="left", padx=(0, 8))
        self._button(form, "Running apps", self.choose_running_app, "muted", width=130).pack(side="left", padx=(0, 8))
        self._button(form, "Add lock", self.add_app, "primary", width=110).pack(side="left")

        self.apps_tree = ttk.Treeview(tab, columns=("mode", "value"), show="headings", height=14)
        self.apps_tree.heading("mode", text="Mode")
        self.apps_tree.heading("value", text="Name or path")
        self.apps_tree.column("mode", width=90, stretch=False)
        self.apps_tree.pack(fill="both", expand=True, pady=10)
        app_buttons = ctk.CTkFrame(tab, fg_color="transparent")
        app_buttons.pack(fill="x")
        self._button(app_buttons, "Test selected", self.test_selected_app_rule, "muted", width=130).pack(side="left")
        self._button(app_buttons, "Unlock for a while", self.password_unlock_selected_app, "primary", width=150).pack(side="left", padx=(8, 0))
        self._button(app_buttons, "Remove selected", self.remove_app, "danger", width=150).pack(side="right")

        options = ctk.CTkFrame(tab, fg_color="transparent")
        options.pack(fill="x", pady=(8, 0))
        self.strict_app_lock_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options,
            text="Close locked apps immediately",
            variable=self.strict_app_lock_var,
            command=self.save_strict_app_lock,
        ).pack(anchor="w")

    def _build_sites(self):
        tab = self._tab("Block Websites")
        status = ctk.CTkFrame(tab, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        status.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(status, textvariable=self.site_lock_status_var, anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=10)
        self._button(status, "Check", self.check_website_block, "muted", width=100).pack(side="right", padx=(0, 12), pady=10)
        ctk.CTkLabel(tab, text="Block a whole website", font=("Segoe UI", 14, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", pady=(6, 0))
        self.site_entry = ctk.CTkEntry(form, height=36, placeholder_text="example.com")
        self.site_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._button(form, "Add domain", self.add_site, width=120).pack(side="left")

        self.sites_list = tk.Listbox(
            tab,
            height=14,
            bd=0,
            highlightthickness=1,
            highlightbackground="#D8DEE9",
            activestyle="none",
            font=("Segoe UI", 10),
            selectbackground="#DBEAFE",
            selectforeground="#0F172A",
        )
        self.sites_list.pack(fill="both", expand=True, pady=10)
        buttons = ctk.CTkFrame(tab, fg_color="transparent")
        buttons.pack(fill="x")
        self._button(buttons, "Remove selected", self.remove_site, "danger", width=150).pack(side="left")
        self._button(buttons, "Turn web blocking on", self.apply_hosts, "success", width=160).pack(side="right")
        self._button(buttons, "Turn web blocking off", self.rollback_hosts, "muted", width=140).pack(side="right", padx=(0, 8))

        ttk.Separator(tab).pack(fill="x", pady=12)
        ctk.CTkLabel(tab, text="Block only part of a website (advanced)", font=("Segoe UI", 14, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        path_form = ctk.CTkFrame(tab, fg_color="transparent")
        path_form.pack(fill="x", pady=(6, 0))
        self.path_domain_entry = ctk.CTkEntry(path_form, width=280, height=36)
        self.path_domain_entry.pack(side="left", padx=(0, 8))
        self.path_domain_entry.insert(0, "youtube.com")
        self.path_prefix_entry = ctk.CTkEntry(path_form, width=240, height=36)
        self.path_prefix_entry.pack(side="left", padx=(0, 8))
        self.path_prefix_entry.insert(0, "/shorts")
        self._button(path_form, "Add path rule", self.add_path_rule, width=130).pack(side="left")

        self.path_tree = ttk.Treeview(tab, columns=("domain", "path"), show="headings", height=6)
        self.path_tree.heading("domain", text="Domain")
        self.path_tree.heading("path", text="Blocked path")
        self.path_tree.pack(fill="both", expand=True, pady=10)
        path_buttons = ctk.CTkFrame(tab, fg_color="transparent")
        path_buttons.pack(fill="x")
        self._button(path_buttons, "Remove selected path", self.remove_path_rule, "danger", width=180).pack(side="left")

    def _build_folders(self):
        tab = self._tab("Lock Folders")
        buttons = ctk.CTkFrame(tab, fg_color="transparent")
        buttons.pack(fill="x", pady=(0, 10))
        self._button(buttons, "Lock folder", self.lock_folder, "primary", width=130).pack(side="left", padx=(0, 8))
        self._button(buttons, "Unlock file", self.unlock_folder, "success", width=130).pack(side="left")
        self.folders_tree = ttk.Treeview(tab, columns=("original", "locked"), show="headings", height=14)
        self.folders_tree.heading("original", text="Original folder")
        self.folders_tree.heading("locked", text="Locked file")
        self.folders_tree.pack(fill="both", expand=True)

    def _build_overrides(self):
        tab = self._tab("Temporary Unlock")
        settings = self._card(tab, fill="x")
        ctk.CTkLabel(settings, text="Unlock phrase", text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=(12, 0), pady=6)
        self.override_phrase = ctk.CTkEntry(settings, height=34)
        self.override_phrase.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)
        ctk.CTkLabel(settings, text="Wait time minutes", text_color=TEXT_MUTED).grid(row=1, column=0, sticky="w", padx=(12, 0), pady=6)
        self.override_cooldown = ttk.Spinbox(settings, from_=0, to=240, width=8)
        self.override_cooldown.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=3)
        ctk.CTkLabel(settings, text="Unlocked for minutes", text_color=TEXT_MUTED).grid(row=2, column=0, sticky="w", padx=(12, 0), pady=6)
        self.override_window = ttk.Spinbox(settings, from_=1, to=240, width=8)
        self.override_window.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=3)
        settings.columnconfigure(1, weight=1)
        self._button(settings, "Save settings", self.save_override_settings, width=140).grid(row=3, column=1, sticky="e", padx=(0, 12), pady=(8, 12))

        request = ctk.CTkFrame(tab, fg_color="transparent")
        request.pack(fill="x", pady=(12, 0))
        self.override_type = ttk.Combobox(request, values=("app", "site", "url_path", "folder"), state="readonly", width=12)
        self.override_type.set("app")
        self.override_type.grid(row=0, column=0, padx=(0, 8))
        self.override_target = ctk.CTkEntry(request, height=34, placeholder_text="Target")
        self.override_target.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.override_phrase_attempt = ctk.CTkEntry(request, height=34, placeholder_text="Unlock phrase")
        self.override_phrase_attempt.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self._button(request, "Request", self.request_override, width=110).grid(row=0, column=3)
        request.columnconfigure(1, weight=1)
        request.columnconfigure(2, weight=1)

        self.override_tree = ttk.Treeview(tab, columns=("status", "type", "target", "requested", "ready", "expires"), show="headings")
        for name, width in (("status", 90), ("type", 80), ("target", 260), ("requested", 155), ("ready", 155), ("expires", 155)):
            self.override_tree.heading(name, text=name.title())
            self.override_tree.column(name, width=width)
        self.override_tree.pack(fill="both", expand=True, pady=12)
        self._button(tab, "Refresh", self.refresh_overrides, "muted", width=110).pack(anchor="e")

    def _build_history(self):
        tab = self._tab("History")
        self.history_tree = ttk.Treeview(tab, columns=("time", "type", "action", "target", "detail"), show="headings")
        for name, width in (("time", 165), ("type", 90), ("action", 110), ("target", 280), ("detail", 220)):
            self.history_tree.heading(name, text=name.title())
            self.history_tree.column(name, width=width)
        self.history_tree.pack(fill="both", expand=True)
        self._button(tab, "Refresh", self.refresh_history, "muted", width=110).pack(anchor="e", pady=(10, 0))

    def _build_settings(self):
        tab = self._tab("Settings")
        panel = self._card(tab, fill="x", pady=(4, 0))
        for text, command, variant in (
            ("Start when Windows starts", self.enable_startup, "success"),
            ("Do not start with Windows", self.disable_startup, "muted"),
            ("Stronger startup (admin)", self.install_startup_task, "primary"),
            ("Remove stronger startup", self.remove_startup_task, "danger"),
            ("Protect settings folder", self.harden_acl, "primary"),
            ("Change master password", self.change_password, "primary"),
            ("Show app data folder", self.show_appdata, "muted"),
        ):
            self._button(panel, text, command, variant, width=220).pack(anchor="w", padx=12, pady=5)
        self._button(tab, "Close UI", self.destroy, "muted", width=120).pack(anchor="w", pady=(18, 4))

    def refresh_all(self):
        self.refresh_status(schedule=False)
        self.refresh_focus()
        self.refresh_apps()
        self.refresh_sites()
        self.refresh_folders()
        self.refresh_overrides()
        self.refresh_history()
        self.refresh_summary()
        self._schedule_status_refresh()

    def refresh_status(self, schedule=True):
        running = runtime_control.is_enforcer_running()
        config = self._load()
        enforce_now = focus_manager.should_enforce(config)
        self.status_var.set(
            f"Background: {'running' if running else 'stopped'} | "
            f"Starts With PC: {'on' if config['settings'].get('run_on_startup') else 'off'} | "
            f"Web: {'on' if config['settings'].get('website_hosts_applied') else 'off'}"
        )
        total_rules = (
            len(config.get("locked_apps", []))
            + len(config.get("blocked_sites", []))
            + len(config.get("blocked_url_paths", []))
            + len(config.get("locked_folders", []))
        )
        self.background_metric_var.set("Running" if running else "Stopped")
        self.startup_metric_var.set("On" if config["settings"].get("run_on_startup") else "Off")
        self.hosts_metric_var.set("On" if config["settings"].get("website_hosts_applied") else "Off")
        self.rules_metric_var.set(str(total_rules))
        self._refresh_app_lock_status(config, running, enforce_now)
        self._refresh_site_lock_status(config)
        if schedule:
            self._schedule_status_refresh()

    def _schedule_status_refresh(self):
        if self._status_after_id:
            try:
                self.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
        self._status_after_id = self.after(5000, self.refresh_status)

    def _refresh_app_lock_status(self, config, running: bool, enforce_now: bool):
        app_count = len(config.get("locked_apps", []))
        if not app_count:
            text = "No apps added yet."
        elif not config["settings"].get("background_enabled"):
            text = f"{app_count} app(s), but protection is off."
        elif not running:
            text = f"{app_count} app(s), but protection is off."
        elif not enforce_now:
            text = f"{app_count} app(s), paused until focus time."
        else:
            text = f"{app_count} app(s), protection is on."
        self.app_lock_status_var.set(text)

    def _refresh_site_lock_status(self, config):
        site_count = len(config.get("blocked_sites", []))
        if not site_count:
            text = "No websites added yet."
        elif not config["settings"].get("website_hosts_applied"):
            text = f"{site_count} website(s), not active yet."
        else:
            text = f"{site_count} website(s), web blocking is on."
        self.site_lock_status_var.set(text)

    def refresh_summary(self):
        config = self._load()
        lines = [
            "STATUS",
            f"  Protection          {'running' if runtime_control.is_enforcer_running() else 'stopped'}",
            f"  Starts with PC      {'enabled' if config['settings'].get('run_on_startup') else 'disabled'}",
            f"  Website blocking   {'on' if config['settings'].get('website_hosts_applied') else 'off'}",
            f"  Focus schedule      {'enabled' if config['settings'].get('schedule_only_mode') else 'disabled'}",
            f"  Focus session      {config['settings'].get('focus_session_until') or 'not active'}",
            "",
            "RULES",
            f"  App locks          {len(config['locked_apps'])}",
            f"  Website domains    {len(config['blocked_sites'])}",
            f"  URL path rules     {len(config['blocked_url_paths'])}",
            f"  Locked folders     {len(config['locked_folders'])}",
            f"  Unlock records     {len(config['override_requests'])}",
            f"  Focus schedules    {len(config['focus_schedules'])}",
            "",
            "SECURITY",
            "  Passwords are not stored in plain text.",
            "  The local config is encrypted.",
            "  A Windows administrator can still bypass user-level controls.",
        ]
        self.summary.configure(state="normal")
        self.summary.configure(bg="#FFFFFF", fg="#0F172A", insertbackground="#0F172A")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", "\n".join(lines))
        self.summary.configure(state="disabled")

    def refresh_apps(self):
        self.apps_tree.delete(*self.apps_tree.get_children())
        for rule in app_blocker.list_locked_apps(self.password):
            self.apps_tree.insert("", "end", values=(rule["mode"], rule["value"]))
        self.strict_app_lock_var.set(bool(self._load()["settings"].get("strict_app_lock", True)))

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
            processes = app_blocker.list_running_process_details()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not list running apps:\n{exc}", parent=self)
            return
        picker = tk.Toplevel(self)
        picker.title("Running Apps")
        picker.geometry("780x460")
        picker.transient(self)

        filter_var = tk.StringVar()
        search = ctk.CTkEntry(picker, textvariable=filter_var)
        search.pack(fill="x", padx=10, pady=(10, 6))

        tree = ttk.Treeview(picker, columns=("pid", "name", "exe"), show="headings")
        tree.heading("pid", text="PID")
        tree.heading("name", text="Process")
        tree.heading("exe", text="Path")
        tree.column("pid", width=70, stretch=False)
        tree.column("name", width=180, stretch=False)
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def fill_tree():
            query = filter_var.get().strip().lower()
            tree.delete(*tree.get_children())
            for process in processes:
                haystack = f"{process['name']} {process['exe']}".lower()
                if query and query not in haystack:
                    continue
                tree.insert("", "end", values=(process["pid"], process["name"], process["exe"]))

        def use_selected():
            selection = tree.focus()
            if selection:
                _, name, exe = tree.item(selection, "values")
                self.app_entry.delete(0, "end")
                self.app_entry.insert(0, exe or name)
                picker.destroy()

        filter_var.trace_add("write", lambda *_: fill_tree())
        fill_tree()
        ctk.CTkButton(picker, text="Use selected", command=use_selected).pack(pady=(0, 10))
        search.focus_set()

    def add_app(self):
        value = self.app_entry.get().strip()
        if value:
            result = self._run("Add app", lambda: self._add_app_and_start(value))
            if result:
                messagebox.showinfo(APP_TITLE, result, parent=self)
                self.app_entry.delete(0, "end")

    def _add_app_and_start(self, value: str) -> str:
        app_blocker.add_locked_app(value, self.password)
        config = self._load()
        notes = []
        if config["settings"].get("schedule_only_mode") and not focus_manager.should_enforce(config):
            notes.append("Saved. It will block during focus time.")
        was_running = runtime_control.is_enforcer_running()
        cfg.enable_background_unlock(self.password)
        if not config["settings"].get("background_enabled"):
            notes.append("Protection turned on.")
        else:
            notes.append("Protection refreshed.")
        if not runtime_control.start_enforcer_and_wait():
            raise RuntimeError("Protection could not start. Open Settings and turn protection on again.")
        if not was_running:
            notes.append("Protection started.")
        return "App rule added. " + (" ".join(notes) if notes else "Protection is on.")

    def remove_app(self):
        item = self.apps_tree.focus()
        if not item:
            return
        _, value = self.apps_tree.item(item, "values")
        self._run("Remove app", lambda: app_blocker.remove_locked_app(value, self.password))

    def test_selected_app_rule(self):
        item = self.apps_tree.focus()
        if not item:
            messagebox.showinfo(APP_TITLE, "Select an app rule first.", parent=self)
            return
        mode, value = self.apps_tree.item(item, "values")
        config = self._load()
        matches = app_blocker.find_matching_processes([{"mode": mode, "value": value}], config)
        running = runtime_control.is_enforcer_running()
        enforce_now = focus_manager.should_enforce(config)
        if matches and running and enforce_now:
            detail = "\n".join(f"{match['name']} pid={match['pid']}" for match in matches[:8])
            messagebox.showinfo(APP_TITLE, f"This lock matches a running app:\n{detail}\n\nProtection should close it.", parent=self)
        elif matches:
            reason = "protection service is stopped" if not running else "focus schedule is paused"
            messagebox.showwarning(APP_TITLE, f"Rule matches a running process, but {reason}.", parent=self)
        else:
            messagebox.showinfo(APP_TITLE, "No running process currently matches this rule.", parent=self)

    def password_unlock_selected_app(self):
        item = self.apps_tree.focus()
        if not item:
            messagebox.showinfo(APP_TITLE, "Select an app rule first.", parent=self)
            return
        _, value = self.apps_tree.item(item, "values")
        password = simpledialog.askstring(APP_TITLE, "Master password", show="*", parent=self)
        if not password:
            return
        if not cfg.verify_password(password):
            messagebox.showerror(APP_TITLE, "Wrong password.", parent=self)
            return
        config = self._load()
        minutes = int(config["settings"].get("password_unlock_minutes", 10))
        result = self._run(
            "Unlock for a while",
            lambda: override_manager.password_unlock(password, "app", value, minutes),
        )
        if result:
            messagebox.showinfo(APP_TITLE, f"Unlocked for {minutes} minute(s).", parent=self)

    def save_strict_app_lock(self):
        def update():
            config = self._load()
            config["settings"]["strict_app_lock"] = bool(self.strict_app_lock_var.get())
            audit_log.add_event(
                config,
                "app",
                "settings",
                "strict_lock_updated",
                f"enabled={config['settings']['strict_app_lock']}",
            )
            EncryptedDatabase(self.password).save_dict(config)
        self._run("Save app lock mode", update)

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
        result = self._run("Turn web blocking on", lambda: site_blocker.apply_hosts_block(self.password))
        if result:
            messagebox.showinfo(
                APP_TITLE,
                "Web blocking is on.\n\nIf the website still opens, restart the browser. In Chrome, Edge, or Brave, turn off Secure DNS if needed.",
                parent=self,
            )

    def rollback_hosts(self):
        self._run("Turn web blocking off", lambda: self._rollback_hosts_and_save())

    def _rollback_hosts_and_save(self):
        path = site_blocker.rollback_hosts_block()
        config = self._load()
        config["settings"]["website_hosts_applied"] = False
        audit_log.add_event(config, "site", "hosts", "rollback", f"path={path}")
        EncryptedDatabase(self.password).save_dict(config)
        return path

    def check_website_block(self):
        status = self._run("Check website block", lambda: site_blocker.website_block_status(self.password), refresh=False)
        if not status:
            return
        if status["error"] == "admin_required":
            detail = "Windows needs administrator permission for website blocking. Run Windslock as administrator, then turn web blocking on."
        elif status["domain_count"] and not status["rules_present"]:
            detail = "Your websites are saved, but Windows has not applied them yet. Run Windslock as administrator and turn web blocking on."
        elif status["domain_count"]:
            detail = "Web blocking is on. Restart the browser if it cached the website. In Chrome, Edge, and Brave, turn off Secure DNS if needed."
        else:
            detail = "No website rules are saved yet."
        messagebox.showinfo(
            APP_TITLE,
            f"{detail}\n\nWindows file:\n{status['hosts_path']}",
            parent=self,
        )

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
        def enable():
            cfg.enable_background_unlock(self.password)
            if not runtime_control.start_enforcer_and_wait():
                raise RuntimeError("Protection could not start.")
        self._run("Turn protection on", enable)

    def disable_background(self):
        self._run("Turn protection off", lambda: (cfg.disable_background_unlock(self.password), runtime_control.stop_enforcer()))

    def enable_startup(self):
        self._run("Start with Windows", lambda: startup.enable_startup(self.password))

    def disable_startup(self):
        self._run("Stop starting with Windows", lambda: startup.disable_startup(self.password))

    def install_startup_task(self):
        self._run("Set stronger startup", lambda: startup.install_scheduled_task(self.password, launch_tray=True))

    def remove_startup_task(self):
        self._run("Remove stronger startup", lambda: startup.uninstall_scheduled_task(self.password))

    def harden_acl(self):
        self._run("Protect settings folder", lambda: tamper.harden_config_acl(self.password))

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
                messagebox.showinfo(APP_TITLE, f"Unlock request: {result['status']}", parent=self)

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


class LockScreenWindow(ctk.CTk):
    def __init__(self, target: str):
        super().__init__()
        import os
        self.target = target
        self.title("Windslock - App Locked")
        self.geometry("480x300")
        self.resizable(False, False)
        self.configure(fg_color=WINDOW_BG)
        
        # Center the window
        self.update_idletasks()
        width = 480
        height = 300
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Attempt to set window icon
        try:
            if brand.icon_ico().exists():
                self.iconbitmap(str(brand.icon_ico()))
        except Exception:
            pass
            
        # Top-most / focus
        self.attributes("-topmost", True)
        self.focus_force()
        
        self._build_ui()

    def _build_ui(self):
        import os
        container = ctk.CTkFrame(self, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=14)
        container.pack(fill="both", expand=True, padx=16, pady=16)
        
        # Header
        header_lbl = ctk.CTkLabel(container, text="🔒 App Locked", font=("Segoe UI", 20, "bold"), text_color=DANGER)
        header_lbl.pack(anchor="w", padx=20, pady=(20, 4))
        
        display_name = os.path.basename(self.target)
        desc_lbl = ctk.CTkLabel(
            container, 
            text=f"'{display_name}' has been locked to keep you focused.", 
            font=("Segoe UI", 12),
            text_color=TEXT_MAIN,
            wraplength=400,
            justify="left"
        )
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 16))
        
        # Password entry
        pwd_label = ctk.CTkLabel(container, text="Enter Master Password to unlock:", font=("Segoe UI", 11, "bold"), text_color=TEXT_MUTED)
        pwd_label.pack(anchor="w", padx=20, pady=(0, 4))
        
        self.password_entry = ctk.CTkEntry(container, show="*", height=36, placeholder_text="Password")
        self.password_entry.pack(fill="x", padx=20, pady=(0, 8))
        self.password_entry.focus()
        
        # Bind Return key to unlock_app
        self.password_entry.bind("<Return>", lambda e: self.unlock_app())
        
        # Error Label
        self.error_label = ctk.CTkLabel(container, text="", font=("Segoe UI", 11), text_color=DANGER)
        self.error_label.pack(anchor="w", padx=20, pady=(0, 8))
        
        # Buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(8, 16))
        
        self.unlock_app_btn = ctk.CTkButton(
            btn_frame, 
            text="Unlock App", 
            command=self.unlock_app, 
            fg_color=ACCENT, 
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            height=32
        )
        self.unlock_app_btn.pack(side="left", padx=(0, 8))
        
        self.unlock_all_btn = ctk.CTkButton(
            btn_frame, 
            text="Unlock All", 
            command=self.unlock_all, 
            fg_color=SUCCESS, 
            hover_color="#15803D",
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            height=32
        )
        self.unlock_all_btn.pack(side="left", padx=(0, 8))
        
        self.cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            command=self.destroy, 
            fg_color=PANEL_ALT, 
            hover_color="#CBD5E1",
            text_color=TEXT_MAIN,
            font=("Segoe UI", 11, "bold"),
            height=32
        )
        self.cancel_btn.pack(side="right")
        
    def unlock_app(self):
        import os
        password = self.password_entry.get()
        if not password:
            self.error_label.configure(text="Password cannot be empty.")
            return
            
        if not cfg.verify_password(password):
            self.error_label.configure(text="Incorrect master password.")
            return
            
        try:
            config = cfg.load_config(password)
            minutes = int(config["settings"].get("password_unlock_minutes", 10))
            override_manager.password_unlock(password, "app", self.target, minutes)
            messagebox.showinfo("Windslock", f"'{os.path.basename(self.target)}' has been unlocked for {minutes} minutes.")
            self.destroy()
        except Exception as exc:
            self.error_label.configure(text=f"Error: {exc}")
            
    def unlock_all(self):
        password = self.password_entry.get()
        if not password:
            self.error_label.configure(text="Password cannot be empty.")
            return
            
        if not cfg.verify_password(password):
            self.error_label.configure(text="Incorrect master password.")
            return
            
        try:
            config = cfg.load_config(password)
            minutes = int(config["settings"].get("password_unlock_minutes", 10))
            override_manager.password_unlock(password, "system", "all", minutes)
            messagebox.showinfo("Windslock", f"All protection rules unlocked for {minutes} minutes.")
            self.destroy()
        except Exception as exc:
            self.error_label.configure(text=f"Error: {exc}")


def run_lock_screen(target: str) -> None:
    ctk.set_appearance_mode('System')
    ctk.set_default_color_theme('blue')
    app = LockScreenWindow(target)
    app.mainloop()


def open_app() -> None:
    import sys
    
    lock_target = None
    if "--lock-screen" in sys.argv:
        try:
            idx = sys.argv.index("--lock-screen")
            if idx + 1 < len(sys.argv):
                lock_target = sys.argv[idx + 1]
        except ValueError:
            pass
            
    if lock_target:
        run_lock_screen(lock_target)
        return

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
