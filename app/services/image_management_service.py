import os
import logging
import datetime

logger = logging.getLogger(__name__)

class ImageManagementService:
    """
    Service for handling image management operations (edit, delete)
    """
    
    def __init__(self):
        self.base_storage_path = 'storage/recognized_faces_prod'
    
    def delete_image(self, filename, domain):
        """
        Delete an image from the recognized_faces_prod directory
        
        Args:
            filename: The filename of the image to delete
            domain: The domain identifier
            
        Returns:
            dict: Information about the deleted image
        """
        try:
            # Construct the full path to the image
            domain_path = os.path.join(self.base_storage_path, domain)
            full_path = os.path.join(domain_path, filename)
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.warning(f"Image not found for deletion: {full_path}")
                return {
                    "deleted": False,
                    "filename": filename,
                    "path": full_path,
                    "reason": "File not found"
                }
            
            # Delete the file
            os.remove(full_path)
            logger.info(f"Successfully deleted image: {full_path}")
            
            return {
                "deleted": True,
                "filename": filename,
                "path": full_path
            }
            
        except Exception as e:
            logger.error(f"Error deleting image {filename}: {str(e)}")
            raise
    
    def edit_image(self, filename, person, domain):
        """
        Edit an image's person name and update metadata
        
        Args:
            filename: The filename of the image to edit
            person: The new person name for the image
            domain: The domain identifier
            
        Returns:
            dict: Information about the edited image
        """
        try:
            # Construct the full path to the image
            domain_path = os.path.join(self.base_storage_path, domain)
            full_path = os.path.join(domain_path, filename)
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.warning(f"Image not found for editing: {full_path}")
                return {
                    "edited": False,
                    "filename": filename,
                    "path": full_path,
                    "reason": "File not found",
                    "message": f"Image not found: {filename}"
                }
            
            # Normalize the person name (remove special characters, preserve capitalization)
            normalized_person = self._normalize_person_name(person)
            
            # Extract parts from the original filename
            # Format: Radmila_Marinkovic_2025-03-25_1744708784728.jpg
            import re
            
            # Try to find the date pattern in the filename
            date_pattern = r'_(\d{4}-\d{2}-\d{2}_\d+)'
            match = re.search(date_pattern, filename)
            
            if match:
                # If date pattern found, preserve the date and ID part
                date_id_part = match.group(1)
                file_extension = os.path.splitext(filename)[1].lower()
                new_filename = f"{normalized_person}_{date_id_part}{file_extension}"
            else:
                # Fallback if the filename doesn't match expected pattern
                file_extension = os.path.splitext(filename)[1].lower()
                timestamp = int(datetime.datetime.now().timestamp())
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                new_filename = f"{normalized_person}_{today}_{timestamp}{file_extension}"
            
            # Check if the new filename would be the same as the old one (ignoring case)
            if filename.lower() == new_filename.lower():
                # If they're the same, add a timestamp to make it unique
                timestamp = int(datetime.datetime.now().timestamp())
                name_part, ext_part = os.path.splitext(new_filename)
                new_filename = f"{name_part}_{timestamp}{ext_part}"
            
            new_full_path = os.path.join(domain_path, new_filename)
            
            # Rename the file
            import shutil
            shutil.copy2(full_path, new_full_path)  # Copy with metadata
            os.remove(full_path)  # Remove original
            
            logger.info(f"Successfully edited image: {filename} -> {new_filename} (Person: {person})")
            
            return {
                "edited": True,
                "original_filename": filename,
                "new_filename": new_filename,
                "original_path": full_path,
                "new_path": new_full_path,
                "person": person,
                "normalized_person": normalized_person,
                "message": f"Image successfully edited: {filename} -> {new_filename}"
            }
            
        except Exception as e:
            logger.error(f"Error editing image {filename}: {str(e)}")
            raise

    def _normalize_person_name(self, person_name):
        """
        Normalize a person name by replacing spaces with underscores
        and transliterating non-English characters to their English equivalents
        
        Args:
            person_name: The person name to normalize
            
        Returns:
            str: The normalized person name
        """
        import re
        import unicodedata
        
        # Transliterate non-ASCII characters to their ASCII equivalents
        # For example: 'ć' -> 'c', 'č' -> 'c', 'đ' -> 'd', etc.
        normalized = ''
        for char in person_name:
            if ord(char) < 128:  # ASCII characters
                normalized += char
            else:
                # Special handling for Serbian characters
                if char == 'ć' or char == 'č':
                    normalized += 'c'
                elif char == 'đ':
                    normalized += 'd'
                elif char == 'š':
                    normalized += 's'
                elif char == 'ž':
                    normalized += 'z'
                elif char == 'Ć' or char == 'Č':
                    normalized += 'C'
                elif char == 'Đ':
                    normalized += 'D'
                elif char == 'Š':
                    normalized += 'S'
                elif char == 'Ž':
                    normalized += 'Z'
                else:
                    # For other non-ASCII characters, try to decompose them
                    # For example: 'é' -> 'e'
                    ascii_char = unicodedata.normalize('NFKD', char).encode('ASCII', 'ignore').decode('ASCII')
                    normalized += ascii_char if ascii_char else '_'
        
        # Replace spaces with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        # Replace other problematic characters for filenames
        normalized = re.sub(r'[/\\:*?"<>|]', '_', normalized)
        # Replace multiple underscores with a single one
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        return normalized