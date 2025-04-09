import os
from werkzeug.utils import secure_filename
from datetime import datetime
from threading import Thread
from io import BytesIO
import time
from app.services.face_processing_service import FaceProcessingService
import logging

logger = logging.getLogger(__name__)

class ImageService:
    BASE_UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ImageService.ALLOWED_EXTENSIONS

    @staticmethod
    def process_image_async(image_file, person, created_date, domain):
        """Asinhrona obrada slike"""
        file_content = image_file.read()
        original_filename = image_file.filename
        
        def background_processing():
            try:
                logger.info(f"Započinje obrada slike za osobu: {person} sa domaina: {domain}")
                
                # Prvo sačuvamo originalnu sliku
                file_copy = BytesIO(file_content)
                file_copy.filename = original_filename
                saved_path = ImageService.save_image(
                    file_copy, 
                    person=person, 
                    created_date=created_date,
                    domain=domain
                )
                
                # Zatim procesiramo lice
                try:
                    result = FaceProcessingService.process_face(
                        saved_path,
                        person,
                        created_date.strftime('%Y-%m-%d'),
                        domain
                    )
                    logger.info(f"Uspešno obrađeno lice: {result['filename']}")
                except Exception as e:
                    logger.error(f"Greška pri obradi lica: {str(e)}")
                    # Ovde možete dodati logiku za slanje informacija o grešci

            except Exception as e:
                logger.error(f"Greška prilikom obrade slike: {str(e)}")

        thread = Thread(target=background_processing)
        thread.daemon = True
        thread.start()
        
        return "Processing started"

    @staticmethod
    def save_image(image_file, person, created_date, domain):
        """Čuva sliku u folder specifičan za domain"""
        if image_file and ImageService.allowed_file(image_file.filename):
            # Čistimo domain string za ime foldera (uklanjamo port ako postoji)
            domain_folder = domain.split(':')[0]
            
            # Kreiramo putanju do foldera specifičnog za domain
            domain_path = os.path.join(ImageService.BASE_UPLOAD_FOLDER, domain_folder)
            
            # Kreiranje imena fajla sa person i created_date
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(image_file.filename)
            filename = f"{person}_{created_date.strftime('%Y%m%d')}_{timestamp}_{original_filename}"
            
            # Kreiramo folder za domain ako ne postoji
            if not os.path.exists(domain_path):
                os.makedirs(domain_path)
            
            # Puna putanja do fajla
            file_path = os.path.join(domain_path, filename)
            
            # Čuvamo fajl
            with open(file_path, 'wb') as f:
                if isinstance(image_file, BytesIO):
                    f.write(image_file.getvalue())
                else:
                    image_file.save(f)
            
            return file_path
        return None 