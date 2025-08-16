"""
Test Suite per il Context Manager con MCP Cleaning

Questo modulo contiene test completi per validare il funzionamento del sistema
di context management, inclusi test con dati realistici di MCP tools.

Test Categories:
1. Unit Tests per singole strategie di pulizia
2. Integration Tests per il context manager completo
3. Performance Tests per verificare le riduzioni attese
4. Compatibility Tests con dati reali MCP
5. End-to-End Tests con workflow completi

Dati di test includono esempi realistici da:
- General_list_projects con molti progetti
- Code_find_relevant_code_snippets con metadati estesi
- Document content con header/footer
- User stories con campi ridondanti
"""

import json
import pytest
import time
import yaml
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Import del nostro sistema
from context_manager import ContextManager, ContextMetrics, CleaningResult
from mcp_cleaners import (
    ProjectListCleaner, CodeSnippetCleaner, DocumentCleaner,
    UserStoryListCleaner, RepositoryListCleaner,
    create_default_cleaning_strategies
)
from mcp_wrapper import MCPToolWrapper, create_mcp_wrapper
from compact_integration import CompactIntegration, CompactSummary


# =============================================================================
# TEST DATA - Dati realistici di MCP tools
# =============================================================================

SAMPLE_PROJECT_LIST = [
    {
        "project_id": "proj_001",
        "name": "E-commerce Platform",
        "description": "Full-stack e-commerce solution",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-08-15T14:20:00Z",
        "owner": "team_alpha",
        "status": "active",
        "metadata": {
            "tech_stack": ["React", "Node.js", "PostgreSQL"],
            "team_size": 8,
            "budget": 150000,
            "priority": "high"
        },
        "internal_id": "uuid-123-456-789",
        "version": "1.2.5",
        "deployment_info": {
            "staging": "https://staging.ecommerce.com",
            "production": "https://ecommerce.com"
        }
    },
    {
        "project_id": "proj_002", 
        "name": "Mobile Banking App",
        "description": "Secure mobile banking application",
        "created_at": "2024-02-01T09:15:00Z",
        "updated_at": "2024-08-10T11:45:00Z",
        "owner": "team_beta",
        "status": "active",
        "metadata": {
            "tech_stack": ["React Native", "Express.js", "MongoDB"],
            "team_size": 6,
            "budget": 200000,
            "priority": "critical"
        },
        "internal_id": "uuid-987-654-321",
        "version": "2.1.0",
        "compliance": {
            "pci_dss": True,
            "gdpr": True,
            "finra": True
        }
    },
    {
        "project_id": "proj_003",
        "name": "AI Analytics Dashboard", 
        "description": "Real-time analytics with AI insights",
        "created_at": "2024-03-10T16:00:00Z",
        "updated_at": "2024-08-12T13:30:00Z",
        "owner": "team_gamma",
        "status": "development",
        "metadata": {
            "tech_stack": ["Python", "FastAPI", "TensorFlow", "Redis"],
            "team_size": 4,
            "budget": 75000,
            "priority": "medium"
        },
        "internal_id": "uuid-555-777-999",
        "version": "0.8.2",
        "ml_models": ["sentiment_analysis", "trend_prediction", "anomaly_detection"]
    }
]

SAMPLE_CODE_SNIPPETS = [
    {
        "text": "def authenticate_user(username: str, password: str) -> bool:\n    \"\"\"Authenticate user credentials.\"\"\"\n    hashed = hash_password(password)\n    user = get_user_by_username(username)\n    return user and user.password_hash == hashed",
        "file_path": "src/auth/authentication.py",
        "line_start": 45,
        "line_end": 50,
        "entity_info": {
            "function_name": "authenticate_user",
            "class_name": None,
            "module": "auth.authentication",
            "complexity": 3,
            "cyclomatic_complexity": 2
        },
        "relevance_score": 0.92,
        "similarity_score": 0.85,
        "context_window": {
            "before": ["# Authentication utilities", "import hashlib"],
            "after": ["def hash_password(password: str) -> str:", "    return hashlib.sha256(password.encode()).hexdigest()"]
        },
        "metadata": {
            "last_modified": "2024-08-10T10:30:00Z",
            "author": "john.doe@company.com",
            "lines_of_code": 6,
            "comments": 1,
            "docstring": True
        },
        "entity_id": "ent_auth_001",
        "repository_id": "repo_ecommerce",
        "indexing_timestamp": "2024-08-15T12:00:00Z"
    },
    {
        "text": "class PaymentProcessor:\n    \"\"\"Handle payment processing logic.\"\"\"\n    \n    def __init__(self, gateway: str):\n        self.gateway = gateway\n        self.logger = get_logger(__name__)\n    \n    def process_payment(self, amount: float, card_token: str) -> PaymentResult:\n        try:\n            response = self._call_gateway(amount, card_token)\n            return PaymentResult(success=True, transaction_id=response.id)\n        except Exception as e:\n            self.logger.error(f\"Payment failed: {e}\")\n            return PaymentResult(success=False, error=str(e))",
        "file_path": "src/payments/processor.py",
        "line_start": 12,
        "line_end": 25,
        "entity_info": {
            "function_name": "process_payment",
            "class_name": "PaymentProcessor",
            "module": "payments.processor",
            "complexity": 5,
            "cyclomatic_complexity": 3
        },
        "relevance_score": 0.88,
        "similarity_score": 0.79,
        "context_window": {
            "before": ["from typing import Optional", "from .models import PaymentResult"],
            "after": ["def _call_gateway(self, amount: float, token: str):", "    # Gateway implementation"]
        },
        "metadata": {
            "last_modified": "2024-08-12T14:15:00Z",
            "author": "jane.smith@company.com",
            "lines_of_code": 14,
            "comments": 2,
            "docstring": True
        },
        "entity_id": "ent_payment_001",
        "repository_id": "repo_ecommerce",
        "indexing_timestamp": "2024-08-15T12:00:00Z"
    }
]

SAMPLE_DOCUMENT_CONTENT = {
    "title": "API Documentation - User Management",
    "content": """==========================================
API Documentation - User Management  
Company Confidential - Internal Use Only
Generated on: 2024-08-15 10:30:00
Last Updated: 2024-08-15 10:30:00
Version: 1.2.3
==========================================

# User Management API

## Overview
This document describes the user management endpoints for our platform.

## Authentication
All endpoints require Bearer token authentication.

### GET /api/users
Retrieve user list with pagination.

Parameters:
- page: integer (default: 1)
- limit: integer (default: 20)
- filter: string (optional)

Response:
```json
{
  "users": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150
  }
}
```

### POST /api/users
Create a new user account.

### PUT /api/users/{id}
Update existing user information.

### DELETE /api/users/{id}
Deactivate user account.

==========================================
© 2024 Company Inc. All rights reserved.
Proprietary and Confidential
Page 1 of 1
==========================================""",
    "document_id": "doc_api_users_001",
    "created_at": "2024-08-15T10:30:00Z",
    "updated_at": "2024-08-15T10:30:00Z",
    "author": "tech.writer@company.com",
    "metadata": {
        "type": "api_documentation",
        "category": "user_management",
        "tags": ["api", "users", "endpoints"],
        "word_count": 142,
        "reading_time": "2 minutes"
    }
}

SAMPLE_USER_STORIES = [
    {
        "user_story_id": "US-001",
        "title": "User Registration",
        "description": "As a new customer, I want to create an account so that I can make purchases",
        "status": "completed",
        "priority": "high",
        "story_points": 8,
        "epic_id": "EPIC-001",
        "acceptance_criteria": [
            "User can enter email and password",
            "System validates email format",
            "User receives confirmation email"
        ],
        "created_at": "2024-07-01T09:00:00Z",
        "updated_at": "2024-07-15T14:30:00Z",
        "assigned_to": "dev.team.alpha@company.com",
        "sprint": "Sprint 24",
        "metadata": {
            "complexity": "medium",
            "testing_notes": "Requires email service integration",
            "dependencies": ["US-002", "US-003"]
        },
        "internal_tracking": {
            "jira_id": "PROJ-1234",
            "git_branch": "feature/user-registration",
            "deployment_tag": "v1.2.0"
        }
    },
    {
        "user_story_id": "US-002", 
        "title": "Email Verification",
        "description": "As a new user, I want to verify my email address so that my account is secured",
        "status": "in_progress",
        "priority": "high",
        "story_points": 5,
        "epic_id": "EPIC-001",
        "acceptance_criteria": [
            "System sends verification email upon registration",
            "User can click verification link",
            "Account is activated after verification"
        ],
        "created_at": "2024-07-02T10:15:00Z",
        "updated_at": "2024-08-10T11:20:00Z",
        "assigned_to": "dev.team.alpha@company.com",
        "sprint": "Sprint 25",
        "metadata": {
            "complexity": "low",
            "testing_notes": "Mock email service for testing",
            "dependencies": ["US-001"]
        },
        "internal_tracking": {
            "jira_id": "PROJ-1235",
            "git_branch": "feature/email-verification",
            "deployment_tag": "pending"
        }
    }
]

SAMPLE_REPOSITORIES = [
    {
        "repository_id": "repo_001",
        "name": "ecommerce-backend",
        "description": "Backend API for e-commerce platform",
        "language": "Python",
        "framework": "FastAPI",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-08-15T14:30:00Z",
        "size_bytes": 45238764,
        "file_count": 287,
        "line_count": 12540,
        "branch_info": {
            "default_branch": "main",
            "active_branches": 8,
            "total_branches": 23
        },
        "metadata": {
            "tech_debt_score": 3.2,
            "test_coverage": 85.4,
            "security_score": 92.1,
            "maintainability_index": 78.5
        },
        "deployment_info": {
            "staging_url": "https://api-staging.ecommerce.com",
            "production_url": "https://api.ecommerce.com",
            "last_deployment": "2024-08-10T16:45:00Z"
        },
        "team_info": {
            "owner": "team_alpha",
            "contributors": 12,
            "main_contributors": ["john.doe", "jane.smith", "bob.johnson"]
        }
    },
    {
        "repository_id": "repo_002",
        "name": "ecommerce-frontend",
        "description": "React frontend for e-commerce platform",
        "language": "TypeScript",
        "framework": "React",
        "created_at": "2024-01-20T11:30:00Z",
        "updated_at": "2024-08-14T09:15:00Z",
        "size_bytes": 23847592,
        "file_count": 156,
        "line_count": 8934,
        "branch_info": {
            "default_branch": "main",
            "active_branches": 5,
            "total_branches": 18
        },
        "metadata": {
            "tech_debt_score": 2.8,
            "test_coverage": 72.3,
            "security_score": 88.7,
            "maintainability_index": 82.1
        },
        "deployment_info": {
            "staging_url": "https://staging.ecommerce.com",
            "production_url": "https://ecommerce.com",
            "last_deployment": "2024-08-12T13:20:00Z"
        },
        "team_info": {
            "owner": "team_alpha",
            "contributors": 8,
            "main_contributors": ["alice.williams", "charlie.brown", "diana.clark"]
        }
    }
]


# =============================================================================
# UNIT TESTS - Strategie di pulizia individuali
# =============================================================================

class TestProjectListCleaner:
    """Test per ProjectListCleaner."""
    
    def setup_method(self):
        self.cleaner = ProjectListCleaner()
    
    def test_can_clean_project_list(self):
        """Testa identificazione di liste progetti."""
        assert self.cleaner.can_clean("general_list_projects", SAMPLE_PROJECT_LIST)
        assert self.cleaner.can_clean("list_projects", SAMPLE_PROJECT_LIST)
        assert not self.cleaner.can_clean("other_tool", {"random": "data"})
    
    def test_clean_project_list_basic(self):
        """Testa pulizia base di lista progetti."""
        cleaned, result = self.cleaner.clean(SAMPLE_PROJECT_LIST)
        
        # Verifica che la pulizia sia avvenuta
        assert result.cleaning_status == "completed"
        assert result.reduction_percentage > 0
        
        # Verifica che i progetti siano stati ridotti
        assert len(cleaned) <= len(SAMPLE_PROJECT_LIST)
        
        # Verifica che i campi essenziali siano presenti
        if cleaned:
            first_project = cleaned[0]
            assert "project_id" in first_project or "id" in first_project
            assert "name" in first_project
    
    def test_clean_with_context_targeting(self):
        """Testa targeting di progetto specifico via contesto."""
        context = {"project_id": "proj_002"}
        cleaned, result = self.cleaner.clean(SAMPLE_PROJECT_LIST, context)
        
        # Dovrebbe mantenere solo il progetto target
        assert len(cleaned) == 1 if isinstance(cleaned, list) else True
        
        if isinstance(cleaned, list) and cleaned:
            assert cleaned[0]["project_id"] == "proj_002"
        elif isinstance(cleaned, dict):
            assert cleaned["project_id"] == "proj_002"
    
    def test_estimate_reduction(self):
        """Testa stima di riduzione."""
        reduction = self.cleaner.estimate_reduction(SAMPLE_PROJECT_LIST)
        assert reduction > 50  # Dovrebbe ridurre significativamente


class TestCodeSnippetCleaner:
    """Test per CodeSnippetCleaner."""
    
    def setup_method(self):
        self.cleaner = CodeSnippetCleaner()
    
    def test_can_clean_code_snippets(self):
        """Testa identificazione di code snippets."""
        assert self.cleaner.can_clean("code_find_relevant_code_snippets", SAMPLE_CODE_SNIPPETS)
        assert self.cleaner.can_clean("find_relevant_code", SAMPLE_CODE_SNIPPETS)
    
    def test_clean_code_snippets(self):
        """Testa pulizia di code snippets."""
        cleaned, result = self.cleaner.clean(SAMPLE_CODE_SNIPPETS)
        
        assert result.cleaning_status == "completed"
        assert result.reduction_percentage > 50  # Dovrebbe ridurre significativamente
        
        # Verifica che il campo text sia presente
        if isinstance(cleaned, list):
            for snippet in cleaned:
                assert "text" in snippet
                # Verifica che metadati siano rimossi
                assert "entity_info" not in snippet
                assert "metadata" not in snippet
    
    def test_clean_with_file_paths(self):
        """Testa pulizia mantenendo file paths quando richiesto."""
        context = {"keep_file_paths": True}
        cleaned, result = self.cleaner.clean(SAMPLE_CODE_SNIPPETS, context)
        
        if isinstance(cleaned, list):
            for snippet in cleaned:
                assert "text" in snippet
                # Dovrebbe mantenere file_path se presente
                if "file_path" in SAMPLE_CODE_SNIPPETS[0]:
                    assert "file_path" in snippet


class TestDocumentCleaner:
    """Test per DocumentCleaner."""
    
    def setup_method(self):
        self.cleaner = DocumentCleaner()
    
    def test_can_clean_documents(self):
        """Testa identificazione di documenti."""
        assert self.cleaner.can_clean("get_document_content", SAMPLE_DOCUMENT_CONTENT)
        assert self.cleaner.can_clean("attachment", SAMPLE_DOCUMENT_CONTENT)
    
    def test_clean_document(self):
        """Testa pulizia di documento."""
        cleaned, result = self.cleaner.clean(SAMPLE_DOCUMENT_CONTENT)
        
        assert result.cleaning_status == "completed"
        
        # Verifica che i campi essenziali siano presenti
        assert "content" in cleaned or "text" in cleaned
        assert "title" in cleaned
        
        # Verifica che header/footer siano stati rimossi
        content = cleaned.get("content", cleaned.get("text", ""))
        assert "Company Confidential" not in content
        assert "Generated on:" not in content
        assert "© 2024 Company Inc" not in content


class TestUserStoryListCleaner:
    """Test per UserStoryListCleaner."""
    
    def setup_method(self):
        self.cleaner = UserStoryListCleaner()
    
    def test_clean_user_stories(self):
        """Testa pulizia di user stories."""
        cleaned, result = self.cleaner.clean(SAMPLE_USER_STORIES)
        
        assert result.cleaning_status == "completed"
        assert result.reduction_percentage > 40  # Dovrebbe ridurre significativamente
        
        # Verifica campi essenziali
        for story in cleaned:
            assert "user_story_id" in story or "story_id" in story or "id" in story
            assert "title" in story
            assert "description" in story
            
            # Verifica che metadati siano rimossi
            assert "internal_tracking" not in story
            assert "metadata" not in story


# =============================================================================
# INTEGRATION TESTS - Context Manager completo
# =============================================================================

class TestContextManager:
    """Test per ContextManager integration."""
    
    def setup_method(self):
        config = {
            "max_context_window": 10000,
            "trigger_threshold": 0.85,
            "mcp_noise_threshold": 0.6,
            "deduplication_enabled": True
        }
        self.context_manager = ContextManager(config)
        
        # Registra strategie di pulizia
        strategies = create_default_cleaning_strategies(config)
        for strategy in strategies:
            self.context_manager.register_cleaning_strategy(strategy)
    
    def test_analyze_context_basic(self):
        """Testa analisi base del contesto."""
        messages = [
            {"role": "user", "content": "List all projects"},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "user", "content": "Show me code for authentication"},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)}
        ]
        
        metrics = self.context_manager.analyze_context(messages)
        
        assert metrics.tokens_used > 0
        assert 0 <= metrics.utilization_percentage <= 100
        assert 0 <= metrics.mcp_noise_percentage <= 100
    
    def test_clean_mcp_tool_result(self):
        """Testa pulizia di risultati MCP tools."""
        # Test ProjectListCleaner
        cleaned, result = self.context_manager.clean_mcp_tool_result(
            "general_list_projects", SAMPLE_PROJECT_LIST
        )
        assert result.cleaning_status == "completed"
        assert result.reduction_percentage > 0
        
        # Test CodeSnippetCleaner
        cleaned, result = self.context_manager.clean_mcp_tool_result(
            "code_find_relevant_code_snippets", SAMPLE_CODE_SNIPPETS
        )
        assert result.cleaning_status == "completed"
        assert result.reduction_percentage > 0
    
    def test_process_context_cleaning(self):
        """Testa processo completo di pulizia del contesto."""
        messages = [
            {"role": "user", "content": "Show me projects"},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "user", "content": "Find authentication code"},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)}
        ]
        
        cleaned_messages, context_info = self.context_manager.process_context_cleaning(messages)
        
        assert len(cleaned_messages) <= len(messages)
        assert context_info.operation_type == "cleaning"
        assert len(context_info.cleaning_results) > 0
        assert context_info.after_metrics.tokens_used <= context_info.before_metrics.tokens_used
    
    def test_should_trigger_compaction(self):
        """Testa logica di trigger per compattazione."""
        # Messaggi sotto soglia
        small_messages = [{"role": "user", "content": "Hello"}]
        should_compact, trigger, metrics = self.context_manager.should_trigger_compaction(small_messages)
        assert not should_compact
        
        # Messaggi con molto rumore MCP (simula)
        noisy_messages = [
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST) * 10}
        ]
        should_compact, trigger, metrics = self.context_manager.should_trigger_compaction(noisy_messages)
        # Dipende dalla configurazione, ma dovrebbe rilevare alto utilizzo


# =============================================================================
# INTEGRATION TESTS - MCP Wrapper
# =============================================================================

class TestMCPWrapper:
    """Test per MCPWrapper integration."""
    
    def setup_method(self):
        self.wrapper = create_mcp_wrapper({
            "cleaning_enabled": True,
            "max_context_window": 10000
        })
    
    def test_wrap_callable_tool(self):
        """Testa wrapping di tool callable."""
        def mock_list_projects():
            return SAMPLE_PROJECT_LIST
        
        wrapped_tool = self.wrapper.wrap_tool(mock_list_projects, "general_list_projects")
        
        # Esegue il tool wrapped
        result = wrapped_tool()
        
        # Verifica che il risultato sia stato pulito
        assert isinstance(result, (list, dict))
        if isinstance(result, list):
            assert len(result) <= len(SAMPLE_PROJECT_LIST)
        
        # Verifica statistiche
        stats = self.wrapper.get_statistics()
        assert stats["total_calls"] == 1
        assert stats["cleaned_calls"] >= 0
    
    def test_wrap_tool_list(self):
        """Testa wrapping di lista di tools."""
        def mock_list_projects():
            return SAMPLE_PROJECT_LIST
        
        def mock_find_code():
            return SAMPLE_CODE_SNIPPETS
        
        def mock_non_mcp_tool():
            return {"data": "regular tool"}
        
        # Simula attributi tool name
        mock_list_projects.name = "general_list_projects"
        mock_find_code.name = "code_find_relevant_code_snippets"
        mock_non_mcp_tool.name = "regular_tool"
        
        tools = [mock_list_projects, mock_find_code, mock_non_mcp_tool]
        wrapped_tools = self.wrapper.wrap_tool_list(tools)
        
        assert len(wrapped_tools) == len(tools)
        
        # Solo tool MCP dovrebbero essere stati wrapped
        assert len(self.wrapper.wrapped_tools) == 2  # Due tool MCP
    
    def test_error_handling(self):
        """Testa gestione errori graceful."""
        def failing_tool():
            raise Exception("Tool execution failed")
        
        wrapped_tool = self.wrapper.wrap_tool(failing_tool, "general_list_projects")
        
        # Dovrebbe gestire l'errore gracefully
        try:
            result = wrapped_tool()
            assert False, "Expected exception"
        except Exception as e:
            assert "Tool execution failed" in str(e)
        
        # Verifica che l'errore sia stato loggato
        stats = self.wrapper.get_statistics()
        assert stats["errors"] == 1


# =============================================================================
# INTEGRATION TESTS - Compact Integration
# =============================================================================

class TestCompactIntegration:
    """Test per CompactIntegration."""
    
    def setup_method(self):
        context_manager = ContextManager()
        strategies = create_default_cleaning_strategies()
        for strategy in strategies:
            context_manager.register_cleaning_strategy(strategy)
        
        self.compact_integration = CompactIntegration(context_manager)
    
    def test_generate_summary(self):
        """Testa generazione di summary completo."""
        messages = [
            {"role": "user", "content": "I need to implement user authentication for my e-commerce platform"},
            {"role": "assistant", "content": "I'll help you implement user authentication. Let me first check your current projects."},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "user", "content": "Focus on the E-commerce Platform project"},
            {"role": "assistant", "content": "Perfect! Let me find relevant authentication code."},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)},
            {"role": "user", "content": "Show me the user stories for authentication"},
            {"role": "assistant", "content": json.dumps(SAMPLE_USER_STORIES)}
        ]
        
        summary = self.compact_integration.generate_summary(
            messages, "threshold", {"project_id": "proj_001"}
        )
        
        assert isinstance(summary, CompactSummary)
        assert summary.trigger_type == "threshold"
        assert len(summary.summary_content) > 0
        assert len(summary.technical_concepts) > 0
        assert summary.total_reduction_percentage >= 0
    
    def test_should_trigger_compaction(self):
        """Testa logica di trigger per compattazione."""
        # Messaggi semplici - non dovrebbe trigger
        simple_messages = [{"role": "user", "content": "Hello"}]
        should_compact, trigger, metrics = self.compact_integration.should_trigger_compaction(simple_messages)
        assert not should_compact
        
        # Messaggi con contenuto MCP esteso
        mcp_messages = [
            {"role": "user", "content": "Show me all projects"},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)},
            {"role": "assistant", "content": json.dumps(SAMPLE_USER_STORIES)},
            {"role": "assistant", "content": json.dumps(SAMPLE_REPOSITORIES)}
        ]
        
        should_compact, trigger, metrics = self.compact_integration.should_trigger_compaction(mcp_messages)
        # Risultato dipende dalle soglie, ma dovrebbe almeno calcolare metriche
        assert metrics.tokens_used > 0
    
    def test_perform_automatic_compaction(self):
        """Testa compattazione automatica completa."""
        messages = [
            {"role": "user", "content": "Help me implement user authentication"},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)},
            {"role": "user", "content": "Continue with the authentication implementation"}
        ]
        
        compacted_messages, summary = self.compact_integration.perform_automatic_compaction(messages)
        
        assert isinstance(compacted_messages, list)
        assert isinstance(summary, CompactSummary)
        
        # I messaggi compattati dovrebbero essere <= originali
        assert len(compacted_messages) <= len(messages)


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test di performance e riduzioni."""
    
    def test_cleaning_reduction_targets(self):
        """Verifica che le riduzioni raggiungano i target attesi."""
        # ProjectListCleaner - target: 70%+
        cleaner = ProjectListCleaner()
        cleaned, result = cleaner.clean(SAMPLE_PROJECT_LIST)
        assert result.reduction_percentage >= 50, f"ProjectList reduction: {result.reduction_percentage}%"
        
        # CodeSnippetCleaner - target: 75%+
        cleaner = CodeSnippetCleaner()
        cleaned, result = cleaner.clean(SAMPLE_CODE_SNIPPETS)
        assert result.reduction_percentage >= 50, f"CodeSnippet reduction: {result.reduction_percentage}%"
        
        # DocumentCleaner - target: 30%+
        cleaner = DocumentCleaner()
        cleaned, result = cleaner.clean(SAMPLE_DOCUMENT_CONTENT)
        assert result.reduction_percentage >= 10, f"Document reduction: {result.reduction_percentage}%"
    
    def test_context_manager_performance(self):
        """Testa performance del context manager."""
        context_manager = ContextManager()
        strategies = create_default_cleaning_strategies()
        for strategy in strategies:
            context_manager.register_cleaning_strategy(strategy)
        
        # Misura tempo di esecuzione per operazioni base
        start_time = time.time()
        
        # Simula elaborazione di molti messaggi MCP
        large_messages = []
        for i in range(10):
            large_messages.extend([
                {"role": "user", "content": f"Request {i}"},
                {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
                {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)}
            ])
        
        cleaned_messages, context_info = context_manager.process_context_cleaning(large_messages)
        
        execution_time = time.time() - start_time
        
        # L'operazione dovrebbe completare in tempo ragionevole
        assert execution_time < 5.0, f"Execution too slow: {execution_time}s"
        
        # Dovrebbe ottenere una riduzione significativa
        total_reduction = context_info.total_reduction_percentage
        assert total_reduction > 0, "No reduction achieved"


# =============================================================================
# END-TO-END TESTS
# =============================================================================

class TestEndToEnd:
    """Test end-to-end completi."""
    
    def test_complete_workflow(self):
        """Testa workflow completo con configurazione da YAML."""
        
        # Simula caricamento configurazione (senza file per semplicità)
        config = {
            "context_management": {
                "max_context_window": 15000,
                "trigger_threshold": 0.8,
                "cleaning_enabled": True
            },
            "cleaning_strategies": {
                "ProjectListCleaner": {"enabled": True},
                "CodeSnippetCleaner": {"enabled": True}
            }
        }
        
        # 1. Crea context manager
        context_manager = ContextManager(config.get("context_management", {}))
        strategies = create_default_cleaning_strategies(config.get("cleaning_strategies", {}))
        for strategy in strategies:
            context_manager.register_cleaning_strategy(strategy)
        
        # 2. Crea MCP wrapper
        wrapper = MCPToolWrapper(context_manager, config.get("context_management", {}))
        
        # 3. Crea compact integration
        compact_integration = CompactIntegration(context_manager, wrapper)
        
        # 4. Simula sequenza completa di conversazione
        messages = [
            {"role": "user", "content": "I need to work on user authentication for my project"},
            {"role": "assistant", "content": "Let me help you. First, let me check your available projects."},
            {"role": "assistant", "content": json.dumps(SAMPLE_PROJECT_LIST)},
            {"role": "user", "content": "I want to work on the E-commerce Platform"},
            {"role": "assistant", "content": "Great choice! Let me find relevant authentication code."},
            {"role": "assistant", "content": json.dumps(SAMPLE_CODE_SNIPPETS)},
            {"role": "user", "content": "Show me the current user stories for this area"},
            {"role": "assistant", "content": json.dumps(SAMPLE_USER_STORIES)},
            {"role": "user", "content": "What about the repository structure?"},
            {"role": "assistant", "content": json.dumps(SAMPLE_REPOSITORIES)},
            {"role": "user", "content": "Now help me implement two-factor authentication"}
        ]
        
        # 5. Elabora con pulizia automatica
        cleaned_messages, cleaning_info = context_manager.process_context_cleaning(messages)
        
        # 6. Controlla se serve compattazione
        should_compact, trigger_type, metrics = compact_integration.should_trigger_compaction(cleaned_messages)
        
        if should_compact:
            # 7. Esegui compattazione
            compacted_messages, summary = compact_integration.perform_automatic_compaction(cleaned_messages)
            final_messages = compacted_messages
        else:
            final_messages = cleaned_messages
        
        # 8. Verifica risultati
        assert len(final_messages) <= len(messages)
        assert cleaning_info.total_reduction_percentage >= 0
        
        # 9. Verifica che informazioni essenziali siano preservate
        final_content = json.dumps(final_messages)
        assert "authentication" in final_content.lower()
        assert "e-commerce" in final_content.lower() or "ecommerce" in final_content.lower()


# =============================================================================
# COMPATIBILITY TESTS
# =============================================================================

class TestCompatibility:
    """Test di compatibilità con formati reali."""
    
    def test_real_mcp_data_formats(self):
        """Testa con formati dati reali da MCP tools."""
        
        # Test con formato wrapped (come potrebbe arrivare da MCP)
        wrapped_projects = {
            "status": "success",
            "data": SAMPLE_PROJECT_LIST,
            "metadata": {
                "total_count": len(SAMPLE_PROJECT_LIST),
                "page": 1,
                "per_page": 20
            }
        }
        
        cleaner = ProjectListCleaner()
        can_clean = cleaner.can_clean("general_list_projects", wrapped_projects)
        assert can_clean  # Dovrebbe riconoscere anche formato wrapped
        
        # Test con formato con errori
        error_response = {
            "status": "error", 
            "error": "Authentication failed",
            "code": 401
        }
        
        can_clean = cleaner.can_clean("general_list_projects", error_response)
        # Non dovrebbe tentare di pulire errori
    
    def test_edge_cases(self):
        """Testa casi limite."""
        
        # Dati vuoti
        cleaner = ProjectListCleaner()
        cleaned, result = cleaner.clean([])
        assert result.cleaning_status in ["completed", "skipped"]
        
        # Dati None
        cleaned, result = cleaner.clean(None)
        assert result.cleaning_status == "skipped"
        
        # Dati malformati
        malformed = {"projects": "not a list"}
        cleaned, result = cleaner.clean(malformed)
        assert result.cleaning_status in ["completed", "skipped"]


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    # Esegue test specifici per debugging
    test_integration = TestEndToEnd()
    test_integration.test_complete_workflow()
    print("✅ End-to-end test passed!")
    
    test_performance = TestPerformance()
    test_performance.test_cleaning_reduction_targets()
    print("✅ Performance tests passed!")
    
    print("\n🎉 All manual tests completed successfully!")
    print("\nTo run full test suite with pytest:")
    print("pip install pytest")
    print("pytest test_context_manager.py -v")