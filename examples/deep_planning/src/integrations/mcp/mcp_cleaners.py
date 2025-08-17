"""
Strategie di pulizia specifiche per tool MCP - Rimozione intelligente del rumore

Questo modulo implementa le strategie di pulizia concrete per i principali tool MCP utilizzati
da DeepAgents, con focus sulla riduzione drastica del rumore mantenendo le informazioni essenziali.

Strategie implementate:
- ProjectListCleaner: Mantiene solo il progetto rilevante da General_list_projects
- CodeSnippetCleaner: Estrae solo il testo da Code_find_relevant_code_snippets
- DocumentCleaner: Pulisce documenti e attachment rimuovendo metadati ridondanti
- UserStoryListCleaner: Semplifica elenchi di user stories mantenendo solo i dati core
- RepositoryListCleaner: Filtra repository info mantenendo solo identificatori essenziali

Ogni strategia implementa l'interfaccia CleaningStrategy e fornisce metriche di riduzione accurate.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass

from ...context.context_manager import CleaningStrategy, CleaningResult, CleaningStatus

# Import configurazione centralizzata
try:
    from ...config.config_loader import get_full_config
    CONFIG_LOADER_AVAILABLE = True
except ImportError:
    CONFIG_LOADER_AVAILABLE = False

# Configure debug logging for MCP cleaners
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def _load_cleaning_config() -> Dict[str, Any]:
    """Carica configurazione cleaning strategies da YAML."""
    if CONFIG_LOADER_AVAILABLE:
        try:
            full_config = get_full_config()
            return full_config.cleaning_strategies
        except Exception as e:
            logger.warning(f"⚠️ Failed to load cleaning strategies config: {e}")
    
    # Fallback configuration
    return {
        "ProjectListCleaner": {
            "enabled": True,
            "max_projects_fallback": 3,
            "keep_fields": ["project_id", "id", "name", "title", "description"],
            "use_context_targeting": True
        },
        "CodeSnippetCleaner": {
            "enabled": True,
            "primary_field": "text",
            "optional_fields": ["file_path", "filename"],
            "remove_metadata": True,
            "max_snippet_length": 5000
        },
        "DocumentCleaner": {
            "enabled": True,
            "essential_fields": ["content", "text", "body", "title", "name"],
            "remove_empty_lines": True,
            "header_footer_patterns": ["^={3,}", "^-{3,}", "^page \\d+"]
        },
        "UserStoryListCleaner": {
            "enabled": True,
            "essential_fields": ["user_story_id", "story_id", "id", "title", "description", "status"],
            "max_stories": 0,
            "normalize_ids": True
        },
        "RepositoryListCleaner": {
            "enabled": True,
            "essential_fields": ["repository_id", "repo_id", "id", "name", "description"],
            "max_repositories": 0,
            "normalize_ids": True
        }
    }


class ProjectListCleaner(CleaningStrategy):
    """
    Pulisce i risultati di General_list_projects mantenendo solo il progetto rilevante.
    
    Problema risolto: General_list_projects restituisce tutti i progetti con molti metadati,
    ma spesso ne serve solo uno. Questa strategia identifica il progetto di interesse e
    rimuove tutti gli altri, riducendo drasticamente il rumore.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config:
            self.config = config
        else:
            self.config = _load_cleaning_config().get("ProjectListCleaner", {})
    
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Identifica se può pulire risultati di General_list_projects."""
        logger.debug(f"ProjectListCleaner.can_clean() invoked with tool_name='{tool_name}', data_type={type(data)}")
        
        can_clean_result = (
            "general_list_projects" in tool_name.lower() or
            (isinstance(data, (dict, list)) and self._contains_project_list(data))
        )
        
        logger.debug(f"ProjectListCleaner.can_clean() result: {can_clean_result}")
        return can_clean_result
    
    def _contains_project_list(self, data: Any) -> bool:
        """Verifica se i dati contengono una lista di progetti."""
        if isinstance(data, dict):
            # Cerca pattern tipici dei progetti
            return any(
                key in str(data).lower() for key in 
                ['project_id', 'projects', 'project_name', 'project_list']
            )
        elif isinstance(data, list) and data:
            # Controlla il primo elemento
            first_item = data[0] if data else {}
            return isinstance(first_item, dict) and any(
                key in first_item for key in ['project_id', 'name', 'id', 'title']
            )
        return False
    
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """
        Pulisce la lista progetti mantenendo solo quello rilevante.
        
        Logica di pulizia:
        1. Identifica il progetto target dal contesto o dal nome
        2. Mantiene solo i campi essenziali: project_id, name
        3. Rimuove tutti gli altri progetti e metadati
        """
        logger.debug(f"ProjectListCleaner.clean() invoked with data_type={type(data)}, context={context}")
        
        if not isinstance(data, (dict, list)):
            logger.debug("ProjectListCleaner.clean() - data is not dict or list, skipping cleaning")
            return self._no_cleaning_result(data)
        
        target_project = self._identify_target_project(data, context)
        logger.debug(f"ProjectListCleaner.clean() - target_project identified: {target_project is not None}")
        
        if not target_project:
            # Se non riesce a identificare un progetto specifico, mantiene solo i primi 3
            logger.debug("ProjectListCleaner.clean() - no target project found, cleaning multiple projects (limit=3)")
            cleaned = self._clean_multiple_projects(data, limit=3)
        else:
            # Mantiene solo il progetto target
            logger.debug("ProjectListCleaner.clean() - cleaning single target project")
            cleaned = self._clean_single_project(target_project)
        
        result = CleaningResult.from_data(
            data, cleaned, "ProjectListCleaner", CleaningStatus.COMPLETED
        )
        result.metadata = {
            "target_project_found": target_project is not None,
            "original_project_count": self._count_projects(data),
            "cleaned_project_count": self._count_projects(cleaned)
        }
        
        logger.debug(f"ProjectListCleaner.clean() completed - original_count={result.metadata['original_project_count']}, cleaned_count={result.metadata['cleaned_project_count']}")
        return cleaned, result
    
    def _identify_target_project(self, data: Any, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Identifica il progetto target basandosi sul contesto."""
        projects = self._extract_projects(data)
        if not projects:
            return None
        
        # Se c'è solo un progetto, quello è il target
        if len(projects) == 1:
            return projects[0]
        
        # Cerca nel contesto indicazioni sul progetto desiderato
        if context:
            target_indicators = [
                context.get('project_id'),
                context.get('project_name'),
                context.get('current_project'),
                context.get('selected_project')
            ]
            
            for project in projects:
                for indicator in target_indicators:
                    if indicator and (
                        str(indicator).lower() in str(project.get('name', '')).lower() or
                        str(indicator) == str(project.get('project_id', '')) or
                        str(indicator) == str(project.get('id', ''))
                    ):
                        return project
        
        # Se non trova match, restituisce il primo progetto
        return projects[0] if projects else None
    
    def _extract_projects(self, data: Any) -> List[Dict[str, Any]]:
        """Estrae la lista dei progetti dai dati."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            # Cerca campi che potrebbero contenere progetti
            for key in ['projects', 'project_list', 'data', 'results']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Se il dict stesso sembra un progetto
            if 'project_id' in data or 'name' in data:
                return [data]
        return []
    
    def _clean_single_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Pulisce un singolo progetto mantenendo solo i campi essenziali."""
        essential_fields = ['project_id', 'id', 'name', 'title', 'description']
        
        cleaned = {}
        for field in essential_fields:
            if field in project:
                cleaned[field] = project[field]
        
        # Se non ha trovato project_id ma ha id, lo rinomina
        if 'project_id' not in cleaned and 'id' in cleaned:
            cleaned['project_id'] = cleaned['id']
        
        return cleaned
    
    def _clean_multiple_projects(self, data: Any, limit: int = 3) -> List[Dict[str, Any]]:
        """Pulisce multipli progetti limitando il numero e i campi."""
        projects = self._extract_projects(data)
        limited_projects = projects[:limit]
        
        return [self._clean_single_project(p) for p in limited_projects]
    
    def _count_projects(self, data: Any) -> int:
        """Conta il numero di progetti nei dati."""
        return len(self._extract_projects(data))
    
    def _no_cleaning_result(self, data: Any) -> Tuple[Any, CleaningResult]:
        """Restituisce risultato quando non è possibile pulire."""
        result = CleaningResult.from_data(
            data, data, "ProjectListCleaner", CleaningStatus.SKIPPED
        )
        return data, result
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la riduzione possibile per progetti."""
        projects = self._extract_projects(data)
        max_projects = self.config.get("max_projects_fallback", 3)
        
        if len(projects) <= 1:
            return 20.0  # Rimozione metadati
        elif len(projects) <= max_projects:
            return 50.0  # Rimozione metadati + alcuni progetti
        else:
            # Rimozione progetti extra basata sulla configurazione
            extra_projects = len(projects) - max_projects
            return 70.0 + min(extra_projects * 10, 20.0)  # Cap alla riduzione del 90%


class CodeSnippetCleaner(CleaningStrategy):
    """
    Pulisce Code_find_relevant_code_snippets mantenendo solo il campo 'text'.
    
    Problema risolto: Code_find_relevant_code_snippets restituisce molti metadati
    (file_path, line_numbers, entity_info, scores) ma spesso serve solo il codice.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config:
            self.config = config
        else:
            self.config = _load_cleaning_config().get("CodeSnippetCleaner", {})
    
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Identifica se può pulire risultati di code search."""
        logger.debug(f"CodeSnippetCleaner.can_clean() invoked with tool_name='{tool_name}', data_type={type(data)}")
        
        can_clean_result = (
            "code_find_relevant_code_snippets" in tool_name.lower() or
            "find_relevant_code" in tool_name.lower() or
            self._contains_code_snippets(data)
        )
        
        logger.debug(f"CodeSnippetCleaner.can_clean() result: {can_clean_result}")
        return can_clean_result
    
    def _contains_code_snippets(self, data: Any) -> bool:
        """Verifica se i dati contengono code snippets."""
        if isinstance(data, dict):
            return any(
                key in data for key in ['text', 'content', 'code', 'snippet']
            ) and any(
                key in str(data).lower() for key in ['file_path', 'line_', 'entity']
            )
        elif isinstance(data, list) and data:
            first_item = data[0] if data else {}
            return isinstance(first_item, dict) and 'text' in first_item
        return False
    
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """
        Pulisce code snippets mantenendo solo il testo e info essenziali.
        
        Campi mantenuti:
        - text: Contenuto del codice (essenziale)
        - file_path: Path del file (opzionale, se richiesto nel context)
        
        Campi rimossi:
        - line_numbers, entity_info, scores, metadata vari
        """
        logger.debug(f"CodeSnippetCleaner.clean() invoked with data_type={type(data)}, context={context}")
        
        if not self._contains_code_snippets(data):
            logger.debug("CodeSnippetCleaner.clean() - data does not contain code snippets, skipping cleaning")
            return self._no_cleaning_result(data)
        
        # Determina se mantenere file_path dal contesto
        keep_file_path = context and context.get('keep_file_paths', False)
        logger.debug(f"CodeSnippetCleaner.clean() - keep_file_paths: {keep_file_path}")
        
        if isinstance(data, list):
            logger.debug(f"CodeSnippetCleaner.clean() - cleaning {len(data)} code snippets")
            cleaned = [self._clean_single_snippet(item, keep_file_path) for item in data]
        elif isinstance(data, dict):
            logger.debug("CodeSnippetCleaner.clean() - cleaning single code snippet")
            cleaned = self._clean_single_snippet(data, keep_file_path)
        else:
            logger.debug("CodeSnippetCleaner.clean() - unexpected data type, skipping cleaning")
            return self._no_cleaning_result(data)
        
        result = CleaningResult.from_data(
            data, cleaned, "CodeSnippetCleaner", CleaningStatus.COMPLETED
        )
        result.metadata = {
            "snippets_cleaned": len(data) if isinstance(data, list) else 1,
            "file_paths_kept": keep_file_path
        }
        
        logger.debug(f"CodeSnippetCleaner.clean() completed - snippets_cleaned={result.metadata['snippets_cleaned']}")
        return cleaned, result
    
    def _clean_single_snippet(self, snippet: Dict[str, Any], keep_file_path: bool = False) -> Dict[str, Any]:
        """Pulisce un singolo code snippet."""
        if not isinstance(snippet, dict):
            return snippet
        
        cleaned = {}
        
        # Campo essenziale: testo del codice
        for text_field in ['text', 'content', 'code', 'snippet']:
            if text_field in snippet:
                cleaned['text'] = snippet[text_field]
                break
        
        # Campo opzionale: file path
        if keep_file_path:
            for path_field in ['file_path', 'path', 'filename']:
                if path_field in snippet:
                    cleaned['file_path'] = snippet[path_field]
                    break
        
        return cleaned
    
    def _no_cleaning_result(self, data: Any) -> Tuple[Any, CleaningResult]:
        """Restituisce risultato quando non è possibile pulire."""
        result = CleaningResult.from_data(
            data, data, "CodeSnippetCleaner", CleaningStatus.SKIPPED
        )
        return data, result
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la riduzione possibile per code snippets."""
        return 75.0  # Rimozione di ~75% dei metadati


class DocumentCleaner(CleaningStrategy):
    """
    Pulisce documenti e attachment rimuovendo metadati ridondanti.
    
    Problema risolto: Document content spesso include headers, metadata,
    formatting che aumenta il rumore senza aggiungere valore semantico.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config:
            self.config = config
        else:
            self.config = _load_cleaning_config().get("DocumentCleaner", {})
    
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Identifica se può pulire documenti."""
        logger.debug(f"DocumentCleaner.can_clean() invoked with tool_name='{tool_name}', data_type={type(data)}")
        
        can_clean_result = (
            "get_document_content" in tool_name.lower() or
            "attachment" in tool_name.lower() or
            self._contains_document_content(data)
        )
        
        logger.debug(f"DocumentCleaner.can_clean() result: {can_clean_result}")
        return can_clean_result
    
    def _contains_document_content(self, data: Any) -> bool:
        """Verifica se i dati contengono contenuto di documenti."""
        if isinstance(data, dict):
            doc_indicators = ['content', 'text', 'body', 'document', 'attachment']
            return any(indicator in data for indicator in doc_indicators)
        return False
    
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """Pulisce il contenuto del documento."""
        logger.debug(f"DocumentCleaner.clean() invoked with data_type={type(data)}, context={context}")
        
        if not self._contains_document_content(data):
            logger.debug("DocumentCleaner.clean() - data does not contain document content, skipping cleaning")
            return self._no_cleaning_result(data)
        
        if isinstance(data, dict):
            logger.debug("DocumentCleaner.clean() - cleaning document dictionary")
            cleaned = self._clean_document_dict(data)
        else:
            logger.debug("DocumentCleaner.clean() - unexpected data type, skipping cleaning")
            return self._no_cleaning_result(data)
        
        result = CleaningResult.from_data(
            data, cleaned, "DocumentCleaner", CleaningStatus.COMPLETED
        )
        
        logger.debug("DocumentCleaner.clean() completed successfully")
        return cleaned, result
    
    def _clean_document_dict(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Pulisce un documento mantenendo solo contenuto essenziale."""
        cleaned = {}
        
        # Campi essenziali da mantenere
        essential_fields = ['content', 'text', 'body', 'title', 'name']
        
        for field in essential_fields:
            if field in doc:
                if field in ['content', 'text', 'body']:
                    # Pulisce il contenuto testuale
                    cleaned[field] = self._clean_text_content(doc[field])
                else:
                    # Mantiene titolo e nome così come sono
                    cleaned[field] = doc[field]
        
        return cleaned
    
    def _clean_text_content(self, content: str) -> str:
        """Pulisce il contenuto testuale rimuovendo elementi di formatting."""
        if not isinstance(content, str):
            return str(content)
        
        # Rimuove header e footer comuni
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Salta linee di header/footer comuni
            if self._is_header_footer_line(line):
                continue
            
            # Salta linee vuote multiple consecutive
            if not line and cleaned_lines and not cleaned_lines[-1]:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _is_header_footer_line(self, line: str) -> bool:
        """Identifica linee di header/footer da rimuovere."""
        line_lower = line.lower()
        
        header_footer_patterns = [
            r'^={3,}',  # Linee di uguale
            r'^-{3,}',  # Linee di trattino
            r'^page \d+',  # Numerazione pagine
            r'confidential',
            r'proprietary',
            r'copyright',
            r'©',
            r'^generated on',
            r'^created by',
            r'^last updated'
        ]
        
        return any(re.match(pattern, line_lower) for pattern in header_footer_patterns)
    
    def _no_cleaning_result(self, data: Any) -> Tuple[Any, CleaningResult]:
        """Restituisce risultato quando non è possibile pulire."""
        result = CleaningResult.from_data(
            data, data, "DocumentCleaner", CleaningStatus.SKIPPED
        )
        return data, result
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la riduzione possibile per documenti."""
        return 30.0  # Rimozione di ~30% del formatting


class UserStoryListCleaner(CleaningStrategy):
    """
    Pulisce liste di user stories mantenendo solo dati core.
    
    Problema risolto: Studio_list_user_stories restituisce molti metadati
    per ogni story, ma spesso servono solo id, title e description.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config:
            self.config = config
        else:
            self.config = _load_cleaning_config().get("UserStoryListCleaner", {})
    
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Identifica se può pulire user stories."""
        logger.debug(f"UserStoryListCleaner.can_clean() invoked with tool_name='{tool_name}', data_type={type(data)}")
        
        can_clean_result = (
            "studio_list_user_stories" in tool_name.lower() or
            "list_user_stories" in tool_name.lower() or
            self._contains_user_stories(data)
        )
        
        logger.debug(f"UserStoryListCleaner.can_clean() result: {can_clean_result}")
        return can_clean_result
    
    def _contains_user_stories(self, data: Any) -> bool:
        """Verifica se i dati contengono user stories."""
        if isinstance(data, list) and data:
            first_item = data[0] if data else {}
            return isinstance(first_item, dict) and any(
                key in first_item for key in ['user_story_id', 'story_id', 'title', 'description']
            )
        return False
    
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """Pulisce user stories mantenendo solo campi essenziali."""
        logger.debug(f"UserStoryListCleaner.clean() invoked with data_type={type(data)}, context={context}")
        
        if not isinstance(data, list):
            logger.debug("UserStoryListCleaner.clean() - data is not a list, skipping cleaning")
            return self._no_cleaning_result(data)
        
        logger.debug(f"UserStoryListCleaner.clean() - cleaning {len(data)} user stories")
        cleaned = [self._clean_single_user_story(story) for story in data if isinstance(story, dict)]
        
        result = CleaningResult.from_data(
            data, cleaned, "UserStoryListCleaner", CleaningStatus.COMPLETED
        )
        result.metadata = {
            "stories_cleaned": len(cleaned),
            "original_stories": len(data)
        }
        
        logger.debug(f"UserStoryListCleaner.clean() completed - original_stories={result.metadata['original_stories']}, stories_cleaned={result.metadata['stories_cleaned']}")
        return cleaned, result
    
    def _clean_single_user_story(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """Pulisce una singola user story."""
        essential_fields = ['user_story_id', 'story_id', 'id', 'title', 'description', 'status']
        
        cleaned = {}
        for field in essential_fields:
            if field in story:
                cleaned[field] = story[field]
        
        # Se non ha story_id ma ha id, lo rinomina
        if 'user_story_id' not in cleaned and 'id' in cleaned:
            cleaned['user_story_id'] = cleaned['id']
        
        return cleaned
    
    def _no_cleaning_result(self, data: Any) -> Tuple[Any, CleaningResult]:
        """Restituisce risultato quando non è possibile pulire."""
        result = CleaningResult.from_data(
            data, data, "UserStoryListCleaner", CleaningStatus.SKIPPED
        )
        return data, result
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la riduzione possibile per user stories."""
        return 60.0  # Rimozione di ~60% dei metadati


class RepositoryListCleaner(CleaningStrategy):
    """
    Pulisce liste di repository mantenendo solo identificatori essenziali.
    
    Problema risolto: Code_list_repositories restituisce molti dettagli
    per ogni repo, ma spesso servono solo id, name e description.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config:
            self.config = config
        else:
            self.config = _load_cleaning_config().get("RepositoryListCleaner", {})
    
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Identifica se può pulire repository lists."""
        logger.debug(f"RepositoryListCleaner.can_clean() invoked with tool_name='{tool_name}', data_type={type(data)}")
        
        can_clean_result = (
            "code_list_repositories" in tool_name.lower() or
            "list_repositories" in tool_name.lower() or
            self._contains_repositories(data)
        )
        
        logger.debug(f"RepositoryListCleaner.can_clean() result: {can_clean_result}")
        return can_clean_result
    
    def _contains_repositories(self, data: Any) -> bool:
        """Verifica se i dati contengono repository."""
        if isinstance(data, list) and data:
            first_item = data[0] if data else {}
            return isinstance(first_item, dict) and any(
                key in first_item for key in ['repository_id', 'repo_id', 'name', 'description']
            )
        return False
    
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """Pulisce repository list mantenendo solo campi essenziali."""
        logger.debug(f"RepositoryListCleaner.clean() invoked with data_type={type(data)}, context={context}")
        
        if not isinstance(data, list):
            logger.debug("RepositoryListCleaner.clean() - data is not a list, skipping cleaning")
            return self._no_cleaning_result(data)
        
        logger.debug(f"RepositoryListCleaner.clean() - cleaning {len(data)} repositories")
        cleaned = [self._clean_single_repository(repo) for repo in data if isinstance(repo, dict)]
        
        result = CleaningResult.from_data(
            data, cleaned, "RepositoryListCleaner", CleaningStatus.COMPLETED
        )
        result.metadata = {
            "repositories_cleaned": len(cleaned),
            "original_repositories": len(data)
        }
        
        logger.debug(f"RepositoryListCleaner.clean() completed - original_repositories={result.metadata['original_repositories']}, repositories_cleaned={result.metadata['repositories_cleaned']}")
        return cleaned, result
    
    def _clean_single_repository(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Pulisce un singolo repository."""
        essential_fields = ['repository_id', 'repo_id', 'id', 'name', 'description']
        
        cleaned = {}
        for field in essential_fields:
            if field in repo:
                cleaned[field] = repo[field]
        
        # Se non ha repository_id ma ha id, lo rinomina
        if 'repository_id' not in cleaned and 'id' in cleaned:
            cleaned['repository_id'] = cleaned['id']
        
        return cleaned
    
    def _no_cleaning_result(self, data: Any) -> Tuple[Any, CleaningResult]:
        """Restituisce risultato quando non è possibile pulire."""
        result = CleaningResult.from_data(
            data, data, "RepositoryListCleaner", CleaningStatus.SKIPPED
        )
        return data, result
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la riduzione possibile per repositories."""
        return 50.0  # Rimozione di ~50% dei metadati


# Registry delle strategie di pulizia per facile registrazione
CLEANING_STRATEGIES = [
    ProjectListCleaner,
    CodeSnippetCleaner, 
    DocumentCleaner,
    UserStoryListCleaner,
    RepositoryListCleaner
]


def create_default_cleaning_strategies(config: Dict[str, Any] = None) -> List[CleaningStrategy]:
    """
    Crea le strategie di pulizia predefinite con configurazione opzionale.
    
    Args:
        config: Configurazione per le strategie
    
    Returns:
        Lista di strategie di pulizia configurate
    """
    logger.debug(f"create_default_cleaning_strategies() invoked with config={config}")
    
    strategies = []
    
    for strategy_class in CLEANING_STRATEGIES:
        strategy_config = {}
        
        if config and hasattr(strategy_class, '__name__'):
            strategy_name = strategy_class.__name__
            strategy_config = config.get(strategy_name, {})
        
        strategy_instance = strategy_class(strategy_config)
        strategies.append(strategy_instance)
        logger.debug(f"Created cleaning strategy: {strategy_class.__name__}")
    
    logger.debug(f"create_default_cleaning_strategies() completed - created {len(strategies)} strategies")
    return strategies