"""
Context Manager per DeepAgents - Sistema di gestione intelligente del contesto con pulizia MCP

Questo modulo implementa un sistema avanzato per gestire il contesto conversazionale degli agenti,
con particolare focus sulla pulizia automatica del rumore proveniente dai tool MCP.

Funzionalità principali:
- Tracking automatico delle metriche del contesto
- Compattazione intelligente quando si raggiunge la soglia
- Strategie di pulizia specifiche per ogni tipo di tool MCP
- Integrazione seamless con LangGraph state management
- Deduplicazione automatica di informazioni ridondanti

Ispirato dalle specifiche di Claude Code compact-implementation per massima compatibilità.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from enum import Enum

try:
    import tiktoken  # Per conteggio token preciso
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class CompactTrigger(str, Enum):
    """Tipi di trigger per la compattazione del contesto."""
    MANUAL = "manual"
    AUTOMATIC = "automatic" 
    THRESHOLD = "threshold"
    MCP_NOISE = "mcp_noise"


class CleaningStatus(str, Enum):
    """Stato delle operazioni di pulizia."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ContextMetrics:
    """Metriche dettagliate del contesto conversazionale."""
    tokens_used: int
    max_context_window: int
    utilization_percentage: float
    trigger_threshold: float = 0.85
    mcp_noise_percentage: float = 0.0
    deduplication_potential: float = 0.0
    
    @property
    def should_trigger_compact(self) -> bool:
        """Determina se deve essere attivata la compattazione."""
        return (
            self.utilization_percentage >= self.trigger_threshold or 
            self.mcp_noise_percentage > 0.6
        )
    
    @property
    def is_near_limit(self) -> bool:
        """Indica se siamo vicini al limite del contesto."""
        return self.utilization_percentage >= 0.70


@dataclass
class CleaningResult:
    """Risultato di un'operazione di pulizia."""
    original_size: int
    cleaned_size: int
    reduction_percentage: float
    strategy_used: str
    cleaning_status: CleaningStatus
    preserved_fields: List[str]
    removed_fields: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_data(cls, original: Any, cleaned: Any, strategy: str, status: CleaningStatus) -> 'CleaningResult':
        """Crea un CleaningResult dal confronto di dati originali e puliti."""
        original_size = len(json.dumps(original, default=str)) if original else 0
        cleaned_size = len(json.dumps(cleaned, default=str)) if cleaned else 0
        
        reduction = ((original_size - cleaned_size) / original_size * 100) if original_size > 0 else 0
        
        # Estrae i campi preservati e rimossi se possibile
        preserved_fields = []
        removed_fields = []
        
        if isinstance(original, dict) and isinstance(cleaned, dict):
            preserved_fields = list(cleaned.keys())
            removed_fields = [k for k in original.keys() if k not in cleaned.keys()]
        
        return cls(
            original_size=original_size,
            cleaned_size=cleaned_size,
            reduction_percentage=round(reduction, 2),
            strategy_used=strategy,
            cleaning_status=status,
            preserved_fields=preserved_fields,
            removed_fields=removed_fields
        )


@dataclass 
class ContextInfo:
    """Informazioni storiche sul contesto."""
    session_id: str
    operation_type: str  # "cleaning", "compaction", "deduplication"
    before_metrics: ContextMetrics
    after_metrics: ContextMetrics
    cleaning_results: List[CleaningResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_reduction_percentage(self) -> float:
        """Percentuale totale di riduzione ottenuta."""
        if not self.cleaning_results:
            return 0.0
        
        total_original = sum(r.original_size for r in self.cleaning_results)
        total_cleaned = sum(r.cleaned_size for r in self.cleaning_results)
        
        if total_original == 0:
            return 0.0
            
        return round((total_original - total_cleaned) / total_original * 100, 2)


class CleaningStrategy(ABC):
    """Interfaccia base per le strategie di pulizia."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def can_clean(self, tool_name: str, data: Any) -> bool:
        """Determina se questa strategia può pulire i dati del tool specificato."""
        pass
    
    @abstractmethod
    def clean(self, data: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """Pulisce i dati e restituisce il risultato."""
        pass
    
    def estimate_reduction(self, data: Any) -> float:
        """Stima la percentuale di riduzione possibile."""
        return 0.0


class ContextManager:
    """
    Gestore principale del contesto conversazionale con pulizia intelligente.
    
    Questo sistema:
    1. Monitora le metriche del contesto in tempo reale
    2. Applica strategie di pulizia specifiche per tool MCP
    3. Gestisce la compattazione automatica quando necessario
    4. Mantiene uno storico delle operazioni per analisi
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.cleaning_strategies: List[CleaningStrategy] = []
        self.context_history: List[ContextInfo] = []
        self.session_id = f"ctx_{int(time.time())}"
        
        # Inizializza tokenizer per conteggio preciso
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-4")
            except:
                try:
                    self.tokenizer = tiktoken.get_encoding("cl100k_base")
                except:
                    pass
    
    def _default_config(self) -> Dict[str, Any]:
        """Configurazione predefinita del context manager."""
        return {
            "max_context_window": 200000,
            "trigger_threshold": 0.85,
            "mcp_noise_threshold": 0.6,
            "deduplication_enabled": True,
            "deduplication_similarity": 0.90,
            "preserve_essential_fields": True,
            "auto_compaction": True,
            "logging_enabled": True
        }
    
    def register_cleaning_strategy(self, strategy: CleaningStrategy) -> None:
        """Registra una nuova strategia di pulizia."""
        self.cleaning_strategies.append(strategy)
    
    def count_tokens(self, text: str) -> int:
        """Conta i token in un testo usando tiktoken."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        # Fallback: stima approssimativa
        return len(text) // 4
    
    def analyze_context(self, messages: List[Dict[str, Any]]) -> ContextMetrics:
        """Analizza le metriche del contesto corrente."""
        total_tokens = 0
        mcp_tokens = 0
        
        for message in messages:
            content = json.dumps(message, default=str)
            message_tokens = self.count_tokens(content)
            total_tokens += message_tokens
            
            # Identifica contenuto MCP basandosi sui pattern
            if self._contains_mcp_content(message):
                mcp_tokens += message_tokens
        
        max_window = self.config["max_context_window"]
        utilization = total_tokens / max_window if max_window > 0 else 0
        mcp_noise = mcp_tokens / total_tokens if total_tokens > 0 else 0
        
        return ContextMetrics(
            tokens_used=total_tokens,
            max_context_window=max_window,
            utilization_percentage=round(utilization * 100, 2),
            trigger_threshold=self.config["trigger_threshold"],
            mcp_noise_percentage=round(mcp_noise * 100, 2)
        )
    
    def _contains_mcp_content(self, message: Dict[str, Any]) -> bool:
        """Identifica se un messaggio contiene contenuto MCP."""
        content_str = json.dumps(message, default=str).lower()
        
        mcp_indicators = [
            "general_list_projects",
            "code_find_relevant_code_snippets", 
            "studio_list_",
            "code_get_",
            "general_rag_retrieve",
            "fairmind",
            "project_id",
            "entity_id",
            "repository_id"
        ]
        
        return any(indicator in content_str for indicator in mcp_indicators)
    
    def clean_mcp_tool_result(self, tool_name: str, result: Any, context: Dict[str, Any] = None) -> Tuple[Any, CleaningResult]:
        """
        Pulisce il risultato di un tool MCP usando la strategia appropriata.
        
        Args:
            tool_name: Nome del tool MCP
            result: Risultato del tool da pulire
            context: Contesto aggiuntivo per la pulizia
        
        Returns:
            Tupla (risultato_pulito, informazioni_pulizia)
        """
        # Trova la strategia appropriata
        for strategy in self.cleaning_strategies:
            if strategy.can_clean(tool_name, result):
                return strategy.clean(result, context)
        
        # Nessuna strategia specifica trovata - pulizia generica
        return self._generic_clean(result, tool_name)
    
    def _generic_clean(self, data: Any, tool_name: str) -> Tuple[Any, CleaningResult]:
        """Pulizia generica per tool senza strategia specifica."""
        if isinstance(data, dict):
            # Rimuove campi comuni che generano rumore
            noise_fields = ['metadata', 'internal_id', 'created_at', 'updated_at', 'version']
            cleaned = {k: v for k, v in data.items() if k not in noise_fields}
            
            result = CleaningResult.from_data(
                data, cleaned, "GenericCleaner", CleaningStatus.COMPLETED
            )
            return cleaned, result
        
        # Per dati non-dict, restituisce così come sono
        result = CleaningResult.from_data(
            data, data, "NoCleaningNeeded", CleaningStatus.SKIPPED
        )
        return data, result
    
    def deduplicate_messages(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], CleaningResult]:
        """
        Rimuove messaggi duplicati o molto simili.
        
        Args:
            messages: Lista di messaggi da deduplicare
        
        Returns:
            Tupla (messaggi_deduplicati, informazioni_deduplicazione)
        """
        if not self.config["deduplication_enabled"] or len(messages) < 2:
            result = CleaningResult.from_data(
                messages, messages, "DeduplicationSkipped", CleaningStatus.SKIPPED
            )
            return messages, result
        
        deduplicated = []
        seen_content = set()
        similarity_threshold = self.config["deduplication_similarity"]
        
        for message in messages:
            content_hash = self._get_content_hash(message)
            
            # Controlla duplicati esatti
            if content_hash in seen_content:
                continue
            
            # Controlla similarità con messaggi già visti
            if not self._is_similar_to_existing(message, deduplicated, similarity_threshold):
                deduplicated.append(message)
                seen_content.add(content_hash)
        
        result = CleaningResult.from_data(
            messages, deduplicated, "MessageDeduplication", CleaningStatus.COMPLETED
        )
        result.metadata = {
            "original_count": len(messages),
            "deduplicated_count": len(deduplicated),
            "removed_count": len(messages) - len(deduplicated)
        }
        
        return deduplicated, result
    
    def _get_content_hash(self, message: Dict[str, Any]) -> str:
        """Genera un hash del contenuto di un messaggio."""
        content = json.dumps(message, sort_keys=True, default=str)
        return str(hash(content))
    
    def _is_similar_to_existing(self, message: Dict[str, Any], existing: List[Dict[str, Any]], threshold: float) -> bool:
        """Controlla se un messaggio è simile a quelli esistenti."""
        message_content = json.dumps(message, default=str)
        
        for existing_msg in existing:
            existing_content = json.dumps(existing_msg, default=str)
            
            # Calcola similarità basata su sovrapposizione di caratteri
            similarity = self._calculate_similarity(message_content, existing_content)
            if similarity >= threshold:
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcola la similarità tra due testi."""
        if not text1 or not text2:
            return 0.0
        
        # Usa l'intersezione dei caratteri come metrica di similarità
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def should_trigger_compaction(self, messages: List[Dict[str, Any]]) -> Tuple[bool, CompactTrigger, ContextMetrics]:
        """
        Determina se dovrebbe essere attivata la compattazione.
        
        Args:
            messages: Messaggi del contesto corrente
        
        Returns:
            Tupla (dovrebbe_compattare, tipo_trigger, metriche)
        """
        metrics = self.analyze_context(messages)
        
        # Controllo soglia standard
        if metrics.should_trigger_compact:
            trigger = CompactTrigger.THRESHOLD if metrics.utilization_percentage >= metrics.trigger_threshold else CompactTrigger.MCP_NOISE
            return True, trigger, metrics
        
        return False, CompactTrigger.MANUAL, metrics
    
    def process_context_cleaning(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], ContextInfo]:
        """
        Processo completo di pulizia del contesto.
        
        Args:
            messages: Messaggi da pulire
            context: Contesto aggiuntivo
        
        Returns:
            Tupla (messaggi_puliti, informazioni_operazione)
        """
        before_metrics = self.analyze_context(messages)
        
        cleaned_messages = messages.copy()
        cleaning_results = []
        
        # 1. Pulizia dei risultati MCP
        for i, message in enumerate(cleaned_messages):
            if self._contains_mcp_content(message):
                tool_name = self._extract_tool_name(message)
                if tool_name:
                    cleaned_content, clean_result = self.clean_mcp_tool_result(tool_name, message, context)
                    cleaned_messages[i] = cleaned_content
                    cleaning_results.append(clean_result)
        
        # 2. Deduplicazione
        if self.config["deduplication_enabled"]:
            cleaned_messages, dedup_result = self.deduplicate_messages(cleaned_messages)
            cleaning_results.append(dedup_result)
        
        after_metrics = self.analyze_context(cleaned_messages)
        
        # Crea info sull'operazione
        context_info = ContextInfo(
            session_id=self.session_id,
            operation_type="cleaning",
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            cleaning_results=cleaning_results
        )
        
        # Salva nello storico
        self.context_history.append(context_info)
        
        return cleaned_messages, context_info
    
    def _extract_tool_name(self, message: Dict[str, Any]) -> Optional[str]:
        """Estrae il nome del tool da un messaggio."""
        content_str = json.dumps(message, default=str).lower()
        
        # Pattern per identificare tool MCP
        tool_patterns = [
            r'general_list_projects',
            r'code_find_relevant_code_snippets',
            r'studio_list_\w+',
            r'code_get_\w+',
            r'general_rag_retrieve_\w+'
        ]
        
        for pattern in tool_patterns:
            match = re.search(pattern, content_str)
            if match:
                return match.group(0)
        
        return None
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Genera un sommario delle operazioni di context management."""
        if not self.context_history:
            return {"status": "no_operations", "message": "Nessuna operazione di pulizia eseguita"}
        
        total_operations = len(self.context_history)
        total_reductions = [info.total_reduction_percentage for info in self.context_history]
        avg_reduction = sum(total_reductions) / len(total_reductions) if total_reductions else 0
        
        latest_metrics = self.context_history[-1].after_metrics if self.context_history else None
        
        return {
            "session_id": self.session_id,
            "total_operations": total_operations,
            "average_reduction_percentage": round(avg_reduction, 2),
            "current_utilization": latest_metrics.utilization_percentage if latest_metrics else 0,
            "current_mcp_noise": latest_metrics.mcp_noise_percentage if latest_metrics else 0,
            "strategies_registered": len(self.cleaning_strategies),
            "config": self.config
        }