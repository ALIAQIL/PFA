import json
import pandas as pd

def json_to_csv_pandas(json_file_path, csv_file_path):
    # Spécifier l'encodage UTF-8 lors de l'ouverture du fichier
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Convert to DataFrame
    df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)
    
    # Write to CSV
    df.to_csv(csv_file_path, index=False, encoding='utf-8')
    print(f"CSV file created at: {csv_file_path}")

# Si vous avez un fichier très volumineux, cette méthode peut être plus robuste
def json_to_csv_pandas_safe(json_file_path, csv_file_path):
    try:
        # Essayer avec différents encodages
        encodings = ['utf-8', 'utf-16', 'latin-1', 'ISO-8859-1']
        
        for encoding in encodings:
            try:
                with open(json_file_path, 'r', encoding=encoding) as file:
                    data = json.load(file)
                    
                # Convert to DataFrame
                df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)
                
                # Write to CSV
                df.to_csv(csv_file_path, index=False, encoding='utf-8')
                print(f"CSV file created with encoding {encoding} at: {csv_file_path}")
                return
            except UnicodeDecodeError:
                continue
            
        print("Impossible de décoder le fichier avec les encodages essayés.")
    except Exception as e:
        print(f"Erreur: {e}")

# Exemple d'utilisation
json_file = "amazon_data.json"
csv_file = "amazon_raw_data.csv"

# Utilisez cette version améliorée
json_to_csv_pandas_safe(json_file, csv_file)
