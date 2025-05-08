"""
Package d'extraction et de traitement des données JSON pour JIRA et Confluence.
Inclut des extracteurs spécialisés et des parsers robustes.
"""

# Import des modules nécessaires
import os
import sys

# Ajouter ce répertoire au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importations pour faciliter l'accès aux fonctions principales
try:
    from extract.outlines_enhanced_parser import (
        outlines_robust_json_parser,
        extract_entities,
        extract_structured_data,
        is_using_stub,
        get_outlines_status
    )
    from extract.outlines_extractor import process_jira_data, process_confluence_data
except ImportError:
    import logging
    logging.warning("Erreur lors de l'import des modules d'extraction. Utilisation de stubs internes ou modules non disponibles.")
    

__all__ = [
    'outlines_robust_json_parser',
    'extract_entities', 
    'extract_structured_data',
    'process_jira_data', 
    'process_confluence_data',
    'is_using_stub',
    'get_outlines_status'
] 