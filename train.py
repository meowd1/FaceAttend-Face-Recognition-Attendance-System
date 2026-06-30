"""
train.py
--------
Face Training Module.

Reads all student images from the images/ folder,
generates face encodings using the face_recognition library,
and saves them to models/encodings.pkl.

Provides the TrainWindow class for displaying progress during training.
"""

import os
import pickle
import threading
import face_recognition
import customtkinter as ctk
from tkinter import messagebox
import utils


class TrainWindow(ctk.CTkToplevel):
    """
    A modal window that trains face encodings from stored student images.
    Shows a progress bar and status messages during training.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Train Face Encodings")
        self.geometry("500x320")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()

        self._build_ui()

        # Start training automatically in a background thread
        # so the UI remains responsive
        threading.Thread(target=self._run_training, daemon=True).start()

    # ──────────────────────────────────────────
    #  UI Construction
    # ──────────────────────────────────────────

    def _build_ui(self):
        """Builds the training progress UI."""

        ctk.CTkLabel(
            self,
            text="Training Face Encodings",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#1E90FF",
        ).pack(pady=(30, 6))

        ctk.CTkLabel(
            self,
            text="Reading images and generating encodings…",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 20))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=400,
            height=18,
            corner_radius=8,
            fg_color="#2A2A2A",
            progress_color="#1E90FF",
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 16))

        # Current file label
        self.file_label = ctk.CTkLabel(
            self,
            text="Initializing…",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.file_label.pack()

        # Student count label
        self.count_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#AAAAAA",
        )
        self.count_label.pack(pady=(4, 0))

        # Result label (shown after completion)
        self.result_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.result_label.pack(pady=(16, 0))

        # Close button (disabled until training is done)
        self.close_btn = ctk.CTkButton(
            self,
            text="Close",
            state="disabled",
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#1E90FF",
            hover_color="#1565C0",
            corner_radius=10,
            command=self.destroy,
        )
        self.close_btn.pack(pady=(20, 0), padx=60, fill="x")

    # ──────────────────────────────────────────
    #  Training Logic
    # ──────────────────────────────────────────

    def _run_training(self):
        """
        Iterates over all student image folders, generates face encodings,
        and saves them to models/encodings.pkl.
        Runs in a background thread to keep the GUI responsive.
        """
        images_dir = utils.IMAGES_DIR

        # Make sure the images folder exists
        if not os.path.isdir(images_dir):
            self._show_error("The 'images/' folder does not exist.\nPlease register students first.")
            return

        # Collect all student subfolders
        student_folders = [
            f for f in os.listdir(images_dir)
            if os.path.isdir(os.path.join(images_dir, f))
        ]

        if not student_folders:
            self._show_error("No student folders found in 'images/'.\nPlease register at least one student.")
            return

        known_encodings = []  # List of face encoding arrays
        known_names     = []  # Corresponding student folder names (used as labels)

        total_students  = len(student_folders)
        processed       = 0

        for folder_name in student_folders:
            folder_path = os.path.join(images_dir, folder_name)

            # Update UI — show which student is being processed
            self._update_status(
                f"Processing: {folder_name.replace('_', ' ')}",
                processed / total_students,
                f"Student {processed + 1} of {total_students}",
            )

            # Read each image file in the student's folder
            image_files = [
                img for img in os.listdir(folder_path)
                if img.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            for img_file in image_files:
                img_path = os.path.join(folder_path, img_file)

                try:
                    # Load image using face_recognition (returns RGB array)
                    image = face_recognition.load_image_file(img_path)

                    # Generate encodings for all faces in the image
                    encodings = face_recognition.face_encodings(image)

                    if encodings:
                        # Take the first face found (should be only one per image)
                        known_encodings.append(encodings[0])
                        known_names.append(folder_name)

                except Exception as e:
                    print(f"[Train] Skipping {img_path}: {e}")

            processed += 1

        if not known_encodings:
            self._show_error(
                "No valid face encodings could be generated.\n"
                "Please ensure student images contain clearly visible faces."
            )
            return

        # Save encodings to pickle file
        encodings_data = {
            "encodings": known_encodings,
            "names":     known_names,
        }

        try:
            with open(utils.ENCODINGS_FILE, "wb") as f:
                pickle.dump(encodings_data, f)
        except Exception as e:
            self._show_error(f"Failed to save encodings file:\n{e}")
            return

        # Training complete — update UI on the main thread
        self.after(0, self._training_complete, total_students, len(known_encodings))

    # ──────────────────────────────────────────
    #  UI Update Helpers (thread-safe via after())
    # ──────────────────────────────────────────

    def _update_status(self, file_text: str, progress: float, count_text: str):
        """Thread-safe UI update during training."""
        self.after(0, lambda: self.file_label.configure(text=file_text))
        self.after(0, lambda: self.progress_bar.set(progress))
        self.after(0, lambda: self.count_label.configure(text=count_text))

    def _training_complete(self, total_students: int, total_encodings: int):
        """Called on the main thread when training finishes successfully."""
        self.progress_bar.set(1.0)
        self.file_label.configure(text="All students processed ✓", text_color="#00CC66")
        self.count_label.configure(
            text=f"{total_students} students  |  {total_encodings} encodings saved"
        )
        self.result_label.configure(
            text="✅  Training Completed Successfully!",
            text_color="#00CC66",
        )
        self.close_btn.configure(state="normal")

    def _show_error(self, message: str):
        """Thread-safe error display."""
        def _do():
            self.result_label.configure(
                text="❌  Training Failed",
                text_color="#FF4444",
            )
            self.file_label.configure(text=message, text_color="#FF4444")
            self.close_btn.configure(state="normal")
            messagebox.showerror("Training Error", message, parent=self)

        self.after(0, _do)
