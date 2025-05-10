#!/usr/bin/env python3
"""
CLI interactive pour le traitement de fichiers JSON
avec options pour l'analyse automatique, la détection de type,
et l'intégration optionnelle avec un LLM.
"""

import os
import sys
import json
import glob
import dotenv
import time
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import inquirer
from openai import OpenAI
from rich.markdown import Markdown
from rich.rule import Rule
from extract.image_describer import PDFImageDescriber

# Importer le module de gestion des langues
try:
    from cli.lang_utils import t, set_language, get_current_language
    TRANSLATIONS_LOADED = True
except ImportError:
    # Fallback si le module de traduction n'est pas disponible
    def t(key, category=None, lang=None):
        return key
    def set_language(lang):
        pass
    def get_current_language():
        return "fr"
    TRANSLATIONS_LOADED = False

# Charger les variables d'environnement
dotenv.load_dotenv()

# Ajout du répertoire parent au chemin de recherche Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import des modules personnalisés du projet
try:
    from extract.generic_json_processor import GenericJsonProcessor
    from extract.extract_jira_structure import extract_structure_from_first_object as extract_jira_structure
    from extract.extract_confluence_structure import extract_structure_from_first_object as extract_confluence_structure
    from extract.match_jira_confluence import find_matches, update_with_matches
    from extract.robust_json_parser import robust_json_parser, JsonParsingException
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Vérifiez que tous les modules requis sont installés et que la structure du projet est correcte.")
    sys.exit(1)

# Import du nouveau module Outlines (avec gestion d'erreur si non installé)
try:
    from extract.outlines_enhanced_parser import outlines_robust_json_parser
    from extract.outlines_extractor import process_jira_data, process_confluence_data
    OUTLINES_AVAILABLE = True
except ImportError:
    print("Module Outlines non disponible. Fonctionnalités d'extraction avancées désactivées.")
    OUTLINES_AVAILABLE = False

# Ajouter l'import pour le résumé LLM
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extract"))
    from extract.llm_summary import generate_llm_summary
except ImportError:
    try:
        from llm_summary import generate_llm_summary
    except ImportError:
        generate_llm_summary = None
        print("⚠️ Module llm_summary non trouvé, la génération de résumés LLM est désactivée")

# Initialisation de Typer et Rich
app = typer.Typer(help="JSON Processor pour Llamendex")
console = Console()

# Constantes
DEFAULT_MAPPINGS_DIR = os.environ.get("MAPPINGS_DIR", "extract/mapping_examples")
DEFAULT_OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
LLM_MODELS = os.environ.get("LLM_MODELS", "gpt-4.1,gpt-3.5-turbo,o3,gpt-4").split(",")
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")

# --- HEADER/LOGO ---
def print_header():
    logo = (
        "[bold magenta]"
        "BBBBB   L       AAAAA   III  K   K  EEEEE\n"
        "B    B  L      A     A  I   K  K   E\n"
        "BBBBB   L      AAAAAAA  I   KKK    EEEE\n"
        "B    B  L      A     A  I   K  K   E\n"
        "BBBBB   LLLLL  A     A III  K   K  EEEEE\n"
        "[/bold magenta]"
    )
    console.print(logo)
    console.print("[bold cyan]J S O N    P A R S E R    C L I[/bold cyan] [green]v1.0[/green] 🚀\n")
    
    # Afficher la langue actuelle
    if TRANSLATIONS_LOADED:
        current_lang = get_current_language()
        lang_display = "Français" if current_lang == "fr" else "English"
        console.print(f"[dim]Language/Langue: {lang_display}[/dim]\n")

# --- STEPPER ---
def print_stepper(current:int, total:int, steps:list):
    stepper = ""
    for i, step in enumerate(steps, 1):
        if i < current:
            stepper += f"[green]●[/green] "
        elif i == current:
            stepper += f"[bold yellow]➤ {step}[/bold yellow] "
        else:
            stepper += f"[grey]○ {step}[/grey] "
        if i < total:
            stepper += "[grey]→[/grey] "
    console.print(stepper)

# --- NAVIGATION AVEC ICONES ---
def _prompt_for_file(message: str, allow_validate: bool = False) -> Optional[str]:
    current_dir = os.getcwd()
    
    # Vérifier si le dossier "files" existe à la racine du projet
    files_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "files")
    
    while True:
        console.print(f"\n[bold]{t('current_directory', 'messages')}[/bold] {current_dir}")
        items = os.listdir(current_dir)
        files = [f for f in items if os.path.isfile(os.path.join(current_dir, f)) and f.endswith('.json')]
        dirs = [d for d in items if os.path.isdir(os.path.join(current_dir, d))]
        
        # Trier les dossiers et les fichiers
        dirs.sort()
        files.sort()
        
        choices = []
        
        # Option pour remonter au dossier parent si nous ne sommes pas à la racine
        if current_dir != os.path.dirname(current_dir):
            choices.append(t("parent_dir", "options"))
        
        # Mettre le dossier "files" en premier si nous sommes à la racine du projet
        if os.path.exists(files_dir) and os.path.dirname(files_dir) == current_dir:
            dirs.remove("files")
            choices.append(f"{t('dir_prefix', 'options')} files")
        
        # Ajouter les autres dossiers
        choices += [f"{t('dir_prefix', 'options')} {d}" for d in dirs]
        
        # Ajouter les fichiers JSON
        choices += [f"{t('file_prefix', 'options')} {f}" for f in files]
        
        # Si nous ne sommes pas dans le dossier "files", proposer d'y aller directement
        if os.path.exists(files_dir) and current_dir != files_dir:
            choices.insert(1, t("go_to_files", "options"))
        
        # Ajouter les options de validation/annulation
        if allow_validate:
            choices.append(t("validate", "options"))
        choices.append(t("enter_manually", "options"))
        choices.append(t("cancel", "options"))
        
        # Poser la question
        questions = [
            inquirer.List('path',
                         message=message,
                         choices=choices,
                         carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if answers is None or not answers['path']:
                return None
                
            choice = answers['path']
            
            # Traiter le choix
            if choice == t("cancel", "options"):
                console.print(f"[italic]{t('operation_cancelled', 'messages')}[/italic]")
                return None
                
            elif choice == t("parent_dir", "options"):
                current_dir = os.path.dirname(current_dir)
                os.chdir(current_dir)
                
            elif choice == t("go_to_files", "options"):
                if os.path.exists(files_dir):
                    current_dir = files_dir
                    os.chdir(current_dir)
                else:
                    console.print("[bold red]Le dossier 'files' n'existe pas.[/bold red]")
                    
            elif choice == t("enter_manually", "options"):
                # Demander un chemin manuellement
                manual_path = inquirer.prompt([
                    inquirer.Text('path',
                                 message=t("manual_path", "prompts"))
                ])
                
                if manual_path and manual_path['path']:
                    path = os.path.expanduser(manual_path['path'])
                    if os.path.exists(path) and (os.path.isdir(path) or (os.path.isfile(path) and path.endswith('.json'))):
                        if os.path.isdir(path):
                            current_dir = path
                            os.chdir(current_dir)
                        else:
                            return path
                    else:
                        console.print(f"[bold red]{t('invalid_path', 'messages')}[/bold red]")
                        
            elif choice == t("validate", "options"):
                return "__VALIDATE__"
                
            elif choice.startswith(t("dir_prefix", "options").split(' ')[0]):
                # Changer de dossier
                folder = choice.split(' ', 2)[-1]
                new_dir = os.path.join(current_dir, folder)
                if os.path.isdir(new_dir):
                    current_dir = new_dir
                    os.chdir(current_dir)
                    
            elif choice.startswith(t("file_prefix", "options").split(' ')[0]):
                # Sélectionner un fichier
                file = choice.split(' ', 2)[-1]
                file_path = os.path.join(current_dir, file)
                if os.path.isfile(file_path) and file_path.endswith('.json'):
                    return file_path
                else:
                    console.print(f"[bold red]{t('invalid_path', 'messages')}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Erreur lors de la sélection du fichier: {e}[/bold red]")
            return None

# --- FEEDBACK/RESUME ---
def print_success(msg:str):
    console.print(f"[bold green]✅ {msg}[/bold green]")
def print_error(msg:str):
    console.print(f"[bold red]❌ {msg}[/bold red]")
def print_info(msg:str):
    console.print(f"[bold blue]ℹ️  {msg}[/bold blue]")
def print_warning(msg:str):
    console.print(f"[bold yellow]⚠️  {msg}[/bold yellow]")

def ensure_dir(directory: str):
    """Assure que le répertoire existe, le crée si nécessaire."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def find_mapping_files() -> List[str]:
    """Trouve tous les fichiers de mapping disponibles dans le répertoire par défaut."""
    mapping_pattern = os.path.join(DEFAULT_MAPPINGS_DIR, "*.json")
    return [os.path.basename(f) for f in glob.glob(mapping_pattern)]

def detect_file_type(file_path: str) -> dict:
    """
    Détecte le type de fichier JSON (JIRA ou Confluence)
    """
    try:
        # Extraire la structure JIRA
        jira_structure = extract_jira_structure(file_path)
        
        # Vérifier si c'est un fichier JIRA
        if not jira_structure.get("error") and jira_structure.get("structure"):
            keys = jira_structure["structure"].get("keys", [])
            if any(key in keys for key in ["key", "summary", "issuetype", "status"]):
                return {"type": "jira", "structure": jira_structure["structure"]}
        
        # Extraire la structure Confluence
        confluence_structure = extract_confluence_structure(file_path)
        
        # Vérifier si c'est un fichier Confluence
        if not confluence_structure.get("error") and confluence_structure.get("structure"):
            keys = confluence_structure["structure"].get("keys", [])
            if any(key in keys for key in ["title", "space", "body", "content"]):
                return {"type": "confluence", "structure": confluence_structure["structure"]}
        
        # Type inconnu
        return {"type": "unknown", "message": "Type de fichier non reconnu"}
    
    except Exception as e:
        return {"type": "error", "message": str(e)}

def process_with_llm(content: Dict[str, Any], model: str = None, api_key: str = None) -> Dict[str, Any]:
    """
    Enrichit les données avec l'analyse LLM.
    
    Args:
        content: Contenu JSON déjà traité
        model: Modèle LLM à utiliser
        api_key: Clé API pour le LLM
        
    Returns:
        Contenu enrichi avec l'analyse LLM
    """
    try:
        # Utiliser les variables d'environnement si non spécifiées
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        model = model or os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")
        
        if not api_key:
            console.print("[bold red]Erreur: Clé API OpenAI manquante. Définissez la variable d'environnement OPENAI_API_KEY ou utilisez l'option --api-key.[/bold red]")
            return content
            
        client = OpenAI(api_key=api_key)
        
        # Si contenu contient des éléments (tickets, pages, etc.)
        if "items" in content and content["items"]:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(f"[cyan]Analyse LLM avec {model}...", total=len(content["items"]))
                
                for item in content["items"]:
                    # Extraire le contenu textuel pour l'analyse
                    text_content = ""
                    if "content" in item:
                        if isinstance(item["content"], dict):
                            for k, v in item["content"].items():
                                if isinstance(v, str):
                                    text_content += v + "\n"
                        elif isinstance(item["content"], str):
                            text_content = item["content"]
                    
                    # Si nous avons du texte à analyser
                    if text_content:
                        prompt = f"""
                        Analyse le contenu suivant et fournis :
                        1. Une liste de mots-clés pertinents (max 7)
                        2. Une classification du type de contenu
                        3. Un résumé de 2-3 phrases
                        
                        Contenu à analyser :
                        {text_content[:1500]}  # Limiter pour rester dans les limites de tokens
                        
                        Format de réponse (JSON) :
                        {{
                            "keywords": ["mot1", "mot2", ...],
                            "content_type": "type de contenu",
                            "summary": "résumé concis"
                        }}
                        """
                        
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "Tu es un assistant spécialisé dans l'analyse de données textuelles."},
                                {"role": "user", "content": prompt}
                            ],
                            response_format={"type": "json_object"}
                        )
                        
                        try:
                            llm_analysis = json.loads(response.choices[0].message.content)
                            
                            # Ajouter l'analyse au contenu
                            if "analysis" not in item:
                                item["analysis"] = {}
                            
                            item["analysis"]["llm"] = llm_analysis
                            
                            # Ajouter ou fusionner les mots-clés
                            if "keywords" in llm_analysis:
                                if "keywords" not in item["analysis"]:
                                    item["analysis"]["keywords"] = []
                                # Éviter les doublons
                                for kw in llm_analysis["keywords"]:
                                    if kw not in item["analysis"]["keywords"]:
                                        item["analysis"]["keywords"].append(kw)
                        except json.JSONDecodeError:
                            # Fallback si le format JSON est incorrect
                            if "analysis" not in item:
                                item["analysis"] = {}
                            item["analysis"]["llm_raw"] = response.choices[0].message.content
                    
                    progress.update(task, advance=1)
        
        return content
    
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'analyse LLM: {e}[/bold red]")
        return content

@app.command()
def process(
    input_file: str = typer.Argument(..., help="Fichier JSON à traiter"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Fichier de sortie (par défaut: {input}_processed.json)"),
    mapping_file: Optional[str] = typer.Option(None, "--mapping", "-m", help="Fichier de mapping à utiliser"),
    detect: bool = typer.Option(True, "--detect/--no-detect", help="Détecter automatiquement le type de fichier"),
    auto_mapping: bool = typer.Option(True, "--auto-mapping/--no-auto-mapping", help="Utiliser le mapping correspondant au type détecté"),
    use_llm: bool = typer.Option(True, "--llm/--no-llm", help="Utiliser un LLM pour l'enrichissement"),
    llm_model: str = typer.Option(None, "--model", help="Modèle LLM à utiliser"),
    preserve_source: bool = typer.Option(True, "--preserve-source/--overwrite-source", help="Préserver les fichiers sources originaux"),
):
    """Traiter un fichier JSON selon son type détecté."""
    console = Console()
    
    # 1. Vérifier que le fichier existe
    if not os.path.exists(input_file):
        console.print(f"[bold red]Le fichier {input_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # 2. Vérifier que le fichier est un JSON valide
    try:
        from tools import validate_file
        is_valid, error_msg = validate_file(input_file)
        if not is_valid:
            console.print(f"[bold red]Le fichier JSON n'est pas valide: {error_msg}[/bold red]")
            
            # Proposer de réparer le fichier
            if typer.confirm("Voulez-vous essayer de réparer le fichier?"):
                try:
                    from tools import repair_json_files
                    repaired_file = input_file + ".repaired"
                    if repair_json_files(input_file, repaired_file):
                        console.print(f"[bold green]Fichier réparé et sauvegardé dans {repaired_file}[/bold green]")
                        input_file = repaired_file
                    else:
                        console.print("[bold red]Impossible de réparer le fichier.[/bold red]")
                        raise typer.Exit(1)
                except ImportError:
                    console.print("[bold yellow]Module tools non trouvé. Impossible de réparer le fichier.[/bold yellow]")
                    raise typer.Exit(1)
    except ImportError:
        console.print("[bold yellow]Module tools non trouvé. Vérification de validité ignorée.[/bold yellow]")
    
    # Générer un timestamp pour le nom du fichier
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Obtenir le chemin absolu vers le répertoire racine du projet
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Utiliser le dossier results comme base à la racine du projet
    base_results_dir = os.path.join(project_root, "results")
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Si pas de fichier de sortie spécifié, créer un nom par défaut avec timestamp dans le dossier results
    if not output_file:
        base, ext = os.path.splitext(os.path.basename(input_file))
        output_file = os.path.join(base_results_dir, f"{base}_processed_{timestamp}{ext}")
    elif not os.path.isabs(output_file) and not output_file.startswith(base_results_dir):
        # Si le chemin n'est pas absolu et ne commence pas par le dossier results,
        # placer le fichier dans le dossier results
        output_file = os.path.join(base_results_dir, output_file)
    
    # 2. Afficher les infos de départ
    console.print(Panel.fit(
        "[bold]Traitement de fichier JSON pour Llamendex[/bold]\n\n"
        f"Fichier d'entrée : [cyan]{input_file}[/cyan]\n"
        f"Fichier de sortie : [cyan]{output_file}[/cyan]\n"
        f"Préservation des sources : [cyan]{'Oui' if preserve_source else 'Non'}[/cyan]",
        title="JSON Processor",
        border_style="blue"
    ))
    
    # 3. Détection du type (optionnelle)
    file_type = None
    if detect:
        with console.status("[bold blue]Détection du type de fichier..."):
            file_type = detect_file_type(input_file)
        
        if file_type:
            console.print(f"Type détecté : [bold green]{file_type['type']}[/bold green]")
        else:
            console.print("[yellow]Type de fichier non détecté. Traitement générique sera utilisé.[/yellow]")
    
    # 4. Gestion du mapping (interactif ou automatique)
    if auto_mapping and file_type and not mapping_file:
        auto_mapping_file = os.path.join(DEFAULT_MAPPINGS_DIR, f"{file_type['type']}_mapping.json")
        if os.path.exists(auto_mapping_file):
            mapping_file = auto_mapping_file
            console.print(f"Utilisation automatique du mapping : [cyan]{mapping_file}[/cyan]")
    
    # 7. Traitement principal
    try:
        # Charger le mapping si spécifié
        field_mappings = None
        if mapping_file and os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    field_mappings = json.load(f)
                console.print(f"Mapping chargé depuis [cyan]{mapping_file}[/cyan]")
            except Exception as e:
                console.print(f"[bold red]Erreur lors du chargement du mapping: {e}[/bold red]")
        
        # Créer le processeur
        processor = GenericJsonProcessor(
            field_mappings=field_mappings,
            detect_fields=detect,
            extract_keywords=True,
            use_llm_fallback=use_llm,
            llm_model=llm_model,
            preserve_source=preserve_source
        )
        
        # Traiter le fichier
        result = processor.process_file(input_file, output_file)
        
        if result:
            console.print(f"[bold green]✅ Fichier traité avec succès: [cyan]{output_file}[/cyan][/bold green]")
            
            # Générer un résumé LLM si l'option est activée et que des données sont disponibles
            if use_llm:
                try:
                    # Charger les données enrichies
                    with open(output_file, 'r', encoding='utf-8') as f:
                        processed_data = json.load(f)
                    
                    # Déterminer le répertoire de sortie à partir du fichier de sortie
                    output_dir = os.path.dirname(output_file)
                    if not output_dir:
                        output_dir = "."
                    
                    # Générer le résumé LLM
                    llm_summary_file = generate_llm_summary(
                        output_dir, 
                        data=processed_data, 
                        filename=f"{os.path.splitext(os.path.basename(output_file))[0]}_llm_summary.md"
                    )
                    console.print(f"[bold green]✅ Résumé LLM généré: [cyan]{llm_summary_file}[/cyan][/bold green]")
                except Exception as e:
                    console.print(f"[bold yellow]⚠️ Impossible de générer le résumé LLM: {e}[/bold yellow]")
            
            return True
        else:
            console.print("[bold red]❌ Erreur lors du traitement du fichier[/bold red]")
            return False
    except Exception as e:
        console.print(f"[bold red]❌ Erreur: {e}[/bold red]")
        return False


def show_summary(file_path: str):
    """Affiche un résumé du fichier traité avec des statistiques."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Créer un tableau de statistiques
        table = Table(title="Résumé du traitement")
        
        table.add_column("Métrique", style="cyan")
        table.add_column("Valeur", style="green")
        
        # Nombre d'éléments
        items_count = len(data.get("items", []))
        table.add_row("Éléments traités", str(items_count))
        
        # Source
        if "metadata" in data and "source_file" in data["metadata"]:
            table.add_row("Fichier source", data["metadata"]["source_file"])
        
        # Date de traitement
        if "metadata" in data and "processed_at" in data["metadata"]:
            table.add_row("Date de traitement", data["metadata"]["processed_at"])
        
        # Statistiques
        if "metadata" in data and "stats" in data["metadata"]:
            for key, value in data["metadata"]["stats"].items():
                table.add_row(key.replace("_", " ").capitalize(), str(value))
        
        # Premier élément en exemple (si présent)
        if items_count > 0:
            first_item = data["items"][0]
            
            # ID et titre
            if "id" in first_item:
                table.add_row("Premier élément ID", str(first_item["id"]))
            if "title" in first_item:
                title = first_item["title"]
                if len(title) > 50:
                    title = title[:47] + "..."
                table.add_row("Premier élément titre", title)
        
        console.print(table)
        
        # Afficher un aperçu du fichier JSON
        console.print("\n[bold]Aperçu du JSON généré:[/bold]")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Limiter à un extrait raisonnable
            content_preview = content[:5000] + ("\n..." if len(content) > 5000 else "")
            syntax = Syntax(content_preview, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        
        console.print(f"\nFichier de sortie : [bold cyan]{file_path}[/bold cyan]")
        console.print("\n[bold green]Traitement terminé avec succès ![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'affichage du résumé: {e}[/bold red]")


@app.command()
def match(
    jira_file: str = typer.Argument(..., help="Fichier JSON de tickets JIRA traités"),
    confluence_file: str = typer.Argument(..., help="Fichier JSON de pages Confluence traitées"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie"),
    min_score: float = typer.Option(None, "--min-score", "-s", help="Score minimum pour les correspondances"),
    llm_assist: bool = typer.Option(False, "--llm-assist", help="Utiliser un LLM pour améliorer les correspondances"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API pour le LLM (ou variable d'environnement OPENAI_API_KEY)"),
    llm_model: str = typer.Option(None, "--model", help="Modèle LLM à utiliser"),
    compress: bool = typer.Option(False, "--compress", help="Compresser les fichiers de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux en plus des compressés"),
):
    """
    Établit des correspondances entre tickets JIRA et pages Confluence.
    """
    # Générer un timestamp pour le nom du dossier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Obtenir le chemin absolu vers le répertoire racine du projet
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Utiliser le dossier results comme base à la racine du projet
    base_results_dir = os.path.join(project_root, "results")
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Si output_dir est spécifié, l'utiliser comme nom de dossier avec le timestamp
    if output_dir:
        output_dir = os.path.join(base_results_dir, f"{output_dir}_{timestamp}")
    else:
        # Créer un nom à partir des noms de fichiers
        jira_name = os.path.splitext(os.path.basename(jira_file))[0]
        confluence_name = os.path.splitext(os.path.basename(confluence_file))[0]
        output_dir = os.path.join(base_results_dir, f"matches_{jira_name}_{confluence_name}_{timestamp}")
    
    # Valeur par défaut pour min_score
    min_score = min_score or float(os.environ.get("MIN_MATCH_SCORE", "0.2"))
    
    # Vérifier que les fichiers existent
    if not os.path.exists(jira_file):
        console.print(f"[bold red]Le fichier JIRA {jira_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    if not os.path.exists(confluence_file):
        console.print(f"[bold red]Le fichier Confluence {confluence_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Créer le répertoire de sortie
    ensure_dir(output_dir)
    
    # Définir les chemins de sortie
    matches_file = os.path.join(output_dir, "jira_confluence_matches.json")
    jira_with_matches_file = os.path.join(output_dir, "jira_with_matches.json")
    confluence_with_matches_file = os.path.join(output_dir, "confluence_with_matches.json")
    
    # Afficher les infos
    console.print(Panel.fit(
        f"[bold]Matching JIRA ↔ Confluence[/bold]\n\n"
        f"JIRA : [cyan]{jira_file}[/cyan]\n"
        f"Confluence : [cyan]{confluence_file}[/cyan]\n"
        f"Score minimum : [cyan]{min_score}[/cyan]",
        title="Matching",
        border_style="blue"
    ))
    
    # Construire le chemin vers le script match_jira_confluence.py
    match_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "extract", "match_jira_confluence.py")
    
    # Exécuter le script de matching
    cmd = [
        sys.executable, match_script,
        "--jira", jira_file,
        "--confluence", confluence_file,
        "--output", matches_file,
        "--updated-jira", jira_with_matches_file,
        "--updated-confluence", confluence_with_matches_file,
        "--min-score", str(min_score)
    ]
    
    with console.status("[bold blue]Matching en cours..."):
        from subprocess import run, PIPE
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    
    if result.returncode != 0:
        console.print("[bold red]Erreur lors du matching:[/bold red]")
        console.print(result.stderr)
        raise typer.Exit(1)
    
    # Afficher les résultats
    console.print(result.stdout)
    
    # LLM pour améliorer les correspondances si demandé
    if llm_assist:
        # Utiliser les valeurs par défaut si non spécifiées
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not llm_model:
            llm_model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")
            
        if not api_key:
            console.print("[bold yellow]Pas de clé API OpenAI trouvée. L'assistance LLM ne sera pas effectuée.[/bold yellow]")
            llm_assist = False
        
        if llm_assist:
            console.print("[bold]Amélioration des correspondances avec LLM...[/bold]")
            
            # TODO: Implémenter l'amélioration des correspondances avec LLM
            # Cela pourrait inclure:
            # 1. Analyse des correspondances de faible score pour confirmer/infirmer
            # 2. Recherche de correspondances supplémentaires basées sur la sémantique
            # 3. Suggestion de nouveaux liens qui n'ont pas été détectés automatiquement
            
            console.print("[bold yellow]Assistance LLM pour les correspondances non implémentée.[/bold yellow]")
    
    # Afficher un résumé
    try:
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        table = Table(title="Résumé des correspondances")
        table.add_column("Métrique", style="cyan")
        table.add_column("Valeur", style="green")
        
        # Nombre de tickets avec correspondances
        total_tickets = len(matches)
        table.add_row("Tickets avec correspondances", str(total_tickets))
        
        # Nombre total de correspondances
        total_matches = sum(len(matches[ticket_id]) for ticket_id in matches)
        table.add_row("Correspondances totales", str(total_matches))
        
        # Moyenne de correspondances par ticket
        avg_matches = total_matches / total_tickets if total_tickets > 0 else 0
        table.add_row("Moyenne par ticket", f"{avg_matches:.2f}")
        
        console.print(table)
        
        console.print(f"\nFichiers générés dans : [bold cyan]{output_dir}[/bold cyan]")
        console.print("\n[bold green]Matching terminé avec succès ![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'affichage du résumé: {e}[/bold red]")


@app.command()
def unified(
    jira_files: List[str] = typer.Argument(..., help="Fichiers JSON JIRA à traiter"),
    confluence_files: List[str] = typer.Option([], "--confluence", "-c", help="Fichiers JSON Confluence à traiter"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie"),
    min_match_score: float = typer.Option(None, "--min-score", "-s", help="Score minimum pour les correspondances"),
    max_items: Optional[int] = typer.Option(None, "--max", help="Nombre maximum d'éléments à traiter par fichier"),
    use_llm: bool = typer.Option(True, "--llm/--no-llm", help="Utiliser un LLM pour l'enrichissement"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API OpenAI (si non définie dans les variables d'environnement)"),
    skip_matching: bool = typer.Option(False, "--skip-matching", help="Ne pas effectuer le matching entre JIRA et Confluence"),
    language: Optional[str] = typer.Option(None, "--lang", help="Langue à utiliser (fr/en)"),
    compress: bool = typer.Option(False, "--compress", help="Compresser les fichiers de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux en plus des compressés")
):
    """
    Traitement unifié JIRA + Confluence.
    Cette commande exécute le flux complet : extraction, division, transformation, matching et analyse LLM.
    """
    # Configuration des chemins
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Vérifier si le répertoire de sortie est spécifié
    output_dir_str = str(output_dir) if output_dir else "output_unified"
    
    # Préparer le chemin complet du répertoire de sortie
    # Utiliser le dossier results comme base, à moins que le chemin soit absolu
    if os.path.isabs(output_dir_str):
        full_output_dir = output_dir_str
    else:
        # Utiliser le dossier results à la racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results_dir = os.path.join(project_root, "results")
        # S'assurer que le répertoire results existe
        os.makedirs(results_dir, exist_ok=True)
        full_output_dir = os.path.join(results_dir, output_dir_str)
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(full_output_dir, exist_ok=True)
    
    # Récupérer les valeurs par défaut des options
    min_score = float(str(min_match_score)) if min_match_score is not None else 0.5
    
    # Afficher un récapitulatif
    console.print(Panel(
        f"Traitement unifié JIRA + Confluence\n\n"
        f"Fichiers JIRA : {', '.join(jira_files)}\n"
        f"Fichiers Confluence : {', '.join(confluence_files)}\n"
        f"Répertoire de sortie : {full_output_dir}\n",
        title=t("unified_processing", "titles"),
        expand=True
    ))
    
    console.print(f"Exécution du flux unifié...")
    
    # S'assurer que la langue est configurée
    if language:
        language_str = str(language)
        # Ne pas afficher l'objet OptionInfo, juste la valeur
        console.print(f"🌐 Langue configurée: {language_str}")
    
    # Options pour run_unified_analysis.py
    cmd = [
        sys.executable,
        os.path.join(parent_dir, "extract", "run_unified_analysis.py"),
        "--jira-files"
    ] + jira_files
    
    if confluence_files:
        cmd.extend(["--confluence-files"] + confluence_files)
    
    cmd.extend([
        "--output-dir", str(full_output_dir),
        "--min-match-score", str(min_score)
    ])
    
    if max_items:
        cmd.extend(["--max-items", str(max_items)])
    
    if use_llm:
        cmd.append("--with-openai")
        if api_key:
            cmd.extend(["--api-key", str(api_key)])
    else:
        cmd.append("--no-openai")
    
    if skip_matching:
        cmd.append("--skip-matching")
    
    if language:
        cmd.extend(["--language", str(language)])
    
    # Ajouter les options de compression si demandées
    if compress:
        cmd.append("--compress")
        cmd.extend(["--compress-level", str(compress_level)])
        if not keep_originals:
            cmd.append("--no-originals")
    
    # Exécuter le script run_unified_analysis.py
    try:
        console.print("\n[bold cyan]Exécution du flux unifié...[/bold cyan]")
        process = subprocess.run(cmd, text=True, capture_output=True)
        
        if process.returncode == 0:
            console.print(process.stdout)
            
            # Corriger les éventuels problèmes de dossiers dupliqués
            try:
                # Importer le module tools
                from tools import fix_duplicate_paths
                
                # Appliquer la correction au répertoire de sortie
                moved_count = fix_duplicate_paths(full_output_dir)
                if moved_count > 0:
                    console.print(f"[yellow]⚠️ Correction de {moved_count} fichiers dans des chemins dupliqués[/yellow]")
            except ImportError:
                console.print("[yellow]Module tools non trouvé. Pas de correction de chemins dupliqués.[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Erreur lors de la correction des chemins: {str(e)}[/yellow]")
            
            print_success(f"Fichiers générés dans : {full_output_dir}")
            console.print(f"Arborescence globale générée dans : {os.path.join(full_output_dir, 'global_arborescence.txt')}")
            
            # Afficher des informations sur la compression si applicable
            if compress:
                current_lang = get_current_language()
                report_path = os.path.join(full_output_dir, f"compression_report_{current_lang}.txt")
                if os.path.exists(report_path):
                    console.print(f"[bold cyan]Rapport de compression généré dans : [/bold cyan]{report_path}")
            
            print_success("Traitement unifié terminé avec succès !")
        else:
            console.print(process.stdout)
            console.print(process.stderr)
            print_error("Le traitement a échoué. Consultez les messages d'erreur ci-dessus.")
            
    except Exception as e:
        print_error(f"Erreur lors de l'exécution du flux unifié: {str(e)}")
        return


@app.command()
def chunks(
    input_file: str = typer.Argument(..., help="Fichier JSON volumineux à découper"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie pour les morceaux"),
    items_per_file: int = typer.Option(500, "--items-per-file", "-n", help="Nombre d'éléments par fichier"),
    process_after: bool = typer.Option(False, "--process", "-p", help="Traiter chaque morceau après découpage"),
    mapping_file: Optional[str] = typer.Option(None, "--mapping", "-m", help="Fichier de mapping à utiliser pour le traitement"),
    use_llm: bool = typer.Option(False, "--llm", help="Utiliser un LLM pour l'enrichissement lors du traitement"),
    compress: bool = typer.Option(False, "--compress", help="Compresser les fichiers de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux en plus des compressés"),
):
    """
    Découpe un fichier JSON volumineux en morceaux plus petits et optionnellement les traite.
    
    Utilise process_by_chunks.py pour gérer efficacement les gros fichiers JSON.
    """
    # Valider les arguments
    if not os.path.exists(input_file):
        console.print(f"[bold red]Le fichier {input_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Générer un timestamp pour le nom du dossier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Obtenir le chemin absolu vers le répertoire racine du projet
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Utiliser le dossier results comme base à la racine du projet
    base_results_dir = os.path.join(project_root, "results")
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Si output_dir est spécifié, l'utiliser comme nom de dossier avec le timestamp
    if output_dir:
        output_dir = os.path.join(base_results_dir, f"{output_dir}_{timestamp}")
    else:
        # Utiliser le nom du fichier d'entrée comme nom de base pour le dossier de sortie
        file_base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.join(base_results_dir, f"chunks_{file_base_name}_{timestamp}")
    
    ensure_dir(output_dir)
    
    # Construire le chemin vers le script process_by_chunks.py
    chunks_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "extract", "process_by_chunks.py")
    
    console.print(Panel.fit(
        "[bold]Découpage de fichier JSON volumineux[/bold]\n\n"
        f"Fichier d'entrée : [cyan]{input_file}[/cyan]\n"
        f"Répertoire de sortie : [cyan]{output_dir}[/cyan]\n"
        f"Éléments par fichier : [cyan]{items_per_file}[/cyan]",
        title="Découpage en morceaux",
        border_style="blue"
    ))
    
    # Commande pour découper le fichier
    cmd = [
        sys.executable, chunks_script,
        "split",
        "--input", input_file,
        "--output-dir", output_dir,
        "--items-per-file", str(items_per_file)
    ]
    
    # Exécuter la commande
    with console.status("[bold blue]Découpage en cours..."):
        from subprocess import run, PIPE
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    
    if result.returncode != 0:
        console.print("[bold red]Erreur lors du découpage:[/bold red]")
        console.print(result.stderr)
        raise typer.Exit(1)
    
    console.print("[bold green]Découpage terminé avec succès ![/bold green]")
    
    # Afficher les fichiers générés
    chunk_files = glob.glob(os.path.join(output_dir, "*.json"))
    console.print(f"[bold]Nombre de morceaux créés:[/bold] {len(chunk_files)}")
    
    # Traiter chaque morceau si demandé
    if process_after and chunk_files:
        console.print("\n[bold]Traitement des morceaux...[/bold]")
        
        # Créer le répertoire pour les fichiers traités
        processed_dir = os.path.join(output_dir, "processed")
        ensure_dir(processed_dir)
        
        # Traiter chaque fichier
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[bold]{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Traitement des morceaux...", total=len(chunk_files))
            
            for chunk_file in chunk_files:
                chunk_name = os.path.basename(chunk_file)
                output_file = os.path.join(processed_dir, f"{os.path.splitext(chunk_name)[0]}_processed.json")
                
                # Construire la commande process
                process_args = {
                    "input_file": chunk_file,
                    "output_file": output_file,
                    "mapping_file": mapping_file,
                    "use_llm": use_llm
                }
                
                # Exécuter process() sur le morceau
                try:
                    process(**process_args)
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[yellow]Erreur lors du traitement de {chunk_name}: {e}[/yellow]")
                    progress.update(task, advance=1)
        
        console.print(f"\n[bold green]Traitement des morceaux terminé ![/bold green]")
        console.print(f"Fichiers traités disponibles dans : [bold cyan]{processed_dir}[/bold cyan]")


@app.command()
def interactive(
    language: str = typer.Option(None, "--lang", "-l", help="Langue de l'interface (fr/en)")
):
    """
    Mode entièrement interactif qui guide l'utilisateur à travers toutes les étapes.
    
    Ce mode permet de choisir le type d'opération à effectuer et guide
    l'utilisateur à travers toutes les options de manière conviviale.
    """
    if language:
        set_language(language)
        
    console.print(Panel.fit(
        t("interactive_content", "panels"),
        title=t("interactive_title", "panels"),
        border_style="green"
    ))
    
    # 1. Sélection du type d'opération
    operation_choices = [
        t("process", "interactive_choices"),
        t("chunks", "interactive_choices"),
        t("match", "interactive_choices"),
        t("unified", "interactive_choices"),
        t("clean", "interactive_choices"),
        t("compress", "interactive_choices"),
        t("describe_images", "interactive_choices"),
        # Ajouter l'option pour changer de langue
        f"🌐 {t('change_language', 'interactive_choices', 'fr')} / {t('change_language', 'interactive_choices', 'en')}",
        t("quit", "interactive_choices")
    ]
    
    questions = [
        inquirer.List('operation',
                     message=t("select_operation", "messages"),
                     choices=operation_choices)
    ]
    answers = inquirer.prompt(questions)
    
    if not answers:
        return
        
    selected_operation = answers['operation']
    
    # Vérifier si l'utilisateur veut changer de langue
    if "🌐" in selected_operation:
        current_lang = get_current_language()
        new_lang = "en" if current_lang == "fr" else "fr"
        
        console.print(f"[bold]Changing language to {new_lang}[/bold]" if new_lang == "en" else f"[bold]Changement de langue vers {new_lang}[/bold]")
        set_language(new_lang)
        
        # Relancer le menu avec la nouvelle langue explicitement spécifiée
        return interactive(language=new_lang)
    
    # Quitter si demandé
    if selected_operation == t("quit", "interactive_choices"):
        return
    
    # 2. Selon l'opération choisie, poser les questions appropriées
    if t("process", "interactive_choices") in selected_operation:
        _run_interactive_process()
    elif t("chunks", "interactive_choices") in selected_operation:
        _run_interactive_chunks()
    elif t("match", "interactive_choices") in selected_operation:
        _run_interactive_match()
    elif t("unified", "interactive_choices") in selected_operation:
        _run_interactive_unified()
    elif t("clean", "interactive_choices") in selected_operation:
        _run_interactive_clean()
    elif t("compress", "interactive_choices") in selected_operation:
        _run_interactive_compress()
    elif t("describe_images", "interactive_choices") in selected_operation:
        _run_interactive_describe_images()


def _run_interactive_process():
    """Interface interactive pour la commande process."""
    # Sélection du fichier d'entrée
    input_file = _prompt_for_file("Sélectionnez le fichier JSON à traiter:")
    if not input_file:
        return
    
    # Détection automatique du type
    file_type = detect_file_type(input_file)
    if file_type:
        console.print(f"Type détecté : [bold green]{file_type['type']}[/bold green]")
    
    # Demander le fichier de sortie
    default_output = f"{os.path.splitext(input_file)[0]}_processed.json"
    output_file = typer.prompt("Fichier de sortie", default=default_output)
    
    # Chercher les mappings disponibles
    mapping_choices = find_mapping_files()
    mapping_choices.insert(0, "Sans mapping (détection automatique)")
    mapping_choices.append("Créer un mapping personnalisé")
    
    # Sélection du mapping
    questions = [
        inquirer.List('mapping_choice',
                     message="Choisissez un mapping pour le traitement",
                     choices=mapping_choices,
                     default="Sans mapping (détection automatique)" if not file_type else f"{file_type['type']}_mapping.json" if f"{file_type['type']}_mapping.json" in mapping_choices else "Sans mapping (détection automatique)")
    ]
    answers = inquirer.prompt(questions)
    
    mapping_file = None
    if answers["mapping_choice"] == "Sans mapping (détection automatique)":
        mapping_file = None
    elif answers["mapping_choice"] == "Créer un mapping personnalisé":
        mapping_file = _create_custom_mapping()
    else:
        mapping_file = os.path.join(DEFAULT_MAPPINGS_DIR, answers["mapping_choice"])
    
    # Options avancées
    questions = [
        inquirer.Confirm('use_llm',
                        message="Voulez-vous enrichir avec LLM (OpenAI) ?",
                        default=False),
        inquirer.Text('max_items',
                     message="Nombre maximum d'éléments à traiter (vide = tous)",
                     default=""),
        inquirer.Confirm('preserve_source',
                         message="Préserver les fichiers sources originaux ?",
                         default=True)
    ]
    answers_advanced = inquirer.prompt(questions)
    
    use_llm = answers_advanced['use_llm']
    max_items = int(answers_advanced['max_items']) if answers_advanced['max_items'].strip() else None
    preserve_source = answers_advanced['preserve_source']
    
    # LLM si demandé
    llm_model = None
    api_key = None
    if use_llm:
        # Clé API
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = typer.prompt("Entrez votre clé API OpenAI", hide_input=True)
        
        # Modèle
        questions = [
            inquirer.List('llm_model',
                         message="Choisissez un modèle LLM",
                         choices=LLM_MODELS,
                         default="gpt-4.1")
        ]
        llm_answers = inquirer.prompt(questions)
        llm_model = llm_answers['llm_model']
    
    # Confirmation finale
    console.print("\n[bold]Récapitulatif :[/bold]")
    console.print(f"- Fichier d'entrée : [cyan]{input_file}[/cyan]")
    console.print(f"- Fichier de sortie : [cyan]{output_file}[/cyan]")
    console.print(f"- Mapping : [cyan]{mapping_file or 'Auto-détection'}[/cyan]")
    console.print(f"- Préservation des sources : [cyan]{'Oui' if preserve_source else 'Non'}[/cyan]")
    if use_llm:
        console.print(f"- Enrichissement LLM : [cyan]Oui ({llm_model})[/cyan]")
    if max_items:
        console.print(f"- Limite d'éléments : [cyan]{max_items}[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                        message="Lancer le traitement ?",
                        default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if not confirm or not confirm['confirm']:
        console.print("[yellow]Opération annulée.[/yellow]")
        return
    
    # Exécuter process avec les paramètres définis
    process(
        input_file=input_file,
        output_file=output_file,
        mapping_file=mapping_file,
        detect=True,
        auto_mapping=True,
        use_llm=use_llm,
        llm_model=llm_model,
        api_key=api_key,
        interactive=False,  # Déjà en mode interactif
        max_items=max_items,
        root_key="items",
        preserve_source=preserve_source,
        outlines=False
    )


def _run_interactive_chunks():
    """Interface interactive pour la commande chunks."""
    # Sélection du fichier d'entrée
    input_file = _prompt_for_file("Sélectionnez le fichier JSON volumineux à découper:")
    if not input_file:
        return
    
    # Répertoire de sortie
    default_output_dir = os.path.join(DEFAULT_OUTPUT_DIR, "chunks")
    output_dir = typer.prompt("Répertoire de sortie pour les morceaux", default=default_output_dir)
    
    # Options de découpage
    questions = [
        inquirer.Text('items_per_file',
                     message="Nombre d'éléments par fichier",
                     default="500"),
        inquirer.Confirm('process_after',
                        message="Traiter les morceaux après découpage ?",
                        default=False),
        inquirer.Confirm('compress',
                        message="Activer la compression des fichiers JSON ?",
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    items_per_file = int(answers['items_per_file'])
    process_after = answers['process_after']
    compress = answers['compress']
    
    # Options de compression si activée
    compress_level = 19  # Valeur par défaut
    keep_originals = True  # Valeur par défaut
    if compress:
        compression_questions = [
            inquirer.List('compress_level',
                          message=t("compression_level_prompt", "compression"),
                          choices=["15 (fast)", "19 (balanced)", "22 (max)"],
                          default="19 (balanced)"),
            inquirer.Confirm('keep_originals',
                             message=t("keep_originals_prompt", "compression"),
                             default=True)
        ]
        compression_answers = inquirer.prompt(compression_questions)
        compress_level = int(compression_answers['compress_level'].split(" ")[0])
        keep_originals = compression_answers['keep_originals']
    
    # Options de traitement si demandé
    mapping_file = None
    use_llm = False
    if process_after:
        # Mapping
        mapping_choices = find_mapping_files()
        mapping_choices.insert(0, "Sans mapping (détection automatique)")
        
        questions = [
            inquirer.List('mapping_choice',
                         message="Mapping pour le traitement des morceaux",
                         choices=mapping_choices),
            inquirer.Confirm('use_llm',
                            message="Enrichir avec LLM ?",
                            default=False)
        ]
        process_answers = inquirer.prompt(questions)
        
        if process_answers['mapping_choice'] != "Sans mapping (détection automatique)":
            mapping_file = os.path.join(DEFAULT_MAPPINGS_DIR, process_answers['mapping_choice'])
        
        use_llm = process_answers['use_llm']
    
    # Confirmation finale
    console.print("\n[bold]Récapitulatif :[/bold]")
    console.print(f"- Fichier d'entrée : [cyan]{input_file}[/cyan]")
    console.print(f"- Répertoire de sortie : [cyan]{output_dir}[/cyan]")
    console.print(f"- Éléments par fichier : [cyan]{items_per_file}[/cyan]")
    if process_after:
        console.print(f"- Traitement après découpage : [cyan]Oui[/cyan]")
        console.print(f"- Mapping : [cyan]{mapping_file or 'Auto-détection'}[/cyan]")
        console.print(f"- Enrichissement LLM : [cyan]{'Oui' if use_llm else 'Non'}[/cyan]")
    if compress:
        console.print(f"- Compression JSON : [cyan]Oui (niveau {compress_level}, conserver originaux: {t('yes', 'messages') if keep_originals else t('no', 'messages')})[/cyan]")
    else:
        console.print(f"- Compression JSON : [cyan]Non[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                        message="Lancer le découpage ?",
                        default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if not confirm or not confirm['confirm']:
        console.print("[yellow]Opération annulée.[/yellow]")
        return
    
    # Exécuter chunks avec les paramètres définis
    chunks(
        input_file=input_file,
        output_dir=output_dir,
        items_per_file=items_per_file,
        process_after=process_after,
        mapping_file=mapping_file,
        use_llm=use_llm,
        compress=compress,
        compress_level=compress_level if compress else None,
        keep_originals=keep_originals if compress else None
    )


def _create_custom_mapping() -> str:
    """Crée un fichier de mapping personnalisé."""
    temp_mapping_file = "temp_mapping.json"
    template = '''{
  "id": "key_field",
  "title": "title_field",
  "content": {
    "field": "content_field",
    "transform": "clean_text"
  },
  "metadata": {
    "created_by": "author_field",
    "created_at": "date_field"
  }
}'''
    with open(temp_mapping_file, 'w') as f:
        f.write(template)
    console.print("[bold]Créez votre mapping personnalisé dans l'éditeur.[/bold]")
    console.print("[yellow]Appuyez sur Entrée pour continuer après avoir sauvegardé et fermé l'éditeur.[/yellow]")
    # Ouvrir l'éditeur par défaut
    if sys.platform == 'win32':
        os.system(f'notepad {temp_mapping_file}')
    else:
        editor = os.environ.get('EDITOR', 'nano')
        os.system(f'{editor} {temp_mapping_file}')
    input("Appuyez sur Entrée pour continuer...")
    # Vérifier que le mapping est valide
    try:
        with open(temp_mapping_file, 'r') as f:
            json.load(f)
        return temp_mapping_file
    except json.JSONDecodeError:
        console.print("[bold red]Le mapping créé n'est pas un JSON valide.[/bold red]")
        return None


@app.command()
def clean(
    input_file: str = typer.Argument(..., help="Fichier ou dossier à nettoyer"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Fichier ou dossier de sortie"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Traiter récursivement les sous-dossiers"),
):
    """
    Nettoie les données sensibles (clés API, identifiants, etc.) des fichiers JSON.
    Utile pour préparer des données de test ou avant de commit des fichiers.
    """
    console = Console()
    
    # Vérifier que le chemin existe
    if not os.path.exists(input_file):
        console.print(f"[bold red]Le chemin {input_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Importer le module clean_sensitive_data
    try:
        from tools import clean_json_file
    except ImportError:
        console.print("[bold red]Module tools non trouvé. Installez-le avec pip install -e .[/bold red]")
        raise typer.Exit(1)
    
    # Afficher les infos
    console.print(Panel.fit(
        "[bold]Nettoyage des données sensibles[/bold]\n\n"
        f"Chemin d'entrée : [cyan]{input_file}[/cyan]\n"
        f"Chemin de sortie : [cyan]{output_file or 'Auto-généré'}[/cyan]\n"
        f"Récursif : [cyan]{'Oui' if recursive else 'Non'}[/cyan]",
        title="Nettoyage de données",
        border_style="blue"
    ))
    
    # Si le chemin est un fichier
    if os.path.isfile(input_file):
        # Obtenir le chemin absolu vers le répertoire racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Utiliser le dossier results comme base à la racine du projet
        base_results_dir = os.path.join(project_root, "results")
        os.makedirs(base_results_dir, exist_ok=True)
        
        # Fichier unique
        if output_file:
            if not os.path.isabs(output_file):
                # Si le chemin n'est pas absolu, le placer dans results
                out_file = os.path.join(base_results_dir, output_file)
            else:
                out_file = output_file
        else:
            # Créer un nom par défaut dans le dossier results
            base, ext = os.path.splitext(os.path.basename(input_file))
            out_file = os.path.join(base_results_dir, f"{base}_clean{ext}")
        
        with console.status(f"[bold blue]Nettoyage de {input_file}..."):
            result = clean_json_file(input_file, out_file)
        
        if result:
            console.print(f"[bold green]✅ Fichier nettoyé: {out_file}[/bold green]")
        else:
            console.print(f"[bold red]❌ Échec du nettoyage de {input_file}[/bold red]")
            
    # Si le chemin est un répertoire
    elif os.path.isdir(input_file):
        # Obtenir le chemin absolu vers le répertoire racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Utiliser le dossier results comme base à la racine du projet
        base_results_dir = os.path.join(project_root, "results")
        os.makedirs(base_results_dir, exist_ok=True)
        
        # Répertoire
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if output_file:
            if not os.path.isabs(output_file):
                # Si le chemin n'est pas absolu, le placer dans results
                out_dir = os.path.join(base_results_dir, output_file)
            else:
                out_dir = output_file
        else:
            # Créer un nom par défaut dans le dossier results
            base = os.path.basename(input_file)
            out_dir = os.path.join(base_results_dir, f"{base}_cleaned_{timestamp}")
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(out_dir, exist_ok=True)
        
        # Trouver tous les fichiers JSON
        if recursive:
            json_files = glob.glob(os.path.join(input_file, "**", "*.json"), recursive=True)
        else:
            json_files = glob.glob(os.path.join(input_file, "*.json"))
        
        if not json_files:
            console.print(f"[bold yellow]Aucun fichier JSON trouvé dans {input_file}[/bold yellow]")
            return
        
        # Traiter chaque fichier
        success_count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[bold]{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Nettoyage des fichiers...", total=len(json_files))
            
            for file_path in json_files:
                # Calculer le chemin relatif au dossier d'entrée
                rel_path = os.path.relpath(file_path, input_file)
                # Construire le chemin dans le dossier de sortie
                out_file_dir = os.path.dirname(os.path.join(out_dir, rel_path))
                os.makedirs(out_file_dir, exist_ok=True)
                out_file = os.path.join(out_dir, f"{os.path.splitext(rel_path)[0]}_clean{os.path.splitext(rel_path)[1]}")
                
                # Nettoyer le fichier
                result = clean_json_file(file_path, out_file)
                if result:
                    success_count += 1
                    
                progress.update(task, advance=1)
        
        console.print(f"[bold green]✅ Nettoyage terminé: {success_count}/{len(json_files)} fichiers nettoyés.[/bold green]")
        console.print(f"Fichiers nettoyés disponibles dans : [bold cyan]{out_dir}[/bold cyan]")


def _run_interactive_clean():
    """Interface interactive pour la commande clean."""
    # Sélection du fichier ou dossier d'entrée
    input_path = _prompt_for_file(t("select_file_clean", "prompts"))
    if not input_path:
        return
    
    # Options
    questions = [
        inquirer.Confirm('recursive',
                         message=t("recursive", "confirmations"),
                         default=True),
        inquirer.Text('output',
                      message=t("output_clean", "prompts"),
                      default="")
    ]
    answers = inquirer.prompt(questions)
    
    recursive = answers['recursive'] if os.path.isdir(input_path) else False
    output = answers['output'] if answers['output'].strip() else None
    
    # Confirmation
    console.print(f"\n[bold]{t('summary', 'messages')}[/bold]")
    console.print(f"- {t('input_path', 'messages')} [cyan]{input_path}[/cyan]")
    console.print(f"- {t('output_path', 'messages')} [cyan]{output or t('auto_detection', 'messages')}[/cyan]")
    if os.path.isdir(input_path):
        console.print(f"- {t('recursive', 'messages')} [cyan]{t('yes', 'messages') if recursive else t('no', 'messages')}[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                         message=t("launch_cleaning", "confirmations"),
                         default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if confirm and confirm['confirm']:
        clean(input_path, output, recursive)


@app.command()
def compress(
    directory: str = typer.Argument(..., help="Répertoire ou fichier JSON à compresser/optimiser"),
    compress_level: int = typer.Option(19, "--level", "-l", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux"),
    language: str = typer.Option(None, "--lang", help="Langue pour le rapport (fr/en)"),
):
    """
    Compresse et optimise des fichiers JSON avec zstd et orjson.
    Réduit considérablement la taille des fichiers et améliore les performances de lecture/écriture.
    """
    console = Console()
    
    # Vérifier que le chemin existe
    if not os.path.exists(directory):
        console.print(f"[bold red]Le chemin {directory} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Définir la langue si spécifiée
    if language and TRANSLATIONS_LOADED:
        set_language(language)
    
    # Importer le module de compression
    try:
        from extract.compress_utils import compress_results_directory
    except ImportError:
        console.print("[bold red]Module de compression non disponible. Installation des dépendances...[/bold red]")
        subprocess.run([sys.executable, "-m", "pip", "install", "zstandard", "orjson"], check=True)
        try:
            from extract.compress_utils import compress_results_directory
        except ImportError:
            console.print("[bold red]Impossible d'importer le module de compression.[/bold red]")
            raise typer.Exit(1)
    
    # Afficher les infos
    console.print(Panel.fit(
        f"[bold]{t('compress_minify_desc', 'compression')}[/bold]\n\n"
        f"{t('directory_help', 'compression')} : [cyan]{directory}[/cyan]\n"
        f"{t('compression_level_help', 'compression')} : [cyan]{compress_level}[/cyan]\n"
        f"{t('keep_originals_help', 'compression')} : [cyan]{t('yes', 'messages') if keep_originals else t('no', 'messages')}[/cyan]",
        title=t("compression", "interactive_choices"),
        border_style="blue"
    ))
    
    # Compresser les fichiers
    with console.status(f"[bold blue]{t('compressing_files', 'compression')} {directory}..."):
        try:
            count, report = compress_results_directory(
                directory, 
                compression_level=compress_level,
                keep_originals=keep_originals,
                generate_report=True
            )
        except Exception as e:
            console.print(f"[bold red]Erreur lors de la compression: {e}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            raise typer.Exit(1)
    
    # Afficher les résultats
    current_lang = get_current_language()
    report_path = os.path.join(directory, f"compression_report_{current_lang}.txt")
    
    console.print(f"[bold green]✅ {count} {t('files_compressed_success', 'compression')}![/bold green]")
    console.print(f"[bold]{t('report_available', 'compression')}:[/bold] {report_path}")
    
    # Si le rapport existe, afficher un résumé
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
            
            # Extraire juste le résumé global
            summary_section = ""
            in_summary = False
            for line in report_content.split('\n'):
                if line.startswith("## Global Summary") or line.startswith("## Résumé Global"):
                    in_summary = True
                    summary_section += line + "\n"
                elif in_summary and line.startswith("##"):
                    in_summary = False
                elif in_summary:
                    summary_section += line + "\n"
            
            # Afficher le résumé
            console.print("\n[bold cyan]Résumé de compression:[/bold cyan]")
            console.print(Markdown(summary_section))


def _run_interactive_compress():
    """Interface interactive pour la commande compress."""
    # Sélection du répertoire ou fichier à compresser
    directory = _prompt_for_file(t("select_dir_compress", "prompts"))
    if not directory:
        return
    
    # Options de compression
    questions = [
        inquirer.List('compress_level',
                      message=t("compression_level_prompt", "compression"),
                      choices=["15 (fast)", "19 (balanced)", "22 (max)"],
                      default="19 (balanced)"),
        inquirer.Confirm('keep_originals',
                         message=t("keep_originals_prompt", "compression"),
                         default=True)
    ]
    answers = inquirer.prompt(questions)
    
    # Extraire le niveau de compression
    compress_level = int(answers['compress_level'].split(" ")[0])
    keep_originals = answers['keep_originals']
    
    # Confirmation
    console.print(f"\n[bold]{t('summary', 'messages')}[/bold]")
    console.print(f"- {t('directory_help', 'compression')} : [cyan]{directory}[/cyan]")
    console.print(f"- {t('compression_level_help', 'compression')} : [cyan]{compress_level}[/cyan]")
    console.print(f"- {t('keep_originals_help', 'compression')} : [cyan]{t('yes', 'messages') if keep_originals else t('no', 'messages')}[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                         message=t("launch_compression", "confirmations"),
                         default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if confirm and confirm['confirm']:
        # Exécuter la compression
        compress(directory, compress_level, keep_originals)


@app.command()
def match(
    jira_file: str = typer.Argument(..., help="Fichier JSON de tickets JIRA traités"),
    confluence_file: str = typer.Argument(..., help="Fichier JSON de pages Confluence traitées"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie"),
    min_score: float = typer.Option(None, "--min-score", "-s", help="Score minimum pour les correspondances"),
    llm_assist: bool = typer.Option(False, "--llm-assist", help="Utiliser un LLM pour améliorer les correspondances"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API pour le LLM (ou variable d'environnement OPENAI_API_KEY)"),
    llm_model: str = typer.Option(None, "--model", help="Modèle LLM à utiliser"),
    compress: bool = typer.Option(False, "--compress", help="Compresser les fichiers de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux en plus des compressés"),
):
    """
    Établit des correspondances entre tickets JIRA et pages Confluence.
    """
    # Générer un timestamp pour le nom du dossier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Obtenir le chemin absolu vers le répertoire racine du projet
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Utiliser le dossier results comme base à la racine du projet
    base_results_dir = os.path.join(project_root, "results")
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Si output_dir est spécifié, l'utiliser comme nom de dossier avec le timestamp
    if output_dir:
        output_dir = os.path.join(base_results_dir, f"{output_dir}_{timestamp}")
    else:
        # Créer un nom à partir des noms de fichiers
        jira_name = os.path.splitext(os.path.basename(jira_file))[0]
        confluence_name = os.path.splitext(os.path.basename(confluence_file))[0]
        output_dir = os.path.join(base_results_dir, f"matches_{jira_name}_{confluence_name}_{timestamp}")
    
    # Valeur par défaut pour min_score
    min_score = min_score or float(os.environ.get("MIN_MATCH_SCORE", "0.2"))
    
    # Vérifier que les fichiers existent
    if not os.path.exists(jira_file):
        console.print(f"[bold red]Le fichier JIRA {jira_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    if not os.path.exists(confluence_file):
        console.print(f"[bold red]Le fichier Confluence {confluence_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Créer le répertoire de sortie
    ensure_dir(output_dir)
    
    # Définir les chemins de sortie
    matches_file = os.path.join(output_dir, "jira_confluence_matches.json")
    jira_with_matches_file = os.path.join(output_dir, "jira_with_matches.json")
    confluence_with_matches_file = os.path.join(output_dir, "confluence_with_matches.json")
    
    # Afficher les infos
    console.print(Panel.fit(
        f"[bold]Matching JIRA ↔ Confluence[/bold]\n\n"
        f"JIRA : [cyan]{jira_file}[/cyan]\n"
        f"Confluence : [cyan]{confluence_file}[/cyan]\n"
        f"Score minimum : [cyan]{min_score}[/cyan]",
        title="Matching",
        border_style="blue"
    ))
    
    # Construire le chemin vers le script match_jira_confluence.py
    match_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "extract", "match_jira_confluence.py")
    
    # Exécuter le script de matching
    cmd = [
        sys.executable, match_script,
        "--jira", jira_file,
        "--confluence", confluence_file,
        "--output", matches_file,
        "--updated-jira", jira_with_matches_file,
        "--updated-confluence", confluence_with_matches_file,
        "--min-score", str(min_score)
    ]
    
    with console.status("[bold blue]Matching en cours..."):
        from subprocess import run, PIPE
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    
    if result.returncode != 0:
        console.print("[bold red]Erreur lors du matching:[/bold red]")
        console.print(result.stderr)
        raise typer.Exit(1)
    
    # Afficher les résultats
    console.print(result.stdout)
    
    # LLM pour améliorer les correspondances si demandé
    if llm_assist:
        # Utiliser les valeurs par défaut si non spécifiées
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not llm_model:
            llm_model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")
            
        if not api_key:
            console.print("[bold yellow]Pas de clé API OpenAI trouvée. L'assistance LLM ne sera pas effectuée.[/bold yellow]")
            llm_assist = False
        
        if llm_assist:
            console.print("[bold]Amélioration des correspondances avec LLM...[/bold]")
            
            # TODO: Implémenter l'amélioration des correspondances avec LLM
            # Cela pourrait inclure:
            # 1. Analyse des correspondances de faible score pour confirmer/infirmer
            # 2. Recherche de correspondances supplémentaires basées sur la sémantique
            # 3. Suggestion de nouveaux liens qui n'ont pas été détectés automatiquement
            
            console.print("[bold yellow]Assistance LLM pour les correspondances non implémentée.[/bold yellow]")
    
    # Afficher un résumé
    try:
        with open(matches_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        table = Table(title="Résumé des correspondances")
        table.add_column("Métrique", style="cyan")
        table.add_column("Valeur", style="green")
        
        # Nombre de tickets avec correspondances
        total_tickets = len(matches)
        table.add_row("Tickets avec correspondances", str(total_tickets))
        
        # Nombre total de correspondances
        total_matches = sum(len(matches[ticket_id]) for ticket_id in matches)
        table.add_row("Correspondances totales", str(total_matches))
        
        # Moyenne de correspondances par ticket
        avg_matches = total_matches / total_tickets if total_tickets > 0 else 0
        table.add_row("Moyenne par ticket", f"{avg_matches:.2f}")
        
        console.print(table)
        
        console.print(f"\nFichiers générés dans : [bold cyan]{output_dir}[/bold cyan]")
        console.print("\n[bold green]Matching terminé avec succès ![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'affichage du résumé: {e}[/bold red]")


@app.command()
def unified(
    jira_files: List[str] = typer.Argument(..., help="Fichiers JSON JIRA à traiter"),
    confluence_files: List[str] = typer.Option([], "--confluence", "-c", help="Fichiers JSON Confluence à traiter"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie"),
    min_match_score: float = typer.Option(None, "--min-score", "-s", help="Score minimum pour les correspondances"),
    max_items: Optional[int] = typer.Option(None, "--max", help="Nombre maximum d'éléments à traiter par fichier"),
    use_llm: bool = typer.Option(True, "--llm/--no-llm", help="Utiliser un LLM pour l'enrichissement"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API OpenAI (si non définie dans les variables d'environnement)"),
    skip_matching: bool = typer.Option(False, "--skip-matching", help="Ne pas effectuer le matching entre JIRA et Confluence"),
    language: Optional[str] = typer.Option(None, "--lang", help="Langue à utiliser (fr/en)"),
    compress: bool = typer.Option(False, "--compress", help="Compresser les fichiers de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver les fichiers JSON originaux en plus des compressés")
):
    """
    Traitement unifié JIRA + Confluence.
    Cette commande exécute le flux complet : extraction, division, transformation, matching et analyse LLM.
    """
    # Configuration des chemins
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Vérifier si le répertoire de sortie est spécifié
    output_dir_str = str(output_dir) if output_dir else "output_unified"
    
    # Préparer le chemin complet du répertoire de sortie
    # Utiliser le dossier results comme base, à moins que le chemin soit absolu
    if os.path.isabs(output_dir_str):
        full_output_dir = output_dir_str
    else:
        # Utiliser le dossier results à la racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results_dir = os.path.join(project_root, "results")
        # S'assurer que le répertoire results existe
        os.makedirs(results_dir, exist_ok=True)
        full_output_dir = os.path.join(results_dir, output_dir_str)
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(full_output_dir, exist_ok=True)
    
    # Récupérer les valeurs par défaut des options
    min_score = float(str(min_match_score)) if min_match_score is not None else 0.5
    
    # Afficher un récapitulatif
    console.print(Panel(
        f"Traitement unifié JIRA + Confluence\n\n"
        f"Fichiers JIRA : {', '.join(jira_files)}\n"
        f"Fichiers Confluence : {', '.join(confluence_files)}\n"
        f"Répertoire de sortie : {full_output_dir}\n",
        title=t("unified_processing", "titles"),
        expand=True
    ))
    
    console.print(f"Exécution du flux unifié...")
    
    # S'assurer que la langue est configurée
    if language:
        language_str = str(language)
        # Ne pas afficher l'objet OptionInfo, juste la valeur
        console.print(f"🌐 Langue configurée: {language_str}")
    
    # Options pour run_unified_analysis.py
    cmd = [
        sys.executable,
        os.path.join(parent_dir, "extract", "run_unified_analysis.py"),
        "--jira-files"
    ] + jira_files
    
    if confluence_files:
        cmd.extend(["--confluence-files"] + confluence_files)
    
    cmd.extend([
        "--output-dir", str(full_output_dir),
        "--min-match-score", str(min_score)
    ])
    
    if max_items:
        cmd.extend(["--max-items", str(max_items)])
    
    if use_llm:
        cmd.append("--with-openai")
        if api_key:
            cmd.extend(["--api-key", str(api_key)])
    else:
        cmd.append("--no-openai")
    
    if skip_matching:
        cmd.append("--skip-matching")
    
    if language:
        cmd.extend(["--language", str(language)])
    
    # Ajouter les options de compression si demandées
    if compress:
        cmd.append("--compress")
        cmd.extend(["--compress-level", str(compress_level)])
        if not keep_originals:
            cmd.append("--no-originals")
    
    # Exécuter le script run_unified_analysis.py
    try:
        console.print("\n[bold cyan]Exécution du flux unifié...[/bold cyan]")
        process = subprocess.run(cmd, text=True, capture_output=True)
        
        if process.returncode == 0:
            console.print(process.stdout)
            
            # Corriger les éventuels problèmes de dossiers dupliqués
            try:
                # Importer le module tools
                from tools import fix_duplicate_paths
                
                # Appliquer la correction au répertoire de sortie
                moved_count = fix_duplicate_paths(full_output_dir)
                if moved_count > 0:
                    console.print(f"[yellow]⚠️ Correction de {moved_count} fichiers dans des chemins dupliqués[/yellow]")
            except ImportError:
                console.print("[yellow]Module tools non trouvé. Pas de correction de chemins dupliqués.[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Erreur lors de la correction des chemins: {str(e)}[/yellow]")
            
            print_success(f"Fichiers générés dans : {full_output_dir}")
            console.print(f"Arborescence globale générée dans : {os.path.join(full_output_dir, 'global_arborescence.txt')}")
            
            # Afficher des informations sur la compression si applicable
            if compress:
                current_lang = get_current_language()
                report_path = os.path.join(full_output_dir, f"compression_report_{current_lang}.txt")
                if os.path.exists(report_path):
                    console.print(f"[bold cyan]Rapport de compression généré dans : [/bold cyan]{report_path}")
            
            print_success("Traitement unifié terminé avec succès !")
        else:
            console.print(process.stdout)
            console.print(process.stderr)
            print_error("Le traitement a échoué. Consultez les messages d'erreur ci-dessus.")
            
    except Exception as e:
        print_error(f"Erreur lors de l'exécution du flux unifié: {str(e)}")
        return


# Ajouter un nouveau décorateur app.callback pour gérer l'option de langue globale
@app.callback()
def main(
    language: str = typer.Option(None, "--lang", "-l", help="Langue de l'interface (fr/en)")
):
    """
    JSON Processor pour Llamendex - Outil d'analyse et de transformation de fichiers JSON.
    """
    if language:
        set_language(language)


def _run_interactive_match():
    """Interface interactive pour la commande match."""
    # Sélection des fichiers
    console.print("[bold]Sélection des fichiers JIRA et Confluence[/bold]")
    
    jira_file = _prompt_for_file("Sélectionnez le fichier JIRA traité:")
    if not jira_file:
        return
    
    confluence_file = _prompt_for_file("Sélectionnez le fichier Confluence traité:")
    if not confluence_file:
        return
    
    # Répertoire de sortie
    default_output_dir = os.environ.get("MATCH_OUTPUT_DIR", "output_matches")
    output_dir = typer.prompt("Répertoire de sortie", default=default_output_dir)
    
    # Options de matching
    questions = [
        inquirer.Text('min_score',
                     message="Score minimum pour les correspondances (0.0-1.0)",
                     default="0.2"),
        inquirer.Confirm('llm_assist',
                        message="Utiliser un LLM pour améliorer les correspondances ?",
                        default=False),
        inquirer.Confirm('compress',
                        message="Activer la compression des fichiers JSON ?",
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    min_score = float(answers['min_score'])
    llm_assist = answers['llm_assist']
    compress = answers['compress']
    
    # Options de compression si activée
    compress_level = 19  # Valeur par défaut
    keep_originals = True  # Valeur par défaut
    if compress:
        compression_questions = [
            inquirer.List('compress_level',
                          message=t("compression_level_prompt", "compression"),
                          choices=["15 (fast)", "19 (balanced)", "22 (max)"],
                          default="19 (balanced)"),
            inquirer.Confirm('keep_originals',
                             message=t("keep_originals_prompt", "compression"),
                             default=True)
        ]
        compression_answers = inquirer.prompt(compression_questions)
        compress_level = int(compression_answers['compress_level'].split(" ")[0])
        keep_originals = compression_answers['keep_originals']
    
    # Options LLM si demandées
    llm_model = None
    api_key = None
    if llm_assist:
        # Clé API
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = typer.prompt("Entrez votre clé API OpenAI", hide_input=True)
        
        # Modèle
        questions = [
            inquirer.List('llm_model',
                         message="Choisissez un modèle LLM",
                         choices=LLM_MODELS,
                         default="gpt-4.1")
        ]
        llm_answers = inquirer.prompt(questions)
        llm_model = llm_answers['llm_model']
    
    # Confirmation finale
    console.print("\n[bold]Récapitulatif :[/bold]")
    console.print(f"- Fichier JIRA : [cyan]{jira_file}[/cyan]")
    console.print(f"- Fichier Confluence : [cyan]{confluence_file}[/cyan]")
    console.print(f"- Répertoire de sortie : [cyan]{output_dir}[/cyan]")
    console.print(f"- Score minimum : [cyan]{min_score}[/cyan]")
    if llm_assist:
        console.print(f"- Assistance LLM : [cyan]Oui ({llm_model})[/cyan]")
    if compress:
        console.print(f"- Compression JSON : [cyan]Oui (niveau {compress_level}, conserver originaux: {t('yes', 'messages') if keep_originals else t('no', 'messages')})[/cyan]")
    else:
        console.print(f"- Compression JSON : [cyan]Non[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                        message="Lancer le matching ?",
                        default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if not confirm or not confirm['confirm']:
        console.print("[yellow]Opération annulée.[/yellow]")
        return
    
    # Exécuter match avec les paramètres définis
    match(
        jira_file=jira_file,
        confluence_file=confluence_file,
        output_dir=output_dir,
        min_score=min_score,
        llm_assist=llm_assist,
        api_key=api_key,
        llm_model=llm_model,
        compress=compress,
        compress_level=compress_level if compress else None,
        keep_originals=keep_originals if compress else None
    )


def _run_interactive_unified():
    """Interface interactive pour la commande unified."""
    console.print("[bold]Flux complet: JIRA + Confluence + Matching[/bold]")
    
    # Sélection des fichiers JIRA (multiples)
    jira_files = []
    while True:
        jira_file = _prompt_for_file(f"Sélectionnez un fichier JIRA ({len(jira_files)} sélectionnés, [Valider la sélection] pour terminer):", allow_validate=True)
        if not jira_file or jira_file == "__VALIDATE__":
            break
        jira_files.append(jira_file)
        console.print(f"Fichier ajouté : [cyan]{jira_file}[/cyan]")
    
    if not jira_files:
        console.print("[yellow]Aucun fichier JIRA sélectionné. Opération annulée.[/yellow]")
        return
    
    # Sélection des fichiers Confluence (facultatif)
    confluence_files = []
    questions = [
        inquirer.Confirm('add_confluence', message="Ajouter des fichiers Confluence ?", default=True)
    ]
    add_conf = inquirer.prompt(questions)
    if add_conf and add_conf['add_confluence']:
        while True:
            confluence_file = _prompt_for_file(f"Sélectionnez un fichier Confluence ({len(confluence_files)} sélectionnés, [Valider la sélection] pour terminer):", allow_validate=True)
            if not confluence_file or confluence_file == "__VALIDATE__":
                break
            confluence_files.append(confluence_file)
            console.print(f"Fichier ajouté : [cyan]{confluence_file}[/cyan]")
    
    # Répertoire de sortie - Utiliser un input simple plutôt que typer.prompt pour éviter les problèmes d'objets OptionInfo
    default_output_dir = os.environ.get("UNIFIED_OUTPUT_DIR", "output_unified")
    output_dir_str = input(f"Répertoire de sortie [{default_output_dir}]: ").strip()
    output_dir_str = output_dir_str if output_dir_str else default_output_dir
    
    # Options avancées
    questions = [
        inquirer.Text('min_match_score',
                     message="Score minimum pour les correspondances (0.0-1.0)",
                     default="0.2"),
        inquirer.Text('max_items',
                     message="Nombre maximum d'éléments à traiter par fichier (vide = tous)",
                     default=""),
        inquirer.Confirm('use_llm',
                        message="Utiliser un LLM pour l'enrichissement ?",
                        default=False),
        inquirer.Confirm('skip_matching',
                        message="Ignorer le matching entre JIRA et Confluence ?",
                        default=False),
        inquirer.Confirm('compress',
                        message="Activer la compression des fichiers JSON ?",
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    min_match_score = float(answers['min_match_score'])
    max_items = int(answers['max_items']) if answers['max_items'].strip() else None
    use_llm = answers['use_llm']
    skip_matching = answers['skip_matching']
    compress = answers['compress']
    
    # Options de compression si activée
    compress_level = 19  # Valeur par défaut
    keep_originals = True  # Valeur par défaut
    if compress:
        compression_questions = [
            inquirer.List('compress_level',
                          message=t("compression_level_prompt", "compression"),
                          choices=["15 (fast)", "19 (balanced)", "22 (max)"],
                          default="19 (balanced)"),
            inquirer.Confirm('keep_originals',
                             message=t("keep_originals_prompt", "compression"),
                             default=True)
        ]
        compression_answers = inquirer.prompt(compression_questions)
        compress_level = int(compression_answers['compress_level'].split(" ")[0])
        keep_originals = compression_answers['keep_originals']
    
    # Options LLM si demandées
    api_key = None
    if use_llm:
        # Clé API
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = input("Entrez votre clé API OpenAI: ").strip()
    
    # Confirmation finale
    console.print("\n[bold]Récapitulatif :[/bold]")
    console.print(f"- Fichiers JIRA : [cyan]{', '.join(jira_files)}[/cyan]")
    if confluence_files:
        console.print(f"- Fichiers Confluence : [cyan]{', '.join(confluence_files)}[/cyan]")
    console.print(f"- Répertoire de sortie : [cyan]{output_dir_str}[/cyan]")
    console.print(f"- Score minimum : [cyan]{min_match_score}[/cyan]")
    if max_items:
        console.print(f"- Limite d'éléments : [cyan]{max_items}[/cyan]")
    console.print(f"- Enrichissement LLM : [cyan]{'Oui' if use_llm else 'Non'}[/cyan]")
    console.print(f"- Ignorer matching : [cyan]{'Oui' if skip_matching else 'Non'}[/cyan]")
    if compress:
        console.print(f"- Compression JSON : [cyan]Oui (niveau {compress_level}, conserver originaux: {t('yes', 'messages') if keep_originals else t('no', 'messages')})[/cyan]")
    else:
        console.print(f"- Compression JSON : [cyan]Non[/cyan]")
    
    questions = [
        inquirer.Confirm('confirm',
                        message="Lancer le traitement unifié ?",
                        default=True)
    ]
    confirm = inquirer.prompt(questions)
    
    if not confirm or not confirm['confirm']:
        console.print("[yellow]Opération annulée.[/yellow]")
        return
    
    # Exécuter unified avec les paramètres définis
    unified(
        jira_files=jira_files,
        confluence_files=confluence_files,
        output_dir=output_dir_str,  # Passer explicitement une chaîne de caractères
        min_match_score=min_match_score,
        max_items=max_items,
        use_llm=use_llm,
        api_key=api_key,
        skip_matching=skip_matching,
        compress=compress,
        compress_level=compress_level if compress else None,
        keep_originals=keep_originals if compress else None
    )


@app.command()
def describe_images(
    input_file: str = typer.Argument(..., help="Fichier PDF à analyser (doit se trouver dans le dossier files/)"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Fichier de sortie JSON (par défaut: dans /results/{pdf_base}_{timestamp}/...)"),
    max_images: int = typer.Option(10, "--max-images", help="Nombre maximum d'images à traiter"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout (secondes) par image pour l'appel API"),
    language: str = typer.Option("fr", "--lang", help="Langue de l'analyse (fr/en)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API OpenAI (si non définie dans les variables d'environnement)"),
    compress: bool = typer.Option(False, "--compress", help="Compresser le fichier de sortie avec zstd et orjson"),
    compress_level: int = typer.Option(19, "--compress-level", help="Niveau de compression zstd (1-22)"),
    keep_originals: bool = typer.Option(True, "--keep-originals/--no-originals", help="Conserver le JSON original en plus du compressé"),
):
    """
    Analyse un PDF, extrait les images intégrées et génère une description intelligente pour chaque image via GPT-4 Vision.
    Les résultats sont sauvegardés dans un fichier JSON dans un dossier horodaté dans /results.
    Possibilité de compresser le résultat comme dans la commande unified.
    """
    console = Console()
    if not os.path.exists(input_file):
        console.print(f"[bold red]Le fichier {input_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    if not input_file.lower().endswith(".pdf"):
        console.print(f"[bold red]Le fichier {input_file} n'est pas un PDF.[/bold red]")
        raise typer.Exit(1)
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Clé API OpenAI manquante. Utilisez --api-key ou définissez OPENAI_API_KEY.[/bold red]")
        raise typer.Exit(1)
    # Générer le dossier de sortie horodaté dans /results
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    pdf_base = os.path.splitext(os.path.basename(input_file))[0]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    output_dir = os.path.join(results_dir, f"{pdf_base}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    # Déterminer le nom du fichier de sortie
    if not output_file:
        output_file = os.path.join(output_dir, f"{pdf_base}_images_described.json")
    elif not os.path.isabs(output_file):
        output_file = os.path.join(output_dir, output_file)
    describer = PDFImageDescriber(
        openai_api_key=api_key,
        max_images=max_images,
        timeout=timeout,
        language=language,
    )
    console.print(Panel(f"Analyse des images du PDF : [cyan]{input_file}[/cyan]", title="Describe Images", border_style="blue"))
    with console.status("[bold blue]Extraction et analyse des images..."):
        try:
            results = describer.describe_images_in_pdf(input_file)
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'analyse : {e}[/bold red]")
            raise typer.Exit(1)
    # Sauvegarder les résultats
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            import json
            json.dump(results, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]✅ Analyse terminée. Résultats sauvegardés dans :\n[cyan]{output_file}[/cyan]\n[dim]Dossier : {output_dir}[/dim][/bold green]")
        # Compression si demandée
        if compress:
            try:
                from extract.compress_utils import compress_results_directory
                count, report = compress_results_directory(
                    output_dir,
                    compression_level=compress_level,
                    keep_originals=keep_originals,
                    generate_report=True
                )
                current_lang = get_current_language()
                report_path = os.path.join(output_dir, f"compression_report_{current_lang}.txt")
                console.print(f"[bold cyan]Compression terminée : {count} fichiers compressés.[/bold cyan]")
                if os.path.exists(report_path):
                    console.print(f"[bold]Rapport de compression :[/bold] {report_path}")
            except Exception as e:
                console.print(f"[bold yellow]⚠️ Erreur lors de la compression : {e}[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Erreur lors de la sauvegarde : {e}[/bold red]")
        raise typer.Exit(1)


def _run_interactive_describe_images():
    """Interface interactive pour la commande describe-images."""
    input_path = _prompt_for_file(t("select_file_pdf", "prompts"))
    if not input_path:
        return
    questions = [
        inquirer.Text('output', message=t("output_file", "prompts"), default=""),
        inquirer.Text('max_images', message="Nombre max d'images à traiter (défaut: 10)", default="10"),
        inquirer.Text('timeout', message="Timeout par image (secondes, défaut: 30)", default="30"),
        inquirer.Text('api_key', message=t("api_key", "prompts"), default=""),
        inquirer.List('language', message="Langue", choices=["fr", "en"], default="fr"),
    ]
    answers = inquirer.prompt(questions)
    output = answers['output'] if answers['output'].strip() else None
    max_images = int(answers['max_images']) if answers['max_images'].strip() else 10
    timeout = int(answers['timeout']) if answers['timeout'].strip() else 30
    api_key = answers['api_key'] if answers['api_key'].strip() else None
    language = answers['language']
    # Confirmation
    console.print(f"\n[bold]{t('summary', 'messages')}[/bold]")
    console.print(f"- {t('input_path', 'messages')} [cyan]{input_path}[/cyan]")
    console.print(f"- {t('output_path', 'messages')} [cyan]{output or t('auto_detection', 'messages')}[/cyan]")
    console.print(f"- Max images: [cyan]{max_images}[/cyan]")
    console.print(f"- Timeout: [cyan]{timeout}[/cyan]")
    console.print(f"- Langue: [cyan]{language}[/cyan]")
    questions = [
        inquirer.Confirm('confirm', message="Lancer l'analyse des images ?", default=True)
    ]
    confirm = inquirer.prompt(questions)
    if confirm and confirm['confirm']:
        describe_images(input_path, output, max_images, timeout, language, api_key)


if __name__ == "__main__":
    print_header()
    # S'assurer que les dépendances sont installées
    try:
        import inquirer
        import dotenv
    except ImportError:
        console.print("[yellow]Installation des dépendances requises...[/yellow]")
        from subprocess import run
        deps = ["inquirer", "python-dotenv", "typer", "rich"]
        run([sys.executable, "-m", "pip", "install"] + deps, check=True)
        import inquirer
        import dotenv
    
    app() 