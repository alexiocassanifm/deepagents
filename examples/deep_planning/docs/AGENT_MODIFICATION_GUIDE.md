# Agent Modification Guide

Una guida completa per modificare l'agente principale e i subagents nel sistema Deep Planning Agent.

## Panoramica del Sistema

Il Deep Planning Agent implementa un'architettura modulare a 4 fasi con un sistema di prompts ottimizzato che ha ottenuto una **riduzione del 91%** nella lunghezza dei prompts mantenendo la piena funzionalità.

### 🏗️ Architettura Principale

```
Agent Principale (Orchestratore)
├── 🔍 Investigation Agent - Fase 1
├── 💬 Discussion Agent - Fase 2  
├── 📋 Planning Agent - Fase 3
└── ⚡ Task Generation Agent - Fase 4
```

### 📁 File Chiave per le Modifiche

- **`src/config/prompt_config.py`** - Configurazioni delle fasi e regole di validazione
- **`src/config/optimized_prompts.py`** - Template dei prompts per tutti gli agenti
- **`src/config/prompt_templates.py`** - Sistema di iniezione dinamica del contesto
- **`src/core/agent_factory.py`** - Factory semplificata per la creazione degli agenti
- **`src/core/agent_core.py`** - Punto di ingresso principale

## 🎯 Modifica dell'Agente Principale (Orchestratore)

### Prompt dell'Orchestratore

Il prompt principale si trova in **`src/config/optimized_prompts.py`**:

```python
ORCHESTRATOR_PROMPT_TEMPLATE = """You are the Deep Planning Orchestrator - coordinator of the 4-phase structured development methodology.

## Mission
Transform user requests into implementation-ready plans through methodical phase execution with todo tracking.

## Current Context
- Phase: {current_phase}
- Progress: {completion_percentage}%
- Project ID: {project_id}
- Available Tools: {tool_count}

## Process Flow
Phase 1: Investigation → Deploy investigation-agent for autonomous exploration
Phase 2: Discussion → Deploy discussion-agent for requirements clarification  
Phase 3: Planning → Deploy planning-agent for 8-section plan creation
Phase 4: Task Generation → Deploy task-generation-agent for implementation setup

## Your Role
- Deploy appropriate sub-agent for current phase
- Validate phase completion before transitions
- Maintain state consistency across phases
- Manage human interaction points (questions, approvals)
- Track overall process progress
...
"""
```

### Come Modificare il Comportamento dell'Orchestratore

**1. Aggiungere nuove responsabilità:**
```python
## Your Role
- Deploy appropriate sub-agent for current phase
- Validate phase completion before transitions
- Maintain state consistency across phases
- Manage human interaction points (questions, approvals)
- Track overall process progress
- [NUOVA RESPONSABILITA]: Monitor performance metrics
- [NUOVA RESPONSABILITA]: Handle error recovery scenarios
```

**2. Modificare i criteri di transizione tra fasi:**
```python
## Phase Transition Criteria
- Investigation → Discussion: Project context fully documented AND security analysis complete
- Discussion → Planning: Requirements clarified and documented AND technical constraints identified
- Planning → Task Generation: Plan approved by human AND risk assessment approved
- Task Generation → Complete: Implementation tasks generated AND deployment plan ready
```

**3. Aggiungere variabili di contesto personalizzate:**

In `src/config/prompt_templates.py`, funzione `inject_dynamic_context()`:
```python
full_context = {
    **tool_context,
    **phase_context,
    "current_phase": phase,
    "completed_phases": ", ".join(state.get("completed_phases", [])),
    # AGGIUNGI NUOVE VARIABILI:
    "security_score": state.get("security_score", "not_assessed"),
    "technical_risk": state.get("technical_risk", "medium"),
    "team_size": state.get("team_size", "unknown"),
    "budget_constraints": state.get("budget_constraints", "none specified")
}
```

## 🤖 Modifica dei Subagents

### Struttura dei Subagents

Ogni subagent è definito in **`src/config/optimized_prompts.py`** nella sezione `AGENT_CONFIGS`:

```python
AGENT_CONFIGS = {
    "investigation-agent": {
        "name": "investigation-agent",
        "description": "Phase 1: Autonomous project exploration and context gathering without user interaction",
        "prompt_template": INVESTIGATION_AGENT_PROMPT_TEMPLATE,
        "tools": ["General_list_projects", "Studio_list_needs", ...],
        "outputs": ["investigation_findings.md", "project_context.md", "technical_analysis.md"],
        "phase": "investigation",
        "requires_user_input": False,
        "validation_criteria": [...]
    },
    # ... altri agenti
}
```

### Come Modificare un Subagent Esistente

**Esempio: Migliorare l'Investigation Agent**

1. **Modificare il prompt template:**
```python
INVESTIGATION_AGENT_PROMPT_TEMPLATE = """You are the Investigation Agent - Phase 1 autonomous project explorer.

## Mission
Silently explore project {project_id} using {tool_categories} without user interaction.

## NEW: Security Focus
- Analyze security patterns in codebase
- Identify potential vulnerabilities
- Document security architecture decisions

## Investigation Focus
{investigation_focus}

## Process
1. Start with project discovery using available tools
2. Systematically explore each discovered area
3. Focus on understanding, not implementation
4. Document everything for next phases
5. NEW: Perform security assessment

## NEW: Security Analysis Tasks
1. Review authentication mechanisms
2. Analyze data encryption patterns  
3. Check for security best practices
4. Document security concerns

## Tool Categories Available
{tool_categories}
...
"""
```

2. **Aggiungere nuovi strumenti:**
```python
"tools": [
    "General_list_projects", 
    "Studio_list_needs", 
    "Studio_list_user_stories", 
    "Code_list_repositories", 
    "Code_get_directory_structure", 
    "Code_find_relevant_code_snippets", 
    "General_rag_retrieve_documents",
    # NUOVI STRUMENTI:
    "Security_scan_vulnerabilities",
    "Code_analyze_security_patterns"
],
```

3. **Aggiungere nuovi output:**
```python
"outputs": [
    "investigation_findings.md", 
    "project_context.md", 
    "technical_analysis.md",
    # NUOVO OUTPUT:
    "security_assessment.md"
],
```

4. **Aggiornare i criteri di validazione:**
```python
"validation_criteria": [
    "All available projects explored",
    "Repository structure documented", 
    "Requirements gathered and analyzed",
    "Technical patterns identified",
    "Findings documented in required files",
    # NUOVO CRITERIO:
    "Security assessment completed"
]
```

## ➕ Aggiungere un Nuovo Subagent

### Passo 1: Definire la Nuova Fase

In **`src/config/prompt_config.py`**, aggiungi alla enum `PhaseType`:

```python
class PhaseType(Enum):
    """Enumeration of deep planning phases."""
    INVESTIGATION = "investigation"
    DISCUSSION = "discussion"
    PLANNING = "planning"
    TASK_GENERATION = "task_generation"
    SECURITY_REVIEW = "security_review"  # NUOVA FASE
    COMPLETE = "complete"
```

### Passo 2: Creare la Configurazione della Fase

```python
# Security Review Phase Configuration
SECURITY_REVIEW_PHASE_CONFIG = PhaseConfig(
    name="Security Review",
    phase_type=PhaseType.SECURITY_REVIEW,
    emoji="🔒",
    goal="Comprehensive security analysis and risk assessment",
    agent_name="security-review-agent",
    duration_estimate="15-25 minutes",
    completion_weight=85,
    requires_user_input=True,  # Per approvazione delle misure di sicurezza
    requires_approval=True,
    
    required_tool_categories=[
        ToolCategory.CODE_ANALYSIS,
        ToolCategory.VALIDATION,
        ToolCategory.APPROVAL
    ],
    optional_tool_categories=[
        ToolCategory.DOCUMENTATION
    ],
    
    required_outputs=[
        "security_analysis.md",
        "vulnerability_report.md",
        "security_recommendations.md"
    ],
    optional_outputs=[
        "threat_model.md",
        "compliance_checklist.md"
    ],
    
    validation_level=ValidationLevel.STRICT,
    validation_rules=[
        ValidationRule(
            name="security_scan_complete",
            description="Comprehensive security scan must be performed",
            required=True,
            validation_function="validate_security_scan",
            error_message="Security scan not completed or insufficient",
            success_message="Security scan completed successfully"
        ),
        ValidationRule(
            name="vulnerabilities_assessed",
            description="All identified vulnerabilities must be assessed and prioritized",
            required=True,
            validation_function="validate_vulnerability_assessment",
            error_message="Vulnerability assessment incomplete",
            success_message="All vulnerabilities properly assessed"
        ),
        ValidationRule(
            name="security_approved",
            description="Security measures must be approved by security reviewer",
            required=True,
            validation_function="validate_security_approval",
            error_message="Security measures not yet approved",
            success_message="Security measures approved"
        )
    ],
    
    transition_criteria=[
        "Security analysis completed",
        "Vulnerabilities documented and prioritized",
        "Security recommendations provided",
        "Security measures approved"
    ],
    
    blocking_conditions=[
        "Critical vulnerabilities not addressed",
        "Security analysis incomplete",
        "Security approval not obtained"
    ],
    
    interaction_points=[
        "Security risk review and approval",
        "Critical vulnerability discussion",
        "Security implementation timeline"
    ],
    
    approval_message="Please review the security analysis and approve the recommended security measures."
)
```

### Passo 3: Aggiungere alla Registry

```python
PHASE_CONFIGS: Dict[PhaseType, PhaseConfig] = {
    PhaseType.INVESTIGATION: INVESTIGATION_PHASE_CONFIG,
    PhaseType.DISCUSSION: DISCUSSION_PHASE_CONFIG,
    PhaseType.PLANNING: PLANNING_PHASE_CONFIG,
    PhaseType.SECURITY_REVIEW: SECURITY_REVIEW_PHASE_CONFIG,  # NUOVA FASE
    PhaseType.TASK_GENERATION: TASK_GENERATION_PHASE_CONFIG
}
```

### Passo 4: Creare il Prompt Template

In **`src/config/optimized_prompts.py`**:

```python
SECURITY_REVIEW_AGENT_PROMPT_TEMPLATE = """You are the Security Review Agent - Comprehensive security analyst and risk assessor.

## Mission
Perform thorough security analysis of the planned implementation and provide security recommendations.

## Available Context
- Implementation plan: {plan_file}
- Technical architecture: {technical_analysis}
- Code patterns: {code_analysis_summary}

## Security Review Process
1. Analyze planned implementation for security implications
2. Review existing codebase for security patterns
3. Identify potential security vulnerabilities
4. Assess compliance requirements
5. Provide prioritized security recommendations

## Security Analysis Areas

### 1. Authentication & Authorization
- Review authentication mechanisms
- Analyze access control patterns
- Check session management
- Validate authorization flows

### 2. Data Protection
- Encryption at rest and in transit
- Sensitive data handling
- Data validation and sanitization
- Privacy compliance (GDPR, etc.)

### 3. Input Validation
- SQL injection prevention
- XSS protection
- CSRF mitigation
- Input sanitization patterns

### 4. Infrastructure Security
- Deployment security
- Network security
- Container/server hardening
- Dependency vulnerabilities

### 5. Application Security
- Error handling
- Logging security
- API security
- Third-party integrations

## Risk Assessment Framework

### Critical (Priority 1)
- Security vulnerabilities that allow unauthorized access
- Data exposure risks
- Authentication bypass possibilities

### High (Priority 2)  
- Privilege escalation risks
- Data integrity threats
- Availability impacts

### Medium (Priority 3)
- Information disclosure
- Logging/monitoring gaps
- Configuration issues

### Low (Priority 4)
- Security hygiene improvements
- Documentation updates
- Compliance enhancements

## Output Requirements

### security_analysis.md
```markdown
# Security Analysis Report

## Executive Summary
[High-level security posture assessment]

## Architecture Security Review
[Security implications of planned architecture]

## Vulnerability Assessment
[Identified security issues by priority]

## Compliance Analysis
[Regulatory/standard compliance status]

## Security Recommendations
[Prioritized security improvements]
```

### vulnerability_report.md
[Detailed technical vulnerability report]

### security_recommendations.md
[Implementation guidance for security measures]

## Approval Process
After completing analysis, request security approval:
```
review_plan(
    plan_type="security",
    plan_content=security_summary
)
```

## Success Criteria
- Comprehensive security analysis completed
- All vulnerabilities identified and prioritized
- Security recommendations provided
- Security measures approved by reviewer
- Implementation security plan ready

Security is not optional - every implementation must pass security review."""
```

### Passo 5: Aggiornare l'Agent Config

```python
AGENT_CONFIGS = {
    # ... agenti esistenti ...
    
    "security-review-agent": {
        "name": "security-review-agent",
        "description": "Security analysis and risk assessment for implementation plans",
        "prompt_template": SECURITY_REVIEW_AGENT_PROMPT_TEMPLATE,
        "tools": ["Code_find_relevant_code_snippets", "Code_get_file", "review_plan"],
        "outputs": ["security_analysis.md", "vulnerability_report.md", "security_recommendations.md"],
        "phase": "security_review",
        "requires_user_input": True,
        "requires_approval": True,
        "approval_points": ["security_review"],
        "validation_criteria": [
            "Security analysis completed",
            "Vulnerabilities assessed and prioritized",
            "Security recommendations provided", 
            "Security measures approved"
        ]
    }
}
```

### Passo 6: Aggiornare le Transizioni di Fase

```python
PHASE_TRANSITIONS = {
    PhaseType.INVESTIGATION: {
        "next_phase": PhaseType.DISCUSSION,
        "transition_message": "Investigation complete. Moving to targeted discussion phase.",
        "requirements": [...]
    },
    
    PhaseType.DISCUSSION: {
        "next_phase": PhaseType.PLANNING,
        "transition_message": "Discussion complete. Moving to structured planning phase.",
        "requirements": [...]
    },
    
    PhaseType.PLANNING: {
        "next_phase": PhaseType.SECURITY_REVIEW,  # CAMBIATO
        "transition_message": "Planning complete and approved. Moving to security review phase.",
        "requirements": [...]
    },
    
    PhaseType.SECURITY_REVIEW: {  # NUOVA TRANSIZIONE
        "next_phase": PhaseType.TASK_GENERATION,
        "transition_message": "Security review complete and approved. Moving to task generation phase.",
        "requirements": [
            "Security analysis completed",
            "Vulnerabilities assessed",
            "Security measures approved"
        ]
    },
    
    PhaseType.TASK_GENERATION: {
        "next_phase": PhaseType.COMPLETE,
        "transition_message": "Task generation complete. Deep planning process finished.",
        "requirements": [...]
    }
}
```

## 🔧 Configurazione degli Strumenti per Fase

### Aggiungere Nuova Categoria di Strumenti

In **`src/config/prompt_config.py`**:

```python
class ToolCategory(Enum):
    """Tool categorization for phase filtering."""
    PROJECT_DISCOVERY = "project_discovery"
    CODE_ANALYSIS = "code_analysis"
    DOCUMENTATION = "documentation"
    FILE_OPERATIONS = "file_operations"
    REQUIREMENTS_MANAGEMENT = "requirements_management"
    VALIDATION = "validation"
    APPROVAL = "approval"
    SECURITY_ANALYSIS = "security_analysis"  # NUOVA CATEGORIA
```

### Configurare la Categoria

```python
TOOL_CATEGORY_CONFIGS = {
    # ... categorie esistenti ...
    
    ToolCategory.SECURITY_ANALYSIS: {
        "name": "Security Analysis",
        "description": "Tools for security scanning and vulnerability assessment",
        "keywords": ["security", "vulnerability", "scan", "audit", "compliance"],
        "examples": ["Security_scan_vulnerabilities", "Code_analyze_security_patterns", "Compliance_check_standards"]
    }
}
```

## 📝 Modifica del Sistema di Template Dinamici

### Aggiungere Variabili di Contesto Personalizzate

In **`src/config/prompt_templates.py`**, funzione `generate_phase_context()`:

```python
def generate_phase_context(phase: str, state: dict) -> dict:
    """Generate phase-specific context for todo generation."""
    
    base_context = {
        "domain": state.get("project_domain", "software development"),
        "project_type": state.get("project_type", "application"),
        "project_name": state.get("project_name", "current project"),
        "focus_area": state.get("focus_area", "core functionality"),
        # NUOVE VARIABILI:
        "security_level": state.get("security_level", "standard"),
        "compliance_requirements": state.get("compliance_requirements", "none"),
        "team_experience": state.get("team_experience", "intermediate")
    }
    
    phase_contexts = {
        "investigation": {
            **base_context,
        },
        "discussion": {
            **base_context,
            "unclear_areas": ", ".join(state.get("knowledge_gaps", ["requirements"])),
            "requirement_type": state.get("requirement_type", "functional")
        },
        "planning": {
            **base_context,
            "context_sources": "investigation and discussion phases",
            "architecture_type": state.get("architecture_type", "modular")
        },
        "security_review": {  # NUOVO CONTESTO
            **base_context,
            "security_focus": state.get("security_focus", "comprehensive"),
            "threat_model": state.get("threat_model", "standard"),
            "compliance_standards": ", ".join(state.get("compliance_standards", ["industry standard"]))
        },
        "task_generation": {
            **base_context,
            "plan_location": "implementation_plan.md",
            "file_count": len(state.get("files_to_track", []))
        }
    }
    
    return phase_contexts.get(phase, base_context)
```

### Aggiungere TODO Template per Nuova Fase

```python
def generate_phase_todos(phase: str, context: dict) -> List[Dict[str, Any]]:
    """Generate context-aware todos for each phase dynamically."""
    
    todo_templates = {
        "investigation": [...],
        "discussion": [...],
        "planning": [...],
        "security_review": [  # NUOVI TODO
            "Analyze implementation plan for security implications in {domain}",
            "Review {project_type} codebase for security patterns",
            "Identify vulnerabilities in {architecture_type} architecture",
            "Assess {compliance_requirements} compliance requirements",
            "Generate prioritized security recommendations"
        ],
        "task_generation": [...]
    }
    
    # ... resto della funzione
```

## 🎨 Personalizzazione Avanzata

### Modificare i Criteri di Validazione

Per cambiare quando una fase è considerata "completa", modifica la funzione `validate_phase_completion()` in **`src/config/prompt_config.py`**:

```python
def validate_phase_completion(phase: PhaseType, state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that a phase has been completed according to its configuration."""
    config = get_phase_config(phase)
    if not config:
        return {"valid": False, "error": "Phase configuration not found"}
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "completed_validations": [],
        "phase": phase.value
    }
    
    # Check required outputs exist
    files = state.get("files", {})
    for required_output in config.required_outputs:
        if required_output not in files or not files[required_output]:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Required output missing: {required_output}")
        else:
            validation_results["completed_validations"].append(f"Output present: {required_output}")
    
    # AGGIUNGERE VALIDAZIONI PERSONALIZZATE:
    if phase == PhaseType.SECURITY_REVIEW:
        # Validazione personalizzata per security review
        security_score = state.get("security_score", 0)
        if security_score < 7:  # Soglia minima di sicurezza
            validation_results["valid"] = False
            validation_results["errors"].append(f"Security score too low: {security_score}/10")
        
        critical_vulns = state.get("critical_vulnerabilities", [])
        if critical_vulns:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Critical vulnerabilities not resolved: {len(critical_vulns)}")
    
    # Check transition criteria
    for criterion in config.transition_criteria:
        validation_results["completed_validations"].append(f"Criterion checked: {criterion}")
    
    return validation_results
```

### Aggiungere Metriche di Performance

Puoi tracciare metriche personalizzate aggiungendole allo stato dell'agente:

```python
# Nel tuo agente personalizzato
def track_performance_metrics(state: dict, phase: str, start_time: float, end_time: float):
    """Track performance metrics for each phase."""
    if "metrics" not in state:
        state["metrics"] = {}
    
    state["metrics"][phase] = {
        "duration": end_time - start_time,
        "completed_at": end_time,
        "validation_score": calculate_validation_score(state, phase),
        "user_satisfaction": state.get(f"{phase}_satisfaction", None)
    }
```

## 🚀 Deploy e Test delle Modifiche

### 1. Testare le Modifiche

```bash
# Test delle configurazioni
python tests/test_configuration.py

# Test dei prompt
python tests/test_prompt_generation.py

# Test dell'agente completo
python src/core/agent_core.py
```

### 2. Avviare il Server di Sviluppo

```bash
# Con hot reload per testare le modifiche
langgraph dev
```

### 3. Testare con Esempi

```python
# Test del nuovo agente di security
from src.core.agent_core import create_optimized_deep_planning_agent

initial_state = {
    "current_phase": "security_review",
    "project_id": "test_project",
    "security_level": "high",
    "compliance_requirements": "SOC2, ISO27001",
    "files": {
        "implementation_plan.md": "... contenuto del piano ..."
    }
}

agent = create_optimized_deep_planning_agent(initial_state)
result = agent.invoke({"messages": [{"role": "user", "content": "Perform security review"}]})
```

## 📋 Checklist per le Modifiche

### ✅ Prima di Implementare
- [ ] Definire chiaramente l'obiettivo della modifica
- [ ] Identificare i file da modificare
- [ ] Pianificare i test necessari
- [ ] Considerare l'impatto sulle fasi esistenti

### ✅ Durante l'Implementazione
- [ ] Aggiornare `PhaseType` enum se necessario
- [ ] Creare/modificare `PhaseConfig`
- [ ] Aggiornare `PHASE_CONFIGS` registry
- [ ] Creare/modificare template del prompt
- [ ] Aggiornare `AGENT_CONFIGS`
- [ ] Modificare `PHASE_TRANSITIONS` se necessario
- [ ] Aggiungere nuove variabili di contesto
- [ ] Aggiornare criteri di validazione

### ✅ Dopo l'Implementazione
- [ ] Testare l'agente modificato
- [ ] Verificare le transizioni tra fasi
- [ ] Testare la validazione
- [ ] Verificare che i file di output siano creati correttamente
- [ ] Testare l'integrazione con il sistema esistente

## 🎯 Esempi Pratici di Uso

### Scenario 1: Aggiungere Focus sulla Performance

```python
# 1. Aggiungere variabili di contesto per performance
"performance_requirements": state.get("performance_requirements", "standard"),
"load_expectations": state.get("load_expectations", "moderate"),

# 2. Modificare investigation agent per includere analisi performance
"## Performance Analysis Tasks\n"
"1. Analyze current system performance metrics\n"
"2. Identify performance bottlenecks\n" 
"3. Review scalability patterns\n"
"4. Document performance baselines\n"

# 3. Aggiungere output per performance
"outputs": [..., "performance_analysis.md"],

# 4. Aggiungere validazione performance nella planning phase
ValidationRule(
    name="performance_requirements_defined",
    description="Performance requirements must be clearly specified",
    required=True,
    validation_function="validate_performance_requirements"
)
```

### Scenario 2: Personalizzare per Team Distribuito

```python
# Modificare il discussion agent per considerare team distribuito
DISCUSSION_AGENT_PROMPT_TEMPLATE = """...
## Team Distribution Considerations
- Time zone differences: {team_timezones}
- Communication preferences: {communication_channels}
- Collaboration tools: {collaboration_tools}

## Discussion Process for Distributed Teams
1. Generate async-friendly clarification questions
2. Provide multiple response channels
3. Consider time zone constraints for approvals
4. Document decisions for full team visibility
...
"""

# Aggiungere variabili di contesto
"team_timezones": ", ".join(state.get("team_timezones", ["UTC"])),
"communication_channels": ", ".join(state.get("communication_channels", ["email"])),
"collaboration_tools": ", ".join(state.get("collaboration_tools", ["standard"])),
```

---

**★ Insight ─────────────────────────────────────**
Il sistema Deep Planning è progettato per la massima modularità - ogni componente può essere modificato indipendentemente. La chiave è mantenere la coerenza tra le configurazioni delle fasi, i template dei prompt e le transizioni. L'architettura factory-based permette di aggiungere nuovi agenti senza impattare quelli esistenti.
**─────────────────────────────────────────────────**

Questa guida ti fornisce tutti gli strumenti necessari per personalizzare completamente il sistema Deep Planning Agent. Inizia con modifiche piccole e incrementali, poi espandi gradualmente per funzionalità più complesse.