"""
Integration Example - Esempio completo di integrazione LLM compression

Questo file mostra come integrare il sistema di compressione LLM con il deep planning agent
esistente, fornendo un esempio end-to-end di utilizzo.
"""

import asyncio
import os
from typing import Dict, Any, List, Optional

# Import sistema esistente
from deep_planning_agent import (
    create_optimized_deep_planning_agent,
    initialize_deep_planning_mcp_tools,
    DEFAULT_MODEL
)

# Import nuovo sistema LLM compression
from llm_compression import LLMCompressor, CompressionConfig, CompressionStrategy
from context_hooks import ContextHookManager, CompressionHook, HookType, with_context_hooks
from enhanced_compact_integration import EnhancedCompactIntegration

# Import necessari per LangGraph
from deepagents.model import get_model
from deepagents.state import DeepAgentState


async def create_enhanced_deep_planning_agent(
    enable_llm_compression: bool = True,
    compression_config: Optional[CompressionConfig] = None,
    model_name: Optional[str] = None
) -> tuple:
    """
    Crea un deep planning agent enhanced con compressione LLM integrata.
    
    Args:
        enable_llm_compression: Abilita compressione LLM
        compression_config: Configurazione per compressione
        model_name: Nome del modello da usare
    
    Returns:
        Tupla (agent, enhanced_compact_integration, hook_manager)
    """
    
    print("🚀 Inizializzazione Enhanced Deep Planning Agent...")
    
    # 1. Inizializza sistema MCP esistente
    print("📡 Inizializzazione MCP tools...")
    deep_planning_tools, mcp_wrapper, original_compact_integration = initialize_deep_planning_mcp_tools()
    
    # 2. Configura modello per compressione LLM
    model = get_model(model_name or DEFAULT_MODEL or "claude-3.5-sonnet")
    print(f"🤖 Modello configurato: {model_name or DEFAULT_MODEL}")
    
    # 3. Crea sistema di compressione LLM se abilitato
    enhanced_compact_integration = None
    hook_manager = None
    
    if enable_llm_compression:
        print("🧠 Configurazione LLM compression...")
        
        # Configurazione compressione
        if compression_config is None:
            compression_config = CompressionConfig(
                strategy=CompressionStrategy.ADAPTIVE,
                target_reduction_percentage=65.0,
                max_output_tokens=2500,
                preserve_last_n_messages=3,
                enable_fallback=True
            )
        
        # Crea compressore LLM
        llm_compressor = LLMCompressor(
            model=model,
            config=compression_config,
            context_manager=mcp_wrapper.context_manager if mcp_wrapper else None
        )
        
        # Crea hook manager con configurazione automatica da YAML
        hook_manager = ContextHookManager(llm_compressor, config_path="context_config.yaml")
        
        # Crea enhanced compact integration
        enhanced_compact_integration = EnhancedCompactIntegration(
            context_manager=mcp_wrapper.context_manager if mcp_wrapper else None,
            mcp_wrapper=mcp_wrapper,
            llm_compressor=llm_compressor,
            hook_manager=hook_manager
        )
        
        print("✅ LLM compression system configured")
        print(f"   📊 Strategy: {compression_config.strategy.value}")
        print(f"   🎯 Target reduction: {compression_config.target_reduction_percentage}%")
        print(f"   ⏱️ Timeout: {compression_config.compression_timeout}s")
    
    else:
        print("⚠️ LLM compression disabled - using template system only")
        enhanced_compact_integration = original_compact_integration
    
    # 4. Crea agent con configurazione iniziale
    print("🔧 Creazione Deep Planning Agent...")
    
    initial_state = {
        "current_phase": "investigation",
        "project_id": "unknown",
        "completed_phases": [],
        "context_summary": "Enhanced deep planning session with LLM compression",
        "files": {},
        "project_domain": "software development",
        "project_type": "application",
        "investigation_focus": "comprehensive project analysis",
        
        # Enhanced state fields
        "compression_enabled": enable_llm_compression,
        "compression_strategy": compression_config.strategy.value if compression_config else "template",
        "context_cleaning_enabled": True,
        "context_session_id": enhanced_compact_integration.context_manager.session_id if enhanced_compact_integration else None
    }
    
    # Crea agent standard
    agent = create_optimized_deep_planning_agent(initial_state)
    
    # 5. Applica hook se LLM compression è abilitato
    if enable_llm_compression and hook_manager:
        print("🔗 Integrazione hook automatici...")
        
        # Wrappa nodi del grafo con hook automatici
        # Nota: questo è un esempio - l'implementazione reale dipende dalla struttura del grafo
        try:
            # Accede al grafo interno
            graph = agent.get_graph()
            
            # Hook sui nodi principali
            for node_name in graph.nodes:
                if callable(graph.nodes[node_name]):
                    original_func = graph.nodes[node_name]
                    graph.nodes[node_name] = with_context_hooks(hook_manager)(original_func)
            
            print("✅ Hook integrati nel grafo LangGraph")
            
        except Exception as e:
            print(f"⚠️ Hook integration failed: {e}")
            print("🔄 Agent running without automatic compression hooks")
    
    print("🎉 Enhanced Deep Planning Agent created successfully!")
    
    if enable_llm_compression:
        print("\n📋 Enhanced Features Active:")
        print("  ✅ LLM-based semantic compression")
        print("  ✅ Intelligent compression triggers")
        print("  ✅ Automatic fallback to template system")
        print("  ✅ Hook-based automatic integration")
        print("  ✅ Advanced performance monitoring")
        print("  ✅ Hybrid compression strategies")
    
    return agent, enhanced_compact_integration, hook_manager


async def test_compression_integration():
    """Test end-to-end dell'integrazione compressione LLM."""
    
    print("\n" + "="*60)
    print("🧪 TEST: LLM Compression Integration")
    print("="*60)
    
    # Crea agent enhanced
    agent, compact_integration, hook_manager = await create_enhanced_deep_planning_agent(
        enable_llm_compression=True
    )
    
    # Simula messaggi di test
    test_messages = [
        {"role": "user", "content": "I want to create a user authentication system for my e-commerce platform"},
        {"role": "assistant", "content": "I'll help you create a comprehensive authentication system. Let me start by investigating your project structure."},
        {"role": "assistant", "content": "I'm calling the general_list_projects tool to discover available projects..."},
        {"role": "assistant", "content": '{"projects": [{"id": "ecom-1", "name": "E-commerce Platform", "description": "Main platform"}]}'},
        {"role": "assistant", "content": "Now let me analyze the code repositories for this project..."},
        {"role": "assistant", "content": "Calling code_list_repositories with project_id ecom-1..."},
        {"role": "assistant", "content": '{"repositories": [{"id": "backend", "name": "Backend API"}, {"id": "frontend", "name": "React Frontend"}]}'},
        {"role": "user", "content": "Focus on implementing JWT authentication with refresh tokens"},
        {"role": "assistant", "content": "I'll implement JWT authentication with refresh tokens. Let me analyze the current authentication patterns in your codebase..."},
        {"role": "assistant", "content": "Searching for existing authentication code with code_find_relevant_code_snippets..."},
        {"role": "assistant", "content": '{"code_snippets": [{"file": "auth/jwt.py", "content": "class JWTManager: ..."}]}'},
        {"role": "user", "content": "Also add two-factor authentication support"},
        {"role": "assistant", "content": "I'll add 2FA support to the authentication system. This will require implementing TOTP (Time-based One-Time Password) functionality..."}
    ]
    
    # Test compressione
    print(f"\n📊 Testing compression with {len(test_messages)} messages...")
    
    if compact_integration and hasattr(compact_integration, 'perform_automatic_compaction'):
        try:
            # Test compressione automatica
            compacted_messages, summary = await compact_integration.perform_automatic_compaction(
                test_messages, {"test": True}
            )
            
            print(f"\n✅ Compression successful!")
            print(f"   📉 Messages: {len(test_messages)} → {len(compacted_messages)}")
            print(f"   🎯 Reduction: {summary.total_reduction_percentage}%")
            print(f"   🔧 Strategy: {getattr(summary, 'compression_strategy', 'unknown')}")
            print(f"   🧠 LLM used: {getattr(summary, 'llm_compression_used', False)}")
            
            if hasattr(summary, 'enhanced_metrics'):
                metrics = summary.enhanced_metrics
                print(f"   ⏱️ Processing time: {metrics.get('processing_time', 0):.3f}s")
            
            # Mostra summary content (abbreviato)
            if hasattr(summary, 'summary_content'):
                content_preview = summary.summary_content[:200] + "..." if len(summary.summary_content) > 200 else summary.summary_content
                print(f"\n📝 Summary preview:\n{content_preview}")
            
        except Exception as e:
            print(f"❌ Compression test failed: {e}")
    
    # Test hook manager se disponibile
    if hook_manager:
        print(f"\n📈 Hook Manager Statistics:")
        stats = hook_manager.get_hook_stats()
        print(f"   🔗 Registered hooks: {stats['total_registered']}")
        print(f"   ✅ Executions: {stats['total_executions']}")
        print(f"   🏃 Success rate: {stats['successful_executions']}/{stats['total_executions']}")
    
    # Statistiche enhanced
    if hasattr(compact_integration, 'get_enhanced_statistics'):
        print(f"\n📊 Enhanced Statistics:")
        enhanced_stats = compact_integration.get_enhanced_statistics()
        print(f"   🎯 Total compressions: {enhanced_stats.get('enhanced_compressions', 0)}")
        print(f"   🧠 LLM success rate: {enhanced_stats.get('llm_compression_success_rate', 0):.1f}%")
        print(f"   📈 Strategies used: {enhanced_stats.get('strategies_used', {})}")
    
    print("\n✅ Integration test completed!")


async def demonstrate_usage():
    """Dimostra l'utilizzo del sistema enhanced."""
    
    print("\n" + "="*60)
    print("📖 DEMONSTRATION: Enhanced Deep Planning Agent")
    print("="*60)
    
    # Crea agent con configurazione personalizzata
    custom_config = CompressionConfig(
        strategy=CompressionStrategy.AGGRESSIVE,
        target_reduction_percentage=75.0,
        max_output_tokens=2000,
        preserve_last_n_messages=2,
        enable_fallback=True
    )
    
    agent, compact_integration, hook_manager = await create_enhanced_deep_planning_agent(
        enable_llm_compression=True,
        compression_config=custom_config,
        model_name="claude-3.5-sonnet"
    )
    
    print("\n🎯 Agent ready for enhanced deep planning with:")
    print("   • Aggressive LLM compression (75% target reduction)")
    print("   • Automatic hook integration")
    print("   • Intelligent fallback system")
    print("   • Advanced monitoring and metrics")
    
    # Esempio di utilizzo in un workflow
    print("\n🔄 Example workflow:")
    print("1. User provides complex development request")
    print("2. Agent performs investigation with MCP tools")
    print("3. Context grows beyond threshold (80% utilization)")
    print("4. Hook automatically triggers LLM compression")
    print("5. Context compressed semantically preserving key information")
    print("6. Agent continues with optimized context")
    print("7. Process repeats as needed")
    
    return agent, compact_integration, hook_manager


async def main():
    """Funzione principale per test e dimostrazione."""
    
    print("🌟 Enhanced Deep Planning Agent - LLM Compression Integration")
    print("=" * 70)
    
    # Test integrazione
    await test_compression_integration()
    
    # Dimostrazione uso
    await demonstrate_usage()
    
    print("\n🎉 Demo completed! Enhanced Deep Planning Agent ready for production use.")
    print("\n💡 Next steps:")
    print("   1. Configure model and API keys in environment")
    print("   2. Adjust compression settings for your use case")
    print("   3. Monitor performance and tune thresholds")
    print("   4. Scale horizontally for production workloads")


if __name__ == "__main__":
    # Configura environment se necessario
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ Warning: ANTHROPIC_API_KEY not set in environment")
        print("   Set it for full LLM compression functionality")
    
    # Esegue demo
    asyncio.run(main())
