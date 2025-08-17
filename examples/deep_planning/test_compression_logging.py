#!/usr/bin/env python3
"""
Test script per verificare il logging della compressione del contesto.

Questo script simula scenari diversi per verificare che tutti i log 
di valutazione compressione e MCP cleaning vengano correttamente registrati.
"""

import logging
import sys
import os
from pathlib import Path

# Aggiungi la directory src al path per poter importare i moduli
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.context.context_manager import ContextManager
from src.context.compact_integration import CompactIntegration
from src.context.context_compression import check_and_compact_if_needed
from src.integrations.mcp.mcp_cleaners import create_default_cleaning_strategies

def setup_test_logging():
    """Setup logging per il test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Abilita logging specifico per context manager
    context_logger = logging.getLogger("context_manager")
    context_logger.setLevel(logging.INFO)
    
    # Abilita logging per compression
    compression_logger = logging.getLogger(__name__)
    compression_logger.setLevel(logging.INFO)
    
    print("🔧 Logging setup completed\n")

def create_test_messages(scenario: str) -> list:
    """Crea messaggi di test per diversi scenari."""
    base_messages = [
        {"role": "user", "content": "Hello, can you help me with my project?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help you with your project."}
    ]
    
    if scenario == "low_context":
        # Scenario con poco contesto (non dovrebbe triggerare compressione)
        return base_messages
    
    elif scenario == "high_context":
        # Scenario con molto contesto (dovrebbe triggerare compressione)
        large_messages = base_messages.copy()
        for i in range(50):
            large_messages.append({
                "role": "assistant", 
                "content": f"This is a very long message number {i} with lots of content " * 100
            })
        return large_messages
    
    elif scenario == "mcp_noise":
        # Scenario con molto rumore MCP
        mcp_messages = base_messages.copy()
        mcp_messages.extend([
            {
                "role": "tool",
                "content": {
                    "General_list_projects": {
                        "result": [
                            {
                                "project_id": "proj123",
                                "name": "Test Project",
                                "description": "A test project",
                                "metadata": {"created_at": "2024-01-01", "internal_refs": ["ref1", "ref2"]},
                                "verbose_field_1": "lots of noise here" * 50,
                                "verbose_field_2": "even more noise" * 100
                            }
                        ] * 20  # Moltiplica per creare molto rumore
                    }
                }
            },
            {
                "role": "tool", 
                "content": {
                    "Code_find_relevant_code_snippets": {
                        "results": [
                            {
                                "text": "def hello(): pass",
                                "file_path": "/test/file.py",
                                "metadata": {"score": 0.95, "confidence": 0.88, "entity_data": {}},
                                "noise_field": "verbose metadata" * 200
                            }
                        ] * 15
                    }
                }
            }
        ])
        return mcp_messages
    
    return base_messages

def test_context_manager_evaluation():
    """Test valutazione compressione dal ContextManager."""
    print("=" * 60)
    print("🧪 TESTING CONTEXT MANAGER EVALUATION")
    print("=" * 60)
    
    # Crea context manager con soglie basse per testing
    test_config = {
        "max_context_window": 10000,  # Finestra piccola per test
        "trigger_threshold": 0.3,     # Soglia bassa (30%)
        "mcp_noise_threshold": 0.2,   # Soglia rumore bassa (20%)
        "deduplication_enabled": True,
        "preserve_essential_fields": True,
        "auto_compaction": True,
        "logging_enabled": True
    }
    
    context_manager = ContextManager(config=test_config)
    
    # Test 1: Scenario con poco contesto
    print("\n📝 Test 1: Low Context Scenario")
    low_messages = create_test_messages("low_context")
    should_compact, trigger_type, metrics = context_manager.should_trigger_compaction(low_messages)
    print(f"Result: should_compact={should_compact}, trigger={trigger_type}")
    
    # Test 2: Scenario con molto contesto
    print("\n📝 Test 2: High Context Scenario")
    high_messages = create_test_messages("high_context")
    should_compact, trigger_type, metrics = context_manager.should_trigger_compaction(high_messages)
    print(f"Result: should_compact={should_compact}, trigger={trigger_type}")
    
    # Test 3: Scenario con rumore MCP
    print("\n📝 Test 3: MCP Noise Scenario")
    mcp_messages = create_test_messages("mcp_noise")
    should_compact, trigger_type, metrics = context_manager.should_trigger_compaction(mcp_messages)
    print(f"Result: should_compact={should_compact}, trigger={trigger_type}")

def test_mcp_cleaning_evaluation():
    """Test valutazione MCP cleaning."""
    print("\n" + "=" * 60)
    print("🧪 TESTING MCP CLEANING EVALUATION")
    print("=" * 60)
    
    # Crea context manager e registra strategie
    context_manager = ContextManager()
    strategies = create_default_cleaning_strategies()
    for strategy in strategies:
        context_manager.register_cleaning_strategy(strategy)
    
    # Test dati MCP tools diversi
    test_tools = [
        ("General_list_projects", {
            "projects": [
                {"project_id": "123", "name": "Test", "metadata": {"noise": "lots of noise"}}
            ]
        }),
        ("Code_find_relevant_code_snippets", {
            "results": [
                {"text": "code here", "file_path": "/test.py", "score": 0.95}
            ]
        }),
        ("Unknown_tool", {
            "some_data": "this tool has no specific strategy"
        })
    ]
    
    for tool_name, tool_result in test_tools:
        print(f"\n📝 Testing MCP cleaning for: {tool_name}")
        cleaned_result, cleaning_info = context_manager.clean_mcp_tool_result(
            tool_name, tool_result
        )
        print(f"Result: {cleaning_info.cleaning_status}, reduction: {cleaning_info.reduction_percentage:.1f}%")

def test_general_compaction_check():
    """Test controllo generale di compattazione."""
    print("\n" + "=" * 60)
    print("🧪 TESTING GENERAL COMPACTION CHECK")
    print("=" * 60)
    
    # Test senza compact_integration
    print("\n📝 Test 1: No CompactIntegration available")
    result_messages, summary = check_and_compact_if_needed(
        create_test_messages("low_context"),
        context=None,
        compact_integration=None
    )
    
    # Test con compact_integration
    print("\n📝 Test 2: With CompactIntegration available")
    context_manager = ContextManager()
    compact_integration = CompactIntegration(context_manager)
    
    result_messages, summary = check_and_compact_if_needed(
        create_test_messages("high_context"),
        context=None,
        compact_integration=compact_integration
    )

def main():
    """Funzione principale di test."""
    print("🚀 STARTING COMPRESSION LOGGING TEST")
    print("This script will test all compression evaluation points and verify logging output.\n")
    
    # Setup logging
    setup_test_logging()
    
    try:
        # Test diversi componenti
        test_context_manager_evaluation()
        test_mcp_cleaning_evaluation()
        test_general_compaction_check()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        print("\nCheck the log output above to verify that all evaluation points")
        print("are properly logging their decisions and metrics.")
        print("\nLook for these log patterns:")
        print("🔍 - Evaluation/checking log entries")
        print("✅ - Triggered/proceeding log entries") 
        print("⏸️ - Skipped/not needed log entries")
        print("🧹 - Cleaning completed log entries")
        print("⚠️ - Warning/error log entries")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())