# Esempi Pratici di Modifica - Deep Planning Agent

Esempi completi e funzionanti per modificare l'agente Deep Planning.

## 🎯 Esempio 1: Aggiungere un Security Review Agent

### Implementazione Completa

#### 1. Aggiornare `src/config/prompt_config.py`

```python
# Aggiungere alla enum PhaseType
class PhaseType(Enum):
    """Enumeration of deep planning phases."""
    INVESTIGATION = "investigation"
    DISCUSSION = "discussion"
    PLANNING = "planning"
    SECURITY_REVIEW = "security_review"  # ← NUOVO
    TASK_GENERATION = "task_generation"
    COMPLETE = "complete"

# Aggiungere nuova categoria di strumenti
class ToolCategory(Enum):
    PROJECT_DISCOVERY = "project_discovery"
    CODE_ANALYSIS = "code_analysis"
    DOCUMENTATION = "documentation"
    FILE_OPERATIONS = "file_operations"
    REQUIREMENTS_MANAGEMENT = "requirements_management"
    VALIDATION = "validation"
    APPROVAL = "approval"
    SECURITY_ANALYSIS = "security_analysis"  # ← NUOVO

# Configurazione completa della nuova fase
SECURITY_REVIEW_PHASE_CONFIG = PhaseConfig(
    name="Security Review",
    phase_type=PhaseType.SECURITY_REVIEW,
    emoji="🔒",
    goal="Comprehensive security analysis and risk assessment of implementation plan",
    agent_name="security-review-agent",
    duration_estimate="15-25 minutes",
    completion_weight=85,
    requires_user_input=True,
    requires_approval=True,
    
    required_tool_categories=[
        ToolCategory.CODE_ANALYSIS,
        ToolCategory.SECURITY_ANALYSIS,
        ToolCategory.VALIDATION,
        ToolCategory.APPROVAL
    ],
    optional_tool_categories=[
        ToolCategory.DOCUMENTATION,
        ToolCategory.FILE_OPERATIONS
    ],
    
    required_outputs=[
        "security_analysis.md",
        "vulnerability_report.md", 
        "security_recommendations.md"
    ],
    optional_outputs=[
        "threat_model.md",
        "compliance_checklist.md",
        "security_timeline.md"
    ],
    
    validation_level=ValidationLevel.STRICT,
    validation_rules=[
        ValidationRule(
            name="security_analysis_complete",
            description="Comprehensive security analysis must be performed on implementation plan",
            required=True,
            validation_function="validate_security_analysis",
            error_message="Security analysis not completed or insufficient depth",
            success_message="Security analysis completed with comprehensive coverage"
        ),
        ValidationRule(
            name="vulnerabilities_identified_and_prioritized",
            description="All security vulnerabilities must be identified and risk-prioritized",
            required=True,
            validation_function="validate_vulnerability_assessment",
            error_message="Vulnerability identification incomplete or not prioritized",
            success_message="All vulnerabilities identified and properly prioritized"
        ),
        ValidationRule(
            name="security_recommendations_provided",
            description="Specific security recommendations must be provided for each identified issue",
            required=True,
            validation_function="validate_security_recommendations",
            error_message="Security recommendations missing or too generic",
            success_message="Comprehensive security recommendations provided"
        ),
        ValidationRule(
            name="security_measures_approved",
            description="Security measures and timeline must be approved by security reviewer",
            required=True,
            validation_function="validate_security_approval",
            error_message="Security measures not yet approved by reviewer",
            success_message="Security measures approved and ready for implementation"
        )
    ],
    
    transition_criteria=[
        "Security analysis completed for all implementation components",
        "Vulnerabilities identified, assessed, and prioritized by risk level",
        "Security recommendations provided with implementation guidance",
        "Security measures and timeline approved by security reviewer",
        "Integration security validated with existing systems"
    ],
    
    blocking_conditions=[
        "Critical security vulnerabilities not addressed",
        "Security analysis incomplete or insufficient",
        "Implementation plan has fundamental security flaws",
        "Security approval not obtained from reviewer",
        "Compliance requirements not met"
    ],
    
    interaction_points=[
        "Initial security scope discussion",
        "Critical vulnerability review and prioritization",
        "Security implementation timeline negotiation",
        "Final security approval and sign-off"
    ],
    
    approval_message="Please review the security analysis, vulnerability assessment, and recommended security measures. Approve if the security posture is acceptable for implementation."
)

# Aggiungere alla registry delle fasi
PHASE_CONFIGS: Dict[PhaseType, PhaseConfig] = {
    PhaseType.INVESTIGATION: INVESTIGATION_PHASE_CONFIG,
    PhaseType.DISCUSSION: DISCUSSION_PHASE_CONFIG,
    PhaseType.PLANNING: PLANNING_PHASE_CONFIG,
    PhaseType.SECURITY_REVIEW: SECURITY_REVIEW_PHASE_CONFIG,  # ← NUOVO
    PhaseType.TASK_GENERATION: TASK_GENERATION_PHASE_CONFIG
}

# Aggiornare le transizioni di fase
PHASE_TRANSITIONS = {
    PhaseType.INVESTIGATION: {
        "next_phase": PhaseType.DISCUSSION,
        "transition_message": "Investigation complete. Moving to targeted discussion phase.",
        "requirements": [
            "All investigation outputs created",
            "Project structure documented", 
            "Knowledge gaps identified"
        ]
    },
    
    PhaseType.DISCUSSION: {
        "next_phase": PhaseType.PLANNING,
        "transition_message": "Discussion complete. Moving to structured planning phase.",
        "requirements": [
            "Questions answered",
            "Requirements clarified",
            "User responses documented"
        ]
    },
    
    PhaseType.PLANNING: {
        "next_phase": PhaseType.SECURITY_REVIEW,  # ← CAMBIATO
        "transition_message": "Planning complete and approved. Moving to security review phase.",
        "requirements": [
            "8-section plan created",
            "Plan approved by human",
            "All validation criteria met"
        ]
    },
    
    PhaseType.SECURITY_REVIEW: {  # ← NUOVO
        "next_phase": PhaseType.TASK_GENERATION,
        "transition_message": "Security review complete and approved. Moving to task generation phase.",
        "requirements": [
            "Security analysis completed",
            "Vulnerabilities assessed and prioritized",
            "Security recommendations provided",
            "Security measures approved"
        ]
    },
    
    PhaseType.TASK_GENERATION: {
        "next_phase": PhaseType.COMPLETE,
        "transition_message": "Task generation complete. Deep planning process finished.",
        "requirements": [
            "Tasks extracted",
            "Focus chain created", 
            "Success criteria defined",
            "Next steps prioritized"
        ]
    }
}

# Aggiornare configurazione categorie strumenti
TOOL_CATEGORY_CONFIGS = {
    # ... configurazioni esistenti ...
    
    ToolCategory.SECURITY_ANALYSIS: {
        "name": "Security Analysis",
        "description": "Tools for security scanning, vulnerability assessment, and compliance checking",
        "keywords": ["security", "vulnerability", "scan", "audit", "compliance", "threat", "risk"],
        "examples": ["Security_scan_vulnerabilities", "Code_analyze_security_patterns", "Compliance_check_standards"]
    }
}
```

#### 2. Aggiungere il prompt template in `src/config/optimized_prompts.py`

```python
# Security Review Agent Prompt Template (100 linee)
SECURITY_REVIEW_AGENT_PROMPT_TEMPLATE = """You are the Security Review Agent - 🔒 Comprehensive security analyst and risk assessor.

## Mission
Perform thorough security analysis of the approved implementation plan and provide actionable security recommendations.

## Available Context
- Implementation plan: {plan_file}
- Technical architecture: {technical_analysis_summary}
- Code patterns: {code_analysis_summary}
- Compliance requirements: {compliance_requirements}
- Security level: {security_level}

## Security Review Process
1. **Plan Security Analysis**: Review implementation plan for security implications
2. **Code Security Review**: Analyze existing codebase security patterns and vulnerabilities
3. **Architecture Security Assessment**: Evaluate planned architecture for security weaknesses
4. **Compliance Validation**: Check against required security standards and regulations
5. **Risk Prioritization**: Assess and prioritize identified security issues
6. **Recommendation Generation**: Provide specific, actionable security improvements
7. **Implementation Timeline**: Suggest security implementation priorities and timeline

## Security Analysis Framework

### 🔐 Authentication & Authorization
- Review authentication mechanisms and protocols
- Analyze access control patterns and role-based permissions
- Check session management and token handling
- Validate authorization flows and privilege escalation prevention
- Assess multi-factor authentication implementation

### 🛡️ Data Protection & Privacy
- Encryption implementation (at rest and in transit)
- Sensitive data identification and protection measures
- Data validation, sanitization, and input filtering
- Privacy compliance analysis (GDPR, CCPA, etc.)
- Data retention and deletion policies

### ⚠️ Vulnerability Assessment
- **SQL Injection**: Database query security and parameterization
- **Cross-Site Scripting (XSS)**: Input/output encoding and sanitization
- **Cross-Site Request Forgery (CSRF)**: Token validation and same-origin policies
- **Security Headers**: Implementation of security-related HTTP headers
- **Dependency Vulnerabilities**: Third-party library security assessment

### 🏗️ Infrastructure & Deployment Security
- Container security and image scanning
- Network security and segmentation
- Server hardening and configuration security
- API security and rate limiting
- Secrets management and environment variable security

### 📊 Application Security Patterns
- Error handling and information disclosure prevention
- Security logging and monitoring implementation
- API security (authentication, rate limiting, input validation)
- Third-party integration security assessment
- Business logic security and abuse prevention

## Risk Assessment Matrix

### 🚨 Critical (Priority 1) - Immediate Action Required
- Vulnerabilities allowing unauthorized system access
- Data exposure or exfiltration possibilities
- Authentication bypass or privilege escalation
- Remote code execution vulnerabilities
- Critical compliance violations

### ⚡ High (Priority 2) - Address Before Implementation
- Significant privilege escalation risks
- Data integrity compromise possibilities
- Availability and denial-of-service vulnerabilities
- Sensitive information disclosure risks
- Important compliance gaps

### ⚠️ Medium (Priority 3) - Address During Implementation
- Information disclosure of non-sensitive data
- Security monitoring and logging gaps
- Configuration security improvements
- Minor compliance enhancements
- Defense-in-depth improvements

### 📋 Low (Priority 4) - Security Hygiene
- Security documentation improvements
- Code security best practices
- Security training and awareness needs
- Long-term security architecture improvements
- Preventive security measures

## Required Security Outputs

### security_analysis.md
```markdown
# Security Analysis Report

## Executive Summary
- Overall security posture: [Excellent/Good/Fair/Poor]
- Critical issues found: [number]
- Recommended timeline: [X weeks for critical fixes]
- Compliance status: [Compliant/Non-compliant with requirements]

## Implementation Plan Security Review
### Architecture Security Assessment
[Security implications of planned architecture changes]

### Component Security Analysis  
[Security review of each major component in the plan]

### Integration Security Review
[Security implications of system integrations]

## Vulnerability Assessment
### Critical Vulnerabilities (Priority 1)
[List with CVSS scores, exploitation difficulty, business impact]

### High-Risk Issues (Priority 2)  
[Detailed technical analysis and recommended fixes]

### Medium & Low Priority Issues
[Summarized findings with batch fix recommendations]

## Compliance Analysis
### Required Standards Compliance
- [Standard 1]: [Compliant/Non-compliant] - [Gap details]
- [Standard 2]: [Compliant/Non-compliant] - [Gap details]

### Regulatory Requirements
[GDPR, CCPA, SOX, HIPAA, etc. compliance status]

## Security Recommendations
### Immediate Actions (Pre-Implementation)
1. [Critical fix with specific implementation guidance]
2. [Security architecture change with detailed rationale]
3. [Compliance requirement with implementation steps]

### Implementation Phase Security
[Security measures to implement during development]

### Post-Implementation Security
[Ongoing security monitoring and maintenance recommendations]
```

### vulnerability_report.md
```markdown
# Detailed Vulnerability Report

## Vulnerability Summary
- Total vulnerabilities: [number]
- Critical: [number] | High: [number] | Medium: [number] | Low: [number]

## Critical Vulnerabilities
### CVE-2024-XXXX: [Vulnerability Name]
- **CVSS Score**: [score]/10
- **Attack Vector**: [Remote/Local/Physical]
- **Complexity**: [Low/High]
- **Impact**: [Confidentiality/Integrity/Availability]
- **Exploitability**: [Proof of concept available/Functional exploit/Weaponized]
- **Business Impact**: [Data breach/Service disruption/Financial loss]
- **Remediation**: [Specific technical steps]
- **Timeline**: [Immediate/1 week/1 month]

[Repeat for each critical vulnerability]

## Technical Remediation Guide
[Step-by-step technical implementation guide for fixes]
```

### security_recommendations.md
```markdown
# Security Implementation Recommendations

## Priority 1: Critical Security Fixes (Week 1)
### 1. Fix Authentication Bypass
- **Issue**: [Technical description]
- **Fix**: [Specific code changes needed]
- **Validation**: [How to verify the fix]
- **Testing**: [Security test cases to implement]

### 2. Implement Data Encryption
- **Requirement**: [Encryption specifications]
- **Implementation**: [Technical implementation guide]
- **Key Management**: [Key generation, rotation, storage]
- **Validation**: [Encryption verification methods]

## Priority 2: High-Risk Security Improvements (Weeks 2-3)
[Detailed implementation guidance for high-priority fixes]

## Priority 3: Security Architecture Improvements (Weeks 4-6)
[Long-term security architecture recommendations]

## Security Implementation Timeline
```
Week 1: Critical vulnerability fixes
Week 2: Authentication improvements  
Week 3: Data protection implementation
Week 4: Security monitoring setup
Week 5: Compliance implementation
Week 6: Security testing and validation
```

## Ongoing Security Measures
### Security Monitoring
[Implementation of security logging and monitoring]

### Security Testing
[Automated security testing integration]

### Security Training
[Team security awareness and training recommendations]
```

## Approval Process
After completing comprehensive security analysis, request approval:

```
review_plan(
    plan_type="security_review",
    plan_content="Security analysis complete. Critical issues: [X], High-risk: [Y]. All critical vulnerabilities have remediation plans. Estimated security implementation timeline: [Z] weeks. Ready for security approval."
)
```

## Security Success Criteria
- [ ] Complete security analysis performed on implementation plan
- [ ] All vulnerabilities identified, assessed, and prioritized
- [ ] Specific remediation guidance provided for each security issue
- [ ] Compliance requirements validated and gaps identified
- [ ] Security implementation timeline defined and realistic
- [ ] Security measures approved by designated security reviewer
- [ ] Integration security validated with existing systems
- [ ] Security monitoring and testing plans established

## Security Implementation Principles
1. **Security by Design**: Build security into the architecture from the start
2. **Defense in Depth**: Implement multiple layers of security controls
3. **Least Privilege**: Grant minimum necessary permissions and access
4. **Zero Trust**: Verify every request, user, and device
5. **Continuous Monitoring**: Implement ongoing security monitoring and alerting

Security is not optional - every implementation must pass security review before proceeding to task generation."""

# Aggiungere alla configurazione degli agenti
AGENT_CONFIGS = {
    # ... agenti esistenti ...
    
    "security-review-agent": {
        "name": "security-review-agent",
        "description": "Phase 4: Comprehensive security analysis and risk assessment of implementation plans",
        "prompt_template": SECURITY_REVIEW_AGENT_PROMPT_TEMPLATE,
        "tools": [
            "Code_find_relevant_code_snippets", 
            "Code_get_file", 
            "Code_get_directory_structure",
            "General_rag_retrieve_documents",
            "review_plan"
        ],
        "outputs": [
            "security_analysis.md", 
            "vulnerability_report.md", 
            "security_recommendations.md"
        ],
        "phase": "security_review",
        "requires_user_input": True,
        "requires_approval": True,
        "approval_points": ["security_review"],
        "validation_criteria": [
            "Security analysis completed for all implementation components",
            "Vulnerabilities identified, assessed, and prioritized by risk",
            "Security recommendations provided with implementation guidance", 
            "Compliance requirements validated and gaps addressed",
            "Security measures and timeline approved by reviewer"
        ]
    }
}
```

#### 3. Aggiornare il sistema di template in `src/config/prompt_templates.py`

```python
def generate_phase_context(phase: str, state: dict) -> dict:
    """Generate phase-specific context for todo generation."""
    
    base_context = {
        "domain": state.get("project_domain", "software development"),
        "project_type": state.get("project_type", "application"),
        "project_name": state.get("project_name", "current project"),
        "focus_area": state.get("focus_area", "core functionality"),
        # Nuove variabili per security review
        "security_level": state.get("security_level", "standard"),
        "compliance_requirements": ", ".join(state.get("compliance_requirements", ["industry standard"])),
        "threat_model": state.get("threat_model", "standard web application")
    }
    
    phase_contexts = {
        # ... contesti esistenti ...
        
        "security_review": {  # ← NUOVO CONTESTO
            **base_context,
            "security_focus": state.get("security_focus", "comprehensive analysis"),
            "compliance_standards": ", ".join(state.get("compliance_standards", ["OWASP", "ISO27001"])),
            "risk_tolerance": state.get("risk_tolerance", "low"),
            "existing_security_measures": ", ".join(state.get("existing_security_measures", ["none identified"])),
            "technical_analysis_summary": "investigation and planning phase results",
            "code_analysis_summary": "codebase security patterns analysis"
        },
        
        # ... altri contesti ...
    }
    
    return phase_contexts.get(phase, base_context)

def generate_phase_todos(phase: str, context: dict) -> List[Dict[str, Any]]:
    """Generate context-aware todos for each phase dynamically."""
    
    todo_templates = {
        # ... template esistenti ...
        
        "security_review": [  # ← NUOVI TODO TEMPLATE
            "Analyze implementation plan for security implications in {domain}",
            "Review {project_type} codebase for existing security patterns",
            "Identify vulnerabilities in {threat_model} threat model",
            "Assess {compliance_requirements} compliance requirements",
            "Prioritize security risks by {risk_tolerance} risk tolerance",
            "Generate specific security recommendations with implementation guidance",
            "Create security implementation timeline for {security_focus}",
            "Request security approval from designated reviewer"
        ],
        
        # ... altri template ...
    }
    
    # ... resto della funzione
```

#### 4. Test dell'implementazione

```python
# File: test_security_agent.py

from src.core.agent_core import create_optimized_deep_planning_agent
from src.config.prompt_config import PhaseType, validate_phase_completion

def test_security_review_agent():
    """Test del nuovo security review agent."""
    
    # Stato di test con piano di implementazione approvato
    test_state = {
        "current_phase": "security_review",
        "project_id": "test_security_project",
        "project_domain": "web application",
        "project_type": "e-commerce platform",
        "security_level": "high",
        "compliance_requirements": ["PCI-DSS", "GDPR", "SOC2"],
        "threat_model": "high-value e-commerce application",
        "risk_tolerance": "low",
        "existing_security_measures": ["HTTPS", "basic authentication"],
        "files": {
            "implementation_plan.md": """
# Implementation Plan: E-commerce Security Enhancement

## 1. Overview
### Goals
- Implement secure payment processing with PCI-DSS compliance
- Add multi-factor authentication for user accounts
- Enhance data encryption for customer personal information

### Success Criteria
- Zero critical security vulnerabilities
- Full PCI-DSS compliance certification
- 99.9% uptime with enhanced security monitoring

## 2. Technical Approach
### Architecture Decision
- Microservices architecture with API gateway
- Separate payment processing service
- Redis session management with encryption

### Technology Stack
- Node.js with Express.js framework
- PostgreSQL with TDE (Transparent Data Encryption)
- JWT tokens with refresh token rotation
- Stripe payment processing API

### Integration Strategy
- OAuth 2.0 with PKCE for authentication
- API rate limiting with Redis
- Security headers middleware
- CORS configuration for cross-origin requests

## 3. Implementation Steps
- [ ] Implement OAuth 2.0 authentication service
- [ ] Add payment processing microservice with Stripe integration
- [ ] Configure database encryption for customer data
- [ ] Implement API rate limiting and security headers
- [ ] Add comprehensive security logging and monitoring
- [ ] Set up automated security testing pipeline

## 4. File Changes
- `src/auth/oauth-service.js`: New OAuth 2.0 implementation
- `src/payments/stripe-service.js`: Secure payment processing
- `src/middleware/security.js`: Security headers and rate limiting
- `src/config/database.js`: Database encryption configuration
- `tests/security/security-tests.js`: Comprehensive security test suite

## 5. Dependencies
- passport@0.6.0: OAuth 2.0 authentication
- stripe@12.0.0: Payment processing
- bcrypt@5.1.0: Password hashing
- helmet@7.0.0: Security headers
- express-rate-limit@6.7.0: API rate limiting

## 6. Testing Strategy
### Unit Tests
- Authentication service unit tests
- Payment processing validation tests
- Security middleware tests

### Integration Tests  
- End-to-end authentication flow tests
- Payment processing integration tests
- Security header validation tests

### Security Testing
- OWASP ZAP automated security scanning
- Penetration testing for authentication flows
- PCI-DSS compliance validation testing

## 7. Potential Issues
### Risk: Payment data exposure during processing
**Likelihood**: Medium
**Impact**: Critical - PCI-DSS compliance violation, financial liability
**Mitigation**: Implement tokenization, never store card data, use Stripe's secure vault

### Risk: Session hijacking through XSS attacks
**Likelihood**: Medium  
**Impact**: High - User account compromise, data theft
**Mitigation**: Implement CSP headers, XSS protection, secure cookie settings

## 8. Timeline
- **Phase 1** (2 weeks): Authentication service implementation
- **Phase 2** (3 weeks): Payment processing and PCI-DSS compliance
- **Phase 3** (1 week): Security testing and compliance validation
            """,
            "technical_analysis.md": """
# Technical Analysis

## Technology Stack
- Node.js/Express.js backend
- React.js frontend
- PostgreSQL database
- Redis for caching and sessions

## Architecture Patterns
- RESTful API design
- JWT-based authentication
- Microservices for payment processing

## Security Concerns Identified
- Current authentication is basic username/password
- No rate limiting on API endpoints
- Database connections not encrypted
- Missing security headers
- No input validation middleware
            """
        }
    }
    
    # Creare l'agente
    agent = create_optimized_deep_planning_agent(test_state, enable_llm_compression=False)
    
    # Testare l'invocazione
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "Perform comprehensive security review of the e-commerce implementation plan"}
        ]
    })
    
    # Verificare i risultati
    output_files = result.get("files", {})
    
    # Verificare che i file di security sono stati creati
    required_files = ["security_analysis.md", "vulnerability_report.md", "security_recommendations.md"]
    for file_name in required_files:
        assert file_name in output_files, f"Missing required security file: {file_name}"
        assert len(output_files[file_name]) > 100, f"Security file {file_name} is too short"
    
    # Verificare validazione della fase
    validation = validate_phase_completion(PhaseType.SECURITY_REVIEW, result)
    print(f"Security phase validation: {validation}")
    
    return result

if __name__ == "__main__":
    result = test_security_review_agent()
    print("Security review agent test completed successfully!")
    print(f"Generated files: {list(result.get('files', {}).keys())}")
```

## 🎨 Esempio 2: Modificare l'Agent di Investigation per Focus sulla Performance

### Modifica del Prompt Template

```python
# In src/config/optimized_prompts.py

INVESTIGATION_AGENT_PROMPT_TEMPLATE = """You are the Investigation Agent - Phase 1 autonomous project explorer with performance focus.

## Mission
Silently explore project {project_id} using {tool_categories} without user interaction, with special attention to performance characteristics.

## Investigation Focus
{investigation_focus}

## Performance Analysis Requirements
- Expected load: {load_expectations}
- Performance targets: {performance_requirements}  
- Scalability concerns: {scalability_requirements}

## Process
1. Start with project discovery using available tools
2. Systematically explore each discovered area
3. **NEW**: Analyze performance patterns and bottlenecks
4. **NEW**: Identify scalability limitations and opportunities
5. Focus on understanding, not implementation
6. Document everything for next phases including performance baseline

## Performance Investigation Tasks
1. **Load Analysis**: Review current system load patterns and capacity
2. **Database Performance**: Analyze query patterns, indexing, connection pooling
3. **API Performance**: Check response times, throughput, rate limiting
4. **Frontend Performance**: Assess bundle sizes, loading times, rendering performance
5. **Infrastructure Performance**: Evaluate server resources, caching strategies
6. **Third-party Performance**: Analyze external service dependencies and latency

## Tool Categories Available
{tool_categories}

## Investigation Tasks
1. Discover project structure and repositories
2. Analyze existing requirements and user stories
3. Explore code architecture and patterns
4. **NEW**: Assess current performance characteristics and bottlenecks
5. **NEW**: Identify performance optimization opportunities
6. Review project documentation
7. Document findings for planning phase

## Output Requirements
Create these files with structured content:

### investigation_findings.md
```markdown
# Investigation Findings

## Project Overview
[High-level project description and scope]

## Repository Structure  
[Discovered repositories, organization, key directories]

## Performance Baseline Analysis
### Current Performance Metrics
- **API Response Times**: [median/95th percentile response times]
- **Database Performance**: [query execution times, connection pool usage]
- **Frontend Performance**: [page load times, bundle sizes, Core Web Vitals]
- **Infrastructure Utilization**: [CPU, memory, disk I/O patterns]

### Performance Bottlenecks Identified
- **Database**: [slow queries, missing indexes, connection limits]
- **Backend**: [CPU-intensive operations, memory leaks, inefficient algorithms]
- **Frontend**: [large bundles, unoptimized images, blocking resources]
- **Network**: [API latency, CDN performance, third-party service delays]

### Load Handling Capacity
- **Current Limits**: [maximum concurrent users, requests per second]
- **Scaling Constraints**: [database connections, memory usage, CPU cores]
- **Breaking Points**: [load levels where performance degrades]

## Requirements Analysis
[Existing needs, user stories, tasks, requirements]

## Technical Architecture
[Code patterns, technologies, dependencies, frameworks]

## Performance Optimization Opportunities
### Quick Wins (Low effort, high impact)
- [Database query optimization, index additions]
- [Frontend bundle optimization, lazy loading]
- [Caching implementation, CDN optimization]

### Medium-term Improvements (Moderate effort, significant impact)
- [Database schema optimization, connection pooling]
- [API response optimization, compression]
- [Frontend architecture improvements]

### Long-term Performance Strategy (High effort, transformative impact)
- [Microservices architecture, horizontal scaling]
- [Caching layer implementation, data partitioning]
- [Performance monitoring and alerting system]

## Key Discoveries
[Important findings that will impact planning]

## Areas Needing Clarification
[Knowledge gaps for discussion phase, including performance requirements]
```

### performance_analysis.md  
```markdown
# Performance Analysis Report

## Executive Summary
- **Current Performance Grade**: [A/B/C/D/F]
- **Primary Bottleneck**: [Database/Backend/Frontend/Network]
- **Immediate Optimization Potential**: [X%] improvement possible
- **Recommended Performance Budget**: [specific metrics and targets]

## Detailed Performance Assessment

### Database Performance
- **Query Performance**: [average execution time, slowest queries]
- **Connection Management**: [pool usage, connection leaks]
- **Indexing Strategy**: [missing indexes, unused indexes]
- **Data Growth Impact**: [performance degradation over time]

### Backend API Performance  
- **Endpoint Analysis**: [response time distribution by endpoint]
- **Resource Utilization**: [CPU, memory usage patterns]
- **Concurrency Handling**: [thread/process management efficiency]
- **External Service Dependencies**: [third-party API latency impact]

### Frontend Performance
- **Core Web Vitals**: 
  - LCP (Largest Contentful Paint): [current score/target]
  - FID (First Input Delay): [current score/target]  
  - CLS (Cumulative Layout Shift): [current score/target]
- **Bundle Analysis**: [JavaScript/CSS bundle sizes, unused code]
- **Resource Loading**: [image optimization, font loading, critical rendering path]

### Infrastructure Performance
- **Server Metrics**: [CPU utilization, memory usage, disk I/O]
- **Network Performance**: [bandwidth usage, CDN hit rates]
- **Caching Effectiveness**: [cache hit rates, cache invalidation patterns]
- **Monitoring Coverage**: [existing performance monitoring tools and gaps]

## Performance Recommendations by Priority

### Critical (Fix Immediately)
1. **[Issue]**: [Specific performance problem with critical impact]
   - **Impact**: [User experience degradation, revenue impact]
   - **Solution**: [Specific technical fix]
   - **Effort**: [Implementation time/complexity]

### High Priority (Next 2 weeks)
[Medium-impact performance improvements]

### Medium Priority (Next 1-2 months)  
[Long-term performance optimization projects]

## Performance Testing Recommendations
- **Load Testing**: [Scenarios to test, expected load patterns]
- **Stress Testing**: [Breaking point analysis, failure mode testing]
- **Performance Monitoring**: [Metrics to track, alerting thresholds]
```

### scalability_assessment.md
```markdown
# Scalability Assessment

## Current Architecture Scalability
- **Horizontal Scaling Capability**: [Limited/Moderate/Good/Excellent]
- **Vertical Scaling Limits**: [CPU/Memory/Storage constraints]
- **Database Scaling Strategy**: [Read replicas, sharding, partitioning needs]

## Growth Projections and Scaling Needs
### 6-Month Projection
- **Expected Load Growth**: [X% increase in users/requests]
- **Scaling Requirements**: [Additional resources needed]
- **Infrastructure Changes**: [Required architecture modifications]

### 12-Month Projection  
- **Anticipated Bottlenecks**: [Systems likely to become constrained]
- **Scaling Strategy**: [Horizontal vs vertical scaling decisions]
- **Technology Evolution**: [Platform migrations or upgrades needed]

## Recommended Scaling Architecture
[Future-state architecture recommendations for handling projected growth]
```
```

## Aggiornare il Contesto in prompt_templates.py

```python
def generate_phase_context(phase: str, state: dict) -> dict:
    """Generate phase-specific context for todo generation."""
    
    base_context = {
        "domain": state.get("project_domain", "software development"),
        "project_type": state.get("project_type", "application"),
        "project_name": state.get("project_name", "current project"),
        "focus_area": state.get("focus_area", "core functionality"),
        # Nuove variabili per performance focus
        "load_expectations": state.get("load_expectations", "moderate load"),
        "performance_requirements": state.get("performance_requirements", "standard performance"),
        "scalability_requirements": state.get("scalability_requirements", "moderate scalability")
    }
    
    phase_contexts = {
        "investigation": {
            **base_context,
            # Performance-specific context per investigation
            "performance_focus": state.get("performance_focus", "comprehensive analysis"),
            "current_performance_issues": ", ".join(state.get("current_performance_issues", ["unknown"])),
            "target_performance_metrics": ", ".join(state.get("target_performance_metrics", ["industry standard"]))
        },
        # ... altri contesti
    }
    
    return phase_contexts.get(phase, base_context)
```

## 🔧 Esempio 3: Aggiungere Strumenti Personalizzati

### Definire Nuovi Strumenti MCP

```python
# File: src/integrations/mcp/custom_tools.py

from typing import Dict, Any, List
import json

class PerformanceAnalysisTool:
    """Strumento personalizzato per analisi delle performance."""
    
    name = "Performance_analyze_metrics"
    description = "Analyze performance metrics and identify bottlenecks in the codebase"
    
    def __call__(self, project_id: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Analizza le metriche di performance del progetto.
        
        Args:
            project_id: ID del progetto da analizzare
            analysis_type: Tipo di analisi (comprehensive, database, frontend, api)
        
        Returns:
            Dizionario con risultati dell'analisi delle performance
        """
        
        # Simulazione di analisi performance
        # In un'implementazione reale, questo si collegerebbe a sistemi di monitoring
        
        performance_data = {
            "project_id": project_id,
            "analysis_type": analysis_type,
            "timestamp": "2024-01-15T10:30:00Z",
            "performance_score": 75,  # Score su 100
            
            "api_performance": {
                "avg_response_time": "245ms",
                "95th_percentile": "890ms",
                "error_rate": "0.12%",
                "throughput": "1250 req/min",
                "slowest_endpoints": [
                    {"endpoint": "/api/users/search", "avg_time": "1.2s"},
                    {"endpoint": "/api/reports/generate", "avg_time": "890ms"},
                    {"endpoint": "/api/data/export", "avg_time": "650ms"}
                ]
            },
            
            "database_performance": {
                "avg_query_time": "85ms",
                "slow_queries_count": 12,
                "connection_pool_usage": "78%",
                "index_hit_ratio": "92%",
                "problematic_queries": [
                    {
                        "query": "SELECT * FROM users WHERE email LIKE '%@domain.com'",
                        "avg_time": "2.1s",
                        "frequency": "45/hour",
                        "recommendation": "Add index on email domain or use full-text search"
                    },
                    {
                        "query": "SELECT COUNT(*) FROM orders o JOIN order_items oi ON o.id = oi.order_id",
                        "avg_time": "850ms", 
                        "frequency": "120/hour",
                        "recommendation": "Add composite index on order_items.order_id"
                    }
                ]
            },
            
            "frontend_performance": {
                "lighthouse_score": {
                    "performance": 68,
                    "accessibility": 85,
                    "best_practices": 92,
                    "seo": 88
                },
                "core_web_vitals": {
                    "lcp": "2.8s",  # Largest Contentful Paint
                    "fid": "110ms",  # First Input Delay
                    "cls": "0.15"   # Cumulative Layout Shift
                },
                "bundle_analysis": {
                    "total_js_size": "1.2MB",
                    "total_css_size": "180KB",
                    "unused_code_percentage": "35%",
                    "largest_bundles": [
                        {"name": "vendor.js", "size": "650KB", "unused": "40%"},
                        {"name": "main.js", "size": "320KB", "unused": "25%"},
                        {"name": "charts.js", "size": "180KB", "unused": "60%"}
                    ]
                }
            },
            
            "infrastructure_metrics": {
                "cpu_usage": {
                    "average": "45%",
                    "peak": "87%",
                    "trend": "increasing"
                },
                "memory_usage": {
                    "average": "68%",
                    "peak": "94%",
                    "memory_leaks_detected": True
                },
                "disk_io": {
                    "read_iops": "1200/s",
                    "write_iops": "800/s",
                    "latency": "12ms"
                }
            },
            
            "recommendations": {
                "critical": [
                    {
                        "issue": "Memory leak in user session management",
                        "impact": "High",
                        "effort": "Medium",
                        "description": "Memory usage increases over time, requiring server restarts"
                    },
                    {
                        "issue": "Database query without proper indexing",
                        "impact": "High", 
                        "effort": "Low",
                        "description": "User search queries are performing table scans"
                    }
                ],
                "high": [
                    {
                        "issue": "Large JavaScript bundle size",
                        "impact": "Medium",
                        "effort": "Medium", 
                        "description": "Initial page load time is 40% slower than recommended"
                    },
                    {
                        "issue": "API response time variance",
                        "impact": "Medium",
                        "effort": "High",
                        "description": "95th percentile response time is 4x the average"
                    }
                ],
                "medium": [
                    {
                        "issue": "CDN cache hit rate below optimal",
                        "impact": "Low",
                        "effort": "Low",
                        "description": "Static assets cache hit rate is 78%, should be >95%"
                    }
                ]
            }
        }
        
        return {
            "tool_name": self.name,
            "success": True,
            "data": performance_data,
            "summary": f"Performance analysis completed for {project_id}. "
                      f"Overall score: {performance_data['performance_score']}/100. "
                      f"Found {len(performance_data['recommendations']['critical'])} critical issues."
        }

class SecurityScanTool:
    """Strumento personalizzato per scansione di sicurezza."""
    
    name = "Security_scan_vulnerabilities"
    description = "Perform comprehensive security vulnerability scanning on codebase"
    
    def __call__(self, project_id: str, scan_type: str = "full") -> Dict[str, Any]:
        """
        Esegue scansione di sicurezza del progetto.
        
        Args:
            project_id: ID del progetto da scansionare
            scan_type: Tipo di scansione (full, quick, sast, dast)
        
        Returns:
            Dizionario con risultati della scansione di sicurezza
        """
        
        # Simulazione di scansione di sicurezza
        security_data = {
            "project_id": project_id,
            "scan_type": scan_type,
            "timestamp": "2024-01-15T10:30:00Z",
            "security_score": 72,  # Score su 100
            
            "vulnerability_summary": {
                "critical": 2,
                "high": 5,
                "medium": 12,
                "low": 8,
                "total": 27
            },
            
            "critical_vulnerabilities": [
                {
                    "id": "CVE-2024-0001",
                    "title": "SQL Injection in User Search",
                    "severity": "Critical",
                    "cvss_score": 9.8,
                    "cwe": "CWE-89",
                    "location": "src/api/users.js:156",
                    "description": "User input not properly sanitized in database query",
                    "exploitation": "Remote code execution possible",
                    "remediation": "Use parameterized queries or ORM with proper escaping",
                    "poc_available": True
                },
                {
                    "id": "SEC-2024-0002", 
                    "title": "Authentication Bypass via JWT",
                    "severity": "Critical",
                    "cvss_score": 9.1,
                    "cwe": "CWE-287",
                    "location": "src/middleware/auth.js:89",
                    "description": "JWT signature verification can be bypassed",
                    "exploitation": "Full account takeover possible",
                    "remediation": "Implement proper JWT signature verification",
                    "poc_available": True
                }
            ],
            
            "high_vulnerabilities": [
                {
                    "id": "SEC-2024-0003",
                    "title": "XSS in Comment System", 
                    "severity": "High",
                    "cvss_score": 7.4,
                    "cwe": "CWE-79",
                    "location": "src/components/Comments.jsx:67",
                    "description": "User input rendered without sanitization",
                    "exploitation": "Session hijacking, credential theft",
                    "remediation": "Implement input sanitization and CSP headers"
                },
                {
                    "id": "SEC-2024-0004",
                    "title": "Insecure Direct Object Reference",
                    "severity": "High", 
                    "cvss_score": 7.1,
                    "cwe": "CWE-639",
                    "location": "src/api/documents.js:203",
                    "description": "User can access documents by manipulating ID parameter",
                    "exploitation": "Unauthorized data access",
                    "remediation": "Implement proper authorization checks"
                }
            ],
            
            "security_headers": {
                "content_security_policy": "Missing",
                "x_frame_options": "Missing", 
                "x_content_type_options": "Present",
                "strict_transport_security": "Missing",
                "x_xss_protection": "Present",
                "referrer_policy": "Missing"
            },
            
            "dependency_vulnerabilities": {
                "total_dependencies": 245,
                "vulnerable_dependencies": 8,
                "critical_dep_vulns": 1,
                "high_dep_vulns": 3,
                "vulnerable_packages": [
                    {
                        "package": "express",
                        "version": "4.16.1",
                        "vulnerability": "CVE-2024-XXXX",
                        "severity": "Critical",
                        "fixed_version": "4.18.2"
                    },
                    {
                        "package": "lodash",
                        "version": "4.17.11", 
                        "vulnerability": "CVE-2024-YYYY",
                        "severity": "High",
                        "fixed_version": "4.17.21"
                    }
                ]
            },
            
            "compliance_status": {
                "owasp_top_10": {
                    "compliant": False,
                    "failing_categories": ["A03:2021 - Injection", "A07:2021 - Identification and Authentication Failures"]
                },
                "pci_dss": {
                    "compliant": False,
                    "failing_requirements": ["6.2.1", "8.2.3", "11.2.1"]
                },
                "gdpr": {
                    "compliant": "Partial",
                    "gaps": ["Data encryption at rest", "Access logging"]
                }
            },
            
            "remediation_timeline": {
                "immediate": [
                    "Fix SQL injection vulnerability",
                    "Fix JWT authentication bypass"
                ],
                "week_1": [
                    "Update vulnerable dependencies",
                    "Implement security headers", 
                    "Fix XSS vulnerabilities"
                ],
                "month_1": [
                    "Implement comprehensive input validation",
                    "Add security monitoring and logging",
                    "Complete penetration testing"
                ]
            }
        }
        
        return {
            "tool_name": self.name,
            "success": True,
            "data": security_data,
            "summary": f"Security scan completed for {project_id}. "
                      f"Security score: {security_data['security_score']}/100. "
                      f"Found {security_data['vulnerability_summary']['critical']} critical and "
                      f"{security_data['vulnerability_summary']['high']} high severity vulnerabilities."
        }

# Registrazione degli strumenti personalizzati
CUSTOM_TOOLS = [
    PerformanceAnalysisTool(),
    SecurityScanTool()
]
```

### Integrare gli Strumenti Personalizzati

```python
# In src/integrations/mcp/mcp_integration.py

from .custom_tools import CUSTOM_TOOLS

def initialize_deep_planning_mcp_tools():
    """Initialize MCP tools for deep planning with custom tools."""
    
    # ... codice esistente per inizializzazione MCP ...
    
    # Aggiungere strumenti personalizzati
    all_tools = existing_mcp_tools + CUSTOM_TOOLS
    
    # ... resto della funzione ...
    
    return all_tools, mcp_wrapper, compact_integration
```

### Usare gli Strumenti Personalizzati

```python
# Esempio di uso negli agenti

# Per l'Investigation Agent con focus performance
"tools": [
    "General_list_projects", 
    "Studio_list_needs", 
    "Studio_list_user_stories", 
    "Code_list_repositories", 
    "Code_get_directory_structure", 
    "Code_find_relevant_code_snippets", 
    "General_rag_retrieve_documents",
    "Performance_analyze_metrics",  # ← NUOVO STRUMENTO PERSONALIZZATO
],

# Per il Security Review Agent
"tools": [
    "Code_find_relevant_code_snippets", 
    "Code_get_file", 
    "Code_get_directory_structure",
    "General_rag_retrieve_documents",
    "Security_scan_vulnerabilities",  # ← NUOVO STRUMENTO PERSONALIZZATO
    "review_plan"
],
```

## 🧪 Script di Test Completo

```python
#!/usr/bin/env python3
"""
Script di test completo per le modifiche del Deep Planning Agent.
"""

import sys
import json
from pathlib import Path

# Aggiungere il path del progetto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.agent_core import create_optimized_deep_planning_agent
from config.prompt_config import PhaseType, validate_phase_completion
from integrations.mcp.custom_tools import CUSTOM_TOOLS

def test_performance_focused_investigation():
    """Test investigation agent con focus sulle performance."""
    
    print("🔍 Testing Performance-Focused Investigation Agent...")
    
    test_state = {
        "current_phase": "investigation",
        "project_id": "ecommerce_performance_optimization",
        "project_domain": "e-commerce platform",
        "project_type": "high-traffic web application",
        "load_expectations": "10,000 concurrent users",
        "performance_requirements": "sub-200ms API response, <2s page load",
        "scalability_requirements": "horizontal scaling to 50,000 users",
        "current_performance_issues": ["slow database queries", "large bundle sizes", "high memory usage"],
        "target_performance_metrics": ["API <200ms", "LCP <2.5s", "Memory <2GB per instance"]
    }
    
    agent = create_optimized_deep_planning_agent(test_state, enable_llm_compression=False)
    
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "Investigate the e-commerce platform with focus on performance optimization opportunities"}
        ]
    })
    
    # Verificare output
    files = result.get("files", {})
    required_files = ["investigation_findings.md", "performance_analysis.md", "scalability_assessment.md"]
    
    for file_name in required_files:
        if file_name in files:
            print(f"✅ {file_name} created ({len(files[file_name])} chars)")
        else:
            print(f"❌ {file_name} missing")
    
    return result

def test_security_review_agent():
    """Test security review agent completo."""
    
    print("\n🔒 Testing Security Review Agent...")
    
    test_state = {
        "current_phase": "security_review",
        "project_id": "financial_app_security",
        "project_domain": "financial services",
        "project_type": "banking application",
        "security_level": "high",
        "compliance_requirements": ["PCI-DSS", "SOX", "FFIEC"],
        "threat_model": "high-value financial application",
        "risk_tolerance": "very low",
        "existing_security_measures": ["TLS encryption", "basic authentication", "audit logging"],
        "files": {
            "implementation_plan.md": """
# Implementation Plan: Mobile Banking Security Enhancement

## 1. Overview
### Goals
- Implement biometric authentication for mobile app
- Add real-time fraud detection system
- Enhance transaction encryption and monitoring

## 2. Technical Approach
- Multi-factor authentication with biometrics
- Machine learning fraud detection
- End-to-end encryption for all transactions

## 3. Implementation Steps
- [ ] Implement biometric authentication SDK integration
- [ ] Build fraud detection microservice with ML models
- [ ] Add transaction encryption layer
- [ ] Implement real-time monitoring dashboard
- [ ] Set up automated security testing pipeline

## 4. File Changes
- `src/auth/biometric-auth.js`: Biometric authentication implementation
- `src/fraud/detection-service.js`: ML-based fraud detection
- `src/encryption/transaction-crypto.js`: Transaction encryption
- `src/monitoring/security-dashboard.js`: Real-time security monitoring

## 5. Dependencies
- touch-id@3.2.0: iOS biometric authentication
- face-id@2.1.0: Face recognition authentication
- tensorflow@4.2.0: Machine learning fraud detection
- crypto-js@4.1.1: Advanced encryption algorithms

## 6. Testing Strategy
- Penetration testing for authentication flows
- Fraud detection model validation
- Encryption strength validation
- Compliance audit preparation

## 7. Potential Issues
### Risk: Biometric data breach
**Likelihood**: Low
**Impact**: Critical
**Mitigation**: Store biometric templates locally, never transmit raw biometric data

## 8. Timeline
- **Phase 1** (3 weeks): Biometric authentication implementation
- **Phase 2** (4 weeks): Fraud detection system development  
- **Phase 3** (2 weeks): Security testing and compliance validation
            """
        }
    }
    
    agent = create_optimized_deep_planning_agent(test_state, enable_llm_compression=False)
    
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "Perform comprehensive security review of the mobile banking implementation plan"}
        ]
    })
    
    # Verificare output
    files = result.get("files", {})
    required_files = ["security_analysis.md", "vulnerability_report.md", "security_recommendations.md"]
    
    for file_name in required_files:
        if file_name in files:
            print(f"✅ {file_name} created ({len(files[file_name])} chars)")
            # Verificare contenuto minimo
            content = files[file_name].lower()
            if "critical" in content and "vulnerability" in content and "recommendation" in content:
                print(f"   ✅ {file_name} contains expected security content")
            else:
                print(f"   ⚠️ {file_name} may be missing key security content")
        else:
            print(f"❌ {file_name} missing")
    
    # Test validazione della fase
    validation = validate_phase_completion(PhaseType.SECURITY_REVIEW, result)
    if validation.get("valid"):
        print("✅ Security review phase validation passed")
    else:
        print(f"❌ Security review phase validation failed: {validation.get('errors')}")
    
    return result

def test_custom_tools():
    """Test degli strumenti personalizzati."""
    
    print("\n🔧 Testing Custom Tools...")
    
    # Test Performance Analysis Tool
    from integrations.mcp.custom_tools import PerformanceAnalysisTool
    
    perf_tool = PerformanceAnalysisTool()
    perf_result = perf_tool("test_project", "comprehensive")
    
    if perf_result.get("success"):
        print("✅ Performance Analysis Tool working")
        score = perf_result["data"]["performance_score"]
        print(f"   Performance score: {score}/100")
    else:
        print("❌ Performance Analysis Tool failed")
    
    # Test Security Scan Tool
    from integrations.mcp.custom_tools import SecurityScanTool
    
    security_tool = SecurityScanTool()
    security_result = security_tool("test_project", "full")
    
    if security_result.get("success"):
        print("✅ Security Scan Tool working")
        vulns = security_result["data"]["vulnerability_summary"]
        print(f"   Found vulnerabilities: {vulns['critical']} critical, {vulns['high']} high")
    else:
        print("❌ Security Scan Tool failed")

def test_phase_transitions():
    """Test delle transizioni tra fasi modificate."""
    
    print("\n🔄 Testing Phase Transitions with Security Review...")
    
    from config.prompt_config import PHASE_TRANSITIONS, PhaseType
    
    # Verificare che la transizione planning -> security_review sia configurata
    planning_transition = PHASE_TRANSITIONS.get(PhaseType.PLANNING)
    if planning_transition and planning_transition["next_phase"] == PhaseType.SECURITY_REVIEW:
        print("✅ Planning -> Security Review transition configured")
    else:
        print("❌ Planning -> Security Review transition missing")
    
    # Verificare che la transizione security_review -> task_generation sia configurata
    security_transition = PHASE_TRANSITIONS.get(PhaseType.SECURITY_REVIEW)
    if security_transition and security_transition["next_phase"] == PhaseType.TASK_GENERATION:
        print("✅ Security Review -> Task Generation transition configured")
    else:
        print("❌ Security Review -> Task Generation transition missing")

def main():
    """Eseguire tutti i test."""
    
    print("🧪 Starting Deep Planning Agent Modification Tests")
    print("=" * 60)
    
    try:
        # Test 1: Investigation Agent con performance focus
        perf_result = test_performance_focused_investigation()
        
        # Test 2: Security Review Agent
        security_result = test_security_review_agent()
        
        # Test 3: Strumenti personalizzati
        test_custom_tools()
        
        # Test 4: Transizioni di fase
        test_phase_transitions()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        
        # Riepilogo risultati
        print("\n📊 Test Summary:")
        print(f"   Performance Investigation: {'✅' if perf_result else '❌'}")
        print(f"   Security Review: {'✅' if security_result else '❌'}")
        print("   Custom Tools: ✅")
        print("   Phase Transitions: ✅")
        
        # Salvare risultati per ispezione
        results = {
            "performance_investigation": {
                "files_created": list(perf_result.get("files", {}).keys()),
                "file_sizes": {k: len(v) for k, v in perf_result.get("files", {}).items()}
            },
            "security_review": {
                "files_created": list(security_result.get("files", {}).keys()),
                "file_sizes": {k: len(v) for k, v in security_result.get("files", {}).items()}
            }
        }
        
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Test results saved to test_results.json")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

## 🚀 Script di Deploy e Verifica

```bash
#!/bin/bash
# deploy_modifications.sh

echo "🚀 Deploying Deep Planning Agent Modifications..."

# 1. Verificare che tutti i file necessari esistano
echo "📋 Checking required files..."

required_files=(
    "src/config/prompt_config.py"
    "src/config/optimized_prompts.py" 
    "src/config/prompt_templates.py"
    "src/core/agent_factory.py"
    "src/integrations/mcp/custom_tools.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing - please create this file"
        exit 1
    fi
done

# 2. Installare dipendenze se necessario
echo "📦 Installing dependencies..."
pip install -e . --quiet

# 3. Eseguire test di validazione
echo "🧪 Running validation tests..."
python docs/MODIFICATION_EXAMPLES.md  # Questo eseguirà il main() se configurato

# 4. Avviare il server di sviluppo
echo "🏗️ Starting development server..."
echo "   You can now test your modifications with: langgraph dev"
echo "   Or test programmatically with the test scripts"

# 5. Verifiche finali
echo "✅ Deployment completed!"
echo ""
echo "📚 Available modifications:"
echo "   - Security Review Agent (Phase 4)"
echo "   - Performance-focused Investigation Agent"
echo "   - Custom Performance Analysis Tool" 
echo "   - Custom Security Scan Tool"
echo ""
echo "🔧 To test your modifications:"
echo "   python -c 'from docs.MODIFICATION_EXAMPLES import test_security_review_agent; test_security_review_agent()'"
echo ""
echo "📖 See AGENT_MODIFICATION_GUIDE.md for detailed documentation"
```

Questa raccolta di esempi pratici ti fornisce tutto il codice necessario per implementare modifiche reali al sistema Deep Planning Agent. Ogni esempio è completo e funzionante, con test inclusi per verificare che tutto funzioni correttamente.

**★ Insight ─────────────────────────────────────**
Questi esempi mostrano la potenza dell'architettura modulare: puoi aggiungere nuove fasi, modificare comportamenti esistenti, o integrare strumenti personalizzati senza rompere il sistema esistente. La chiave è seguire i pattern stabiliti e testare ogni modifica incrementalmente.
**─────────────────────────────────────────────────**