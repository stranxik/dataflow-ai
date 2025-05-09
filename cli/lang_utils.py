#!/usr/bin/env python3
"""
Utilitaire de gestion des traductions pour l'interface CLI
"""

import os
import json
import locale
from typing import Dict, Any, Optional

# Chemin vers le fichier de traductions
TRANSLATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations.json")

# Variable globale pour stocker les traductions
_translations: Dict[str, Dict[str, Any]] = {}
_current_lang = None

def load_translations() -> Dict[str, Dict[str, Any]]:
    """
    Charge les traductions depuis le fichier JSON
    
    Returns:
        Dict contenant toutes les traductions par langue
    """
    global _translations
    
    if _translations:
        return _translations
    
    try:
        if os.path.exists(TRANSLATIONS_FILE):
            with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
                _translations = json.load(f)
            return _translations
        else:
            print(f"Fichier de traductions non trouvé: {TRANSLATIONS_FILE}")
            _translations = {"fr": {}, "en": {}}
            return _translations
    except Exception as e:
        print(f"Erreur lors du chargement des traductions: {e}")
        _translations = {"fr": {}, "en": {}}
        return _translations

def detect_language() -> str:
    """
    Détecte la langue du système
    
    Returns:
        Code de langue (fr, en, etc.)
    """
    try:
        system_lang = locale.getdefaultlocale()[0]
        if system_lang:
            lang_code = system_lang.split('_')[0].lower()
            return lang_code if lang_code in ["fr", "en"] else "en"
        return "en"
    except:
        return "en"

def set_language(lang: str) -> None:
    """
    Définit la langue courante
    
    Args:
        lang: Code de langue (fr, en)
    """
    global _current_lang
    _current_lang = lang if lang in ["fr", "en"] else "en"

def get_current_language() -> str:
    """
    Obtient la langue courante
    
    Returns:
        Code de langue actuel
    """
    global _current_lang
    if _current_lang is None:
        _current_lang = detect_language()
    return _current_lang

def t(key: str, category: Optional[str] = None, lang: Optional[str] = None) -> str:
    """
    Obtient la traduction pour une clé donnée
    
    Args:
        key: Clé de traduction
        category: Catégorie de la clé (optional)
        lang: Langue (si différente de la langue courante)
        
    Returns:
        Texte traduit
    """
    # S'assurer que les traductions sont chargées
    load_translations()
    
    # Déterminer la langue à utiliser
    use_lang = lang or get_current_language()
    
    # Si la langue n'existe pas, fallback sur le français ou l'anglais
    if use_lang not in _translations:
        use_lang = "fr" if "fr" in _translations else "en"
    
    # Récupérer le dictionnaire de traduction pour la langue
    lang_dict = _translations.get(use_lang, {})
    
    # Si une catégorie est spécifiée, chercher la clé dans cette catégorie
    if category:
        category_dict = lang_dict.get(category, {})
        if isinstance(category_dict, dict):
            if key in category_dict:
                return category_dict[key]
    
    # Sinon, chercher la clé directement dans toutes les catégories
    for cat, values in lang_dict.items():
        if isinstance(values, dict) and key in values:
            return values[key]
    
    # Si la clé n'est pas trouvée, retourner la clé elle-même
    return key

# Initialiser les traductions au chargement du module
load_translations() 