import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
import boto3
from botocore.exceptions import NoCredentialsError
from werkzeug.utils import secure_filename

class StorageManager:
    def __init__(self, config):
        self.config = config
        self.local_mode = not (config.AWS_ACCESS_KEY and config.AWS_SECRET_KEY)
        
        # Create necessary directories
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(config.PROCESSED_FOLDER, exist_ok=True)
        os.makedirs(config.FACES_FOLDER, exist_ok=True)
        
        # Initialize S3 client if credentials available
        if not self.local_mode:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.AWS_ACCESS_KEY,
                aws_secret_access_key=config.AWS_SECRET_KEY
            )
            self.s3_bucket = config.AWS_BUCKET
    
    def save_uploaded_file(self, file, event_id: str) -> Optional[str]:
        """Save uploaded file to appropriate storage"""
        if file.filename == '':
            return None
        
        # Secure the filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        if self.local_mode:
            # Save locally
            event_folder = os.path.join(self.config.UPLOAD_FOLDER, event_id)
            os.makedirs(event_folder, exist_ok=True)
            
            file_path = os.path.join(event_folder, unique_filename)
            file.save(file_path)
            
            return file_path
        else:
            # Upload to S3
            s3_key = f"events/{event_id}/{unique_filename}"
            try:
                self.s3_client.upload_fileobj(
                    file,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={'ContentType': file.content_type}
                )
                return f"s3://{self.s3_bucket}/{s3_key}"
            except NoCredentialsError:
                print("AWS credentials not available, falling back to local storage")
                return self.save_uploaded_file(file, event_id)  # Fallback to local
    
    def save_selfie(self, file, event_id: str, user_id: str) -> Optional[str]:
        """Save user selfie temporarily"""
        if file.filename == '':
            return None
        
        filename = secure_filename(file.filename)
        unique_filename = f"selfie_{user_id}_{uuid.uuid4()}_{filename}"
        
        selfie_folder = os.path.join(self.config.UPLOAD_FOLDER, event_id, "selfies")
        os.makedirs(selfie_folder, exist_ok=True)
        
        file_path = os.path.join(selfie_folder, unique_filename)
        file.save(file_path)
        
        return file_path
    
    def get_file_url(self, file_path: str) -> str:
        """Get accessible URL for a file"""
        if file_path.startswith('s3://'):
            # Generate pre-signed URL for S3
            bucket_key = file_path.replace(f"s3://{self.s3_bucket}/", "")
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.s3_bucket, 'Key': bucket_key},
                    ExpiresIn=3600  # URL expires in 1 hour
                )
                return url
            except Exception as e:
                print(f"Error generating S3 URL: {e}")
                return file_path
        else:
            # Local file - return relative path for Flask to serve
            return f"/static/{os.path.relpath(file_path, start='.')}"
    
    def get_event_photos(self, event_id: str) -> List[str]:
        """Get all photo paths for an event"""
        if self.local_mode:
            event_folder = os.path.join(self.config.UPLOAD_FOLDER, event_id)
            if os.path.exists(event_folder):
                photos = []
                for filename in os.listdir(event_folder):
                    if filename.lower().endswith(tuple(self.config.ALLOWED_EXTENSIONS)):
                        photos.append(os.path.join(event_folder, filename))
                return photos
            return []
        else:
            # List files from S3
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=f"events/{event_id}/"
                )
                
                photos = []
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if any(obj['Key'].lower().endswith(ext) for ext in self.config.ALLOWED_EXTENSIONS):
                            photos.append(f"s3://{self.s3_bucket}/{obj['Key']}")
                return photos
            except Exception as e:
                print(f"Error listing S3 files: {e}")
                return []
    
    def cleanup_temp_files(self, file_path: str):
        """Clean up temporary files"""
        try:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")
    
    def cleanup_old_selfies(self, event_id: str, max_age_hours: int = 24):
        """Clean up selfies older than specified hours"""
        selfie_folder = os.path.join(self.config.UPLOAD_FOLDER, event_id, "selfies")
        if not os.path.exists(selfie_folder):
            return
        
        current_time = datetime.now()
        for filename in os.listdir(selfie_folder):
            file_path = os.path.join(selfie_folder, filename)
            if os.path.isfile(file_path):
                file_age = current_time - datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_age.total_seconds() > max_age_hours * 3600:
                    self.cleanup_temp_files(file_path)