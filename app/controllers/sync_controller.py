import os
import shutil
import logging
from app.services.recognition_service import RecognitionService
from app.controllers.recognition_controller import RecognitionController
from app.services.background_service import BackgroundService

logger = logging.getLogger(__name__)

class SyncController:
    # Dozvoljene ekstenzije slika
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
    
    @staticmethod
    def is_image_file(filename):
        """Proverava da li je fajl slika na osnovu ekstenzije"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in SyncController.ALLOWED_EXTENSIONS
    
    @staticmethod
    def sync_faces(source_dir='storage/recognized_faces', target_dir='storage/recognized_faces_prod', test_image_path=None):
        """
        Sinhronizuje slike iz izvornog u ciljni direktorijum
        """
        try:
            logger.info(f"Započinjem sinhronizaciju iz {source_dir} u {target_dir}")
            
            # Osiguraj da ciljni direktorijum postoji
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                logger.info(f"Kreiran glavni ciljni direktorijum: {target_dir}")
            
            # Dobavi listu domen foldera
            if not os.path.exists(source_dir):
                logger.error(f"Izvorni direktorijum ne postoji: {source_dir}")
                return {"error": "Izvorni direktorijum ne postoji"}
                
            domain_folders = [f for f in os.listdir(source_dir) 
                             if os.path.isdir(os.path.join(source_dir, f))]
            logger.info(f"Pronađeni domeni: {domain_folders}")
            
            if not domain_folders:
                logger.warning("Nisu pronađeni domeni za sinhronizaciju!")
                return {"message": "Nisu pronađeni domeni za sinhronizaciju"}
            
            # Sinhronizuj svaki domen folder
            total_copied = 0
            results = []
            
            for domain_folder in domain_folders:
                domain_result = SyncController.sync_domain_folder(
                    domain_folder, 
                    source_dir, 
                    target_dir, 
                    test_image_path
                )
                total_copied += domain_result["copied_count"]
                results.append(domain_result)
            
            return {
                "message": f"Sinhronizacija završena. Ukupno kopirano {total_copied} slika.",
                "total_copied": total_copied,
                "domain_results": results
            }
            
        except Exception as e:
            logger.error(f"Greška pri sinhronizaciji: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def sync_domain_folder(domain_folder, source_dir, target_dir, test_image_path=None):
        """Sinhronizuje slike za jedan domen i briše originale nakon kopiranja"""
        source_domain_path = os.path.join(source_dir, domain_folder)
        target_domain_path = os.path.join(target_dir, domain_folder)
        
        # Konstante za limite slika
        MAX_TOTAL_IMAGES = 40
        MAX_DAILY_IMAGES = 3
        
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
            source_images = {f for f in all_source_files if SyncController.is_image_file(f)}
            logger.info(f"Ukupno fajlova: {len(all_source_files)}, od toga slika: {len(source_images)}")
        except Exception as e:
            logger.error(f"Greška pri čitanju izvornog foldera: {str(e)}")
            return {"domain": domain_folder, "error": str(e), "copied_count": 0}
            
        try:
            all_target_files = os.listdir(target_domain_path) if os.path.exists(target_domain_path) else []
            # Filtriraj samo slike
            target_images = {f for f in all_target_files if SyncController.is_image_file(f)}
            logger.info(f"Broj slika u ciljnom folderu: {len(target_images)}")
        except Exception as e:
            logger.error(f"Greška pri čitanju ciljnog foldera: {str(e)}")
            target_images = set()
        
        # Pronađi nove slike koje treba kopirati
        new_images = source_images - target_images
        logger.info(f"Broj novih slika za kopiranje: {len(new_images)}")
        
        if not new_images:
            logger.info(f"Nema novih slika za domen: {domain_folder}")
            return {"domain": domain_folder, "message": "Nema novih slika", "copied_count": 0}
        
        # Kopiraj nove slike i briši originale
        copied_count = 0
        copied_images = []
        skipped_images = []
        
        # Funkcija za izvlačenje imena osobe i datuma iz naziva fajla
        def extract_person_and_date(filename):
            try:
                # Pretpostavljamo format: ime_osobe_YYYYMMDD.jpg ili ime_osobe_YYYY-MM-DD.jpg
                parts = filename.split('_')
                
                # Tražimo deo koji izgleda kao datum
                date_part = None
                person_parts = []
                
                for part in parts:
                    # Proveri da li deo izgleda kao datum (YYYYMMDD ili YYYY-MM-DD)
                    if (len(part) >= 8 and part[0:4].isdigit()) or '-' in part:
                        date_part = part.split('.')[0]  # Ukloni ekstenziju ako je deo sa datumom
                        break
                    person_parts.append(part)
                
                # Ako nismo našli datum, vraćamo None
                if not date_part:
                    return None, None
                    
                person_name = '_'.join(person_parts)
                return person_name, date_part
            except Exception:
                return None, None
        
        # Funkcija za brojanje slika po osobi
        def count_images_for_person(person_name, target_images):
            count = 0
            for img in target_images:
                img_person, _ = extract_person_and_date(img)
                if img_person == person_name:
                    count += 1
            return count
        
        # Funkcija za brojanje slika po osobi i datumu
        def count_images_for_person_on_date(person_name, date_str, target_images):
            count = 0
            for img in target_images:
                img_person, img_date = extract_person_and_date(img)
                if img_person == person_name and img_date == date_str:
                    count += 1
            return count
        
        # Sortiraj slike po datumu (novije prvo) da bismo zadržali najnovije slike
        sorted_new_images = sorted(new_images, reverse=True)
        
        for image in sorted_new_images:
            source_path = os.path.join(source_domain_path, image)
            target_path = os.path.join(target_domain_path, image)
            
            # Proveri da li je fajl (ne folder) i da li je slika
            if os.path.isfile(source_path) and SyncController.is_image_file(image):
                try:
                    # Izvuci ime osobe i datum iz naziva fajla
                    person_name, date_str = extract_person_and_date(image)
                    
                    if not person_name or not date_str:
                        logger.warning(f"Nije moguće izvući ime osobe ili datum iz naziva fajla: {image}")
                        # Kopiraj sliku bez provere limita
                        shutil.copy2(source_path, target_path)
                        copied_count += 1
                        copied_images.append(image)
                        logger.info(f"Kopirana slika (bez provere limita): {image}")
                        
                        # Obriši original
                        if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(source_path):
                            os.remove(source_path)
                            logger.info(f"Obrisan original: {image}")
                        continue
                    
                    # Proveri ukupan broj slika za osobu
                    total_images = count_images_for_person(person_name, target_images)
                    logger.info(f"Trenutni ukupan broj slika za {person_name}: {total_images}")
                    
                    if total_images >= MAX_TOTAL_IMAGES:
                        logger.info(f"Preskačem kopiranje: {person_name} već ima {MAX_TOTAL_IMAGES} sačuvanih slika.")
                        # Obriši original bez kopiranja
                        os.remove(source_path)
                        logger.info(f"Obrisan original (limit slika): {image}")
                        skipped_images.append({"image": image, "reason": f"Person image limit reached ({MAX_TOTAL_IMAGES} images)"})
                        continue
                    
                    # Proveri broj slika za osobu na taj datum
                    daily_images = count_images_for_person_on_date(person_name, date_str, target_images)
                    logger.info(f"Trenutni broj dnevnih slika za {person_name} na datum {date_str}: {daily_images}")
                    
                    if daily_images >= MAX_DAILY_IMAGES:
                        logger.info(f"Preskačem kopiranje: Već postoji {MAX_DAILY_IMAGES} slika za {person_name} na datum {date_str}.")
                        # Obriši original bez kopiranja
                        os.remove(source_path)
                        logger.info(f"Obrisan original (dnevni limit): {image}")
                        skipped_images.append({"image": image, "reason": f"Daily image limit reached ({MAX_DAILY_IMAGES} images)"})
                        continue
                    
                    # Kopiraj sliku ako su svi limiti zadovoljeni
                    shutil.copy2(source_path, target_path)
                    copied_count += 1
                    copied_images.append(image)
                    logger.info(f"Kopirana slika: {image}")
                    
                    # Dodaj sliku u listu ciljnih slika za tačno brojanje
                    target_images.add(image)
                    
                    # Obriši original
                    if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(source_path):
                        os.remove(source_path)
                        logger.info(f"Obrisan original: {image}")
                    else:
                        logger.warning(f"Kopiranje nije uspelo, original nije obrisan: {image}")
                    
                except Exception as e:
                    logger.error(f"Greška pri kopiranju/brisanju {image}: {str(e)}")
        
        logger.info(f"Kopirano i obrisano {copied_count} slika za domen: {domain_folder}")
        logger.info(f"Preskočeno {len(skipped_images)} slika zbog limita")
        
        # Inicijalizuj prepoznavanje lica nakon kopiranja
        recognition_result = None
        if copied_count > 0 and test_image_path and os.path.exists(test_image_path):
            try:
                # Učitaj test sliku
                with open(test_image_path, 'rb') as f:
                    test_image_bytes = f.read()
                
                # Pozovi prepoznavanje lica
                recognition_result = RecognitionController.recognize_face(test_image_bytes, domain_folder)
                logger.info(f"Inicijalizacija prepoznavanja lica za domen {domain_folder} uspešna")
            except Exception as e:
                logger.error(f"Greška pri inicijalizaciji prepoznavanja lica za domen {domain_folder}: {str(e)}")
                recognition_result = {"error": str(e)}
        
        return {
            "domain": domain_folder,
            "copied_count": copied_count,
            "copied_images": copied_images,
            "skipped_images": skipped_images,
            "recognition_result": recognition_result
        }
    
    @staticmethod
    def sync_faces_background(source_dir='storage/recognized_faces', target_dir='storage/recognized_faces_prod', test_image_path=None):
        """
        Pokreće sinhronizaciju u pozadini
        """
        # Pokreni sinhronizaciju u pozadini
        BackgroundService.run_in_background(
            SyncController.sync_faces,
            source_dir,
            target_dir,
            test_image_path
        )
        
        return {
            "message": "Sinhronizacija pokrenuta u pozadini",
            "source_dir": source_dir,
            "target_dir": target_dir
        } 