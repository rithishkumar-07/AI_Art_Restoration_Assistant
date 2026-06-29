# 🎨 AI Art Restoration Assistant

AI Art Restoration Assistant is a desktop application developed using Python, OpenCV, Tkinter, Pillow, and SQLite. The system restores damaged or low-quality artworks using image processing techniques such as noise reduction, detail enhancement, and contrast enhancement.

---

## 🎯 Project Objective

The objective of this project is to restore damaged artworks and improve image quality using artificial intelligence and image processing techniques. The system provides an easy-to-use interface for artwork restoration while maintaining restoration history and performance statistics.

---

## ✨ Features

* User Registration & Login System
* Secure Password Hashing (SHA-256 + Salt)
* Artwork Upload and Restoration
* Noise Reduction using OpenCV
* Detail Enhancement using Sharpening Filter
* Quality Improvement using CLAHE
* Quality Score Calculation
* Restoration History Management
* Search Restoration Records
* Export History to CSV
* Dashboard Statistics
* Modern Dark-Themed GUI
* SQLite Database Integration

---

## 🛠 Tech Stack

### Programming Language

* Python 3.x

### Libraries

* OpenCV
* NumPy
* Pillow
* Tkinter
* SQLite3

### Database

* SQLite

### GUI Framework

* Tkinter

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/your-username/AI-Art-Restoration-Assistant.git
cd AI-Art-Restoration-Assistant
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python AI_Art_Restoration_Assistant.py
```

---

## 🚀 Usage

1. Run the application.
2. Register a new account or log in.
3. Click **Upload & Restore**.
4. Select an artwork image.
5. Wait for the restoration process to complete.
6. View the restored image and quality score.
7. Save the restored image.
8. View restoration history and export reports if required.

---

## 🔄 Restoration Pipeline

### Stage 1 – Noise Reduction

OpenCV Fast Non-Local Means Denoising

### Stage 2 – Detail Enhancement

Image Sharpening Filter

### Stage 3 – Quality Improvement

CLAHE (Contrast Limited Adaptive Histogram Equalization)

---

## 📊 Output Information

The application provides:

* File Size
* Image Dimensions
* Quality Score
* Restoration History
* Average Score
* Best Score

---

## 📸 Screenshots

### Login Page

![Login Page](screenshots/login.png)

### Dashboard

![Dashboard](screenshots/dashboard.png)

### Restoration History/

![History](screenshots/history.png)

---

## 📂 Project Structure

```text
AI-Art-Restoration-Assistant/
│
├── AI_Art_Restoration_Assistant.py
├── requirements.txt
├── README.md
├── frontend_setup.md
├── ui_design_notes.md
├── .gitignore
└── screenshots/
```

---