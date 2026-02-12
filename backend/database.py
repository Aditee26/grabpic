import sqlite3
import json
import hashlib
import datetime
from typing import List, Dict, Any
import numpy as np

class Database:
    def __init__(self, db_path='instance/database.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_name TEXT,
                    organizer_name TEXT,
                    created_at TIMESTAMP,
                    access_code TEXT UNIQUE,
                    status TEXT DEFAULT 'processing'
                )
            ''')
            
            # Photos table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS photos (
                    photo_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    file_path TEXT,
                    file_name TEXT,
                    upload_time TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # Faces table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faces (
                    face_id TEXT PRIMARY KEY,
                    photo_id TEXT,
                    event_id TEXT,
                    person_id INTEGER,
                    embedding BLOB,
                    bbox_x1 REAL,
                    bbox_y1 REAL,
                    bbox_x2 REAL,
                    bbox_y2 REAL,
                    FOREIGN KEY (photo_id) REFERENCES photos (photo_id),
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # Persons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS persons (
                    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    face_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # Users table (matched attendees)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    person_id INTEGER,
                    last_login TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id),
                    FOREIGN KEY (person_id) REFERENCES persons (person_id)
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_faces_event_person ON faces(event_id, person_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_event ON photos(event_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_event ON users(event_id)')
            
            conn.commit()
    
    # Event methods
    def create_event(self, event_id: str, event_name: str, organizer_name: str) -> str:
        """Create a new event and generate access code"""
        import random
        import string
        
        access_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (event_id, event_name, organizer_name, created_at, access_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_id, event_name, organizer_name, datetime.datetime.now(), access_code))
            conn.commit()
        
        return access_code
    
    def get_event_by_code(self, access_code: str) -> Dict:
        """Get event details by access code"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE access_code = ?', (access_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Photo methods
    def add_photos(self, photos_data: List[Dict]):
        """Add multiple photos to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO photos (photo_id, event_id, file_path, file_name, upload_time)
                VALUES (?, ?, ?, ?, ?)
            ''', photos_data)
            conn.commit()
    
    def get_photos_by_person(self, event_id: str, person_id: int) -> List[Dict]:
        """Get all photos for a specific person in an event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT p.* 
                FROM photos p
                JOIN faces f ON p.photo_id = f.photo_id
                WHERE f.event_id = ? AND f.person_id = ?
                ORDER BY p.upload_time
            ''', (event_id, person_id))
            return [dict(row) for row in cursor.fetchall()]
    
    # Face methods
    def add_faces(self, faces_data: List[Dict]):
        """Add face encodings to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for face in faces_data:
                # Convert numpy array to bytes
                embedding_bytes = face['embedding'].tobytes() if isinstance(face['embedding'], np.ndarray) else face['embedding']
                cursor.execute('''
                    INSERT INTO faces (face_id, photo_id, event_id, person_id, embedding, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    face['face_id'], face['photo_id'], face['event_id'], 
                    face['person_id'], embedding_bytes,
                    face['bbox_x1'], face['bbox_y1'], face['bbox_x2'], face['bbox_y2']
                ))
            conn.commit()
    
    def get_all_faces_for_event(self, event_id: str) -> List[Dict]:
        """Get all face encodings for an event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT face_id, embedding, person_id
                FROM faces 
                WHERE event_id = ?
            ''', (event_id,))
            
            faces = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Convert bytes back to numpy array
                row_dict['embedding'] = np.frombuffer(row_dict['embedding'], dtype=np.float64)
                faces.append(row_dict)
            return faces
    
    # Person methods
    def create_person(self, event_id: str) -> int:
        """Create a new person record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO persons (event_id, created_at)
                VALUES (?, ?)
            ''', (event_id, datetime.datetime.now()))
            conn.commit()
            return cursor.lastrowid
    
    def update_person_face_count(self, person_id: int, count: int):
        """Update face count for a person"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE persons SET face_count = ? WHERE person_id = ?
            ''', (count, person_id))
            conn.commit()
    
    # User methods
    def create_or_update_user(self, user_id: str, event_id: str, person_id: int):
        """Create or update user mapping"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, event_id, person_id, last_login)
                VALUES (?, ?, ?, ?)
            ''', (user_id, event_id, person_id, datetime.datetime.now()))
            conn.commit()
    
    def get_user_photos(self, user_id: str) -> List[Dict]:
        """Get all photos for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* 
                FROM photos p
                JOIN faces f ON p.photo_id = f.photo_id
                JOIN users u ON f.event_id = u.event_id AND f.person_id = u.person_id
                WHERE u.user_id = ?
                ORDER BY p.upload_time
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]