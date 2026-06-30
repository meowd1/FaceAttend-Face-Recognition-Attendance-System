# 🎓 FaceAttend — Face Recognition Attendance System

A **web-based** Face Recognition Attendance System built with Python + Flask.  
Open it in your browser, register students, train the model, and take live attendance — all from `http://localhost:5000`.

---

## ✨ Features

- 🌐 **Browser-based UI** — No desktop app needed, runs at `http://localhost:5000`
- 👤 **Student Registration** — Capture 20 webcam photos per student via the browser
- 🧠 **Face Training** — Generate face encodings with a single click
- 📷 **Live Attendance** — Real-time MJPEG webcam stream; faces auto-recognised and attendance logged
- 📋 **Attendance Records** — Sortable/filterable table with CSV export
- 🗄️ **Dual storage** — SQLite database + CSV file, no duplicates per day
- 🌑 **Dark glassmorphism UI** — Cyan/purple gradient theme, live clock, micro-animations

---

## 📁 Project Structure

```
FaceRecognitionAttendance/
│
├── web_app.py          ← Flask app (main entry point) ✅ NEW
├── app.py              ← Old CustomTkinter desktop app (legacy)
│
├── database.py         ← SQLite helper functions
├── utils.py            ← Date/time, CSV, folder helpers
├── attendance.py       ← Face recognition logic (shared)
├── train.py            ← Training logic (shared)
├── register.py         ← Registration logic (legacy desktop)
│
├── templates/          ← Jinja2 HTML templates
│   ├── base.html       ← Sidebar layout
│   ├── index.html      ← Dashboard
│   ├── register.html   ← Register student
│   ├── train.html      ← Train faces
│   ├── attendance.html ← Live attendance
│   └── records.html    ← View records
│
├── static/
│   ├── style.css       ← Global dark theme CSS
│   └── app.js          ← Shared JS (live clock)
│
├── images/             ← Auto-created: student webcam photos
├── models/             ← Auto-created: face encodings (encodings.pkl)
├── database/           ← Auto-created: SQLite DB
├── attendance/         ← Auto-created: CSV attendance file
│
└── requirements.txt
```

---

## 💻 Installation

### Prerequisites

- **Python 3.11 or higher** (tested on Python 3.13 with Miniconda)
- A working **webcam**
- Windows / Linux / macOS

---

### Step 1 — Clone or Download the Project

```bash
# Clone
git clone https://github.com/yourname/FaceRecognitionAttendance.git
cd FaceRecognitionAttendance

# OR simply download and extract the ZIP
```

---

### Step 2 — Install `dlib` (Windows — important)

`dlib` requires pre-compiled binaries on Windows. Use **conda**:

```bash
conda install -c conda-forge dlib -y
```

> ⚠️ **Do NOT use `pip install dlib` on Windows** without Visual C++ Build Tools installed — it will fail to compile.
>
> If you don't have conda, install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) first.

---

### Step 3 — Install Python Dependencies

```bash
pip install flask face_recognition customtkinter opencv-python numpy pandas Pillow
```

All packages in one command. `dlib` is already installed via conda from Step 2.

---

### Step 4 — Run the Web App

```bash
python web_app.py
```

You will see:

```
  [*] FaceAttend Web App
  ---------------------------------
  Running at:  http://localhost:5000
  Press CTRL+C to stop

 * Running on http://127.0.0.1:5000
```

Open your browser and go to **http://localhost:5000** 🎉

---

## 📖 How to Use

### 1. Register a Student

1. Click **Register Student** in the sidebar.
2. Enter the **Student Name** and **Roll Number**.
3. Click **Save & Capture Face Images**.
4. The webcam opens server-side — look directly at the camera.
5. **20 images** are captured automatically (progress bar updates live).
6. ✅ Success message appears when done.

---

### 2. Train Face Encodings

1. Click **Train Faces** in the sidebar.
2. Click **Start Training**.
3. Progress bar fills as each student's images are processed.
4. Wait for **Training Complete** — this creates `models/encodings.pkl`.
5. You only need to re-train when new students are added.

---

### 3. Take Live Attendance

1. Click **Live Attendance** in the sidebar.
2. Click **▶ Start Attendance**.
3. The live webcam feed appears in the browser.
4. Students walk up to the camera — faces are recognised automatically:
   - 🟢 **Green box** = Known student → Attendance marked
   - 🔵 **Blue box** = Unknown face
5. The **Today's Log** panel on the right updates in real time.
6. Click **⏹ Stop** to end the session.

> Attendance is **duplicate-protected** — each student is marked only once per day.

---

### 4. View Attendance Records

1. Click **View Records** in the sidebar.
2. Use the **search box** to filter by name or roll number.
3. Use the **date picker** to filter by a specific date.
4. Click any column header to sort.
5. Click **⬇ Export CSV** to download all records.

---

## 🗃️ Data Storage

| Type | Location | Details |
|---|---|---|
| SQLite DB | `database/attendance.db` | Students + attendance records |
| CSV | `attendance/attendance.csv` | Appended on every new mark |
| Face images | `images/<Student_Name>/` | 20 JPEGs per student |
| Encodings | `models/encodings.pkl` | Generated during training |

---

## 🐛 Troubleshooting

### `dlib` fails to install on Windows

Use conda as described in Step 2:
```bash
conda install -c conda-forge dlib -y
```

### Webcam not detected

- Ensure no other application is using the webcam (Teams, Zoom, etc.)
- Try a different webcam index in `web_app.py`:
  ```python
  cap = cv2.VideoCapture(1)  # Change 0 → 1 or 2
  ```

### `ModuleNotFoundError: No module named 'face_recognition'`

```bash
pip install face_recognition
```

### Port 5000 already in use

Change the port in `web_app.py`:
```python
app.run(debug=False, threaded=True, host="0.0.0.0", port=5001)
```
Then access at `http://localhost:5001`.

### UnicodeEncodeError on Windows console

This is a cosmetic issue with emoji in print statements and does not affect the app. The fix is already applied in `web_app.py`.

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard |
| `GET` | `/register` | Registration page |
| `POST` | `/api/register` | Save student + start capture |
| `GET` | `/api/register/status` | Poll capture progress |
| `GET` | `/train` | Training page |
| `POST` | `/api/train` | Start training |
| `GET` | `/api/train/status` | Poll training progress |
| `GET` | `/attendance` | Live attendance page |
| `POST` | `/api/attendance/start` | Start webcam session |
| `POST` | `/api/attendance/stop` | Stop webcam session |
| `GET` | `/api/attendance/status` | Poll attendance log |
| `GET` | `/video_feed` | MJPEG webcam stream |
| `GET` | `/records` | Records page |
| `GET` | `/api/records` | JSON attendance data |
| `GET` | `/api/students` | JSON student list |
| `GET` | `/api/stats` | JSON dashboard stats |
| `GET` | `/api/export_csv` | Download CSV |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ + Flask 3.x |
| Face Recognition | `face_recognition` (dlib-based) |
| Webcam | OpenCV (`cv2`) — server-side |
| Video Stream | MJPEG over HTTP (`/video_feed`) |
| Frontend | Vanilla HTML + CSS + JS |
| Styling | Dark glassmorphism, Inter font, CSS animations |
| Database | SQLite (via `sqlite3`) |
| Export | CSV via Python `csv` module |

---

## 📝 License

MIT License — free to use and modify.
