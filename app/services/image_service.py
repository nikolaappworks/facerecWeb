import os
from werkzeug.utils import secure_filename
from datetime import datetime
from threading import Thread
from io import BytesIO
import time
from app.services.face_processing_service import FaceProcessingService
import logging
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

class ImageService:
    BASE_UPLOAD_FOLDER = 'storage/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_IMAGE_SIZE = (1024, 1024)  # Maksimalna veličina slike

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ImageService.ALLOWED_EXTENSIONS

    @staticmethod
    def resize_image(image_data):
        """
        Smanjuje veličinu slike održavajući proporcije originalne slike
        
        Args:
            image_data: Bytes ili BytesIO objekat sa slikom
            
        Returns:
            BytesIO: Procesirana slika kao BytesIO objekat
        """
        try:
            # Konvertuj bytes u BytesIO ako je potrebno
            if isinstance(image_data, bytes):
                image_data = BytesIO(image_data)
            
            # Otvori sliku
            with PILImage.open(image_data) as img:
                # Sačuvaj original format
                img_format = img.format or 'JPEG'
                
                # Proveri orijentaciju iz EXIF podataka
                try:
                    exif = img._getexif()
                    if exif and 274 in exif:  # 274 je tag za orijentaciju
                        orientation = exif[274]
                        rotate_values = {
                            3: 180,
                            6: 270,
                            8: 90
                        }
                        if orientation in rotate_values:
                            img = img.rotate(rotate_values[orientation], expand=True)
                except:
                    pass  # Ignoriši ako nema EXIF podataka

                # Uzmi trenutne dimenzije
                width, height = img.size
                
                # Izračunaj nove dimenzije
                if width > height:
                    # Horizontalna slika
                    if width > ImageService.MAX_IMAGE_SIZE[0]:
                        ratio = ImageService.MAX_IMAGE_SIZE[0] / width
                        new_width = ImageService.MAX_IMAGE_SIZE[0]
                        new_height = int(height * ratio)
                    else:
                        return image_data  # Vrati original ako je već manja
                else:
                    # Vertikalna slika
                    if height > ImageService.MAX_IMAGE_SIZE[1]:
                        ratio = ImageService.MAX_IMAGE_SIZE[1] / height
                        new_height = ImageService.MAX_IMAGE_SIZE[1]
                        new_width = int(width * ratio)
                    else:
                        return image_data  # Vrati original ako je već manja

                logger.info(f"Resizing image from {img.size} to {(new_width, new_height)}")
                
                # Resize sliku
                img = img.resize((new_width, new_height), PILImage.LANCZOS)
                
                # Sačuvaj procesiranu sliku u BytesIO
                output = BytesIO()
                img.save(output, format=img_format, quality=85)
                output.seek(0)
                
                return output
                
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            raise

    @staticmethod
    def process_image_async(image_file, person, created_date, domain, image_id=None):
        """
        Asinhrona obrada slike
        
        Args:
            image_file: Fajl slike
            person: Ime osobe
            created_date: Datum kreiranja
            domain: Domen
            image_id: ID slike (opciono, koristi se samo za Kylo API)
        """
        # Prvo smanjimo veličinu slike
        # resized_image = ImageService.resize_image(image_file)
        file_content = image_file.getvalue()
        original_filename = image_file.filename
        
        def background_processing():
            try:
                logger.info(f"Započinje obrada slike za osobu: {person} sa domaina: {domain}")
                
                # Sačuvaj smanjenu sliku
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
                    # Ako image_id nije prosleđen, prosledi None
                    result = FaceProcessingService.process_face(
                        saved_path,
                        person,
                        created_date.strftime('%Y-%m-%d'),
                        domain,
                        image_id  # Može biti None
                    )
                    logger.info(f"Uspešno obrađeno lice: {result['filename']}")
                except Exception as e:
                    logger.error(f"Greška pri obradi lica: {str(e)}")

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