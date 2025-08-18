"""
Integrazione del sistema di compattazione automatica con compact-implementation di Claude Code

Questo modulo implementa l'integrazione tra il nostro sistema di context management
e le specifiche di compattazione di Claude Code, garantendo compatibilità completa
con il workflow di summarize_task e continuation prompts.

Funzionalità principali:
1. Compattazione automatica quando il contesto raggiunge la soglia
2. Integrazione con summarize_task tool di Claude Code
3. Generazione di continuation prompts compatibili
4. Preservazione del contesto tecnico essenziale
5. Supporto per trigger manuali (/compact, /smol)

Compatibilità: 100% con compact-implementation.md specifications
"""

import json
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .context_manager import ContextManager, ContextMetrics, CompactTrigger
# DISABLED: MCPToolWrapper no longer needed with simplified approach
# from ..integrations.mcp.mcp_wrapper import MCPToolWrapper

# Check LLM compression availability (lazy import to avoid circular imports)
try:
    import langchain_anthropic
    LLM_COMPRESSION_AVAILABLE = True
except ImportError as e:
    LLM_COMPRESSION_AVAILABLE = False
    logging.warning(f"⚠️ LLM compression not available: {e}")

# Import config loader for LLM compression settings
try:
    from ..config.config_loader import get_full_config
    CONFIG_LOADER_AVAILABLE = True
except ImportError:
    CONFIG_LOADER_AVAILABLE = False
    logging.warning("⚠️ Config loader not available")


@dataclass
class CompactSummary:
    """Risultato di una compattazione del contesto."""
    session_id: str
    trigger_type: CompactTrigger
    summary_content: str
    before_metrics: ContextMetrics
    after_metrics: ContextMetrics
    preserved_elements: List[str]
    technical_concepts: List[str]
    pending_tasks: List[str]
    current_work: Optional[str]
    next_steps: List[str]
    timestamp: str
    
    @property
    def total_reduction_percentage(self) -> float:
        """Calcola la riduzione percentuale totale."""
        before_tokens = self.before_metrics.tokens_used
        after_tokens = self.after_metrics.tokens_used
        
        if before_tokens == 0:
            return 0.0
            
        return round((before_tokens - after_tokens) / before_tokens * 100, 2)


class CompactIntegration:
    """
    Sistema di integrazione per compattazione automatica compatibile con Claude Code.
    
    Questo sistema:
    1. Monitora continuamente le metriche del contesto
    2. Attiva compattazione quando necessario
    3. Genera summary compatibili con Claude Code format
    4. Crea continuation prompts standard
    5. Preserva informazioni tecniche essenziali
    """
    
    def __init__(self, context_manager: ContextManager, model_name: str = None):
        self.context_manager = context_manager
        self.model_name = model_name  # For accurate LiteLLM token counting
        # DISABLED: mcp_wrapper no longer needed with simplified approach
        # self.mcp_wrapper = mcp_wrapper
        self.compact_history: List[CompactSummary] = []
        self.last_check_time = time.time()
        
        # Template per summary generation (compatibile con Claude Code)
        self.summary_template = self._load_summary_template()
        
        # Initialize LLM compressor if available and configured
        self.llm_compressor = None
        self.llm_config = None
        self.use_llm_compression = False
        
        if LLM_COMPRESSION_AVAILABLE and CONFIG_LOADER_AVAILABLE:
            try:
                self.llm_config = self._load_llm_compression_config()
                if self.llm_config and self.llm_config.get('enabled', False):
                    self.llm_compressor = self._initialize_llm_compressor()
                    self.use_llm_compression = True
                    logging.info("✅ LLM compression initialized successfully")
            except Exception as e:
                logging.warning(f"⚠️ Failed to initialize LLM compression: {e}")
                self.use_llm_compression = False
    
    def _load_summary_template(self) -> str:
        """Carica il template per generazione summary compatibile con Claude Code."""
        return """
## Context Compression Summary

The context has been automatically compressed to manage token limits.
The conversation is summarized below:

## Previous Conversation Summary

### 1. Primary Request and Intent
{primary_request}

### 2. Key Technical Concepts
{technical_concepts}

### 3. Files and Code Sections
{files_and_code}

### 4. Problem Solving
{problem_solving}

### 5. Pending Tasks
{pending_tasks}

### 6. Current Work
{current_work}

### 7. Next Steps
{next_steps}

## Context Optimization Summary
- **Context reduction achieved**: {reduction_percentage}%
- **Essential data preserved**: {preserved_elements_count} elements
- **Token-based compression**: Simplified architecture without noise detection

## Continuation Instructions

The assistant should continue naturally from this compressed context.
All essential information has been preserved in the summary above.
"""
    
    def _load_llm_compression_config(self) -> Optional[Dict[str, Any]]:
        """Carica configurazione per LLM compression dal YAML."""
        try:
            full_config = get_full_config()
            # Handle both dict and object access
            if hasattr(full_config, 'llm_compression'):
                return full_config.llm_compression
            elif hasattr(full_config, 'get'):
                return full_config.get('llm_compression', {})
            elif hasattr(full_config, '__dict__'):
                return getattr(full_config, 'llm_compression', {})
            else:
                logging.warning("Unknown config format, returning empty config")
                return {}
        except Exception as e:
            logging.error(f"Failed to load LLM compression config: {e}")
            return None
    
    def _initialize_llm_compressor(self) -> Optional[Any]:
        """Inizializza LLMCompressor con configurazione dedicata."""
        try:
            # Import here to avoid circular imports
            from .llm_compression import LLMCompressor, CompressionStrategy
            
            # Get model configuration from env variables
            model_name = os.getenv('COMPRESSION_MODEL', self.llm_config.get('model_name', 'claude-3-haiku-20240307'))
            api_key = os.getenv('COMPRESSION_MODEL_API_KEY', os.getenv('ANTHROPIC_API_KEY'))
            
            if not api_key:
                logging.error("No API key found for compression model")
                return None
            
            # Initialize the compression model
            model = ChatAnthropic(
                model_name=model_name,
                api_key=api_key,
                temperature=0,  # For consistent compression results
                max_tokens=self.llm_config.get('max_output_tokens', 3000),
                timeout=self.llm_config.get('timeout_seconds', 10)
            )
            
            # Create compression configuration
            compression_config = CompressionConfig(
                strategy=CompressionStrategy[self.llm_config.get('strategy', 'BALANCED').upper()],
                target_reduction_percentage=self.llm_config.get('target_reduction_percentage', 60.0),
                max_output_tokens=self.llm_config.get('max_output_tokens', 3000),
                preserve_last_n_messages=3,  # Always preserve recent context
                compression_timeout=self.llm_config.get('timeout_seconds', 10),
                enable_fallback=self.llm_config.get('fallback_to_pattern', True)
            )
            
            return LLMCompressor(
                model=model,
                config=compression_config,
                context_manager=self.context_manager
            )
            
        except Exception as e:
            logging.error(f"Failed to initialize LLM compressor: {e}")
            return None
    
    def should_trigger_compaction(self, messages: List[Dict[str, Any]], trigger_type: str = "standard", 
                                model_name: str = None, tools: List = None) -> Tuple[bool, CompactTrigger, ContextMetrics]:
        """
        Determina se dovrebbe essere attivata la compattazione usando il sistema semplificato.
        Compatibile con compact-implementation.md logic.
        
        Args:
            messages: Messaggi del contesto corrente
            trigger_type: Tipo di trigger ("standard" o "post_tool")
            model_name: Nome modello per token counting accurato
            tools: Lista tool disponibili
        
        Returns:
            Tupla (should_compact, trigger_type, metrics)
        """
        # Use model_name from constructor if not provided
        model_for_counting = model_name or self.model_name
        
        # Analizza contesto corrente con LiteLLM token counting
        metrics = self.context_manager.analyze_context(messages, model_for_counting, tools)
        
        # Use simplified context manager API for threshold checking
        if trigger_type == "post_tool":
            should_compact = metrics.should_trigger_post_tool()
            trigger_reason = CompactTrigger.POST_TOOL
        else:
            should_compact = metrics.should_trigger_compact()
            trigger_reason = CompactTrigger.CONTEXT_SIZE
        
        if should_compact:
            return True, trigger_reason, metrics
        
        # Nessuna compattazione necessaria
        return False, CompactTrigger.MANUAL, metrics
    
    def generate_summary(self, 
                        messages: List[Dict[str, Any]], 
                        trigger_type: CompactTrigger,
                        context: Dict[str, Any] = None) -> CompactSummary:
        """
        Genera un summary completo del contesto per compattazione.
        
        Args:
            messages: Messaggi da summarizzare
            trigger_type: Tipo di trigger che ha attivato la compattazione
            context: Contesto aggiuntivo per la generazione
        
        Returns:
            Summary completo pronto per continuation
        """
        before_metrics = self.context_manager.analyze_context(messages)
        
        # 1. Messages pass through unchanged (simplified architecture, no cleaning needed)
        cleaned_messages = messages
        
        # 2. Analizza il contenuto per estrazione informazioni
        analysis = self._analyze_conversation_content(cleaned_messages)
        
        # 3. Genera il summary usando il template
        summary_content = self._generate_summary_content(analysis, before_metrics)
        
        # 4. Crea prompt di continuation
        continuation_messages = self._create_continuation_messages(summary_content, cleaned_messages)
        
        after_metrics = self.context_manager.analyze_context(continuation_messages)
        
        # 5. Crea oggetto CompactSummary
        compact_summary = CompactSummary(
            session_id=self.context_manager.session_id,
            trigger_type=trigger_type,
            summary_content=summary_content,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            preserved_elements=analysis.get("preserved_elements", []),
            technical_concepts=analysis.get("technical_concepts", []),
            pending_tasks=analysis.get("pending_tasks", []),
            current_work=analysis.get("current_work"),
            next_steps=analysis.get("next_steps", []),
            timestamp=datetime.now().isoformat()
        )
        
        # 6. Salva nella cronologia
        self.compact_history.append(compact_summary)
        
        return compact_summary
    
    def _get_message_field(self, message, field: str, default=None):
        """Helper to safely get fields from both dict messages and LangChain message objects."""
        if hasattr(message, field):
            # LangChain message object - use attribute access
            return getattr(message, field, default)
        elif isinstance(message, dict):
            # Dictionary message - use dict access
            return message.get(field, default)
        else:
            # Unknown message type
            return default
    
    def _get_message_role(self, message) -> str:
        """Get the role from a message, handling both dict and LangChain message objects."""
        if hasattr(message, 'type'):
            # LangChain message object - map type to role
            message_type = message.type
            role_mapping = {
                'human': 'user',
                'ai': 'assistant', 
                'tool': 'tool',
                'system': 'system'
            }
            return role_mapping.get(message_type, "unknown")
        elif isinstance(message, dict):
            # Dictionary message - get role directly
            return message.get("role", "unknown")
        else:
            # Unknown message type
            return "unknown"

    def _analyze_conversation_content(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizza contenuto usando LLM se disponibile, altrimenti pattern-matching."""
        
        # Usa LLM se disponibile e configurato
        if self.use_llm_compression and self.llm_compressor:
            try:
                return self._analyze_with_llm(messages)
            except Exception as e:
                logging.warning(f"⚠️ LLM analysis failed, falling back to patterns: {e}")
        
        # Fallback a pattern-matching esistente
        return self._analyze_with_patterns(messages)
    
    def _analyze_with_patterns(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisi pattern-based (metodo originale rinominato)."""
        analysis = {
            "primary_request": [],
            "technical_concepts": set(),
            "files_and_code": [],
            "problem_solving": [],
            "pending_tasks": [],
            "current_work": None,
            "next_steps": [],
            "preserved_elements": []
        }
        
        for i, message in enumerate(messages):
            content = json.dumps(message, default=str)
            role = self._get_message_role(message)
            
            # Identifica richieste primarie (messaggi user)
            if role == "user":
                analysis["primary_request"].append(self._extract_user_request(message))
            
            # Estrae concetti tecnici
            tech_concepts = self._extract_technical_concepts(content)
            analysis["technical_concepts"].update(tech_concepts)
            
            # Identifica file e codice
            files_mentioned = self._extract_file_references(content)
            analysis["files_and_code"].extend(files_mentioned)
            
            # Identifica problem solving
            if self._contains_problem_solving(content):
                analysis["problem_solving"].append(self._extract_problem_context(message, i))
            
            # Estrae pending tasks
            tasks = self._extract_tasks(content)
            analysis["pending_tasks"].extend(tasks)
            
            # Identifica lavoro corrente (ultimi messaggi)
            if i >= len(messages) - 3:  # Ultimi 3 messaggi
                current_work = self._extract_current_work(message)
                if current_work:
                    analysis["current_work"] = current_work
        
        # Converte set in list per serializzazione
        analysis["technical_concepts"] = list(analysis["technical_concepts"])
        
        # Identifica next steps dai task e dal contesto
        analysis["next_steps"] = self._identify_next_steps(analysis)
        
        return analysis
    
    def _analyze_with_llm(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisi semantica profonda con LLM per software design."""
        
        try:
            # Prepara il prompt specializzato per software design
            analysis_prompt = self._build_software_design_analysis_prompt(messages)
            
            # Usa LLM per analisi semantica
            from langchain_core.messages import HumanMessage
            response = self.llm_compressor.model.invoke([
                HumanMessage(content=analysis_prompt)
            ])
            
            # Parse della risposta LLM in formato strutturato
            llm_analysis = self._parse_llm_analysis_response(response.content)
            
            # Log per monitoring
            logging.info(f"✅ LLM analysis completed: {len(llm_analysis.get('primary_request', []))} requests, "
                        f"{len(llm_analysis.get('technical_concepts', []))} concepts identified")
            
            return llm_analysis
            
        except Exception as e:
            logging.error(f"❌ LLM analysis failed: {e}")
            raise e
    
    def _build_software_design_analysis_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Costruisce prompt specializzato per analisi software design."""
        
        # Prepara la conversazione per l'analisi
        conversation_text = self._prepare_conversation_for_llm_analysis(messages)
        
        prompt = f"""You are a software architecture expert analyzing a conversation about software design and development.

CONTEXT: This is a conversation between users and an AI assistant working on software design from user stories and architectural guidelines. Extract detailed information for context compression while preserving all critical software design elements.

ANALYZE AND EXTRACT:

1. **PRIMARY REQUESTS**: Main user goals and business requirements
   - What the user wants to achieve (business goals)
   - Core functionality being designed/implemented
   - User stories and their intent

2. **TECHNICAL CONCEPTS**: Technologies, frameworks, patterns mentioned or implied
   - Programming languages, frameworks, libraries
   - Architectural patterns (microservices, MVC, etc.)
   - Infrastructure and deployment technologies
   - APIs, databases, external services

3. **ARCHITECTURAL REQUIREMENTS**: Non-functional requirements (explicit and implicit)
   - Security requirements (authentication, encryption, compliance)
   - Performance requirements (scalability, response times)
   - Reliability requirements (availability, fault tolerance)
   - Maintainability requirements (testing, documentation)

4. **FILES & CODE**: Specific files, modules, or code sections discussed
   - File paths and their purposes
   - Code modules and their responsibilities
   - Configuration files and settings

5. **DEPENDENCIES**: Cross-component dependencies and integration points
   - Service-to-service communications
   - Data flow between components
   - External system integrations
   - Shared resources and databases

6. **DESIGN DECISIONS**: Architecture choices and technical trade-offs made
   - Technology stack choices and rationale
   - Pattern selections (e.g., Observer, Factory, Repository)
   - Database design decisions
   - API design choices

7. **RISK AREAS**: Potential technical debt and complexity hotspots
   - Areas that might need refactoring
   - Performance bottlenecks
   - Security vulnerabilities
   - Maintainability concerns

8. **CURRENT WORK**: What's actively being worked on
   - Current development focus
   - Work in progress
   - Recent completions

9. **NEXT STEPS**: Pending tasks and immediate priorities
   - TODO items and action items
   - Planned implementations
   - Testing requirements

IMPORTANT INSTRUCTIONS:
- Focus on SOFTWARE DESIGN context - prioritize architectural and technical information
- Extract IMPLICIT requirements (e.g., "user-friendly" → UX requirements, accessibility)
- Identify cross-references between user stories and technical components
- Preserve all identifiers (project IDs, entity IDs, file paths)
- Note security and performance implications

Return the analysis as a valid JSON object with this exact structure:
{{
    "primary_request": [list of main business goals/user stories],
    "technical_concepts": [list of technologies, frameworks, patterns],
    "architectural_requirements": [list of non-functional requirements with details],
    "files_and_code": [{{"path": "string", "purpose": "string", "context": "string"}}],
    "dependencies": [{{"from": "string", "to": "string", "type": "string", "description": "string"}}],
    "design_decisions": [list of architecture choices with rationale],
    "risk_areas": [{{"area": "string", "risk": "string", "impact": "string"}}],
    "problem_solving": [list of issues being solved],
    "pending_tasks": [list of tasks to be completed],
    "current_work": "current focus description",
    "next_steps": [list of immediate next actions],
    "preserved_elements": [list of critical elements to preserve]
}}

CONVERSATION TO ANALYZE:
{conversation_text}

Provide the JSON analysis:"""

        return prompt
    
    def _prepare_conversation_for_llm_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """Prepara la conversazione per analisi LLM."""
        conversation_lines = []
        
        for i, message in enumerate(messages):
            role = self._get_message_role(message)
            content = str(self._get_message_field(message, "content", ""))
            
            # Limita la lunghezza del contenuto per gestire token limits
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"
            
            conversation_lines.append(f"[{role.upper()}]: {content}")
        
        return "\n\n".join(conversation_lines)
    
    def _parse_llm_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse della risposta LLM in formato strutturato."""
        try:
            # Cerca JSON nella risposta
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                analysis = json.loads(json_text)
                
                # Converti set in list e valida struttura
                return self._validate_and_normalize_llm_analysis(analysis)
            else:
                logging.warning("No JSON found in LLM response, using fallback parsing")
                return self._fallback_parse_llm_response(response_text)
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in LLM response: {e}")
            return self._fallback_parse_llm_response(response_text)
        except Exception as e:
            logging.error(f"Error parsing LLM response: {e}")
            raise e
    
    def _validate_and_normalize_llm_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e normalizza l'analisi LLM per compatibilità."""
        
        # Assicura che tutti i campi richiesti esistano
        required_fields = [
            "primary_request", "technical_concepts", "files_and_code",
            "problem_solving", "pending_tasks", "current_work", "next_steps",
            "preserved_elements"
        ]
        
        for field in required_fields:
            if field not in analysis:
                analysis[field] = []
        
        # Converte set in list se necessario
        if isinstance(analysis.get("technical_concepts"), set):
            analysis["technical_concepts"] = list(analysis["technical_concepts"])
        
        # Assicura che current_work sia stringa
        if not isinstance(analysis.get("current_work"), str):
            analysis["current_work"] = str(analysis.get("current_work", ""))
        
        return analysis
    
    def _fallback_parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing se JSON parsing fallisce."""
        return {
            "primary_request": [response_text[:200] + "..."],
            "technical_concepts": [],
            "files_and_code": [],
            "problem_solving": [],
            "pending_tasks": [],
            "current_work": "LLM analysis parsing failed",
            "next_steps": ["Review LLM response parsing"],
            "preserved_elements": []
        }
    
    def _extract_user_request(self, message: Dict[str, Any]) -> str:
        """Estrae la richiesta dell'utente da un messaggio."""
        content = self._get_message_field(message, "content", "")
        if isinstance(content, str):
            # Prende la prima riga significativa
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            return lines[0] if lines else content[:100]
        return str(content)[:100]
    
    def _extract_technical_concepts(self, content: str) -> set:
        """Estrae concetti tecnici dal contenuto."""
        concepts = set()
        
        # Pattern per identificare tecnologie, framework, linguaggi
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|React|Vue|Angular|Node\.js|Django|Flask|FastAPI)\b',
            r'\b(Docker|Kubernetes|AWS|Azure|GCP|MongoDB|PostgreSQL|MySQL)\b',
            r'\b(Git|GitHub|GitLab|CI/CD|DevOps|API|REST|GraphQL|JSON|XML)\b',
            r'\b(LangGraph|LangChain|OpenAI|Anthropic|Claude|GPT|LLM|AI|ML)\b',
            r'\b(MCP|tools?|agent|prompt|context|token)\b'
        ]
        
        import re
        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            concepts.update(match.lower() for match in matches)
        
        return concepts
    
    def _extract_file_references(self, content: str) -> List[Dict[str, Any]]:
        """Estrae riferimenti a file dal contenuto."""
        files = []
        
        # Pattern per file mentions
        import re
        file_patterns = [
            r'`([^`]+\.(py|js|ts|jsx|tsx|json|yaml|yml|md|txt))`',
            r'"([^"]+\.(py|js|ts|jsx|tsx|json|yaml|yml|md|txt))"',
            r"'([^']+\.(py|js|ts|jsx|tsx|json|yaml|yml|md|txt))'",
            r'\b([a-zA-Z_][a-zA-Z0-9_/]*\.(py|js|ts|jsx|tsx|json|yaml|yml|md|txt))\b'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                file_path = match[0] if isinstance(match, tuple) else match
                files.append({"path": file_path, "context": "mentioned"})
        
        return files
    
    def _contains_problem_solving(self, content: str) -> bool:
        """Determina se il contenuto contiene problem solving."""
        problem_indicators = [
            "error", "bug", "issue", "problem", "fix", "solve",
            "debug", "troubleshoot", "exception", "fail"
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in problem_indicators)
    
    def _extract_problem_context(self, message: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Estrae il contesto di problem solving."""
        return {
            "message_index": index,
            "content_preview": str(self._get_message_field(message, "content", ""))[:200],
            "role": self._get_message_role(message)
        }
    
    def _extract_tasks(self, content: str) -> List[str]:
        """Estrae task dal contenuto."""
        tasks = []
        
        # Pattern per identificare task
        import re
        task_patterns = [
            r'TODO:?\s*([^\n]+)',
            r'Task:?\s*([^\n]+)',
            r'\d+\.\s*([^\n]+)',
            r'[-*]\s*([^\n]+)'
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            tasks.extend(matches)
        
        return tasks[:5]  # Limita a 5 task per evitare rumore
    
    def _extract_current_work(self, message: Dict[str, Any]) -> Optional[str]:
        """Estrae il lavoro corrente da un messaggio recente."""
        content = str(self._get_message_field(message, "content", ""))
        
        # Se è un messaggio di assistant con azioni
        if self._get_message_role(message) == "assistant" and len(content) > 50:
            # Cerca pattern di azioni in corso
            action_patterns = [
                r'(Creating|Building|Implementing|Writing|Updating|Adding)\s+([^\n]+)',
                r'(Working on|Focusing on|Currently)\s+([^\n]+)',
                r'(I\'m|I am)\s+(creating|building|implementing|writing|updating|adding)\s+([^\n]+)'
            ]
            
            import re
            for pattern in action_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(0)
        
        return None
    
    def _identify_next_steps(self, analysis: Dict[str, Any]) -> List[str]:
        """Identifica i next steps basandosi sull'analisi."""
        next_steps = []
        
        # Da pending tasks
        if analysis["pending_tasks"]:
            next_steps.extend(analysis["pending_tasks"][:3])
        
        # Da current work
        if analysis["current_work"]:
            next_steps.append(f"Continue: {analysis['current_work']}")
        
        # Steps generici se non ci sono altri
        if not next_steps:
            next_steps = [
                "Review current progress",
                "Continue with main task",
                "Address any pending issues"
            ]
        
        return next_steps[:5]  # Massimo 5 steps
    
    def _generate_summary_content(self, analysis: Dict[str, Any], metrics: ContextMetrics) -> str:
        """Genera il contenuto del summary usando il template."""
        
        # Prepara i dati per il template
        template_data = {
            "primary_request": self._format_primary_requests(analysis["primary_request"]),
            "technical_concepts": self._format_technical_concepts(analysis["technical_concepts"]),
            "files_and_code": self._format_files_and_code(analysis["files_and_code"]),
            "problem_solving": self._format_problem_solving(analysis["problem_solving"]),
            "pending_tasks": self._format_pending_tasks(analysis["pending_tasks"]),
            "current_work": analysis["current_work"] or "No specific current work identified",
            "next_steps": self._format_next_steps(analysis["next_steps"]),
            "reduction_percentage": 0,  # Sarà calcolato dopo
            "mcp_noise_reduction": 0,  # MCP noise detection disabled in simplified architecture
            "preserved_elements_count": len(analysis.get("preserved_elements", []))
        }
        
        return self.summary_template.format(**template_data)
    
    def _format_primary_requests(self, requests: List[str]) -> str:
        """Formatta le richieste primarie."""
        if not requests:
            return "No specific primary requests identified."
        
        formatted = []
        for i, request in enumerate(requests[:3], 1):
            formatted.append(f"{i}. {request}")
        
        return "\n".join(formatted)
    
    def _format_technical_concepts(self, concepts: List[str]) -> str:
        """Formatta i concetti tecnici."""
        if not concepts:
            return "No specific technical concepts identified."
        
        # Raggruppa per categoria
        categories = {
            "Languages & Frameworks": [],
            "Tools & Platforms": [],
            "AI & ML": [],
            "Other": []
        }
        
        ai_terms = ["langraph", "langchain", "openai", "anthropic", "claude", "gpt", "llm", "ai", "ml", "mcp"]
        tool_terms = ["docker", "kubernetes", "aws", "azure", "gcp", "git", "github", "gitlab"]
        lang_terms = ["python", "javascript", "typescript", "react", "vue", "angular", "node.js"]
        
        for concept in concepts:
            concept_lower = concept.lower()
            if concept_lower in ai_terms:
                categories["AI & ML"].append(concept)
            elif concept_lower in tool_terms:
                categories["Tools & Platforms"].append(concept)
            elif concept_lower in lang_terms:
                categories["Languages & Frameworks"].append(concept)
            else:
                categories["Other"].append(concept)
        
        formatted = []
        for category, items in categories.items():
            if items:
                formatted.append(f"**{category}**: {', '.join(items)}")
        
        return "\n".join(formatted) if formatted else "No specific technical concepts identified."
    
    def _format_files_and_code(self, files: List[Dict[str, Any]]) -> str:
        """Formatta file e codice."""
        if not files:
            return "No specific files identified."
        
        file_paths = set()
        for file_info in files:
            file_paths.add(file_info.get("path", "unknown"))
        
        formatted = []
        for i, path in enumerate(sorted(file_paths)[:10], 1):
            formatted.append(f"{i}. {path}")
        
        return "\n".join(formatted)
    
    def _format_problem_solving(self, problems: List[Dict[str, Any]]) -> str:
        """Formatta problem solving."""
        if not problems:
            return "No specific problems or debugging identified."
        
        formatted = []
        for i, problem in enumerate(problems[:3], 1):
            preview = problem.get("content_preview", "")[:100]
            formatted.append(f"{i}. {preview}...")
        
        return "\n".join(formatted)
    
    def _format_pending_tasks(self, tasks: List[str]) -> str:
        """Formatta pending tasks."""
        if not tasks:
            return "No specific pending tasks identified."
        
        formatted = []
        for i, task in enumerate(tasks[:5], 1):
            formatted.append(f"{i}. {task}")
        
        return "\n".join(formatted)
    
    def _format_next_steps(self, steps: List[str]) -> str:
        """Formatta next steps."""
        if not steps:
            return "Continue with the current conversation flow."
        
        formatted = []
        for i, step in enumerate(steps, 1):
            formatted.append(f"{i}. {step}")
        
        return "\n".join(formatted)
    
    def _create_continuation_messages(self, summary_content: str, original_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crea messaggi di continuation compatibili con Claude Code."""
        
        # Messaggio di sistema con summary
        system_message = {
            "role": "system",
            "content": summary_content
        }
        
        # Mantiene l'ultimo messaggio utente se presente
        last_user_message = None
        for message in reversed(original_messages):
            if self._get_message_role(message) == "user":
                last_user_message = message
                break
        
        continuation_messages = [system_message]
        if last_user_message:
            continuation_messages.append(last_user_message)
        
        return continuation_messages
    
    def perform_automatic_compaction(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], CompactSummary]:
        """
        Esegue compattazione automatica completa.
        
        Args:
            messages: Messaggi da compattare
            context: Contesto aggiuntivo
        
        Returns:
            Tupla (messaggi_compattati, summary_info)
        """
        # Determina trigger type
        should_compact, trigger_type, metrics = self.should_trigger_compaction(messages)
        
        if not should_compact:
            # Nessuna compattazione necessaria
            summary = CompactSummary(
                session_id=self.context_manager.session_id,
                trigger_type=CompactTrigger.MANUAL,
                summary_content="No compaction needed",
                before_metrics=metrics,
                after_metrics=metrics,
                preserved_elements=[],
                technical_concepts=[],
                pending_tasks=[],
                current_work=None,
                next_steps=[],
                timestamp=datetime.now().isoformat()
            )
            return messages, summary
        
        # Genera summary
        summary = self.generate_summary(messages, trigger_type, context)
        
        # Crea messaggi compattati
        compacted_messages = self._create_continuation_messages(
            summary.summary_content, messages
        )
        
        # Aggiorna metriche after
        summary.after_metrics = self.context_manager.analyze_context(compacted_messages)
        
        return compacted_messages, summary
    
    def get_compaction_statistics(self) -> Dict[str, Any]:
        """Restituisce statistiche delle compattazioni."""
        if not self.compact_history:
            return {"total_compactions": 0}
        
        total_reductions = [s.total_reduction_percentage for s in self.compact_history]
        avg_reduction = sum(total_reductions) / len(total_reductions)
        
        trigger_counts = {}
        for summary in self.compact_history:
            trigger = summary.trigger_type
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        return {
            "total_compactions": len(self.compact_history),
            "average_reduction_percentage": round(avg_reduction, 2),
            "trigger_breakdown": trigger_counts,
            "latest_compaction": self.compact_history[-1].timestamp if self.compact_history else None
        }


# Alias per compatibilità con il sistema di compressione esistente
# Il refactoring precedente ha integrato le funzionalità di EnhancedCompactIntegration
# in CompactIntegration, quindi utilizziamo un alias per mantenere la compatibilità
EnhancedCompactIntegration = CompactIntegration