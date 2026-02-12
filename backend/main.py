from fastapi import FastAPI, UploadFile
import shutil, os, pickle
import face_recognition
import boto3
from botocore.exceptions import NoCredentialsError

UPLOAD_FOLDER = "event_photos/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AWS S3 setup
AWS_BUCKET = "your-bucket-name"
AWS_ACCESS_KEY = "YOUR_ACCESS_KEY"
AWS_SECRET_KEY = "YOUR_SECRET_KEY"
s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

app = FastAPI()

@app.post("/upload/")
async def upload_photo(file: UploadFile):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        s3.upload_file(file_location, AWS_BUCKET, file.filename)
    except NoCredentialsError:
        return {"error": "AWS credentials not configured"}
    return {"info": f"file '{file.filename}' saved & uploaded to S3"}

@app.post("/find_photos/")
async def find_photos(file: UploadFile):
    face_db_file = "face_db.pkl"
    if not os.path.exists(face_db_file):
        return {"error": "Face DB not built yet."}
    with open(face_db_file, "rb") as f:
        face_db = pickle.load(f)

    user_img = face_recognition.load_image_file(file.file)
    user_encoding = face_recognition.face_encodings(user_img)[0]

    matched_photos = []
    for face_id, photos in face_db.items():
        known_image = face_recognition.load_image_file(os.path.join(UPLOAD_FOLDER, photos[0]))
        known_encoding = face_recognition.face_encodings(known_image)[0]
        results = face_recognition.compare_faces([known_encoding], user_encoding)
        if results[0]:
            matched_photos.extend(photos)

    s3_urls = [f"https://{AWS_BUCKET}.s3.amazonaws.com/{p}" for p in matched_photos]
    return {"photos": s3_urls}
