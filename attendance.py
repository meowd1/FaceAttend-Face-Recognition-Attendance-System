"""
attendance.py
-------------
Face Recognition & Attendance Marking Module.

Opens the webcam, recognizes faces in real time using the stored
encodings, and marks attendance in SQLite + CSV for recognized students.
Prevents duplicate attendance entries for the same day.
"""

import os
import pickle
import cv2
import face_recognition
import numpy as np
from tkinter import messagebox
import database
import utils


# Minimum confidence threshold for accepting a face match
# Lower distance = better match (face_recognition uses L2 distance)
RECOGNITION_THRESHOLD = 0.50   # distances below this are considered a match


def load_encodings() -> dict | None:
    """
    Loads the saved face encodings from models/encodings.pkl.

    Returns:
        A dict with 'encodings' and 'names' lists, or None if file not found.
    """
    if not os.path.isfile(utils.ENCODINGS_FILE):
        return None

    with open(utils.ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    return data


def start_attendance_session(parent_window=None):
    """
    Main function that starts the webcam-based face recognition session.
    Called when the user clicks 'Start Attendance' in the home window.

    Parameters:
        parent_window: The parent CTk window (used for error dialogs).
    """

    # ── Load encodings ──
    encodings_data = load_encodings()

    if encodings_data is None:
        messagebox.showerror(
            "Model Not Found",
            "No trained model found.\n"
            "Please click 'Train Faces' first to generate encodings.",
            parent=parent_window,
        )
        return

    known_encodings = encodings_data["encodings"]
    known_names     = encodings_data["names"]      # These are folder names (e.g. "Rahul_Sharma")

    if not known_encodings:
        messagebox.showerror(
            "Empty Model",
            "The encodings file is empty.\n"
            "Please re-train the model after registering students.",
            parent=parent_window,
        )
        return

    # ── Open webcam ──
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror(
            "Webcam Error",
            "Could not open the webcam.\n"
            "Please check that it is connected and not in use.",
            parent=parent_window,
        )
        return

    # A set to avoid repeated "Already Marked" console spam in one session
    already_notified = set()

    print("\n[Attendance] Session started. Press Q to stop.\n")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("[Attendance] Could not read frame from webcam.")
            break

        # ── Resize frame for faster processing ──
        # We process a small frame but display the original
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small   = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # ── Detect faces and generate encodings ──
        face_locations  = face_recognition.face_locations(rgb_small)
        face_encodings  = face_recognition.face_encodings(rgb_small, face_locations)

        for face_encoding, face_location in zip(face_encodings, face_locations):

            # Compare against all known encodings
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_idx = int(np.argmin(face_distances))
            best_distance  = face_distances[best_match_idx]

            # Scale face location back to original frame size
            top, right, bottom, left = [coord * 2 for coord in face_location]

            if best_distance < RECOGNITION_THRESHOLD:
                # ── Known face ──
                folder_name    = known_names[best_match_idx]
                display_name   = folder_name.replace("_", " ")   # e.g. "Rahul Sharma"
                confidence_pct = int((1 - best_distance) * 100)  # Convert distance to %

                # Look up roll number from the database
                student = _get_student_by_name_folder(folder_name)
                roll_number = student["roll"] if student else "N/A"

                # ── Draw green rectangle ──
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 200, 50), 2)

                # ── Display name, roll, confidence ──
                _draw_label(frame, left, top, bottom, display_name, roll_number, confidence_pct)

                # ── Mark attendance ──
                today = utils.get_today_date()
                now   = utils.get_current_time()

                marked = database.mark_attendance(display_name, roll_number, today, now)

                if marked:
                    # First time today — save to CSV and log
                    utils.append_to_csv(display_name, roll_number, today, now)
                    print(f"[Attendance] ✅  Marked: {display_name} ({roll_number}) at {now}")

                else:
                    # Already marked — notify once per session
                    if roll_number not in already_notified:
                        already_notified.add(roll_number)
                        print(f"[Attendance] ℹ️   Already marked today: {display_name}")

                    # Show "Already Marked" overlay on frame
                    cv2.putText(
                        frame,
                        "Attendance Already Marked",
                        (left, top - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 165, 255),
                        1,
                    )

            else:
                # ── Unknown face ──
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 220), 2)

                cv2.putText(
                    frame,
                    "Unknown",
                    (left + 4, bottom + 18),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 220),
                    2,
                )

        # ── HUD overlay ──
        date_str, time_str = utils.get_current_datetime_display()
        cv2.putText(
            frame,
            f"{date_str}  |  {time_str}",
            (10, frame.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (180, 180, 180),
            1,
        )
        cv2.putText(
            frame,
            "Press Q to stop attendance",
            (10, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (200, 200, 200),
            1,
        )

        cv2.imshow("Face Recognition Attendance — Live", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n[Attendance] Session ended.\n")


# ──────────────────────────────────────────────
#  Private Helper Functions
# ──────────────────────────────────────────────

def _draw_label(frame, left: int, top: int, bottom: int,
                name: str, roll: str, confidence: int):
    """
    Draws a small info box below the face rectangle showing
    the student name, roll number, and recognition confidence.
    """
    label_lines = [
        f"{name}",
        f"Roll: {roll}",
        f"Confidence: {confidence}%",
    ]

    y_start = bottom + 4
    for i, line in enumerate(label_lines):
        y = y_start + (i * 18)
        cv2.putText(
            frame,
            line,
            (left + 2, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (0, 230, 80),
            1,
        )


def _get_student_by_name_folder(folder_name: str):
    """
    Tries to look up a student in the DB using the folder name.
    The folder name uses underscores (e.g. 'Rahul_Sharma'),
    so we convert to space-separated before querying.

    Returns:
        A sqlite3.Row or None.
    """
    display_name = folder_name.replace("_", " ")
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM students WHERE name = ?",
        (display_name,)
    )
    student = cursor.fetchone()
    conn.close()
    return student
