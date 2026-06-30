"""
database.py
-----------
Handles all SQLite database operations.
Creates the database, tables, and provides helper functions
for inserting and querying student and attendance data.
"""

import sqlite3
import os

# Path to the SQLite database file
DB_PATH = os.path.join("database", "attendance.db")


def get_connection():
    """
    Returns a connection to the SQLite database.
    Ensures the database file exists before connecting.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


def create_tables():
    """
    Creates the 'students' and 'attendance' tables if they don't already exist.
    This is called automatically when the app starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create the students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            roll    TEXT NOT NULL UNIQUE
        )
    """)

    # Create the attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            roll    TEXT NOT NULL,
            date    TEXT NOT NULL,
            time    TEXT NOT NULL,
            status  TEXT NOT NULL DEFAULT 'Present'
        )
    """)

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
#  Student Functions
# ──────────────────────────────────────────────

def add_student(name: str, roll: str) -> bool:
    """
    Inserts a new student into the students table.

    Parameters:
        name (str): Student's full name.
        roll (str): Student's roll number (must be unique).

    Returns:
        True if inserted successfully, False if roll number already exists.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, roll) VALUES (?, ?)",
            (name, roll)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Roll number already exists
        return False


def get_all_students() -> list:
    """
    Fetches all students from the database.

    Returns:
        A list of sqlite3.Row objects with 'id', 'name', 'roll' fields.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY id ASC")
    students = cursor.fetchall()
    conn.close()
    return students


def get_student_by_roll(roll: str):
    """
    Fetches a single student record by roll number.

    Parameters:
        roll (str): The student's roll number.

    Returns:
        A sqlite3.Row object or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE roll = ?", (roll,))
    student = cursor.fetchone()
    conn.close()
    return student


def count_students() -> int:
    """
    Returns the total number of registered students.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ──────────────────────────────────────────────
#  Attendance Functions
# ──────────────────────────────────────────────

def mark_attendance(name: str, roll: str, date: str, time: str) -> bool:
    """
    Marks attendance for a student on a given date.
    Prevents duplicate entries for the same student on the same day.

    Parameters:
        name (str): Student's full name.
        roll (str): Student's roll number.
        date (str): Date string in 'YYYY-MM-DD' format.
        time (str): Time string in 'HH:MM:SS' format.

    Returns:
        True if attendance was marked, False if already marked today.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if attendance is already marked for today
    cursor.execute(
        "SELECT id FROM attendance WHERE roll = ? AND date = ?",
        (roll, date)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return False  # Already marked

    # Insert new attendance record
    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time, status) VALUES (?, ?, ?, ?, ?)",
        (name, roll, date, time, "Present")
    )
    conn.commit()
    conn.close()
    return True


def get_all_attendance() -> list:
    """
    Fetches all attendance records from the database, newest first.

    Returns:
        A list of sqlite3.Row objects.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM attendance ORDER BY date DESC, time DESC"
    )
    records = cursor.fetchall()
    conn.close()
    return records


def is_attendance_marked_today(roll: str, date: str) -> bool:
    """
    Checks if a student's attendance is already marked for today.

    Parameters:
        roll (str): Student's roll number.
        date (str): Today's date string.

    Returns:
        True if already marked, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM attendance WHERE roll = ? AND date = ?",
        (roll, date)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None
