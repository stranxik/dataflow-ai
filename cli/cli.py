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
    while True:
        console.print(f"\n[bold]Répertoire actuel:[/bold] {current_dir}")
        items = os.listdir(current_dir)
        files = [f for f in items if os.path.isfile(os.path.join(current_dir, f)) and f.endswith('.json')]
        dirs = [d for d in items if os.path.isdir(os.path.join(current_dir, d))]
        dirs.sort()
        files.sort()
        choices = []
        if current_dir != os.path.dirname(current_dir):
            choices.append("⬆️  [Dossier parent]")
        choices += [f"📁 [Dir] {d}" for d in dirs]
        choices += [f"📄 [Fichier] {f}" for f in files]
        if allow_validate:
            choices.append("✅ [Valider la sélection]")
        choices.append("✏️  [Entrer un chemin manuellement]")
        choices.append("❌ [Annuler]")
        questions = [
            inquirer.List('selection', message=message, choices=choices)
        ]
        answer = inquirer.prompt(questions)
        if not answer:
            return None
        selection = answer['selection']
        if selection.startswith("⬆️"):
            current_dir = os.path.dirname(current_dir)
        elif selection.startswith("✏️"):
            path = typer.prompt("Entrez le chemin complet du fichier")
            if os.path.isfile(path) and path.endswith('.json'):
                return path
            else:
                console.print("[yellow]Chemin invalide ou fichier non JSON.[/yellow]")
        elif selection.startswith("❌"):
            return None
        elif selection.startswith("✅"):
            return "__VALIDATE__"
        elif selection.startswith("📁"):
            dir_name = selection.split("[Dir] ",1)[1]
            current_dir = os.path.join(current_dir, dir_name)
        elif selection.startswith("📄"):
            file_name = selection.split("[Fichier] ",1)[1]
            return os.path.join(current_dir, file_name)

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
    use_llm: bool = typer.Option(False, "--llm/--no-llm", help="Utiliser un LLM pour l'enrichissement"),
    llm_model: str = typer.Option(None, "--model", help="Modèle LLM à utiliser"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API pour le LLM (ou variable d'environnement OPENAI_API_KEY)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Mode interactif pour les choix"),
    max_items: Optional[int] = typer.Option(None, "--max", help="Nombre maximum d'éléments à traiter"),
    root_key: str = typer.Option("items", "--root-key", help="Clé racine pour les éléments dans le JSON de sortie"),
    outlines: bool = typer.Option(False, help="Utiliser Outlines pour l'extraction structurée")
):
    """
    Traite un fichier JSON en le transformant pour utilisation avec LLM/Llamendex.
    """
    # 1. Vérifier que le fichier existe
    if not os.path.exists(input_file):
        console.print(f"[bold red]Le fichier {input_file} n'existe pas.[/bold red]")
        raise typer.Exit(1)
    
    # Générer un timestamp pour le nom du fichier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Utiliser le dossier results comme base
    base_results_dir = "results"
    ensure_dir(base_results_dir)
    
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
        f"Fichier de sortie : [cyan]{output_file}[/cyan]",
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
    if interactive:
        mapping_choices = find_mapping_files()
        mapping_choices.append("Sans mapping (détection automatique)")
        mapping_choices.append("Créer un mapping personnalisé")
        questions = [
            inquirer.List('mapping_choice',
                          message="Choisissez un mapping pour le traitement",
                          choices=mapping_choices,
                          default="Sans mapping (détection automatique)" if not file_type else f"{file_type['type']}_mapping.json" if f"{file_type['type']}_mapping.json" in mapping_choices else "Sans mapping (détection automatique)")
        ]
        answers = inquirer.prompt(questions)
        if answers["mapping_choice"] == "Sans mapping (détection automatique)":
            mapping_file = None
        elif answers["mapping_choice"] == "Créer un mapping personnalisé":
            # Ouvrir un éditeur pour créer un mapping personnalisé
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
                mapping_file = temp_mapping_file
            except json.JSONDecodeError:
                console.print("[bold red]Le mapping créé n'est pas un JSON valide. Poursuite sans mapping.[/bold red]")
                mapping_file = None
        else:
            mapping_file = os.path.join(DEFAULT_MAPPINGS_DIR, answers["mapping_choice"])
    
    # 5. Si auto_mapping et qu'on a détecté un type, mais pas de mapping spécifié
    elif auto_mapping and file_type and not mapping_file:
        auto_mapping_file = os.path.join(DEFAULT_MAPPINGS_DIR, f"{file_type['type']}_mapping.json")
        if os.path.exists(auto_mapping_file):
            mapping_file = auto_mapping_file
            console.print(f"Utilisation automatique du mapping : [cyan]{mapping_file}[/cyan]")
    
    # 6. Traitement LLM interactif (si demandé)
    if use_llm and interactive and not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = typer.prompt("Entrez votre clé API OpenAI", hide_input=True)
        
        if not api_key:
            console.print("[bold yellow]Pas de clé API fournie. L'analyse LLM sera désactivée.[/bold yellow]")
            use_llm = False
        
        if use_llm:
            questions = [
                inquirer.List('llm_model',
                            message="Choisissez un modèle LLM",
                            choices=LLM_MODELS,
                            default="gpt-4.1")
            ]
            answers = inquirer.prompt(questions)
            llm_model = answers["llm_model"]
    
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
            detect_fields=True,
            extract_keywords=True
        )
        
        # Traiter le fichier
        with console.status("[bold blue]Traitement en cours..."):
            success = processor.process_file(
                input_file=input_file,
                output_file=output_file,
                max_items=max_items,
                root_key=root_key
            )
        
        if not success:
            console.print("[bold red]Erreur lors du traitement du fichier.[/bold red]")
            raise typer.Exit(1)
        
        # 8. Post-traitement avec LLM si demandé
        if use_llm:
            # Utiliser les valeurs par défaut si non spécifiées
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
            
            if not llm_model:
                llm_model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")
            
            if not api_key:
                console.print("[bold yellow]Pas de clé API OpenAI trouvée. L'analyse LLM ne sera pas effectuée.[/bold yellow]")
                use_llm = False
            
            if use_llm:
                console.print(f"Enrichissement avec LLM ([cyan]{llm_model}[/cyan])...")
                
                # Charger le fichier de sortie
                with open(output_file, 'r', encoding='utf-8') as f:
                    processed_data = json.load(f)
                
                # Enrichir avec LLM
                enriched_data = process_with_llm(
                    content=processed_data,
                    model=llm_model,
                    api_key=api_key
                )
                
                # Sauvegarder les données enrichies
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(enriched_data, f, indent=2, ensure_ascii=False)
                
                console.print("[bold green]Enrichissement LLM terminé ![/bold green]")
        
        # 9. Afficher un résumé et des statistiques
        show_summary(output_file)
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors du traitement: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


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
):
    """
    Établit des correspondances entre tickets JIRA et pages Confluence.
    """
    # Générer un timestamp pour le nom du dossier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Utiliser le dossier results comme base
    base_results_dir = "results"
    ensure_dir(base_results_dir)
    
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
    use_llm: bool = typer.Option(False, "--llm", help="Utiliser un LLM pour l'enrichissement"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Clé API pour le LLM"),
    skip_matching: bool = typer.Option(False, "--skip-matching", help="Ne pas effectuer le matching entre JIRA et Confluence"),
):
    """
    Exécute le flux unifié : traitement JIRA + Confluence et matching.
    """
    # Générer un timestamp pour le nom du dossier
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # Utiliser le dossier results comme base et ajouter le timestamp
    base_results_dir = "results"
    ensure_dir(base_results_dir)
    
    # Si output_dir est spécifié, l'utiliser comme nom de dossier avec le timestamp
    if output_dir:
        output_dir = os.path.join(base_results_dir, f"{output_dir}_{timestamp}")
    else:
        default_dir = os.environ.get("UNIFIED_OUTPUT_DIR", "output_unified")
        output_dir = os.path.join(base_results_dir, f"{default_dir}_{timestamp}")
    
    # Vérifier les fichiers
    for file in jira_files + confluence_files:
        if not os.path.exists(file):
            console.print(f"[bold red]Le fichier {file} n'existe pas.[/bold red]")
            raise typer.Exit(1)
    
    # Créer le répertoire de sortie
    ensure_dir(output_dir)
    
    # Créer les sous-répertoires pour une meilleure organisation
    jira_dir = os.path.join(output_dir, "jira")
    confluence_dir = os.path.join(output_dir, "confluence")
    matches_dir = os.path.join(output_dir, "matches")
    split_jira_dir = os.path.join(output_dir, "split_jira_files")
    split_confluence_dir = os.path.join(output_dir, "split_confluence_files")
    llm_ready_dir = os.path.join(output_dir, "llm_ready")
    
    for directory in [jira_dir, confluence_dir, matches_dir, split_jira_dir, split_confluence_dir, llm_ready_dir]:
        ensure_dir(directory)
    
    # Afficher les infos
    console.print(Panel.fit(
        f"[bold]Traitement unifié JIRA + Confluence[/bold]\n\n"
        f"Fichiers JIRA : [cyan]{', '.join(jira_files)}[/cyan]\n"
        f"Fichiers Confluence : [cyan]{', '.join(confluence_files)}[/cyan]\n"
        f"Répertoire de sortie : [cyan]{output_dir}[/cyan]",
        title="Traitement Unifié",
        border_style="blue"
    ))
    
    # Construire le chemin vers le script unified_analysis
    unified_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               "extract", "run_unified_analysis.py")
    
    # Exécuter le script unifié avec la nouvelle structure de dossiers
    cmd = [
        sys.executable, unified_script,
        "--jira-files"
    ] + jira_files
    
    if confluence_files:
        cmd += ["--confluence-files"] + confluence_files
    
    cmd += [
        "--output-dir", output_dir,
        "--min-match-score", str(min_match_score),
        "--jira-dir", jira_dir,
        "--confluence-dir", confluence_dir,
        "--matches-dir", matches_dir,
        "--split-jira-dir", split_jira_dir,
        "--split-confluence-dir", split_confluence_dir,
        "--llm-ready-dir", llm_ready_dir
    ]
    
    if max_items:
        cmd += ["--max-items", str(max_items)]
    
    if skip_matching:
        cmd += ["--skip-matching"]
    
    if use_llm:
        cmd += ["--with-openai"]
        if api_key or os.environ.get("OPENAI_API_KEY"):
            cmd += ["--api-key", api_key or os.environ.get("OPENAI_API_KEY")]
    
    with console.status("[bold blue]Traitement unifié en cours..."):
        from subprocess import run, PIPE
        result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    
    if result.returncode != 0:
        console.print("[bold red]Erreur lors du traitement unifié:[/bold red]")
        console.print(result.stderr)
        raise typer.Exit(1)
    
    # Afficher les résultats
    console.print(result.stdout)
    
    # Générer un arborescence globale du répertoire de sortie
    from extract.generic_json_processor import write_tree
    write_tree(output_dir, "global_arborescence.txt")
    
    console.print(f"\nFichiers générés dans : [bold cyan]{output_dir}[/bold cyan]")
    console.print(f"Arborescence globale générée dans : [bold cyan]{os.path.join(output_dir, 'global_arborescence.txt')}[/bold cyan]")
    console.print("\n[bold green]Traitement unifié terminé avec succès ![/bold green]")


@app.command()
def chunks(
    input_file: str = typer.Argument(..., help="Fichier JSON volumineux à découper"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Répertoire de sortie pour les morceaux"),
    items_per_file: int = typer.Option(500, "--items-per-file", "-n", help="Nombre d'éléments par fichier"),
    process_after: bool = typer.Option(False, "--process", "-p", help="Traiter chaque morceau après découpage"),
    mapping_file: Optional[str] = typer.Option(None, "--mapping", "-m", help="Fichier de mapping à utiliser pour le traitement"),
    use_llm: bool = typer.Option(False, "--llm", help="Utiliser un LLM pour l'enrichissement lors du traitement"),
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
    
    # Utiliser le dossier results comme base
    base_results_dir = "results"
    ensure_dir(base_results_dir)
    
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
def interactive():
    """
    Mode entièrement interactif qui guide l'utilisateur à travers toutes les étapes.
    
    Ce mode permet de choisir le type d'opération à effectuer et guide
    l'utilisateur à travers toutes les options de manière conviviale.
    """
    console.print(Panel.fit(
        "[bold]Assistant interactif pour le traitement de données[/bold]\n\n"
        "Cet assistant va vous guider à travers les différentes étapes de traitement.",
        title="Mode Interactif",
        border_style="green"
    ))
    
    # 1. Sélection du type d'opération
    operation_choices = [
        "Traiter un fichier JSON (process)",
        "Découper un fichier volumineux (chunks)",
        "Établir des correspondances JIRA-Confluence (match)",
        "Flux complet JIRA + Confluence (unified)",
        "Quitter"
    ]
    
    questions = [
        inquirer.List('operation',
                     message="Quelle opération souhaitez-vous effectuer ?",
                     choices=operation_choices)
    ]
    answers = inquirer.prompt(questions)
    
    if not answers or answers['operation'] == "Quitter":
        return
    
    # 2. Selon l'opération choisie, poser les questions appropriées
    if "Traiter un fichier JSON" in answers['operation']:
        _run_interactive_process()
    elif "Découper un fichier volumineux" in answers['operation']:
        _run_interactive_chunks()
    elif "Établir des correspondances" in answers['operation']:
        _run_interactive_match()
    elif "Flux complet" in answers['operation']:
        _run_interactive_unified()


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
                     default="")
    ]
    answers_advanced = inquirer.prompt(questions)
    
    use_llm = answers_advanced['use_llm']
    max_items = int(answers_advanced['max_items']) if answers_advanced['max_items'].strip() else None
    
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
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    items_per_file = int(answers['items_per_file'])
    process_after = answers['process_after']
    
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
        use_llm=use_llm
    )


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
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    min_score = float(answers['min_score'])
    llm_assist = answers['llm_assist']
    
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
        llm_model=llm_model
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
    
    # Répertoire de sortie
    default_output_dir = os.environ.get("UNIFIED_OUTPUT_DIR", "output_unified")
    output_dir = typer.prompt("Répertoire de sortie", default=default_output_dir)
    
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
                        default=False)
    ]
    answers = inquirer.prompt(questions)
    
    min_match_score = float(answers['min_match_score'])
    max_items = int(answers['max_items']) if answers['max_items'].strip() else None
    use_llm = answers['use_llm']
    skip_matching = answers['skip_matching']
    
    # Options LLM si demandées
    api_key = None
    if use_llm:
        # Clé API
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = typer.prompt("Entrez votre clé API OpenAI", hide_input=True)
    
    # Confirmation finale
    console.print("\n[bold]Récapitulatif :[/bold]")
    console.print(f"- Fichiers JIRA : [cyan]{', '.join(jira_files)}[/cyan]")
    if confluence_files:
        console.print(f"- Fichiers Confluence : [cyan]{', '.join(confluence_files)}[/cyan]")
    console.print(f"- Répertoire de sortie : [cyan]{output_dir}[/cyan]")
    console.print(f"- Score minimum : [cyan]{min_match_score}[/cyan]")
    if max_items:
        console.print(f"- Limite d'éléments : [cyan]{max_items}[/cyan]")
    console.print(f"- Enrichissement LLM : [cyan]{'Oui' if use_llm else 'Non'}[/cyan]")
    console.print(f"- Ignorer matching : [cyan]{'Oui' if skip_matching else 'Non'}[/cyan]")
    
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
        output_dir=output_dir,
        min_match_score=min_match_score,
        max_items=max_items,
        use_llm=use_llm,
        api_key=api_key,
        skip_matching=skip_matching
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