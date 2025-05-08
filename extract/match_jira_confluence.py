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

def load_json_file(file_path):
    """Charger un fichier JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return safe_json_load(f, log_prefix=file_path)
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
        page_text = page["title"] + " " + page["content"]["markdown"]
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
        # Combiner le titre et la description pour obtenir plus de mots-clés
        text = ticket["content"]["title"] + " " + ticket["content"]["description"]
        jira_keywords[ticket["id"]] = text_to_words(text)
    
    # Préparer les mots-clés des pages Confluence
    confluence_keywords = {}
    for page in confluence_pages:
        # Combiner le titre et le contenu markdown
        text = page["title"] + " " + page["content"]["markdown"]
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
    """Combiner et filtrer tous les matches pour obtenir les meilleurs pour chaque ticket JIRA"""
    # Regrouper les matches par ticket JIRA
    jira_matches = defaultdict(list)
    for match in all_matches:
        jira_matches[match["jira_id"]].append(match)
    
    # Pour chaque ticket JIRA, sélectionner les meilleurs matches
    best_matches = {}
    for jira_id, matches in jira_matches.items():
        # Trier par score de match (du plus élevé au plus bas)
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Filtrer les matches avec un score suffisant
        good_matches = [m for m in matches if m["match_score"] >= min_score]
        
        # Limiter à 5 best matches maximum par ticket
        best_matches[jira_id] = good_matches[:5]
    
    return best_matches

def update_with_matches(jira_data, confluence_data, best_matches):
    """Mettre à jour les données JIRA et Confluence avec les matches trouvés"""
    # Créer des dictionnaires pour un accès rapide
    jira_dict = {ticket["id"]: ticket for ticket in jira_data["tickets"]}
    confluence_dict = {page["id"]: page for page in confluence_data["pages"]}
    
    # Mettre à jour les tickets JIRA avec les liens vers Confluence
    for jira_id, matches in best_matches.items():
        if jira_id in jira_dict:
            # Créer une liste de liens Confluence
            conf_links = []
            for match in matches:
                conf_id = match["confluence_id"]
                if conf_id in confluence_dict:
                    conf_page = confluence_dict[conf_id]
                    conf_links.append({
                        "id": conf_id,
                        "title": conf_page["title"],
                        "match_type": match["match_type"],
                        "match_score": match["match_score"]
                    })
            
            # Mettre à jour le ticket JIRA
            jira_dict[jira_id]["confluence_links"] = conf_links
    
    # Mettre à jour les pages Confluence avec les liens vers les tickets JIRA
    # Inverser la structure des matches pour trouver tous les tickets liés à une page
    page_to_tickets = defaultdict(list)
    for jira_id, matches in best_matches.items():
        for match in matches:
            conf_id = match["confluence_id"]
            if jira_id in jira_dict:
                page_to_tickets[conf_id].append({
                    "id": jira_id,
                    "title": jira_dict[jira_id]["content"]["title"],
                    "match_type": match["match_type"],
                    "match_score": match["match_score"]
                })
    
    # Mettre à jour chaque page Confluence
    for conf_id, ticket_links in page_to_tickets.items():
        if conf_id in confluence_dict:
            confluence_dict[conf_id]["relationships"]["jira_tickets"] = ticket_links
    
    return jira_data, confluence_data

def main():
    parser = argparse.ArgumentParser(description="Faire correspondre les tickets JIRA et les pages Confluence")
    parser.add_argument("--jira", required=True, help="Fichier JSON contenant les tickets JIRA transformés")
    parser.add_argument("--confluence", required=True, help="Fichier JSON contenant les pages Confluence transformées")
    parser.add_argument("--output", default="matches.json", help="Fichier de sortie pour les correspondances")
    parser.add_argument("--updated-jira", default="jira_with_matches.json", help="Fichier de sortie pour les tickets JIRA mis à jour")
    parser.add_argument("--updated-confluence", default="confluence_with_matches.json", help="Fichier de sortie pour les pages Confluence mises à jour")
    parser.add_argument("--min-score", type=float, default=0.2, help="Score minimum pour considérer une correspondance")
    
    args = parser.parse_args()
    
    # 1. Charger les données
    print("Chargement des données JIRA et Confluence...")
    jira_data = load_json_file(args.jira)
    confluence_data = load_json_file(args.confluence)
    
    if not jira_data or not confluence_data:
        print("Erreur: Impossible de charger les données. Vérifiez les fichiers d'entrée.")
        return
    
    jira_tickets = jira_data["tickets"]
    confluence_pages = confluence_data["pages"]
    
    print(f"Données chargées: {len(jira_tickets)} tickets JIRA et {len(confluence_pages)} pages Confluence")
    
    # 2. Trouver les correspondances
    print("\nRecherche des mentions explicites...")
    mention_matches = find_mentions(jira_tickets, confluence_pages)
    print(f"Trouvé {len(mention_matches)} mentions explicites.")
    
    print("\nRecherche des correspondances par mots-clés...")
    keyword_matches = find_keyword_matches(jira_tickets, confluence_pages, min_similarity=args.min_score)
    print(f"Trouvé {len(keyword_matches)} correspondances par mots-clés.")
    
    print("\nRecherche des correspondances par proximité temporelle...")
    date_matches = find_date_proximity_matches(jira_tickets, confluence_pages, date_threshold_days=7)
    print(f"Trouvé {len(date_matches)} correspondances par proximité temporelle.")
    
    # 3. Combiner toutes les correspondances
    print("\nCombination de toutes les correspondances...")
    all_matches = mention_matches + keyword_matches + date_matches
    best_matches = combine_matches(all_matches, min_score=args.min_score)
    
    # Compter le nombre total de tickets ayant au moins une correspondance
    tickets_with_matches = len(best_matches)
    total_matches = sum(len(matches) for matches in best_matches.values())
    
    print(f"Au total, {tickets_with_matches} tickets JIRA sur {len(jira_tickets)} ont des correspondances")
    print(f"Nombre total de correspondances: {total_matches}")
    
    # 4. Sauvegarder les correspondances
    print("\nSauvegarde des correspondances...")
    save_json_file(best_matches, args.output)
    
    # 5. Mettre à jour les données JIRA et Confluence avec les correspondances
    print("\nMise à jour des données JIRA et Confluence avec les correspondances...")
    updated_jira, updated_confluence = update_with_matches(jira_data, confluence_data, best_matches)
    
    # 6. Sauvegarder les données mises à jour
    print("\nSauvegarde des données mises à jour...")
    save_json_file(updated_jira, args.updated_jira)
    save_json_file(updated_confluence, args.updated_confluence)
    
    print("\nTraitement terminé avec succès!")

    # Générer l'arborescence du dossier courant
    write_tree(os.getcwd())
    print(f"\nArborescence du dossier générée dans {os.path.join(os.getcwd(), 'arborescence.txt')}")

if __name__ == "__main__":
    main() 