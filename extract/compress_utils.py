#!/usr/bin/env python3
"""
Utilitaires pour la compression et la minification des fichiers JSON
dans les résultats générés.
"""

import os
import sys
import zstandard as zstd
import orjson
import json as std_json
from pathlib import Path
from typing import Union, Dict, Any, Optional, Tuple, List

# Ajouter le chemin du parent au path pour trouver le module cli
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from cli.lang_utils import t, get_current_language
    TRANSLATIONS_LOADED = True
except ImportError:
    # Fallback si le module de traduction n'est pas disponible
    def t(key, category=None, lang=None):
        return key
    def get_current_language():
        return "fr"
    TRANSLATIONS_LOADED = False


def compress_json(data: Dict[Any, Any], output_path: Union[str, Path], 
                  compression_level: int = 19, minify: bool = True,
                  keep_original: bool = True) -> Tuple[bool, int, int]:
    """
    Compresse et minifie des données JSON avec zstd et orjson.
    
    Args:
        data: Données JSON à compresser
        output_path: Chemin du fichier à générer (base)
        compression_level: Niveau de compression zstd (1-22, défaut=19)
        minify: Si True, minifie le JSON avant compression
        keep_original: Si True, conserve également une version .json non compressée
    
    Returns:
        Tuple[bool, int, int]: (succès, taille originale, taille compressée)
    """
    try:
        # Définir les chemins de sortie
        original_path = output_path
        compressed_path = str(output_path) + '.zst'
        
        # Taille originale avec orjson
        if minify:
            json_bytes = orjson.dumps(
                data,
                option=orjson.OPT_SORT_KEYS | orjson.OPT_OMIT_MICROSECONDS
            )
        else:
            # Option pour une indentation lisible si minify=False
            json_bytes = orjson.dumps(
                data,
                option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
            )
        
        original_size = len(json_bytes)
        
        # Sauvegarder la version non compressée si demandé
        if keep_original:
            with open(original_path, 'wb') as f:
                f.write(json_bytes)
        
        # Compresser avec zstd
        compressor = zstd.ZstdCompressor(level=compression_level)
        compressed_data = compressor.compress(json_bytes)
        compressed_size = len(compressed_data)
        
        # Écrire le fichier compressé
        with open(compressed_path, 'wb') as f:
            f.write(compressed_data)
            
        return True, original_size, compressed_size
    except Exception as e:
        print(f"Erreur lors de la compression: {e}")
        return False, 0, 0


def decompress_json(input_path: Union[str, Path]) -> Optional[Dict[Any, Any]]:
    """
    Décompresse un fichier JSON compressé avec zstd.
    
    Args:
        input_path: Chemin du fichier compressé (.json.zst)
    
    Returns:
        Dict: Données JSON décompressées ou None en cas d'erreur
    """
    try:
        # Lire le fichier compressé
        with open(input_path, 'rb') as f:
            compressed_data = f.read()
        
        # Décompresser
        decompressor = zstd.ZstdDecompressor()
        json_bytes = decompressor.decompress(compressed_data)
        
        # Désérialiser avec orjson
        data = orjson.loads(json_bytes)
        
        return data
    except Exception as e:
        print(f"Erreur lors de la décompression: {e}")
        return None


def compress_results_directory(directory: Union[str, Path], 
                              compression_level: int = 19,
                              keep_originals: bool = True,
                              generate_report: bool = True) -> Tuple[int, Dict[str, List[Tuple[str, int, int, int]]]]:
    """
    Compresse tous les fichiers JSON dans un répertoire de résultats.
    
    Args:
        directory: Répertoire contenant les fichiers JSON à compresser
        compression_level: Niveau de compression zstd (1-22)
        keep_originals: Si True, conserve les fichiers originaux
        generate_report: Si True, génère un rapport de compression
    
    Returns:
        Tuple[int, Dict]: (Nombre de fichiers compressés, rapport de compression)
    """
    count = 0
    compression_report = {}
    
    for root, _, files in os.walk(directory):
        relative_dir = os.path.relpath(root, directory)
        compression_report[relative_dir] = []
        
        for file in files:
            if file.endswith('.json') and not file.endswith('.zst'):
                input_path = os.path.join(root, file)
                output_path = input_path  # Même chemin pour la version orjson
                
                try:
                    # Charger le JSON avec la bibliothèque standard
                    with open(input_path, 'r', encoding='utf-8') as f:
                        try:
                            data = std_json.load(f)
                        except std_json.JSONDecodeError:
                            print(f"⚠️ {t('invalid_json_file', 'compression')}: {input_path}, {t('skipped', 'compression')}")
                            continue
                    
                    # Obtenir la taille du fichier original
                    original_std_size = os.path.getsize(input_path)
                    
                    # Compresser avec orjson + zstd
                    success, orjson_size, compressed_size = compress_json(
                        data, output_path, compression_level, True, keep_originals
                    )
                    
                    if success:
                        count += 1
                        # Ajouter au rapport
                        compression_report[relative_dir].append((
                            file,
                            original_std_size,  # Taille standard JSON
                            orjson_size,        # Taille avec orjson
                            compressed_size     # Taille avec zstd
                        ))
                except Exception as e:
                    print(f"{t('error_processing', 'compression')} {input_path}: {e}")
    
    # Générer le rapport si demandé
    if generate_report:
        _generate_compression_report(directory, compression_report)
    
    return count, compression_report


def _generate_compression_report(directory: Union[str, Path], 
                                compression_data: Dict[str, List[Tuple[str, int, int, int]]]) -> str:
    """
    Génère un rapport détaillé sur la compression des fichiers.
    
    Args:
        directory: Répertoire de base
        compression_data: Données de compression
    
    Returns:
        str: Chemin du rapport généré
    """
    # Déterminer la langue actuelle
    current_lang = get_current_language()
    
    # Titre du rapport selon la langue
    report_title = {
        "fr": "# Rapport de compression JSON (orjson + zstd)",
        "en": "# JSON Compression Report (orjson + zstd)"
    }.get(current_lang, "# Rapport de compression JSON (orjson + zstd)")
    
    # Textes traduits
    report_texts = {
        "fr": {
            "date": "Date",
            "directory": "Répertoire",
            "details_by_folder": "## Détails par dossier",
            "file": "Fichier",
            "standard_json": "JSON standard",
            "gain_orjson": "Gain orjson",
            "gain_zstd": "Gain zstd",
            "total_gain": "Gain total",
            "global_summary": "## Résumé Global",
            "files_processed": "Fichiers traités",
            "total_original_size": "Taille totale originale",
            "size_with_orjson": "Taille avec orjson",
            "size_with_orjsonzstd": "Taille avec orjson+zstd",
            "gain": "gain",
            "observations": "## Observations",
            "orjson_optimizes": "**orjson** optimise la sérialisation JSON et élimine les espaces non nécessaires",
            "zstd_applies": "**zstd** applique une compression avancée préservant l'accès rapide aux données",
            "jsonzst_require": "Les fichiers `.json.zst` nécessitent une décompression avant utilisation",
            "avg_compression": "La compression moyenne constatée réduit l'espace disque de"
        },
        "en": {
            "date": "Date",
            "directory": "Directory",
            "details_by_folder": "## Details by folder",
            "file": "File",
            "standard_json": "Standard JSON",
            "gain_orjson": "orjson gain",
            "gain_zstd": "zstd gain",
            "total_gain": "Total gain",
            "global_summary": "## Global Summary",
            "files_processed": "Files processed",
            "total_original_size": "Total original size",
            "size_with_orjson": "Size with orjson",
            "size_with_orjsonzstd": "Size with orjson+zstd",
            "gain": "gain",
            "observations": "## Observations",
            "orjson_optimizes": "**orjson** optimizes JSON serialization and eliminates unnecessary spaces",
            "zstd_applies": "**zstd** applies advanced compression while preserving fast data access",
            "jsonzst_require": "`.json.zst` files require decompression before use",
            "avg_compression": "The average compression reduces disk space by"
        }
    }
    
    # Utiliser les textes traduits ou les textes en français par défaut
    txt = report_texts.get(current_lang, report_texts["fr"])
    
    report_path = os.path.join(directory, f"compression_report_{current_lang}.txt")
    
    total_original = 0
    total_orjson = 0
    total_compressed = 0
    total_files = 0
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"{report_title}\n\n")
        f.write(f"{txt['date']}: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{txt['directory']}: {directory}\n\n")
        
        f.write(f"{txt['details_by_folder']}\n\n")
        
        for dir_path, files in compression_data.items():
            if not files:
                continue
                
            f.write(f"### {dir_path}\n\n")
            f.write(f"| {txt['file']} | {txt['standard_json']} | orjson | zstd | {txt['gain_orjson']} | {txt['gain_zstd']} | {txt['total_gain']} |\n")
            f.write("|---------|---------------|--------|------|-------------|-----------|------------|\n")
            
            for file_data in files:
                filename, std_size, orjson_size, zstd_size = file_data
                total_original += std_size
                total_orjson += orjson_size
                total_compressed += zstd_size
                total_files += 1
                
                # Calculer les gains
                orjson_gain_pct = ((std_size - orjson_size) / std_size) * 100 if std_size > 0 else 0
                zstd_gain_pct = ((orjson_size - zstd_size) / orjson_size) * 100 if orjson_size > 0 else 0
                total_gain_pct = ((std_size - zstd_size) / std_size) * 100 if std_size > 0 else 0
                
                f.write(f"| {filename} | {_format_size(std_size)} | {_format_size(orjson_size)} | "
                       f"{_format_size(zstd_size)} | {orjson_gain_pct:.1f}% | {zstd_gain_pct:.1f}% | "
                       f"{total_gain_pct:.1f}% |\n")
            
            f.write("\n")
        
        # Résumé global
        f.write(f"{txt['global_summary']}\n\n")
        
        total_orjson_gain = ((total_original - total_orjson) / total_original) * 100 if total_original > 0 else 0
        total_zstd_gain = ((total_orjson - total_compressed) / total_orjson) * 100 if total_orjson > 0 else 0
        total_gain = ((total_original - total_compressed) / total_original) * 100 if total_original > 0 else 0
        
        f.write(f"- **{txt['files_processed']}**: {total_files}\n")
        f.write(f"- **{txt['total_original_size']}**: {_format_size(total_original)}\n")
        f.write(f"- **{txt['size_with_orjson']}**: {_format_size(total_orjson)} ({txt['gain']}: {total_orjson_gain:.1f}%)\n")
        f.write(f"- **{txt['size_with_orjsonzstd']}**: {_format_size(total_compressed)} ({txt['gain']}: {total_gain:.1f}%)\n\n")
        
        f.write(f"{txt['observations']}\n\n")
        f.write(f"- {txt['orjson_optimizes']}\n")
        f.write(f"- {txt['zstd_applies']}\n")
        f.write(f"- {txt['jsonzst_require']}\n")
        f.write(f"- {txt['avg_compression']} ")
        f.write(f"**{total_gain:.1f}%** {t('compared_to_standard', 'compression')}\n")
    
    return report_path


def _format_size(size_bytes: int) -> str:
    """Formate une taille en bytes en format lisible."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"


if __name__ == "__main__":
    """
    Utilisation en ligne de commande pour compresser un répertoire de résultats.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description=t('compress_minify_desc', 'compression'))
    parser.add_argument('--directory', '-d', required=True, help=t('directory_help', 'compression'))
    parser.add_argument('--level', '-l', type=int, default=19, help=t('compression_level_help', 'compression'))
    parser.add_argument('--keep-originals', '-k', action='store_true', default=True, 
                       help=t('keep_originals_help', 'compression'))
    parser.add_argument('--language', '-lang', default=None, 
                       help=t('language_help', 'compression'))
    
    args = parser.parse_args()
    
    # Définir la langue si spécifiée
    if args.language and TRANSLATIONS_LOADED:
        from cli.lang_utils import set_language
        set_language(args.language)
    
    print(f"{t('compressing_files', 'compression')} {args.directory}...")
    count, _ = compress_results_directory(args.directory, args.level, args.keep_originals)
    print(f"✅ {count} {t('files_compressed_success', 'compression')}!")
    current_lang = get_current_language()
    report_path = os.path.join(args.directory, f"compression_report_{current_lang}.txt")
    print(f"   {t('report_available', 'compression')}: {report_path}") 