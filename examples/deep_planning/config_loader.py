"""
Configuration Loader - Carica configurazione da YAML per trigger points centralizzati

Questo modulo carica la configurazione da context_config.yaml e la rende disponibile
a tutti i componenti del sistema per trigger points consistenti.
"""

import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TriggerConfig:
    """Configurazione centralizzata per tutti i trigger points."""
    # Context management triggers
    max_context_window: int = 200000
    trigger_threshold: float = 0.85
    mcp_noise_threshold: float = 0.6
    
    # LLM compression specific triggers
    llm_compression_threshold: float = 0.75
    force_llm_threshold: float = 0.90
    post_tool_threshold: float = 0.70
    min_reduction_threshold: float = 0.30
    
    # Performance settings
    preserve_last_n_messages: int = 3
    compression_timeout: float = 30.0
    enable_fallback: bool = True
    
    # Deduplication
    deduplication_enabled: bool = True
    similarity_threshold: float = 0.90


@dataclass
class FullConfig:
    """Configurazione completa caricata da YAML."""
    triggers: TriggerConfig = field(default_factory=TriggerConfig)
    context_management: Dict[str, Any] = field(default_factory=dict)
    cleaning_strategies: Dict[str, Any] = field(default_factory=dict)
    deduplication: Dict[str, Any] = field(default_factory=dict)
    compaction: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    integration: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """Caricatore centralizzato della configurazione YAML."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Try to find the config file in common locations
            import os
            possible_paths = [
                "context_config.yaml",  # Same directory
                "examples/deep_planning/context_config.yaml",  # From project root
                os.path.join(os.path.dirname(__file__), "context_config.yaml"),  # Module directory
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            else:
                config_path = "context_config.yaml"  # Fallback
                
        self.config_path = config_path
        self._config: Optional[FullConfig] = None
        self._loaded = False
    
    def load_config(self) -> FullConfig:
        """Carica configurazione da YAML con fallback a default."""
        if self._loaded and self._config:
            return self._config
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                
                print(f"✅ Configuration loaded from {self.config_path}")
                self._config = self._parse_yaml_config(yaml_data)
            else:
                print(f"⚠️ Config file not found: {self.config_path}")
                print("🔄 Using default configuration")
                self._config = FullConfig()
        
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            print("🔄 Using default configuration")
            self._config = FullConfig()
        
        self._loaded = True
        return self._config
    
    def _parse_yaml_config(self, yaml_data: Dict[str, Any]) -> FullConfig:
        """Converte YAML data in FullConfig strutturata."""
        
        # Estrae context management settings
        context_mgmt = yaml_data.get("context_management", {})
        
        # Crea trigger config dal YAML
        triggers = TriggerConfig(
            max_context_window=context_mgmt.get("max_context_window", 200000),
            trigger_threshold=context_mgmt.get("trigger_threshold", 0.85),
            mcp_noise_threshold=context_mgmt.get("mcp_noise_threshold", 0.6),
            
            # Usa soglie LLM dal YAML se disponibili, altrimenti calcola
            llm_compression_threshold=context_mgmt.get("llm_compression_threshold", 
                max(0.70, context_mgmt.get("trigger_threshold", 0.85) - 0.10)),
            force_llm_threshold=context_mgmt.get("force_llm_threshold",
                min(0.95, context_mgmt.get("trigger_threshold", 0.85) + 0.05)),
            post_tool_threshold=context_mgmt.get("post_tool_threshold",
                max(0.65, context_mgmt.get("trigger_threshold", 0.85) - 0.15)),
            
            # Deduplication da YAML
            deduplication_enabled=yaml_data.get("deduplication", {}).get("enabled", True),
            similarity_threshold=yaml_data.get("deduplication", {}).get("similarity_threshold", 0.90),
            
            # Performance da YAML
            compression_timeout=yaml_data.get("performance", {}).get("analysis_cache_duration", 30.0),
        )
        
        return FullConfig(
            triggers=triggers,
            context_management=context_mgmt,
            cleaning_strategies=yaml_data.get("cleaning_strategies", {}),
            deduplication=yaml_data.get("deduplication", {}),
            compaction=yaml_data.get("compaction", {}),
            performance=yaml_data.get("performance", {}),
            monitoring=yaml_data.get("monitoring", {}),
            integration=yaml_data.get("integration", {})
        )
    
    def get_trigger_config(self) -> TriggerConfig:
        """Ottiene configurazione trigger centralizzata."""
        return self.load_config().triggers
    
    def get_context_management_config(self) -> Dict[str, Any]:
        """Ottiene configurazione context management."""
        config = self.load_config()
        
        # Merge triggers nella config context management per compatibilità
        context_config = config.context_management.copy()
        context_config.update({
            "max_context_window": config.triggers.max_context_window,
            "trigger_threshold": config.triggers.trigger_threshold,
            "mcp_noise_threshold": config.triggers.mcp_noise_threshold,
            "deduplication_enabled": config.triggers.deduplication_enabled,
            "deduplication_similarity": config.triggers.similarity_threshold,
        })
        
        return context_config
    
    def print_trigger_summary(self):
        """Stampa riassunto dei trigger configurati."""
        triggers = self.get_trigger_config()
        
        print("\n📊 TRIGGER CONFIGURATION SUMMARY")
        print("=" * 40)
        print(f"📏 Max context window: {triggers.max_context_window:,} tokens")
        print(f"🎯 Standard trigger: {triggers.trigger_threshold:.0%}")
        print(f"🔇 MCP noise trigger: {triggers.mcp_noise_threshold:.0%}")
        print()
        print("🧠 LLM COMPRESSION TRIGGERS:")
        print(f"  • LLM compression: {triggers.llm_compression_threshold:.0%}")
        print(f"  • POST_TOOL hook: {triggers.post_tool_threshold:.0%}")
        print(f"  • Force LLM: {triggers.force_llm_threshold:.0%}")
        print(f"  • Min reduction: {triggers.min_reduction_threshold:.0%}")
        print()
        print("⚙️ OTHER SETTINGS:")
        print(f"  • Preserve messages: {triggers.preserve_last_n_messages}")
        print(f"  • Compression timeout: {triggers.compression_timeout}s")
        print(f"  • Deduplication: {triggers.deduplication_enabled}")
        print(f"  • Similarity threshold: {triggers.similarity_threshold:.0%}")


# Singleton instance per accesso globale
_config_loader = ConfigLoader()

def get_trigger_config() -> TriggerConfig:
    """Accesso rapido alla configurazione trigger."""
    return _config_loader.get_trigger_config()

def get_context_management_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione context management."""
    return _config_loader.get_context_management_config()

def get_full_config() -> FullConfig:
    """Accesso alla configurazione completa."""
    return _config_loader.load_config()

def print_config_summary():
    """Stampa riassunto configurazione."""
    _config_loader.print_trigger_summary()

def reload_config():
    """Ricarica configurazione da file."""
    _config_loader._loaded = False
    return _config_loader.load_config()
