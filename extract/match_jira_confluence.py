import json
import os
import re
import argparse
from datetime import datetime
import math
from collections import defaultdict
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import safe_json_load, write_tree

def load_json_file(file_path, llm_fallback=False, model=None):
    """
    Charger un fichier JSON avec gestion robuste des erreurs
    
    Args:
        file_path: Chemin du fichier à charger
        llm_fallback: Si True, utilise LLM en cas d'échec
        model: Modèle LLM à utiliser
        
    Returns:
        Contenu JSON ou None en cas d'erreur
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return safe_json_load(f, log_prefix=file_path, llm_fallback=llm_fallback, model=model)
    except Exception as e:
        print(f"Erreur lors du chargement de {file_path}: {e}")
        return None

def save_json_file(data, file_path):
    """Sauvegarder des données dans un fichier JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Données sauvegardées dans {file_path}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde dans {file_path}: {e}")
        return False

def text_to_words(text):
    """Convertir un texte en une liste de mots normalisés"""
    if not text:
        return []
    # Nettoyer et normaliser le texte
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    # Diviser en mots et filtrer les mots courts
    return [word for word in text.split() if len(word) > 2]

def calculate_tfidf(document_words, all_documents_words):
    """Calculer les scores TF-IDF pour les mots d'un document"""
    # Nombre total de documents
    num_docs = len(all_documents_words)
    
    # Fréquence des mots dans le document (TF)
    word_freq = {}
    for word in document_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Nombre de documents contenant chaque mot (pour IDF)
    word_doc_count = defaultdict(int)
    for doc_words in all_documents_words:
        unique_words = set(doc_words)
        for word in unique_words:
            word_doc_count[word] += 1
    
    # Calculer TF-IDF
    tfidf = {}
    for word, tf in word_freq.items():
        idf = math.log(num_docs / (1 + word_doc_count.get(word, 0)))
        tfidf[word] = tf * idf
    
    return tfidf

def calculate_similarity(words1, words2):
    """Calculer la similarité de Jaccard entre deux ensembles de mots"""
    set1 = set(words1)
    set2 = set(words2)
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def extract_jira_ids_from_text(text):
    """Extraire les IDs de tickets JIRA mentionnés dans un texte (format PROJECT-123)"""
    if not text:
        return []
    
    # Chercher les motifs PROJECT-NUMBER
    jira_patterns = re.findall(r'([A-Z]+-\d+)', text)
    return list(set(jira_patterns))  # Enlever les doublons

def find_mentions(jira_tickets, confluence_pages):
    """Trouver les mentions explicites de tickets JIRA dans les pages Confluence"""
    matches = []
    
    # Créer un dictionnaire pour rechercher les tickets JIRA par ID
    jira_dict = {ticket["id"]: ticket for ticket in jira_tickets}
    
    # Pour chaque page Confluence
    for page in confluence_pages:
        # Chercher des mentions de tickets JIRA dans le titre et le contenu
        # Gérer les différentes structures possibles de données Confluence
        title = page.get("title", "")
        if not title and "content" in page:
            title = page["content"].get("title", "")
        
        content_text = ""
        if isinstance(page.get("content"), dict):
            # Nouvelle structure (content est un dict avec markdown)
            content_text = page["content"].get("markdown", "")
            if not content_text and "description" in page["content"]:
                content_text = page["content"].get("description", "")
        elif isinstance(page.get("content"), str):
            # Ancienne structure (content est directement une chaîne)
            content_text = page.get("content", "")
        
        # Combiner titre et contenu pour la recherche
        page_text = f"{title} {content_text}"
        
        jira_ids = extract_jira_ids_from_text(page_text)
        
        # Pour chaque ID de ticket trouvé
        for jira_id in jira_ids:
            if jira_id in jira_dict:
                matches.append({
                    "jira_id": jira_id,
                    "confluence_id": page["id"],
                    "match_type": "explicit_mention",
                    "match_score": 1.0,  # Score maximum pour une mention explicite
                    "match_location": "title_or_content"
                })
    
    return matches

def find_keyword_matches(jira_tickets, confluence_pages, min_similarity=0.2):
    """Trouver les correspondances basées sur les mots-clés"""
    matches = []
    
    # Préparer les mots-clés des tickets JIRA
    jira_keywords = {}
    for ticket in jira_tickets:
        # Gérer les différentes structures possibles
        title = ""
        description = ""
        
        if "content" in ticket:
            if isinstance(ticket["content"], dict):
                title = ticket["content"].get("title", "")
                description = ticket["content"].get("description", "")
            elif isinstance(ticket["content"], str):
                description = ticket["content"]
        
        # Combiner le titre et la description pour obtenir plus de mots-clés
        text = f"{title} {description}"
        jira_keywords[ticket["id"]] = text_to_words(text)
    
    # Préparer les mots-clés des pages Confluence
    confluence_keywords = {}
    for page in confluence_pages:
        # Gérer les différentes structures possibles
        title = page.get("title", "")
        if not title and "content" in page:
            title = page["content"].get("title", "")
        
        content_text = ""
        if "content" in page:
            if isinstance(page["content"], dict):
                content_text = page["content"].get("markdown", "")
                if not content_text and "description" in page["content"]:
                    content_text = page["content"].get("description", "")
            elif isinstance(page["content"], str):
                content_text = page["content"]
        
        # Combiner le titre et le contenu
        text = f"{title} {content_text}"
        confluence_keywords[page["id"]] = text_to_words(text)
    
    # Calculer la similarité entre chaque paire de tickets JIRA et pages Confluence
    for jira_id, jira_words in jira_keywords.items():
        for conf_id, conf_words in confluence_keywords.items():
            similarity = calculate_similarity(jira_words, conf_words)
            
            # Ajouter un match si la similarité est suffisante
            if similarity >= min_similarity:
                matches.append({
                    "jira_id": jira_id,
                    "confluence_id": conf_id,
                    "match_type": "keyword_similarity",
                    "match_score": similarity,
                    "jira_keywords": jira_words[:10],  # Limiter à 10 mots-clés par souci de taille
                    "confluence_keywords": conf_words[:10]
                })
    
    # Trier les matches par score (du plus élevé au plus bas)
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return matches

def find_date_proximity_matches(jira_tickets, confluence_pages, date_threshold_days=7):
    """Trouver les correspondances basées sur la proximité des dates"""
    matches = []
    
    # Convertir le seuil en secondes
    date_threshold_seconds = date_threshold_days * 24 * 60 * 60
    
    # Fonction pour extraire un timestamp d'une date ISO
    def extract_timestamp(date_string):
        if not date_string:
            return None
        try:
            # Supprimer la partie milliseconde et timezone pour simplifier
            date_string = re.sub(r'\.\d+', '', date_string)
            date_string = re.sub(r'[+-]\d{2}:\d{2}$', '', date_string)
            
            # Convertir en timestamp
            dt = datetime.fromisoformat(date_string)
            return dt.timestamp()
        except:
            return None
    
    # Préparer les dates des tickets JIRA
    jira_dates = {}
    for ticket in jira_tickets:
        created_timestamp = extract_timestamp(ticket["metadata"].get("created_at"))
        if created_timestamp:
            jira_dates[ticket["id"]] = created_timestamp
    
    # Préparer les dates des pages Confluence
    confluence_dates = {}
    for page in confluence_pages:
        created_timestamp = extract_timestamp(page["metadata"].get("created_at"))
        if created_timestamp:
            confluence_dates[page["id"]] = created_timestamp
    
    # Calculer la proximité temporelle entre chaque paire
    for jira_id, jira_timestamp in jira_dates.items():
        for conf_id, conf_timestamp in confluence_dates.items():
            # Calculer la différence absolue en secondes
            time_diff = abs(jira_timestamp - conf_timestamp)
            
            # Ajouter un match si la différence est inférieure au seuil
            if time_diff <= date_threshold_seconds:
                # Normaliser le score entre 0 et 1 (plus proche = plus élevé)
                score = 1.0 - (time_diff / date_threshold_seconds)
                
                matches.append({
                    "jira_id": jira_id,
                    "confluence_id": conf_id,
                    "match_type": "date_proximity",
                    "match_score": score,
                    "time_difference_days": time_diff / (24 * 60 * 60)
                })
    
    # Trier les matches par score (du plus élevé au plus bas)
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return matches

def combine_matches(all_matches, min_score=0.2):
    """
    Combiner et filtrer tous les matches pour obtenir les meilleurs
    
    Args:
        all_matches: Liste de toutes les correspondances trouvées
        min_score: Score minimum pour conserver une correspondance
        
    Returns:
        Liste des meilleures correspondances triées par score
    """
    # Regrouper les matches par paire (jira_id, confluence_id)
    pair_matches = {}
    for match in all_matches:
        pair_key = (match["jira_id"], match["confluence_id"])
        
        # Si c'est le premier match pour cette paire ou si le score est meilleur
        if pair_key not in pair_matches or match["match_score"] > pair_matches[pair_key]["match_score"]:
            pair_matches[pair_key] = match
    
    # Récupérer les meilleurs matches et filtrer par score
    best_matches = [match for match in pair_matches.values() if match["match_score"] >= min_score]
    
    # Trier par score (du plus élevé au plus bas)
    best_matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return best_matches

def update_with_matches(jira_data, confluence_data, best_matches):
    """
    Mettre à jour les données JIRA et Confluence avec les correspondances trouvées
    
    Args:
        jira_data: Données JIRA
        confluence_data: Données Confluence
        best_matches: Liste des correspondances
        
    Returns:
        Tuple (données JIRA mises à jour, données Confluence mises à jour)
    """
    # Extraire les éléments
    jira_items = jira_data.get("items", [])
    if not jira_items and "tickets" in jira_data:
        jira_items = jira_data["tickets"]
    
    confluence_items = confluence_data.get("items", [])
    if not confluence_items and "pages" in confluence_data:
        confluence_items = confluence_data["pages"]
    
    # Créer des dictionnaires pour accéder facilement aux éléments par ID
    jira_dict = {ticket["id"]: ticket for ticket in jira_items}
    confluence_dict = {page["id"]: page for page in confluence_items}
    
    # Pour chaque correspondance, mettre à jour les éléments
    for match in best_matches:
        jira_id = match["jira_id"]
        conf_id = match["confluence_id"]
        
        # Mettre à jour le ticket JIRA avec les infos de correspondance
        if jira_id in jira_dict:
            if "confluence_matches" not in jira_dict[jira_id]:
                jira_dict[jira_id]["confluence_matches"] = []
            
            jira_dict[jira_id]["confluence_matches"].append({
                "confluence_id": conf_id,
                "match_score": match["match_score"],
                "match_type": match["match_type"]
            })
        
        # Mettre à jour la page Confluence avec les infos de correspondance
        if conf_id in confluence_dict:
            if "jira_matches" not in confluence_dict[conf_id]:
                confluence_dict[conf_id]["jira_matches"] = []
            
            confluence_dict[conf_id]["jira_matches"].append({
                "jira_id": jira_id,
                "match_score": match["match_score"],
                "match_type": match["match_type"]
            })
    
    # Reconstruire les données JIRA et Confluence avec les éléments mis à jour
    jira_updated = {
        "items": list(jira_dict.values()),
        "metadata": jira_data.get("metadata", {})
    }
    
    confluence_updated = {
        "items": list(confluence_dict.values()),
        "metadata": confluence_data.get("metadata", {})
    }
    
    # Ajouter des métadonnées supplémentaires
    jira_updated["metadata"]["updated_with_matches"] = True
    jira_updated["metadata"]["match_date"] = datetime.now().isoformat()
    
    confluence_updated["metadata"]["updated_with_matches"] = True
    confluence_updated["metadata"]["match_date"] = datetime.now().isoformat()
    
    return jira_updated, confluence_updated

def detect_entities_in_text(text):
    """Détecter des entités dans un texte (IDs, emails, URLs)"""
    if not text:
        return {"ids": [], "emails": [], "urls": []}
    
    # Détecter les IDs (format clé-nombre, comme PROJ-123)
    ids = re.findall(r'([A-Z]+-\d+)', text)
    
    # Détecter les emails
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    
    # Détecter les URLs
    urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
    
    return {
        "ids": list(set(ids)),
        "emails": list(set(emails)),
        "urls": list(set(urls))
    }

def find_matches(jira_items, confluence_items, min_score=0.2):
    """
    Trouver des correspondances entre tickets JIRA et pages Confluence.
    
    Args:
        jira_items: Liste des tickets JIRA
        confluence_items: Liste des pages Confluence
        min_score: Score minimum pour considérer une correspondance
        
    Returns:
        Liste des meilleures correspondances
    """
    all_matches = []
    
    # 1. Chercher les mentions explicites de tickets JIRA dans Confluence
    explicit_mentions = find_mentions(jira_items, confluence_items)
    all_matches.extend(explicit_mentions)
    
    # 2. Chercher les correspondances par similarité de mots-clés
    keyword_matches = find_keyword_matches(jira_items, confluence_items, min_score)
    all_matches.extend(keyword_matches)
    
    # 3. Chercher les correspondances par proximité de dates
    date_matches = find_date_proximity_matches(jira_items, confluence_items)
    all_matches.extend(date_matches)
    
    # 4. Combiner tous les matches et conserver les meilleurs
    best_matches = combine_matches(all_matches, min_score)
    
    return best_matches

def main():
    """
    Point d'entrée principal du script
    """
    parser = argparse.ArgumentParser(description='Trouver les correspondances entre tickets JIRA et pages Confluence')
    parser.add_argument('--jira', required=True, help='Fichier JSON contenant les tickets JIRA')
    parser.add_argument('--confluence', required=True, help='Fichier JSON contenant les pages Confluence')
    parser.add_argument('--output', required=True, help='Fichier JSON de sortie pour les correspondances')
    parser.add_argument('--min-score', type=float, default=0.2, help='Score minimum pour les correspondances (0-1)')
    parser.add_argument('--updated-jira', help='Fichier JSON de sortie pour les tickets JIRA mis à jour')
    parser.add_argument('--updated-confluence', help='Fichier JSON de sortie pour les pages Confluence mises à jour')
    parser.add_argument('--use-llm', action='store_true', help='Utiliser un LLM pour améliorer les correspondances')
    parser.add_argument('--tree-output', default='matches_arborescence.txt', help='Nom du fichier d\'arborescence')
    
    args = parser.parse_args()
    
    # Chemins de sortie par défaut si non spécifiés
    if not args.updated_jira:
        jira_base = os.path.splitext(os.path.basename(args.jira))[0]
        args.updated_jira = f"{jira_base}_with_matches.json"
    
    if not args.updated_confluence:
        confluence_base = os.path.splitext(os.path.basename(args.confluence))[0]
        args.updated_confluence = f"{confluence_base}_with_matches.json"
    
    # S'assurer que les répertoires de sortie existent
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Charger les fichiers JIRA et Confluence
    jira_data = load_json_file(args.jira)
    if not jira_data:
        print(f"Impossible de charger les données JIRA depuis {args.jira}")
        return False
    
    confluence_data = load_json_file(args.confluence)
    if not confluence_data:
        print(f"Impossible de charger les données Confluence depuis {args.confluence}")
        return False
    
    # Extraire les listes d'éléments
    jira_items = jira_data.get("items", [])
    if not jira_items and "tickets" in jira_data:
        jira_items = jira_data["tickets"]
    
    confluence_items = confluence_data.get("items", [])
    if not confluence_items and "pages" in confluence_data:
        confluence_items = confluence_data["pages"]
    
    print(f"Tickets JIRA chargés: {len(jira_items)}")
    print(f"Pages Confluence chargées: {len(confluence_items)}")
    
    # Trouver les correspondances
    best_matches = find_matches(jira_items, confluence_items, min_score=args.min_score)
    
    # Préparer les résultats
    matches_result = {
        "metadata": {
            "jira_source": os.path.basename(args.jira),
            "confluence_source": os.path.basename(args.confluence),
            "match_date": datetime.now().isoformat(),
            "min_score": args.min_score
        },
        "matches": best_matches
    }
    
    # Enregistrer les correspondances
    save_json_file(matches_result, args.output)
    
    # Mettre à jour les données JIRA et Confluence avec les correspondances
    if best_matches:
        jira_updated, confluence_updated = update_with_matches(jira_data, confluence_data, best_matches)
        
        # Enregistrer les données mises à jour
        if args.updated_jira:
            updated_jira_output = args.updated_jira
            save_json_file(jira_updated, updated_jira_output)
        
        if args.updated_confluence:
            updated_confluence_output = args.updated_confluence
            save_json_file(confluence_updated, updated_confluence_output)
    
    # Générer une arborescence pour visualiser les résultats
    try:
        # Déterminer le répertoire de sortie
        if output_dir:
            tree_file = os.path.join(output_dir, args.tree_output)
        else:
            tree_file = args.tree_output
        
        write_tree(os.path.dirname(args.output) or '.', os.path.basename(tree_file))
    except Exception as e:
        print(f"Erreur lors de la génération de l'arborescence: {e}")
    
    print(f"\nMatches trouvés: {len(best_matches)}")
    print(f"Résultats sauvegardés dans:")
    print(f"- {args.output}")
    print(f"- {args.updated_jira}")
    print(f"- {args.updated_confluence}")
    print(f"\nArborescence générée dans {tree_file}" if 'tree_file' in locals() else "")
    
    return True

if __name__ == "__main__":
    main() 