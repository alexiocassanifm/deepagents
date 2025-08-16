"""
Enhanced Compact Integration - Integrazione completa LLM compression con sistema esistente

Questo modulo estende compact_integration.py aggiungendo supporto per compressione LLM
mantenendo completa compatibilità con il sistema di pulizia esistente.

Funzionalità principali:
1. Integrazione seamless con LLMCompressor
2. Trigger intelligenti basati su metriche precise
3. Fallback automatico al sistema di pulizia esistente
4. Compatibilità 100% con CompactIntegration originale
5. Metriche avanzate e monitoring
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict

# Import sistema esistente
from compact_integration import CompactIntegration, CompactSummary, CompactTrigger
from context_manager import ContextManager, ContextMetrics, ContextInfo
from mcp_wrapper import MCPToolWrapper

# Import nuovo sistema LLM
from llm_compression import LLMCompressor, CompressionConfig, LLMCompressionResult, CompressionType
from context_hooks import ContextHookManager, CompressionHook, HookType


@dataclass
class EnhancedCompactSummary(CompactSummary):
    """Estende CompactSummary con informazioni LLM compression."""
    llm_compression_used: bool = False
    llm_compression_result: Optional[LLMCompressionResult] = None
    fallback_reason: Optional[str] = None
    compression_strategy: str = "template"  # "llm" | "template" | "hybrid"
    enhanced_metrics: Dict[str, Any] = None


class EnhancedCompactIntegration(CompactIntegration):
    """
    Versione potenziata di CompactIntegration con supporto LLM compression.
    
    Mantiene completa compatibilità con CompactIntegration originale mentre aggiunge:
    1. Compressione semantica LLM
    2. Trigger intelligenti avanzati
    3. Fallback graceful automatico
    4. Monitoring e metriche dettagliate
    """
    
    def __init__(self, 
                 context_manager: ContextManager, 
                 mcp_wrapper: MCPToolWrapper = None,
                 llm_compressor: LLMCompressor = None,
                 hook_manager: ContextHookManager = None,
                 config: Dict[str, Any] = None):
        
        # Inizializza sistema base
        super().__init__(context_manager, mcp_wrapper)
        
        # Componenti LLM compression
        self.llm_compressor = llm_compressor
        self.hook_manager = hook_manager
        self.config = config or self._default_enhanced_config()
        
        # Tracking avanzato
        self.enhanced_history: List[EnhancedCompactSummary] = []
        self.compression_strategies_used = {
            "llm": 0,
            "template": 0, 
            "hybrid": 0,
            "fallback": 0
        }
        
        # Metriche performance
        self.performance_metrics = {
            "total_compressions": 0,
            "llm_compressions": 0,
            "template_compressions": 0,
            "average_llm_time": 0.0,
            "average_template_time": 0.0,
            "total_tokens_saved": 0
        }
    
    def _default_enhanced_config(self) -> Dict[str, Any]:
        """Configurazione estesa per sistema enhanced."""
        return {
            # Trigger configuration
            "prefer_llm_compression": True,
            "llm_threshold": 0.75,  # Usa LLM se utilizzo > 75%
            "template_threshold": 0.60,  # Usa template se utilizzo > 60%
            "force_llm_threshold": 0.90,  # Forza LLM se utilizzo > 90%
            
            # Performance configuration
            "llm_timeout": 30.0,
            "max_retry_attempts": 2,
            "enable_hybrid_mode": True,
            
            # Quality configuration
            "min_reduction_threshold": 0.30,  # Accetta solo se riduzione > 30%
            "preserve_recent_messages": 3,
            
            # Monitoring
            "enable_detailed_metrics": True,
            "log_compression_details": True
        }
    
    async def should_trigger_compaction(self, messages: List[Dict[str, Any]]) -> Tuple[bool, CompactTrigger, ContextMetrics]:
        """
        Versione enhanced di should_trigger_compaction con logica LLM.
        Mantiene compatibilità con l'interfaccia originale.
        """
        # Usa logica base per compatibilità
        base_should_compact, base_trigger, metrics = super().should_trigger_compaction(messages)
        
        if not base_should_compact:
            return False, base_trigger, metrics
        
        # Enhanced logic per LLM
        utilization = metrics.utilization_percentage / 100.0
        
        # Determina strategia di compressione basata su utilizzo
        if utilization >= self.config["force_llm_threshold"]:
            return True, CompactTrigger.THRESHOLD, metrics
        elif utilization >= self.config["llm_threshold"] and self.llm_compressor:
            return True, CompactTrigger.THRESHOLD, metrics
        elif utilization >= self.config["template_threshold"]:
            return True, base_trigger, metrics
        
        return base_should_compact, base_trigger, metrics
    
    async def perform_automatic_compaction(self, 
                                         messages: List[Dict[str, Any]], 
                                         context: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], EnhancedCompactSummary]:
        """
        Versione enhanced di perform_automatic_compaction con supporto LLM.
        """
        start_time = time.time()
        self.performance_metrics["total_compressions"] += 1
        
        # Analizza metriche per decidere strategia
        should_compact, trigger_type, metrics = await self.should_trigger_compaction(messages)
        
        if not should_compact:
            # Nessuna compressione necessaria - usa logica base
            original_messages, original_summary = super().perform_automatic_compaction(messages, context)
            return original_messages, self._enhance_summary(original_summary, "none", start_time)
        
        # Decide strategia di compressione
        compression_strategy = self._determine_compression_strategy(metrics, messages)
        
        try:
            if compression_strategy == "llm" and self.llm_compressor:
                return await self._perform_llm_compaction(messages, context, trigger_type, start_time)
            
            elif compression_strategy == "hybrid" and self.llm_compressor:
                return await self._perform_hybrid_compaction(messages, context, trigger_type, start_time)
            
            else:
                return await self._perform_template_compaction(messages, context, trigger_type, start_time)
                
        except Exception as e:
            # Fallback automatico al sistema template
            print(f"⚠️ Enhanced compression failed: {e}")
            return await self._perform_fallback_compaction(messages, context, trigger_type, start_time, str(e))
    
    def _determine_compression_strategy(self, metrics: ContextMetrics, messages: List[Dict[str, Any]]) -> str:
        """Determina la strategia di compressione ottimale."""
        utilization = metrics.utilization_percentage / 100.0
        
        # Forza LLM per utilizzo molto alto
        if utilization >= self.config["force_llm_threshold"]:
            return "llm"
        
        # Preferisce LLM se disponibile e configurato
        if (utilization >= self.config["llm_threshold"] and 
            self.llm_compressor and 
            self.config["prefer_llm_compression"]):
            
            # Analizza contenuto per decidere se vale la pena LLM
            if self._should_use_llm_for_content(messages):
                return "llm" if not self.config["enable_hybrid_mode"] else "hybrid"
        
        # Fallback a template
        return "template"
    
    def _should_use_llm_for_content(self, messages: List[Dict[str, Any]]) -> bool:
        """Analizza se il contenuto beneficierebbe di compressione LLM."""
        conversation_text = json.dumps(messages, default=str).lower()
        
        # Indicatori che beneficiano di LLM compression
        complex_indicators = [
            "planning", "architecture", "design", "analysis", 
            "requirements", "user stories", "technical",
            "implementation", "code review", "debugging"
        ]
        
        # Indicatori di rumore MCP che beneficiano meno
        mcp_noise_indicators = [
            "project_id", "entity_id", "repository_id",
            "tool_call", "function_call", "metadata"
        ]
        
        complex_score = sum(1 for indicator in complex_indicators if indicator in conversation_text)
        noise_score = sum(1 for indicator in mcp_noise_indicators if indicator in conversation_text)
        
        # Usa LLM se c'è complessità semantica da preservare
        return complex_score >= 3 and (noise_score / len(messages)) < 0.5
    
    async def _perform_llm_compaction(self, 
                                    messages: List[Dict[str, Any]], 
                                    context: Dict[str, Any],
                                    trigger_type: CompactTrigger,
                                    start_time: float) -> Tuple[List[Dict[str, Any]], EnhancedCompactSummary]:
        """Esegue compressione tramite LLM."""
        
        try:
            # Auto-detect compression type o usa context
            compression_type = context.get("compression_type") if context else None
            
            # Esegue compressione LLM
            llm_result = await self.llm_compressor.compress_conversation(
                messages, compression_type, context
            )
            
            if llm_result.success and llm_result.actual_reduction_percentage >= self.config["min_reduction_threshold"]:
                # Successo LLM - crea messaggi compattati
                compacted_messages = self._create_llm_continuation_messages(llm_result, messages)
                
                # Crea enhanced summary
                enhanced_summary = self._create_enhanced_summary(
                    messages, compacted_messages, trigger_type, "llm", start_time, 
                    llm_compression_result=llm_result
                )
                
                self.performance_metrics["llm_compressions"] += 1
                self.compression_strategies_used["llm"] += 1
                self.performance_metrics["total_tokens_saved"] += (llm_result.tokens_before - llm_result.tokens_after)
                
                return compacted_messages, enhanced_summary
            
            else:
                # LLM non efficace - fallback a template
                return await self._perform_template_compaction(messages, context, trigger_type, start_time)
                
        except asyncio.TimeoutError:
            print("⚠️ LLM compression timeout - falling back to template")
            return await self._perform_template_compaction(messages, context, trigger_type, start_time)
    
    async def _perform_hybrid_compaction(self,
                                       messages: List[Dict[str, Any]],
                                       context: Dict[str, Any], 
                                       trigger_type: CompactTrigger,
                                       start_time: float) -> Tuple[List[Dict[str, Any]], EnhancedCompactSummary]:
        """Esegue compressione ibrida: LLM per semantica + template per struttura."""
        
        try:
            # Fase 1: Pulizia template per rimuovere rumore
            cleaned_messages, cleaning_info = self.context_manager.process_context_cleaning(messages, context)
            
            # Fase 2: Compressione LLM sul contenuto pulito
            llm_result = await self.llm_compressor.compress_conversation(
                cleaned_messages, CompressionType.GENERAL, context
            )
            
            if llm_result.success:
                # Combina risultati
                compacted_messages = self._create_llm_continuation_messages(llm_result, messages)
                
                enhanced_summary = self._create_enhanced_summary(
                    messages, compacted_messages, trigger_type, "hybrid", start_time,
                    llm_compression_result=llm_result
                )
                
                self.compression_strategies_used["hybrid"] += 1
                return compacted_messages, enhanced_summary
            
            else:
                # Fallback a solo template
                return await self._perform_template_compaction(messages, context, trigger_type, start_time)
                
        except Exception as e:
            return await self._perform_template_compaction(messages, context, trigger_type, start_time)
    
    async def _perform_template_compaction(self,
                                         messages: List[Dict[str, Any]],
                                         context: Dict[str, Any],
                                         trigger_type: CompactTrigger, 
                                         start_time: float) -> Tuple[List[Dict[str, Any]], EnhancedCompactSummary]:
        """Esegue compressione template standard (sistema originale)."""
        
        # Usa sistema originale
        compacted_messages, original_summary = super().perform_automatic_compaction(messages, context)
        
        # Enhance summary
        enhanced_summary = self._enhance_summary(original_summary, "template", start_time)
        
        self.performance_metrics["template_compressions"] += 1
        self.compression_strategies_used["template"] += 1
        
        return compacted_messages, enhanced_summary
    
    async def _perform_fallback_compaction(self,
                                         messages: List[Dict[str, Any]],
                                         context: Dict[str, Any],
                                         trigger_type: CompactTrigger,
                                         start_time: float,
                                         error_reason: str) -> Tuple[List[Dict[str, Any]], EnhancedCompactSummary]:
        """Esegue compressione fallback in caso di errori."""
        
        compacted_messages, original_summary = super().perform_automatic_compaction(messages, context)
        
        enhanced_summary = self._enhance_summary(
            original_summary, "fallback", start_time, fallback_reason=error_reason
        )
        
        self.compression_strategies_used["fallback"] += 1
        
        return compacted_messages, enhanced_summary
    
    def _create_llm_continuation_messages(self, 
                                        llm_result: LLMCompressionResult, 
                                        original_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crea messaggi di continuation da risultato LLM."""
        
        # Messaggio di sistema con compression LLM
        system_message = {
            "role": "system",
            "content": llm_result.compressed_content,
            "compression_metadata": {
                "type": "llm_compression",
                "compression_type": llm_result.compression_type.value,
                "reduction_percentage": llm_result.actual_reduction_percentage,
                "tokens_before": llm_result.tokens_before,
                "tokens_after": llm_result.tokens_after,
                "timestamp": llm_result.timestamp,
                "fallback_used": llm_result.fallback_used
            }
        }
        
        continuation_messages = [system_message]
        
        # Preserva ultimi messaggi se configurato
        if self.config["preserve_recent_messages"] > 0:
            recent_messages = original_messages[-self.config["preserve_recent_messages"]:]
            continuation_messages.extend(recent_messages)
        
        return continuation_messages
    
    def _create_enhanced_summary(self,
                               original_messages: List[Dict[str, Any]],
                               compacted_messages: List[Dict[str, Any]], 
                               trigger_type: CompactTrigger,
                               strategy: str,
                               start_time: float,
                               llm_compression_result: LLMCompressionResult = None) -> EnhancedCompactSummary:
        """Crea enhanced summary con tutte le informazioni."""
        
        # Calcola metriche before/after
        before_metrics = self.context_manager.analyze_context(original_messages)
        after_metrics = self.context_manager.analyze_context(compacted_messages)
        
        # Estrae informazioni dal contenuto
        if llm_compression_result:
            summary_content = llm_compression_result.compressed_content
            preserved_elements = llm_compression_result.preserved_elements
            technical_concepts = []  # Estratto dal LLM result
            pending_tasks = []
            current_work = None
            next_steps = []
        else:
            # Usa analisi template per compatibilità
            analysis = self._analyze_conversation_content(original_messages)
            summary_content = self._generate_summary_content(analysis, before_metrics)
            preserved_elements = analysis.get("preserved_elements", [])
            technical_concepts = analysis.get("technical_concepts", [])
            pending_tasks = analysis.get("pending_tasks", [])
            current_work = analysis.get("current_work")
            next_steps = analysis.get("next_steps", [])
        
        enhanced_summary = EnhancedCompactSummary(
            session_id=self.context_manager.session_id,
            trigger_type=trigger_type,
            summary_content=summary_content,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            preserved_elements=preserved_elements,
            technical_concepts=technical_concepts,
            pending_tasks=pending_tasks,
            current_work=current_work,
            next_steps=next_steps,
            timestamp=datetime.now().isoformat(),
            
            # Enhanced fields
            llm_compression_used=(strategy in ["llm", "hybrid"]),
            llm_compression_result=llm_compression_result,
            compression_strategy=strategy,
            enhanced_metrics={
                "processing_time": time.time() - start_time,
                "strategy_used": strategy,
                "original_message_count": len(original_messages),
                "compacted_message_count": len(compacted_messages)
            }
        )
        
        # Salva in cronologia enhanced
        self.enhanced_history.append(enhanced_summary)
        
        return enhanced_summary
    
    def _enhance_summary(self, 
                        original_summary: CompactSummary, 
                        strategy: str, 
                        start_time: float,
                        fallback_reason: str = None) -> EnhancedCompactSummary:
        """Converte CompactSummary in EnhancedCompactSummary."""
        
        enhanced_summary = EnhancedCompactSummary(
            session_id=original_summary.session_id,
            trigger_type=original_summary.trigger_type,
            summary_content=original_summary.summary_content,
            before_metrics=original_summary.before_metrics,
            after_metrics=original_summary.after_metrics,
            preserved_elements=original_summary.preserved_elements,
            technical_concepts=original_summary.technical_concepts,
            pending_tasks=original_summary.pending_tasks,
            current_work=original_summary.current_work,
            next_steps=original_summary.next_steps,
            timestamp=original_summary.timestamp,
            
            # Enhanced fields
            llm_compression_used=False,
            compression_strategy=strategy,
            fallback_reason=fallback_reason,
            enhanced_metrics={
                "processing_time": time.time() - start_time,
                "strategy_used": strategy
            }
        )
        
        self.enhanced_history.append(enhanced_summary)
        return enhanced_summary
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Restituisce statistiche dettagliate del sistema enhanced."""
        
        base_stats = self.get_compaction_statistics()
        
        # Calcola metriche enhanced
        if self.enhanced_history:
            avg_processing_time = sum(
                s.enhanced_metrics.get("processing_time", 0) for s in self.enhanced_history
            ) / len(self.enhanced_history)
            
            reduction_percentages = [s.total_reduction_percentage for s in self.enhanced_history]
            avg_reduction = sum(reduction_percentages) / len(reduction_percentages)
        else:
            avg_processing_time = 0
            avg_reduction = 0
        
        enhanced_stats = {
            **base_stats,
            "enhanced_compressions": len(self.enhanced_history),
            "strategies_used": dict(self.compression_strategies_used),
            "performance_metrics": dict(self.performance_metrics),
            "average_processing_time": round(avg_processing_time, 3),
            "average_reduction_percentage": round(avg_reduction, 2),
            "llm_compression_success_rate": (
                (self.compression_strategies_used["llm"] + self.compression_strategies_used["hybrid"]) /
                max(self.performance_metrics["total_compressions"], 1) * 100
            ),
            "configuration": self.config
        }
        
        return enhanced_stats
    
    def get_recent_enhanced_compressions(self, limit: int = 5) -> List[EnhancedCompactSummary]:
        """Restituisce le compressioni enhanced recenti."""
        return self.enhanced_history[-limit:]
