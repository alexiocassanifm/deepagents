#!/usr/bin/env python3
"""
Test Script for Deep Planning Agent Optimization

This script tests the optimized prompt system to ensure:
- Dynamic context injection works correctly
- Todo generation is context-aware
- Template variables are properly substituted
- Phase-specific configurations are applied
"""

import sys
import os
from typing import Dict, Any, List

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from optimized_prompts import (
        ORCHESTRATOR_PROMPT_TEMPLATE,
        INVESTIGATION_AGENT_PROMPT_TEMPLATE,
        AGENT_CONFIGS,
        OPTIMIZATION_STATS
    )
    from prompt_templates import (
        inject_dynamic_context,
        generate_phase_todos,
        generate_phase_context,
        get_tool_context,
        create_context_report
    )
    from prompt_config import (
        PhaseType,
        get_phase_config,
        get_phase_summary
    )
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


# ============================================================================
# MOCK DATA FOR TESTING
# ============================================================================

class MockTool:
    """Mock tool for testing purposes."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

# Create mock tools
mock_tools = [
    MockTool("General_list_projects", "List available projects"),
    MockTool("Studio_list_needs", "Get project needs"),
    MockTool("Code_find_relevant_code_snippets", "Search code semantically"),
    MockTool("General_rag_retrieve_documents", "Find documentation"),
    MockTool("read_file", "Read file contents"),
    MockTool("write_file", "Write file contents"),
    MockTool("review_plan", "Review implementation plan")
]

# Test state scenarios
test_states = {
    "initial": {
        "current_phase": "investigation",
        "project_id": "test_project",
        "completed_phases": [],
        "context_summary": "Initial project exploration",
        "files": {},
        "project_domain": "web development",
        "project_type": "e-commerce platform",
        "investigation_focus": "user authentication system"
    },
    
    "discussion": {
        "current_phase": "discussion", 
        "project_id": "test_project",
        "completed_phases": ["investigation"],
        "context_summary": "Investigation completed, requirements clarification needed",
        "files": {
            "investigation_findings.md": "Project analysis complete",
            "project_context.md": "E-commerce platform context",
            "technical_analysis.md": "React/Node.js stack"
        },
        "project_domain": "web development",
        "project_type": "e-commerce platform",
        "knowledge_gaps": ["authentication method", "payment integration"]
    },
    
    "planning": {
        "current_phase": "planning",
        "project_id": "test_project", 
        "completed_phases": ["investigation", "discussion"],
        "context_summary": "Requirements clarified, ready for planning",
        "files": {
            "investigation_findings.md": "Project analysis complete",
            "requirements_clarified.md": "OAuth and Stripe integration confirmed"
        },
        "project_domain": "web development",
        "project_type": "e-commerce platform",
        "feature_name": "User Authentication System"
    }
}


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_optimization_stats():
    """Test that optimization statistics are loaded correctly."""
    print("\n🧪 Testing Optimization Statistics...")
    
    required_keys = [
        "original_main_prompt_lines",
        "optimized_main_prompt_lines", 
        "reduction_percentage",
        "overall_reduction_percentage"
    ]
    
    for key in required_keys:
        if key not in OPTIMIZATION_STATS:
            print(f"❌ Missing optimization stat: {key}")
            return False
        print(f"✅ {key}: {OPTIMIZATION_STATS[key]}")
    
    # Verify reduction percentage calculation
    original = OPTIMIZATION_STATS["original_main_prompt_lines"]
    optimized = OPTIMIZATION_STATS["optimized_main_prompt_lines"]
    calculated_reduction = round(((original - optimized) / original) * 100)
    reported_reduction = OPTIMIZATION_STATS["reduction_percentage"]
    
    if calculated_reduction == reported_reduction:
        print(f"✅ Reduction percentage calculation verified: {reported_reduction}%")
        return True
    else:
        print(f"❌ Reduction percentage mismatch: calculated {calculated_reduction}%, reported {reported_reduction}%")
        return False


def test_template_variable_injection():
    """Test that template variables are properly injected."""
    print("\n🧪 Testing Template Variable Injection...")
    
    test_phase = "investigation"
    test_state = test_states["initial"]
    
    # Test orchestrator prompt injection
    injected_prompt = inject_dynamic_context(
        ORCHESTRATOR_PROMPT_TEMPLATE,
        test_phase,
        test_state,
        mock_tools
    )
    
    # Check that key variables were replaced
    test_variables = [
        "{current_phase}",
        "{project_id}",
        "{tool_count}",
        "{completion_percentage}"
    ]
    
    success = True
    for variable in test_variables:
        if variable in injected_prompt:
            print(f"❌ Variable not replaced: {variable}")
            success = False
        else:
            print(f"✅ Variable replaced: {variable}")
    
    # Verify some specific injections
    if "investigation" in injected_prompt:
        print("✅ Current phase correctly injected")
    else:
        print("❌ Current phase not found in injected prompt")
        success = False
    
    if "test_project" in injected_prompt:
        print("✅ Project ID correctly injected")
    else:
        print("❌ Project ID not found in injected prompt")
        success = False
    
    return success


def test_todo_generation():
    """Test dynamic todo generation for different phases."""
    print("\n🧪 Testing Dynamic Todo Generation...")
    
    success = True
    phases = ["investigation", "discussion", "planning", "task_generation"]
    
    for phase in phases:
        print(f"\n  Testing {phase} phase todos...")
        
        # Get appropriate test state
        state_key = phase if phase in test_states else "initial"
        test_state = test_states[state_key]
        
        # Generate phase context
        phase_context = generate_phase_context(phase, test_state)
        
        # Generate todos
        todos = generate_phase_todos(phase, phase_context)
        
        if not todos:
            print(f"❌ No todos generated for {phase}")
            success = False
            continue
        
        print(f"✅ Generated {len(todos)} todos for {phase}")
        
        # Verify todo structure
        for i, todo in enumerate(todos):
            required_keys = ["id", "content", "status"]
            for key in required_keys:
                if key not in todo:
                    print(f"❌ Todo {i} missing key: {key}")
                    success = False
                    continue
            
            # Check ID format
            expected_prefix = phase[:3]
            if not todo["id"].startswith(expected_prefix):
                print(f"❌ Todo ID format incorrect: {todo['id']} (expected prefix: {expected_prefix})")
                success = False
            
            # Check content not empty
            if not todo["content"].strip():
                print(f"❌ Todo content empty: {todo['id']}")
                success = False
        
        if success:
            print(f"✅ All todos for {phase} are properly structured")
            # Print first todo as example
            print(f"  Example: {todos[0]['id']}: {todos[0]['content']}")
    
    return success


def test_tool_context_generation():
    """Test tool context generation and filtering."""
    print("\n🧪 Testing Tool Context Generation...")
    
    success = True
    phases = ["investigation", "discussion", "planning", "task_generation"]
    
    for phase in phases:
        print(f"\n  Testing tool context for {phase}...")
        
        tool_context = get_tool_context(phase, mock_tools)
        
        required_keys = ["tool_count", "current_phase", "tool_categories", "phase_objectives"]
        for key in required_keys:
            if key not in tool_context:
                print(f"❌ Tool context missing key: {key}")
                success = False
            else:
                print(f"✅ {key}: {tool_context[key]}")
        
        # Verify phase-specific filtering
        if tool_context["current_phase"] != phase:
            print(f"❌ Phase mismatch in tool context: {tool_context['current_phase']} != {phase}")
            success = False
    
    return success


def test_phase_configurations():
    """Test phase configuration system."""
    print("\n🧪 Testing Phase Configurations...")
    
    success = True
    phases = [PhaseType.INVESTIGATION, PhaseType.DISCUSSION, PhaseType.PLANNING, PhaseType.TASK_GENERATION]
    
    for phase in phases:
        print(f"\n  Testing configuration for {phase.value}...")
        
        config = get_phase_config(phase)
        if not config:
            print(f"❌ No configuration found for {phase.value}")
            success = False
            continue
        
        print(f"✅ Configuration loaded for {phase.value}")
        
        # Test phase summary
        summary = get_phase_summary(phase)
        if not summary:
            print(f"❌ No summary generated for {phase.value}")
            success = False
        else:
            print(f"✅ Summary: {summary['name']} - {summary['goal']}")
    
    return success


def test_agent_configs():
    """Test agent configuration loading."""
    print("\n🧪 Testing Agent Configurations...")
    
    success = True
    expected_agents = ["investigation-agent", "discussion-agent", "planning-agent", "task-generation-agent"]
    
    for agent_name in expected_agents:
        if agent_name not in AGENT_CONFIGS:
            print(f"❌ Missing agent configuration: {agent_name}")
            success = False
            continue
        
        config = AGENT_CONFIGS[agent_name]
        required_keys = ["name", "description", "prompt_template", "tools", "outputs", "phase"]
        
        for key in required_keys:
            if key not in config:
                print(f"❌ Agent {agent_name} missing key: {key}")
                success = False
        
        if success:
            print(f"✅ Agent configuration complete: {agent_name}")
    
    return success


def test_context_report_generation():
    """Test context report generation for debugging."""
    print("\n🧪 Testing Context Report Generation...")
    
    test_phase = "investigation"
    test_state = test_states["initial"]
    
    try:
        report = create_context_report(test_phase, test_state, mock_tools)
        
        required_keys = ["phase", "tool_context", "phase_context", "completion_percentage"]
        success = True
        
        for key in required_keys:
            if key not in report:
                print(f"❌ Context report missing key: {key}")
                success = False
            else:
                print(f"✅ Context report key present: {key}")
        
        if success:
            print("✅ Context report generation successful")
            print(f"  Phase: {report['phase']}")
            print(f"  Completion: {report['completion_percentage']}%")
        
        return success
        
    except Exception as e:
        print(f"❌ Context report generation failed: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all optimization tests."""
    print("🚀 Running Deep Planning Agent Optimization Tests")
    print("=" * 60)
    
    tests = [
        ("Optimization Statistics", test_optimization_stats),
        ("Template Variable Injection", test_template_variable_injection),
        ("Todo Generation", test_todo_generation),
        ("Tool Context Generation", test_tool_context_generation),
        ("Phase Configurations", test_phase_configurations),
        ("Agent Configurations", test_agent_configs),
        ("Context Report Generation", test_context_report_generation)
    ]
    
    results = {}
    
    for test_name, test_function in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_function()
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Optimization system is working correctly.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)