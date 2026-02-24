#!/usr/bin/env python3
"""
SCODA Desktop — GUI Control Panel

Provides a Docker Desktop-style graphical interface to select a package
and control the web server.
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import logging
import threading
import webbrowser
import os
import sys
import time
import subprocess

from scoda_engine import __version__
import scoda_engine_core as scoda_package


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

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Enable drag-and-drop if tkinterdnd2 is available
        self._setup_dnd()

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

        # Open .scoda file button
        self.open_btn = tk.Button(control_frame, text="Open .scoda File...", width=26,
                                  command=self._open_scoda_file,
                                  relief="raised", bd=2)
        self.open_btn.pack(pady=3)

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

    def _open_scoda_file(self):
        """Open a file dialog to select and load a .scoda file."""
        if self.server_running:
            self._append_log("Stop server before loading a new package", "WARNING")
            return

        path = filedialog.askopenfilename(
            title="Open .scoda Package",
            filetypes=[("SCODA packages", "*.scoda"), ("All files", "*.*")],
        )
        if path:
            self._load_scoda_from_path(path)

    def _load_scoda_from_path(self, path):
        """Load a .scoda file from an arbitrary path into the registry."""
        try:
            name = self.registry.register_path(path)
            self._external_scoda_paths[name] = os.path.abspath(path)
            self.packages = self.registry.list_packages()
            self._refresh_pkg_listbox()

            # Select the newly loaded package
            self.selected_package = name
            for i, pkg in enumerate(self.packages):
                if pkg['name'] == name:
                    self.pkg_listbox.selection_clear(0, "end")
                    self.pkg_listbox.selection_set(i)
                    break
            self._update_pkg_info()
            self._update_status()
            self._append_log(f"Loaded: {name} from {path}", "SUCCESS")
        except (FileNotFoundError, ValueError) as e:
            self._append_log(f"ERROR: Failed to load {path}: {e}", "ERROR")
            messagebox.showerror("Load Error", f"Could not load package:\n{e}")

    def _setup_dnd(self):
        """Enable drag-and-drop for .scoda files if tkinterdnd2 is available."""
        try:
            import tkinterdnd2
            self.root.drop_target_register(tkinterdnd2.DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
            self._append_log("Drag-and-drop enabled")
        except (ImportError, Exception):
            pass  # tkinterdnd2 not installed — silently skip

    def _on_drop(self, event):
        """Handle drag-and-drop of .scoda files."""
        path = event.data.strip()
        # tkinterdnd2 wraps paths with spaces in braces: {/path/with spaces/file.scoda}
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        if path.lower().endswith('.scoda'):
            self._load_scoda_from_path(path)
        else:
            self._append_log(f"Dropped file is not a .scoda package: {path}", "WARNING")

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
