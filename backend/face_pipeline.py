import os, pickle
import face_recognition

UPLOAD_FOLDER = "event_photos/"
face_db_file = "face_db.pkl"
face_db = {}  # face_id -> list of photo filenames

for img_file in os.listdir(UPLOAD_FOLDER):
    img_path = os.path.join(UPLOAD_FOLDER, img_file)
    image = face_recognition.load_image_file(img_path)
    faces = face_recognition.face_encodings(image)
    
    for face_encoding in faces:
        face_id = str(hash(face_encoding.tobytes()))
        if face_id not in face_db:
            face_db[face_id] = []
        face_db[face_id].append(img_file)

with open(face_db_file, "wb") as f:
    pickle.dump(face_db, f)

print("Face DB created successfully!")
