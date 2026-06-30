"""
app.py
------
Main application entry point.

Builds the home window using CustomTkinter and connects all modules:
  - register.py   → Register Student
  - train.py      → Train Faces
  - attendance.py → Start Attendance
  - view_attendance (defined here) → View Attendance table
"""

import threading
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk

import database
import utils
import register
import train
import attendance


# ──────────────────────────────────────────────
#  CustomTkinter global settings
# ──────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HomeWindow(ctk.CTk):
    """
    The main home window of the Face Recognition Attendance System.
    Displays:
      - App title and branding
      - Current date and time (live)
      - Total registered students
      - Navigation buttons for all features
    """

    def __init__(self):
        super().__init__()

        self.title("Face Recognition Attendance System")
        self.geometry("860x600")
        self.minsize(860, 600)
        self.resizable(True, True)

        # Center the window on screen
        self._center_window(860, 600)

        self._build_ui()
        self._refresh_stats()
        self._start_clock()

    # ──────────────────────────────────────────
    #  Window Helpers
    # ──────────────────────────────────────────

    def _center_window(self, width: int, height: int):
        """Centers the window on the screen."""
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ──────────────────────────────────────────
    #  UI Construction
    # ──────────────────────────────────────────

    def _build_ui(self):
        """Builds the complete home window layout."""

        # ────────────────────────────────────────
        #  Left Sidebar
        # ────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=0,
            fg_color="#0D1B2A",
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # App logo / icon text
        ctk.CTkLabel(
            self.sidebar,
            text="🎓",
            font=ctk.CTkFont(size=52),
        ).pack(pady=(40, 4))

        ctk.CTkLabel(
            self.sidebar,
            text="Face Attendance",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#4FC3F7",
        ).pack()

        ctk.CTkLabel(
            self.sidebar,
            text="System",
            font=ctk.CTkFont(size=13),
            text_color="#546E7A",
        ).pack(pady=(0, 30))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1E3A52").pack(fill="x", padx=20, pady=(0, 20))

        # ── Sidebar Buttons ──
        buttons = [
            ("👤  Register Student",  self._open_register),
            ("🧠  Train Faces",       self._open_train),
            ("📷  Start Attendance",  self._open_attendance),
            ("📋  View Attendance",   self._open_view_attendance),
        ]

        for text, command in buttons:
            ctk.CTkButton(
                self.sidebar,
                text=text,
                height=44,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent",
                hover_color="#1E3A52",
                anchor="w",
                corner_radius=8,
                command=command,
            ).pack(fill="x", padx=16, pady=5)

        # Spacer
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)

        # Exit button at the bottom of sidebar
        ctk.CTkButton(
            self.sidebar,
            text="🚪  Exit",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#1A1A2E",
            hover_color="#7B1010",
            corner_radius=8,
            command=self.quit,
        ).pack(fill="x", padx=16, pady=(0, 24))

        # ────────────────────────────────────────
        #  Main Content Area (right side)
        # ────────────────────────────────────────
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#0F2030")
        self.main_area.pack(side="right", fill="both", expand=True)

        # ── Header ──
        header = ctk.CTkFrame(self.main_area, corner_radius=0, fg_color="#0D1B2A", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Face Recognition Attendance System",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#4FC3F7",
        ).pack(side="left", padx=28, pady=20)

        # ── Stats Cards Row ──
        stats_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        stats_frame.pack(fill="x", padx=28, pady=(24, 0))

        # Date card
        self.date_label = self._make_stat_card(
            stats_frame,
            icon="📅",
            title="Today's Date",
            value="Loading…",
            color="#1565C0",
        )

        # Time card
        self.time_label = self._make_stat_card(
            stats_frame,
            icon="🕐",
            title="Current Time",
            value="Loading…",
            color="#006064",
        )

        # Students card
        self.students_label = self._make_stat_card(
            stats_frame,
            icon="👥",
            title="Total Students",
            value="0",
            color="#4A148C",
        )

        # ── Welcome Panel ──
        welcome_frame = ctk.CTkFrame(
            self.main_area,
            corner_radius=14,
            fg_color="#0D1B2A",
            border_width=1,
            border_color="#1E3A52",
        )
        welcome_frame.pack(fill="both", expand=True, padx=28, pady=24)

        ctk.CTkLabel(
            welcome_frame,
            text="Welcome, Teacher! 👋",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="white",
        ).pack(pady=(34, 6))

        ctk.CTkLabel(
            welcome_frame,
            text="Use the sidebar to register students, train face encodings,\nstart the live attendance session, or view records.",
            font=ctk.CTkFont(size=13),
            text_color="#78909C",
            justify="center",
        ).pack(pady=(0, 28))

        # ── Quick Action Buttons (large, in main area) ──
        btn_grid = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        btn_grid.pack()

        quick_buttons = [
            ("👤  Register Student",  "#1565C0", "#0D47A1", self._open_register),
            ("🧠  Train Faces",       "#006064", "#004D40", self._open_train),
            ("📷  Start Attendance",  "#1B5E20", "#145214", self._open_attendance),
            ("📋  View Attendance",   "#4A148C", "#380E6A", self._open_view_attendance),
        ]

        for i, (text, fg, hover, cmd) in enumerate(quick_buttons):
            col = i % 2
            row = i // 2
            ctk.CTkButton(
                btn_grid,
                text=text,
                width=190,
                height=52,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color=fg,
                hover_color=hover,
                corner_radius=12,
                command=cmd,
            ).grid(row=row, column=col, padx=10, pady=8)

    def _make_stat_card(self, parent, icon: str, title: str, value: str, color: str):
        """
        Creates and returns a small stats card widget.
        Returns the value CTkLabel so it can be updated later.
        """
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=color,
        )
        card.pack(side="left", expand=True, fill="x", padx=(0, 12))

        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=28),
        ).pack(pady=(14, 2))

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11),
            text_color="#B0BEC5",
        ).pack()

        value_lbl = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="white",
        )
        value_lbl.pack(pady=(2, 14))

        return value_lbl

    # ──────────────────────────────────────────
    #  Live Clock
    # ──────────────────────────────────────────

    def _start_clock(self):
        """Starts a recurring update that refreshes the date/time labels every second."""
        self._update_clock()

    def _update_clock(self):
        """Updates date and time labels, then schedules itself to run again in 1 second."""
        date_str, time_str = utils.get_current_datetime_display()
        self.date_label.configure(text=date_str)
        self.time_label.configure(text=time_str)
        self.after(1000, self._update_clock)

    # ──────────────────────────────────────────
    #  Stats Refresh
    # ──────────────────────────────────────────

    def _refresh_stats(self):
        """Refreshes the total student count shown on the home screen."""
        count = database.count_students()
        self.students_label.configure(text=str(count))

    # ──────────────────────────────────────────
    #  Button Handlers
    # ──────────────────────────────────────────

    def _open_register(self):
        """Opens the student registration window."""
        register.RegisterWindow(self, refresh_callback=self._refresh_stats)

    def _open_train(self):
        """Opens the face training window."""
        train.TrainWindow(self)

    def _open_attendance(self):
        """Starts the attendance session in a background thread."""
        thread = threading.Thread(
            target=attendance.start_attendance_session,
            args=(self,),
            daemon=True,
        )
        thread.start()

    def _open_view_attendance(self):
        """Opens the attendance records viewer window."""
        ViewAttendanceWindow(self)


# ══════════════════════════════════════════════
#  View Attendance Window
# ══════════════════════════════════════════════

class ViewAttendanceWindow(ctk.CTkToplevel):
    """
    Displays all attendance records in a scrollable table.
    Provides an 'Export CSV' button to save records to a file.
    """

    # Column configuration: (header_text, column_width)
    COLUMNS = [
        ("Name",        180),
        ("Roll Number", 130),
        ("Date",        120),
        ("Time",        110),
        ("Status",      90),
    ]

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Attendance Records")
        self.geometry("760x500")
        self.minsize(700, 400)
        self.grab_set()
        self.focus_force()

        self._build_ui()
        self._load_records()

    def _build_ui(self):
        """Builds the attendance table window."""

        # ── Title Bar ──
        top_bar = ctk.CTkFrame(self, corner_radius=0, fg_color="#0D1B2A", height=60)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text="📋  Attendance Records",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#4FC3F7",
        ).pack(side="left", padx=20, pady=14)

        # Export button
        ctk.CTkButton(
            top_bar,
            text="⬇  Export CSV",
            width=130,
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#1565C0",
            hover_color="#0D47A1",
            corner_radius=8,
            command=self._export_csv,
        ).pack(side="right", padx=16, pady=12)

        # ── Table using tkinter's ttk.Treeview ──
        table_frame = ctk.CTkFrame(self, corner_radius=0)
        table_frame.pack(fill="both", expand=True, padx=0, pady=0)

        import tkinter.ttk as ttk

        # Style the treeview to match dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background="#1C1C2E",
            foreground="white",
            rowheight=28,
            fieldbackground="#1C1C2E",
            font=("Segoe UI", 11),
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#0D1B2A",
            foreground="#4FC3F7",
            font=("Segoe UI", 12, "bold"),
        )
        style.map("Custom.Treeview", background=[("selected", "#1565C0")])

        col_ids = [col[0] for col in self.COLUMNS]

        self.tree = ttk.Treeview(
            table_frame,
            columns=col_ids,
            show="headings",
            style="Custom.Treeview",
        )

        for col_name, col_width in self.COLUMNS:
            self.tree.heading(col_name, text=col_name)
            self.tree.column(col_name, width=col_width, anchor="center")

        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right",  fill="y")
        self.tree.pack(fill="both", expand=True)

        # ── Bottom bar ──
        bottom_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#0D1B2A")
        bottom_bar.pack(fill="x")
        bottom_bar.pack_propagate(False)

        self.record_count_label = ctk.CTkLabel(
            bottom_bar,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#546E7A",
        )
        self.record_count_label.pack(side="left", padx=16, pady=8)

    def _load_records(self):
        """Fetches all attendance records from DB and populates the table."""
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        records = database.get_all_attendance()

        for i, rec in enumerate(records):
            # Alternate row colors for readability
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(rec["name"], rec["roll"], rec["date"], rec["time"], rec["status"]),
                tags=(tag,),
            )

        self.tree.tag_configure("even", background="#1C1C2E")
        self.tree.tag_configure("odd",  background="#222236")

        self.record_count_label.configure(text=f"Total Records: {len(records)}")

    def _export_csv(self):
        """Opens a file dialog and exports all attendance records to CSV."""
        export_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Attendance as CSV",
            initialfile="attendance_export.csv",
        )

        if not export_path:
            return  # User cancelled

        success = utils.export_all_attendance_to_csv(export_path)

        if success:
            messagebox.showinfo(
                "Export Successful",
                f"✅  Attendance records exported to:\n{export_path}",
                parent=self,
            )
        else:
            messagebox.showerror(
                "Export Failed",
                "Could not export attendance records.\nPlease try again.",
                parent=self,
            )


# ══════════════════════════════════════════════
#  Application Entry Point
# ══════════════════════════════════════════════

def main():
    """
    Initializes everything and launches the home window.
    Called when app.py is run directly.
    """
    # Step 1: Create required folders (database/, images/, models/, attendance/)
    utils.create_required_folders()

    # Step 2: Create database tables if they don't exist
    database.create_tables()

    # Step 3: Launch the main GUI window
    app = HomeWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
