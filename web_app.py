"""
web_app.py
----------
Flask-based web application entry point.
Replaces the CustomTkinter GUI with a browser-accessible interface at http://localhost:5000.

All face-recognition logic, database, and utility functions are reused unchanged.
"""

import io
import os
import csv
import json
import time
import pickle
import threading
import queue

import cv2
import numpy as np
import face_recognition as fr
from flask import (
    Flask, render_template, request, jsonify,
    Response, stream_with_context, send_file
)

import database
import utils

app = Flask(__name__)
app.secret_key = "face_attendance_secret_key_2024"

# ─────────────────────────────────────────────────────────────────────────────
#  Global State
# ─────────────────────────────────────────────────────────────────────────────

# --- Registration state ---
reg_lock = threading.Lock()
reg_state = {
    "running": False,
    "progress": 0,
    "total": 20,
    "status": "idle",   # idle | capturing | done | error
    "message": "",
}

# --- Training state ---
train_lock = threading.Lock()
train_state = {
    "running": False,
    "progress": 0.0,
    "status": "idle",   # idle | running | done | error
    "current": "",
    "message": "",
    "success": False,
}

# --- Attendance / video state ---
attendance_running = False
attendance_frame = None                 # Latest JPEG bytes
attendance_frame_lock = threading.Lock()
attendance_log_lock = threading.Lock()
attendance_log: list[dict] = []        # Recent attendance events

RECOGNITION_THRESHOLD = 0.50


# ─────────────────────────────────────────────────────────────────────────────
#  Page Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    student_count = database.count_students()
    model_exists = os.path.isfile(utils.ENCODINGS_FILE)
    today = utils.get_today_date()

    # Count today's attendance
    records = database.get_all_attendance()
    today_count = sum(1 for r in records if r["date"] == today)

    return render_template(
        "index.html",
        active="home",
        student_count=student_count,
        model_exists=model_exists,
        today_count=today_count,
    )


@app.route("/register")
def register_page():
    return render_template("register.html", active="register")


@app.route("/train")
def train_page():
    model_exists = os.path.isfile(utils.ENCODINGS_FILE)
    student_count = database.count_students()
    return render_template("train.html", active="train",
                           model_exists=model_exists,
                           student_count=student_count)


@app.route("/attendance")
def attendance_page():
    global attendance_running
    model_exists = os.path.isfile(utils.ENCODINGS_FILE)
    return render_template("attendance.html", active="attendance",
                           model_exists=model_exists,
                           attendance_running=attendance_running)


@app.route("/records")
def records_page():
    return render_template("records.html", active="records")


# ─────────────────────────────────────────────────────────────────────────────
#  API: Registration
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    roll = (data.get("roll") or "").strip()

    if not name or not roll:
        return jsonify({"success": False, "error": "Name and roll number are required"}), 400

    saved = database.add_student(name, roll)
    if not saved:
        return jsonify({"success": False,
                        "error": f"Roll number '{roll}' is already registered"}), 409

    with reg_lock:
        reg_state.update({
            "running": True,
            "progress": 0,
            "total": 20,
            "status": "capturing",
            "message": "Opening webcam…",
        })

    threading.Thread(target=_capture_face_images, args=(name,), daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/register/status")
def api_register_status():
    """Polled by the frontend every 400 ms during registration."""
    with reg_lock:
        return jsonify(dict(reg_state))


def _capture_face_images(student_name: str):
    """Background thread: captures 20 face images using the webcam."""
    image_folder = utils.get_student_image_folder(student_name)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        with reg_lock:
            reg_state.update({"status": "error", "running": False,
                               "message": "Could not open webcam. Is it connected?"})
        return

    captured, total, skip, frame_no = 0, 20, 3, 0

    with reg_lock:
        reg_state["message"] = "Look directly at the camera…"

    while captured < total:
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        if len(faces) == 1 and frame_no % skip == 0:
            captured += 1
            cv2.imwrite(os.path.join(image_folder, f"img_{captured:02d}.jpg"), frame)
            with reg_lock:
                reg_state["progress"] = captured
                reg_state["message"] = f"Captured {captured}/{total} images…"
        elif len(faces) == 0:
            with reg_lock:
                reg_state["message"] = "⚠ No face detected — please face the camera"
        elif len(faces) > 1:
            with reg_lock:
                reg_state["message"] = "⚠ Multiple faces detected — only one person should be visible"

    cap.release()

    if captured >= total:
        with reg_lock:
            reg_state.update({"status": "done", "progress": total, "running": False,
                               "message": f"✅ Done! {total} images captured successfully."})
    else:
        with reg_lock:
            reg_state.update({"status": "error", "running": False,
                               "message": f"⚠ Only {captured}/{total} images captured. Try again."})


# ─────────────────────────────────────────────────────────────────────────────
#  API: Training
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/train", methods=["POST"])
def api_train():
    with train_lock:
        if train_state["running"]:
            return jsonify({"success": False, "error": "Training already in progress"}), 409
        train_state.update({
            "running": True, "progress": 0.0, "status": "running",
            "current": "", "success": False, "message": "Initializing…",
        })

    threading.Thread(target=_run_training, daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/train/status")
def api_train_status():
    with train_lock:
        return jsonify(dict(train_state))


def _run_training():
    """Background thread: generates and saves face encodings."""
    images_dir = utils.IMAGES_DIR

    if not os.path.isdir(images_dir):
        with train_lock:
            train_state.update({"status": "error", "running": False,
                                 "message": "images/ folder not found. Register students first."})
        return

    folders = [f for f in os.listdir(images_dir)
               if os.path.isdir(os.path.join(images_dir, f))]

    if not folders:
        with train_lock:
            train_state.update({"status": "error", "running": False,
                                 "message": "No student folders found. Register at least one student."})
        return

    known_encodings, known_names = [], []
    total = len(folders)

    for i, folder_name in enumerate(folders):
        folder_path = os.path.join(images_dir, folder_name)
        display = folder_name.replace("_", " ")

        with train_lock:
            train_state.update({
                "current": display,
                "progress": i / total,
                "message": f"Processing {display}… ({i + 1}/{total})",
            })

        for img_file in os.listdir(folder_path):
            if not img_file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            try:
                image = fr.load_image_file(os.path.join(folder_path, img_file))
                encodings = fr.face_encodings(image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(folder_name)
            except Exception as e:
                print(f"[Train] Skipping {img_file}: {e}")

    if not known_encodings:
        with train_lock:
            train_state.update({"status": "error", "running": False,
                                 "message": "No valid face encodings generated. Ensure clear face images."})
        return

    try:
        with open(utils.ENCODINGS_FILE, "wb") as f:
            pickle.dump({"encodings": known_encodings, "names": known_names}, f)

        with train_lock:
            train_state.update({
                "status": "done", "running": False, "success": True, "progress": 1.0,
                "message": f"✅ Training complete! {total} students, {len(known_encodings)} encodings saved.",
            })
    except Exception as e:
        with train_lock:
            train_state.update({"status": "error", "running": False,
                                 "message": f"Failed to save encodings: {e}"})


# ─────────────────────────────────────────────────────────────────────────────
#  API: Live Attendance + Video Feed
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/attendance/start", methods=["POST"])
def api_attendance_start():
    global attendance_running

    if attendance_running:
        return jsonify({"success": False, "error": "Session already running"}), 409

    if not os.path.isfile(utils.ENCODINGS_FILE):
        return jsonify({"success": False,
                        "error": "No trained model found. Train faces first."}), 400

    attendance_running = True
    with attendance_log_lock:
        attendance_log.clear()

    threading.Thread(target=_attendance_thread, daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/attendance/stop", methods=["POST"])
def api_attendance_stop():
    global attendance_running
    attendance_running = False
    return jsonify({"success": True})


@app.route("/api/attendance/status")
def api_attendance_status():
    global attendance_running
    with attendance_log_lock:
        log = list(attendance_log[-30:])
    return jsonify({"running": attendance_running, "log": log})


@app.route("/video_feed")
def video_feed():
    return Response(
        _generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def _attendance_thread():
    """Background thread: reads webcam, runs face recognition, marks attendance."""
    global attendance_running, attendance_frame

    with open(utils.ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    known_encodings = data["encodings"]
    known_names = data["names"]

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        attendance_running = False
        return

    already_marked_today = set()

    while attendance_running:
        ret, frame = cap.read()
        if not ret:
            break

        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locs = fr.face_locations(rgb)
        face_encs = fr.face_encodings(rgb, face_locs)

        for enc, loc in zip(face_encs, face_locs):
            distances = fr.face_distance(known_encodings, enc)
            best_idx = int(np.argmin(distances))
            best_dist = distances[best_idx]

            top, right, bottom, left = [c * 2 for c in loc]

            if best_dist < RECOGNITION_THRESHOLD:
                folder_name = known_names[best_idx]
                display_name = folder_name.replace("_", " ")
                confidence = int((1 - best_dist) * 100)

                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT roll FROM students WHERE name = ?", (display_name,))
                row = cursor.fetchone()
                conn.close()
                roll = row["roll"] if row else "N/A"

                today = utils.get_today_date()
                now = utils.get_current_time()
                marked = database.mark_attendance(display_name, roll, today, now)

                if marked:
                    utils.append_to_csv(display_name, roll, today, now)
                    already_marked_today.add(roll)
                    with attendance_log_lock:
                        attendance_log.append({
                            "name": display_name,
                            "roll": roll,
                            "time": now,
                            "confidence": confidence,
                            "new": True,
                        })

                # Draw face box
                color = (0, 210, 80)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 1), (right, bottom + 55), color, cv2.FILLED)
                cv2.putText(frame, display_name, (left + 4, bottom + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 1)
                status_text = "MARKED ✓" if marked else "Already Marked"
                cv2.putText(frame, f"Roll: {roll} | {confidence}%  {status_text}",
                            (left + 4, bottom + 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (10, 10, 10), 1)
            else:
                # Unknown face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 60, 220), 2)
                cv2.rectangle(frame, (left, bottom - 1), (right, bottom + 28), (0, 60, 220), cv2.FILLED)
                cv2.putText(frame, "Unknown", (left + 4, bottom + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # HUD overlay
        date_str, time_str = utils.get_current_datetime_display()
        cv2.putText(frame, f"{date_str}  |  {time_str}",
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        ret2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ret2:
            with attendance_frame_lock:
                attendance_frame = buf.tobytes()

    cap.release()
    attendance_running = False
    with attendance_frame_lock:
        attendance_frame = None


def _generate_frames():
    """Generator: yields MJPEG frames for the /video_feed endpoint."""
    while True:
        if not attendance_running:
            # Serve a dark placeholder
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder,
                        "Click  Start Attendance  to begin",
                        (70, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (60, 60, 60), 2)
            cv2.putText(placeholder, "Camera feed will appear here",
                        (140, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
            _, buf = cv2.imencode(".jpg", placeholder)
            frame_bytes = buf.tobytes()
        else:
            with attendance_frame_lock:
                frame_bytes = attendance_frame
            if frame_bytes is None:
                time.sleep(0.03)
                continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
        time.sleep(0.033)


# ─────────────────────────────────────────────────────────────────────────────
#  API: Records
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/records")
def api_records():
    records = database.get_all_attendance()
    data = [
        {"name": r["name"], "roll": r["roll"],
         "date": r["date"], "time": r["time"], "status": r["status"]}
        for r in records
    ]
    return jsonify(data)


@app.route("/api/students")
def api_students():
    students = database.get_all_students()
    return jsonify([{"id": s["id"], "name": s["name"], "roll": s["roll"]} for s in students])


@app.route("/api/stats")
def api_stats():
    student_count = database.count_students()
    today = utils.get_today_date()
    records = database.get_all_attendance()
    today_count = sum(1 for r in records if r["date"] == today)
    model_exists = os.path.isfile(utils.ENCODINGS_FILE)
    return jsonify({
        "students": student_count,
        "today": today_count,
        "model": model_exists,
    })


@app.route("/api/export_csv")
def api_export_csv():
    records = database.get_all_attendance()
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["Name", "Roll Number", "Date", "Time", "Status"]
    )
    writer.writeheader()
    for r in records:
        writer.writerow({
            "Name": r["name"], "Roll Number": r["roll"],
            "Date": r["date"], "Time": r["time"], "Status": r["status"],
        })
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"},
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    utils.create_required_folders()
    database.create_tables()
    print("\n  [*] FaceAttend Web App")
    print("  ---------------------------------")
    print("  Running at:  http://localhost:5000")
    print("  Press CTRL+C to stop\n")
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
