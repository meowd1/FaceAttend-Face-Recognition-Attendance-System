"""
register.py
-----------
Face Registration Module.

Provides the RegisterWindow class that opens a form for the teacher
to enter student details and then captures 20 face images via webcam.
Images are saved to images/<Student_Name>/ and student is stored in DB.
"""

import os
import cv2
import customtkinter as ctk
from tkinter import messagebox
import database
import utils


class RegisterWindow(ctk.CTkToplevel):
    """
    A modal window for registering a new student.
    Collects student name + roll number, then opens webcam
    to capture 20 face images automatically.
    """

    def __init__(self, parent, refresh_callback=None):
        super().__init__(parent)

        self.title("Register New Student")
        self.geometry("480x380")
        self.resizable(False, False)
        self.grab_set()           # Make this window modal
        self.focus_force()

        # Called after successful registration to refresh home stats
        self.refresh_callback = refresh_callback

        self._build_ui()

    # ──────────────────────────────────────────
    #  UI Construction
    # ──────────────────────────────────────────

    def _build_ui(self):
        """Builds all the widgets for the registration form."""

        # ── Title Label ──
        ctk.CTkLabel(
            self,
            text="Student Registration",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#1E90FF",
        ).pack(pady=(28, 8))

        ctk.CTkLabel(
            self,
            text="Fill in the details below and capture face images",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 20))

        # ── Form Frame ──
        form_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        form_frame.pack(padx=40, fill="x")

        # Student Name
        ctk.CTkLabel(
            form_frame,
            text="Student Name:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.name_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="e.g.  Rahul Sharma",
            height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self.name_entry.pack(fill="x", pady=(0, 14))

        # Roll Number
        ctk.CTkLabel(
            form_frame,
            text="Roll Number:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.roll_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="e.g.  CS2024001",
            height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self.roll_entry.pack(fill="x", pady=(0, 20))

        # ── Status Label ──
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="#FFA500",
        )
        self.status_label.pack()

        # ── Save & Capture Button ──
        ctk.CTkButton(
            self,
            text="💾  Save & Capture Face Images",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1E90FF",
            hover_color="#1565C0",
            corner_radius=10,
            command=self._on_save_clicked,
        ).pack(padx=40, pady=(10, 6), fill="x")

        # ── Cancel Button ──
        ctk.CTkButton(
            self,
            text="Cancel",
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=1,
            border_color="gray",
            hover_color="#2A2A2A",
            corner_radius=10,
            command=self.destroy,
        ).pack(padx=40, pady=(0, 20), fill="x")

    # ──────────────────────────────────────────
    #  Logic
    # ──────────────────────────────────────────

    def _on_save_clicked(self):
        """Validates inputs, saves to DB, then starts face capture."""
        student_name = self.name_entry.get().strip()
        roll_number  = self.roll_entry.get().strip()

        # ── Validate ──
        if not student_name:
            messagebox.showerror("Validation Error", "Student Name cannot be empty.", parent=self)
            return

        if not roll_number:
            messagebox.showerror("Validation Error", "Roll Number cannot be empty.", parent=self)
            return

        # ── Save to Database ──
        saved = database.add_student(student_name, roll_number)
        if not saved:
            messagebox.showerror(
                "Duplicate Roll Number",
                f"Roll Number '{roll_number}' is already registered.\n"
                "Please use a unique roll number.",
                parent=self,
            )
            return

        # ── Start Face Capture ──
        self.status_label.configure(
            text="📷  Opening webcam... Please look at the camera.",
            text_color="#FFA500",
        )
        self.update()  # Force UI refresh before blocking call

        success = self._capture_face_images(student_name)

        if success:
            if self.refresh_callback:
                self.refresh_callback()
            messagebox.showinfo(
                "Registration Successful",
                f"✅  {student_name} has been registered successfully!\n"
                "20 face images captured and saved.",
                parent=self,
            )
            self.destroy()

    def _capture_face_images(self, student_name: str) -> bool:
        """
        Opens the webcam and captures exactly 20 face images.
        Draws a rectangle around the detected face during capture.
        Saves images to images/<Student_Name>/ folder.

        Parameters:
            student_name (str): Used to name the storage folder.

        Returns:
            True if 20 images were captured, False on error.
        """
        image_folder = utils.get_student_image_folder(student_name)

        # Load OpenCV's built-in face detector
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        cap = cv2.VideoCapture(0)  # 0 = default webcam

        if not cap.isOpened():
            messagebox.showerror(
                "Webcam Error",
                "Could not open the webcam.\n"
                "Please check that it is connected and not in use by another application.",
                parent=self,
            )
            return False

        captured_count = 0
        total_images   = 20
        skip_frames    = 3   # Capture every 3rd frame to get varied images
        frame_counter  = 0

        while captured_count < total_images:
            ret, frame = cap.read()

            if not ret:
                break

            frame_counter += 1

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces in the frame
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80),
            )

            # Draw rectangles around detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 2)

            # Only capture if exactly one face is detected
            if len(faces) == 1 and frame_counter % skip_frames == 0:
                captured_count += 1
                img_path = os.path.join(image_folder, f"img_{captured_count:02d}.jpg")
                cv2.imwrite(img_path, frame)

            # Overlay progress text on the frame
            cv2.putText(
                frame,
                f"Capturing: {captured_count}/{total_images}  |  Press Q to cancel",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
            )

            cv2.imshow("Face Capture — Keep your face in view", frame)

            # Allow user to cancel by pressing Q
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()

        if captured_count < total_images:
            messagebox.showwarning(
                "Capture Incomplete",
                f"Only {captured_count} images were captured (need {total_images}).\n"
                "Please try again, ensuring your face is clearly visible.",
                parent=self,
            )
            return False

        return True
