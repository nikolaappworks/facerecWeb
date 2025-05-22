#!/usr/bin/env python
import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv

# Dodajte putanju do root direktorijuma aplikacije
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Sada možete uvesti module iz app
from app.services.openai_service import OpenAIService

# Učitavanje environment varijabli
load_dotenv()

class ExcelChecker:
    def __init__(self, source_excel_path=None, target_excel_path=None):
        """
        Inicijalizacija skripte za proveru imena iz Excel fajla
        
        Args:
            source_excel_path (str): Putanja do izvornog Excel fajla
            target_excel_path (str): Putanja do ciljnog Excel fajla
        """
        self.source_excel_path = source_excel_path or os.getenv('SOURCE_EXCEL_PATH', 'storage/excel/test.xlsx')
        self.target_excel_path = target_excel_path or os.getenv('TARGET_EXCEL_PATH', 'storage/excel/data.xlsx')
        
        print(f"Inicijalizacija skripte za proveru imena iz Excel fajla")
        print(f"Izvorni Excel: {self.source_excel_path}")
        print(f"Ciljni Excel: {self.target_excel_path}")

    def load_source_excel(self):
        """
        Učitavanje izvornog Excel fajla
        
        Returns:
            pandas.DataFrame: DataFrame sa podacima iz izvornog Excel fajla
        """
        try:
            if not os.path.exists(self.source_excel_path):
                print(f"Greška: Izvorni Excel fajl ne postoji na putanji: {self.source_excel_path}")
                return None
                
            df = pd.read_excel(self.source_excel_path)
            
            if df.empty:
                print(f"Upozorenje: Izvorni Excel fajl je prazan: {self.source_excel_path}")
                return None
                
            # Provera da li postoji kolona 'name'
            if 'name' not in df.columns:
                print(f"Greška: Izvorni Excel fajl nema kolonu 'name'")
                return None
                
            print(f"Uspešno učitan izvorni Excel fajl sa {len(df)} redova")
            return df
            
        except Exception as e:
            print(f"Greška prilikom učitavanja izvornog Excel fajla: {str(e)}")
            return None

    def load_target_excel(self):
        """
        Učitavanje ciljnog Excel fajla
        
        Returns:
            pandas.DataFrame: DataFrame sa podacima iz ciljnog Excel fajla
        """
        try:
            if not os.path.exists(self.target_excel_path):
                print(f"Upozorenje: Ciljni Excel fajl ne postoji na putanji: {self.target_excel_path}")
                return pd.DataFrame(columns=["name", "last_name"])
                
            df = pd.read_excel(self.target_excel_path)
            
            print(f"Uspešno učitan ciljni Excel fajl sa {len(df)} redova")
            return df
            
        except Exception as e:
            print(f"Greška prilikom učitavanja ciljnog Excel fajla: {str(e)}")
            return pd.DataFrame(columns=["name", "last_name"])

    def check_name_exists(self, full_name, target_df):
        """
        Provera da li ime i prezime već postoje u ciljnom Excel fajlu
        
        Args:
            full_name (str): Puno ime (ime i prezime) za proveru
            target_df (pandas.DataFrame): DataFrame sa podacima iz ciljnog Excel fajla
            
        Returns:
            bool: True ako ime i prezime već postoje, False inače
        """
        if target_df is None or target_df.empty:
            return False
            
        # Razdvajanje punog imena na ime i prezime
        name_parts = full_name.strip().split(' ', 1)
        if len(name_parts) < 2:
            print(f"Upozorenje: Nije moguće razdvojiti ime i prezime iz '{full_name}'")
            return False
            
        name = name_parts[0]
        last_name = name_parts[1]
        
        # Normalizacija imena i prezimena za proveru
        name_lower = name.lower().strip() if isinstance(name, str) else ""
        last_name_lower = last_name.lower().strip() if isinstance(last_name, str) else ""
        
        # Provera da li ime i prezime već postoje
        for _, row in target_df.iterrows():
            row_name = row.get('name', '')
            row_last_name = row.get('last_name', '')
            
            if isinstance(row_name, str) and isinstance(row_last_name, str):
                if row_name.lower().strip() == name_lower and row_last_name.lower().strip() == last_name_lower:
                    return True
                    
        return False

    def generate_statistics(self):
        """
        Generisanje statistike o imenima koja postoje u oba Excel fajla
        """
        try:
            # Učitavanje izvornog Excel fajla
            source_df = self.load_source_excel()
            if source_df is None:
                print("Prekid obrade zbog greške pri učitavanju izvornog Excel fajla")
                return
                
            # Učitavanje ciljnog Excel fajla
            target_df = self.load_target_excel()
            
            # Brojači za statistiku
            total_rows = len(source_df)
            processed_rows = 0
            existing_names = 0
            new_names = 0
            invalid_names = 0
            
            print(f"Započeta analiza {total_rows} redova iz izvornog Excel fajla")
            
            # Lista za čuvanje detalja o postojećim imenima
            existing_names_details = []
            
            # Lista za čuvanje detalja o novim imenima
            new_names_details = []
            
            # Lista za čuvanje detalja o nevalidnim imenima
            invalid_names_details = []
            
            # Obrada svakog reda
            for index, row in source_df.iterrows():
                try:
                    # Dobijanje punog imena iz reda
                    full_name = row.get('name', '')
                    
                    if not full_name:
                        invalid_names += 1
                        invalid_names_details.append(f"Red {index+1}: Prazno ime")
                        continue
                        
                    # Provera da li ime sadrži i ime i prezime
                    name_parts = full_name.strip().split(' ', 1)
                    if len(name_parts) < 2:
                        invalid_names += 1
                        invalid_names_details.append(f"Red {index+1}: '{full_name}' - nema prezime")
                        continue
                    
                    # Provera da li ime i prezime već postoje u ciljnom Excel fajlu
                    if self.check_name_exists(full_name, target_df):
                        existing_names += 1
                        existing_names_details.append(f"Red {index+1}: {full_name}")
                    else:
                        new_names += 1
                        new_names_details.append(f"Red {index+1}: {full_name}")
                        
                        # ============= OBRADA NOVOG IMENA =============
                        print(f"\n--- Otkriveno novo ime: {full_name} ---")
                        name = name_parts[0]
                        last_name = name_parts[1]
                        
                        # Ovde dodajte vaš kod za obradu novog imena
                        self.process_new_name(full_name, name, last_name, index + 1)
                        
                    processed_rows += 1
                    
                except Exception as row_error:
                    invalid_names += 1
                    invalid_names_details.append(f"Red {index+1}: Greška - {str(row_error)}")
            
            # Prikaz samo ukupne statistike
            print("\n" + "="*50)
            print("UKUPNA STATISTIKA ANALIZE IMENA")
            print("="*50)
            print(f"Ukupno redova u izvornom Excel fajlu: {total_rows}")
            print(f"Uspešno obrađeno redova: {processed_rows}")
            print(f"Imena koja već postoje u ciljnom Excel fajlu: {existing_names} ({existing_names/total_rows*100:.2f}%)")
            print(f"Nova imena koja ne postoje u ciljnom Excel fajlu: {new_names} ({new_names/total_rows*100:.2f}%)")
            print(f"Nevalidni redovi: {invalid_names} ({invalid_names/total_rows*100:.2f}%)")
            print("="*50)
            
        except Exception as e:
            print(f"Greška prilikom generisanja statistike: {str(e)}")

    def process_new_name(self, full_name, name, last_name, row_index):
        """
        Obrada novog imena koje ne postoji u ciljnom Excel fajlu
        
        Args:
            full_name (str): Puno ime (ime i prezime)
            name (str): Ime
            last_name (str): Prezime
            row_index (int): Indeks reda u izvornom Excel fajlu
        """
        try:
            print(f"Obrada novog imena: {full_name}")
            print(f"  - Ime: {name}")
            print(f"  - Prezime: {last_name}")
            print(f"  - Red u izvornom Excel fajlu: {row_index}")
            
            # Uvoz OpenAIService
            from app.services.openai_service import OpenAIService
                        
            # Inicijalizacija OpenAI servisa
            openai_service = OpenAIService()
            
            # Priprema parametara za API poziv
            schema = openai_service.get_humanity_check_schema()
            messages = [
                {
                    "role": "system", 
                    "content": """You are a precise verification assistant whose only job is to check if a given string represents a real, famous person (a person), and not a band, organization, fictional character, or anything else.

                    TASK: For each string you receive, return `true` if it is the name of a real person (notable individual), otherwise return `false`.

                    CONSTRAINTS:
                    - Return only `true` or `false`.
                    - If the string refers to a band, organization, event, fictional character, or anything other than a real person, return `false`.
                    - If it is a real person, return `true`.
                    - Your response will be passed into a structured function call for further processing.
                    """
                },
                {
                    "role": "user", 
                    "content": [
                        { "type": "text", "text": f"Check if the following string is a real person: '{full_name}'." }
                    ]
                }
            ]
            
            # Poziv OpenAI API-ja
            response = openai_service.safe_openai_request(
                model="gpt-4.1",  # Koristite model koji je dostupan
                messages=messages,
                temperature=0.3,
                max_tokens=2100,
                functions=[schema],
                function_call={"name": "get_humanity_check"}
            )
            
            # Obrada odgovora
            if response.choices and response.choices[0].message.function_call:
                function_call = response.choices[0].message.function_call
                arguments = json.loads(function_call.arguments)
                print(f"Response: {json.dumps(arguments, ensure_ascii=False, indent=4)}")
                
                # Provera da li je osoba stvarna
                is_human = arguments.get('human', False)
                if is_human:
                    print(f"✅ '{full_name}' je stvarna osoba.")
                    # Čuvanje u ciljni Excel fajl
                    self.save_to_target_excel(full_name)
                else:
                    print(f"❌ '{full_name}' nije stvarna osoba.")
            
        except Exception as e:
            print(f"Greška prilikom obrade novog imena '{full_name}': {str(e)}")

    def save_to_target_excel(self, full_name):
        """
        Čuvanje imena i prezimena u ciljni Excel fajl
        
        Args:
            full_name (str): Puno ime (ime i prezime) za čuvanje
            
        Returns:
            bool: True ako je uspešno sačuvano, False inače
        """
        try:
            # Razdvajanje punog imena na ime i prezime
            name_parts = full_name.strip().split(' ', 1)
            if len(name_parts) < 2:
                print(f"Upozorenje: Nije moguće razdvojiti ime i prezime iz '{full_name}'")
                return False
            
            name = name_parts[0]
            last_name = name_parts[1]
            
            # Učitavanje postojećeg Excel fajla ili kreiranje novog
            if os.path.exists(self.target_excel_path):
                try:
                    df = pd.read_excel(self.target_excel_path)
                except Exception as e:
                    print(f"Greška prilikom učitavanja ciljnog Excel fajla: {str(e)}")
                    # Kreiranje novog DataFrame-a ako ne možemo da učitamo postojeći
                    df = pd.DataFrame(columns=["name", "last_name"])
            else:
                # Kreiranje novog DataFrame-a ako fajl ne postoji
                df = pd.DataFrame(columns=["name", "last_name"])
            
            # Dodavanje novog reda
            new_row = pd.DataFrame({"name": [name], "last_name": [last_name]})
            df = pd.concat([df, new_row], ignore_index=True)
            
            # Kreiranje direktorijuma ako ne postoji
            os.makedirs(os.path.dirname(self.target_excel_path), exist_ok=True)
            
            # Čuvanje DataFrame-a u Excel fajl
            df.to_excel(self.target_excel_path, index=False)
            
            print(f"✅ Uspešno sačuvano ime '{name}' i prezime '{last_name}' u ciljni Excel fajl")
            return True
            
        except Exception as e:
            print(f"❌ Greška prilikom čuvanja imena i prezimena u ciljni Excel fajl: {str(e)}")
            return False

    def save_summary_to_file(self, **stats):
        """
        Čuvanje samo ukupne statistike u tekstualni fajl
        
        Args:
            **stats: Statistički podaci za čuvanje
        """
        try:
            # Kreiranje putanje za fajl sa statistikom
            stats_dir = 'storage/statistics'
            os.makedirs(stats_dir, exist_ok=True)
            
            # Kreiranje imena fajla sa trenutnim datumom i vremenom
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            stats_file = os.path.join(stats_dir, f"excel_summary_{timestamp}.txt")
            
            # Pisanje statistike u fajl
            with open(stats_file, 'w', encoding='utf-8') as f:
                f.write("="*50 + "\n")
                f.write("UKUPNA STATISTIKA ANALIZE IMENA\n")
                f.write("="*50 + "\n")
                f.write(f"Datum i vreme analize: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Izvorni Excel fajl: {self.source_excel_path}\n")
                f.write(f"Ciljni Excel fajl: {self.target_excel_path}\n\n")
                
                f.write(f"Ukupno redova u izvornom Excel fajlu: {stats['total_rows']}\n")
                f.write(f"Uspešno obrađeno redova: {stats['processed_rows']}\n")
                f.write(f"Imena koja već postoje u ciljnom Excel fajlu: {stats['existing_names']} ({stats['existing_names']/stats['total_rows']*100:.2f}%)\n")
                f.write(f"Nova imena koja ne postoje u ciljnom Excel fajlu: {stats['new_names']} ({stats['new_names']/stats['total_rows']*100:.2f}%)\n")
                f.write(f"Nevalidni redovi: {stats['invalid_names']} ({stats['invalid_names']/stats['total_rows']*100:.2f}%)\n")
            
            print(f"\nUkupna statistika je sačuvana u fajl: {stats_file}")
            
        except Exception as e:
            print(f"Greška prilikom čuvanja statistike u fajl: {str(e)}")

def main():
    """
    Glavna funkcija za pokretanje skripte
    """
    try:
        # Parsiranje argumenata komandne linije
        source_excel_path = sys.argv[1] if len(sys.argv) > 1 else None
        target_excel_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Inicijalizacija i pokretanje analize
        checker = ExcelChecker(source_excel_path, target_excel_path)
        checker.generate_statistics()
        
    except Exception as e:
        print(f"Greška prilikom izvršavanja skripte: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 