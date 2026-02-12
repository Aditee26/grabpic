import face_recognition
import numpy as np
import cv2
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.cluster import DBSCAN
from collections import defaultdict
import pickle
from typing import List, Dict, Tuple
import time

class FaceProcessor:
    def __init__(self, config):
        self.config = config
        self.face_cache = {}
        
    def detect_faces_in_image(self, image_path: str) -> List[Dict]:
        """Detect faces in a single image and return encodings"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(
                image, 
                model=self.config.FACE_DETECTION_MODEL
            )
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            faces_data = []
            for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                face_id = str(uuid.uuid4())
                
                # Extract bounding box coordinates
                top, right, bottom, left = face_location
                
                faces_data.append({
                    'face_id': face_id,
                    'encoding': face_encoding,
                    'bbox': (left, top, right, bottom),
                    'image_path': image_path
                })
            
            return faces_data
            
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return []
    
    def batch_process_images(self, image_paths: List[str], max_workers: int = 4) -> List[Dict]:
        """Process multiple images in parallel"""
        all_faces = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(self.detect_faces_in_image, img_path): img_path 
                for img_path in image_paths
            }
            
            # Process completed tasks
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                try:
                    faces = future.result()
                    all_faces.extend(faces)
                    print(f"Processed {image_path}: Found {len(faces)} faces")
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
        
        return all_faces
    
    def cluster_faces(self, face_encodings: List[np.ndarray], threshold: float = 0.5) -> List[int]:
        """Cluster face encodings to find unique individuals"""
        if len(face_encodings) == 0:
            return []
        
        # Convert to numpy array
        encodings_array = np.array(face_encodings)
        
        # Use DBSCAN for clustering
        # eps: maximum distance between samples in the same cluster
        # min_samples: minimum number of samples in a cluster
        clustering = DBSCAN(
            eps=threshold, 
            min_samples=1, 
            metric='euclidean'
        ).fit(encodings_array)
        
        # DBSCAN returns -1 for outliers, we want to assign them new clusters
        labels = clustering.labels_
        
        # Assign new cluster IDs to outliers
        next_label = max(labels) + 1 if len(labels) > 0 else 0
        for i in range(len(labels)):
            if labels[i] == -1:  # Outlier
                labels[i] = next_label
                next_label += 1
        
        return labels.tolist()
    
    def find_best_match(self, target_encoding: np.ndarray, face_encodings: List[np.ndarray], 
                       face_ids: List[str], threshold: float = 0.6) -> Tuple[str, float]:
        """Find the best matching face for a target encoding"""
        if not face_encodings:
            return None, float('inf')
        
        # Calculate distances to all faces
        distances = face_recognition.face_distance(face_encodings, target_encoding)
        
        # Find the best match
        best_match_idx = np.argmin(distances)
        best_distance = distances[best_match_idx]
        
        if best_distance < threshold:
            return face_ids[best_match_idx], best_distance
        else:
            return None, best_distance
    
    def process_event_photos(self, event_id: str, photo_paths: List[str]) -> Dict:
        """Main processing pipeline for an event"""
        print(f"Starting face processing for event {event_id}")
        
        # Step 1: Detect faces in all photos
        print(f"Step 1/4: Detecting faces in {len(photo_paths)} photos...")
        all_faces = self.batch_process_images(photo_paths, max_workers=self.config.MAX_WORKERS)
        print(f"Found {len(all_faces)} total faces")
        
        if not all_faces:
            return {"status": "error", "message": "No faces found in photos"}
        
        # Step 2: Extract encodings
        print("Step 2/4: Extracting face encodings...")
        face_encodings = [face['encoding'] for face in all_faces]
        face_ids = [face['face_id'] for face in all_faces]
        
        # Step 3: Cluster faces to find unique individuals
        print("Step 3/4: Clustering faces to identify individuals...")
        person_labels = self.cluster_faces(face_encodings, self.config.FACE_CLUSTERING_THRESHOLD)
        
        # Step 4: Organize results
        print("Step 4/4: Organizing results...")
        
        # Group faces by person
        person_to_faces = defaultdict(list)
        for face, person_id in zip(all_faces, person_labels):
            face['person_id'] = person_id
            person_to_faces[person_id].append(face)
        
        # Prepare database-ready data
        faces_db_data = []
        for face in all_faces:
            faces_db_data.append({
                'face_id': face['face_id'],
                'photo_id': os.path.basename(face['image_path']).split('.')[0],
                'event_id': event_id,
                'person_id': face['person_id'],
                'embedding': face['encoding'],
                'bbox_x1': face['bbox'][0],
                'bbox_y1': face['bbox'][1],
                'bbox_x2': face['bbox'][2],
                'bbox_y2': face['bbox'][3]
            })
        
        result = {
            'status': 'success',
            'total_faces': len(all_faces),
            'unique_people': len(set(person_labels)),
            'faces_data': faces_db_data,
            'person_groups': {
                person_id: {
                    'face_count': len(faces),
                    'sample_faces': faces[:3]  # First 3 faces as samples
                }
                for person_id, faces in person_to_faces.items()
            }
        }
        
        print(f"Processing complete: Found {result['unique_people']} unique people")
        return result
    
    def process_selfie(self, selfie_path: str, event_faces: List[Dict], threshold: float = 0.6) -> Dict:
        """Process a selfie and find matching person"""
        try:
            # Detect face in selfie
            selfie_faces = self.detect_faces_in_image(selfie_path)
            
            if not selfie_faces:
                return {"status": "error", "message": "No face found in selfie"}
            
            # Take the first face (assuming one person in selfie)
            selfie_encoding = selfie_faces[0]['encoding']
            
            # Extract event face data
            event_encodings = [face['embedding'] for face in event_faces]
            event_face_ids = [face['face_id'] for face in event_faces]
            event_person_ids = [face['person_id'] for face in event_faces]
            
            # Find best match
            best_face_id, best_distance = self.find_best_match(
                selfie_encoding, event_encodings, event_face_ids, threshold
            )
            
            if best_face_id:
                # Find the person_id for the matched face
                match_idx = event_face_ids.index(best_face_id)
                matched_person_id = event_person_ids[match_idx]
                
                return {
                    "status": "success",
                    "matched": True,
                    "person_id": int(matched_person_id),
                    "confidence": 1 - best_distance,  # Convert distance to confidence
                    "distance": float(best_distance)
                }
            else:
                return {
                    "status": "success",
                    "matched": False,
                    "confidence": 1 - best_distance,
                    "distance": float(best_distance)
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}