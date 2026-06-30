"""
utils.py
--------
Utility / helper functions used across the project.
Handles folder creation, CSV export, and date/time helpers.
"""

import os
import csv
import datetime
import database


# ──────────────────────────────────────────────
#  Folder Setup
# ──────────────────────────────────────────────

def create_required_folders():
    """
    Creates all required directories on first run if they don't exist.
    Called once when the application starts.
    """
    folders = [
        "database",
        "images",
        "models",
        "attendance",
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


# ──────────────────────────────────────────────
#  Date / Time Helpers
# ──────────────────────────────────────────────

def get_today_date() -> str:
    """Returns today's date as 'YYYY-MM-DD'."""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_current_time() -> str:
    """Returns the current time as 'HH:MM:SS'."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def get_current_datetime_display() -> tuple:
    """
    Returns a tuple of (date_string, time_string) formatted for display.
    Example: ('Sunday, 29 June 2026', '08:10:07 PM')
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M:%S %p")
    return date_str, time_str


# ──────────────────────────────────────────────
#  CSV Export
# ──────────────────────────────────────────────

CSV_PATH = os.path.join("attendance", "attendance.csv")

CSV_HEADERS = ["Name", "Roll Number", "Date", "Time", "Status"]


def append_to_csv(name: str, roll: str, date: str, time: str, status: str = "Present"):
    """
    Appends a single attendance record to the CSV file.
    Creates the file with headers if it doesn't exist yet.

    Parameters:
        name   (str): Student name.
        roll   (str): Roll number.
        date   (str): Date string.
        time   (str): Time string.
        status (str): Attendance status (default 'Present').
    """
    file_exists = os.path.isfile(CSV_PATH)

    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)

        # Write header only if the file is new
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "Name":        name,
            "Roll Number": roll,
            "Date":        date,
            "Time":        time,
            "Status":      status,
        })


def export_all_attendance_to_csv(export_path: str) -> bool:
    """
    Exports all attendance records from the SQLite database into a CSV file.
    Used by the 'Export CSV' button in the View Attendance window.

    Parameters:
        export_path (str): Full file path where the CSV should be saved.

    Returns:
        True if export succeeded, False otherwise.
    """
    try:
        records = database.get_all_attendance()

        with open(export_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()

            for record in records:
                writer.writerow({
                    "Name":        record["name"],
                    "Roll Number": record["roll"],
                    "Date":        record["date"],
                    "Time":        record["time"],
                    "Status":      record["status"],
                })
        return True
    except Exception as e:
        print(f"[CSV Export Error] {e}")
        return False


# ──────────────────────────────────────────────
#  Image / Model Paths
# ──────────────────────────────────────────────

IMAGES_DIR  = "images"
MODELS_DIR  = "models"
ENCODINGS_FILE = os.path.join(MODELS_DIR, "encodings.pkl")


def get_student_image_folder(student_name: str) -> str:
    """
    Returns (and creates) the image folder for a given student.

    Parameters:
        student_name (str): The student's name used as the folder name.

    Returns:
        Absolute path string to the student's image folder.
    """
    # Replace spaces with underscores to keep folder names clean
    safe_name = student_name.strip().replace(" ", "_")
    folder = os.path.join(IMAGES_DIR, safe_name)
    os.makedirs(folder, exist_ok=True)
    return folder
