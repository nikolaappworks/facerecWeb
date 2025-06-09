import os
import time
import logging
from collections import defaultdict
from deepface import DeepFace
from PIL import Image
from io import BytesIO
import numpy as np
from app.services.image_service import ImageService

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

class RecognitionService:
    @staticmethod
    def clean_domain_for_path(domain):
        """Čisti domain string za korišćenje u putanjama"""
        # Ukloni port i nedozvoljene karaktere
        domain = domain.split(':')[0]  # Ukloni port
        # Zameni bilo koje nedozvoljene karaktere sa '_'
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            domain = domain.replace(char, '_')
        return domain

    @staticmethod
    def recognize_face(image_bytes, domain):
        """
        Prepoznaje lice iz prosleđene slike
        """
        try:
            logger.info("Starting face recognition process")
            start_time = time.time()
            
            # Prvo dobijamo dimenzije originalne slike
            from PIL import Image
            # Proverimo tip i izvučimo bytes ako je potrebno
            if hasattr(image_bytes, 'getvalue'):
                # Ako je BytesIO objekat
                actual_bytes = image_bytes.getvalue()
                image_bytes.seek(0)  # Reset pointer za slučaj da se koristi ponovo
            else:
                # Ako su već bytes
                actual_bytes = image_bytes
            
            original_image = Image.open(BytesIO(actual_bytes))
            original_width, original_height = original_image.size
            logger.info(f"Original image dimensions: {original_width}x{original_height}")
            
            # Smanjimo veličinu slike - proslijedi bytes
            resized_image = ImageService.resize_image(actual_bytes)
            
            # Dobijamo dimenzije smanjene slike
            resized_pil = Image.open(resized_image)
            resized_width, resized_height = resized_pil.size
            logger.info(f"Resized image dimensions: {resized_width}x{resized_height}")
            
            # Očisti domain za putanju
            clean_domain = RecognitionService.clean_domain_for_path(domain)
            
            # Kreiraj privremeni folder za domain ako ne postoji
            temp_folder = os.path.join('storage/uploads', clean_domain)
            os.makedirs(temp_folder, exist_ok=True)
            
            # Sačuvaj smanjenu sliku privremeno
            image_path = os.path.join(temp_folder, f"temp_recognition_{int(time.time() * 1000)}.jpg")
            with open(image_path, "wb") as f:
                f.write(resized_image.getvalue())
            logger.info(f"Resized image saved temporarily at: {image_path}")
            
            try:
                # Definišemo parametre
                model_name = "VGG-Face"
                detector_backend = "retinaface"
                distance_metric = "cosine"
                db_path = os.path.join('storage/recognized_faces_prod', clean_domain)
                
                logger.info("Building VGG-Face model...")
                _ = DeepFace.build_model("VGG-Face")
                logger.info("Model built")
                logger.info("DB path: " + db_path)
                
                # Izvršavamo prepoznavanje bez batched parametra
                dfs = DeepFace.find(
                    img_path=image_path,
                    db_path=db_path,
                    model_name=model_name,
                    detector_backend=detector_backend,
                    distance_metric=distance_metric,
                    enforce_detection=False,
                    align=True,
                    threshold=0.35,
                    silent=False
                )
                
                # Analiziramo rezultate sa dimenzijama slike
                result = RecognitionService.analyze_recognition_results(
                    dfs, 
                    threshold=0.35,
                    original_width=original_width,
                    original_height=original_height,
                    resized_width=resized_width,
                    resized_height=resized_height
                )
                logger.info(f"Recognition completed in {time.time() - start_time:.2f}s")
                return result
                
            except Exception as e:
                error_msg = f"Error during face recognition: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"Error in recognize_face: {str(e)}")
            raise
        finally:
            # Čišćenje
            try:
                if 'image_path' in locals() and os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Cleaned up temporary file: {image_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")

    @staticmethod
    def are_coordinates_similar(coord1, coord2, tolerance=10):
        """
        Proverava da li su koordinate dovoljno slične (u procentima).
        tolerance: razlika u procentima za x, y koordinate
        """
        if not coord1 or not coord2:
            return False
        
        x_diff = abs(coord1['x_percent'] - coord2['x_percent'])
        y_diff = abs(coord1['y_percent'] - coord2['y_percent'])
        
        return x_diff <= tolerance and y_diff <= tolerance
    
    @staticmethod
    def group_matches_by_coordinates(matches_with_coords, tolerance=10):
        """
        Grupira prepoznate osobe po sličnim koordinatama i zadržava samo onu sa najvećim confidence-om
        """
        if not matches_with_coords:
            return []
        
        grouped_matches = []
        used_indices = set()
        
        for i, match in enumerate(matches_with_coords):
            if i in used_indices:
                continue
                
            # Kreiraj grupu za trenutni match
            current_group = [match]
            used_indices.add(i)
            
            # Pronađi sve ostale matches sa sličnim koordinatama
            for j, other_match in enumerate(matches_with_coords):
                if j in used_indices:
                    continue
                    
                if RecognitionService.are_coordinates_similar(
                    match.get('face_coords'), 
                    other_match.get('face_coords'), 
                    tolerance
                ):
                    current_group.append(other_match)
                    used_indices.add(j)
            
            # Iz grupe izaberi match sa najmanjom distance (najvećim confidence-om)
            best_match_in_group = min(current_group, key=lambda x: x['distance'])
            grouped_matches.append(best_match_in_group)
            
            if len(current_group) > 1:
                logger.info(f"Grouped {len(current_group)} matches at similar coordinates, selected: {best_match_in_group['name']} (confidence: {round((1 - best_match_in_group['distance']) * 100, 2)}%)")
        
        return grouped_matches

    @staticmethod
    def analyze_recognition_results(results, threshold=0.4, original_width=None, original_height=None, resized_width=None, resized_height=None):
        """
        Analizira rezultate prepoznavanja i vraća najverovatnije ime.
        """
        name_scores = defaultdict(list)
        all_matches = defaultdict(list)
        face_coordinates_map = defaultdict(list)  # Nova mapa za koordinate
        matches_with_coords = []  # Lista svih match-ova sa koordinatama
        original_deepface_results = {}  # Čuva originalne DeepFace rezultate po imenu
        
        logger.info("Analyzing recognition results...")
        
        # Provera da li je results None ili prazan
        if results is None or len(results) == 0:
            logger.info("No results to analyze")
            return {"status": "error", "message": "No matches found"}
        
        try:
            logger.info(f"Results type: {type(results)}")
            
            # DeepFace.find vraća listu DataFrame-ova
            if isinstance(results, list):
                logger.info("Processing list of DataFrames")
                for df in results:
                    if hasattr(df, 'iterrows'):
                        for _, row in df.iterrows():
                            try:
                                distance = float(row['distance'])
                                full_path = row['identity']
                                
                                # Izvlačimo koordinate lica sa smanjene slike
                                face_coords = None
                                if all(dim is not None for dim in [original_width, original_height, resized_width, resized_height]):
                                    try:
                                        source_x = float(row['source_x'])
                                        source_y = float(row['source_y'])
                                        source_w = float(row['source_w'])
                                        source_h = float(row['source_h'])
                                        
                                        # Konvertujemo u procente originalne slike
                                        face_coords = {
                                            "x_percent": round((source_x / resized_width) * 100, 2),
                                            "y_percent": round((source_y / resized_height) * 100, 2),
                                            "width_percent": round((source_w / resized_width) * 100, 2),
                                            "height_percent": round((source_h / resized_height) * 100, 2)
                                        }
                                        logger.debug(f"Face coordinates: {face_coords}")
                                    except (KeyError, ValueError) as coord_error:
                                        logger.warning(f"Could not extract face coordinates: {coord_error}")
                                        face_coords = None
                                
                                # Izvlačimo ime osobe (sve do datuma)
                                if '\\' in full_path:  # Windows putanja
                                    filename = full_path.split('\\')[-1]
                                else:  # Unix putanja
                                    filename = full_path.split('/')[-1]
                                
                                # Uzimamo sve do prvog datuma (YYYYMMDD ili YYYY-MM-DD format)
                                name_parts = filename.split('_')
                                name = []
                                for part in name_parts:
                                    if len(part) >= 8 and (part[0:4].isdigit() or '-' in part):
                                        break
                                    name.append(part)
                                name = '_'.join(name)  # Koristimo donju crtu za spajanje
                                
                                normalized_name = name.strip()
                                
                                # Store match sa koordinatama za grupiranje
                                match_data = {
                                    'name': normalized_name,
                                    'distance': distance,
                                    'face_coords': face_coords,
                                    'full_path': full_path
                                }
                                matches_with_coords.append(match_data)
                                
                                # Čuvaj originalne DeepFace rezultate za svaku osobu
                                if normalized_name not in original_deepface_results:
                                    original_deepface_results[normalized_name] = []
                                original_deepface_results[normalized_name].append(dict(row))
                                
                                # Store all matches (za kompatibilnost)
                                all_matches[normalized_name].append(distance)
                                if face_coords:
                                    face_coordinates_map[normalized_name].append(face_coords)
                                logger.debug(f"Found match: {normalized_name} with distance {distance}")
                            except Exception as e:
                                logger.warning(f"Error processing row: {str(e)}")
                                continue
            else:
                logger.error(f"Unexpected results format: {type(results)}")
                return {"status": "error", "message": "Unexpected results format"}
                
        except Exception as e:
            logger.error(f"Error processing results: {str(e)}")
            return {"status": "error", "message": "Error processing recognition results"}

        # Grupiranje match-ova po koordinatama 
        logger.info(f"Total matches before grouping: {len(matches_with_coords)}")
        grouped_matches = RecognitionService.group_matches_by_coordinates(matches_with_coords, tolerance=10)
        logger.info(f"Total matches after grouping: {len(grouped_matches)}")
        
        # Kreiranje novih struktura podataka na osnovu grupiranih rezultata
        name_scores = defaultdict(list)
        all_matches = defaultdict(list)
        face_coordinates_map = defaultdict(list)
        
        for match in grouped_matches:
            name = match['name']
            distance = match['distance']
            face_coords = match['face_coords']
            
            # Store all matches
            all_matches[name].append(distance)
            if face_coords:
                face_coordinates_map[name].append(face_coords)
                
            # Store matches that pass threshold
            if distance < threshold:
                name_scores[name].append(distance)
                logger.debug(f"Grouped match passed threshold: {name} with distance {distance}")

        # Log summary of all matches found
        logger.info(f"\n{'='*50}")
        logger.info(f"RECOGNITION RESULTS:")
        logger.info(f"Total unique persons found: {len(all_matches)}")
        for name, distances in all_matches.items():
            avg_confidence = round((1 - sum(distances)/len(distances)) * 100, 2)
            logger.info(f"Person: {name}")
            logger.info(f"- Occurrences: {len(distances)}")
            logger.info(f"- Average confidence: {avg_confidence}%")
            logger.info(f"- Best confidence: {round((1 - min(distances)) * 100, 2)}%")
        logger.info(f"{'='*50}\n")

        # Process matches that passed threshold
        if not name_scores:
            logger.info(f"No matches found within threshold {threshold}")
            # Return all matches even if none passed threshold
            return {
                "status": "error",
                "message": "No matches within threshold",
                "all_detected_matches": [
                    {
                        "person_name": name,
                        "metrics": {
                            "occurrences": len(distances),
                            "average_distance": round(sum(distances) / len(distances), 4),
                            "min_distance": round(min(distances), 4),
                            "distances": distances
                        }
                    }
                    for name, distances in all_matches.items()
                ]
            }
        
        # Calculate statistics for matches that passed threshold
        name_statistics = {}
        for name, distances in name_scores.items():
            avg_distance = sum(distances) / len(distances)
            min_distance = min(distances)
            occurrences = len(distances)
            
            weighted_score = (avg_distance * 0.4) + (min_distance * 0.3) - (occurrences * 0.1)
            
            name_statistics[name] = {
                "occurrences": occurrences,
                "avg_distance": avg_distance,
                "min_distance": min_distance,
                "weighted_score": weighted_score,
                "distances": distances
            }
            
            logging.info(f"Threshold-passing matches for {name}:")
            logger.info(f"- Occurrences: {occurrences}")
            logger.info(f"- Average distance: {avg_distance:.4f}")
            logger.info(f"- Min distance: {min_distance:.4f}")
            logger.info(f"- Weighted score: {weighted_score:.4f}")
        
        # Find best match among threshold-passing matches
        best_match = min(name_statistics.items(), key=lambda x: x[1]['weighted_score'])
        best_name = best_match[0]
        stats = best_match[1]
        
        # Dodajemo ispis najboljeg podudaranja
        logger.info("\n" + "="*50)
        logger.info(f"BEST MATCH FOUND: {best_name}")
        logger.info(f"Confidence: {round((1 - stats['min_distance']) * 100, 2)}%")
        logger.info("="*50 + "\n")
        
        logger.info(f"Best match found: {best_name} with confidence {round((1 - stats['min_distance']) * 100, 2)}%")
        
        # Dobavi originalno ime osobe iz mapiranja
        from app.services.text_service import TextService
        original_person = TextService.get_original_text(best_name)
        
        # Ako je pronađeno originalno ime, koristi ga
        if original_person != best_name:
            logger.info(f"Found original name for {best_name}: {original_person}")
            display_name = original_person
        # Ako nije pronađeno originalno ime, a ime sadrži donju crtu, zameni je razmakom
        elif '_' in best_name:
            display_name = best_name.replace('_', ' ')
            logger.info(f"No mapping found, using formatted name: {display_name}")
        else:
            display_name = best_name
        
        # Kreiraj niz svih prepoznatih osoba koje su prošle threshold
        recognized_persons = []
        for person_name in name_scores.keys():
            original_person = TextService.get_original_text(person_name)
            if original_person != person_name:
                formatted_display_name = original_person
            elif '_' in person_name:
                formatted_display_name = person_name.replace('_', ' ')
            else:
                formatted_display_name = person_name
            
            # Uzmi samo prve koordinate za tu osobu (sve su iste jer se odnose na istu lokaciju na ulaznoj slici)
            coords_list = face_coordinates_map.get(person_name, [])
            face_coordinates = coords_list[0] if coords_list else None
            
            # Dodajemo objekat sa imenom i jednim setom koordinata
            person_obj = {
                "name": formatted_display_name,
                "face_coordinates": face_coordinates
            }
            recognized_persons.append(person_obj)
        
        logger.info(f"All recognized persons: {[p['name'] for p in recognized_persons]}")
        
        # Logiraj originalne DeepFace rezultate za finalne prepoznate osobe
        logger.info("\n" + "="*80)
        logger.info("ORIGINAL DEEPFACE RESULTS FOR FINAL RECOGNIZED PERSONS:")
        logger.info("="*80)
        for person_name in name_scores.keys():
            if person_name in original_deepface_results:
                logger.info(f"\nPerson: {person_name}")
                logger.info("-" * 50)
                for i, result in enumerate(original_deepface_results[person_name]):
                    logger.info(f"DeepFace Result #{i+1}:")
                    for key, value in result.items():
                        logger.info(f"  {key}: {value}")
                    logger.info("-" * 30)
        logger.info("="*80 + "\n")
        
        return {
            "status": "success",
            "message": f"Face recognized as: {display_name}",
            "person": display_name,  # Koristimo originalno ili formatirano ime
            "recognized_persons": recognized_persons,  # Novi niz objekata sa imenima i koordinatama
            "best_match": {
                "person_name": best_name,  # Originalno normalizovano ime
                "display_name": display_name,  # Ime za prikaz (originalno ili formatirano)
                "confidence_metrics": {
                    "occurrences": stats['occurrences'],
                    "average_distance": round(stats['avg_distance'], 4),
                    "min_distance": round(stats['min_distance'], 4),
                    "weighted_score": round(stats['weighted_score'], 4),
                    "confidence_percentage": round((1 - stats['min_distance']) * 100, 2),
                    "distances": stats['distances']
                }
            },
            "all_detected_matches": [
                {
                    "person_name": name,
                    "metrics": {
                        "occurrences": len(distances),
                        "average_distance": round(sum(distances) / len(distances), 4),
                        "min_distance": round(min(distances), 4),
                        "confidence_percentage": round((1 - min(distances)) * 100, 2),
                        "distances": distances
                    }
                }
                for name, distances in all_matches.items()
            ]
        }