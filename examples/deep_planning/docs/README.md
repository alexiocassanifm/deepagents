# Deep Planning Agent

Un agente specializzato che trasforma richieste di sviluppo complesse in piani di implementazione strutturati utilizzando una metodologia a 4 fasi con integrazione MCP e gestione todo.

## Panoramica

Il Deep Planning Agent implementa un approccio metodico per i task di sviluppo software complessi:

1. **🔍 Silent Investigation** - Esplorazione autonoma del progetto usando MCP tools
2. **💬 Targeted Discussion** - Domande mirate per chiarire i requisiti  
3. **📋 Structured Planning** - Creazione di un piano comprensivo con 8 sezioni obbligatorie
4. **⚡ Task Generation** - Scomposizione del piano in task azionabili

## Caratteristiche Principali

### ✅ Metodologia Deep Planning a 4 Fasi
- Processo strutturato che trasforma richieste vaghe in piani dettagliati
- Ogni fase ha obiettivi e deliverable specifici
- Transizioni automatiche tra le fasi con criteri di completamento

### ✅ Gestione Todo Integrata
- Utilizzo del tool `write_todos` throughout tutte le fasi
- Tracking del progresso in tempo reale
- Todo specifici per ogni fase del processo

### ✅ Integrazione MCP Fairmind
- Accesso real-time ai dati del progetto
- Analisi semantica del codice
- Recupero di documentazione e requisiti

### ✅ Human-in-the-Loop Plan Approval
- Approvazione umana obbligatoria per i piani
- Tool `review_plan` per revisione strutturata
- Possibilità di modificare o rigettare i piani

### ✅ Validazione Piano Strutturata
- 8 sezioni obbligatorie per ogni piano di implementazione
- Validazione automatica della completezza
- Criteri di successo chiari

### ✅ Orchestrazione Sub-Agenti
- Agent specializzati per ogni fase
- Separazione delle responsabilità
- Esecuzione parallela quando possibile

### ✅ Sistema di Compatibilità Modelli
- Fix automatici per problemi di serializzazione tool calls
- Registry di modelli con profili di compatibilità
- Supporto per diversi LLM (GPT, Claude, modelli open source)
- Logging per debugging e analisi

## Installazione

1. Installa le dipendenze:
```bash
cd examples/deep_planning
pip install -r requirements.txt
```

2. Configura le variabili d'ambiente per MCP (opzionale):
```bash
export FAIRMIND_MCP_URL="https://project-context.mindstream.fairmind.ai/mcp/mcp/"
export FAIRMIND_MCP_TOKEN="your_token_here"
```

## Utilizzo

### Standalone Mode

```python
from agent_core import agent

# Invocare l'agente con una richiesta
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "Voglio implementare un sistema di autenticazione utente per la mia app e-commerce"}
    ]
})

print(result["messages"][-1]["content"])
```

### LangGraph Cloud Deployment

```bash
# Deployment su LangGraph Cloud
langgraph up

# Sviluppo locale con hot reload
langgraph dev
```

## Le 4 Fasi del Deep Planning

### Fase 1: Silent Investigation 🔍

**Obiettivo**: Comprendere il progetto e la codebase senza interazione utente

**Processo**:
1. Crea todo di investigazione usando `write_todos`
2. Deploy dell'`investigation-agent` per esplorare autonomamente:
   - Progetti e repository disponibili
   - Requisiti esistenti, user stories, task
   - Architettura del codice e pattern
   - Documentazione del progetto
3. Segna i todo come completati durante l'investigazione
4. Revisiona i risultati prima di passare alla Fase 2

**Tool MCP Utilizzati**:
- `General_list_projects()` - Scoperta progetti
- `Studio_list_needs/user_stories/tasks()` - Raccolta requisiti
- `Code_list_repositories()` - Esplorazione repository
- `Code_find_relevant_code_snippets()` - Ricerca codice semantica

### Fase 2: Targeted Discussion 💬

**Obiettivo**: Chiarire i requisiti attraverso domande mirate

**Processo**:
1. Crea todo di discussione per tracciare il workflow di chiarimento
2. Deploy del `discussion-agent` per:
   - Rivedere i risultati dell'investigazione
   - Identificare gap di conoscenza
   - Generare 5-7 domande mirate
   - Processare le risposte dell'utente
3. Aggiorna i todo man mano che le domande vengono risposte
4. Documenta i chiarimenti per la fase di planning

**Tipi di Domande Generate**:
- **Vincoli Tecnici**: "Quali sono i requisiti di performance per la feature di ricerca?"
- **Preferenze Utente**: "Dovremmo prioritizzare mobile-first o desktop?"
- **Requisiti di Integrazione**: "Quali servizi third-party devono essere integrati?"
- **Chiarimenti di Scope**: "Implementiamo solo l'MVP o il feature set completo?"

### Fase 3: Structured Planning 📋

**Obiettivo**: Creare un piano di implementazione comprensivo con 8 sezioni obbligatorie

**Sezioni Obbligatorie del Piano**:
1. **Overview** - Descrizione feature, obiettivi, criteri di successo
2. **Technical Approach** - Decisioni architetturali, scelte tecnologiche
3. **Implementation Steps** - Passi dettagliati con checkbox todo
4. **File Changes** - File specifici da creare/modificare
5. **Dependencies** - Nuovi package, compatibilità versioni
6. **Testing Strategy** - Approccio testing unit/integration
7. **Potential Issues** - Rischi noti, strategie di mitigazione
8. **Timeline** - Fasi di sviluppo, milestone, stime

**Processo**:
1. Crea todo di planning per il workflow di creazione piano
2. Deploy del `planning-agent` per:
   - Sintetizzare risultati investigazione e discussione
   - Creare `implementation_plan.md` con tutte le 8 sezioni
   - Validare completezza del piano
   - Richiedere approvazione umana via tool `review_plan`

### Fase 4: Task Generation ⚡

**Obiettivo**: Trasformare il piano approvato in task di implementazione azionabili

**Processo**:
1. Crea todo di task generation per il setup finale
2. Deploy del `task-generation-agent` per:
   - Estrarre dettagli implementazione dal piano approvato
   - Creare focus chain con file chiave
   - Generare breakdown task azionabili
   - Setup tracking implementazione

**Output Generati**:
- `implementation_tasks.md` - Breakdown task implementazione
- `focus_chain.md` - File da tracciare durante implementazione
- `success_criteria.md` - Metriche di successo chiare
- `next_steps.md` - Azioni immediate da intraprendere

## Gestione Todo Throughout All Phases

Il sistema di todo management è integrato in tutte le fasi:

```python
# Esempio Todo Structure per Fase
write_todos([
    {"id": "inv1", "content": "Discover available projects", "status": "pending"},
    {"id": "inv2", "content": "Analyze project structure", "status": "pending"},
    {"id": "inv3", "content": "Gather requirements and user stories", "status": "pending"},
    {"id": "inv4", "content": "Explore code architecture", "status": "pending"},
    {"id": "inv5", "content": "Document investigation findings", "status": "pending"}
])
```

## MCP Tools Disponibili

### Project Discovery
- `General_list_projects()` - Lista progetti disponibili
- `General_list_user_attachments(project_id)` - Lista documenti progetto
- `General_get_document_content(document_id)` - Ottieni contenuto documento

### Requirements Analysis  
- `Studio_list_needs(project_id)` - Ottieni needs progetto
- `Studio_list_user_stories(project_id)` - Ottieni user stories
- `Studio_list_tasks(project_id)` - Ottieni task progetto
- `Studio_list_requirements(project_id)` - Ottieni requisiti

### Code Analysis
- `Code_list_repositories(project_id)` - Lista repository codice
- `Code_get_directory_structure(project_id, repository_id)` - Struttura repository
- `Code_find_relevant_code_snippets(query, project_id)` - Ricerca codice semantica
- `Code_get_file(project_id, repository_id, file_path)` - Contenuti file

### Documentation Search
- `General_rag_retrieve_documents(query, project_id)` - Ricerca documenti semantica

## File System Mock

L'agente usa un file system mock per:
- **investigation_findings.md** - Risultati fase investigazione
- **clarification_questions.md** - Domande per l'utente
- **user_responses.md** - Chiarimenti utente
- **implementation_plan.md** - Il documento piano principale (8 sezioni)
- **focus_chain.md** - File da tracciare durante implementazione
- **implementation_tasks.md** - Breakdown task per esecuzione

## Criteri di Successo

Il Deep Planning è completo quando:
- ✅ Tutte le 4 fasi sono state eseguite
- ✅ Tutti i todo delle fasi sono marcati come completati
- ✅ Il piano di implementazione ha tutte le 8 sezioni
- ✅ Il piano è stato approvato dall'umano
- ✅ Il breakdown task è pronto per l'implementazione
- ✅ La focus chain è stabilita per il tracking

## Punti di Interazione Umana

- **Fase 2**: Domande di chiarimento mirate
- **Fase 3**: Richiesta approvazione piano via tool `review_plan`
- **Tra le fasi**: Aggiornamenti di stato brevi sul progresso

## Esempio di Workflow Completo

1. **Utente**: "Voglio implementare un sistema di notifiche push per la mia app mobile"

2. **Fase 1 - Investigation**: L'agente esplora automaticamente:
   - Progetti disponibili
   - Architettura app esistente
   - Pattern notifiche attuali
   - Documenti tecnici

3. **Fase 2 - Discussion**: L'agente chiede:
   - "Che piattaforme mobile supportiamo? iOS, Android o entrambe?"
   - "Abbiamo già un provider push notification o dobbiamo sceglierne uno?"
   - "Che tipi di notifiche: marketing, transazionali o entrambi?"

4. **Fase 3 - Planning**: L'agente crea un piano con 8 sezioni e richiede approvazione

5. **Fase 4 - Task Generation**: L'agente genera task azionabili e focus chain per implementazione

## Sistema di Compatibilità Modelli

Il Deep Planning Agent include un sistema avanzato di compatibilità per garantire il funzionamento ottimale con diversi modelli LLM.

### 🔧 Funzionalità

#### Rilevamento Automatico del Modello
L'agente rileva automaticamente il modello in uso da:
- Variabile d'ambiente `DEEPAGENTS_MODEL`
- Altre variabili d'ambiente comuni (`ANTHROPIC_MODEL`, `OPENAI_MODEL`, etc.)
- Configurazione di default

#### Registry di Compatibilità
Database integrato di modelli con profili di compatibilità:

```python
# Esempi di modelli supportati
"claude-3.5-sonnet"    # ✅ Eccellente - nessun fix necessario
"claude-3-sonnet"      # ✅ Eccellente - nessun fix necessario  
"gpt-4-turbo"          # ⚠️  Minimo - fix occasionali
"gpt-3.5-turbo"        # 🔧 Moderato - fix regolari
"llama-based-models"   # 🚧 Estensivo - molti fix necessari
```

#### Fix Automatici Applicati

**JSON String → Python List**
Corregge automaticamente modelli che inviano parametri come stringhe JSON:
```python
# Problema: modello invia
'[{"content": "Review findings", "status": "in_progress"}]'

# Fix: converte automaticamente a
[{"content": "Review findings", "status": "in_progress"}]
```

**Validazione e Normalizzazione**
- Aggiunge campi mancanti (es. `id`, `status` di default)
- Valida struttura dei todo
- Corregge valori di status non validi

### 🚀 Configurazione

#### Abilitazione Automatica
Il sistema si attiva automaticamente per modelli che ne hanno bisogno:

```bash
# Set model via environment
export DEEPAGENTS_MODEL="gpt-3.5-turbo"

# Il sistema applicherà automaticamente i fix necessari
python deep_planning_agent.py
```

#### Output di Configurazione
All'avvio, l'agente mostra la configurazione di compatibilità:

```
🔧 Model Compatibility Configuration:
🤖 Detected/Configured model: gpt-3.5-turbo
🛡️  Compatibility fixes enabled: True

🤖 Model Compatibility Report: gpt-3.5-turbo
===================================================
📋 Profile: gpt-3.5-turbo
🎯 Compatibility Level: moderate
⚠️  Known Issues:
   • Serializes list parameters as JSON strings
   • Inconsistent tool call formatting
🔧 Fixes Applied:
   • write_todos_json_fix
📝 Notes: Earlier GPT models often serialize complex parameters as JSON strings
```

#### Aggiunta di Nuovi Modelli

Per aggiungere supporto per un nuovo modello:

```python
# In model_compatibility.py
from model_compatibility import default_registry, ModelCompatibilityProfile, CompatibilityLevel

# Registra nuovo modello
new_model = ModelCompatibilityProfile(
    name="nuovo-modello",
    patterns=[r"nuovo.*modello", r"new.*model"],
    compatibility_level=CompatibilityLevel.MINIMAL,
    known_issues=["Specific issue description"],
    fixes_needed={"write_todos_json_fix"},
    notes="Additional notes about the model"
)

default_registry.register_model(new_model)
```

### 🐛 Debugging

#### Logging di Compatibilità
Il sistema logga tutte le conversioni e fix applicati:

```python
# Abilita logging dettagliato
from tool_compatibility import setup_compatibility_logging
setup_compatibility_logging(level="DEBUG")
```

#### Log di Esempio
```
2024-01-15 10:30:15 - deepagents.compatibility - INFO - Detected JSON string input for write_todos, attempting to parse...
2024-01-15 10:30:15 - deepagents.compatibility - INFO - Successfully processed 3 todos for write_todos
2024-01-15 10:30:15 - deepagents.compatibility - INFO - Applied compatibility fixes for: write_todos
```

#### Disabilitazione per Testing
Per disabilitare i fix durante il testing:

```python
# Forza disabilitazione
ENABLE_COMPATIBILITY_FIXES = False
```

### 🔮 Estensibilità

Il sistema è progettato per essere facilmente estendibile:

**Nuovi Tool Fix**
- Aggiungi wrapper in `tool_compatibility.py`
- Registra il fix nel sistema

**Nuovi Tipi di Problemi**
- Estendi `ModelCompatibilityProfile`
- Aggiungi logica di rilevamento

**Model-Specific Behaviors**
- Crea profili personalizzati
- Applica fix condizionali

## Troubleshooting

### MCP Server Non Disponibile
Se il server MCP Fairmind non è disponibile, l'agente utilizza automaticamente tool demo di fallback che forniscono dati mock per lo sviluppo e testing.

### Missing Environment Variables
Se `FAIRMIND_MCP_TOKEN` non è settato, l'agente funziona in modalità demo con dati mock.

### Plan Approval Issues
Se l'approvazione del piano fallisce, l'agente tornerà alla fase di planning per ricreare il piano in base al feedback ricevuto.

### Tool Compatibility Issues

#### Errori di Validazione Tool
Se vedi errori come:
```
1 validation error for write_todos
todos
  Input should be a valid list [type=list_type, input_value='[{"content": ...}]', input_type=str]
```

**Soluzione**: Il sistema di compatibilità dovrebbe risolvere automaticamente questo problema. Se persiste:
1. Verifica che il modello sia riconosciuto nel registry
2. Abilita logging DEBUG per vedere i dettagli
3. Considera di aggiungere un profilo personalizzato per il modello

#### Performance con Fix Abilitati
I fix di compatibilità hanno overhead minimo per modelli che funzionano correttamente. Per modelli problematici, l'overhead è compensato dall'affidabilità migliorata.

#### Aggiornamenti di deepagents
Il sistema di compatibilità è progettato per non interferire con gli aggiornamenti di deepagents:
- Non modifica il codice sorgente originale
- Usa wrapper e monkey patching
- Può essere facilmente disabilitato se necessario

## Contribuire

Per contribuire al Deep Planning Agent:

1. Fork il repository
2. Crea un feature branch
3. Implementa le modifiche
4. Aggiungi test se necessario  
5. Submit una pull request

---

**Deep Planning Agent**: Trasforma richieste complesse in piani strutturati con metodologia a 4 fasi, todo management integrato e human-in-the-loop approval.