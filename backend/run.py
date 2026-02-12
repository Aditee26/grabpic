#!/usr/bin/env python3
"""
GrabPic - Simple Launcher
"""
import os
import sys

print("🚀 Starting GrabPic...")

# Check requirements
try:
    import flask
    import face_recognition
    print("✓ All dependencies installed")
except ImportError as e:
    print(f"✗ Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

# Run the main app
os.system("python app.py")