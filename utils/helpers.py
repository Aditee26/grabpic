import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional
import json

def generate_id(prefix: str = '') -> str:
    """Generate a unique ID"""
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id

def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ensure_directory(path: str):
    """Ensure a directory exists"""
    os.makedirs(path, exist_ok=True)

def safe_filename(filename: str) -> str:
    """Convert filename to safe version"""
    # Keep it simple: remove problematic characters
    keepchars = (' ', '.', '_', '-')
    return "".join(c for c in filename if c.isalnum() or c in keepchars).rstrip()

def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def format_file_size(size_in_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Type {type(obj)} not serializable")

def save_json(data, filepath: str):
    """Save data as JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, default=json_serializer, indent=2)

def load_json(filepath: str):
    """Load data from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)