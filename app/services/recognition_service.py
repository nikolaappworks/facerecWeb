import os
import time
import logging
from collections import defaultdict
from deepface import DeepFace
from PIL import Image
import numpy as np

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
            
            # Očisti domain za putanju
            clean_domain = RecognitionService.clean_domain_for_path(domain)
            
            # Kreiraj privremeni folder za domain ako ne postoji
            temp_folder = os.path.join('uploads', clean_domain)
            os.makedirs(temp_folder, exist_ok=True)
            
            # Sačuvaj sliku privremeno
            image_path = os.path.join(temp_folder, f"temp_recognition_{int(time.time() * 1000)}.jpg")
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Image saved temporarily at: {image_path}")
            
            try:
                # Definišemo parametre
                model_name = "VGG-Face"
                detector_backend = "retinaface"
                distance_metric = "cosine"
                db_path = os.path.join('recognized_faces', clean_domain)
                
                logger.info("Building VGG-Face model...")
                _ = DeepFace.build_model("VGG-Face")
                logger.info("Model built")
                
                # Izvršavamo prepoznavanje bez batched parametra
                dfs = DeepFace.find(
                    img_path=image_path,
                    db_path=db_path,
                    model_name=model_name,
                    detector_backend=detector_backend,
                    distance_metric=distance_metric,
                    enforce_detection=False,
                    threshold=0.4,
                    silent=False
                )
                
                # Analiziramo rezultate
                result = RecognitionService.analyze_recognition_results(dfs)
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
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Cleaned up temporary file: {image_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")

    @staticmethod
    def analyze_recognition_results(results, threshold=0.4):
        """
        Analizira rezultate prepoznavanja i vraća najverovatnije ime.
        """
        name_scores = defaultdict(list)
        all_matches = defaultdict(list)
        
        logger.info("Analyzing recognition results...")
        
        # Provera da li je results None ili prazan
        if results is None or len(results) == 0:
            logger.info("No results to analyze")
            return {"message": "No matches found"}
        
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
                                name = full_path.split('/')[-1].split('_')[0]
                                # Ako je Windows putanja
                                if '\\' in full_path:
                                    name = full_path.split('\\')[-1].split('_')[0]
                                    
                                normalized_name = ' '.join(sorted(set(name.split())))
                                
                                # Store all matches
                                all_matches[normalized_name].append(distance)
                                logger.debug(f"Found match: {normalized_name} with distance {distance}")
                                
                                # Store matches that pass threshold
                                if distance < threshold:
                                    name_scores[normalized_name].append(distance)
                                    logger.debug(f"Match passed threshold: {normalized_name} with distance {distance}")
                            except Exception as e:
                                logger.warning(f"Error processing row: {str(e)}")
                                continue
            else:
                logger.error(f"Unexpected results format: {type(results)}")
                return {"message": "Unexpected results format"}
                
        except Exception as e:
            logger.error(f"Error processing results: {str(e)}")
            return {"message": "Error processing recognition results"}

        # Log summary of all matches found
        logger.info(f"Total unique names found (before threshold): {len(all_matches)}")
        for name, distances in all_matches.items():
            logger.info(f"All matches for {name}: {len(distances)} occurrences, distances: {distances}")

        # Process matches that passed threshold
        if not name_scores:
            logger.info(f"No matches found within threshold {threshold}")
            # Return all matches even if none passed threshold
            return {
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
        
        return {
            "message": f"Face recognized as: {best_name}",
            "best_match": {
                "person_name": best_name,
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