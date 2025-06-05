#!/usr/bin/env python3
"""
Skripta za testiranje face recognition funkcionalnosti.
Učitava test sliku i poziva RecognitionService.recognize_face().
"""

import os
import sys
import logging

# Dodaj parent direktorijum u Python path da možemo importovati app module
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from app.services.recognition_service import RecognitionService

# Podesi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def test_face_recognition():
    """
    Testira face recognition na test slici
    """
    try:
        # Putanja do test slike
        test_image_path = os.path.join(script_dir, 'test_face.JPG')
        
        # Provjeri da li test slika postoji
        if not os.path.exists(test_image_path):
            logger.error(f"Test slika ne postoji na putanji: {test_image_path}")
            return False
            
        logger.info(f"Učitavam test sliku: {test_image_path}")
        
        # Učitaj test sliku kao bytes
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
            
        logger.info(f"Test slika učitana, veličina: {len(image_bytes)} bytes")
        
        # Test domain - možeš promeniti ovo
        test_domain = "media24"
        
        logger.info(f"Pokretam face recognition za domain: {test_domain}")
        
        # Pozovi face recognition
        result = RecognitionService.recognize_face(image_bytes, test_domain)
        
        # Prikaži rezultat
        logger.info("="*50)
        logger.info("REZULTAT FACE RECOGNITION:")
        logger.info("="*50)
        
        if result.get("status") == "success":
            logger.info(f"✅ USPEH: {result.get('message')}")
            logger.info(f"Prepoznata osoba: {result.get('person')}")
            
            if "best_match" in result:
                confidence = result["best_match"]["confidence_metrics"]["confidence_percentage"]
                logger.info(f"Pouzdanost: {confidence}%")
                
            if "recognized_persons" in result:
                logger.info(f"Broj prepoznatih osoba: {len(result['recognized_persons'])}")
                for person in result["recognized_persons"]:
                    logger.info(f"- {person['name']}")
        else:
            logger.warning(f"❌ GREŠKA: {result.get('message')}")
            
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"Greška tokom testiranja: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Pokretanje test skripte za face recognition...")
    
    success = test_face_recognition()
    
    if success:
        logger.info("Test završen uspešno!")
    else:
        logger.error("Test neuspešan!")
        sys.exit(1) 