# Deep Planning Agent - Analisi e Miglioramenti dei Prompt

## Sommario Esecutivo

L'analisi comparativa tra i prompt del deep planning agent e il notebook ufficiale di LangGraph ha evidenziato significative opportunità di miglioramento. Il prompt principale attuale di 650+ righe può essere ridotto del 60-70% applicando i principi di modularità e responsabilità singola.

**Problemi Chiave Identificati:**
- Prompt principale eccessivamente lungo (650+ righe vs 50-150 raccomandato)
- Gestione dei todo ripetitiva tra tutti i sub-agent
- Miscelazione di responsabilità di orchestrazione ed esecuzione
- Esempi hard-coded invece di template dinamici
- Descrizioni degli strumenti integrate nei prompt

**Impatto dei Miglioramenti:**
- Riduzione del 60-70% della lunghezza dei prompt
- Migliore focus e performance degli agent
- Maggiore manutenibilità e debugging
- Gestione dello stato potenziata

## Analisi Dettagliata

### Confronto Struttura Attuale vs Best Practice LangGraph

| Aspetto | Approccio Attuale | Best Practice LangGraph |
|---------|-------------------|------------------------|
| **Lunghezza Prompt** | 650+ righe per agent principale | 50-150 righe per agent |
| **Responsabilità** | Orchestrazione + esecuzione mista | Responsabilità singola per agent |
| **Integrazione Tool** | Descrizioni manuali degli strumenti | Scoperta strumenti gestita dal framework |
| **Gestione Stato** | Istruzioni basate su prompt | Schema stato LangGraph |
| **Gestione Todo** | Esempi ripetuti in ogni prompt | Approccio centralizzato basato su stato |

### Aree Problematiche Specifiche

#### 1. **Bloat del Prompt e Diluizione dell'Attenzione**

**Problema Attuale:**
Il prompt principale del deep planning agent contiene:
- 650+ righe di istruzioni dettagliate
- Responsabilità multiple mescolate insieme
- Esempi verbosi ripetuti per ogni fase

**Impatto:** I LLM perdono focus con prompt estremamente lunghi, portando a prestazioni degradate.

#### 2. **Gestione Todo Ripetitiva**

**Problema Identificato:**
Ogni sub-agent ripete pattern simili per i todo:
```python
# Investigation Agent
write_todos([
    {"id": "inv1", "content": "Discover available projects", "status": "pending"},
    ...
])

# Discussion Agent  
write_todos([
    {"id": "disc1", "content": "Review investigation findings", "status": "pending"},
    ...
])
```

**Problema:** Informazioni ridondanti che potrebbero essere centralizzate e rese context-aware.

#### 3. **Responsabilità Miste nell'Orchestratore**

**Problema:** L'agent principale cerca di gestire sia l'orchestrazione CHE fornire istruzioni dettagliate per le fasi.

**Violazione:** Principio di responsabilità singola e crea confusione.

## Raccomandazioni Specifiche

### 1. **Architettura Modulare dei Prompt**

#### Prompt Orchestratore Principale Raccomandato

```python
main_orchestrator_prompt = """Sei il Deep Planning Orchestrator, responsabile del coordinamento di un processo di pianificazione dello sviluppo a 4 fasi.

## Il Tuo Ruolo
Coordina i sub-agent attraverso fasi strutturate, assicurando transizioni fluide e validazione della completezza.

## Flusso del Processo
1. **Fase Investigazione** → Deploya investigation-agent per esplorazione autonoma del progetto
2. **Fase Discussione** → Deploya discussion-agent per chiarimento requisiti
3. **Fase Pianificazione** → Deploya planning-agent per creazione piano completo
4. **Generazione Task** → Deploya task-generation-agent per setup implementazione

## Fase Attuale: {current_phase}
## Contesto Disponibile: {context_summary}

## I Tuoi Compiti
- Deploya il sub-agent appropriato per la fase attuale
- Valida il completamento della fase prima della transizione
- Mantieni la consistenza dello stato tra le fasi
- Gestisci i punti di interazione umana (domande, approvazioni)

## Criteri di Successo
Ogni fase deve essere marcata come completa con validazione prima di procedere alla successiva.
"""
```

#### Prompt Investigation Agent Raccomandato

```python
investigation_agent_prompt = """Sei l'Investigation Agent per l'esplorazione autonoma del progetto.

## La Tua Missione
Esplora e comprendi il contesto del progetto senza interazione utente.

## Contesto Attuale
- Project ID: {project_id}
- Strumenti disponibili: {available_tools}
- Focus investigazione: {investigation_focus}

## Task di Investigazione
1. Scopri struttura del progetto e repository
2. Analizza requisiti esistenti e user story
3. Esplora architettura del codice e pattern
4. Documenta i risultati per la fase di pianificazione

## Requisiti Output
- investigation_findings.md con scoperte strutturate
- project_context.md con panoramica progetto
- technical_analysis.md con insights architettura

## Strumenti Disponibili
Usa strumenti MCP per scoperta e analisi progetto. Concentrati sulla raccolta di informazioni complete autonomamente.
"""
```

### 2. **Gestione Todo Basata su Stato**

#### Approccio Problematico Attuale
```python
# Hard-coded in ogni prompt
write_todos([
    {"id": "inv1", "content": "Discover available projects", "status": "pending"},
    # ... ripetuto tra gli agent
])
```

#### Approccio Template-Based Raccomandato
```python
def generate_phase_todos(phase: str, context: dict) -> list:
    """Genera todo context-aware per ogni fase"""
    todo_templates = {
        "investigation": [
            "Scopri progetti in {domain}",
            "Analizza architettura {project_type}", 
            "Documenta risultati {focus_area}"
        ],
        "discussion": [
            "Rivedi risultati per {project_id}",
            "Genera domande su {unclear_areas}",
            "Processa risposte per {requirement_type}"
        ]
    }
    return [
        {"id": f"{phase[:3]}{i}", "content": template.format(**context), "status": "pending"}
        for i, template in enumerate(todo_templates.get(phase, []), 1)
    ]
```

### 3. **Miglioramenti Integrazione Strumenti**

#### Approccio Statico Attuale
```python
## Available MCP Tools:
- General_list_projects() - Discover available projects
- Studio_list_needs(project_id) - Get project needs  
# ... 20+ righe di descrizioni manuali strumenti
```

#### Approccio Dinamico Raccomandato
```python
tool_integration_prompt = """## Strumenti Disponibili
Hai accesso a {tool_count} strumenti specializzati per {current_phase}.
Usa gli strumenti in modo contestuale basato sui tuoi task attuali.

Categorie chiave strumenti:
{tool_categories}

Concentrati su strumenti rilevanti per: {phase_objectives}
"""

def get_tool_context(phase: str, available_tools: list) -> dict:
    """Genera contesto dinamico strumenti per la fase attuale"""
    tool_categories = categorize_tools_by_phase(available_tools, phase)
    return {
        "tool_count": len(available_tools),
        "current_phase": phase,
        "tool_categories": format_tool_categories(tool_categories),
        "phase_objectives": get_phase_objectives(phase)
    }
```

### 4. **Validazione e Gestione Errori**

#### Prompt di Validazione Raccomandati
```python
planning_validation_prompt = """## Checklist Validazione Piano

Il tuo piano di implementazione deve includere TUTTE le sezioni richieste:

✅ Requisiti di Validazione:
- [ ] Panoramica con obiettivi chiari e criteri di successo
- [ ] Approccio tecnico con decisioni architetturali
- [ ] Passi implementazione con todo azionabili
- [ ] Modifiche file con percorsi specifici
- [ ] Dipendenze con requisiti versione
- [ ] Strategia testing con approccio validazione
- [ ] Analisi rischi con strategie mitigazione
- [ ] Timeline con stime realistiche

## Stato Piano Attuale
Sezioni mancanti: {missing_sections}
Errori validazione: {validation_errors}

{validation_instructions}
"""
```

### 5. **Deployment Sub-Agent Context-Aware**

#### Logica Selezione Agent Raccomandato
```python
agent_deployment_prompt = """## Decisione Deployment Sub-Agent

Situazione attuale:
- Fase: {current_phase}
- Contesto: {available_context}
- Output precedenti: {previous_outputs}
- Stato validazione: {validation_status}

## Azione Raccomandata
{deployment_recommendation}

## Configurazione Agent
- Agent: {selected_agent}
- Strumenti: {agent_tools}
- Contesto: {agent_context}
- Criteri successo: {success_criteria}
"""
```

## Roadmap di Implementazione

### Fase 1: Ristrutturazione Prompt (Settimana 1)
1. **Dividi prompt monolitico principale** in orchestratore + template
2. **Crea prompt sub-agent modulari** con responsabilità singole
3. **Implementa generazione todo basata su template**
4. **Aggiungi generazione contesto strumenti dinamico**

### Fase 2: Integrazione Stato (Settimana 2)
1. **Potenzia schema stato** per migliore tracciamento fase
2. **Implementa middleware validazione** per transizioni fase
3. **Aggiungi rendering prompt context-aware**
4. **Crea template gestione errori**

### Fase 3: Testing & Ottimizzazione (Settimana 3)
1. **Test A/B variazioni prompt** per efficacia
2. **Misura miglioramenti performance** (qualità risposta, consistenza)
3. **Ottimizza template prompt** basato su pattern di utilizzo
4. **Aggiungi monitoring per efficacia prompt**

## Esempio Struttura Prompt Migliorata

### Il Prompt Orchestratore Principale
```python
orchestrator_prompt_template = """Sei il Deep Planning Orchestrator che gestisce un processo di pianificazione sviluppo a {phase_count} fasi.

## Stato Attuale
- Fase: {current_phase} di {total_phases}
- Contesto: {context_summary}
- Progresso: {completion_percentage}%

## Il Tuo Ruolo
Deploya e coordina sub-agent per pianificazione sviluppo strutturata.

{phase_specific_instructions}

## Prossima Azione
{recommended_action}

## Validazione Successo
{validation_criteria}
"""
```

### Prompt Investigation Agent Migliorato
```python
investigation_agent_prompt = """Sei un Investigation Agent focalizzato sull'esplorazione autonoma del progetto.

## Missione
{investigation_mission}

## Contesto
- Target: {investigation_target}
- Strumenti: {available_tool_count} strumenti specializzati
- Focus: {investigation_focus}

## Processo
1. {investigation_step_1}
2. {investigation_step_2}
3. {investigation_step_3}

## Formato Output
{output_specifications}

Inizia investigazione usando strumenti MCP disponibili.
"""
```

## Note di Implementazione

### Tecniche Chiave Utilizzate
- **Prompt basati su template** per consistenza e manutenibilità
- **Iniezione contesto** per istruzioni dinamiche e rilevanti
- **Responsabilità singola** per ogni prompt agent
- **Logica basata su stato** invece di gestione stato basata su prompt
- **Template validazione** per controlli qualità consistenti

### Perché Queste Scelte
- **Ridotto carico cognitivo** migliora focus e performance LLM
- **Design modulare** abilita testing e ottimizzazione più facili
- **Approccio template** permette customizzazione dinamica basata su contesto
- **Integrazione stato** sfrutta i punti di forza di LangGraph
- **Focus validazione** assicura qualità output consistente

### Risultati Attesi
- **Riduzione 60-70%** nella lunghezza prompt
- **Migliorato focus agent** su responsabilità specifiche
- **Migliore gestione errori** con template validazione
- **Manutenibilità potenziata** attraverso struttura modulare
- **Performance consistente** tra scenari diversi

## Insights Tecnici

`★ Insight ─────────────────────────────────────`
L'analisi ha rivelato come i prompt lunghi diluiscano l'attenzione dei LLM, un principio chiave nel design di sistemi multi-agent. La separazione delle responsabilità non è solo una best practice software ma è essenziale per l'efficacia degli agent AI. L'uso di template dinamici invece di esempi statici permette maggiore flessibilità mantenendo la consistenza.
`─────────────────────────────────────────────────`

Questa ristrutturazione trasformerà il deep planning agent da un sistema complesso e monolitico in un orchestratore multi-agent focalizzato ed efficiente che segue le best practice di LangGraph mantenendo tutte le funzionalità attuali.