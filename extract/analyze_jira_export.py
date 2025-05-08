import json
import os
from openai import OpenAI
import ijson  # Pour parser des JSON volumineux par morceaux

# Initialisation du client OpenAI
client = OpenAI(api_key='ta-clé-api')  # Remplace par ta clé API

def extract_structure_from_large_json(json_file_path, sample_size=10):
    """
    Extraire un échantillon et la structure d'un fichier JSON volumineux
    en le traitant par morceaux
    """
    sample = []
    count = 0
    
    # Utiliser ijson pour traiter le fichier par morceaux
    with open(json_file_path, 'r') as file:
        # Parser le JSON par morceaux (tickets)
        parser = ijson.items(file, 'item')
        
        for i, item in enumerate(parser):
            if i < sample_size:
                sample.append(item)
            count += 1
            if i % 1000 == 0:
                print(f"Traitement de {json_file_path}: {i} tickets analysés...")
    
    # Extraire les clés et la structure
    if sample:
        structure = {
            "filename": os.path.basename(json_file_path),
            "estimated_total_items": count,
            "sample_size": len(sample),
            "keys": list(sample[0].keys()) if sample else [],
            "example": sample[0] if sample else None
        }
    else:
        structure = {
            "filename": os.path.basename(json_file_path),
            "error": "Format non reconnu ou fichier vide"
        }
    
    return structure

def fallback_extract_structure(json_file_path, sample_size=10):
    """
    Extraction de structure utilisant un parsing manuel pour gérer des fichiers extrêmement volumineux
    """
    sample = []
    count = 0
    
    with open(json_file_path, 'r') as file:
        # Lire le début du fichier pour déterminer s'il s'agit d'un tableau JSON
        beginning = file.read(1000)
        if not beginning.strip().startswith('['):
            return {"filename": os.path.basename(json_file_path), "error": "Format JSON non reconnu (doit commencer par '[')"}
        
        file.seek(0)  # Remettre le curseur au début
        
        # Lire les premiers objets JSON
        depth = 0
        buffer = ""
        in_string = False
        escape = False
        item_started = False
        
        for chunk in iter(lambda: file.read(8192), ''):
            for char in chunk:
                if escape:
                    escape = False
                    buffer += char
                    continue
                
                if char == '\\':
                    escape = True
                    buffer += char
                    continue
                    
                if char == '"' and not escape:
                    in_string = not in_string
                    buffer += char
                    continue
                
                if not in_string:
                    if char == '{':
                        depth += 1
                        if depth == 1:
                            item_started = True
                            buffer = char
                        else:
                            buffer += char
                    elif char == '}':
                        depth -= 1
                        buffer += char
                        if depth == 0 and item_started:
                            try:
                                obj = json.loads(buffer)
                                count += 1
                                if len(sample) < sample_size:
                                    sample.append(obj)
                                if count % 100 == 0:
                                    print(f"Traitement manuel de {json_file_path}: {count} tickets analysés...")
                            except json.JSONDecodeError:
                                print(f"Erreur de décodage JSON: {buffer[:100]}...")
                            buffer = ""
                            item_started = False
                            
                            if count >= 1000:  # Limiter le nombre d'éléments traités
                                break
                    elif not item_started:
                        # Ignorer les caractères entre les objets (virgules, espaces, etc.)
                        continue
                    else:
                        buffer += char
                else:
                    buffer += char
            
            if count >= 1000:
                break
    
    # Extraire les clés et la structure
    if sample:
        structure = {
            "filename": os.path.basename(json_file_path),
            "estimated_total_items": "plus de 1000" if count >= 1000 else count,
            "sample_size": len(sample),
            "keys": list(sample[0].keys()) if sample else [],
            "example": sample[0] if sample else None
        }
    else:
        structure = {
            "filename": os.path.basename(json_file_path),
            "error": "Format non reconnu ou fichier vide"
        }
    
    return structure

def extract_structure(json_file_path, sample_size=10):
    """
    Essayer différentes méthodes pour extraire la structure des fichiers JSON volumineux
    """
    try:
        print(f"Tentative d'analyse par morceaux de {json_file_path}...")
        return extract_structure_from_large_json(json_file_path, sample_size)
    except Exception as e:
        print(f"Erreur avec ijson: {e}")
        try:
            print(f"Tentative d'analyse manuelle de {json_file_path}...")
            return fallback_extract_structure(json_file_path, sample_size)
        except Exception as e:
            print(f"Toutes les méthodes ont échoué: {e}")
            
            # Dernière tentative: lire seulement les premiers tickets avec un parsing simple
            with open(json_file_path, 'r') as f:
                first_lines = ''.join([f.readline() for _ in range(1000)])
                try:
                    # Essayer de détecter la fin du premier objet JSON
                    first_lines = first_lines + "]"  # Fermer le tableau
                    first_object = json.loads(first_lines)[0]
                    return {
                        "filename": os.path.basename(json_file_path),
                        "note": "Analyse partielle seulement",
                        "keys": list(first_object.keys()),
                        "example": first_object
                    }
                except:
                    return {
                        "filename": os.path.basename(json_file_path),
                        "error": "Impossible d'analyser ce fichier"
                    }

def analyze_with_llm(structures):
    """
    Analyser les structures extraites avec GPT-4
    """
    prompt = f"""
    Analyse les structures suivantes de fichiers JSON d'export JIRA. 
    Détermine les similitudes, les différences et comment structurer ces données pour:
    1. Faciliter le matching avec des documents Confluence
    2. Permettre à un LLM de comprendre les relations entre tickets et documentation
    3. Proposer une architecture de données normalisée pour l'intégration
    
    Structures des fichiers:
    {json.dumps(structures, indent=2, ensure_ascii=False)}
    """

    response = client.chat.completions.create(
        model="gpt-4-turbo",  # ou gpt-3.5-turbo si GPT-4 n'est pas disponible
        messages=[
            {"role": "system", "content": "Tu es un expert en analyse de données et intégration de systèmes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def main():
    # Installer ijson si nécessaire
    try:
        import ijson
    except ImportError:
        print("Installation du module ijson pour le traitement de gros fichiers JSON...")
        import subprocess
        subprocess.check_call(["pip", "install", "ijson"])
        import ijson
    
    # Analyse des fichiers
    files_to_analyze = ['CARTAN (1).json', 'CASM.json']
    print(f"Analyse de {len(files_to_analyze)} fichiers JIRA...")
    
    structures = []
    for file in files_to_analyze:
        try:
            structure = extract_structure(file)
            structures.append(structure)
            print(f"Structure extraite pour {file}")
        except Exception as e:
            print(f"Erreur lors de l'analyse de {file}: {e}")
            structures.append({"filename": file, "error": str(e)})
    
    # Obtenir l'analyse du LLM
    print("Envoi des structures au LLM pour analyse...")
    llm_analysis = analyze_with_llm(structures)
    print("\nRÉSULTATS DE L'ANALYSE:")
    print("------------------------")
    print(llm_analysis)
    
    # Sauvegarder l'analyse
    with open('jira_structure_analysis.txt', 'w') as f:
        f.write(llm_analysis)
    
    print("\nL'analyse a été sauvegardée dans 'jira_structure_analysis.txt'")

if __name__ == "__main__":
    main() 