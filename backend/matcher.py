import numpy as np
import face_recognition
from typing import Dict, List, Optional
import time

class FaceMatcher:
    def __init__(self, config):
        self.config = config
        
    def match_selfie_to_event(self, selfie_encoding: np.ndarray, 
                             event_faces: List[Dict]) -> Dict:
        """
        Match a selfie to faces in an event
        
        Args:
            selfie_encoding: Face encoding from selfie
            event_faces: List of face dictionaries from database
        
        Returns:
            Dictionary with match results
        """
        if not event_faces:
            return {
                "status": "error",
                "message": "No faces found in event"
            }
        
        # Extract encodings and metadata
        face_encodings = []
        face_ids = []
        person_ids = []
        
        for face in event_faces:
            if isinstance(face['embedding'], bytes):
                # Convert bytes back to numpy array
                encoding = np.frombuffer(face['embedding'], dtype=np.float64)
            else:
                encoding = face['embedding']
            
            face_encodings.append(encoding)
            face_ids.append(face['face_id'])
            person_ids.append(face['person_id'])
        
        # Calculate distances
        start_time = time.time()
        
        # Use face_recognition's optimized distance calculation
        distances = face_recognition.face_distance(face_encodings, selfie_encoding)
        
        # Find the best match
        best_match_idx = np.argmin(distances)
        best_distance = distances[best_match_idx]
        
        processing_time = time.time() - start_time
        
        # Check if match is within threshold
        if best_distance < self.config.FACE_MATCH_THRESHOLD:
            matched_person_id = person_ids[best_match_idx]
            matched_face_id = face_ids[best_match_idx]
            
            # Calculate confidence (inverse of distance, normalized)
            confidence = max(0, 1 - (best_distance / self.config.FACE_MATCH_THRESHOLD))
            
            return {
                "status": "success",
                "matched": True,
                "person_id": int(matched_person_id),
                "face_id": matched_face_id,
                "distance": float(best_distance),
                "confidence": float(confidence),
                "processing_time": processing_time,
                "total_faces_compared": len(face_encodings)
            }
        else:
            # No good match found
            return {
                "status": "success",
                "matched": False,
                "distance": float(best_distance),
                "confidence": 0.0,
                "processing_time": processing_time,
                "total_faces_compared": len(face_encodings),
                "message": "No matching face found. Try a clearer photo or check if you're in the event."
            }
    
    def find_similar_faces(self, target_encoding: np.ndarray, 
                          face_encodings: List[np.ndarray],
                          threshold: float = 0.6) -> List[int]:
        """
        Find all faces similar to target encoding
        
        Returns:
            List of indices of similar faces
        """
        if not face_encodings:
            return []
        
        distances = face_recognition.face_distance(face_encodings, target_encoding)
        similar_indices = np.where(distances < threshold)[0]
        
        return similar_indices.tolist()
    
    def verify_match_quality(self, selfie_encoding: np.ndarray, 
                           matched_encodings: List[np.ndarray]) -> Dict:
        """
        Verify the quality of a match by checking consistency
        
        Returns:
            Quality metrics
        """
        if not matched_encodings:
            return {"quality": "poor", "consistency": 0.0}
        
        # Calculate distances to all matched encodings
        distances = face_recognition.face_distance(matched_encodings, selfie_encoding)
        
        # Calculate statistics
        avg_distance = np.mean(distances)
        std_distance = np.std(distances)
        min_distance = np.min(distances)
        max_distance = np.max(distances)
        
        # Determine quality
        if avg_distance < 0.4 and std_distance < 0.1:
            quality = "excellent"
        elif avg_distance < 0.5 and std_distance < 0.15:
            quality = "good"
        elif avg_distance < 0.6:
            quality = "fair"
        else:
            quality = "poor"
        
        # Consistency score (higher is better)
        consistency = max(0, 1 - (std_distance / 0.3))
        
        return {
            "quality": quality,
            "consistency": float(consistency),
            "avg_distance": float(avg_distance),
            "std_distance": float(std_distance),
            "min_distance": float(min_distance),
            "max_distance": float(max_distance),
            "num_samples": len(matched_encodings)
        }