import re
from typing import List, Optional

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else True

def validate_event_code(code: str) -> bool:
    """Validate event code format"""
    if not code or len(code) != 8:
        return False
    # Should be alphanumeric
    return code.isalnum()

def validate_filename(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate filename and extension"""
    if not filename or '.' not in filename:
        return False
    
    extension = filename.split('.')[-1].lower()
    return extension in allowed_extensions

def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
    """Validate file size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes

def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\'%;()&+]', '', text)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()