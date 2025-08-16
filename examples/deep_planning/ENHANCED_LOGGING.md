# Enhanced Context Management Logging

Il sistema di context management è stato potenziato con logging dettagliato che mostra in tempo reale le operazioni di pulizia, compattazione e gestione del contesto per ogni chiamata MCP tool.

## 🆕 Nuove Funzionalità di Logging

### 📊 Context Length Tracking
Ad ogni chiamata di tool MCP, il sistema ora mostra:
- **Lunghezza del contesto** prima e dopo l'esecuzione
- **Utilizzo percentuale** della finestra di contesto 
- **Percentuale di rumore MCP** nel contesto corrente
- **Tempo di esecuzione** del tool

### 🧹 Cleaning Operations
Logging dettagliato delle operazioni di pulizia:
- **Strategia applicata** (ProjectListCleaner, CodeSnippetCleaner, etc.)
- **Riduzione ottenuta** (es: 1,124 → 303 chars, 73.0% reduction)
- **Status dell'operazione** (completed, skipped, failed)
- **Campi preservati/rimossi** durante la pulizia

### 🔄 Compaction Triggers
Monitoraggio automatico dei trigger di compattazione:
- **Soglie di attivazione** (utilization threshold, MCP noise threshold)
- **Tipo di trigger** (automatic, threshold, mcp_noise)
- **Operazioni di compattazione** eseguite automaticamente
- **Statistiche di riduzione** totale

## 📝 Esempi di Log

### Tool Call con Cleaning
```
2025-08-16 21:06:46,811 - mcp_context_tracker - INFO - 🔧 MCP Tool Call: General_list_projects
2025-08-16 21:06:46,811 - mcp_context_tracker - INFO - 📊 Pre-execution Context: 13 tokens (0.0% utilization, 0.0% MCP noise)
2025-08-16 21:06:46,811 - context_manager - INFO - 🔍 Searching cleaning strategy for General_list_projects (1,124 chars)
2025-08-16 21:06:46,811 - context_manager - INFO - ✅ Found strategy: ProjectListCleaner for General_list_projects
2025-08-16 21:06:46,811 - context_manager - INFO - 🧹 ProjectListCleaner cleaned General_list_projects: 1,124 → 303 chars (73.0% reduction)
2025-08-16 21:06:46,811 - mcp_context_tracker - INFO - 🧹 Cleaning applied to General_list_projects: 1,124 → 303 chars (73.0% reduction) using ProjectListCleaner
2025-08-16 21:06:46,811 - mcp_context_tracker - INFO - 📈 Post-execution Context: 13 tokens (0.0% utilization) - Execution time: 0.001s
```

### Compaction Trigger
```
2025-08-16 21:15:30,123 - mcp_context_tracker - WARNING - 🔄 COMPACTION TRIGGERED: threshold (Utilization: 87.3%, MCP Noise: 45.2%)
2025-08-16 21:15:30,125 - mcp_context_tracker - INFO - 🔄 Starting context compaction (threshold)...
2025-08-16 21:15:30,135 - mcp_context_tracker - INFO - ✅ Context compaction completed: 65.4% total reduction (8 operations)
```

### Near Limit Warning
```
2025-08-16 21:20:15,456 - mcp_context_tracker - INFO - ⚠️ Context near limit: 78.9% utilization
```

## 🚀 Come Attivare il Logging Dettagliato

### Metodo 1: Setup Automatico
```python
from configure_detailed_logging import setup_detailed_logging
from mcp_wrapper import wrap_existing_mcp_tools

# Abilita logging dettagliato
setup_detailed_logging()

# Wrappa i tuoi tool MCP
wrapped_tools, wrapper = wrap_existing_mcp_tools(your_mcp_tools)

# Usa i tool wrapped - i log dettagliati appariranno automaticamente
result = wrapped_tools[0]()
```

### Metodo 2: Configurazione Manuale
```python
import logging

# Configura logging per context management
logging.basicConfig(level=logging.INFO)
context_logger = logging.getLogger("mcp_context_tracker")
context_logger.setLevel(logging.INFO)

# Crea wrapper con logging
from mcp_wrapper import create_mcp_wrapper
wrapper = create_mcp_wrapper({
    "cleaning_enabled": True,
    "max_context_window": 200000,
    "trigger_threshold": 0.85
})
```

## 📊 Monitoraggio delle Statistiche

### Statistiche in Tempo Reale
```python
# Ottieni statistiche del wrapper
stats = wrapper.get_statistics()
print(f"Total calls: {stats['total_calls']}")
print(f"Cleaned calls: {stats['cleaned_calls']}")
print(f"Average reduction: {stats['average_reduction_percentage']:.1f}%")

# Ottieni sommario del context manager
summary = wrapper.context_manager.get_context_summary()
print(f"Session ID: {summary['session_id']}")
print(f"Current utilization: {summary['current_utilization']:.1f}%")
print(f"Current MCP noise: {summary['current_mcp_noise']:.1f}%")
```

### Chiamate Recenti
```python
# Visualizza le ultime chiamate con dettagli
recent_calls = wrapper.get_recent_calls(5)
for call in recent_calls:
    print(f"Tool: {call['tool_name']}")
    print(f"Size: {call['original_size']} → {call['cleaned_size']} chars")
    print(f"Reduction: {call['cleaning_info']['reduction_percentage']:.1f}%")
    print(f"Time: {call['execution_time']:.3f}s")
```

## 🎯 Configurazioni Consigliate

### Per Sviluppo (Verbose)
```python
config = {
    "cleaning_enabled": True,
    "max_context_window": 50000,    # Più piccolo per vedere più trigger
    "trigger_threshold": 0.60,      # Soglia più bassa
    "mcp_noise_threshold": 0.40,    # Triggera pulizia prima
    "auto_compaction": True
}
```

### Per Produzione (Ottimizzato)
```python
config = {
    "cleaning_enabled": True,
    "max_context_window": 200000,   # Finestra piena
    "trigger_threshold": 0.85,      # Soglia standard
    "mcp_noise_threshold": 0.60,    # Triggera solo quando necessario
    "auto_compaction": True
}
```

## 📋 Log Files

I log vengono scritti sia su console che su file:
- **Console**: Livello INFO per sviluppo
- **File**: `context_detailed.log` per analisi successiva
- **Debug log**: Viene mantenuto il file debug.log esistente

## 🔧 Personalizzazione

### Livelli di Logging Personalizzati
```python
import logging

# Personalizza i livelli per diversi componenti
loggers_config = {
    'context_manager': logging.INFO,        # Context analysis
    'mcp_context_tracker': logging.INFO,   # Tool calls e cleaning
    'mcp_cleaners': logging.DEBUG,         # Dettagli strategie
    'mcp.client': logging.WARNING,         # Riduci noise MCP
    'litellm': logging.WARNING             # Riduci noise LLM
}

for logger_name, level in loggers_config.items():
    logging.getLogger(logger_name).setLevel(level)
```

### Filtri Personalizzati
```python
# Filtra solo specifici tool
def tool_filter(record):
    return 'General_list_projects' in record.getMessage()

logging.getLogger('mcp_context_tracker').addFilter(tool_filter)
```

## ✅ Benefici

1. **Visibilità Completa**: Vedi esattamente cosa succede ad ogni chiamata tool
2. **Performance Monitoring**: Traccia i tempi di esecuzione e le riduzioni
3. **Debug Facilitato**: Identifica rapidamente problemi di context management
4. **Ottimizzazione**: Monitora l'efficacia delle strategie di pulizia
5. **Alerting**: Ricevi avvisi quando il contesto si avvicina ai limiti

Il sistema è completamente trasparente e non influisce sulle performance - i log sono asincroni e ottimizzati.