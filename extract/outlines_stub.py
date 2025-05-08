"""
Fichier stub pour faciliter le développement sans dépendre d'Outlines
et pour supporter l'analyse statique de code.

Ce fichier imite la structure d'Outlines 0.2.3 pour que le code 
continue à fonctionner même si la bibliothèque n'est pas installée.
"""
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generator

# Constante pour détecter l'utilisation du stub
IS_STUB = True

# Type pour les modèles
T = TypeVar('T')

# ===== Module outlines ======
class Template:
    """Classe pour créer des templates de prompt avec variables"""
    
    def __init__(self, template_string):
        self.template_string = template_string
    
    @staticmethod
    def from_string(template_string):
        """Crée un template à partir d'une chaîne de caractères"""
        return Template(template_string)
    
    def __call__(self, **kwargs):
        """Rend le template avec les variables spécifiées"""
        # Version simplifiée qui remplace les variables {{var}} par leur valeur
        result = self.template_string
        for key, value in kwargs.items():
            placeholder = "{{{{ {} }}}}".format(key)
            result = result.replace(placeholder, str(value))
        return result

class models:
    @staticmethod
    def openai(model: str, api_key: str, temperature: float = 0.0) -> 'OpenAIModel':
        """Crée un modèle OpenAI"""
        return OpenAIModel(model, api_key, temperature)

    @staticmethod
    def transformers(model_name: str, **kwargs) -> 'TransformersModel':
        """Crée un modèle Transformers"""
        return TransformersModel(model_name, **kwargs)

class OpenAIModel:
    def __init__(self, model: str, api_key: str, temperature: float = 0.0):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

class TransformersModel:
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs

class samplers:
    @staticmethod
    def greedy():
        """Renvoie un sampler greedy (déterministe)"""
        return "greedy"
    
    @staticmethod
    def multinomial():
        """Renvoie un sampler multinomial (aléatoire)"""
        return "multinomial"

# ===== Module outlines.generate ======
class generate:
    @staticmethod
    def text(model: Any) -> Callable:
        """Génère du texte libre"""
        def _generate_text(prompt: str, **kwargs) -> str:
            return f"[Texte généré depuis prompt: {prompt[:30]}...]"
        return _generate_text
    
    @staticmethod
    def regex(model: Any, pattern: str, sampler: Any = None) -> Callable:
        """Génère du texte qui suit un pattern regex"""
        def _generate_with_regex(prompt: str, **kwargs) -> str:
            return f"[Texte généré avec regex]"
        return _generate_with_regex
    
    @staticmethod
    def choice(model: Any, choices: Union[List[str], Any]) -> Callable:
        """Génère un texte parmi des choix définis"""
        def _generate_choice(prompt: str, **kwargs) -> str:
            if isinstance(choices, list) and choices:
                return choices[0]
            return "[Choix généré]"
        return _generate_choice
    
    @staticmethod
    def json(model: Any, schema: Union[Dict[str, Any], Any]) -> Callable:
        """Génère du JSON suivant un schéma"""
        def _generate_json(prompt: str, **kwargs) -> Dict[str, Any]:
            return {
                "summary": "Résumé généré par le stub",
                "keywords": ["mot-clé1", "mot-clé2"],
                "entities": {
                    "people": ["Personne1", "Personne2"],
                    "organizations": ["Organisation1", "Organisation2"],
                    "locations": ["Lieu1", "Lieu2"],
                    "technical_terms": ["Terme1", "Terme2"]
                },
                "sentiment": "neutral"
            }
        return _generate_json
    
    @staticmethod
    def cfg(model: Any, grammar: str) -> Callable:
        """Génère du texte suivant une grammaire formelle"""
        def _generate_with_grammar(prompt: str, **kwargs) -> str:
            return f"[Texte généré avec grammaire]"
        return _generate_with_grammar
    
    @staticmethod
    def format(model: Any, type_constraint: Any) -> Callable:
        """Génère du texte avec une contrainte de type"""
        def _generate_with_type(prompt: str, **kwargs) -> Any:
            if type_constraint == int:
                return 42
            elif type_constraint == float:
                return 3.14
            return f"[Donnée générée de type {type_constraint.__name__}]"
        return _generate_with_type

# Module outlines.prompts
class ChatPrompt:
    def __init__(self, messages: List[Dict[str, str]]):
        self.messages = messages
    
    def __call__(self, **kwargs) -> str:
        """Render the prompt with variables"""
        return "[ChatPrompt généré]"

class prompts:
    ChatPrompt = ChatPrompt
    
    @staticmethod
    def Template(template_string: str):
        """Créer un template de prompt Jinja2"""
        def _render(**kwargs) -> str:
            return f"[Template avec variables: {list(kwargs.keys())}]"
        return _render

# Module outlines.regex
class regex:
    """Classe pour définir des contraintes regex pour la génération"""
    def __init__(self, pattern: str):
        self.pattern = pattern
    
    def __call__(self, *args, **kwargs) -> str:
        return f"[Regex appliqué: {self.pattern[:20]}...]"

# Module outlines.json_schema
class JsonSchemaParser:
    """Parseur de JSON Schema pour guider la génération"""
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
    
    def __call__(self, *args, **kwargs) -> Dict[str, Any]:
        return {"result": "Données générées selon schéma"}

# Ancienne fonction generate (retro-compatibilité)
def generate_func(model: Any, prompt: Any, guide: Any = None, **kwargs) -> Union[str, Dict[str, Any]]:
    """Version stub de la fonction generate d'Outlines (ancienne API)"""
    if isinstance(guide, JsonSchemaParser):
        return {"result": "Stub JSON généré"}
    return "Texte généré par le stub Outlines"
