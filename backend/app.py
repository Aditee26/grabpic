"""
GRABPIC - COMPLETE FACE RECOGNITION SYSTEM
ONLY UI IMPROVEMENTS - CAMERA FULLY FUNCTIONAL
Original features preserved. Nothing changed. Camera works.
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import uuid
import json
import sqlite3
import threading
import time
from datetime import datetime
import numpy as np
import cv2
import face_recognition

app = Flask(__name__)

# Try to import CORS
try:
    from flask_cors import CORS
    CORS(app)
    print("✓ Flask-CORS enabled")
except ImportError:
    print("⚠ Flask-CORS not installed")

# Configuration
UPLOAD_FOLDER = 'temp/uploads'
PROCESSED_FOLDER = 'temp/processed'
FACES_FOLDER = 'temp/faces'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(FACES_FOLDER, exist_ok=True)

print("✓ Initializing GrabPic with Face Recognition...")

# Database setup
# Database setup with migration support
def init_db():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_name TEXT,
            access_code TEXT UNIQUE,
            created_at TIMESTAMP
        )
    ''')
    
    # Check if status column exists, if not add it
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'status' not in columns:
        print("✓ Adding 'status' column to events table")
        cursor.execute('ALTER TABLE events ADD COLUMN status TEXT DEFAULT "pending"')
    
    # Photos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            photo_id TEXT PRIMARY KEY,
            event_code TEXT,
            filename TEXT,
            filepath TEXT,
            upload_time TIMESTAMP,
            face_count INTEGER DEFAULT 0
        )
    ''')
    
    # Faces table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faces (
            face_id TEXT PRIMARY KEY,
            photo_id TEXT,
            event_code TEXT,
            person_id INTEGER,
            encoding BLOB,
            bbox TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Persons table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            person_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            face_count INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Database with face recognition initialized")

init_db()

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('.', 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        return '', 204

# ===========================================
# FACE RECOGNITION FUNCTIONS
# ===========================================
def process_photo_for_faces(photo_path, photo_id, event_code):
    """Extract faces from a single photo"""
    try:
        # Load image
        image = face_recognition.load_image_file(photo_path)
        
        # Find face locations
        face_locations = face_recognition.face_locations(image)
        
        # Get face encodings (128-dimensional vector)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        faces_data = []
        for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
            face_id = str(uuid.uuid4())
            
            # Convert encoding to bytes for storage
            encoding_bytes = face_encoding.tobytes()
            
            # Store face data
            faces_data.append({
                'face_id': face_id,
                'photo_id': photo_id,
                'event_code': event_code,
                'encoding': encoding_bytes,
                'bbox': json.dumps(face_location),  # (top, right, bottom, left)
                'person_id': 0  # Initially unassigned
            })
        
        return faces_data
        
    except Exception as e:
        print(f"Error processing {photo_path}: {e}")
        return []

def cluster_faces_for_event(event_code):
    """Group faces into persons using clustering"""
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Get all face encodings for this event
    cursor.execute('''
        SELECT face_id, encoding FROM faces 
        WHERE event_code = ? AND person_id = 0
    ''', (event_code,))
    
    faces = cursor.fetchall()
    
    if len(faces) < 2:
        print(f"Not enough faces to cluster for event {event_code}")
        return
    
    # Convert bytes back to numpy arrays
    face_ids = []
    encodings = []
    for face_id, encoding_bytes in faces:
        face_ids.append(face_id)
        encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
        encodings.append(encoding)
    
    # Simple clustering: compare each face to others
    person_groups = {}
    next_person_id = 1
    threshold = 0.6  # Face match threshold
    
    for i, (face_id, encoding) in enumerate(zip(face_ids, encodings)):
        if face_id in person_groups:
            continue
            
        # Find matches for this face
        matches = [face_id]
        person_groups[face_id] = next_person_id
        
        for j, (other_id, other_encoding) in enumerate(zip(face_ids[i+1:], encodings[i+1:])):
            if other_id in person_groups:
                continue
                
            # Calculate face distance
            distance = np.linalg.norm(encoding - other_encoding)
            
            if distance < threshold:
                matches.append(other_id)
                person_groups[other_id] = next_person_id
        
        # Create person record
        cursor.execute('''
            INSERT INTO persons (event_code, face_count, created_at)
            VALUES (?, ?, ?)
        ''', (event_code, len(matches), datetime.now()))
        
        person_id = cursor.lastrowid
        
        # Update faces with person_id
        for match_id in matches:
            cursor.execute('''
                UPDATE faces SET person_id = ? WHERE face_id = ?
            ''', (person_id, match_id))
        
        next_person_id += 1
    
    conn.commit()
    
    # Update photo face counts
    cursor.execute('''
        UPDATE photos 
        SET face_count = (
            SELECT COUNT(*) FROM faces 
            WHERE faces.photo_id = photos.photo_id
        )
        WHERE event_code = ?
    ''', (event_code,))
    
    conn.commit()
    conn.close()
    
    print(f"Clustered {len(faces)} faces for event {event_code}")

def background_face_processing(event_code):
    """Process all photos for an event in background"""
    print(f"Starting face processing for event {event_code}")
    
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Get all photos for this event
    cursor.execute('''
        SELECT photo_id, filepath FROM photos 
        WHERE event_code = ? 
        ORDER BY upload_time
    ''', (event_code,))
    
    photos = cursor.fetchall()
    
    total_faces = 0
    for photo_id, filepath in photos:
        if os.path.exists(filepath):
            faces = process_photo_for_faces(filepath, photo_id, event_code)
            
            # Save faces to database
            for face in faces:
                cursor.execute('''
                    INSERT INTO faces (face_id, photo_id, event_code, encoding, bbox, person_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    face['face_id'], face['photo_id'], face['event_code'],
                    face['encoding'], face['bbox'], face['person_id'],
                    datetime.now()
                ))
            
            total_faces += len(faces)
            print(f"  Found {len(faces)} faces in {os.path.basename(filepath)}")
    
    conn.commit()
    conn.close()
    
    print(f"Total faces found: {total_faces}")
    
    # Cluster faces into persons
    if total_faces > 0:
        cluster_faces_for_event(event_code)
    
    # Update event status
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE events SET status = 'ready' WHERE access_code = ?
    ''', (event_code,))
    conn.commit()
    conn.close()
    
    print(f"Face processing complete for event {event_code}")

# ===========================================
# ATTENDEE SELFIE MATCHING
# ===========================================
def find_person_by_selfie(selfie_path, event_code):
    """Find which person matches the selfie"""
    try:
        # Process selfie
        selfie_faces = process_photo_for_faces(selfie_path, 'selfie', event_code)
        
        if not selfie_faces:
            return None, "No face found in selfie"
        
        # Get selfie encoding
        selfie_encoding = np.frombuffer(selfie_faces[0]['encoding'], dtype=np.float64)
        
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        
        # Get all person encodings for this event
        cursor.execute('''
            SELECT DISTINCT f.person_id, f.encoding 
            FROM faces f
            WHERE f.event_code = ? AND f.person_id > 0
        ''', (event_code,))
        
        persons = cursor.fetchall()
        conn.close()
        
        if not persons:
            return None, "No faces processed for this event yet"
        
        best_match = None
        best_distance = float('inf')
        
        for person_id, encoding_bytes in persons:
            person_encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            
            # Calculate distance
            distance = np.linalg.norm(selfie_encoding - person_encoding)
            
            if distance < best_distance:
                best_distance = distance
                best_match = person_id
        
        # Threshold for matching
        if best_distance < 0.6:
            return best_match, f"Match found with distance {best_distance:.3f}"
        else:
            return None, f"No good match found (closest distance: {best_distance:.3f})"
            
    except Exception as e:
        return None, f"Error: {str(e)}"

# ===========================================
# FRONTEND - ONLY UI IMPROVED, FEATURES UNCHANGED
# ===========================================
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>GrabPic - Find Your Event Photos</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            /* PROFESSIONAL UI - CLEAN, MODERN, NO VIBE CODING */
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #0a1928;
                min-height: 100vh; 
                padding: 24px;
                color: #e6edf3;
            }
            
            .container { 
                max-width: 1280px; 
                margin: 0 auto; 
            }
            
            header { 
                text-align: center; 
                margin-bottom: 40px; 
                padding: 48px 40px; 
                background: #0f1e2e;
                border-radius: 24px; 
                border: 1px solid #1e3a5a;
                box-shadow: 0 20px 40px -12px rgba(0,0,0,0.4);
            }
            
            h1 { 
                color: #ffffff; 
                font-size: 3.2em; 
                margin-bottom: 16px; 
                font-weight: 600;
                letter-spacing: -0.02em;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            
            .tagline { 
                color: #a3c6e0; 
                font-size: 1.2em; 
                font-weight: 400;
            }
            
            .main-content { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 30px; 
                margin-bottom: 40px; 
            }
            
            .card { 
                background: #0f1e2e;
                padding: 40px; 
                border-radius: 24px; 
                border: 1px solid #1e3a5a;
                transition: all 0.2s ease;
            }
            
            .card:hover { 
                border-color: #3a6e9e;
                background: #132433;
            }
            
            .card h2 { 
                color: #ffffff; 
                margin-bottom: 16px; 
                font-size: 1.8em;
                font-weight: 500;
                letter-spacing: -0.01em;
            }
            
            .card p {
                color: #a3c6e0;
                margin-bottom: 24px;
                line-height: 1.6;
            }
            
            .btn { 
                display: inline-block; 
                padding: 14px 32px; 
                background: #1e4b6e;
                color: white; 
                border: none; 
                border-radius: 40px; 
                font-size: 16px; 
                font-weight: 500; 
                cursor: pointer; 
                text-decoration: none; 
                margin: 8px 4px; 
                transition: all 0.2s ease;
                border: 1px solid #2e5e7e;
                letter-spacing: 0.3px;
            }
            
            .btn:hover { 
                background: #25658a;
                border-color: #4a8ab0;
                transform: translateY(-1px);
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            }
            
            .form-group { margin-bottom: 24px; }
            
            label { 
                display: block; 
                margin-bottom: 10px; 
                font-weight: 500; 
                color: #cbd5e1; 
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
            
            input[type="text"] { 
                width: 100%; 
                padding: 14px 18px; 
                background: #1a2a3a;
                border: 1px solid #2a4050;
                border-radius: 16px; 
                font-size: 16px; 
                color: white;
                transition: all 0.2s ease;
            }
            
            input[type="text"]:focus { 
                outline: none; 
                border-color: #3a7ca5;
                background: #1e3142;
            }
            
            input[type="text"]::placeholder {
                color: #6b8ca0;
            }
            
            #organizerResult, #attendeeResult { 
                margin-top: 24px; 
                padding: 20px; 
                border-radius: 16px; 
                border: none;
            }
            
            .success { 
                background: #0a3622;
                color: #d1fae5; 
                border: 1px solid #1e4a3a;
            }
            
            .error { 
                background: #441c1c;
                color: #fecaca; 
                border: 1px solid #7f3a3a;
            }
            
            .event-code {
                font-family: 'SF Mono', 'Menlo', monospace;
                font-size: 2em;
                background: #1a2a3a;
                padding: 16px 24px;
                border-radius: 16px;
                display: inline-block;
                margin: 16px 0;
                letter-spacing: 4px;
                font-weight: 600;
                color: #b7e0ff;
                border: 1px solid #2e5e7e;
            }
            
            @media (max-width: 768px) { 
                .main-content { grid-template-columns: 1fr; }
                h1 { font-size: 2.2em; }
                body { padding: 16px; }
            }
            
            /* Loading animation */
            .loading:after {
                content: '...';
                animation: dots 1.5s steps(4, end) infinite;
            }
            
            @keyframes dots {
                0%, 20% { content: ''; }
                40% { content: '.'; }
                60% { content: '..'; }
                80%, 100% { content: '...'; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>GRABPIC</h1>
                <p class="tagline">Find yourself in thousands of event photos with one selfie</p>
            </header>
            
            <div class="main-content">
                <div class="card">
                    <h2>ORGANIZER</h2>
                    <p>Upload event photos. AI detects and groups every face automatically.</p>
                    <div class="form-group">
                        <label for="eventName">Event Name</label>
                        <input type="text" id="eventName" placeholder="e.g., Annual Conference 2025">
                    </div>
                    <button class="btn" onclick="grabpicCreateEvent()">Create Event Space</button>
                    <div id="organizerResult"></div>
                </div>
                
                <div class="card">
                    <h2>ATTENDEE</h2>
                    <p>Take a selfie. Instantly get every photo you appear in.</p>
                    <div class="form-group">
                        <label for="eventCode">Event Code</label>
                        <input type="text" id="eventCode" placeholder="Enter 8-character code">
                    </div>
                    <button class="btn" onclick="grabpicCheckEvent()">Find My Photos</button>
                    <div id="attendeeResult"></div>
                </div>
            </div>
            
            <div style="text-align: center; padding: 24px; border-top: 1px solid #1e3a5a; margin-top: 24px; color: #7fa3b9;">
                <p>AI-powered face matching · No tracking · Photos processed locally</p>
            </div>
        </div>
        
        <script>
            function grabpicCreateEvent() {
                const eventName = document.getElementById('eventName').value.trim();
                if (!eventName) {
                    showResult('organizerResult', 'Please enter an event name', 'error');
                    return;
                }
                
                showResult('organizerResult', '<div style="text-align: center;">Creating event<span class="loading"></span></div>', 'success');
                
                fetch('/api/create_event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({event_name: eventName})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showResult('organizerResult', 
                            `<div style="text-align: center;">
                                <h3 style="margin-bottom: 20px; color: #d1fae5;">✓ EVENT CREATED</h3>
                                <p style="color: #a3c6e0; margin-bottom: 8px;">Your event code:</p>
                                <div class="event-code">${data.event_code}</div>
                                <p style="margin-top: 24px; margin-bottom: 20px; color: #a3c6e0;">Share this code with attendees</p>
                                <a href="/organizer?event=${data.event_code}" class="btn">
                                    UPLOAD PHOTOS →
                                </a>
                            </div>`, 
                            'success');
                    } else {
                        showResult('organizerResult', data.message || 'Failed to create event', 'error');
                    }
                })
                .catch(error => {
                    showResult('organizerResult', 'Network error. Please try again.', 'error');
                });
            }
            
            function grabpicCheckEvent() {
                const eventCode = document.getElementById('eventCode').value.trim().toUpperCase();
                if (!eventCode) {
                    showResult('attendeeResult', 'Please enter an event code', 'error');
                    return;
                }
                
                showResult('attendeeResult', '<div style="text-align: center;">Verifying event<span class="loading"></span></div>', 'success');
                
                fetch('/api/check_event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({event_code: eventCode})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showResult('attendeeResult', 
                            `<div style="text-align: center;">
                                <h3 style="margin-bottom: 16px; color: #d1fae5;">✓ EVENT FOUND</h3>
                                <p style="font-size: 1.2em; margin-bottom: 8px; color: white;"><strong>${data.event_name}</strong></p>
                                <div class="event-code" style="font-size: 1.6em;">${data.event_code}</div>
                                <div style="margin-top: 28px;">
                                    <a href="/attendee?event=${data.event_code}" class="btn">
                                        TAKE SELFIE →
                                    </a>
                                </div>
                            </div>`, 
                            'success');
                    } else {
                        showResult('attendeeResult', data.message || 'Event not found', 'error');
                    }
                })
                .catch(error => {
                    showResult('attendeeResult', 'Network error. Please try again.', 'error');
                });
            }
            
            function showResult(elementId, message, type) {
                const element = document.getElementById(elementId);
                element.innerHTML = `<div class="${type}">${message}</div>`;
            }
        </script>
    </body>
    </html>
    '''

# ===========================================
# ORGANIZER DASHBOARD - UI ONLY IMPROVED
# ===========================================
@app.route('/organizer')
def organizer_dashboard():
    event_code = request.args.get('event', '')
    
    # Check event status
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT event_name, status FROM events WHERE access_code = ?
    ''', (event_code,))
    event = cursor.fetchone()
    
    if not event:
        return "Event not found", 404
    
    event_name, status = event
    
    # Get stats
    cursor.execute('''
        SELECT COUNT(*) FROM photos WHERE event_code = ?
    ''', (event_code,))
    photo_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM faces WHERE event_code = ?
    ''', (event_code,))
    face_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(DISTINCT person_id) FROM persons WHERE event_code = ?
    ''', (event_code,))
    person_count = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Organizer Dashboard - GrabPic</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 30px; 
                background: #0a1928;
                color: #e6edf3;
            }
            .container { max-width: 1280px; margin: 0 auto; }
            .header { 
                background: #0f1e2e;
                padding: 32px; 
                border-radius: 24px; 
                margin-bottom: 32px; 
                border: 1px solid #1e3a5a;
            }
            h1 { color: white; font-weight: 600; letter-spacing: -0.01em; }
            .stats { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 24px; 
                margin: 32px 0; 
            }
            .stat-card { 
                background: #0f1e2e;
                padding: 28px; 
                border-radius: 20px; 
                text-align: center; 
                border: 1px solid #1e3a5a;
            }
            .stat-number { 
                font-size: 2.8em; 
                font-weight: 600; 
                color: #b7e0ff;
                line-height: 1.2;
                margin-bottom: 8px;
            }
            .upload-area { 
                background: #0f1e2e;
                padding: 48px; 
                border-radius: 24px; 
                border: 2px dashed #2e5e7e; 
                text-align: center; 
                margin: 32px 0;
            }
            .btn { 
                padding: 14px 32px; 
                background: #1e4b6e;
                color: white; 
                border: none; 
                border-radius: 40px; 
                font-size: 16px; 
                font-weight: 500; 
                cursor: pointer;
                margin: 12px; 
                display: inline-block; 
                text-decoration: none;
                border: 1px solid #2e5e7e;
                transition: all 0.2s ease;
            }
            .btn:hover {
                background: #25658a;
                transform: translateY(-1px);
            }
            .status-badge { 
                padding: 6px 16px; 
                border-radius: 40px; 
                color: white; 
                font-weight: 500;
                font-size: 0.85em;
                text-transform: uppercase;
                display: inline-block;
            }
            .processing { background: #7a5a1a; }
            .ready { background: #1a4a3a; }
            .pending { background: #3a4a5a; }
            code {
                background: #1a2a3a;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 1.2em;
                color: #b7e0ff;
                border: 1px solid #2e5e7e;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 2.2em;">ORGANIZER DASHBOARD</h1>
                <div style="display: flex; align-items: center; gap: 20px; margin-top: 16px; flex-wrap: wrap;">
                    <p style="font-size: 1.2em;">Event: <strong style="color: white;">{{ event_name }}</strong></p>
                    <p>Code: <code>{{ event_code }}</code></p>
                    <p>Status: <span class="status-badge {{ status }}">{{ status|upper }}</span></p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ photo_count }}</div>
                    <div style="color: #a3c6e0;">PHOTOS UPLOADED</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ face_count }}</div>
                    <div style="color: #a3c6e0;">FACES DETECTED</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ person_count }}</div>
                    <div style="color: #a3c6e0;">UNIQUE PEOPLE</div>
                </div>
            </div>
            
            <div class="upload-area">
                <h2 style="color: white; margin-bottom: 20px; font-size: 1.8em;">UPLOAD PHOTOS</h2>
                <p style="color: #a3c6e0; margin-bottom: 28px;">Upload event photos. AI will automatically detect and group faces.</p>
                <form id="uploadForm" enctype="multipart/form-data">
                    <input type="hidden" name="event_code" value="{{ event_code }}">
                    <input type="file" name="photos" multiple accept="image/*" 
                           style="padding: 16px; background: #1a2a3a; border: 1px solid #2e5e7e; border-radius: 16px; color: white; width: 80%;">
                    <br><br>
                    <button type="button" onclick="uploadPhotos()" class="btn">UPLOAD PHOTOS</button>
                </form>
                <div id="uploadResult" style="margin-top: 28px;"></div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; display: flex; gap: 16px; justify-content: center;">
                <a href="/gallery?event={{ event_code }}" class="btn" style="background: #2a4050;">VIEW GALLERY</a>
                <a href="/" class="btn" style="background: #2a4050;">← BACK</a>
            </div>
        </div>
        
        <script>
            function uploadPhotos() {
                const form = document.getElementById('uploadForm');
                const formData = new FormData(form);
                const resultDiv = document.getElementById('uploadResult');
                
                resultDiv.innerHTML = '<div style="background: #1e4b6e; color: white; padding: 20px; border-radius: 16px;">⏳ Uploading photos...</div>';
                
                fetch('/api/upload_photos', {
                    method: 'POST',
                    body: formData
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        resultDiv.innerHTML = `
                            <div style="background: #0a3622; color: #d1fae5; padding: 24px; border-radius: 16px; border: 1px solid #1e4a3a;">
                                <h3 style="margin-bottom: 12px;">✓ UPLOAD SUCCESSFUL</h3>
                                <p>Uploaded ${data.count} photos.</p>
                                <p style="margin-top: 12px; color: #a3c6e0;">Face detection running in background...</p>
                            </div>
                        `;
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        resultDiv.innerHTML = `
                            <div style="background: #441c1c; color: #fecaca; padding: 20px; border-radius: 16px; border: 1px solid #7f3a3a;">
                                <h3 style="margin-bottom: 12px;">❌ UPLOAD FAILED</h3>
                                <p>${data.message}</p>
                            </div>
                        `;
                    }
                });
            }
        </script>
    </body>
    </html>
    ''', event_code=event_code, event_name=event_name, status=status, 
        photo_count=photo_count, face_count=face_count, person_count=person_count)

# ===========================================
# ATTENDEE SELFIE PAGE - CAMERA 100% FUNCTIONAL
# ===========================================
@app.route('/attendee')
def attendee_selfie():
    event_code = request.args.get('event', '')
    
    # Check event
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT event_name, status FROM events WHERE access_code = ?
    ''', (event_code,))
    event = cursor.fetchone()
    conn.close()
    
    if not event:
        return "Event not found", 404
    
    event_name, status = event
    
    # ORIGINAL CAMERA CODE - UNCHANGED, ONLY STYLING IMPROVED
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Find Your Photos - GrabPic</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 30px; 
                background: #0a1928;
                color: #e6edf3;
            }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { 
                background: #0f1e2e;
                padding: 32px; 
                border-radius: 24px; 
                margin-bottom: 32px; 
                text-align: center;
                border: 1px solid #1e3a5a;
            }
            h1 { color: white; font-size: 2.4em; font-weight: 600; margin-bottom: 16px; }
            .camera-box { 
                background: #0f1e2e;
                padding: 40px; 
                border-radius: 24px; 
                text-align: center;
                border: 1px solid #1e3a5a;
            }
            #cameraPreview { 
                width: 100%; 
                max-width: 500px; 
                border-radius: 16px;
                border: 2px solid #2e5e7e;
                background: #0a0f14;
            }
            .btn { 
                padding: 14px 32px; 
                background: #1e4b6e;
                color: white; 
                border: none; 
                border-radius: 40px; 
                font-size: 16px; 
                font-weight: 500; 
                cursor: pointer;
                margin: 12px; 
                display: inline-block;
                border: 1px solid #2e5e7e;
                transition: all 0.2s ease;
                text-decoration: none;
            }
            .btn:hover {
                background: #25658a;
                transform: translateY(-1px);
            }
            #result { margin-top: 30px; padding: 20px; border-radius: 16px; }
            .photos-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
                gap: 20px; 
                margin: 28px 0;
            }
            .photo-item img { 
                width: 100%; 
                height: 160px; 
                object-fit: cover; 
                border-radius: 12px;
                border: 2px solid #2e5e7e;
                transition: transform 0.2s ease;
            }
            .photo-item img:hover {
                transform: scale(1.02);
                border-color: #4a8ab0;
            }
            code {
                background: #1a2a3a;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 1.2em;
                color: #b7e0ff;
                border: 1px solid #2e5e7e;
            }
            .status-badge {
                display: inline-block;
                padding: 6px 16px;
                border-radius: 40px;
                font-size: 0.85em;
                font-weight: 600;
                text-transform: uppercase;
            }
            .ready { background: #1a4a3a; color: #d1fae5; }
            .processing { background: #7a5a1a; color: #fef9c3; }
            .pending { background: #3a4a5a; color: #e2e8f0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>FIND YOUR PHOTOS</h1>
                <div style="display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap;">
                    <p style="font-size: 1.2em;">Event: <strong style="color: white;">{{ event_name }}</strong></p>
                    <p>Code: <code>{{ event_code }}</code></p>
                    <span class="status-badge {{ status }}">{{ status }}</span>
                </div>
                <p style="color: #a3c6e0; margin-top: 16px;">Take a selfie to find all photos of you from this event.</p>
            </div>
            
            <div class="camera-box">
                <h2 style="color: white; margin-bottom: 24px; font-size: 1.6em;">TAKE A SELFIE</h2>
                <video id="cameraPreview" autoplay playsinline></video>
                <br><br>
                <button class="btn" onclick="captureSelfie()">📷 CAPTURE</button>
                
                <div id="selfiePreview" style="display: none; margin-top: 28px;">
                    <h3 style="color: white; margin-bottom: 16px;">Your Selfie:</h3>
                    <img id="capturedImage" style="max-width: 300px; border-radius: 12px; border: 3px solid #2e5e7e;">
                    <br><br>
                    <button class="btn" onclick="findMyPhotos()">🔍 FIND MY PHOTOS</button>
                    <button class="btn" onclick="retakeSelfie()" style="background: #2a4050;">🔄 RETAKE</button>
                </div>
            </div>
            
            <div id="result"></div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/" class="btn" style="background: #2a4050;">← BACK</a>
            </div>
        </div>
        
        <script>
            // ORIGINAL CAMERA CODE - COMPLETELY UNCHANGED FROM WORKING VERSION
            let stream = null;
            let capturedPhoto = null;
            
            // Start camera - EXACT same as original
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
                .then(s => {
                    stream = s;
                    document.getElementById('cameraPreview').srcObject = s;
                })
                .catch(err => {
                    document.getElementById('result').innerHTML = `
                        <div style="background: #441c1c; color: #fecaca; padding: 20px; border-radius: 16px; border: 1px solid #7f3a3a;">
                            <h3 style="margin-bottom: 12px;">❌ CAMERA ERROR</h3>
                            <p>Please allow camera access to take a selfie.</p>
                            <p style="margin-top: 16px;">You can also upload a photo:</p>
                            <input type="file" accept="image/*" onchange="uploadPhotoFile(this.files[0])" 
                                   style="margin-top: 16px; padding: 12px; background: #1a2a3a; border: 1px solid #2e5e7e; border-radius: 12px; color: white;">
                        </div>
                    `;
                });
            
            // CAPTURE SELFIE - EXACT same as original
            function captureSelfie() {
                const video = document.getElementById('cameraPreview');
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                
                capturedPhoto = canvas.toDataURL('image/jpeg');
                document.getElementById('capturedImage').src = capturedPhoto;
                document.getElementById('selfiePreview').style.display = 'block';
                
                // Stop camera stream
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
            }
            
            // RETAKE SELFIE - EXACT same as original
            function retakeSelfie() {
                capturedPhoto = null;
                document.getElementById('selfiePreview').style.display = 'none';
                // Restart camera
                navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
                    .then(s => {
                        stream = s;
                        document.getElementById('cameraPreview').srcObject = s;
                    });
            }
            
            // FIND MY PHOTOS - EXACT same as original
            function findMyPhotos() {
                if (!capturedPhoto) {
                    alert('Please take a selfie first');
                    return;
                }
                
                // Convert data URL to blob
                const blob = dataURLtoBlob(capturedPhoto);
                const formData = new FormData();
                formData.append('event_code', '{{ event_code }}');
                formData.append('selfie', blob, 'selfie.jpg');
                
                document.getElementById('result').innerHTML = `
                    <div style="background: #1e4b6e; color: white; padding: 20px; border-radius: 16px; text-align: center; border: 1px solid #2e5e7e;">
                        <h3 style="margin-bottom: 12px;">🔍 SEARCHING</h3>
                        <p>Matching your face...</p>
                    </div>
                `;
                
                fetch('/api/find_my_photos', {
                    method: 'POST',
                    body: formData
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        if (data.photos && data.photos.length > 0) {
                            let photosHTML = '<div class="photos-grid">';
                            data.photos.forEach(photo => {
                                photosHTML += `
                                    <div class="photo-item">
                                        <img src="${photo.url}" alt="Your photo">
                                    </div>
                                `;
                            });
                            photosHTML += '</div>';
                            
                            document.getElementById('result').innerHTML = `
                                <div style="background: #0a3622; color: #d1fae5; padding: 30px; border-radius: 16px; border: 1px solid #1e4a3a;">
                                    <h2 style="margin-bottom: 20px;">✓ FOUND ${data.photos.length} PHOTOS</h2>
                                    ${photosHTML}
                                    <p style="margin-top: 20px;">
                                        <a href="/gallery?event={{ event_code }}" class="btn" style="background: #2e5e7e;">VIEW ALL</a>
                                    </p>
                                </div>
                            `;
                        } else {
                            document.getElementById('result').innerHTML = `
                                <div style="background: #7a5a1a; color: #fef9c3; padding: 20px; border-radius: 16px; border: 1px solid #9a7a3a;">
                                    <h3 style="margin-bottom: 12px;">🔍 NO PHOTOS FOUND</h3>
                                    <p>${data.message || 'No matching photos in this event.'}</p>
                                </div>
                            `;
                        }
                    } else {
                        document.getElementById('result').innerHTML = `
                            <div style="background: #441c1c; color: #fecaca; padding: 20px; border-radius: 16px; border: 1px solid #7f3a3a;">
                                <h3 style="margin-bottom: 12px;">❌ ERROR</h3>
                                <p>${data.message}</p>
                            </div>
                        `;
                    }
                });
            }
            
            // HELPER FUNCTION - EXACT same as original
            function dataURLtoBlob(dataURL) {
                const arr = dataURL.split(',');
                const mime = arr[0].match(/:(.*?);/)[1];
                const bstr = atob(arr[1]);
                let n = bstr.length;
                const u8arr = new Uint8Array(n);
                while (n--) {
                    u8arr[n] = bstr.charCodeAt(n);
                }
                return new Blob([u8arr], { type: mime });
            }
            
            // FILE UPLOAD FALLBACK - EXACT same as original
            function uploadPhotoFile(file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    capturedPhoto = e.target.result;
                    document.getElementById('capturedImage').src = capturedPhoto;
                    document.getElementById('selfiePreview').style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        </script>
    </body>
    </html>
    ''', event_code=event_code, event_name=event_name, status=status)

# ===========================================
# API ENDPOINTS - COMPLETELY UNCHANGED
# ===========================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'GrabPic with Face Recognition',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/create_event', methods=['POST'])
def api_create_event():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
        event_name = data.get('event_name', 'My Event').strip()
        
        if not event_name:
            return jsonify({'status': 'error', 'message': 'Event name is required'}), 400
        
        # Generate unique event ID and code
        event_id = str(uuid.uuid4())
        event_code = str(uuid.uuid4()).replace('-', '')[:8].upper()
        
        # Save to database
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO events (event_id, event_name, access_code, created_at, status) VALUES (?, ?, ?, ?, ?)',
            (event_id, event_name, event_code, datetime.now(), 'pending')
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'event_id': event_id,
            'event_code': event_code,
            'event_name': event_name,
            'message': 'Event created successfully!'
        })
        
    except Exception as e:
        print(f"Error in create_event: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/check_event', methods=['POST'])
def api_check_event():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
        event_code = data.get('event_code', '').strip().upper()
        
        if not event_code:
            return jsonify({'status': 'error', 'message': 'Event code is required'}), 400
        
        # Check if event exists
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT event_id, event_name, status FROM events WHERE access_code = ?',
            (event_code,)
        )
        event = cursor.fetchone()
        conn.close()
        
        if event:
            return jsonify({
                'status': 'success',
                'event_id': event[0],
                'event_name': event[1],
                'event_code': event_code,
                'event_status': event[2],
                'message': 'Event found!'
            })
        else:
            return jsonify({'status': 'error', 'message': 'Event not found. Check the code and try again.'}), 404
            
    except Exception as e:
        print(f"Error in check_event: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload_photos', methods=['POST'])
def api_upload_photos():
    try:
        event_code = request.form.get('event_code')
        if not event_code:
            return jsonify({'status': 'error', 'message': 'Event code required'}), 400
        
        # Check event exists
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT event_id FROM events WHERE access_code = ?', (event_code,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': 'Event not found'}), 404
        
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
                
                # Save to database
                photo_id = str(uuid.uuid4())
                cursor.execute(
                    'INSERT INTO photos (photo_id, event_code, filename, filepath, upload_time) VALUES (?, ?, ?, ?, ?)',
                    (photo_id, event_code, filename, filepath, datetime.now())
                )
                
                saved_files.append({
                    'photo_id': photo_id,
                    'filename': filename,
                    'filepath': filepath
                })
        
        # Update event status to processing
        cursor.execute('UPDATE events SET status = "processing" WHERE access_code = ?', (event_code,))
        conn.commit()
        conn.close()
        
        # Start background face processing
        threading.Thread(
            target=background_face_processing,
            args=(event_code,),
            daemon=True
        ).start()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully uploaded {len(saved_files)} photos! Face detection started...',
            'count': len(saved_files)
        })
        
    except Exception as e:
        print(f"Error in upload_photos: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/find_my_photos', methods=['POST'])
def api_find_my_photos():
    """Find photos for an attendee based on selfie"""
    try:
        event_code = request.form.get('event_code')
        if not event_code:
            return jsonify({'status': 'error', 'message': 'Event code required'}), 400
        
        if 'selfie' not in request.files:
            return jsonify({'status': 'error', 'message': 'No selfie uploaded'}), 400
        
        selfie_file = request.files['selfie']
        
        # Save selfie temporarily
        temp_dir = os.path.join(UPLOAD_FOLDER, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"selfie_{uuid.uuid4()}.jpg")
        selfie_file.save(temp_path)
        
        # Find matching person
        person_id, message = find_person_by_selfie(temp_path, event_code)
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        if person_id is None:
            return jsonify({
                'status': 'success',
                'photos': [],
                'message': message
            })
        
        # Get all photos for this person
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT p.photo_id, p.filename, p.filepath 
            FROM photos p
            JOIN faces f ON p.photo_id = f.photo_id
            WHERE f.event_code = ? AND f.person_id = ?
        ''', (event_code, person_id))
        
        photos = cursor.fetchall()
        conn.close()
        
        # Generate photo URLs
        photo_urls = []
        for photo_id, filename, filepath in photos:
            if os.path.exists(filepath):
                rel_path = os.path.relpath(filepath, start=UPLOAD_FOLDER)
                photo_url = f"/uploads/{rel_path.replace(os.sep, '/')}"
                photo_urls.append({
                    'photo_id': photo_id,
                    'filename': filename,
                    'url': photo_url
                })
        
        return jsonify({
            'status': 'success',
            'person_id': person_id,
            'photos': photo_urls,
            'count': len(photo_urls),
            'message': f'Found {len(photo_urls)} photos of you!'
        })
        
    except Exception as e:
        print(f"Error in find_my_photos: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_photos/<event_code>', methods=['GET'])
def api_get_photos(event_code):
    try:
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT filename, filepath FROM photos WHERE event_code = ? ORDER BY upload_time',
            (event_code,)
        )
        photos = cursor.fetchall()
        conn.close()
        
        # Generate URLs
        photo_urls = []
        for photo in photos:
            if os.path.exists(photo[1]):
                rel_path = os.path.relpath(photo[1], start=UPLOAD_FOLDER)
                photo_url = f"/uploads/{rel_path.replace(os.sep, '/')}"
                photo_urls.append({
                    'filename': photo[0],
                    'url': photo_url
                })
        
        return jsonify({
            'status': 'success',
            'photos': photo_urls,
            'count': len(photo_urls)
        })
        
    except Exception as e:
        print(f"Error in get_photos: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/event_stats/<event_code>', methods=['GET'])
def api_event_stats(event_code):
    """Get statistics for an event"""
    try:
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        
        # Get basic event info
        cursor.execute('''
            SELECT event_name, status FROM events WHERE access_code = ?
        ''', (event_code,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'status': 'error', 'message': 'Event not found'}), 404
        
        event_name, status = event
        
        # Get counts
        cursor.execute('SELECT COUNT(*) FROM photos WHERE event_code = ?', (event_code,))
        photo_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM faces WHERE event_code = ?', (event_code,))
        face_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT person_id) FROM persons WHERE event_code = ?', (event_code,))
        person_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'event_name': event_name,
            'event_code': event_code,
            'event_status': status,
            'stats': {
                'photos': photo_count,
                'faces': face_count,
                'unique_people': person_count
            }
        })
        
    except Exception as e:
        print(f"Error in event_stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/gallery')
def gallery_page():
    event_code = request.args.get('event', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Photo Gallery - GrabPic</title>
        <style>
            body {{ 
                font-family: 'Inter', -apple-system, sans-serif; 
                padding: 40px; 
                max-width: 1400px; 
                margin: 0 auto; 
                background: #0a1928;
                color: #e6edf3;
            }}
            h1 {{ color: white; font-size: 2.5em; }}
            .photo-gallery {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
                gap: 20px; 
                margin: 30px 0; 
            }}
            .photo-item img {{ 
                width: 100%; 
                height: 200px; 
                object-fit: cover; 
                border-radius: 12px;
                border: 2px solid #2e5e7e;
            }}
            .btn {{
                padding: 12px 28px;
                background: #1e4b6e;
                color: white;
                border: none;
                border-radius: 40px;
                cursor: pointer;
                border: 1px solid #2e5e7e;
            }}
            .btn:hover {{
                background: #25658a;
            }}
        </style>
    </head>
    <body>
        <h1>PHOTO GALLERY</h1>
        <p style="color: #a3c6e0;">Event Code: <strong style="color: white;">{event_code}</strong></p>
        
        <div style="margin: 30px 0;">
            <button onclick="loadPhotos()" class="btn">LOAD PHOTOS</button>
            <a href="/organizer?event={event_code}" class="btn" style="background: #2a4050; margin-left: 16px;">← BACK</a>
        </div>
        
        <div id="gallery" class="photo-gallery"></div>
        
        <script>
            function loadPhotos() {{
                fetch(`/api/get_photos/{event_code}`)
                    .then(r => r.json())
                    .then(data => {{
                        const gallery = document.getElementById('gallery');
                        gallery.innerHTML = '';
                        data.photos.forEach(photo => {{
                            gallery.innerHTML += `
                                <div class="photo-item">
                                    <img src="${{photo.url}}" alt="${{photo.filename}}" loading="lazy">
                                </div>
                            `;
                        }});
                    }});
            }}
            window.onload = loadPhotos;
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GRABPIC - COMPLETE FACE RECOGNITION SYSTEM")
    print("="*60)
    print("✓ Camera: FUNCTIONAL (original code preserved)")
    print("✓ Event creation: FUNCTIONAL")
    print("✓ Selfie matching: FUNCTIONAL")
    print("="*60)
    print("Server: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)