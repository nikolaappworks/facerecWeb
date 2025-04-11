#!/usr/bin/env python3
"""
Skripta za sinhronizaciju slika iz recognized_faces u recognized_faces_prod folder.
Održava istu strukturu foldera i kopira samo nove slike.
"""

import os
import shutil
import time
import logging
import argparse
from datetime import datetime
import sys

# Dodajemo root direktorijum u Python path da bismo mogli da importujemo app module
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

# Sada možemo da importujemo module iz app
from app.services.recognition_service import RecognitionService

# Konfiguracija logovanja
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class FacesSynchronizer:
    # Dozvoljene ekstenzije slika
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
    # Putanja do test slike za inicijalizaciju prepoznavanja
    TEST_IMAGE_PATH = os.path.join(script_dir, 'test_face.JPG')
    
    def __init__(self, source_dir='storage/recognized_faces', target_dir='storage/recognized_faces_prod'):
        # Koristi apsolutne putanje
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.source_dir = os.path.join(self.root_dir, source_dir)
        self.target_dir = os.path.join(self.root_dir, target_dir)
        
        logger.info(f"Root direktorijum: {self.root_dir}")
        logger.info(f"Izvorni direktorijum: {self.source_dir}")
        logger.info(f"Ciljni direktorijum: {self.target_dir}")
        
        # Proveri da li postoji test slika
        if not os.path.exists(self.TEST_IMAGE_PATH):
            logger.warning(f"Test slika ne postoji na putanji: {self.TEST_IMAGE_PATH}")
            logger.warning("Inicijalizacija prepoznavanja lica neće biti izvršena!")
    
    def ensure_target_dirs(self):
        """Osigurava da ciljni direktorijum i poddirektorijumi postoje"""
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)
            logger.info(f"Kreiran glavni ciljni direktorijum: {self.target_dir}")
            
        # Kreiraj poddirektorijume za domene ako ne postoje
        for domain_folder in self._get_domain_folders():
            target_domain_path = os.path.join(self.target_dir, domain_folder)
            if not os.path.exists(target_domain_path):
                os.makedirs(target_domain_path)
                logger.info(f"Kreiran poddirektorijum za domen: {target_domain_path}")
    
    def _get_domain_folders(self):
        """Vraća listu svih domen foldera u izvornom direktorijumu"""
        if not os.path.exists(self.source_dir):
            logger.error(f"Izvorni direktorijum ne postoji: {self.source_dir}")
            return []
            
        folders = [f for f in os.listdir(self.source_dir) 
                  if os.path.isdir(os.path.join(self.source_dir, f))]
        logger.info(f"Pronađeni domeni: {folders}")
        return folders
    
    @staticmethod
    def is_image_file(filename):
        """Proverava da li je fajl slika na osnovu ekstenzije"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in FacesSynchronizer.ALLOWED_EXTENSIONS
    
    def initialize_face_recognition(self, domain_folder):
        """
        Inicijalizuje prepoznavanje lica za domen pokretanjem test prepoznavanja
        """
        if not os.path.exists(self.TEST_IMAGE_PATH):
            logger.warning("Test slika ne postoji, preskačem inicijalizaciju prepoznavanja")
            return False
            
        try:
            logger.info(f"Inicijalizujem prepoznavanje lica za domen: {domain_folder}")
            
            # Učitaj test sliku
            with open(self.TEST_IMAGE_PATH, 'rb') as f:
                test_image_bytes = f.read()
            
            # Proveri da li postoji folder za domen u ciljnom direktorijumu
            domain_path = os.path.join(self.target_dir, domain_folder)
            if not os.path.exists(domain_path):
                logger.warning(f"Folder za domen ne postoji: {domain_path}")
                logger.warning("Preskačem inicijalizaciju prepoznavanja")
                return False
            
            # Proveri da li ima slika u folderu
            images = [f for f in os.listdir(domain_path) if self.is_image_file(f)]
            if not images:
                logger.warning(f"Nema slika u folderu za domen: {domain_path}")
                logger.warning("Preskačem inicijalizaciju prepoznavanja")
                return False
            
            # Pozovi prepoznavanje lica sa posebnim parametrom za db_path
            try:
                from app.services.recognition_service import DeepFace
                
                # Sačuvaj test sliku privremeno
                temp_image_path = os.path.join(self.root_dir, 'scripts', f"temp_test_{int(time.time())}.jpg")
                with open(temp_image_path, 'wb') as f:
                    f.write(test_image_bytes)
                
                # Normalizuj putanje za Windows/Unix kompatibilnost
                temp_image_path = temp_image_path.replace('\\', '/')
                target_domain_path = domain_path.replace('\\', '/')
                
                logger.info(f"Pozivam DeepFace.find sa db_path: {target_domain_path}")
                
                # Direktno pozovi DeepFace.find sa ciljnim folderom kao db_path
                _ = DeepFace.find(
                    img_path=temp_image_path,
                    db_path=target_domain_path,
                    model_name="VGG-Face",
                    detector_backend="retinaface",
                    distance_metric="cosine",
                    enforce_detection=False,
                    silent=False
                )
                
                # Očisti privremeni fajl
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    
                logger.info(f"Inicijalizacija prepoznavanja lica za domen {domain_folder} uspešna")
                return True
                
            except Exception as e:
                logger.error(f"Greška pri direktnom pozivu DeepFace: {str(e)}")
                # Očisti privremeni fajl ako postoji
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                return False
            
        except Exception as e:
            logger.error(f"Greška pri inicijalizaciji prepoznavanja lica za domen {domain_folder}: {str(e)}")
            return False
    
    def sync_domain_folder(self, domain_folder):
        """Sinhronizuje slike za jedan domen i briše originale nakon kopiranja"""
        source_domain_path = os.path.join(self.source_dir, domain_folder)
        target_domain_path = os.path.join(self.target_dir, domain_folder)
        
        logger.info(f"Sinhronizujem domen {domain_folder}")
        logger.info(f"Izvorni folder: {source_domain_path}")
        logger.info(f"Ciljni folder: {target_domain_path}")
        
        # Osiguraj da ciljni folder postoji
        if not os.path.exists(target_domain_path):
            os.makedirs(target_domain_path)
            logger.info(f"Kreiran ciljni folder: {target_domain_path}")
        
        # Dobavi listu slika u izvornom i ciljnom folderu
        try:
            all_source_files = os.listdir(source_domain_path)
            # Filtriraj samo slike
            source_images = {f for f in all_source_files if self.is_image_file(f)}
            logger.info(f"Ukupno fajlova: {len(all_source_files)}, od toga slika: {len(source_images)}")
        except Exception as e:
            logger.error(f"Greška pri čitanju izvornog foldera: {str(e)}")
            return 0
            
        try:
            all_target_files = os.listdir(target_domain_path) if os.path.exists(target_domain_path) else []
            # Filtriraj samo slike
            target_images = {f for f in all_target_files if self.is_image_file(f)}
            logger.info(f"Broj slika u ciljnom folderu: {len(target_images)}")
        except Exception as e:
            logger.error(f"Greška pri čitanju ciljnog foldera: {str(e)}")
            target_images = set()
        
        # Pronađi nove slike koje treba kopirati
        new_images = source_images - target_images
        logger.info(f"Broj novih slika za kopiranje: {len(new_images)}")
        
        if not new_images:
            logger.info(f"Nema novih slika za domen: {domain_folder}")
            return 0
        
        # Kopiraj nove slike i briši originale
        copied_count = 0
        for image in new_images:
            source_path = os.path.join(source_domain_path, image)
            target_path = os.path.join(target_domain_path, image)
            
            # Proveri da li je fajl (ne folder) i da li je slika
            if os.path.isfile(source_path) and self.is_image_file(image):
                try:
                    # Kopiraj sliku u ciljni folder
                    shutil.copy2(source_path, target_path)
                    copied_count += 1
                    logger.info(f"Kopirana slika: {image}")
                    
                    # Proveri da li je kopiranje uspešno
                    if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(source_path):
                        # Obriši original
                        os.remove(source_path)
                        logger.info(f"Obrisan original: {image}")
                    else:
                        logger.warning(f"Kopiranje nije uspelo, original nije obrisan: {image}")
                    
                except Exception as e:
                    logger.error(f"Greška pri kopiranju/brisanju {image}: {str(e)}")
        
        logger.info(f"Kopirano i obrisano {copied_count} slika za domen: {domain_folder}")
        
        # Inicijalizuj prepoznavanje lica nakon kopiranja
        if copied_count > 0:
            self.initialize_face_recognition(domain_folder)
            
        return copied_count
    
    def sync_all(self):
        """Sinhronizuje sve domene"""
        start_time = time.time()
        logger.info(f"Započinjem sinhronizaciju iz {self.source_dir} u {self.target_dir}")
        
        # Osiguraj da ciljni direktorijumi postoje
        self.ensure_target_dirs()
        
        # Sinhronizuj svaki domen folder
        total_copied = 0
        domain_folders = self._get_domain_folders()
        
        if not domain_folders:
            logger.warning("Nisu pronađeni domeni za sinhronizaciju!")
        
        for domain_folder in domain_folders:
            copied = self.sync_domain_folder(domain_folder)
            total_copied += copied
        
        elapsed_time = time.time() - start_time
        logger.info(f"Sinhronizacija završena. Ukupno kopirano {total_copied} slika za {elapsed_time:.2f} sekundi.")
        return total_copied

def main():
    parser = argparse.ArgumentParser(description='Sinhronizacija slika lica iz razvoja u produkciju')
    parser.add_argument('--source', default='storage/recognized_faces', help='Izvorni direktorijum (default: storage/recognized_faces)')
    parser.add_argument('--target', default='storage/recognized_faces_prod', help='Ciljni direktorijum (default: storage/recognized_faces_prod)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Detaljniji ispis')
    parser.add_argument('--skip-init', action='store_true', help='Preskoči inicijalizaciju prepoznavanja lica')
    
    args = parser.parse_args()
    
    # Podesi nivo logovanja
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Kreiraj i pokreni sinhronizator
    syncer = FacesSynchronizer(args.source, args.target)
    
    # Ako je zadat --skip-init, modifikuj metodu da preskoči inicijalizaciju
    if args.skip_init:
        logger.info("Preskačem inicijalizaciju prepoznavanja lica")
        original_sync_method = syncer.sync_domain_folder
        
        def sync_without_init(domain_folder):
            result = original_sync_method(domain_folder)
            return result
            
        syncer.sync_domain_folder = sync_without_init
    
    syncer.sync_all()

if __name__ == "__main__":
    main() 