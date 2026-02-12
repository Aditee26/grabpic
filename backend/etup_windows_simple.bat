@echo off
echo Setting up GrabPic (Simplified Windows Version)...

REM Create directories
mkdir temp\uploads 2>nul
mkdir temp\processed 2>nul
mkdir instance 2>nul
mkdir models 2>nul

REM Install requirements (no dlib!)
pip install Flask==2.3.3 Flask-CORS==4.0.0 opencv-python==4.8.1.78
pip install numpy==1.24.3 Pillow==10.0.0 scikit-learn==1.3.0
pip install scipy==1.11.4 werkzeug==2.3.7 python-dotenv==1.0.0

echo.
echo Downloading face detection models...
python -c "
import urllib.request
import os

model_dir = 'models'
os.makedirs(model_dir, exist_ok=True)

models = {
    'deploy.prototxt': 'https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt',
    'res10_300x300_ssd_iter_140000.caffemodel': 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel'
}

for name, url in models.items():
    path = os.path.join(model_dir, name)
    if not os.path.exists(path):
        print(f'Downloading {name}...')
        try:
            urllib.request.urlretrieve(url, path)
            print(f'✓ Downloaded {name}')
        except Exception as e:
            print(f'⚠ Could not download {name}: {e}')
"

echo.
echo Setup complete!
echo.
echo To run the application:
echo   python backend\app.py
echo.
echo Then open: http://localhost:5000
pause