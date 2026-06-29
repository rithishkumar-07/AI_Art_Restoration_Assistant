# Frontend Setup Documentation

## AI Art Restoration Assistant

### Overview

The frontend of the AI Art Restoration Assistant is developed using Python Tkinter. It provides a user-friendly graphical interface for uploading artwork images, performing restoration, viewing restoration results, and managing restoration history.

---

## User Interface Modules

### 1. Login & Registration Page

Purpose:

* User authentication
* New user registration
* Secure access to the application

Features:

* Username and Password Login
* New User Registration
* Password Validation
* Error Message Display

---

### 2. Main Dashboard

Purpose:

* Central workspace of the application

Features:

* Upload Artwork Button
* Save Restored Image Button
* Restoration History Access
* About Information
* Logout Option
* Progress Bar
* Status Display

---

### 3. Artwork Comparison Panel

Purpose:

* Compare original and restored images

Sections:

* Original Artwork Display
* Restored Artwork Display

Features:

* Image Preview
* Side-by-Side Comparison
* Restoration Result Visualization

---

### 4. Dashboard Statistics Panel

Purpose:

* Display restoration information

Information Displayed:

* Total Restored Images
* Last Quality Score
* File Size
* Image Dimensions
* Current User
* Average Restoration Score
* Best Restoration Score

---

### 5. Restoration History Window

Purpose:

* Manage previously restored artworks

Features:

* Search History Records
* View Restoration Details
* Refresh History
* Clear History
* Export History as CSV

Displayed Information:

* Filename
* File Size
* Width
* Height
* Quality Score
* Restoration Date

---

### 6. Progress Tracking System

Purpose:

* Show restoration progress

Stages:

1. Noise Reduction
2. Detail Enhancement
3. Quality Improvement

Features:

* Real-Time Progress Bar
* Status Updates
* Completion Notifications

---

## User Workflow

1. User logs into the system.
2. User uploads an artwork image.
3. System performs restoration processing.
4. Original and restored images are displayed.
5. Quality score and statistics are updated.
6. User saves the restored image.
7. Restoration details are stored in history.

---

## Frontend Technologies Used

* Python
* Tkinter
* Pillow (PIL)
* OpenCV
* SQLite

---

## Conclusion

The frontend provides a modern and interactive graphical user interface that enables users to restore artworks efficiently, monitor restoration progress, and manage restoration history through an easy-to-use dashboard.
