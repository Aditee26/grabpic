# 📸 GrabPic – AI-Powered Event Photo Discovery Platform

GrabPic is a facial recognition-based photo retrieval platform that helps users instantly find their photos from large collections of event images.

Imagine attending a college fest, wedding, conference, hackathon, or sports event where thousands of photos are captured. Instead of manually scrolling through every image, users simply verify their identity using their face, and GrabPic automatically finds and displays all photos containing them.

---

## 🚀 Problem Statement

Event organizers often share hundreds or thousands of photos after an event. Finding personal photos among these large collections is time-consuming and frustrating.

GrabPic solves this problem using AI-powered facial recognition to automatically identify and organize photos for each attendee.

---

## ✨ Features

### 👤 User Features

* 📸 Upload or access event photo collections
* 🎥 Face verification using webcam
* 🤖 AI-powered facial recognition
* 🔍 Automatically discover photos containing the user
* 🖼️ View personalized photo gallery
* ⬇️ Download selected photos instantly
* 🔐 Secure authentication and access control

### 🛠️ Organizer Features

* 📂 Upload bulk event photos
* ⚡ Automatic face indexing and processing
* 📊 Manage event image collections
* 👥 Enable attendees to retrieve their photos independently

---

## 🧠 How It Works

1. Event organizers upload event photographs.
2. The system detects and extracts facial embeddings from all uploaded images.
3. Users open GrabPic and verify their identity through a webcam capture.
4. The captured face is compared against stored facial embeddings.
5. Matching photos are retrieved and displayed in a personalized gallery.
6. Users can preview and download their photos.

---

## 🏗️ System Architecture

```text
User Webcam
      │
      ▼
Face Verification
      │
      ▼
Face Embedding Generation
      │
      ▼
Face Matching Engine
      │
      ▼
Photo Retrieval System
      │
      ▼
Personalized Gallery
```

---

## 🛠️ Tech Stack

### Backend

* Python
* Flask
* OpenCV
* Face Recognition
* SQLite Database
* Docker

### Frontend

* HTML
* CSS
* JavaScript

### AI & Computer Vision

* Facial Detection
* Facial Embedding Extraction
* Similarity Matching
* Automated Image Processing

---

## 📂 Project Structure

```text
grabpic/
│
├── backend/
│   ├── app.py
│   ├── face_pipeline.py
│   ├── face_processor.py
│   ├── matcher.py
│   ├── storage_manager.py
│   └── database.py
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── upload.html
│   ├── gallery.html
│   ├── camera.js
│   └── upload.js
│
├── models/
│   └── download_models.py
│
├── utils/
│   ├── helpers.py
│   └── validators.py
│
└── main.py
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/Aditee26/grabpic.git
cd grabpic
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python main.py
```

---

## 🎯 Use Cases

* 🎓 College Festivals
* 💒 Weddings
* 🏢 Corporate Events
* 🏃 Sports Competitions
* 🎤 Concerts
* 🛠️ Hackathons
* 📸 Professional Photography Events

---

## 🔒 Privacy & Security

* Face data is processed solely for photo matching.
* Users only receive access to photos containing their face.
* Authentication mechanisms help prevent unauthorized access.
* Event organizers maintain control over uploaded content.

---

## 🚀 Future Enhancements

* Mobile application support
* Real-time event photo updates
* Multi-face search capability
* Cloud storage integration
* QR code event access
* Face clustering and tagging
* AI-powered image quality ranking

---

## 📈 Impact

GrabPic transforms the way event photos are shared by reducing search time from hours to seconds, creating a seamless and personalized experience for attendees.

---

## 👩‍💻 Author

**Aditee Singh**

GitHub: https://github.com/Aditee26

---

### 📸 Find Your Moments, Instantly.

### Powered by AI Facial Recognition.
