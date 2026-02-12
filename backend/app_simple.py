"""
GrabPic - Minimal Working Version
"""
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid
import json
import sqlite3
from datetime import datetime
import cv2
import numpy as np
import threading

app = Flask(__name__, 
           static_folder='../frontend',
           template_folder='../frontend')

# Configuration
UPLOAD_FOLDER = 'temp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Simple face detection using OpenCV
def detect_faces_simple(image_path):
    """Simple face detection using OpenCV Haar Cascade"""
    try:
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            return []
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Load Haar Cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        if face_cascade.empty():
            print("Haar cascade not loaded properly")
            return []
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        face_data = []
        for (x, y, w, h) in faces:
            # Extract face region
            face_img = image[y:y+h, x:x+w]
            
            # Resize to consistent size
            face_img_resized = cv2.resize(face_img, (64, 64))
            
            # Simple feature extraction (histogram)
            hsv = cv2.cvtColor(face_img_resized, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            face_data.append({
                'bbox': [int(x), int(y), int(x+w), int(y+h)],
                'features': hist.tolist(),
                'face_id': str(uuid.uuid4()),
                'confidence': 1.0
            })
        
        return face_data
        
    except Exception as e:
        print(f"Error in face detection: {e}")
        return []

# Database setup
def init_db():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT UNIQUE,
            event_name TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Photos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            filename TEXT,
            filepath TEXT,
            upload_time TIMESTAMP
        )
    ''')
    
    # Faces table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER,
            event_code TEXT,
            face_features TEXT,  -- JSON string
            bbox TEXT,           -- JSON string [x,y,w,h]
            person_id INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def index():
    return """
    <html>
    <head><title>GrabPic</title></head>
    <body>
        <h1>GrabPic - Event Photo Finder</h1>
        <p>Server is running!</p>
        <p>Endpoints:</p>
        <ul>
            <li><a href="/api/health">/api/health</a> - Health check</li>
            <li>/api/create_event - Create new event</li>
            <li>/api/upload_photos - Upload photos</li>
            <li>/api/login - Login with selfie</li>
        </ul>
    </body>
    </html>
    """

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'GrabPic server is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/create_event', methods=['POST'])
def create_event():
    try:
        data = request.json
        event_name = data.get('event_name', 'My Event')
        
        # Generate event code
        event_code = str(uuid.uuid4())[:8].upper()
        
        # Save to database
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO events (event_code, event_name, created_at) VALUES (?, ?, ?)',
            (event_code, event_name, datetime.now())
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'event_code': event_code,
            'message': f'Event created! Code: {event_code}'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload_photos', methods=['POST'])
def upload_photos():
    try:
        event_code = request.form.get('event_code')
        
        if not event_code:
            return jsonify({'status': 'error', 'message': 'Event code required'}), 400
        
        # Create event directory
        event_dir = os.path.join(UPLOAD_FOLDER, event_code)
        os.makedirs(event_dir, exist_ok=True)
        
        # Save uploaded files
        files = request.files.getlist('photos')
        saved_files = []
        
        for file in files:
            if file.filename:
                # Generate unique filename
                filename = f"{uuid.uuid4()}_{file.filename}"
                filepath = os.path.join(event_dir, filename)
                file.save(filepath)
                saved_files.append({
                    'filename': filename,
                    'filepath': filepath
                })
                
                # Save to database
                conn = sqlite3.connect('instance/database.db')
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO photos (event_code, filename, filepath, upload_time) VALUES (?, ?, ?, ?)',
                    (event_code, filename, filepath, datetime.now())
                )
                conn.commit()
                conn.close()
        
        # Process faces in background
        def process_faces():
            for file_info in saved_files:
                faces = detect_faces_simple(file_info['filepath'])
                print(f"Found {len(faces)} faces in {file_info['filename']}")
        
        thread = threading.Thread(target=process_faces)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Uploaded {len(saved_files)} photos',
            'photos_count': len(saved_files)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        event_code = request.form.get('event_code')
        
        if not event_code:
            return jsonify({'status': 'error', 'message': 'Event code required'}), 400
        
        # For now, return a simple response
        return jsonify({
            'status': 'success',
            'message': 'Login endpoint working',
            'event_code': event_code
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("GrabPic - Minimal Version")
    print("=" * 60)
    print("Server starting on: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)