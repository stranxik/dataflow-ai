#!/usr/bin/env python3
# pyright: reportGeneralTypeIssues=false
"""
Module d'extraction de données structurées à partir de JIRA et Confluence
utilisant Outlines pour une extraction précise et robuste.

Ce module fournit des extracteurs spécialisés qui exploitent la capacité
d'Outlines à générer des données structurées à partir de texte.
"""

import json
import os
import re
import logging
import sys
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Import d'Outlines avec gestion des erreurs
try:
    import outlines
    from outlines import models
    from outlines import Template
    from outlines import samplers
    import outlines.generate as generate
    USING_STUB = False
except ImportError as e:
    import traceback
    logging.warning(f"Modules Outlines non disponibles. Utilisation des stubs internes. Erreur: {e}\n{traceback.format_exc()}")
    USING_STUB = True
    try:
        from extract.outlines_stub import models, generate, Template, samplers, IS_STUB
    except ImportError:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from extract.outlines_stub import models, generate, Template, samplers, IS_STUB

# Définir une version de secours pour la classe qui pourrait ne pas être disponible
class FallbackJsonSchemaParser:
    """Version de secours de la classe JsonSchemaParser d'Outlines"""
    def __init__(self, schema):
        self.schema = schema

# Import du nouveau parser JSON basé sur Outlines
try:
    from extract.outlines_enhanced_parser import extract_structured_data, extract_entities
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extract.outlines_enhanced_parser import extract_structured_data, extract_entities

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'API OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1")

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("outlines_extractor")

# Schémas pour l'extraction de données structurées
JIRA_TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Identifiant unique du ticket JIRA (ex: PROJ-123)"
        },
        "title": {
            "type": "string",
            "description": "Titre ou résumé du ticket"
        },
        "type": {
            "type": "string",
            "description": "Type de ticket (bug, tâche, histoire, etc.)"
        },
        "priority": {
            "type": "string",
            "description": "Priorité du ticket"
        },
        "status": {
            "type": "string",
            "description": "Statut actuel du ticket"
        },
        "assignee": {
            "type": "string",
            "description": "Personne assignée au ticket"
        },
        "reporter": {
            "type": "string",
            "description": "Personne ayant créé le ticket"
        },
        "description": {
            "type": "string",
            "description": "Description détaillée du ticket"
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Mots-clés extraits du contenu du ticket"
        },
        "components": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Composants concernés par ce ticket"
        },
        "entities": {
            "type": "object",
            "properties": {
                "mentioned_tickets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Autres tickets JIRA mentionnés dans ce ticket"
                },
                "people": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Personnes mentionnées dans le ticket"
                },
                "organizations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Organisations mentionnées dans le ticket"
                }
            }
        }
    },
    "required": ["id", "title", "description"]
}

CONFLUENCE_PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Identifiant unique de la page Confluence"
        },
        "title": {
            "type": "string",
            "description": "Titre de la page"
        },
        "space": {
            "type": "string",
            "description": "Espace Confluence où se trouve la page"
        },
        "content_summary": {
            "type": "string",
            "description": "Résumé du contenu de la page (max 200 mots)"
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Mots-clés extraits du contenu de la page"
        },
        "entities": {
            "type": "object",
            "properties": {
                "mentioned_tickets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tickets JIRA mentionnés dans cette page"
                },
                "people": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Personnes mentionnées dans la page"
                },
                "organizations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Organisations mentionnées dans la page"
                }
            }
        }
    },
    "required": ["id", "title", "content_summary"]
}

class OutlinesDocumentExtractor:
    """
    Classe pour extraire des informations structurées à partir de documents
    JIRA et Confluence en utilisant Outlines.
    """
    
    def __init__(self, llm_model: str = DEFAULT_LLM_MODEL):
        """
        Initialiser l'extracteur de documents
        
        Args:
            llm_model: Modèle LLM à utiliser pour l'extraction
        """
        self.llm_model = llm_model
        
        # Initialiser le modèle Outlines
        if openai_api_key:
            self.model = models.openai(
                model=llm_model,
                api_key=openai_api_key,
                temperature=0.0
            )
        else:
            logger.warning("Clé API OpenAI non disponible. Les fonctionnalités LLM seront désactivées.")
            self.model = None
    
    def extract_jira_ticket_info(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrait des informations structurées d'un ticket JIRA
        
        Args:
            ticket_data: Données brutes du ticket JIRA
            
        Returns:
            Informations structurées selon JIRA_TICKET_SCHEMA
        """
        if not self.model:
            logger.warning("Modèle LLM non disponible. Extraction limitée.")
            return self._extract_jira_ticket_info_basic(ticket_data)
        
        # Préparation des données pour l'extraction
        # Combiner les champs importants en un texte
        title = ticket_data.get("summary", ticket_data.get("title", ""))
        description = ticket_data.get("description", "")
        comments = ticket_data.get("comments", [])
        
        # Concaténer les commentaires
        comments_text = ""
        if comments:
            if isinstance(comments, list):
                for comment in comments[:5]:  # Limiter à 5 commentaires pour éviter les tokens trop longs
                    if isinstance(comment, dict):
                        comments_text += f"\nCommentaire: {comment.get('body', '')}\n"
                    elif isinstance(comment, str):
                        comments_text += f"\nCommentaire: {comment}\n"
        
        # Créer un texte complet pour l'extraction
        full_text = f"Titre: {title}\n\nDescription: {description}\n\n{comments_text}"
        
        # Extraire les entités nommées directement du texte (personnes, orgs, etc.)
        entities = extract_entities(full_text, model=self.llm_model)
        
        # Utiliser Outlines pour extraire des informations structurées
        # Configuration du prompt pour l'extraction
        prompt_template = """
        Analysez ce ticket JIRA et extrayez les informations structurées selon le schéma fourni:
        
        ID: {id}
        Type: {type}
        Statut: {status}
        Priorité: {priority}
        Assigné à: {assignee}
        Reporter: {reporter}
        
        Titre: {title}
        
        Description:
        {description}
        
        {comments}
        """
        
        # Préparer les valeurs pour le template
        prompt_values = {
            "id": ticket_data.get("key", ticket_data.get("id", "")),
            "type": ticket_data.get("issuetype", {}).get("name", "") if isinstance(ticket_data.get("issuetype"), dict) else ticket_data.get("type", ""),
            "status": ticket_data.get("status", {}).get("name", "") if isinstance(ticket_data.get("status"), dict) else ticket_data.get("status", ""),
            "priority": ticket_data.get("priority", {}).get("name", "") if isinstance(ticket_data.get("priority"), dict) else ticket_data.get("priority", ""),
            "assignee": ticket_data.get("assignee", {}).get("displayName", "") if isinstance(ticket_data.get("assignee"), dict) else ticket_data.get("assignee", ""),
            "reporter": ticket_data.get("reporter", {}).get("displayName", "") if isinstance(ticket_data.get("reporter"), dict) else ticket_data.get("reporter", ""),
            "title": title,
            "description": description[:1000] if description else "",  # Limiter la longueur
            "comments": comments_text[:500] if comments_text else ""   # Limiter la longueur
        }
        
        # Configurer le prompt
        formatted_prompt = prompt_template.format(**prompt_values)
        prompt = prompts.ChatPrompt([
            {"role": "system", "content": "Vous êtes un expert en extraction d'informations structurées à partir de tickets JIRA."},
            {"role": "user", "content": formatted_prompt}
        ])
        
        try:
            # Extraire les données structurées avec Outlines
            parser = JsonSchemaParser(JIRA_TICKET_SCHEMA)
            result = generate(self.model, prompt, guide=parser)
            
            # Fusionner avec les entités extraites séparément
            if "entities" not in result:
                result["entities"] = {}
            
            # Ajouter les entités extraites
            result["entities"]["mentioned_tickets"] = entities.get("ids", [])
            result["entities"]["people"] = entities.get("persons", [])
            result["entities"]["organizations"] = entities.get("organizations", [])
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des informations JIRA: {str(e)}")
            return self._extract_jira_ticket_info_basic(ticket_data)
    
    def _extract_jira_ticket_info_basic(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extraction basique des informations JIRA sans LLM
        
        Args:
            ticket_data: Données brutes du ticket JIRA
            
        Returns:
            Informations structurées extraites manuellement
        """
        # Extraction basique des champs JIRA
        title = ticket_data.get("summary", ticket_data.get("title", ""))
        description = ticket_data.get("description", "")
        
        # Extraire les IDs de tickets mentionnés (PROJ-123)
        mentioned_tickets = []
        if description:
            mentioned_tickets = re.findall(r'([A-Z]+-\d+)', description)
        
        # Extraire des mots-clés simples
        keywords = []
        if description:
            # Nettoyer le texte
            clean_text = re.sub(r'[^\w\s]', ' ', description.lower())
            # Extraire les mots de plus de 3 caractères
            words = [word for word in clean_text.split() if len(word) > 3]
            # Compter la fréquence des mots
            word_count = {}
            for word in words:
                word_count[word] = word_count.get(word, 0) + 1
            # Prendre les mots les plus fréquents
            keywords = [word for word, count in sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        return {
            "id": ticket_data.get("key", ticket_data.get("id", "")),
            "title": title,
            "type": ticket_data.get("issuetype", {}).get("name", "") if isinstance(ticket_data.get("issuetype"), dict) else ticket_data.get("type", ""),
            "priority": ticket_data.get("priority", {}).get("name", "") if isinstance(ticket_data.get("priority"), dict) else ticket_data.get("priority", ""),
            "status": ticket_data.get("status", {}).get("name", "") if isinstance(ticket_data.get("status"), dict) else ticket_data.get("status", ""),
            "assignee": ticket_data.get("assignee", {}).get("displayName", "") if isinstance(ticket_data.get("assignee"), dict) else ticket_data.get("assignee", ""),
            "reporter": ticket_data.get("reporter", {}).get("displayName", "") if isinstance(ticket_data.get("reporter"), dict) else ticket_data.get("reporter", ""),
            "description": description,
            "keywords": keywords,
            "components": [],
            "entities": {
                "mentioned_tickets": mentioned_tickets,
                "people": [],
                "organizations": []
            }
        }
    
    def extract_confluence_page_info(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrait des informations structurées d'une page Confluence
        
        Args:
            page_data: Données brutes de la page Confluence
            
        Returns:
            Informations structurées selon CONFLUENCE_PAGE_SCHEMA
        """
        if not self.model:
            logger.warning("Modèle LLM non disponible. Extraction limitée.")
            return self._extract_confluence_page_info_basic(page_data)
        
        # Préparation des données pour l'extraction
        title = page_data.get("title", "")
        content = page_data.get("markdown", page_data.get("content", ""))
        space = page_data.get("space", {}).get("name", "") if isinstance(page_data.get("space"), dict) else page_data.get("space", "")
        
        # Extraire les entités nommées directement du texte
        entities = extract_entities(content, model=self.llm_model)
        
        # Utiliser Outlines pour extraire des informations structurées
        # Configuration du prompt pour l'extraction
        prompt_template = """
        Analysez cette page Confluence et extrayez les informations structurées selon le schéma fourni:
        
        ID: {id}
        Titre: {title}
        Espace: {space}
        
        Contenu:
        {content}
        """
        
        # Préparer les valeurs pour le template
        prompt_values = {
            "id": page_data.get("id", ""),
            "title": title,
            "space": space,
            "content": content[:2000] if content else ""  # Limiter la longueur
        }
        
        # Configurer le prompt
        formatted_prompt = prompt_template.format(**prompt_values)
        prompt = prompts.ChatPrompt([
            {"role": "system", "content": "Vous êtes un expert en extraction d'informations structurées à partir de pages Confluence."},
            {"role": "user", "content": formatted_prompt}
        ])
        
        try:
            # Extraire les données structurées avec Outlines
            parser = JsonSchemaParser(CONFLUENCE_PAGE_SCHEMA)
            result = generate(self.model, prompt, guide=parser)
            
            # Fusionner avec les entités extraites séparément
            if "entities" not in result:
                result["entities"] = {}
            
            # Ajouter les entités extraites
            result["entities"]["mentioned_tickets"] = entities.get("ids", [])
            result["entities"]["people"] = entities.get("persons", [])
            result["entities"]["organizations"] = entities.get("organizations", [])
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des informations Confluence: {str(e)}")
            return self._extract_confluence_page_info_basic(page_data)
    
    def _extract_confluence_page_info_basic(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extraction basique des informations Confluence sans LLM
        
        Args:
            page_data: Données brutes de la page Confluence
            
        Returns:
            Informations structurées extraites manuellement
        """
        title = page_data.get("title", "")
        content = page_data.get("markdown", page_data.get("content", ""))
        space = page_data.get("space", {}).get("name", "") if isinstance(page_data.get("space"), dict) else page_data.get("space", "")
        
        # Extraire les IDs de tickets mentionnés (PROJ-123)
        mentioned_tickets = []
        if content:
            mentioned_tickets = re.findall(r'([A-Z]+-\d+)', content)
        
        # Créer un résumé simple
        content_summary = content[:500] + "..." if content and len(content) > 500 else content
        
        # Extraire des mots-clés simples
        keywords = []
        if content:
            # Nettoyer le texte
            clean_text = re.sub(r'[^\w\s]', ' ', content.lower())
            # Extraire les mots de plus de 3 caractères
            words = [word for word in clean_text.split() if len(word) > 3]
            # Compter la fréquence des mots
            word_count = {}
            for word in words:
                word_count[word] = word_count.get(word, 0) + 1
            # Prendre les mots les plus fréquents
            keywords = [word for word, count in sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        return {
            "id": page_data.get("id", ""),
            "title": title,
            "space": space,
            "content_summary": content_summary,
            "keywords": keywords,
            "entities": {
                "mentioned_tickets": mentioned_tickets,
                "people": [],
                "organizations": []
            }
        }

def process_jira_data(jira_data: Dict[str, Any], model: str = DEFAULT_LLM_MODEL) -> Dict[str, Any]:
    """
    Traite un fichier de données JIRA pour extraire des informations structurées
    
    Args:
        jira_data: Données JIRA chargées depuis un fichier JSON
        model: Modèle LLM à utiliser
        
    Returns:
        Données JIRA structurées prêtes pour le système RAG
    """
    extractor = OutlinesDocumentExtractor(llm_model=model)
    
    # Trouver les tickets dans la structure
    tickets = []
    if "items" in jira_data and isinstance(jira_data["items"], list):
        tickets = jira_data["items"]
    elif isinstance(jira_data, list):
        tickets = jira_data
    
    # Traiter chaque ticket
    processed_tickets = []
    for ticket in tickets:
        try:
            processed_ticket = extractor.extract_jira_ticket_info(ticket)
            processed_tickets.append(processed_ticket)
        except Exception as e:
            logger.error(f"Erreur lors du traitement d'un ticket JIRA: {str(e)}")
            # Ajouter le ticket original en cas d'erreur
            processed_tickets.append(ticket)
    
    # Construire le résultat
    return {
        "items": processed_tickets,
        "metadata": {
            "processed_at": jira_data.get("metadata", {}).get("processed_at", ""),
            "source_file": jira_data.get("metadata", {}).get("source_file", ""),
            "extractor": "OutlinesDocumentExtractor",
            "model": model
        }
    }

def process_confluence_data(confluence_data: Dict[str, Any], model: str = DEFAULT_LLM_MODEL) -> Dict[str, Any]:
    """
    Traite un fichier de données Confluence pour extraire des informations structurées
    
    Args:
        confluence_data: Données Confluence chargées depuis un fichier JSON
        model: Modèle LLM à utiliser
        
    Returns:
        Données Confluence structurées prêtes pour le système RAG
    """
    extractor = OutlinesDocumentExtractor(llm_model=model)
    
    # Trouver les pages dans la structure
    pages = []
    if "items" in confluence_data and isinstance(confluence_data["items"], list):
        pages = confluence_data["items"]
    elif isinstance(confluence_data, list):
        pages = confluence_data
    
    # Traiter chaque page
    processed_pages = []
    for page in pages:
        try:
            processed_page = extractor.extract_confluence_page_info(page)
            processed_pages.append(processed_page)
        except Exception as e:
            logger.error(f"Erreur lors du traitement d'une page Confluence: {str(e)}")
            # Ajouter la page originale en cas d'erreur
            processed_pages.append(page)
    
    # Construire le résultat
    return {
        "items": processed_pages,
        "metadata": {
            "processed_at": confluence_data.get("metadata", {}).get("processed_at", ""),
            "source_file": confluence_data.get("metadata", {}).get("source_file", ""),
            "extractor": "OutlinesDocumentExtractor",
            "model": model
        }
    }

if __name__ == "__main__":
    # Test du module avec des fichiers spécifiés en arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Extraire des informations structurées de données JIRA et Confluence")
    parser.add_argument("--jira", help="Fichier JSON de données JIRA")
    parser.add_argument("--confluence", help="Fichier JSON de données Confluence")
    parser.add_argument("--output", help="Dossier de sortie", default="results")
    parser.add_argument("--model", help="Modèle LLM à utiliser", default=DEFAULT_LLM_MODEL)
    
    args = parser.parse_args()
    
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(args.output, exist_ok=True)
    
    # Traiter les données JIRA
    if args.jira:
        try:
            with open(args.jira, 'r', encoding='utf-8') as f:
                jira_data = json.load(f)
            
            processed_jira = process_jira_data(jira_data, model=args.model)
            
            # Sauvegarder le résultat
            output_file = os.path.join(args.output, f"jira_processed_{Path(args.jira).stem}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_jira, f, indent=2, ensure_ascii=False)
            
            print(f"Données JIRA traitées et sauvegardées dans {output_file}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier JIRA: {str(e)}")
    
    # Traiter les données Confluence
    if args.confluence:
        try:
            with open(args.confluence, 'r', encoding='utf-8') as f:
                confluence_data = json.load(f)
            
            processed_confluence = process_confluence_data(confluence_data, model=args.model)
            
            # Sauvegarder le résultat
            output_file = os.path.join(args.output, f"confluence_processed_{Path(args.confluence).stem}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_confluence, f, indent=2, ensure_ascii=False)
            
            print(f"Données Confluence traitées et sauvegardées dans {output_file}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier Confluence: {str(e)}") 