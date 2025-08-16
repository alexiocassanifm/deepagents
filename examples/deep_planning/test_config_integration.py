#!/usr/bin/env python3
"""
Test di integrazione per verificare che la configurazione sia correttamente utilizzata
in tutti i componenti del sistema deep_planning.
"""

import sys
import os
from typing import Dict, Any

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_config_loader():
    """Test del config loader."""
    print("🧪 Testing config_loader...")
    
    try:
        from config_loader import (
            get_trigger_config, get_context_management_config, 
            get_full_config, validate_configuration, log_configuration_status
        )
        
        # Test caricamento configurazione
        trigger_config = get_trigger_config()
        print(f"   ✅ Trigger config loaded: threshold={trigger_config.trigger_threshold}")
        
        context_config = get_context_management_config()
        print(f"   ✅ Context config loaded: max_window={context_config.get('max_context_window')}")
        
        # Test validazione
        validation = validate_configuration()
        print(f"   ✅ Configuration validation: {validation['status']}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_context_manager():
    """Test del context manager con configurazione."""
    print("\n🧪 Testing context_manager...")
    
    try:
        from context_manager import ContextManager
        
        # Crea context manager che dovrebbe caricare config da YAML
        cm = ContextManager()
        print(f"   ✅ ContextManager created with max_window={cm.config.get('max_context_window')}")
        print(f"   ✅ Performance settings: tokenization={cm.use_precise_tokenization}, cache={cm.analysis_cache_duration}s")
        
        # Test analyze con cache
        dummy_messages = [{"role": "user", "content": "test message"}]
        metrics = cm.analyze_context(dummy_messages)
        print(f"   ✅ Analysis completed: {metrics.utilization_percentage:.1f}% utilization")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_enhanced_compact_integration():
    """Test di enhanced compact integration."""
    print("\n🧪 Testing enhanced_compact_integration...")
    
    try:
        from enhanced_compact_integration import EnhancedCompactIntegration
        from context_manager import ContextManager
        
        cm = ContextManager()
        eci = EnhancedCompactIntegration(cm)
        
        print(f"   ✅ EnhancedCompactIntegration created")
        print(f"   ✅ LLM threshold: {eci.config.get('llm_threshold')}")
        print(f"   ✅ Force LLM threshold: {eci.config.get('force_llm_threshold')}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_mcp_cleaners():
    """Test delle MCP cleaning strategies."""
    print("\n🧪 Testing mcp_cleaners...")
    
    try:
        from mcp_cleaners import (
            ProjectListCleaner, CodeSnippetCleaner, DocumentCleaner,
            UserStoryListCleaner, RepositoryListCleaner, _load_cleaning_config
        )
        
        # Test caricamento configurazione
        config = _load_cleaning_config()
        print(f"   ✅ Cleaning config loaded with {len(config)} strategies")
        
        # Test creazione cleaner
        project_cleaner = ProjectListCleaner()
        print(f"   ✅ ProjectListCleaner created with config: {list(project_cleaner.config.keys())}")
        
        code_cleaner = CodeSnippetCleaner()
        print(f"   ✅ CodeSnippetCleaner created")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_llm_compression():
    """Test di LLM compression."""
    print("\n🧪 Testing llm_compression...")
    
    try:
        from llm_compression import CompressionConfig, _load_compression_config
        
        # Test caricamento configurazione
        config_data = _load_compression_config()
        print(f"   ✅ Compression config loaded: timeout={config_data['compression_timeout']}s")
        
        # Test creazione config da YAML
        compression_config = CompressionConfig.from_yaml()
        print(f"   ✅ CompressionConfig created: preserve_messages={compression_config.preserve_last_n_messages}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Esegue tutti i test di integrazione."""
    print("🔧 DEEP PLANNING - CONFIGURATION INTEGRATION TEST")
    print("="*60)
    
    tests = [
        test_config_loader,
        test_context_manager,
        test_enhanced_compact_integration,
        test_mcp_cleaners,
        test_llm_compression
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 TEST RESULTS: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed! Configuration integration is working correctly.")
        
        # Mostra status configurazione completo
        print("\n" + "="*60)
        try:
            from config_loader import log_configuration_status
            log_configuration_status()
        except Exception as e:
            print(f"⚠️ Could not display configuration status: {e}")
    else:
        print("❌ Some tests failed. Check the configuration integration.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)