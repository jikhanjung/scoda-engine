#!/usr/bin/env python3
"""
SCODA Desktop — GUI Control Panel

Provides a Docker Desktop-style graphical interface to select a package
and control the web server.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import json
import logging
import threading
import webbrowser
import os
import sys
import time
import subprocess

from scoda_engine import __version__
import scoda_engine_core as scoda_package
from scoda_engine_core.hub_client import (
    fetch_hub_index, compare_with_local, download_package,
    resolve_download_order,
    HubError, HubConnectionError, HubSSLError, HubChecksumError,
)

def _get_settings_path():
    """Return the path to ScodaDesktop.cfg.

    Stored next to the executable (frozen) or next to the project root (dev),
    so the user can see and edit it alongside the .scoda packages.
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "ScodaDesktop.cfg")


def _load_settings():
    """Load persistent settings from disk."""
    try:
        with open(_get_settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_settings(settings):
    """Save persistent settings to disk."""
    try:
        with open(_get_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


class LogRedirector:
    """Redirect stdout/stderr to GUI log viewer."""
    def __init__(self, callback):
        self.callback = callback

    def write(self, text):
        if text.strip():
            self.callback(text.strip())

    def flush(self):
        pass

    def isatty(self):
        """Return False to indicate this is not a TTY (required by uvicorn logger)."""
        return False

    def fileno(self):
        """Return a dummy file descriptor (required by some logging handlers)."""
        return -1


class TkLogHandler(logging.Handler):
    """Route Python logging output to the GUI log panel."""

    def __init__(self, append_log_fn):
        super().__init__()
        self._append_log = append_log_fn

    def emit(self, record):
        try:
            msg = self.format(record)
            level_map = {
                'ERROR': 'ERROR',
                'CRITICAL': 'ERROR',
                'WARNING': 'WARNING',
                'INFO': 'INFO',
            }
            tag = level_map.get(record.levelname)
            self._append_log(msg, tag)
        except Exception:
            self.handleError(record)


class ScodaDesktopGUI:
    def __init__(self, scoda_path=None):
        self.root = tk.Tk()
        self.root.title(f"SCODA Desktop v{__version__}")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        self.root.minsize(600, 400)

        # Web server state
        self.server_process = None  # For subprocess mode
        self.server_thread = None   # For threaded mode (frozen)
        self.uvicorn_server = None  # For threaded mode (graceful shutdown)
        self.original_stdout = None # For restoring stdout after redirect
        self.original_stderr = None # For restoring stderr after redirect
        self.log_reader_thread = None
        self.server_running = False
        self.port = 8080

        # Selected package
        self.selected_package = None

        # Track externally loaded .scoda paths (name → scoda_path)
        self._external_scoda_paths = {}

        # Hub state
        self._hub_index = None
        self._hub_available = []   # available + updatable combined for display
        self._hub_updatable = []
        self._download_in_progress = False

        # SSL settings (persisted)
        self._settings = _load_settings()
        self._ssl_noverify = self._settings.get("ssl_noverify", False)

        # Determine base path
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(self.base_path)

        # If a .scoda path was given, register it before scanning
        if scoda_path:
            scoda_package._reset_registry()
            self.registry = scoda_package.get_registry()
            try:
                name = self.registry.register_path(scoda_path)
                self._external_scoda_paths[name] = os.path.abspath(scoda_path)
            except (FileNotFoundError, ValueError) as e:
                logging.getLogger(__name__).warning("Failed to load %s: %s", scoda_path, e)
                self.registry = scoda_package.get_registry()
        else:
            # Use PackageRegistry for package discovery
            self.registry = scoda_package.get_registry()

        self.packages = self.registry.list_packages()

        # Auto-select if only one package
        if len(self.packages) == 1:
            self.selected_package = self.packages[0]['name']

        self._create_widgets()
        self._update_status()

        # Route Python logging to GUI log panel
        self._tk_log_handler = TkLogHandler(
            lambda msg, tag=None: self.root.after(0, self._append_log, msg, tag)
        )
        self._tk_log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logging.getLogger("scoda_engine").setLevel(logging.INFO)
        logging.getLogger("scoda_engine").addHandler(self._tk_log_handler)
        logging.getLogger("scoda_engine_core").setLevel(logging.INFO)
        logging.getLogger("scoda_engine_core").addHandler(self._tk_log_handler)

        # Initial log messages
        self._append_log("SCODA Desktop initialized")
        if self.packages:
            for pkg in self.packages:
                src = f" ({pkg['source_type']})" if pkg['source_type'] == 'scoda' else ''
                self._append_log(f"Loaded: {pkg['name']} v{pkg['version']}{src}, {pkg['record_count']} records")
        else:
            self._append_log("WARNING: No packages found!", "WARNING")

        if self.selected_package:
            self._append_log(f"Selected: {self.selected_package}")

        if self._ssl_noverify:
            self._append_log("SSL verification: disabled (saved setting)", "WARNING")

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Fetch Hub index in background
        threading.Thread(target=self._fetch_hub_index, daemon=True).start()

        # Auto-start if single package (same UX as before)
        if len(self.packages) == 1:
            self.root.after(500, self.start_server)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Header
        header_frame = tk.Frame(self.root, bg="#2196F3", height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        header_inner = tk.Frame(header_frame, bg="#2196F3")
        header_inner.pack(pady=12)

        header = tk.Label(header_inner, text="SCODA Desktop",
                         font=("Arial", 14, "bold"), bg="#2196F3", fg="white")
        header.pack(side="left")

        self.header_pkg_label = tk.Label(header_inner, text="",
                                          font=("Arial", 10), bg="#2196F3", fg="#BBDEFB")
        self.header_pkg_label.pack(side="left", padx=(10, 0))

        # Top section (Packages + Controls side by side, fixed 50:50 ratio)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)
        top_frame.columnconfigure(0, weight=1, uniform="top")
        top_frame.columnconfigure(1, weight=1, uniform="top")

        # Left: Package selection
        pkg_frame = tk.LabelFrame(top_frame, text="Packages", padx=10, pady=10)
        pkg_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Package Listbox
        listbox_frame = tk.Frame(pkg_frame)
        listbox_frame.pack(fill="both", expand=True)

        self.pkg_listbox = tk.Listbox(
            listbox_frame,
            height=max(3, len(self.packages)),
            selectmode="browse",
            font=("Courier", 9),
            exportselection=False
        )
        self.pkg_listbox.pack(fill="both", expand=True)

        # Populate listbox
        self._refresh_pkg_listbox()

        # Pre-select if auto-selected
        if self.selected_package:
            for i, pkg in enumerate(self.packages):
                if pkg['name'] == self.selected_package:
                    self.pkg_listbox.selection_set(i)
                    break

        self.pkg_listbox.bind("<<ListboxSelect>>", self._on_package_select)

        # Selected package info area
        self.pkg_info_label = tk.Label(pkg_frame, text="", anchor="w",
                                        justify="left", fg="#555",
                                        font=("Arial", 8), wraplength=300)
        self.pkg_info_label.pack(fill="x", pady=(5, 0))
        self._update_pkg_info()

        # Right: Control section
        control_frame = tk.LabelFrame(top_frame, text="Controls", padx=10, pady=10)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Flask Start/Stop row
        server_row = tk.Frame(control_frame)
        server_row.pack(pady=3)

        self.start_btn = tk.Button(server_row, text="\u25b6 Start Server", width=12,
                                   command=self.start_server, bg="#4CAF50", fg="white",
                                   relief="raised", bd=2)
        self.start_btn.pack(side="left", padx=2)

        self.stop_btn = tk.Button(server_row, text="\u25a0 Stop Server", width=12,
                                  command=self.stop_server, state="disabled",
                                  bg="#f44336", fg="white", relief="raised", bd=2)
        self.stop_btn.pack(side="left", padx=2)

        # Open browser button
        self.browser_btn = tk.Button(control_frame, text="Open Browser", width=26,
                                     command=self.open_browser, state="disabled",
                                     relief="raised", bd=2)
        self.browser_btn.pack(pady=3)

        # Clear log button
        self.clear_log_btn = tk.Button(control_frame, text="Clear Log", width=26,
                                       command=self.clear_log,
                                       relief="raised", bd=2)
        self.clear_log_btn.pack(pady=3)

        # Quit button
        quit_btn = tk.Button(control_frame, text="Exit", width=26,
                            command=self.quit_app, bg="#9E9E9E", fg="white",
                            relief="raised", bd=2)
        quit_btn.pack(pady=3)

        # Bottom: Log Viewer
        log_frame = tk.LabelFrame(self.root, text="Server Log", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Hub: Available Packages (initially hidden, inserted BEFORE log_frame)
        self._hub_log_frame = log_frame  # keep reference for pack(before=)
        self._hub_frame = tk.LabelFrame(self.root, text="Hub - Available Packages",
                                         padx=10, pady=5)
        # Not packed yet — shown only after successful Hub fetch

        hub_top = tk.Frame(self._hub_frame)
        hub_top.pack(fill="x")

        self._hub_listbox = tk.Listbox(
            hub_top, height=3, selectmode="browse",
            font=("Courier", 9), exportselection=False,
        )
        self._hub_listbox.pack(side="left", fill="both", expand=True)

        hub_btn_frame = tk.Frame(hub_top)
        hub_btn_frame.pack(side="left", padx=(5, 0))

        self._hub_download_btn = tk.Button(
            hub_btn_frame, text="Download", width=10,
            command=self._download_selected_hub_package,
            bg="#2196F3", fg="white", relief="raised", bd=2,
        )
        self._hub_download_btn.pack(pady=2)

        self._hub_dl_all_btn = tk.Button(
            hub_btn_frame, text="Download All", width=10,
            command=self._download_all_hub_packages,
            bg="#4CAF50", fg="white", relief="raised", bd=2,
        )
        self._hub_dl_all_btn.pack(pady=2)

        hub_bottom = tk.Frame(self._hub_frame)
        hub_bottom.pack(fill="x", pady=(3, 0))

        self._hub_status_label = tk.Label(
            hub_bottom, text="Checking Hub...", anchor="w",
            font=("Arial", 8), fg="#888",
        )
        self._hub_status_label.pack(side="left", fill="x", expand=True)

        self._hub_progress = ttk.Progressbar(
            hub_bottom, mode="determinate", length=200,
        )
        # Progress bar not packed — shown only during download

        # Scrollbar
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        # Text widget (read-only)
        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            state="disabled",
            height=20,
            font=("Courier", 9),
            bg="#f5f5f5",
            fg="#333333"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Color tags for log levels
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("INFO", foreground="blue")
        self.log_text.tag_config("SUCCESS", foreground="green")

    def _on_package_select(self, event):
        """Handle package selection change in Listbox."""
        if self.server_running:
            self._append_log("Stop server before switching packages", "WARNING")
            # Re-select the current package
            for i, pkg in enumerate(self.packages):
                if pkg['name'] == self.selected_package:
                    self.pkg_listbox.selection_clear(0, "end")
                    self.pkg_listbox.selection_set(i)
                    break
            return

        idx = self.pkg_listbox.curselection()
        if not idx:
            return
        self.selected_package = self.packages[idx[0]]['name']
        self._update_pkg_info()
        self._update_status()
        self._append_log(f"Selected: {self.selected_package}")

    def _refresh_pkg_listbox(self):
        """Refresh listbox items with current status indicators."""
        self.pkg_listbox.config(state="normal")
        self.pkg_listbox.delete(0, "end")

        # Build dep names for the running package
        running_dep_names = set()
        if self.server_running and self.selected_package:
            running_pkg = self._get_selected_pkg()
            if running_pkg:
                for dep in running_pkg.get('deps', []):
                    running_dep_names.add(dep.get('name'))

        sel_idx = None
        row = 0
        for pkg in self.packages:
            is_running = self.server_running and pkg['name'] == self.selected_package
            is_loaded_dep = self.server_running and pkg['name'] in running_dep_names

            # Skip deps here; they'll appear as children under the running package
            if is_loaded_dep:
                continue

            if is_running:
                label = f" \u25b6 Running  {pkg['name']} v{pkg['version']} \u2014 {pkg['record_count']:,} records"
            else:
                label = f" \u25a0 Stopped  {pkg['name']} v{pkg['version']} \u2014 {pkg['record_count']:,} records"
            self.pkg_listbox.insert("end", label)

            if pkg['name'] == self.selected_package:
                sel_idx = row
            row += 1

            # Insert dependency children under running package
            if is_running:
                for dep in pkg.get('deps', []):
                    dep_name = dep.get('name')
                    dep_pkg = None
                    for p in self.packages:
                        if p['name'] == dep_name:
                            dep_pkg = p
                            break
                    if dep_pkg:
                        dep_label = (f"   \u2514\u2500 Loaded  {dep_pkg['name']} v{dep_pkg['version']}"
                                     f" \u2014 {dep_pkg['record_count']:,} records")
                    else:
                        dep_label = f"   \u2514\u2500 Loaded  {dep_name} (alias: {dep.get('alias', dep_name)})"
                    self.pkg_listbox.insert("end", dep_label)
                    row += 1

        # Restore selection
        if sel_idx is not None:
            self.pkg_listbox.selection_set(sel_idx)

        # Disable switching while running
        if self.server_running:
            self.pkg_listbox.config(state="disabled")

    def _get_selected_pkg(self):
        """Return the selected package dict or None."""
        if not self.selected_package:
            return None
        for p in self.packages:
            if p['name'] == self.selected_package:
                return p
        return None

    def _update_pkg_info(self):
        """Update the package info label below the Listbox."""
        if not self.selected_package:
            self.pkg_info_label.config(text="Select a package to start")
            return

        pkg = None
        for p in self.packages:
            if p['name'] == self.selected_package:
                pkg = p
                break

        if pkg:
            info_parts = [f"{pkg['title']}"]
            if pkg.get('description'):
                info_parts.append(pkg['description'])
            if pkg.get('has_dependencies'):
                info_parts.append("Has dependencies")
            self.pkg_info_label.config(text="\n".join(info_parts))

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _set_ssl_noverify(self, value):
        """Update and persist the SSL noverify setting."""
        self._ssl_noverify = value
        self._settings["ssl_noverify"] = value
        _save_settings(self._settings)

    # ------------------------------------------------------------------
    # SSL fallback dialog
    # ------------------------------------------------------------------

    def _ask_ssl_fallback(self):
        """Show a dialog asking the user to allow SSL fallback.

        Called on the main thread.  Returns True if the user agrees.
        If the "remember" checkbox is checked, persists the choice.
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("SSL Certificate Error")
        dlg.resizable(False, False)
        dlg.grab_set()

        # Center on parent
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 220) // 2
        dlg.geometry(f"420x220+{x}+{y}")

        msg = (
            "SSL certificate verification failed.\n\n"
            "This commonly happens on networks with SSL inspection\n"
            "proxies (e.g. corporate/institutional firewalls).\n\n"
            "Would you like to continue without SSL verification?\n"
            "(Package integrity is verified via SHA-256 checksum.)"
        )
        tk.Label(dlg, text=msg, justify="left", padx=15, pady=10,
                 wraplength=390).pack(fill="x")

        remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="Remember this choice",
                       variable=remember_var).pack(anchor="w", padx=20)

        result = {"accepted": False}

        def on_yes():
            result["accepted"] = True
            if remember_var.get():
                self._set_ssl_noverify(True)
                self._append_log(
                    "SSL verification disabled (saved to settings)",
                    "WARNING")
            dlg.destroy()

        def on_no():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Yes, continue", width=14,
                  command=on_yes, bg="#2196F3", fg="white").pack(
                      side="left", padx=5)
        tk.Button(btn_frame, text="No, cancel", width=14,
                  command=on_no).pack(side="left", padx=5)

        dlg.protocol("WM_DELETE_WINDOW", on_no)
        self.root.wait_window(dlg)
        return result["accepted"]

    # ------------------------------------------------------------------
    # Hub methods
    # ------------------------------------------------------------------

    def _fetch_hub_index(self):
        """Background thread: fetch Hub index and compare with local packages."""
        self.root.after(0, self._set_wait_cursor, True)
        self.root.after(0, self._hub_status_label.config,
                        {"text": "Checking Hub...", "fg": "#888"})
        try:
            index = fetch_hub_index(ssl_noverify=self._ssl_noverify)
            comparison = compare_with_local(index, self.packages)
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_hub_fetch_complete, index, comparison)
        except HubSSLError as e:
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_hub_ssl_error, str(e), "fetch")
        except HubError as e:
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_hub_fetch_error, str(e))

    def _on_hub_ssl_error(self, error_msg, phase, download_items=None):
        """Main thread: handle SSL error by showing dialog and retrying."""
        self._append_log(f"Hub: {error_msg}", "WARNING")

        accepted = self._ask_ssl_fallback()
        if not accepted:
            self._append_log("Hub: SSL fallback declined by user", "WARNING")
            if phase == "download":
                self._on_download_error("Download cancelled (SSL error)")
            return

        # Retry the operation with SSL verification disabled
        self._ssl_noverify = True
        self._append_log("Hub: retrying without SSL verification...", "INFO")

        if phase == "fetch":
            threading.Thread(target=self._fetch_hub_index, daemon=True).start()
        elif phase == "download" and download_items:
            self._do_download_start(download_items)

    def _on_hub_fetch_complete(self, index, comparison):
        """Main thread callback after successful Hub fetch."""
        self._hub_index = index
        self._hub_available = comparison["available"]
        self._hub_updatable = comparison["updatable"]

        if self._ssl_noverify:
            self._append_log(
                "Hub: connected (SSL verification disabled)", "WARNING")

        total = len(self._hub_available) + len(self._hub_updatable)
        if total == 0:
            self._append_log("Hub: all packages up to date")
            return

        # Show Hub section (insert before log frame so it's visible)
        self._hub_frame.pack(fill="x", padx=10, pady=(0, 5),
                             before=self._hub_log_frame)
        self._refresh_hub_listbox()

        avail_count = len(self._hub_available)
        upd_count = len(self._hub_updatable)
        parts = []
        if avail_count:
            parts.append(f"{avail_count} new")
        if upd_count:
            parts.append(f"{upd_count} update(s)")
        status = f"Hub: {', '.join(parts)} available"
        self._hub_status_label.config(text=status, fg="#333")
        self._append_log(status, "INFO")

    def _on_hub_fetch_error(self, error_msg):
        """Main thread callback on Hub fetch failure."""
        self._append_log(f"Hub: {error_msg}", "WARNING")

    def _refresh_hub_listbox(self):
        """Populate Hub listbox with available/updatable packages."""
        self._hub_listbox.delete(0, "end")
        for item in self._hub_updatable:
            entry = item["hub_entry"]
            size = entry.get("size_bytes", 0)
            size_str = self._format_size(size)
            deps = list(entry.get("dependencies", {}).keys())
            dep_suffix = f"  [requires: {', '.join(deps)}]" if deps else ""
            label = (f" [UPD] {item['name']}  "
                     f"v{item['local_version']} -> v{item['hub_version']}  {size_str}{dep_suffix}")
            self._hub_listbox.insert("end", label)
        for item in self._hub_available:
            entry = item["hub_entry"]
            size = entry.get("size_bytes", 0)
            size_str = self._format_size(size)
            deps = list(entry.get("dependencies", {}).keys())
            dep_suffix = f"  [requires: {', '.join(deps)}]" if deps else ""
            label = f" [NEW] {item['name']}  v{item['hub_version']}  {size_str}{dep_suffix}"
            self._hub_listbox.insert("end", label)

    @staticmethod
    def _format_size(size_bytes):
        """Format byte count to human-readable string."""
        if size_bytes <= 0:
            return ""
        if size_bytes < 1024:
            return f"({size_bytes} B)"
        elif size_bytes < 1024 * 1024:
            return f"({size_bytes / 1024:.1f} KB)"
        else:
            return f"({size_bytes / (1024 * 1024):.1f} MB)"

    def _download_selected_hub_package(self):
        """Handle Download button click."""
        if self._download_in_progress:
            return

        idx = self._hub_listbox.curselection()
        if not idx:
            messagebox.showinfo("No Selection", "Please select a package to download.")
            return

        i = idx[0]
        # Updatable items come first, then available
        all_items = self._hub_updatable + self._hub_available
        if i >= len(all_items):
            return
        selected = all_items[i]
        self._start_hub_download([selected])

    def _download_all_hub_packages(self):
        """Handle Download All button click."""
        if self._download_in_progress:
            return
        all_items = self._hub_updatable + self._hub_available
        if not all_items:
            return
        self._start_hub_download(all_items)

    def _start_hub_download(self, items):
        """Start background download for a list of Hub items (with confirmation)."""
        # Resolve full download order (deps included) — no network, instant
        full_order = []
        seen = set()
        requested_names = {it["name"] for it in items}
        for item in items:
            order = resolve_download_order(
                self._hub_index, item["name"], self.packages)
            for pkg_info in order:
                if pkg_info["name"] not in seen:
                    seen.add(pkg_info["name"])
                    full_order.append(pkg_info)

        if not full_order:
            self._append_log("Hub: nothing to download (already up to date)")
            return

        # Build confirmation message
        lines = []
        total_size = 0
        for pkg_info in full_order:
            entry = pkg_info["entry"]
            size = entry.get("size_bytes", 0)
            total_size += size
            size_str = self._format_size(size)
            is_dep = pkg_info["name"] not in requested_names
            dep_tag = "  [dependency]" if is_dep else ""
            prefix = "+ " if is_dep else ""
            lines.append(f"{prefix}{pkg_info['name']} v{pkg_info['version']} {size_str}{dep_tag}")

        total_str = self._format_size(total_size)
        summary = f"\n{len(full_order)} package(s), {total_str.strip('()')}"

        confirm_msg = "\n".join(lines) + "\n\n" + summary + "\n\nProceed with download?"

        if not messagebox.askyesno("Confirm Download", confirm_msg):
            self._append_log("Hub: download cancelled by user")
            return

        self._do_download_start(items)

    def _do_download_start(self, items):
        """Begin the download process (shared by initial and SSL retry)."""
        self._download_in_progress = True
        self._hub_download_btn.config(state="disabled")
        self._hub_dl_all_btn.config(state="disabled")
        self._hub_progress.pack(side="right", padx=(5, 0))
        self._hub_progress["value"] = 0

        names = ", ".join(it["name"] for it in items)
        self._hub_status_label.config(text=f"Downloading {names}...", fg="#2196F3")
        self._set_wait_cursor(True)

        threading.Thread(
            target=self._do_download_multi,
            args=(items,),
            daemon=True,
        ).start()

    def _do_download_multi(self, items):
        """Background thread: resolve deps and download package(s)."""
        try:
            # Determine download directory
            scan_dir = self.registry._scan_dir
            if not scan_dir:
                if getattr(sys, 'frozen', False):
                    scan_dir = os.path.dirname(sys.executable)
                else:
                    scan_dir = self.base_path
            os.makedirs(scan_dir, exist_ok=True)

            # Build full download order (deps first, deduplicated)
            full_order = []
            seen = set()
            for item in items:
                order = resolve_download_order(
                    self._hub_index, item["name"], self.packages)
                for pkg_info in order:
                    if pkg_info["name"] not in seen:
                        seen.add(pkg_info["name"])
                        full_order.append(pkg_info)

            if not full_order:
                names = ", ".join(it["name"] for it in items)
                self.root.after(0, self._set_wait_cursor, False)
                self.root.after(0, self._on_download_complete, names, [])
                return

            downloaded_paths = []
            total_packages = len(full_order)

            for pkg_idx, pkg_info in enumerate(full_order):
                entry = pkg_info["entry"]
                url = entry.get("download_url", "")
                sha256 = entry.get("sha256", "") or None

                def progress_cb(dl, total, _idx=pkg_idx, _total=total_packages):
                    if total > 0:
                        pct = ((dl / total) + _idx) / _total * 100
                    else:
                        pct = (_idx / _total) * 100
                    self.root.after(0, self._update_download_progress, pct)

                self.root.after(0, self._hub_status_label.config,
                                {"text": f"Downloading {pkg_info['name']} v{pkg_info['version']}"
                                         f" ({pkg_idx + 1}/{total_packages})..."})

                path = download_package(
                    url, scan_dir,
                    expected_sha256=sha256,
                    progress_callback=progress_cb,
                    ssl_noverify=self._ssl_noverify,
                )
                downloaded_paths.append(path)

            names = ", ".join(it["name"] for it in items)
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_download_complete,
                            names, downloaded_paths)

        except HubSSLError as e:
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_hub_ssl_error,
                            str(e), "download", items)
        except HubError as e:
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_download_error, str(e))
        except Exception as e:
            self.root.after(0, self._set_wait_cursor, False)
            self.root.after(0, self._on_download_error, str(e))

    def _update_download_progress(self, pct):
        """Main thread: update progress bar."""
        self._hub_progress["value"] = min(pct, 100)

    def _on_download_complete(self, pkg_name, downloaded_paths):
        """Main thread callback after download completes."""
        self._download_in_progress = False
        self._hub_download_btn.config(state="normal")
        self._hub_dl_all_btn.config(state="normal")
        self._hub_progress.pack_forget()

        if not downloaded_paths:
            self._hub_status_label.config(text="Package already up to date", fg="#333")
            self._append_log(f"Hub: {pkg_name} already up to date")
            return

        # Register downloaded packages
        for path in downloaded_paths:
            try:
                name = self.registry.register_path(path)
                self._append_log(f"Installed: {name} from Hub", "SUCCESS")
            except (FileNotFoundError, ValueError) as e:
                self._append_log(f"ERROR: Failed to register {path}: {e}", "ERROR")

        # Refresh package list
        self.packages = self.registry.list_packages()
        self._refresh_pkg_listbox()

        # Re-compare with Hub
        if self._hub_index:
            comparison = compare_with_local(self._hub_index, self.packages)
            self._hub_available = comparison["available"]
            self._hub_updatable = comparison["updatable"]
            self._refresh_hub_listbox()

            total = len(self._hub_available) + len(self._hub_updatable)
            if total == 0:
                self._hub_frame.pack_forget()
                self._hub_status_label.config(text="All packages up to date", fg="#333")
            else:
                self._hub_status_label.config(
                    text=f"{total} package(s) available", fg="#333")

        self._append_log(f"Hub: {pkg_name} download complete", "SUCCESS")

    def _on_download_error(self, error_msg):
        """Main thread callback on download failure."""
        self._download_in_progress = False
        self._hub_download_btn.config(state="normal")
        self._hub_dl_all_btn.config(state="normal")
        self._hub_progress.pack_forget()
        self._hub_status_label.config(text="Download failed", fg="red")
        self._append_log(f"Hub download error: {error_msg}", "ERROR")
        messagebox.showerror("Download Error", f"Failed to download package:\n{error_msg}")

    def _set_wait_cursor(self, waiting):
        """Set or clear the wait cursor on the root window."""
        self.root.config(cursor="wait" if waiting else "")
        self.root.update_idletasks()

    def start_server(self):
        """Start web server for the selected package."""
        if self.server_running:
            return

        if not self.selected_package:
            self._append_log("ERROR: No package selected!", "ERROR")
            messagebox.showerror("No Package",
                               "Please select a package before starting the server.")
            return

        # Verify the package exists in registry
        try:
            self.registry.get_package(self.selected_package)
        except KeyError:
            self._append_log(f"ERROR: Package '{self.selected_package}' not found!", "ERROR")
            return

        self.root.config(cursor="wait")
        self.root.update()
        try:
            # In frozen mode (PyInstaller), run in thread with stdout redirect
            # In dev mode, run as subprocess for better log capture
            if getattr(sys, 'frozen', False):
                self._start_server_threaded()
            else:
                self._start_server_subprocess()

            self.server_running = True
            self._update_status()

            # Auto-open browser after 1.5 seconds
            self.root.after(1500, self.open_browser)

        except Exception as e:
            self._append_log(f"ERROR: Failed to start server: {e}", "ERROR")
            messagebox.showerror("Server Error", f"Could not start server:\n{e}")
        finally:
            self.root.config(cursor="")
            self.root.update()

    def _start_server_threaded(self):
        """Start web server in thread (for frozen/PyInstaller mode)."""
        self._append_log(f"Starting web server (package={self.selected_package})...", "INFO")

        # Set active package before importing app
        scoda_package.set_active_package(self.selected_package)

        # Redirect stdout/stderr to GUI
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = LogRedirector(lambda msg: self.root.after(0, self._append_log, msg))
        sys.stderr = LogRedirector(lambda msg: self.root.after(0, self._append_log, msg))

        # Start web server in thread
        self.server_thread = threading.Thread(target=self._run_web_server, daemon=True)
        self.server_thread.start()

        self._append_log("Web server started", "INFO")

    def _start_server_subprocess(self):
        """Start web server as subprocess (for development mode)."""
        python_exe = sys.executable

        self._append_log(f"Starting web server (package={self.selected_package})...", "INFO")

        # Build command: use --scoda-path for externally loaded packages
        cmd = [python_exe, '-m', 'scoda_engine.app']
        ext_path = self._external_scoda_paths.get(self.selected_package)
        if ext_path:
            cmd.extend(['--scoda-path', ext_path])
        else:
            cmd.extend(['--package', self.selected_package])

        # Start server as subprocess (using -m for package import)
        self.server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=self.base_path
        )

        # Start log reader thread
        self.log_reader_thread = threading.Thread(
            target=self._read_server_logs,
            daemon=True
        )
        self.log_reader_thread.start()

    def _run_web_server(self):
        """Run FastAPI app with uvicorn (called in thread for frozen mode)."""
        try:
            import uvicorn
            from .app import app

            config = uvicorn.Config(
                app,
                host='127.0.0.1',
                port=self.port,
                log_level='info'
            )
            self.uvicorn_server = uvicorn.Server(config)
            self.uvicorn_server.run()
        except OSError as e:
            if "Address already in use" in str(e):
                self.root.after(0, self._append_log, f"ERROR: Port {self.port} already in use", "ERROR")
                self.root.after(0, lambda: messagebox.showerror(
                    "Port Error",
                    f"Port {self.port} is already in use.\nPlease close other applications."
                ))
            else:
                self.root.after(0, self._append_log, f"ERROR: {e}", "ERROR")
            self.server_running = False
            self.root.after(0, self._update_status)
        except Exception as e:
            import traceback
            self.root.after(0, self._append_log, f"ERROR: {e}", "ERROR")
            self.root.after(0, self._append_log, traceback.format_exc(), "ERROR")
            self.server_running = False
            self.root.after(0, self._update_status)

    def stop_server(self):
        """Stop web server (independent of MCP)."""
        if not self.server_running:
            return

        self.root.config(cursor="wait")
        self.root.update()
        self._append_log("Stopping web server...", "INFO")
        self.server_running = False

        # Terminate server process (subprocess mode)
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
                self._append_log("Server stopped successfully", "INFO")
            except subprocess.TimeoutExpired:
                self._append_log("Server did not stop gracefully, forcing...", "WARNING")
                self.server_process.kill()
                self.server_process.wait()
                self._append_log("Server forcefully stopped", "WARNING")
            except Exception as e:
                self._append_log(f"WARNING: Error stopping server: {e}", "WARNING")
            finally:
                self.server_process = None

        # Thread mode (frozen) - signal uvicorn to shut down gracefully
        elif self.server_thread:
            if self.uvicorn_server:
                self.uvicorn_server.should_exit = True
                self._append_log("Shutting down uvicorn...", "INFO")
                # Wait for thread to finish
                self.server_thread.join(timeout=5)
                if self.server_thread.is_alive():
                    self._append_log("Server thread still active after timeout", "WARNING")
                else:
                    self._append_log("Server stopped successfully", "INFO")
                self.uvicorn_server = None
            if hasattr(self, 'original_stdout') and self.original_stdout:
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
                self.original_stdout = None
                self.original_stderr = None
            self.server_thread = None

        self._update_status()
        self.root.config(cursor="")
        self.root.update()

    def _read_server_logs(self):
        """Read server logs from subprocess and display in GUI."""
        while self.server_running and self.server_process:
            try:
                line = self.server_process.stdout.readline()
                if line:
                    self.root.after(0, self._append_log, line.strip())
                else:
                    break
            except Exception as e:
                self._append_log(f"Log reader error: {e}", "ERROR")
                break

        if self.server_process:
            returncode = self.server_process.poll()
            if returncode is not None and returncode != 0:
                self.root.after(0, self._append_log,
                              f"Server process exited with code {returncode}", "ERROR")

    def _append_log(self, line, tag=None):
        """Append log line to text widget (called from main thread)."""
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')

        self.log_text.config(state="normal")

        # Auto-detect log level if not specified
        if tag is None:
            if "ERROR" in line or "error" in line.lower() or "Exception" in line or "Traceback" in line:
                tag = "ERROR"
            elif "WARNING" in line or "warning" in line.lower():
                tag = "WARNING"
            elif "INFO" in line or "Running on" in line or "Uvicorn running" in line:
                tag = "INFO"
            elif "200 GET" in line or "200 POST" in line or "GET /" in line:
                tag = "SUCCESS"
            elif "Address already in use" in line:
                tag = "ERROR"
                self.root.after(0, lambda: messagebox.showerror(
                    "Port Error",
                    f"Port {self.port} is already in use.\n"
                    "Please close other applications using this port."
                ))

        # Add timestamp
        timestamp = time.strftime("[%H:%M:%S] ")

        if tag:
            self.log_text.insert("end", timestamp + line + "\n", tag)
        else:
            self.log_text.insert("end", timestamp + line + "\n")

        self.log_text.see("end")

        self.log_text.config(state="disabled")

        # Limit log size (keep last 1000 lines)
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > 1000:
            self.log_text.config(state="normal")
            self.log_text.delete('1.0', '500.0')
            self.log_text.config(state="disabled")

    def clear_log(self):
        """Clear log viewer."""
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state="disabled")
        self._append_log("Log cleared")

    def open_browser(self):
        """Open default browser."""
        if not self.server_running:
            return

        try:
            webbrowser.open(f'http://localhost:{self.port}')
        except Exception as e:
            messagebox.showerror("Browser Error",
                               f"Could not open browser:\n{e}")

    def quit_app(self):
        """Quit application."""
        if self.server_running:
            result = messagebox.askyesno("Quit",
                                        "Server is still running.\n\n"
                                        "Are you sure you want to quit?")
            if not result:
                return

            self.server_running = False

        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=2)
            except:
                try:
                    self.server_process.kill()
                except:
                    pass

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _update_status(self):
        """Update UI based on server status."""
        if self.server_running:
            self.browser_btn.config(state="normal")
            self.start_btn.config(state="disabled", relief="sunken")
            self.stop_btn.config(state="normal", relief="raised")
            # Show running package in header
            pkg = self._get_selected_pkg()
            if pkg:
                self.header_pkg_label.config(
                    text=f"\u25b6 {pkg['name']} v{pkg['version']}",
                    fg="white")
        else:
            self.browser_btn.config(state="disabled")
            can_start = self.selected_package is not None
            self.start_btn.config(state="normal" if can_start else "disabled",
                                 relief="raised")
            self.stop_btn.config(state="disabled", relief="sunken")
            # Clear header package indicator
            self.header_pkg_label.config(text="", fg="#BBDEFB")

        # Refresh listbox (handles status text + disabled state)
        self._refresh_pkg_listbox()

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="SCODA Desktop GUI")
    parser.add_argument('--scoda-path', type=str, default=None,
                        help='Path to a .scoda file to load')
    args = parser.parse_args()

    try:
        gui = ScodaDesktopGUI(scoda_path=args.scoda_path)
        gui.run()
    except Exception as e:
        import traceback
        print("GUI Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
