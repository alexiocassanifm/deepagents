#!/usr/bin/env python3
"""
Configurazione per logging dettagliato del context manager.

Questo script mostra come configurare il sistema per ottenere log molto dettagliati
di tutte le operazioni di context management, pulizia e compattazione.
"""

import logging
import sys

def setup_detailed_logging():
    """Configura logging dettagliato per tutto il sistema context management."""
    
    # Configurazione logging globale
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('context_detailed.log', mode='a')
        ]
    )
    
    # Logger specifici con livelli personalizzati
    loggers_config = {
        'context_manager': logging.INFO,
        'mcp_context_tracker': logging.INFO,
        'mcp_cleaners': logging.INFO,
        'mcp.client': logging.WARNING,  # Riduci noise da MCP client
        'litellm': logging.WARNING,     # Riduci noise da LiteLLM
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    print("✅ Detailed logging configured for context management")
    print(f"📝 Logs will be written to: context_detailed.log")
    print(f"📊 Console output level: INFO")
    print()
    print("🎯 You will now see detailed logs for:")
    print("   🔧 Every MCP tool call with context length")
    print("   🧹 Cleaning operations with before/after sizes")
    print("   📊 Context analysis with token counts and noise percentages")
    print("   🔄 Compaction triggers and operations")
    print("   ⚠️ Near-limit warnings and optimization suggestions")
    print("   📈 Performance metrics and execution times")

def example_usage():
    """Esempio di utilizzo con logging dettagliato."""
    from mcp_wrapper import create_mcp_wrapper
    
    # Configurazione con soglie basse per vedere più azioni
    config = {
        "cleaning_enabled": True,
        "max_context_window": 30000,   # Finestra più piccola per test
        "trigger_threshold": 0.60,     # Soglia più bassa
        "mcp_noise_threshold": 0.40,   # Soglia rumore più bassa 
        "deduplication_enabled": True,
        "preserve_essential_fields": True,
        "auto_compaction": True
    }
    
    # Crea wrapper con logging avanzato
    wrapper = create_mcp_wrapper(config)
    
    print("\n🚀 MCP Wrapper created with detailed logging enabled")
    print("Now every MCP tool call will produce detailed logs showing:")
    print("- Context length before and after execution")
    print("- Cleaning strategies applied and reduction achieved")
    print("- Compaction triggers when thresholds are exceeded")
    print("- Performance metrics for each operation")
    
    return wrapper

if __name__ == "__main__":
    setup_detailed_logging()
    
    print("\n" + "="*60)
    print("EXAMPLE: Creating wrapper with detailed logging")
    print("="*60)
    
    wrapper = example_usage()
    
    print("\n✅ Setup complete! Your context manager now has enhanced logging.")
    print("\n💡 To integrate this in your agent:")
    print("""
    # In your agent setup:
    from configure_detailed_logging import setup_detailed_logging
    from mcp_wrapper import wrap_existing_mcp_tools
    
    # Enable detailed logging
    setup_detailed_logging()
    
    # Wrap your MCP tools
    wrapped_tools, wrapper = wrap_existing_mcp_tools(your_mcp_tools)
    
    # Use wrapped tools - detailed logs will show automatically
    result = wrapped_tools[0]()
    """)