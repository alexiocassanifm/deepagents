"""
MCP Tool Wrapper con Auto-Cleaning - Intercettore intelligente per tool MCP

Questo modulo implementa un sistema di wrapping automatico per i tool MCP che:
1. Intercetta le chiamate ai tool MCP
2. Applica automaticamente le strategie di pulizia appropriate
3. Aggiorna lo state dell'agente con i risultati puliti
4. Mantiene traccia delle metriche di riduzione del contesto
5. Supporta fallback graceful quando la pulizia fallisce

Il wrapper è trasparente - i tool wrapped mantengono la stessa interfaccia dei tool originali,
ma i risultati vengono automaticamente puliti per ridurre il rumore del contesto.
"""

import asyncio
import json
import time
import inspect
import logging
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import asdict

from context_manager import ContextManager, ContextMetrics, ContextInfo, CleaningResult
from mcp_cleaners import create_default_cleaning_strategies

# Configurazione logging specifico per context tracking
# NON usare basicConfig - usa la configurazione del root logger
context_logger = logging.getLogger("mcp_context_tracker")
context_logger.setLevel(logging.INFO)
context_logger.propagate = True  # Assicurati che propaghi al root logger


class MCPToolWrapper:
    """
    Wrapper per tool MCP che applica automaticamente la pulizia del contesto.
    
    Questo wrapper:
    1. Intercetta le chiamate ai tool MCP
    2. Esegue il tool originale
    3. Applica la strategia di pulizia appropriata al risultato
    4. Aggiorna lo state dell'agente con metriche e risultati puliti
    5. Fornisce fallback graceful in caso di errori
    """
    
    def __init__(self, context_manager: ContextManager, config: Dict[str, Any] = None):
        self.context_manager = context_manager
        self.config = config or {}
        self.wrapped_tools: Dict[str, Any] = {}
        self.call_history: List[Dict[str, Any]] = []
        
        # Statistiche delle operazioni
        self.stats = {
            "total_calls": 0,
            "cleaned_calls": 0,
            "total_reduction_percentage": 0.0,
            "errors": 0
        }
    
    def wrap_tool(self, tool: Any, tool_name: Optional[str] = None) -> Any:
        """
        Wrappa un singolo tool MCP con auto-cleaning.
        
        Args:
            tool: Tool MCP da wrappare
            tool_name: Nome opzionale del tool (se non rilevabile automaticamente)
        
        Returns:
            Tool wrapped con auto-cleaning
        """
        # Estrae il nome del tool se non fornito
        if not tool_name:
            tool_name = self._extract_tool_name(tool)
        
        # Se è un tool callable (function)
        if callable(tool):
            return self._wrap_callable_tool(tool, tool_name)
        
        # Se è un tool object con metodi
        elif hasattr(tool, 'run') or hasattr(tool, '__call__'):
            return self._wrap_tool_object(tool, tool_name)
        
        # Se non riconosciuto, restituisce il tool originale
        else:
            return tool
    
    def wrap_tool_list(self, tools: List[Any]) -> List[Any]:
        """
        Wrappa una lista di tool MCP.
        
        Args:
            tools: Lista di tool da wrappare
        
        Returns:
            Lista di tool wrapped
        """
        wrapped_tools = []
        
        for tool in tools:
            tool_name = self._extract_tool_name(tool)
            
            # Wrappa solo tool MCP riconosciuti
            if self._is_mcp_tool(tool_name):
                wrapped_tool = self.wrap_tool(tool, tool_name)
                wrapped_tools.append(wrapped_tool)
                self.wrapped_tools[tool_name] = wrapped_tool
            else:
                # Tool non-MCP passano attraverso senza modifiche
                wrapped_tools.append(tool)
        
        return wrapped_tools
    
    def _extract_tool_name(self, tool: Any) -> str:
        """Estrae il nome del tool da vari tipi di oggetti tool."""
        # Prova attributi comuni per il nome
        for attr in ['name', '__name__', 'tool_name', '_name']:
            if hasattr(tool, attr):
                name = getattr(tool, attr)
                if isinstance(name, str):
                    return name
        
        # Fallback al nome della classe
        if hasattr(tool, '__class__'):
            return tool.__class__.__name__
        
        # Ultimo fallback
        return str(tool)
    
    def _is_mcp_tool(self, tool_name: str) -> bool:
        """Determina se un tool è un tool MCP basandosi sul nome."""
        mcp_patterns = [
            'general_list_projects',
            'general_list_user_attachments',
            'general_get_document_content',
            'general_rag_retrieve',
            'studio_list_',
            'studio_get_',
            'code_list_',
            'code_get_',
            'code_find_',
            'fairmind'
        ]
        
        tool_name_lower = tool_name.lower()
        return any(pattern in tool_name_lower for pattern in mcp_patterns)
    
    def _wrap_callable_tool(self, tool: Callable, tool_name: str) -> Callable:
        """Wrappa un tool callable (function) preservando completamente la signature."""
        
        # Se il tool è già wrapped, non wrapparlo di nuovo
        if hasattr(tool, '__wrapped__'):
            return tool
        
        # Se è un StructuredTool, wrappa la sua func direttamente  
        if hasattr(tool, '_schema') or 'StructuredTool' in str(type(tool)):
            context_logger.info(f"🔧 WRAPPING StructuredTool: {tool_name}")
            context_logger.info(f"🔧 TOOL TYPE: {type(tool)}")
            context_logger.info(f"🔧 HAS FUNC: {hasattr(tool, 'func')}")
            
            # Wrap the underlying function instead
            if hasattr(tool, 'func'):
                context_logger.info(f"🔧 ACCESSING: tool.func for {tool_name}")
                original_func = tool.func
                context_logger.info(f"🔧 FUNC TYPE: {type(original_func)} for {tool_name}")
                
                try:
                    wrapped_func = self._create_function_wrapper(original_func, tool_name)
                    context_logger.info(f"🔧 WRAPPER CREATED: {tool_name}")
                    tool.func = wrapped_func
                    context_logger.info(f"✅ WRAPPED StructuredTool.func for {tool_name}")
                    return tool
                except Exception as e:
                    context_logger.error(f"❌ FAILED to wrap {tool_name}: {type(e).__name__}: {e}")
                    return tool
            else:
                context_logger.warning(f"⚠️ StructuredTool {tool_name} has no func attribute")
                return tool
        
        try:
            # Cattura la signature originale PRIMA del wrapping
            original_signature = inspect.signature(tool)
        except (ValueError, TypeError):
            # Se non possiamo ottenere la signature, non wrappare
            return tool
        
        @wraps(tool)
        def wrapped_function(*args, **kwargs):
            return self._execute_with_cleaning(tool, tool_name, *args, **kwargs)
        
        # Preserva metadati del tool originale
        wrapped_function.__wrapped__ = tool
        wrapped_function.tool_name = tool_name
        
        # CRITICO: Preserva la signature originale per Pydantic/LangGraph
        wrapped_function.__signature__ = original_signature
        
        # Preserva anche annotations se presenti
        if hasattr(tool, '__annotations__'):
            wrapped_function.__annotations__ = tool.__annotations__.copy()
        
        # Preserva altri metadati importanti per tool creation
        for attr in ['name', '__name__', '__doc__', '__module__', '__qualname__']:
            if hasattr(tool, attr):
                try:
                    setattr(wrapped_function, attr, getattr(tool, attr))
                except (AttributeError, TypeError):
                    # Ignora errori su attributi read-only
                    pass
        
        return wrapped_function
    
    def _create_function_wrapper(self, func: Callable, tool_name: str) -> Callable:
        """Create a wrapper for a raw function that will be used in StructuredTool.func"""
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            return self._execute_with_cleaning(func, tool_name, *args, **kwargs)
        
        return wrapped_function
    
    def _wrap_tool_object(self, tool: Any, tool_name: str) -> Any:
        """Wrappa un tool object."""
        
        class WrappedTool:
            def __init__(self, original_tool, wrapper_instance, name):
                self._original_tool = original_tool
                self._wrapper = wrapper_instance
                self.tool_name = name
                
                # Copia attributi del tool originale
                for attr in dir(original_tool):
                    if not attr.startswith('_') and attr not in ['run', '__call__']:
                        try:
                            setattr(self, attr, getattr(original_tool, attr))
                        except:
                            pass
            
            def run(self, *args, **kwargs):
                if hasattr(self._original_tool, 'run'):
                    return self._wrapper._execute_with_cleaning(
                        self._original_tool.run, self.tool_name, *args, **kwargs
                    )
                else:
                    raise AttributeError(f"Tool {self.tool_name} has no 'run' method")
            
            def __call__(self, *args, **kwargs):
                if hasattr(self._original_tool, '__call__'):
                    return self._wrapper._execute_with_cleaning(
                        self._original_tool, self.tool_name, *args, **kwargs
                    )
                else:
                    return self.run(*args, **kwargs)
        
        return WrappedTool(tool, self, tool_name)
    
    def _execute_with_cleaning(self, tool_func: Callable, tool_name: str, *args, **kwargs) -> Any:
        """
        Esegue un tool con pulizia automatica del risultato.
        
        Args:
            tool_func: Funzione del tool da eseguire
            tool_name: Nome del tool
            *args, **kwargs: Argomenti per il tool
        
        Returns:
            Risultato pulito del tool
        """
        start_time = time.time()
        
        try:
            # Incrementa statistiche
            self.stats["total_calls"] += 1
            
            # Log pre-execution con context length - MASSIMA VISIBILITÀ
            context_logger.info(f"🔧 MCP Tool Call: {tool_name}")
            print(f"🔥 TOOL CALL: {tool_name} - EXECUTING NOW")  # Extra visibility
            self._log_pre_execution_context()
            
            # Esegue il tool originale
            original_result = tool_func(*args, **kwargs)
            
            # Calcola dimensioni pre-pulizia
            original_size = len(json.dumps(original_result, default=str))
            
            # Applica pulizia se abilitata
            if self.config.get("cleaning_enabled", True):
                cleaned_result, cleaning_info = self._clean_tool_result(
                    tool_name, original_result, args, kwargs
                )
                # Log cleaning operation
                self._log_cleaning_operation(tool_name, cleaning_info, original_size)
                print(f"✅ TOOL COMPLETED: {tool_name} - Result processed and cleaned")  # Extra visibility
            else:
                cleaned_result = original_result
                cleaning_info = self._create_no_cleaning_result(original_result)
                context_logger.info(f"⚪ No cleaning applied for {tool_name} (cleaning disabled)")
            
            # Verifica se è necessaria compattazione
            self._check_and_log_compaction_trigger()
            
            # Aggiorna statistiche
            if cleaning_info.cleaning_status == "completed":
                self.stats["cleaned_calls"] += 1
                self.stats["total_reduction_percentage"] += cleaning_info.reduction_percentage
            
            # Registra la chiamata
            execution_time = time.time() - start_time
            self._log_tool_call(tool_name, args, kwargs, original_result, cleaned_result, 
                              cleaning_info, execution_time)
            
            # Log post-execution context length
            self._log_post_execution_context(execution_time)
            
            # Restituisce il risultato pulito
            return cleaned_result
            
        except Exception as e:
            # Gestione errori graceful
            self.stats["errors"] += 1
            context_logger.error(f"❌ Error in {tool_name}: {str(e)}")
            self._log_error(tool_name, args, kwargs, e, time.time() - start_time)
            
            # Se la pulizia fallisce, restituisce il risultato originale
            if 'original_result' in locals():
                return original_result
            else:
                # Se anche l'esecuzione del tool fallisce, rilancia l'errore
                raise
    
    def _clean_tool_result(self, tool_name: str, result: Any, args: tuple, kwargs: dict) -> tuple[Any, CleaningResult]:
        """Applica pulizia al risultato del tool."""
        try:
            # Crea contesto per la pulizia
            context = {
                "tool_name": tool_name,
                "args": args,
                "kwargs": kwargs,
                "timestamp": time.time()
            }
            
            # Applica pulizia usando il context manager
            cleaned_result, cleaning_result = self.context_manager.clean_mcp_tool_result(
                tool_name, result, context
            )
            
            return cleaned_result, cleaning_result
            
        except Exception as e:
            # Se la pulizia fallisce, restituisce il risultato originale
            error_result = CleaningResult.from_data(
                result, result, "CleaningError", "failed"
            )
            error_result.metadata = {"error": str(e)}
            return result, error_result
    
    def _create_no_cleaning_result(self, result: Any) -> CleaningResult:
        """Crea un CleaningResult per quando la pulizia è disabilitata."""
        return CleaningResult.from_data(
            result, result, "CleaningDisabled", "skipped"
        )
    
    def _log_tool_call(self, tool_name: str, args: tuple, kwargs: dict, 
                      original_result: Any, cleaned_result: Any, 
                      cleaning_info: CleaningResult, execution_time: float) -> None:
        """Registra una chiamata al tool per analisi successive."""
        call_record = {
            "tool_name": tool_name,
            "timestamp": time.time(),
            "execution_time": execution_time,
            "args_count": len(args),
            "kwargs_count": len(kwargs),
            "original_size": len(json.dumps(original_result, default=str)),
            "cleaned_size": len(json.dumps(cleaned_result, default=str)),
            "cleaning_info": asdict(cleaning_info) if hasattr(cleaning_info, '__dict__') else cleaning_info.__dict__,
            "success": True
        }
        
        self.call_history.append(call_record)
        
        # Mantiene solo gli ultimi 100 record per evitare memory leak
        if len(self.call_history) > 100:
            self.call_history = self.call_history[-100:]
    
    def _log_error(self, tool_name: str, args: tuple, kwargs: dict, 
                   error: Exception, execution_time: float) -> None:
        """Registra un errore di esecuzione del tool."""
        error_record = {
            "tool_name": tool_name,
            "timestamp": time.time(),
            "execution_time": execution_time,
            "args_count": len(args),
            "kwargs_count": len(kwargs),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "success": False
        }
        
        self.call_history.append(error_record)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Restituisce statistiche delle operazioni di wrapping."""
        avg_reduction = 0.0
        if self.stats["cleaned_calls"] > 0:
            avg_reduction = self.stats["total_reduction_percentage"] / self.stats["cleaned_calls"]
        
        return {
            "total_calls": self.stats["total_calls"],
            "cleaned_calls": self.stats["cleaned_calls"],
            "cleaning_success_rate": (self.stats["cleaned_calls"] / self.stats["total_calls"] * 100) if self.stats["total_calls"] > 0 else 0,
            "average_reduction_percentage": round(avg_reduction, 2),
            "errors": self.stats["errors"],
            "wrapped_tools_count": len(self.wrapped_tools),
            "recent_calls": len(self.call_history)
        }
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Restituisce le chiamate recenti ai tool."""
        return self.call_history[-limit:]
    
    def reset_statistics(self) -> None:
        """Resetta le statistiche."""
        self.stats = {
            "total_calls": 0,
            "cleaned_calls": 0,
            "total_reduction_percentage": 0.0,
            "errors": 0
        }
        self.call_history = []
    
    def clean_message_list(self, messages: List[Any]) -> List[Any]:
        """
        Pulisce una lista di messaggi LangGraph, applicando cleaning ai ToolMessage MCP.
        
        Questo metodo è specificamente progettato per risolvere il gap di integrazione
        con LangGraph state, pulendo i ToolMessage DOPO che sono stati salvati nello stato.
        
        Args:
            messages: Lista di messaggi LangGraph (HumanMessage, AIMessage, ToolMessage, etc.)
        
        Returns:
            Lista di messaggi con ToolMessage MCP puliti
        """
        if not messages:
            return messages
        
        cleaned_messages = []
        
        for message in messages:
            # Verifica se è un ToolMessage che necessita pulizia
            if self._is_mcp_tool_message(message):
                try:
                    # Applica pulizia al contenuto del ToolMessage
                    cleaned_content = self._clean_tool_message_content(message)
                    
                    # Crea una copia del messaggio con contenuto pulito
                    cleaned_message = self._create_cleaned_tool_message(message, cleaned_content)
                    cleaned_messages.append(cleaned_message)
                    
                    # Log dell'operazione
                    self._log_message_cleaning(message, cleaned_message)
                    
                except Exception as e:
                    # Se la pulizia fallisce, mantieni il messaggio originale
                    print(f"⚠️ Failed to clean ToolMessage: {e}")
                    cleaned_messages.append(message)
            else:
                # Non è un ToolMessage MCP, mantieni invariato
                cleaned_messages.append(message)
        
        return cleaned_messages
    
    def _is_mcp_tool_message(self, message: Any) -> bool:
        """Verifica se un messaggio è un ToolMessage MCP che necessita pulizia."""
        # Verifica se ha attributi di ToolMessage
        if not (hasattr(message, 'type') and hasattr(message, 'content')):
            return False
        
        # Verifica se è di tipo tool
        if getattr(message, 'type', None) != 'tool':
            return False
        
        # Verifica se ha tool_call_id o name che indica MCP tool
        tool_name = getattr(message, 'name', '') or getattr(message, 'tool_call_id', '')
        
        return self._is_mcp_tool(tool_name)
    
    def _clean_tool_message_content(self, message: Any) -> Any:
        """Pulisce il contenuto di un ToolMessage."""
        content = getattr(message, 'content', '')
        tool_name = getattr(message, 'name', '') or getattr(message, 'tool_call_id', '')
        
        # Se il contenuto è già una stringa JSON, prova a parsarlo
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # Se non è JSON valido, restituisci il contenuto originale
                return content
        
        # Applica pulizia usando il context manager
        try:
            cleaned_result, cleaning_info = self._clean_tool_result(
                tool_name, content, (), {}
            )
            return cleaned_result
        except Exception:
            # Fallback al contenuto originale se la pulizia fallisce
            return content
    
    def _create_cleaned_tool_message(self, original_message: Any, cleaned_content: Any) -> Any:
        """Crea una copia del ToolMessage con contenuto pulito."""
        # Se il contenuto pulito è un dict/list, convertilo in JSON string
        if isinstance(cleaned_content, (dict, list)):
            content_str = json.dumps(cleaned_content, ensure_ascii=False, indent=2)
        else:
            content_str = str(cleaned_content)
        
        # Crea una copia del messaggio mantenendo tutti gli attributi originali
        if hasattr(original_message, '__dict__'):
            # Se il messaggio è un oggetto con attributi, crea una copia
            cleaned_message = type(original_message).__new__(type(original_message))
            
            # Copia tutti gli attributi dall'originale
            for attr, value in original_message.__dict__.items():
                if attr == 'content':
                    setattr(cleaned_message, attr, content_str)
                else:
                    setattr(cleaned_message, attr, value)
            
            return cleaned_message
        else:
            # Fallback: restituisci il messaggio originale
            return original_message
    
    def _log_pre_execution_context(self) -> None:
        """Log del contesto prima dell'esecuzione del tool."""
        try:
            # Simula una lista di messaggi per analizzare il contesto
            # In un ambiente reale, questo dovrebbe essere iniettato dal sistema LangGraph
            mock_messages = [{"content": "current context", "type": "placeholder"}]
            metrics = self.context_manager.analyze_context(mock_messages)
            
            context_logger.info(f"📊 Pre-execution Context: {metrics.tokens_used:,} tokens "
                              f"({metrics.utilization_percentage:.1f}% utilization, "
                              f"{metrics.mcp_noise_percentage:.1f}% MCP noise)")
        except Exception as e:
            context_logger.info(f"Could not analyze pre-execution context: {e}")
    
    def _log_post_execution_context(self, execution_time: float) -> None:
        """Log del contesto dopo l'esecuzione del tool."""
        try:
            # Simula una lista di messaggi per analizzare il contesto post-esecuzione
            mock_messages = [{"content": "updated context", "type": "placeholder"}]
            metrics = self.context_manager.analyze_context(mock_messages)
            
            context_logger.info(f"📈 Post-execution Context: {metrics.tokens_used:,} tokens "
                              f"({metrics.utilization_percentage:.1f}% utilization) "
                              f"- Execution time: {execution_time:.3f}s")
        except Exception as e:
            context_logger.info(f"Could not analyze post-execution context: {e}")
    
    def _log_cleaning_operation(self, tool_name: str, cleaning_info: CleaningResult, original_size: int) -> None:
        """Log delle operazioni di pulizia."""
        if cleaning_info.cleaning_status == "completed":
            context_logger.info(f"🧹 Cleaning applied to {tool_name}: "
                              f"{original_size:,} → {cleaning_info.cleaned_size:,} chars "
                              f"({cleaning_info.reduction_percentage:.1f}% reduction) "
                              f"using {cleaning_info.strategy_used}")
        elif cleaning_info.cleaning_status == "skipped":
            context_logger.info(f"⏭️ Cleaning skipped for {tool_name}: {cleaning_info.strategy_used}")
        elif cleaning_info.cleaning_status == "failed":
            context_logger.warning(f"⚠️ Cleaning failed for {tool_name}: "
                                  f"{cleaning_info.metadata.get('error', 'Unknown error')}")
    
    def _check_and_log_compaction_trigger(self) -> None:
        """Verifica e log dei trigger di compattazione."""
        try:
            # Simula una lista di messaggi per il controllo compattazione
            mock_messages = [{"content": "context for compaction check", "type": "placeholder"}]
            should_compact, trigger_type, metrics = self.context_manager.should_trigger_compaction(mock_messages)
            
            if should_compact:
                context_logger.warning(f"🔄 COMPACTION TRIGGERED: {trigger_type.value} "
                                     f"(Utilization: {metrics.utilization_percentage:.1f}%, "
                                     f"MCP Noise: {metrics.mcp_noise_percentage:.1f}%)")
                
                # Qui potresti attivare effettivamente la compattazione
                self._trigger_context_compaction(mock_messages, trigger_type, metrics)
            elif metrics.is_near_limit:
                context_logger.info(f"⚠️ Context near limit: {metrics.utilization_percentage:.1f}% utilization")
        except Exception as e:
            context_logger.info(f"Could not check compaction trigger: {e}")
    
    def _trigger_context_compaction(self, messages: List[Any], trigger_type: Any, metrics: ContextMetrics) -> None:
        """Esegue la compattazione del contesto."""
        try:
            context_logger.info(f"🔄 Starting context compaction ({trigger_type.value})...")
            
            # Esegue la pulizia completa del contesto
            cleaned_messages, context_info = self.context_manager.process_context_cleaning(messages)
            
            context_logger.info(f"✅ Context compaction completed: "
                              f"{context_info.total_reduction_percentage:.1f}% total reduction "
                              f"({len(context_info.cleaning_results)} operations)")
            
            # Aggiorna le statistiche
            self.context_manager.context_history.append(context_info)
            
        except Exception as e:
            context_logger.error(f"❌ Context compaction failed: {e}")
    
    def _log_message_cleaning(self, original_message: Any, cleaned_message: Any) -> None:
        """Log dell'operazione di pulizia messaggio."""
        original_size = len(str(getattr(original_message, 'content', '')))
        cleaned_size = len(str(getattr(cleaned_message, 'content', '')))
        
        if original_size > 0:
            reduction = ((original_size - cleaned_size) / original_size) * 100
            context_logger.info(f"🧹 ToolMessage cleaned: {original_size:,} → {cleaned_size:,} chars ({reduction:.1f}% reduction)")
        else:
            context_logger.info("🧹 ToolMessage processed (no size change)")
        
        # Aggiorna statistiche se non già contate
        self.stats["cleaned_calls"] += 1


def create_mcp_wrapper(config: Dict[str, Any] = None) -> MCPToolWrapper:
    """
    Crea un wrapper MCP configurato con strategie di pulizia predefinite.
    
    Args:
        config: Configurazione per il wrapper e context manager
    
    Returns:
        Wrapper MCP configurato e pronto all'uso
    """
    # Configurazione predefinita
    default_config = {
        "cleaning_enabled": True,
        "max_context_window": 200000,
        "trigger_threshold": 0.85,
        "mcp_noise_threshold": 0.6,
        "deduplication_enabled": True,
        "preserve_essential_fields": True,
        "auto_compaction": True
    }
    
    if config:
        default_config.update(config)
    
    # Crea context manager
    context_manager = ContextManager(default_config)
    
    # Registra strategie di pulizia predefinite
    strategies = create_default_cleaning_strategies(default_config)
    for strategy in strategies:
        context_manager.register_cleaning_strategy(strategy)
    
    # Crea wrapper
    return MCPToolWrapper(context_manager, default_config)


def wrap_existing_mcp_tools(tools: List[Any], config: Dict[str, Any] = None) -> tuple[List[Any], MCPToolWrapper]:
    """
    Utility per wrappare rapidamente una lista di tool MCP esistenti.
    
    Args:
        tools: Lista di tool MCP da wrappare
        config: Configurazione opzionale
    
    Returns:
        Tupla (tool_wrapped, wrapper_instance)
    """
    wrapper = create_mcp_wrapper(config)
    wrapped_tools = wrapper.wrap_tool_list(tools)
    
    return wrapped_tools, wrapper