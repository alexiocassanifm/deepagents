# Deep Planning Implementation Analysis

## Overview & Goals

Deep Planning (`/deep-planning`) is a structured approach to complex software development tasks that implements a 4-phase methodology:

1. **Silent Investigation** - Autonomous exploration and analysis
2. **Targeted Discussion** - Clarifying questions and requirements gathering  
3. **Structured Planning** - Comprehensive plan document creation
4. **Task Generation** - Breaking down the plan into actionable tasks

The feature transforms ad-hoc development requests into methodical, well-documented implementation plans with clear progress tracking.

## Core Architecture

### Slash Command System
**Location**: `src/core/slash-commands/index.ts`

```typescript
export function parseSlashCommands(input: string): ParsedSlashCommand | null {
  // Deep planning command detection
  if (input.trim() === '/deep-planning') {
    return {
      type: 'deep-planning',
      content: input,
      originalInput: input
    }
  }
  return null
}
```

### Command Processing Flow
**Location**: `src/core/prompts/responses.ts`

```typescript
export function deepPlanningToolResponse(cwd: string): ToolResponse {
  return {
    tool: "str_replace_based_edit_tool",
    content: `# Deep Planning Mode Activated

You are now in Deep Planning mode. Follow this structured 4-step process...`,
    isError: false
  }
}
```

## Deep Planning Methodology

### Phase 1: Silent Investigation
- **Objective**: Understand the codebase and requirements without user interaction
- **Actions**: File exploration, terminal commands, dependency analysis
- **Output**: Internal understanding of current state

**Implementation Pattern**:
```typescript
// Silent investigation tools
- read_file: Explore existing code
- list_files: Understand project structure  
- execute_command: Check dependencies, run tests
- search_files: Find relevant patterns
```

### Phase 2: Targeted Discussion
- **Objective**: Gather missing information through focused questions
- **Actions**: Ask specific technical questions about requirements
- **Output**: Clarified requirements and constraints

**Implementation Pattern**:
```typescript
// Discussion phase markers
"## Questions for Clarification"
"Before proceeding with the implementation plan, I need to clarify..."
```

### Phase 3: Structured Planning
- **Objective**: Create comprehensive implementation plan document
- **Actions**: Generate `implementation_plan.md` with 8 required sections
- **Output**: Detailed plan file with todos and technical approach

### Phase 4: Task Generation  
- **Objective**: Create new task with structured context
- **Actions**: Use `new_task` tool with plan reference and focus chain
- **Output**: New actionable task ready for execution

## Plan Document Structure

### Required Sections in `implementation_plan.md`

```markdown
# Implementation Plan: [Feature Name]

## 1. Overview
- Feature description and goals
- Success criteria
- User impact

## 2. Technical Approach  
- Architecture decisions
- Technology choices
- Integration patterns

## 3. Implementation Steps
- [ ] Step 1: Setup and scaffolding
- [ ] Step 2: Core functionality
- [ ] Step 3: Integration
- [ ] Step 4: Testing
- [ ] Step 5: Documentation

## 4. File Changes
- `src/component.ts` - New component implementation
- `tests/component.test.ts` - Test coverage
- `docs/feature.md` - Documentation

## 5. Dependencies
- New packages required
- Version compatibility
- Breaking changes

## 6. Testing Strategy
- Unit test approach
- Integration test scenarios
- Manual testing steps

## 7. Potential Issues
- Known risks and mitigation
- Performance considerations
- Edge cases

## 8. Timeline
- Development phases
- Milestones and deliverables
- Estimated effort
```

## System Integration

### Plan/Act Mode Integration
**Location**: `src/core/context/instructions/user-instructions/workflows.ts`

Deep Planning automatically enables Plan/Act mode for structured execution:

```typescript
// Plan/Act mode prompts
const planActInstructions = `
When plan_act_mode is enabled:
1. Always announce your plan before taking action
2. Ask for approval before executing potentially disruptive operations
3. Break complex tasks into smaller, reviewable steps
`
```

### Focus Chain Integration
Deep Planning seamlessly integrates with Focus Chain:

```typescript
// Plan document triggers focus chain creation
"Create a focus chain file to track progress through the implementation plan files"

// Files automatically added to focus chain
const focusChainFiles = [
  "implementation_plan.md",
  ...extractedImplementationFiles
]
```

### Task State Management
**Location**: `src/core/task/TaskState.ts`

```typescript
interface TaskState {
  deepPlanningEnabled?: boolean
  planDocumentPath?: string
  currentPhase?: 'investigation' | 'discussion' | 'planning' | 'implementation'
  planningContext?: {
    originalRequest: string
    clarifications: string[]
    investigationFindings: string[]
  }
}
```

## Prompt Engineering Analysis

### Core Deep Planning Prompt
**Location**: `src/core/prompts/responses.ts`

The deep planning prompt implements a sophisticated instruction set:

```typescript
const DEEP_PLANNING_INSTRUCTIONS = `
# Deep Planning Mode - 4 Step Process

## Step 1: Silent Investigation (No User Interaction)
- Explore codebase thoroughly using available tools
- Understand existing architecture and patterns  
- Identify dependencies and constraints
- Document findings internally

## Step 2: Targeted Discussion  
- Ask focused questions about unclear requirements
- Clarify technical constraints and preferences
- Gather missing context needed for planning
- Keep questions specific and actionable

## Step 3: Structured Planning
- Create comprehensive implementation_plan.md
- Must include all 8 required sections
- Use checkbox format for action items
- Be specific about file changes and technical approach

## Step 4: Task Generation
- Use new_task tool to create implementation task
- Reference the plan document 
- Set up focus chain for progress tracking
- Include clear success criteria
`
```

### Phase Transition Logic
```typescript
// Phase detection patterns
const PHASE_MARKERS = {
  investigation: /^(reading|exploring|analyzing|checking)/i,
  discussion: /^(questions?|clarification|before proceeding)/i, 
  planning: /^(implementation plan|creating plan|planning)/i,
  task_generation: /^(creating task|new task|ready to implement)/i
}
```

## File Generation Process

### Plan Document Creation
```typescript
async function createPlanDocument(planContent: string, taskDir: string) {
  const planPath = path.join(taskDir, 'implementation_plan.md')
  
  // Validate required sections
  const requiredSections = [
    '## 1. Overview',
    '## 2. Technical Approach', 
    '## 3. Implementation Steps',
    '## 4. File Changes',
    '## 5. Dependencies',
    '## 6. Testing Strategy',
    '## 7. Potential Issues',
    '## 8. Timeline'
  ]
  
  validatePlanSections(planContent, requiredSections)
  
  await fs.writeFile(planPath, planContent)
  return planPath
}
```

### Task Creation Integration
```typescript
// new_task tool usage pattern
{
  "tool": "new_task",
  "description": "Implement [feature] following the detailed plan",
  "content": `Implement the feature as outlined in implementation_plan.md.

Key files to focus on:
- ${planDocument.fileChanges.join('\n- ')}

Success criteria:
- ${planDocument.successCriteria.join('\n- ')}

Refer to implementation_plan.md for complete technical details and step-by-step approach.`
}
```

## Error Handling & Validation

### Plan Validation Logic
```typescript
function validatePlanDocument(content: string): ValidationResult {
  const errors: string[] = []
  
  // Check required sections
  REQUIRED_SECTIONS.forEach(section => {
    if (!content.includes(section)) {
      errors.push(`Missing required section: ${section}`)
    }
  })
  
  // Check for actionable items
  const todoPattern = /- \[ \]/g
  const todoCount = (content.match(todoPattern) || []).length
  if (todoCount < 3) {
    errors.push('Plan must include at least 3 actionable todo items')
  }
  
  // Validate file paths
  const filePattern = /`([^`]+\.(ts|js|tsx|jsx|py|md))`/g
  const files = content.match(filePattern)
  if (!files || files.length < 1) {
    errors.push('Plan must specify specific files to be modified')
  }
  
  return { valid: errors.length === 0, errors }
}
```

### Recovery Mechanisms
```typescript
// Handle incomplete plans
if (!isValidPlan(planContent)) {
  return `The plan appears incomplete. Please ensure all 8 sections are included:
${REQUIRED_SECTIONS.join('\n')}`
}

// Handle missing clarifications
if (hasUnansweredQuestions(context)) {
  return `Some questions from Step 2 remain unanswered. Please provide clarification before proceeding to implementation.`
}
```

## LangGraph Node Design Specifications

### State Schema
```python
from typing import List, Optional, Literal
from pydantic import BaseModel

class DeepPlanningState(BaseModel):
    phase: Literal['investigation', 'discussion', 'planning', 'implementation'] = 'investigation'
    original_request: str
    investigation_findings: List[str] = []
    clarification_questions: List[str] = []
    clarifications_received: List[str] = []
    plan_document_path: Optional[str] = None
    plan_content: Optional[str] = None
    implementation_files: List[str] = []
    task_created: bool = False

class PlanSection(BaseModel):
    title: str
    content: str
    todos: List[str] = []
    
class ImplementationPlan(BaseModel):
    overview: PlanSection
    technical_approach: PlanSection  
    implementation_steps: PlanSection
    file_changes: PlanSection
    dependencies: PlanSection
    testing_strategy: PlanSection
    potential_issues: PlanSection
    timeline: PlanSection
```

### Node Implementations

```python
def deep_planning_router(state: AgentState) -> str:
    """Route to appropriate phase based on current state"""
    if not state.deep_planning_state:
        return "investigation"
    
    phase = state.deep_planning_state.phase
    
    if phase == "investigation" and investigation_complete(state):
        return "discussion"
    elif phase == "discussion" and all_questions_answered(state):
        return "planning" 
    elif phase == "planning" and plan_document_created(state):
        return "task_generation"
    else:
        return phase

def investigation_node(state: AgentState) -> AgentState:
    """Silent investigation phase"""
    # Use tools to explore codebase
    file_structure = explore_project_structure(state.workspace_path)
    dependencies = analyze_dependencies(state.workspace_path)
    existing_patterns = find_relevant_patterns(state.workspace_path, state.request)
    
    state.deep_planning_state.investigation_findings.extend([
        f"Project structure: {file_structure}",
        f"Dependencies: {dependencies}", 
        f"Relevant patterns: {existing_patterns}"
    ])
    
    state.deep_planning_state.phase = "discussion"
    return state

def discussion_node(state: AgentState) -> AgentState:
    """Targeted discussion phase"""
    questions = generate_clarification_questions(
        state.request,
        state.deep_planning_state.investigation_findings
    )
    
    if questions:
        state.deep_planning_state.clarification_questions = questions
        state.messages.append(SystemMessage(
            content=f"Questions for clarification:\n" + "\n".join(questions)
        ))
        # Wait for user response
        return state
    else:
        state.deep_planning_state.phase = "planning"
        return state

def planning_node(state: AgentState) -> AgentState:
    """Structured planning phase"""
    plan = generate_implementation_plan(
        request=state.request,
        findings=state.deep_planning_state.investigation_findings,
        clarifications=state.deep_planning_state.clarifications_received
    )
    
    # Validate plan completeness
    validation = validate_plan_structure(plan)
    if not validation.valid:
        raise ValueError(f"Invalid plan: {validation.errors}")
    
    # Save plan document
    plan_path = save_plan_document(plan, state.workspace_path)
    
    state.deep_planning_state.plan_document_path = plan_path
    state.deep_planning_state.plan_content = plan
    state.deep_planning_state.phase = "task_generation"
    
    return state

def task_generation_node(state: AgentState) -> AgentState:
    """Task generation phase"""
    # Extract implementation files from plan
    files = extract_implementation_files(state.deep_planning_state.plan_content)
    
    # Create new task
    task_content = generate_task_content(
        state.deep_planning_state.plan_document_path,
        files
    )
    
    # Create focus chain with plan files
    create_focus_chain(files + [state.deep_planning_state.plan_document_path])
    
    state.deep_planning_state.task_created = True
    state.messages.append(SystemMessage(
        content=f"Implementation task created with plan: {state.deep_planning_state.plan_document_path}"
    ))
    
    return state
```

### Plan Generation Engine
```python
class PlanGenerator:
    def __init__(self, template_path: str):
        self.template = self.load_template(template_path)
    
    def generate_plan(self, 
                     request: str,
                     findings: List[str],
                     clarifications: List[str]) -> str:
        """Generate structured implementation plan"""
        
        context = {
            'request': request,
            'findings': findings,
            'clarifications': clarifications,
            'timestamp': datetime.now().isoformat()
        }
        
        sections = {}
        for section_name in REQUIRED_SECTIONS:
            sections[section_name] = self.generate_section(
                section_name, context
            )
        
        return self.template.render(sections=sections, **context)
    
    def generate_section(self, section_name: str, context: dict) -> PlanSection:
        """Generate individual plan section"""
        prompt = self.get_section_prompt(section_name)
        
        # Use LLM to generate section content
        content = self.llm.invoke(prompt.format(**context))
        
        # Extract todos from content
        todos = extract_todos(content)
        
        return PlanSection(
            title=section_name,
            content=content,
            todos=todos
        )
```

### Validation Framework
```python
class PlanValidator:
    REQUIRED_SECTIONS = [
        "Overview", "Technical Approach", "Implementation Steps",
        "File Changes", "Dependencies", "Testing Strategy", 
        "Potential Issues", "Timeline"
    ]
    
    def validate_plan(self, plan_content: str) -> ValidationResult:
        """Comprehensive plan validation"""
        errors = []
        
        # Section validation
        for section in self.REQUIRED_SECTIONS:
            if not self.has_section(plan_content, section):
                errors.append(f"Missing section: {section}")
        
        # Todo validation  
        todos = self.extract_todos(plan_content)
        if len(todos) < 3:
            errors.append("Plan must contain at least 3 actionable items")
            
        # File validation
        files = self.extract_file_paths(plan_content)
        if len(files) < 1:
            errors.append("Plan must specify files to be modified")
            
        # Technical depth validation
        if not self.has_technical_details(plan_content):
            errors.append("Plan lacks sufficient technical detail")
            
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def extract_todos(self, content: str) -> List[str]:
        """Extract todo items from markdown"""
        import re
        pattern = r'- \[ \] (.+)'
        return re.findall(pattern, content)
    
    def extract_file_paths(self, content: str) -> List[str]:
        """Extract file paths from plan"""
        import re
        pattern = r'`([^`]+\.(ts|js|tsx|jsx|py|md|json))`'
        matches = re.findall(pattern, content)
        return [match[0] for match in matches]
```

## Implementation Recommendations

### 1. Modular Phase Design
- Implement each phase as a separate node
- Use state machines for phase transitions
- Enable phase rollback for error recovery

### 2. Template System
- Create customizable plan templates
- Support project-specific sections
- Enable section reordering and customization

### 3. Validation Pipeline
- Multi-stage plan validation
- Real-time feedback during generation
- Automatic plan improvement suggestions

### 4. Integration Patterns
- Clean interfaces with focus chain
- Task creation automation
- Progress tracking integration

### 5. Error Recovery
- Graceful handling of incomplete plans
- Automatic retry mechanisms
- User intervention points

Deep Planning represents a sophisticated approach to structured software development that can be effectively reimplemented as a multi-node LangGraph workflow with proper state management and validation.