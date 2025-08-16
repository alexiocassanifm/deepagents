#!/usr/bin/env python3
"""
Test del sistema di logging avanzato per context manager e MCP wrapper.

Questo script dimostra i nuovi log informativi che mostrano:
- Lunghezza del contesto prima e dopo ogni chiamata tool
- Operazioni di pulizia e compressione applicate
- Trigger di compattazione automatica
- Statistiche dettagliate di riduzione
"""

import json
import logging
import sys
from typing import Dict, Any

# Configurazione logging per vedere tutti i dettagli
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def mock_mcp_tool_general_list_projects() -> Dict[str, Any]:
    """Mock tool che simula General_list_projects con risultato realistico."""
    return [
        {
            "name": "FairMind Studio",
            "type": "web",
            "description": "Un'applicazione web per la gestione di requisiti e user stories con integrazione di agenti AI. Il progetto include metodologia Agile e supporto per sessioni di lavoro collaborative.",
            "documents": ["requirements.pdf", "architecture.md", "user_guide.md"],
            "images": ["mockup1.png", "diagram.svg"],
            "userId": "d68e2280-c091-70d6-4ba8-d1aca9f04975",
            "company": "674db9c2e139cb75dccac682",
            "createdAt": "2024-12-15T18:19:02.040000",
            "updatedAt": "2024-12-15T18:19:02.040000",
            "__v": 0,
            "id": "675f1d96f417109894d938fb",
            "repositories": [
                {
                    "id": "repo1",
                    "name": "mindstream-reqs-studio",
                    "type": "frontend",
                    "language": "TypeScript"
                },
                {
                    "id": "repo2", 
                    "name": "fm-agents",
                    "type": "backend",
                    "language": "Python"
                }
            ]
        },
        {
            "name": "Mobile Task Manager",
            "type": "mobile",
            "description": "App mobile per gestione task con sincronizzazione cloud",
            "documents": [],
            "images": [],
            "userId": "another-user-id",
            "company": "674db9c2e139cb75dccac682",
            "createdAt": "2024-12-10T10:00:00.000000",
            "updatedAt": "2024-12-10T10:00:00.000000",
            "__v": 0,
            "id": "675f1d96f417109894d938fc"
        }
    ]

def mock_mcp_tool_code_find_snippets() -> Dict[str, Any]:
    """Mock tool che simula Code_find_relevant_code_snippets con risultato verboso."""
    return {
        "results": [
            {
                "file_path": "src/components/WorkSessionSelector.tsx",
                "line_numbers": [25, 50],
                "content": "export const WorkSessionSelector: React.FC<Props> = ({ projectId, onSessionSelect }) => {\n  const [sessions, setSessions] = useState<WorkSession[]>([]);\n  const [loading, setLoading] = useState(true);\n  \n  useEffect(() => {\n    const fetchSessions = async () => {\n      try {\n        const result = await getWorkSessions(projectId, userId, studioId);\n        if (result.success) {\n          setSessions(result.data);\n        }\n      } catch (error) {\n        console.error('Error fetching sessions:', error);\n      } finally {\n        setLoading(false);\n      }\n    };\n    \n    fetchSessions();\n  }, [projectId, userId, studioId]);\n  \n  return (\n    <div className=\"work-session-selector\">\n      {loading ? (\n        <Spinner />\n      ) : (\n        <SessionList sessions={sessions} onSelect={onSessionSelect} />\n      )}\n    </div>\n  );\n};",
                "relevance_score": 0.95,
                "metadata": {
                    "function_name": "WorkSessionSelector",
                    "component_type": "React.FC",
                    "imports": ["useState", "useEffect"],
                    "dependencies": ["getWorkSessions", "WorkSession"],
                    "last_modified": "2024-12-15T10:30:00Z",
                    "file_size": 2048,
                    "lines_count": 85
                },
                "entity_id": "tsx_component_work_session_selector_123"
            },
            {
                "file_path": "src/hooks/useWorkSessionStore.ts", 
                "line_numbers": [10, 35],
                "content": "export const useWorkSessionStore = create<WorkSessionStore>((set, get) => ({\n  currentSession: null,\n  sessions: [],\n  loading: false,\n  \n  setCurrentSession: (session: WorkSession | null) => {\n    set({ currentSession: session });\n  },\n  \n  addSession: (session: WorkSession) => {\n    set((state) => ({\n      sessions: [...state.sessions, session]\n    }));\n  },\n  \n  updateSession: (sessionId: string, updates: Partial<WorkSession>) => {\n    set((state) => ({\n      sessions: state.sessions.map(s => \n        s.mindstreamId === sessionId ? { ...s, ...updates } : s\n      )\n    }));\n  },\n  \n  removeSession: (sessionId: string) => {\n    set((state) => ({\n      sessions: state.sessions.filter(s => s.mindstreamId !== sessionId)\n    }));\n  }\n}));",
                "relevance_score": 0.88,
                "metadata": {
                    "function_name": "useWorkSessionStore",
                    "hook_type": "zustand",
                    "state_properties": ["currentSession", "sessions", "loading"],
                    "actions": ["setCurrentSession", "addSession", "updateSession", "removeSession"],
                    "last_modified": "2024-12-14T16:45:00Z",
                    "file_size": 1024,
                    "lines_count": 45
                },
                "entity_id": "hook_work_session_store_456"
            }
        ],
        "total_results": 2,
        "search_metadata": {
            "query": "work session management",
            "repository": "mindstream-reqs-studio",
            "search_time_ms": 245,
            "total_files_scanned": 156,
            "matching_files": 8
        }
    }

def test_enhanced_logging():
    """Test del sistema di logging avanzato."""
    print("🚀 Testing Enhanced Logging System for Context Manager")
    print("=" * 60)
    
    try:
        # Import dei moduli con nuovo logging
        from mcp_wrapper import create_mcp_wrapper
        from context_manager import ContextManager
        
        print("✅ Modules imported successfully")
        
        # Crea wrapper con configurazione di test
        config = {
            "cleaning_enabled": True,
            "max_context_window": 50000,  # Più piccolo per test
            "trigger_threshold": 0.70,    # Soglia più bassa per trigger test
            "mcp_noise_threshold": 0.50,
            "deduplication_enabled": True,
            "preserve_essential_fields": True,
            "auto_compaction": True
        }
        
        wrapper = create_mcp_wrapper(config)
        print("✅ MCP Wrapper created with enhanced logging")
        
        # Test 1: Tool con risultato grande (dovrebbe essere pulito)
        print("\n📋 TEST 1: Large MCP Tool Result (should trigger cleaning)")
        print("-" * 50)
        
        def mock_general_list_projects():
            return mock_mcp_tool_general_list_projects()
        
        # Wrappa il mock tool
        wrapped_tool = wrapper.wrap_tool(mock_general_list_projects, "General_list_projects")
        
        # Esegui il tool - dovrebbe vedere log dettagliati
        result1 = wrapped_tool()
        print(f"📊 Result size: {len(json.dumps(result1, default=str)):,} characters")
        
        # Test 2: Tool con risultato molto grande (dovrebbe triggerare compattazione)
        print("\n📋 TEST 2: Very Large MCP Tool Result (should trigger compaction)")
        print("-" * 50)
        
        def mock_code_find_snippets():
            return mock_mcp_tool_code_find_snippets()
        
        wrapped_tool2 = wrapper.wrap_tool(mock_code_find_snippets, "Code_find_relevant_code_snippets")
        result2 = wrapped_tool2()
        print(f"📊 Result size: {len(json.dumps(result2, default=str)):,} characters")
        
        # Test 3: Mostra statistiche finali
        print("\n📊 FINAL STATISTICS")
        print("-" * 50)
        
        stats = wrapper.get_statistics()
        context_summary = wrapper.context_manager.get_context_summary()
        
        print(f"🔧 Total tool calls: {stats['total_calls']}")
        print(f"🧹 Cleaned calls: {stats['cleaned_calls']}")
        print(f"📉 Average reduction: {stats['average_reduction_percentage']:.1f}%")
        print(f"❌ Errors: {stats['errors']}")
        print(f"📋 Context operations: {context_summary.get('total_operations', 0)}")
        print(f"🎯 Current utilization: {context_summary.get('current_utilization', 0):.1f}%")
        print(f"🔊 Current MCP noise: {context_summary.get('current_mcp_noise', 0):.1f}%")
        
        # Test 4: Mostra chiamate recenti con dettagli
        print("\n📝 RECENT CALLS DETAILS")
        print("-" * 50)
        
        recent_calls = wrapper.get_recent_calls(5)
        for i, call in enumerate(recent_calls, 1):
            print(f"Call {i}: {call['tool_name']}")
            print(f"  📊 Size: {call['original_size']:,} → {call['cleaned_size']:,} chars")
            if 'cleaning_info' in call:
                cleaning = call['cleaning_info']
                print(f"  🧹 Strategy: {cleaning.get('strategy_used', 'Unknown')}")
                print(f"  📉 Reduction: {cleaning.get('reduction_percentage', 0):.1f}%")
            print(f"  ⏱️ Time: {call['execution_time']:.3f}s")
            print()
        
        print("✅ Enhanced logging test completed successfully!")
        print("\n🎯 What to look for in the logs above:")
        print("   🔧 MCP Tool Call notifications")
        print("   📊 Pre/Post execution context metrics")
        print("   🧹 Cleaning operations with reduction percentages")
        print("   🔍 Strategy selection for each tool")
        print("   🔄 Compaction triggers (if thresholds exceeded)")
        print("   📈 Real-time context utilization tracking")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running from the deep_planning directory")
        return False
    except Exception as e:
        print(f"❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_enhanced_logging()
    sys.exit(0 if success else 1)