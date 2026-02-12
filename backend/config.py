import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # App Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/database.db')
    
    # File Storage
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max
    UPLOAD_FOLDER = 'temp/uploads'
    PROCESSED_FOLDER = 'temp/processed'
    FACES_FOLDER = 'temp/faces'
    
    # Face Recognition
    FACE_DETECTION_MODEL = 'hog'  # 'hog' or 'cnn' (cnn more accurate but slower)
    FACE_ENCODING_MODEL = 'facenet'  # 'facenet' or 'openface'
    FACE_MATCH_THRESHOLD = 0.6  # Lower = stricter
    FACE_CLUSTERING_THRESHOLD = 0.5
    
    # Performance
    BATCH_SIZE = 10
    MAX_WORKERS = 4
    
    # Event Settings
    EVENT_CODE_LENGTH = 8
    EVENT_EXPIRE_DAYS = 30
    
    # Security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')
    
    # API Keys (if using cloud services)
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY', '')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY', '')
    AWS_BUCKET = os.getenv('AWS_BUCKET', '')
    
config = Config()