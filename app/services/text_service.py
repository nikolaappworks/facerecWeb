import unicodedata
import re

class TextService:
    @staticmethod
    def normalize_text(text):
        """
        Normalizuje tekst uklanjanjem dijakritičkih znakova i zamenom specijalnih karaktera
        """
        if not text:
            return text
            
        # Prvo normalizujemo unicode karaktere
        normalized = unicodedata.normalize('NFKD', text)
        
        # Uklanjamo dijakritičke znakove
        normalized = ''.join([c for c in normalized if not unicodedata.combining(c)])
        
        # Zamena specifičnih karaktera
        replacements = {
            'ć': 'c', 'č': 'c', 'đ': 'dj', 'š': 's', 'ž': 'z',
            'Ć': 'C', 'Č': 'C', 'Đ': 'Dj', 'Š': 'S', 'Ž': 'Z',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
            'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U'
        }
        
        for char, replacement in replacements.items():
            normalized = normalized.replace(char, replacement)
        
        # Uklanjamo sve karaktere koji nisu alfanumerički ili razmak
        normalized = re.sub(r'[^a-zA-Z0-9\s_-]', '', normalized)
        
        # Zamenjujemo više uzastopnih razmaka jednim razmakom
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Uklanjamo razmake na početku i kraju
        normalized = normalized.strip()
        
        # Zamenjujemo razmake donjom crtom za nazive fajlova
        normalized = normalized.replace(' ', '_')
        
        return normalized 