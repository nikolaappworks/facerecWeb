import os
import time
import re
import cv2
import numpy as np
from datetime import datetime
from PIL import Image as PILImage
from deepface import DeepFace
import logging

logger = logging.getLogger(__name__)

class FaceProcessingService:
    RECOGNIZED_DATABASE_PATH = 'recognized_faces'
    MAX_TOTAL_IMAGES = 40
    MAX_DAILY_IMAGES = 3
    
    @staticmethod
    def get_domain_folder(domain):
        """Kreira i vraća putanju do foldera za specifični domain"""
        # Čistimo domain string (uklanjamo port ako postoji)
        domain_folder = domain.split(':')[0]
        # Kreiramo punu putanju
        domain_path = os.path.join(FaceProcessingService.RECOGNIZED_DATABASE_PATH, domain_folder)
        # Kreiramo folder ako ne postoji
        if not os.path.exists(domain_path):
            os.makedirs(domain_path, exist_ok=True)
        return domain_path

    @staticmethod
    def is_blurred(image_array, number_of_detected_faces):
        try:
            # Prvo konvertujemo u uint8 ako je potrebno
            if image_array.dtype == 'float64' or image_array.dtype == 'float32':
                image_array = (image_array * 255).astype(np.uint8)
            elif image_array.dtype != np.uint8:
                image_array = image_array.astype(np.uint8)

            print(f"Image array dtype before grayscale: {image_array.dtype}")
            print(f"Image array shape before grayscale: {image_array.shape}")

            # Konverzija u grayscale
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)

            print(f"Grayscale image dtype: {gray.dtype}")
            print(f"Grayscale image shape: {gray.shape}")

            # Povećanje kontrasta pre Laplaciana if there is only one face
            if number_of_detected_faces == 1:
                gray = cv2.equalizeHist(gray)
                print(f"After equalizeHist - Grayscale mean: {gray.mean()}, var: {gray.var()}")

            # Izračunavanje Laplacian varijanse
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian_var = laplacian.var()
            print(f"Laplacian variance after contrast adjustment: {laplacian_var}")
            
            # Provera mutnoće sa povećanjem praga
            return laplacian_var < 55  # Prag za mutnoću, može se dalje podešavati
        except Exception as e:
            print(f"Error in is_blurred: {str(e)}")
            print(f"Image array info - dtype: {image_array.dtype}, shape: {image_array.shape}")
            return False

    @staticmethod
    def extract_faces_with_timeout(img_path, timeout_duration=70):
        try:
            print(f"Extracting faces from {img_path}")
            return DeepFace.extract_faces(img_path=img_path, enforce_detection=True, detector_backend='retinaface')
        except Exception as e:
            logger.error(f"Face extraction error: {str(e)}")
            return None

    @staticmethod
    def count_images_for_person_on_date(person: str, date_str: str, domain: str) -> int:
        """Broji slike za osobu na određeni datum u domenu"""
        try:
            # Dobijamo putanju do domain foldera
            domain_path = FaceProcessingService.get_domain_folder(domain)
            
            # Ako folder ne postoji, vrati 0
            if not os.path.exists(domain_path):
                return 0
            
            # Listamo sve fajlove u domain folderu
            all_files = os.listdir(domain_path)
            
            # Filtriramo fajlove za osobu i datum
            person_date_pattern = re.compile(rf"{re.escape(person)}_{re.escape(date_str)}")
            matching_files = [f for f in all_files if person_date_pattern.search(f)]
            
            logger.info(f"Found {len(matching_files)} images for {person} on {date_str} in domain {domain}")
            return len(matching_files)
            
        except Exception as e:
            logger.error(f"Error counting images: {str(e)}")
            return 0

    @staticmethod
    def count_total_images_for_person(person: str, domain: str) -> int:
        """Broji ukupan broj slika za osobu u domenu"""
        try:
            # Dobijamo putanju do domain foldera
            domain_path = FaceProcessingService.get_domain_folder(domain)
            
            # Ako folder ne postoji, vrati 0
            if not os.path.exists(domain_path):
                return 0
            
            # Listamo sve fajlove u domain folderu
            all_files = os.listdir(domain_path)
            
            # Filtriramo fajlove za osobu
            person_pattern = re.compile(rf"^{re.escape(person)}_")
            matching_files = [f for f in all_files if person_pattern.search(f)]
            
            logger.info(f"Found total of {len(matching_files)} images for {person} in domain {domain}")
            return len(matching_files)
            
        except Exception as e:
            logger.error(f"Error counting total images: {str(e)}")
            return 0

    @staticmethod
    def cleanup_original_image(image_path):
        """Briše originalnu sliku nakon obrade"""
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Successfully deleted original image: {image_path}")
            else:
                logger.warning(f"Original image not found for deletion: {image_path}")
        except Exception as e:
            logger.error(f"Error deleting original image {image_path}: {str(e)}")

    @staticmethod
    def process_face(image_path, person, created_date, domain):
        """Process face from image and return results"""
        logger.info(f"Starting face processing for image: {image_path}")
        
        try:
            # Convert date string to datetime object
            date_obj = datetime.strptime(created_date, "%Y-%m-%d")
            date_str = date_obj.strftime("%Y-%m-%d")

            # Provera ukupnog broja slika
            total_images = FaceProcessingService.count_total_images_for_person(person, domain)
            logger.info(f"Current total images for {person} in domain {domain}: {total_images}")
            if total_images >= FaceProcessingService.MAX_TOTAL_IMAGES:
                logger.info(f"Skipping extraction: {person} already has {FaceProcessingService.MAX_TOTAL_IMAGES} saved images.")
                FaceProcessingService.cleanup_original_image(image_path)
                raise Exception(f"Person image limit reached ({FaceProcessingService.MAX_TOTAL_IMAGES} images).")

            # Provera broja slika za taj dan
            daily_images = FaceProcessingService.count_images_for_person_on_date(person, date_str, domain)
            logger.info(f"Current daily images for {person} on {date_str} in domain {domain}: {daily_images}")
            if daily_images >= FaceProcessingService.MAX_DAILY_IMAGES:
                logger.info(f"Skipping extraction: Already {FaceProcessingService.MAX_DAILY_IMAGES} images for {person} on {date_str}.")
                FaceProcessingService.cleanup_original_image(image_path)
                raise Exception(f"Daily image limit reached ({FaceProcessingService.MAX_DAILY_IMAGES} images).")

            # Kreiramo base folder ako ne postoji
            if not os.path.exists(FaceProcessingService.RECOGNIZED_DATABASE_PATH):
                os.makedirs(FaceProcessingService.RECOGNIZED_DATABASE_PATH, exist_ok=True)

            # Kreiramo i dobijamo putanju do domain foldera
            domain_path = FaceProcessingService.get_domain_folder(domain)

            # Provera da li fajl postoji
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                raise Exception("Image file not found")

            # Extract faces
            face_objs = FaceProcessingService.extract_faces_with_timeout(image_path)

            if face_objs is None:
                raise Exception("Face extraction failed")

            valid_faces = []
            invalid_faces = []
            number_of_detected_faces = len(face_objs)
            
            for i, item in enumerate(face_objs):
                face_image_array = item['face']
                w, h = face_image_array.shape[1], face_image_array.shape[0]

                print(f"Original face array shape: {face_image_array.shape}")
                print(f"Original face array dtype: {face_image_array.dtype}")

                # Check face size
                if w < 70 or h < 70:
                    continue

                # Check for blurriness
                if FaceProcessingService.is_blurred(face_image_array, number_of_detected_faces):
                    invalid_faces.append((face_image_array, i))
                    continue

                valid_faces.append((face_image_array, i))

            # Process results
            if len(valid_faces) > 1:
                raise Exception("Multiple faces detected")
            elif len(valid_faces) == 0:
                if len(invalid_faces) > 0:
                    raise Exception("Face(s) blurry")
                else:
                    raise Exception("No face found")

            # Process the single valid face
            face_image_array, i = valid_faces[0]
            unique_id = f"{person}_{date_str}_{int(time.time() * 1000)}"

            print(f"Processing face array shape: {face_image_array.shape}")
            print(f"Processing face array dtype: {face_image_array.dtype}")
            
            # Convert to PIL Image
            face_image_pil = PILImage.fromarray((face_image_array * 255).astype(np.uint8))
            
            # Resize nakon cropa
            new_height = 224
            new_width = int(face_image_pil.width * (new_height / face_image_pil.height))
            face_image_pil = face_image_pil.resize((new_width, new_height), PILImage.LANCZOS)
            
            print(f"PIL Image size after resize: {face_image_pil.size}")

            # Get face coordinates
            facial_area = face_objs[i].get('facial_area', {})
            img = cv2.imread(image_path)
            img_height, img_width = img.shape[:2]
            
            coordinates = {
                "x": round(facial_area.get('x', 0) / img_width, 3),
                "y": round(facial_area.get('y', 0) / img_height, 3),
                "width": round(facial_area.get('w', 0) / img_width, 3),
                "height": round(facial_area.get('h', 0) / img_height, 3)
            }
            print(f"Face coordinates: {coordinates}")
            # Save processed face
            sanitized_filename = re.sub(r'[^\w\-_. ]', '_', f"{unique_id}.jpg")
            face_path = os.path.join(domain_path, sanitized_filename)
            face_image_pil.save(face_path, format="JPEG", quality=85)

            # Na kraju uspešne obrade
            result = {
                'face_path': face_path,
                'coordinates': coordinates,
                'filename': sanitized_filename
            }
            
            # Brisanje originalne slike nakon uspešne obrade
            FaceProcessingService.cleanup_original_image(image_path)
            
            return result
            
        except Exception as e:
            # Brisanje originalne slike i u slučaju greške
            FaceProcessingService.cleanup_original_image(image_path)
            logger.error(f"Error in process_face: {str(e)}")
            raise 