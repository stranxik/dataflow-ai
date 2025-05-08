#!/usr/bin/env python3
"""
Processeur JSON générique capable d'analyser, transformer et adapter
n'importe quelle structure JSON pour l'utilisation avec LLM.

Ce script offre :
1. Détection automatique de la structure JSON
2. Système de mappers personnalisables
3. Transformation flexible des données
"""

import json
import os
import sys
import re
import ijson
import argparse
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional, Union, Tuple
import logging

# Types pour les mappers personnalisés
MapperFunc = Callable[[Dict[str, Any]], Dict[str, Any]]
FieldMapType = Dict[str, Union[str, List[str], Dict[str, str]]]

class GenericJsonProcessor:
    """
    Classe qui traite n'importe quelle structure JSON de manière flexible
    """
    
    def __init__(self, 
                 field_mappings: Optional[FieldMapType] = None,
                 custom_mapper: Optional[MapperFunc] = None,
                 detect_fields: bool = True,
                 extract_keywords: bool = True):
        """
        Initialiser le processeur
        
        Args:
            field_mappings: Correspondances entre champs source et cible
            custom_mapper: Fonction personnalisée pour transformer un objet
            detect_fields: Si vrai, tente de détecter automatiquement les champs importants
            extract_keywords: Si vrai, extrait des mots-clés du texte
        """
        self.field_mappings = field_mappings or {}
        self.custom_mapper = custom_mapper
        self.detect_fields = detect_fields
        self.extract_keywords = extract_keywords
        
        # Statistiques
        self.stats = {
            "processed_items": 0,
            "extracted_keywords": 0,
            "detected_fields": set()
        }
    
    def detect_json_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Détecte la structure d'un fichier JSON en analysant un échantillon
        
        Args:
            file_path: Chemin vers le fichier JSON
            
        Returns:
            Dictionnaire avec les informations sur la structure détectée
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Lire les 8KB pour l'analyse
                sample = f.read(8192)
                
                # Vérifier si c'est un tableau ou un objet
                is_array = sample.strip().startswith('[')
                
                # Revenir au début du fichier
                f.seek(0)
                
                # Essayer de lire le premier élément pour en extraire les champs
                if is_array:
                    # Pour un tableau, lire le premier élément
                    parser = ijson.items(f, 'item')
                    try:
                        first_item = next(parser)
                        fields = list(first_item.keys()) if isinstance(first_item, dict) else []
                    except StopIteration:
                        fields = []
                else:
                    # Pour un objet, lire les clés de premier niveau
                    try:
                        # Lire juste assez pour obtenir la structure de premier niveau
                        first_level = json.loads(sample + '}' if '{' in sample and '}' not in sample else sample)
                        fields = list(first_level.keys()) if isinstance(first_level, dict) else []
                    except json.JSONDecodeError:
                        # Si erreur de décodage, essayer de lire tout le fichier
                        f.seek(0)
                        try:
                            data = json.load(f)
                            fields = list(data.keys()) if isinstance(data, dict) else []
                        except json.JSONDecodeError:
                            fields = []
                
                # Détecter les champs qui pourraient contenir du texte, des identifiants, des dates, etc.
                detected_structure = {}
                if self.detect_fields and fields:
                    field_types = {}
                    text_fields = []
                    id_fields = []
                    date_fields = []
                    
                    common_text_fields = ['title', 'description', 'content', 'text', 'body', 'markdown', 'comment', 'message']
                    common_id_fields = ['id', 'key', 'uuid', 'slug', 'ref']
                    common_date_fields = ['date', 'created', 'updated', 'timestamp', 'time', 'modified']
                    
                    for field in fields:
                        field_lower = field.lower()
                        
                        # Détecter les champs textuels
                        if any(text_field in field_lower for text_field in common_text_fields):
                            text_fields.append(field)
                            field_types[field] = 'text'
                        
                        # Détecter les champs d'identifiants
                        elif any(id_field in field_lower for id_field in common_id_fields):
                            id_fields.append(field)
                            field_types[field] = 'id'
                        
                        # Détecter les champs de dates
                        elif any(date_field in field_lower for date_field in common_date_fields):
                            date_fields.append(field)
                            field_types[field] = 'date'
                        
                        else:
                            field_types[field] = 'unknown'
                    
                    detected_structure = {
                        "text_fields": text_fields,
                        "id_fields": id_fields,
                        "date_fields": date_fields,
                        "field_types": field_types
                    }
                    
                    self.stats["detected_fields"] = set(fields)
                
                return {
                    "is_array": is_array,
                    "all_fields": fields,
                    "detected_structure": detected_structure,
                    "filename": os.path.basename(file_path),
                    "filesize": os.path.getsize(file_path)
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "filename": os.path.basename(file_path)
            }
    
    def extract_keywords_from_text(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extrait des mots-clés pertinents d'un texte
        
        Args:
            text: Texte à analyser
            max_keywords: Nombre maximum de mots-clés à extraire
            
        Returns:
            Liste de mots-clés
        """
        if not text or not isinstance(text, str):
            return []
        
        # Nettoyer le texte
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Diviser en mots et filtrer les mots courts
        words = [word for word in cleaned_text.split() if len(word) > 3]
        
        # Compter la fréquence des mots
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Trier par fréquence et prendre les top mots
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:max_keywords]]
        
        self.stats["extracted_keywords"] += len(keywords)
        
        return keywords
    
    def clean_text(self, text: str) -> str:
        """
        Nettoie un texte en supprimant les balises et caractères spéciaux
        
        Args:
            text: Texte à nettoyer
            
        Returns:
            Texte nettoyé
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Nettoyer les balises HTML
        cleaned_text = re.sub(r'<.*?>', '', text)
        
        # Nettoyer les balises markdown et wiki
        cleaned_text = re.sub(r'!\[.*?\]\(.*?\)', '', cleaned_text)  # Images
        cleaned_text = re.sub(r'\[.*?\]\(.*?\)', '', cleaned_text)    # Liens
        cleaned_text = re.sub(r'`.*?`', '', cleaned_text)             # Code inline
        cleaned_text = re.sub(r'```.*?```', '', cleaned_text, flags=re.DOTALL)  # Blocs de code
        
        return cleaned_text.strip()
    
    def detect_entities_in_text(self, text: str) -> Dict[str, List[str]]:
        """
        Détecte des entités dans un texte (IDs, emails, URLs)
        
        Args:
            text: Texte à analyser
            
        Returns:
            Dictionnaire avec des listes d'entités détectées
        """
        if not text or not isinstance(text, str):
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
    
    def apply_field_mapping(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique une transformation basée sur les mappings de champs définis
        
        Args:
            item: Élément JSON à transformer
            
        Returns:
            Élément transformé
        """
        if not self.field_mappings:
            return item
        
        result = {}
        
        # Appliquer les mappings
        for target_field, source_spec in self.field_mappings.items():
            # Cas simple: mapping direct d'un champ à un autre
            if isinstance(source_spec, str):
                if source_spec in item:
                    result[target_field] = item[source_spec]
            
            # Cas composé: liste de champs à essayer (premier non vide)
            elif isinstance(source_spec, list):
                for source_field in source_spec:
                    if source_field in item and item[source_field]:
                        result[target_field] = item[source_field]
                        break
            
            # Cas complexe: dictionnaire avec spécifications supplémentaires
            elif isinstance(source_spec, dict):
                if "field" in source_spec and source_spec["field"] in item:
                    value = item[source_spec["field"]]
                    
                    # Appliquer transformations selon les specs
                    if "transform" in source_spec:
                        transform_type = source_spec["transform"]
                        if transform_type == "clean_text" and isinstance(value, str):
                            value = self.clean_text(value)
                        elif transform_type == "extract_keywords" and isinstance(value, str):
                            value = self.extract_keywords_from_text(value)
                        elif transform_type == "detect_entities" and isinstance(value, str):
                            value = self.detect_entities_in_text(value)
                    
                    result[target_field] = value
        
        return result
    
    def generate_standard_mapper(self, structure: Dict[str, Any]) -> MapperFunc:
        """
        Génère un mapper standard basé sur la structure détectée
        
        Args:
            structure: Structure détectée du JSON
            
        Returns:
            Fonction de mapping
        """
        detected = structure.get("detected_structure", {})
        id_fields = detected.get("id_fields", [])
        text_fields = detected.get("text_fields", [])
        date_fields = detected.get("date_fields", [])
        
        def standard_mapper(item: Dict[str, Any]) -> Dict[str, Any]:
            result = {"metadata": {}, "content": {}, "analysis": {}}
            
            # ID principal
            for id_field in id_fields:
                if id_field in item:
                    result["id"] = item[id_field]
                    break
            
            # Contenu textuel
            for text_field in text_fields:
                if text_field in item:
                    clean_text = self.clean_text(item[text_field])
                    result["content"][text_field] = clean_text
                    
                    # Si c'est le titre, le mettre aussi au niveau principal
                    if text_field.lower() in ["title", "name", "subject"]:
                        result["title"] = clean_text
            
            # Métadonnées (dates)
            for date_field in date_fields:
                if date_field in item:
                    result["metadata"][date_field] = item[date_field]
            
            # Analyse de texte
            all_text = " ".join([
                result["content"].get(field, "") 
                for field in result["content"]
            ])
            
            if all_text and self.extract_keywords:
                result["analysis"]["keywords"] = self.extract_keywords_from_text(all_text)
                result["analysis"]["entities"] = self.detect_entities_in_text(all_text)
            
            return result
        
        return standard_mapper
    
    def process_file(self, 
                     input_file: str, 
                     output_file: str, 
                     max_items: Optional[int] = None,
                     root_key: str = "items") -> bool:
        """
        Traite un fichier JSON complet, transforme les données et les sauvegarde
        
        Args:
            input_file: Chemin du fichier JSON d'entrée
            output_file: Chemin du fichier JSON de sortie
            max_items: Nombre maximum d'éléments à traiter
            root_key: Clé de premier niveau pour les éléments dans le JSON de sortie
            
        Returns:
            True si le traitement a réussi, False sinon
        """
        try:
            # 1. Détecter la structure
            structure = self.detect_json_structure(input_file)
            print(f"Structure détectée: {len(structure.get('all_fields', []))} champs")
            
            # 2. Définir un mapper (personnalisé ou standard)
            mapper = self.custom_mapper
            if not mapper:
                mapper = self.generate_standard_mapper(structure)
            
            # 3. Traiter le fichier par morceaux
            transformed_items = []
            
            with open(input_file, 'r', encoding='utf-8') as f:
                if structure.get("is_array", True):
                    # Fichier est un tableau JSON
                    parser = ijson.items(f, 'item')
                    
                    for i, item in enumerate(parser):
                        if max_items and i >= max_items:
                            break
                        
                        # Appliquer le mapping personnalisé
                        transformed = mapper(item)
                        
                        # Appliquer le mapping de champs
                        if self.field_mappings:
                            field_mapped = self.apply_field_mapping(item)
                            # Fusionner avec les résultats du mapper
                            for key, value in field_mapped.items():
                                if key not in transformed:
                                    transformed[key] = value
                        
                        transformed_items.append(transformed)
                        self.stats["processed_items"] += 1
                        
                        if i % 100 == 0:
                            print(f"Traitement en cours: {i} éléments")
                else:
                    # Fichier est un objet JSON unique
                    data = json.load(f)
                    transformed = mapper(data)
                    
                    if self.field_mappings:
                        field_mapped = self.apply_field_mapping(data)
                        # Fusionner
                        for key, value in field_mapped.items():
                            if key not in transformed:
                                transformed[key] = value
                    
                    transformed_items.append(transformed)
                    self.stats["processed_items"] += 1
            
            # 4. Sauvegarder le résultat
            result = {
                root_key: transformed_items,
                "metadata": {
                    "source_file": os.path.basename(input_file),
                    "processed_at": datetime.now().isoformat(),
                    "structure": {
                        "fields": structure.get("all_fields", []),
                        "is_array": structure.get("is_array", True)
                    },
                    "stats": {
                        "processed_items": self.stats["processed_items"],
                        "extracted_keywords": self.stats["extracted_keywords"]
                    }
                }
            }
            
            # Créer le répertoire de sortie s'il n'existe pas
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # 5. Générer l'arborescence du fichier traité
            output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "."
            file_base_name = os.path.splitext(os.path.basename(input_file))[0]
            arborescence_file = f"{file_base_name}_arborescence.txt"
            write_file_structure(input_file, output_dir, arborescence_file)
            
            print(f"Traitement terminé: {len(transformed_items)} éléments sauvegardés dans {output_file}")
            print(f"Structure du fichier générée dans {os.path.join(output_dir, arborescence_file)}")
            return True
            
        except Exception as e:
            print(f"Erreur lors du traitement de {input_file}: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    parser = argparse.ArgumentParser(description="Processeur JSON générique pour analyse et transformation")
    parser.add_argument("--input", required=True, help="Fichier JSON d'entrée")
    parser.add_argument("--output", required=True, help="Fichier JSON de sortie")
    parser.add_argument("--max-items", type=int, default=None, help="Nombre maximum d'éléments à traiter")
    parser.add_argument("--mapping-file", help="Fichier JSON avec les mappings de champs personnalisés")
    parser.add_argument("--root-key", default="items", help="Clé de premier niveau pour les éléments dans le JSON de sortie")
    parser.add_argument("--no-keywords", action="store_true", help="Désactiver l'extraction de mots-clés")
    parser.add_argument("--no-detection", action="store_true", help="Désactiver la détection automatique des champs")
    
    args = parser.parse_args()
    
    # Charger les mappings personnalisés
    field_mappings = None
    if args.mapping_file:
        try:
            with open(args.mapping_file, 'r', encoding='utf-8') as f:
                field_mappings = json.load(f)
            print(f"Mappings chargés depuis {args.mapping_file}")
        except Exception as e:
            print(f"Erreur lors du chargement des mappings: {e}")
            field_mappings = None
    
    # Créer le processeur
    processor = GenericJsonProcessor(
        field_mappings=field_mappings,
        detect_fields=not args.no_detection,
        extract_keywords=not args.no_keywords
    )
    
    # Traiter le fichier
    success = processor.process_file(
        input_file=args.input,
        output_file=args.output,
        max_items=args.max_items,
        root_key=args.root_key
    )
    
    if success:
        print("Traitement terminé avec succès")
    else:
        print("Erreur lors du traitement")
        sys.exit(1)

def remove_trailing_commas(json_str):
    # Supprime les virgules en trop avant ] ou }
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str

def safe_json_load(fp, log_prefix=None):
    """Charge un JSON de façon robuste, corrige les trailing commas si besoin."""
    try:
        return json.load(fp)
    except json.JSONDecodeError as e:
        # Tenter de corriger les trailing commas
        fp.seek(0)
        raw = fp.read()
        fixed = remove_trailing_commas(raw)
        try:
            data = json.loads(fixed)
            if log_prefix:
                logging.warning(f"[{log_prefix}] Correction automatique des trailing commas appliquée.")
            return data
        except Exception as e2:
            if log_prefix:
                logging.error(f"[{log_prefix}] Erreur de parsing JSON même après correction: {e2}")
            raise

def write_tree(root_path, output_file="arborescence.txt"):
    """
    Génère une arborescence combinant les structures des fichiers dans root_path.
    Cette fonction agrège les arborescences de contenu de chaque fichier JSON.
    
    Args:
        root_path: Dossier contenant les fichiers à analyser
        output_file: Nom du fichier de sortie pour l'arborescence
    """
    import os
    import json
    import glob
    from datetime import datetime
    
    # Créer un rapport d'arborescence
    report = [f"# Arborescence des fichiers traités dans {os.path.basename(os.path.abspath(root_path))}"]
    report.append(f"# Généré le {datetime.now().isoformat()}")
    report.append("=" * 80)
    report.append("")
    
    # Trouver tous les fichiers JSON
    json_files = []
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    # Si aucun fichier JSON trouvé, analyser tous les fichiers dans le répertoire principal
    if not json_files and os.path.isdir(root_path):
        files = [f for f in os.listdir(root_path) if os.path.isfile(os.path.join(root_path, f))]
        if files:
            report.append(f"## Aucun fichier JSON trouvé, liste des fichiers dans {root_path}:")
            for file in sorted(files):
                file_path = os.path.join(root_path, file)
                file_size = os.path.getsize(file_path)
                report.append(f"- {file} ({file_size} octets)")
            
            with open(os.path.join(root_path, output_file), "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            return
    
    # Pour chaque fichier JSON, essayer d'extraire sa structure
    for json_file in sorted(json_files):
        rel_path = os.path.relpath(json_file, root_path)
        report.append(f"## {rel_path}")
        
        try:
            # Lire un échantillon du fichier
            with open(json_file, 'r', encoding='utf-8') as f:
                try:
                    sample_content = f.read(50000)
                    if os.path.getsize(json_file) > 50000:
                        sample_content += "..."
                    
                    try:
                        # Essayer de parser le JSON
                        data = json.loads(sample_content)
                        
                        # Analyser la structure
                        if isinstance(data, list):
                            report.append(f"- Type: Array avec {len(data)} éléments")
                            if data:
                                if isinstance(data[0], dict):
                                    report.append(f"- Premier élément: Object avec clés {', '.join(data[0].keys())}")
                                else:
                                    report.append(f"- Premier élément: {type(data[0]).__name__}")
                        elif isinstance(data, dict):
                            report.append(f"- Type: Object avec {len(data)} clés")
                            report.append(f"- Clés principales: {', '.join(data.keys())}")
                            
                            # Afficher quelques valeurs d'exemple
                            for key, value in list(data.items())[:3]:
                                if isinstance(value, (dict, list)):
                                    if isinstance(value, dict):
                                        report.append(f"  - {key}: Object avec {len(value)} clés")
                                    else:
                                        report.append(f"  - {key}: Array avec {len(value)} éléments")
                                else:
                                    val_str = str(value)
                                    if len(val_str) > 50:
                                        val_str = val_str[:47] + "..."
                                    report.append(f"  - {key}: {val_str}")
                        
                        report.append("")
                    except json.JSONDecodeError as e:
                        report.append(f"- Erreur de parsing JSON: {str(e)}")
                        report.append("")
                except Exception as e:
                    report.append(f"- Erreur lors de la lecture: {str(e)}")
                    report.append("")
        except Exception as e:
            report.append(f"- Erreur d'accès au fichier: {str(e)}")
            report.append("")
    
    # Ajouter des infos sur les sous-dossiers
    if os.path.isdir(root_path):
        subdirs = [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))]
        if subdirs:
            report.append("## Sous-dossiers:")
            for subdir in sorted(subdirs):
                subdir_path = os.path.join(root_path, subdir)
                files_count = sum(1 for _ in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, _)))
                report.append(f"- {subdir}/ ({files_count} fichiers)")
            report.append("")
    
    # Écrire le rapport dans le fichier
    with open(os.path.join(root_path, output_file), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

def write_file_structure(input_file, output_dir, output_file="arborescence.txt"):
    """
    Génère un fichier décrivant la structure et le contenu d'un fichier JSON traité.
    
    Args:
        input_file: Le fichier JSON source qui a été traité
        output_dir: Le répertoire où écrire le fichier d'arborescence
        output_file: Nom du fichier d'arborescence à générer
    """
    import os
    import json
    import re
    from datetime import datetime
    
    # Structure de base pour le rapport
    file_structure = {
        "nom_fichier": os.path.basename(input_file),
        "chemin_complet": os.path.abspath(input_file),
        "taille": os.path.getsize(input_file) if os.path.exists(input_file) else "Fichier non trouvé",
        "date_traitement": datetime.now().isoformat(),
        "structure": {},
        "arborescence": []
    }
    
    def format_value(value, level=0):
        """Formate une valeur pour l'affichage dans l'arborescence"""
        indent = "    " * level
        if isinstance(value, dict):
            lines = [f"{indent}{{"]
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{indent}    \"{k}\": {format_value(v, level+1)}")
                else:
                    v_str = f'"{v}"' if isinstance(v, str) else str(v)
                    if len(v_str) > 50:  # Tronquer les valeurs longues
                        v_str = f'"{str(v)[:47]}..."'
                    lines.append(f"{indent}    \"{k}\": {v_str}")
            lines.append(f"{indent}}}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            if len(value) > 5:  # Limiter le nombre d'éléments à afficher
                sample = value[:5]
                lines = [f"{indent}["]
                for item in sample:
                    lines.append(f"{indent}    {format_value(item, level+1)},")
                lines.append(f"{indent}    ... {len(value)-5} éléments supplémentaires")
                lines.append(f"{indent}]")
                return "\n".join(lines)
            else:
                lines = [f"{indent}["]
                for item in value:
                    lines.append(f"{indent}    {format_value(item, level+1)},")
                lines.append(f"{indent}]")
                return "\n".join(lines)
        else:
            return f'"{value}"' if isinstance(value, str) else str(value)
    
    def extract_json_structure(json_data, max_depth=3, current_depth=0):
        """Extrait récursivement la structure d'un objet JSON"""
        if current_depth >= max_depth:
            return "..."  # Arrêter la récursion à max_depth
        
        if isinstance(json_data, dict):
            result = {}
            for key, value in json_data.items():
                if isinstance(value, (dict, list)):
                    result[key] = extract_json_structure(value, max_depth, current_depth + 1)
                else:
                    # Pour les valeurs simples, juste indiquer le type
                    result[key] = f"<{type(value).__name__}>"
            return result
        elif isinstance(json_data, list):
            if not json_data:
                return []
            # Pour les listes, prendre juste quelques exemples
            sample = json_data[:min(3, len(json_data))]
            result = [extract_json_structure(item, max_depth, current_depth + 1) for item in sample]
            if len(json_data) > 3:
                result.append(f"... {len(json_data)-3} éléments supplémentaires")
            return result
        else:
            return f"<{type(json_data).__name__}>"
    
    try:
        if os.path.exists(input_file):
            with open(input_file, 'r', encoding='utf-8') as f:
                try:
                    # Essayer d'abord avec json standard
                    sample_content = f.read(50000)  # Lire un échantillon
                    
                    # Si le fichier est trop grand, ne lire qu'un échantillon
                    if os.path.getsize(input_file) > 50000:
                        sample_content += "..."  # Indiquer que c'est tronqué
                    
                    # Nettoyer le contenu pour éviter les erreurs courantes
                    clean_content = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', sample_content)
                    clean_content = re.sub(r'(?<!\\)"(?![:,}\] ])', r'\"', clean_content)
                    
                    try:
                        # Essayer de parser le JSON nettoyé
                        sample = json.loads(clean_content)
                    except json.JSONDecodeError:
                        # Si ça échoue, essayer de lire ligne par ligne pour trouver un objet complet
                        f.seek(0)
                        bracket_count = 0
                        brace_count = 0
                        json_content = ""
                        
                        for i, line in enumerate(f):
                            if i > 1000:  # Limiter le nombre de lignes lues
                                break
                            
                            json_content += line
                            bracket_count += line.count('[') - line.count(']')
                            brace_count += line.count('{') - line.count('}')
                            
                            # Si on trouve un objet ou tableau complet, arrêter
                            if (bracket_count == 0 and brace_count == 0) and (']' in line or '}' in line):
                                break
                        
                        # Essayer de parser ce qu'on a lu
                        try:
                            sample = json.loads(json_content)
                        except json.JSONDecodeError:
                            # En dernier recours, essayer de réparer le JSON
                            try:
                                # Fixer les problèmes courants
                                fixed_content = remove_trailing_commas(json_content)
                                fixed_content = re.sub(r'(?<!\\)"(?![:,}\] ])', r'\"', fixed_content)
                                
                                # S'assurer que c'est un JSON valide
                                if not fixed_content.strip().startswith('{') and not fixed_content.strip().startswith('['):
                                    fixed_content = '[' + fixed_content
                                if not fixed_content.strip().endswith('}') and not fixed_content.strip().endswith(']'):
                                    fixed_content = fixed_content + ']'
                                
                                sample = json.loads(fixed_content)
                            except:
                                # Si tout échoue, abandonner
                                raise
                    
                    # Analyser la structure
                    if isinstance(sample, list):
                        file_structure["structure"]["type"] = "array"
                        file_structure["structure"]["nombre_elements"] = len(sample)
                        if sample:
                            first_item = sample[0]
                            if isinstance(first_item, dict):
                                file_structure["structure"]["schema_premier_element"] = list(first_item.keys())
                                # Extraire la structure détaillée
                                file_structure["structure"]["exemple_structure"] = extract_json_structure(first_item)
                            else:
                                file_structure["structure"]["type_elements"] = type(first_item).__name__
                        
                        # Générer l'arborescence textuelle
                        file_structure["arborescence"] = ["["]
                        if sample:
                            # Montrer le premier élément en détail
                            if isinstance(sample[0], dict):
                                formatted = format_value(sample[0]).split('\n')
                                file_structure["arborescence"].extend(["    " + line for line in formatted])
                            else:
                                file_structure["arborescence"].append(f"    {sample[0]}")
                            
                            # Indiquer combien d'éléments supplémentaires
                            if len(sample) > 1:
                                file_structure["arborescence"].append(f"    ... {len(sample)-1} éléments supplémentaires")
                        file_structure["arborescence"].append("]")
                            
                    elif isinstance(sample, dict):
                        file_structure["structure"]["type"] = "object"
                        file_structure["structure"]["cles_principales"] = list(sample.keys())
                        file_structure["structure"]["exemple_structure"] = extract_json_structure(sample)
                        
                        # Générer l'arborescence textuelle
                        formatted = format_value(sample).split('\n')
                        file_structure["arborescence"] = formatted
                except Exception as e:
                    file_structure["erreur_analyse"] = str(e)
                    file_structure["structure"]["type"] = "Inconnu - Erreur de parsing"
                    file_structure["arborescence"] = [f"Impossible de générer l'arborescence: {str(e)}"]
    except Exception as e:
        file_structure["erreur_analyse"] = str(e)
        file_structure["structure"]["type"] = "Inconnu - Erreur de lecture du fichier"
        file_structure["arborescence"] = [f"Impossible de générer l'arborescence: {str(e)}"]
    
    # Générer le fichier d'arborescence au format texte
    with open(os.path.join(output_dir, output_file), "w", encoding="utf-8") as f:
        f.write(f"Structure et contenu du fichier: {os.path.basename(input_file)}\n")
        f.write("="*50 + "\n\n")
        
        f.write(f"Nom: {file_structure['nom_fichier']}\n")
        f.write(f"Chemin: {file_structure['chemin_complet']}\n")
        f.write(f"Taille: {file_structure['taille']} octets\n")
        f.write(f"Date de traitement: {file_structure['date_traitement']}\n\n")
        
        f.write("Structure interne:\n")
        f.write("-----------------\n")
        if "structure" in file_structure:
            f.write(f"Type: {file_structure['structure'].get('type', 'Inconnu')}\n\n")
            
            if "nombre_elements" in file_structure["structure"]:
                f.write(f"Nombre d'éléments: {file_structure['structure']['nombre_elements']}\n")
            
            if "cles_principales" in file_structure["structure"]:
                f.write(f"Clés principales: {', '.join(file_structure['structure']['cles_principales'])}\n\n")
            
            if "schema_premier_element" in file_structure["structure"]:
                f.write(f"Schéma du premier élément: {', '.join(file_structure['structure']['schema_premier_element'])}\n\n")
        
        if "erreur_analyse" in file_structure:
            f.write(f"Erreur lors de l'analyse: {file_structure['erreur_analyse']}\n\n")
        
        f.write("Arborescence du contenu:\n")
        f.write("-----------------------\n")
        if "arborescence" in file_structure and file_structure["arborescence"]:
            f.write("\n".join(file_structure["arborescence"]))
        else:
            f.write("Impossible de générer l'arborescence du contenu")

if __name__ == "__main__":
    main() 