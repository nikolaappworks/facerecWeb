import os
import pandas as pd
from flask import current_app
import json

class ExcelService:
    def __init__(self, excel_path=None):
        self.excel_path = excel_path or os.getenv('EXCEL_FILE_PATH', 'storage/excel/data.xlsx')
    
    def process_excel_file(self):
        """
        Process the Excel file:
        1. Read the first row
        2. Remove the first row
        3. Save the updated Excel file
        4. Return the data from the first row
        """
        try:
            # Check if file exists
            if not os.path.exists(self.excel_path):
                current_app.logger.error(f"Excel file not found at {self.excel_path}")
                return None
            
            # Read the Excel file
            df = pd.read_excel(self.excel_path)
            
            # Check if file has data
            if df.empty:
                current_app.logger.warning(f"Excel file is empty: {self.excel_path}")
                return None
            
            # Get the first row
            first_row = df.iloc[0]
            
            # Remove the first row
            df = df.iloc[1:].reset_index(drop=True)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.excel_path), exist_ok=True)
            
            # Save the updated Excel file
            df.to_excel(self.excel_path, index=False)
            
            # Get original values
            original_name = first_row['name'] if 'name' in first_row else ""
            original_last_name = first_row['last_name'] if 'last_name' in first_row else ""
            original_occupation = first_row['occupation'] if 'occupation' in first_row else ""
            
            # Normalize values for search
            normalized_name = self._normalize_text(original_name)
            normalized_last_name = self._normalize_text(original_last_name)
            normalized_occupation = self._normalize_text(original_occupation)
            
            # Create a key for the name mapping
            normalized_key = f"{normalized_name}_{normalized_last_name}"
            original_value = f"{original_name} {original_last_name}"
            
            # Save the original name to the mapping file
            self._save_name_mapping(normalized_key, original_value)
            
            # Return the extracted data
            return {
                'name': normalized_name,
                'last_name': normalized_last_name,
                'occupation': normalized_occupation,
                'original_name': original_name,
                'original_last_name': original_last_name,
                'original_occupation': original_occupation
            }
            
        except Exception as e:
            current_app.logger.error(f"Error processing Excel file: {str(e)}")
            raise Exception(f"Failed to process Excel file: {str(e)}")
    
    def _normalize_text(self, text):
        """
        Normalize text by removing special characters and converting to ASCII
        """
        if pd.isna(text) or text is None:
            return ""
        
        import unicodedata
        import re
        
        # Convert to string if not already
        text = str(text)
        
        # Normalize unicode characters
        normalized = unicodedata.normalize('NFKD', text)
        
        # Remove accents
        ascii_text = ''.join([c for c in normalized if not unicodedata.combining(c)])
        
        # Replace any remaining non-ASCII characters with closest ASCII equivalent
        ascii_text = unicodedata.normalize('NFKC', ascii_text.encode('ascii', 'ignore').decode('ascii'))
        
        # Remove any characters that aren't alphanumeric or spaces
        ascii_text = re.sub(r'[^\w\s]', '', ascii_text)
        
        return ascii_text.strip()

    def _save_name_mapping(self, normalized_key, original_value):
        """
        Save the mapping between normalized name and original name to a JSON file
        """
        mapping_file = os.path.join('storage', 'name_mapping.json')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
        
        # Load existing mapping if it exists
        mapping = {}
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            except Exception as e:
                current_app.logger.error(f"Error loading name mapping file: {str(e)}")
        
        # Add new mapping
        mapping[normalized_key] = original_value
        
        # Save updated mapping
        try:
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            current_app.logger.info(f"Saved name mapping: {normalized_key} -> {original_value}")
        except Exception as e:
            current_app.logger.error(f"Error saving name mapping file: {str(e)}") 