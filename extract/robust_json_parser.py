import json
import re
import os
import logging
import ijson
from typing import Dict, Any, Optional, Tuple, List
import traceback
from dotenv import load_dotenv
import openai
from pathlib import Path

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1")

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("robust_json_parser")

class JsonParsingException(Exception):
    """Exception personnalisée pour les erreurs de parsing JSON."""
    pass


def escape_special_chars_in_strings(content: str) -> str:
    """
    Échappe les caractères spéciaux dans les chaînes JSON.
    
    Args:
        content: Contenu JSON à traiter
        
    Returns:
        Contenu JSON avec caractères spéciaux échappés dans les chaînes
    """
    # Regex pour trouver les chaînes entre guillemets doubles
    # et échapper les caractères spéciaux à l'intérieur
    in_string = False
    escaped = False
    result = []
    
    for char in content:
        if escaped:
            result.append(char)
            escaped = False
        elif char == '\\':
            result.append(char)
            escaped = True
        elif char == '"' and not escaped:
            in_string = not in_string
            result.append(char)
        elif in_string:
            # Si on est dans une chaîne, échapper les caractères spéciaux
            if char in ['\n', '\r', '\t', '\b', '\f']:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif char == '\b':
                    result.append('\\b')
                elif char == '\f':
                    result.append('\\f')
            else:
                result.append(char)
        else:
            result.append(char)
            
    return ''.join(result)


def fix_common_json_errors(content: str) -> str:
    """
    Corrige les erreurs JSON courantes.
    
    Args:
        content: Contenu JSON à corriger
        
    Returns:
        Contenu JSON corrigé
    """
    # Correction 1: Remplacer les single quotes par des double quotes pour les clés et valeurs
    # Attention à ne pas remplacer les apostrophes dans les textes
    content = re.sub(r"(?<![a-zA-Z0-9])'([^']*?)'(?![a-zA-Z0-9])", r'"\1"', content)
    
    # Correction 2: Ajouter des virgules manquantes entre objets
    content = re.sub(r"}\s*{", "},{", content)
    
    # Correction 3: Ajouter des virgules manquantes entre tableaux
    content = re.sub(r"]\s*\[", "],[", content)
    
    # Correction 4: Ajouter des guillemets autour des noms de propriétés non quotés
    content = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', content)
    
    # Correction 5: Réparer les guillemets non fermés (cas simple)
    content = fix_unclosed_quotes(content)
    
    # Correction 6: Échapper les caractères spéciaux
    content = escape_special_chars_in_strings(content)
    
    # Correction 7: Supprimer les virgules en trop à la fin des objets/tableaux
    content = re.sub(r',\s*}', '}', content)
    content = re.sub(r',\s*]', ']', content)
    
    # Correction 8: Convertir "True", "False", "None" en "true", "false", "null"
    content = re.sub(r':\s*True\b', ': true', content)
    content = re.sub(r':\s*False\b', ': false', content)
    content = re.sub(r':\s*None\b', ': null', content)
    
    return content


def fix_unclosed_quotes(content: str) -> str:
    """
    Tente de réparer les guillemets non fermés dans le contenu JSON.
    
    Args:
        content: Contenu JSON à réparer
        
    Returns:
        Contenu JSON avec guillemets réparés
    """
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Compte les guillemets non échappés
        quote_count = 0
        j = 0
        while j < len(line):
            if line[j] == '\\' and j + 1 < len(line) and line[j + 1] == '"':
                j += 2  # Saute le guillemet échappé
                continue
            if line[j] == '"':
                quote_count += 1
            j += 1
        
        # Si nombre impair de guillemets, ajouter un guillemet à la fin
        if quote_count % 2 == 1:
            lines[i] = line + '"'
    
    return '\n'.join(lines)


def fix_property_name_quotes(line: str, col: int) -> str:
    """
    Ajoute des guillemets autour d'un nom de propriété à la position spécifiée.
    
    Args:
        line: Ligne contenant l'erreur
        col: Position de l'erreur dans la ligne
        
    Returns:
        Ligne corrigée
    """
    # Identifier le début du nom de propriété
    start = col
    while start > 0 and line[start-1].isalnum() or line[start-1] in "_-":
        start -= 1
        
    # Identifier la fin du nom de propriété
    end = col
    while end < len(line) and (line[end].isalnum() or line[end] in "_-"):
        end += 1
    
    # Extraire le nom de propriété
    prop_name = line[start:end]
    
    # Remplacer par le nom avec guillemets
    return line[:start] + f'"{prop_name}"' + line[end:]


def targeted_json_fix(content: str, error_message: str) -> str:
    """
    Applique une correction ciblée basée sur le message d'erreur.
    
    Args:
        content: Contenu JSON à corriger
        error_message: Message d'erreur du parser JSON
        
    Returns:
        Contenu JSON corrigé si possible
    """
    lines = content.split('\n')
    
    # Cas 1: Propriété sans guillemets
    if "Expecting property name enclosed in double quotes" in error_message:
        match = re.search(r"line (\d+) column (\d+)", error_message)
        if match:
            line_idx, col = int(match.group(1)) - 1, int(match.group(2)) - 1
            if 0 <= line_idx < len(lines):
                lines[line_idx] = fix_property_name_quotes(lines[line_idx], col)
    
    # Cas 2: Virgule manquante
    elif "Expecting ',' delimiter" in error_message:
        match = re.search(r"line (\d+) column (\d+)", error_message)
        if match:
            line_idx, col = int(match.group(1)) - 1, int(match.group(2)) - 1
            if 0 <= line_idx < len(lines):
                # Insérer une virgule à la position indiquée
                line = lines[line_idx]
                lines[line_idx] = line[:col] + "," + line[col:]
    
    # Cas 3: Guillemet fermant manquant
    elif "Unterminated string" in error_message or "Invalid control character" in error_message:
        match = re.search(r"line (\d+) column (\d+)", error_message)
        if match:
            line_idx = int(match.group(1)) - 1
            if 0 <= line_idx < len(lines):
                lines[line_idx] = fix_unclosed_quotes(lines[line_idx])
    
    return '\n'.join(lines)


def parse_with_ijson(file_path: str) -> Dict:
    """
    Tente de parser le fichier JSON avec ijson (plus tolérant).
    
    Args:
        file_path: Chemin du fichier à parser
        
    Returns:
        Dictionnaire contenant les données JSON parsées ou None si échec
    """
    try:
        result = {}
        with open(file_path, 'rb') as f:
            # Essayer de parser tout le fichier comme un objet
            for prefix, event, value in ijson.parse(f):
                if prefix == '' and event == 'map_key':
                    result[value] = {}
                    current_key = value
                elif prefix and prefix.count('.') == 0 and event == 'map_key':
                    result[current_key][value] = {}
                # Construction simplifiée - pour des structures plus complexes
                # un traitement plus sophistiqué serait nécessaire
        
        if result:
            return result
        
        # Si la première approche échoue, essayer de parser comme un tableau d'objets
        with open(file_path, 'rb') as f:
            items = list(ijson.items(f, 'item'))
            if items:
                return {"items": items}
        
        return None
    except Exception as e:
        logger.warning(f"Échec du parsing avec ijson: {str(e)}")
        return None


def extract_json_from_llm_response(response: str) -> str:
    """
    Extrait le JSON de la réponse du LLM.
    
    Args:
        response: Réponse textuelle du LLM
        
    Returns:
        Contenu JSON extrait
    """
    # Chercher le contenu entre des délimiteurs de code
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        return json_match.group(1).strip()
    
    # Si pas de délimiteurs, essayer de trouver un objet JSON
    json_match = re.search(r'({[\s\S]*}|\[[\s\S]*\])', response)
    if json_match:
        return json_match.group(1).strip()
    
    # Sinon, retourner toute la réponse
    return response.strip()


def save_repaired_json(file_path: str, repaired_content: str) -> str:
    """
    Sauvegarde le JSON réparé dans un nouveau fichier.
    
    Args:
        file_path: Chemin du fichier original
        repaired_content: Contenu JSON réparé
        
    Returns:
        Chemin du fichier réparé
    """
    base_path = os.path.splitext(file_path)[0]
    repaired_path = f"{base_path}_repaired.json"
    
    with open(repaired_path, 'w', encoding='utf-8') as f:
        f.write(repaired_content)
    
    logger.info(f"JSON réparé sauvegardé dans {repaired_path}")
    return repaired_path


def repair_json_chunk_with_llm(chunk: str, model: str = DEFAULT_LLM_MODEL) -> str:
    """
    Utilise le LLM pour réparer un fragment de JSON.
    
    Args:
        chunk: Fragment de JSON à réparer
        model: Modèle LLM à utiliser
        
    Returns:
        Fragment JSON réparé
    """
    prompt = f"""
    Ce fragment JSON contient des erreurs de syntaxe. Corrigez-les pour produire un JSON valide.
    Ne modifiez que ce qui est nécessaire pour la validité syntaxique.
    Renvoyez uniquement le JSON corrigé, sans commentaires ni explications.
    
    Fragment JSON à réparer:
    {chunk}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "Vous êtes un expert en réparation de JSON. Votre tâche est de corriger les erreurs de syntaxe JSON tout en préservant au maximum le contenu original."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # Réduire la température pour des réponses plus déterministes
        )
        
        repaired_json = extract_json_from_llm_response(response.choices[0].message.content)
        return repaired_json
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au LLM: {str(e)}")
        raise


def repair_large_json_with_llm(content: str, chunk_size: int = 5000, model: str = DEFAULT_LLM_MODEL) -> Dict:
    """
    Répare un grand fichier JSON en le divisant en morceaux traités par LLM.
    
    Args:
        content: Contenu JSON complet
        chunk_size: Taille des morceaux à envoyer au LLM
        model: Modèle LLM à utiliser
        
    Returns:
        Dictionnaire contenant les données JSON réparées
    """
    # Découper en morceaux en respectant la structure des objets/tableaux
    chunks = split_json_into_chunks(content, chunk_size)
    
    # Réparer chaque morceau
    repaired_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Réparation du morceau {i+1}/{len(chunks)} avec LLM")
        try:
            repaired_chunk = repair_json_chunk_with_llm(chunk, model)
            repaired_chunks.append(repaired_chunk)
        except Exception as e:
            logger.error(f"Échec de la réparation du morceau {i+1}: {str(e)}")
            repaired_chunks.append(chunk)  # Utiliser le morceau original en cas d'échec
    
    # Recombiner les morceaux
    combined_json = combine_json_chunks(repaired_chunks)
    
    try:
        # Valider que le résultat est un JSON valide
        return json.loads(combined_json)
    except json.JSONDecodeError as e:
        logger.error(f"Le JSON recombinée n'est toujours pas valide: {str(e)}")
        # Tentative finale avec le LLM sur une version simplifiée
        simplified = simplify_json_structure(combined_json)
        return json.loads(repair_json_chunk_with_llm(simplified, model))


def split_json_into_chunks(content: str, chunk_size: int) -> List[str]:
    """
    Découpe le contenu JSON en morceaux tout en respectant la structure.
    
    Args:
        content: Contenu JSON à découper
        chunk_size: Taille maximale des morceaux
        
    Returns:
        Liste de morceaux JSON
    """
    chunks = []
    current_chunk = ""
    bracket_count = 0
    in_string = False
    escaped = False
    
    for char in content:
        current_chunk += char
        
        if escaped:
            escaped = False
            continue
            
        if char == '\\':
            escaped = True
        elif char == '"' and not escaped:
            in_string = not in_string
        elif not in_string:
            if char in '{[':
                bracket_count += 1
            elif char in ']}':
                bracket_count -= 1
                
                # Si on est revenu à l'équilibre et que le morceau est assez grand
                if bracket_count == 0 and len(current_chunk) >= chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = ""
        
        # Si le morceau devient trop grand et qu'on n'est pas dans une chaîne
        if len(current_chunk) >= chunk_size * 1.5 and not in_string and bracket_count == 0:
            chunks.append(current_chunk)
            current_chunk = ""
    
    # Ajouter le dernier morceau s'il reste du contenu
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def combine_json_chunks(chunks: List[str]) -> str:
    """
    Recombine les morceaux JSON en un seul document.
    
    Args:
        chunks: Liste de morceaux JSON
        
    Returns:
        Contenu JSON recombinée
    """
    # Déterminer si les morceaux sont des objets ou des tableaux
    first_chunk = chunks[0].strip()
    is_array = first_chunk.startswith('[')
    
    if is_array:
        # Extraire les items des tableaux et les combiner
        result = "["
        items = []
        
        for chunk in chunks:
            # Extraire le contenu entre crochets
            content = chunk.strip()
            if content.startswith('[') and content.endswith(']'):
                content = content[1:-1].strip()
                if content:  # S'il y a du contenu après avoir enlevé les crochets
                    items.append(content)
        
        result += ",".join(items)
        result += "]"
        return result
    else:
        # Extraire les paires clé-valeur des objets et les combiner
        result = "{"
        properties = []
        
        for chunk in chunks:
            # Extraire le contenu entre accolades
            content = chunk.strip()
            if content.startswith('{') and content.endswith('}'):
                content = content[1:-1].strip()
                if content:  # S'il y a du contenu après avoir enlevé les accolades
                    properties.append(content)
        
        result += ",".join(properties)
        result += "}"
        return result


def simplify_json_structure(content: str) -> str:
    """
    Simplifie la structure JSON pour faciliter la réparation par LLM.
    
    Args:
        content: Contenu JSON complexe
        
    Returns:
        Version simplifiée du JSON
    """
    try:
        # Tenter de charger comme JSON
        data = json.loads(content)
        
        # Si c'est un tableau, prendre les premiers éléments
        if isinstance(data, list):
            if len(data) > 3:
                return json.dumps(data[:3]) + "..."
            return content
        
        # Si c'est un objet, garder les clés principales
        if isinstance(data, dict):
            simplified = {}
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    if isinstance(value, list) and len(value) > 0:
                        simplified[key] = [value[0]]  # Garder uniquement le premier élément
                    elif isinstance(value, dict):
                        simplified[key] = {k: "..." for k in list(value.keys())[:5]}  # Garder uniquement les clés
                else:
                    simplified[key] = value
            return json.dumps(simplified)
        
    except:
        # En cas d'échec, tenter une simplification basée sur le texte
        # Garder uniquement les 500 premiers caractères et les 500 derniers
        if len(content) > 1000:
            return content[:500] + "\n...\n" + content[-500:]
        return content


def repair_json_with_llm(file_path: str, model: str = DEFAULT_LLM_MODEL) -> Dict:
    """
    Utilise LLM pour réparer un fichier JSON entier.
    
    Args:
        file_path: Chemin du fichier JSON à réparer
        model: Modèle LLM à utiliser
        
    Returns:
        Dictionnaire contenant les données JSON réparées
    """
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier la taille du fichier
    if len(content) > 100000:
        logger.info(f"Fichier volumineux ({len(content)} caractères), traitement par morceaux")
        return repair_large_json_with_llm(content, model=model)
    
    # Pour les fichiers plus petits, traiter en une seule fois
    logger.info("Réparation du fichier JSON avec LLM")
    repaired_json = repair_json_chunk_with_llm(content, model)
    
    # Valider et sauvegarder le JSON réparé
    try:
        result = json.loads(repaired_json)
        save_repaired_json(file_path, repaired_json)
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Le JSON réparé par LLM n'est toujours pas valide: {str(e)}")
        raise JsonParsingException(f"Échec de la réparation par LLM: {str(e)}")


def robust_json_parser(file_path: str, llm_fallback: bool = False, model: str = DEFAULT_LLM_MODEL) -> Dict:
    """
    Parser JSON robuste avec fallback LLM.
    
    Args:
        file_path: Chemin du fichier JSON à parser
        llm_fallback: Activer le fallback LLM en cas d'échec
        model: Modèle LLM à utiliser si fallback activé
        
    Returns:
        Dictionnaire contenant les données JSON parsées
    """
    error_details = {}
    
    # 1. Tentative avec json standard
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        error_details["standard"] = str(e)
        logger.warning(f"Erreur standard JSON: {str(e)}")
    
    # 2. Tentative avec corrections automatiques
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Appliquer des corrections courantes
            content = fix_common_json_errors(content)
            return json.loads(content)
    except json.JSONDecodeError as e:
        error_details["auto_fix"] = str(e)
        logger.warning(f"Échec après corrections automatiques: {str(e)}")
        
        # 2.1 Tentative avec correction ciblée
        try:
            fixed_content = targeted_json_fix(content, str(e))
            return json.loads(fixed_content)
        except json.JSONDecodeError as e2:
            error_details["targeted_fix"] = str(e2)
            logger.warning(f"Échec après correction ciblée: {str(e2)}")
    
    # 3. Tentative avec ijson (parsing itératif)
    try:
        result = parse_with_ijson(file_path)
        if result:
            logger.info("Parsing réussi avec ijson")
            return result
    except Exception as e:
        error_details["ijson"] = str(e)
        logger.warning(f"Échec avec ijson: {str(e)}")
    
    # 4. Fallback LLM si activé
    if llm_fallback:
        try:
            logger.info("Tentative de réparation avec LLM")
            return repair_json_with_llm(file_path, model)
        except Exception as e:
            error_details["llm"] = str(e)
            logger.error(f"Échec de la réparation LLM: {str(e)}")
    
    # 5. Si tout échoue, lever une exception détaillée
    error_msg = "\n".join([f"{method}: {error}" for method, error in error_details.items()])
    raise JsonParsingException(f"Impossible de parser {file_path} malgré plusieurs tentatives:\n{error_msg}")


if __name__ == "__main__":
    # Test du parser avec un fichier spécifié en argument
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        use_llm = "--llm" in sys.argv
        
        try:
            result = robust_json_parser(input_file, llm_fallback=use_llm)
            print(f"Parsing réussi! Structure racine: {type(result)}")
            if isinstance(result, dict):
                print(f"Clés: {list(result.keys())}")
            elif isinstance(result, list):
                print(f"Nombre d'éléments: {len(result)}")
        except JsonParsingException as e:
            print(f"Échec final: {e}")
    else:
        print("Usage: python robust_json_parser.py <fichier_json> [--llm]") 