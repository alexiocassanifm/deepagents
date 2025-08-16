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

def validate_configuration() -> Dict[str, Any]:
    """Valida la configurazione caricata e restituisce report di validazione."""
    config = get_full_config()
    validation_report = {
        "status": "valid",
        "warnings": [],
        "errors": [],
        "unused_parameters": [],
        "performance_recommendations": []
    }
    
    # Validazione soglie
    trigger_config = config.triggers
    if trigger_config.trigger_threshold >= 1.0 or trigger_config.trigger_threshold <= 0.0:
        validation_report["errors"].append("trigger_threshold must be between 0.0 and 1.0")
    
    if trigger_config.mcp_noise_threshold >= 1.0 or trigger_config.mcp_noise_threshold <= 0.0:
        validation_report["errors"].append("mcp_noise_threshold must be between 0.0 and 1.0")
    
    if trigger_config.post_tool_threshold >= trigger_config.trigger_threshold:
        validation_report["warnings"].append("post_tool_threshold >= trigger_threshold may cause frequent compressions")
    
    # Validazione performance
    performance_config = config.performance
    if performance_config.get("auto_check_interval", 30) > 300:
        validation_report["warnings"].append("auto_check_interval > 5 minutes may reduce responsiveness")
    
    if performance_config.get("analysis_cache_duration", 60) < 10:
        validation_report["warnings"].append("analysis_cache_duration < 10 seconds may cause excessive reanalysis")
    
    # Controllo per parametri non utilizzati (based on what we implemented)
    implemented_params = {
        "context_management", "cleaning_strategies", "deduplication", 
        "compaction", "performance", "monitoring", "integration"
    }
    yaml_sections = set(config.__dict__.keys()) - {"triggers"}
    unused_sections = yaml_sections - implemented_params
    if unused_sections:
        validation_report["unused_parameters"].extend(list(unused_sections))
    
    # Raccomandazioni performance
    if trigger_config.llm_compression_threshold < trigger_config.trigger_threshold:
        validation_report["performance_recommendations"].append(
            "Consider lowering llm_compression_threshold for better compression quality"
        )
    
    if validation_report["errors"]:
        validation_report["status"] = "invalid"
    elif validation_report["warnings"]:
        validation_report["status"] = "valid_with_warnings"
    
    return validation_report

def log_configuration_status():
    """Stampa stato completo della configurazione con validazione."""
    print("\n" + "="*60)
    print("🔧 DEEP PLANNING - CONFIGURATION STATUS")
    print("="*60)
    
    # Carica e valida configurazione
    config = get_full_config()
    validation = validate_configuration()
    
    # Status generale
    status_icon = "✅" if validation["status"] == "valid" else "⚠️" if validation["status"] == "valid_with_warnings" else "❌"
    print(f"{status_icon} Configuration Status: {validation['status'].upper()}")
    
    # Trigger summary
    print_config_summary()
    
    # Validation results
    if validation["errors"]:
        print("\n❌ CONFIGURATION ERRORS:")
        for error in validation["errors"]:
            print(f"   • {error}")
    
    if validation["warnings"]:
        print("\n⚠️ CONFIGURATION WARNINGS:")
        for warning in validation["warnings"]:
            print(f"   • {warning}")
    
    if validation["unused_parameters"]:
        print("\n📋 UNUSED CONFIGURATION SECTIONS:")
        for param in validation["unused_parameters"]:
            print(f"   • {param}")
    
    if validation["performance_recommendations"]:
        print("\n🚀 PERFORMANCE RECOMMENDATIONS:")
        for rec in validation["performance_recommendations"]:
            print(f"   • {rec}")
    
    # Performance settings summary
    performance = config.performance
    print("\n⚡ PERFORMANCE SETTINGS:")
    print(f"   📊 Analysis cache: {performance.get('analysis_cache_duration', 60)}s")
    print(f"   🔄 Auto check interval: {performance.get('auto_check_interval', 30)}s")
    print(f"   🎯 Precise tokenization: {performance.get('use_precise_tokenization', True)}")
    print(f"   📈 Track performance: {performance.get('track_cleaning_performance', True)}")
    
    # Monitoring settings
    monitoring = config.monitoring
    print("\n📊 MONITORING SETTINGS:")
    print(f"   📈 Collect metrics: {monitoring.get('collect_metrics', True)}")
    print(f"   📝 Log level: {monitoring.get('log_level', 'INFO')}")
    print(f"   📤 Export statistics: {monitoring.get('export_statistics', True)}")
    
    print("="*60)
