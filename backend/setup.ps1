Write-Host "Setting up GrabPic..." -ForegroundColor Green

# Create directories
Write-Host "Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "temp\uploads"
New-Item -ItemType Directory -Force -Path "temp\processed"
New-Item -ItemType Directory -Force -Path "instance"
New-Item -ItemType Directory -Force -Path "models"
New-Item -ItemType Directory -Force -Path "frontend"

# Create requirements.txt
Write-Host "Creating requirements.txt..." -ForegroundColor Yellow
@"
Flask==2.3.3
Flask-CORS==4.0.0
opencv-python==4.8.1.78
numpy==1.24.3
Pillow==10.0.0
scikit-learn==1.3.0
scipy==1.11.4
werkzeug==2.3.7
python-dotenv==1.0.0
"@ | Out-File -FilePath "requirements.txt" -Encoding UTF8

# Install packages
Write-Host "Installing Python packages..." -ForegroundColor Yellow
pip install Flask==2.3.3
pip install Flask-CORS==4.0.0
pip install opencv-python==4.8.1.78
pip install numpy==1.24.3
pip install Pillow==10.0.0
pip install scikit-learn==1.3.0
pip install scipy==1.11.4
pip install werkzeug==2.3.7
pip install python-dotenv==1.0.0

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To run the application:" -ForegroundColor Cyan
Write-Host "  python backend/app_simple.py" -ForegroundColor White
Write-Host "`nThen open: http://localhost:5000" -ForegroundColor Cyan