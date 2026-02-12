import bz2
import urllib.request
import os

models_dir = os.path.expanduser("~/.face_recognition_models")
os.makedirs(models_dir, exist_ok=True)

# Download and extract shape predictor
print("Downloading shape predictor...")
url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
response = urllib.request.urlopen(url)
compressed_data = response.read()
data = bz2.decompress(compressed_data)
with open(os.path.join(models_dir, "shape_predictor_68_face_landmarks.dat"), "wb") as f:
    f.write(data)

# Download and extract face recognition model
print("Downloading face recognition model...")
url = "http://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2"
response = urllib.request.urlopen(url)
compressed_data = response.read()
data = bz2.decompress(compressed_data)
with open(os.path.join(models_dir, "dlib_face_recognition_resnet_model_v1.dat"), "wb") as f:
    f.write(data)

print("Models downloaded successfully!")