import os
import json
import logging
import requests
import threading
from app.services.image_service import ImageService
from app.services.background_service import BackgroundService
from dotenv import load_dotenv
from app.services.text_service import TextService

# Učitavanje .env fajla
load_dotenv()

logger = logging.getLogger(__name__)

class KyloService:
    @staticmethod
    def fetch_images_from_kylo():
        """
        Preuzima slike sa Kylo API-ja.
        
        Returns:
            list: Lista metapodataka o slikama
        """
        api_url = "https://media24.kylo.space/api/v1/getImagesForPython"
        api_token = "7|SRvNn5DOZN42K51ije6vl4WwnaTRgqk0Ym92guoM"
        
        try:
            headers = {
                'Authorization': f'Bearer {api_token}'
            }
            
            logger.info(f"Preuzimanje slika sa URL-a: {api_url}")
            
            response = requests.get(api_url, headers=headers)
            
            logger.info(f"Status kod odgovora: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Greška pri preuzimanju slika: Status {response.status_code}, Odgovor: {response.text}")
                return []
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Greška pri parsiranju JSON odgovora: {e}")
                return []
            
            if 'data' not in data:
                logger.error("Polje 'data' nije pronađeno u odgovoru API-ja.")
                return []
            
            logger.info(f"Uspešno preuzeto {len(data.get('data', []))} slika sa Kylo API-ja.")
            return data.get("data", [])
            
        except requests.RequestException as e:
            logger.error(f"Greška pri slanju API zahteva: {e}")
            return []
    
    @staticmethod
    def download_image_from_kylo(image_id):
        """
        Preuzima sadržaj slike sa Kylo sistema na osnovu ID-a i loguje detalje odgovora.
        
        Args:
            image_id (str): ID slike za preuzimanje
            
        Returns:
            bytes: Sadržaj slike ili None ako preuzimanje nije uspelo
        """
        api_url = f"https://media24.kylo.space/api/v1/assets/{image_id}/download/original"
        api_token = "7|SRvNn5DOZN42K51ije6vl4WwnaTRgqk0Ym92guoM"
        
        try:
            headers = {
                'Authorization': f'Bearer {api_token}'
            }
            
            logger.info(f"Preuzimanje slike ID: {image_id}")
            
            response = requests.get(api_url, headers=headers)
            
            # Logujemo detalje odgovora
            logger.info(f"Status kod odgovora za sliku {image_id}: {response.status_code}")
            logger.info(f"Zaglavlja odgovora za sliku {image_id}: {dict(response.headers)}")
            
            # Ako je odgovor uspešan, logujemo tip sadržaja i veličinu
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'Nepoznat')
                content_length = len(response.content)
                logger.info(f"Tip sadržaja za sliku {image_id}: {content_type}")
                logger.info(f"Veličina sadržaja za sliku {image_id}: {content_length} bajtova")
                return response.content
            else:
                # Ako je odgovor neuspešan, pokušavamo da logujemo tekst odgovora
                try:
                    error_text = response.text[:500]  # Prvih 500 karaktera
                    logger.error(f"Greška pri preuzimanju slike {image_id}: Status {response.status_code}, Odgovor: {error_text}")
                except:
                    logger.error(f"Greška pri preuzimanju slike {image_id}: Status {response.status_code}, Nije moguće prikazati odgovor")
                return None
            
        except requests.RequestException as e:
            logger.error(f"Greška pri preuzimanju slike {image_id}: {e}")
            return None
    
    @staticmethod
    def process_single_image_from_kylo(image_info, domain):
        """
        Obrađuje jednu sliku sa Kylo sistema.
        
        Args:
            image_info (dict): Metapodaci o slici
            domain (str): Domen za koji se obrađuje slika
            
        Returns:
            dict: Rezultat obrade
        """
        try:
            image_id = image_info["id"]
            person = image_info.get("person", "")
            created_date = image_info.get("created_date", None)
            
            # Normalizacija imena osobe koristeći postojeću metodu normalize_text
            normalized_person = TextService.normalize_text(person) if person else ""
            
            logger.info(f"Obrada slike ID: {image_id}, Osoba: {person}, Normalizovano: {normalized_person}")
            
            # Preuzimanje sadržaja slike
            image_content = KyloService.download_image_from_kylo(image_id)
            
            if not image_content:
                logger.error(f"Neuspešno preuzimanje slike: {image_id}")
                return {"status": "error", "message": f"Neuspešno preuzimanje slike: {image_id}"}
            
            # Kreiranje privremenog fajla
            from io import BytesIO
            from datetime import datetime
            
            image_file = BytesIO(image_content)
            image_file.filename = f"{normalized_person}_{image_id}.jpg"
            
            # Konvertovanje created_date u datetime objekat ako je string
            if isinstance(created_date, str):
                try:
                    # Pokušaj različite formate datuma
                    date_formats = [
                        '%Y-%m-%d',           # npr. 2025-04-03
                        '%d-%m-%Y %H:%M:%S',  # npr. 03-04-2025 09:20:08
                        '%d-%m-%Y',           # npr. 03-04-2025
                        '%d.%m.%Y %H:%M:%S',  # npr. 03.04.2025 09:20:08
                        '%d.%m.%Y'            # npr. 03.04.2025
                    ]
                    
                    parsed_date = None
                    for date_format in date_formats:
                        try:
                            parsed_date = datetime.strptime(created_date, date_format)
                            logger.info(f"Uspešno parsiran datum '{created_date}' koristeći format '{date_format}'")
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date:
                        created_date = parsed_date
                    else:
                        logger.warning(f"Neispravan format datuma: {created_date}, koristim trenutni datum")
                        created_date = datetime.now()
                except Exception as e:
                    logger.warning(f"Greška pri parsiranju datuma {created_date}: {str(e)}, koristim trenutni datum")
                    created_date = datetime.now()
            elif created_date is None:
                created_date = datetime.now()
            
            # Obrada slike
            result = ImageService.process_image_async(
                image_file=image_file,
                person=normalized_person,  # Koristimo normalizovano ime
                created_date=created_date,
                domain=domain
            )
            
            return {"status": "success", "message": f"Slika {image_id} poslata na obradu", "image_id": image_id}
            
        except Exception as e:
            logger.error(f"Greška pri obradi slike {image_info.get('id')}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def process_images_from_kylo(images_data, domain):
        """
        Asinhrono obrađuje slike sa Kylo sistema koristeći thread-ove.
        
        Args:
            images_data (list): Lista metapodataka o slikama
            domain (str): Domen za koji se obrađuju slike
            
        Returns:
            dict: Rezultat pokretanja asinhrone obrade
        """
        def process_batch(batch):
            for image_info in batch:
                try:
                    KyloService.process_single_image_from_kylo(image_info, domain)
                except Exception as e:
                    logger.error(f"Greška pri obradi slike u batch-u: {str(e)}")
        
        try:
            # Provera dostupnosti slika pre obrade
            available_images = []
            unavailable_count = 0
            
            # Prvo proverimo koje slike su dostupne
            for image_info in images_data:
                image_id = image_info["id"]
                # Samo proverimo da li je slika dostupna
                test_content = KyloService.download_image_from_kylo(image_id)
                if test_content:
                    available_images.append(image_info)
                else:
                    unavailable_count += 1
                    logger.info(f"Slika {image_id} nije dostupna, preskačem")
            
            if not available_images:
                logger.info("Nema dostupnih slika za obradu.")
                return {
                    "status": "success", 
                    "message": "Nema dostupnih slika za obradu", 
                    "total": len(images_data),
                    "unavailable": unavailable_count
                }
            
            # Broj thread-ova za paralelnu obradu
            num_threads = 4
            
            # Podela slika u batch-eve za thread-ove
            batch_size = max(1, len(available_images) // num_threads)
            batches = [available_images[i:i + batch_size] for i in range(0, len(available_images), batch_size)]
            
            # Pokretanje thread-ova za obradu batch-eva
            for batch in batches:
                # Koristimo samo BackgroundService za pokretanje thread-a
                BackgroundService.run_in_background(process_batch, batch)
            
            return {
                "status": "success", 
                "message": f"Pokrenuta obrada {len(available_images)} dostupnih slika u pozadini",
                "total": len(images_data),
                "available": len(available_images),
                "unavailable": unavailable_count
            }
            
        except Exception as e:
            logger.error(f"Greška pri pokretanju asinhrone obrade: {str(e)}")
            return {"status": "error", "message": str(e)} 