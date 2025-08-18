# MCP Tools Documentation

Questo documento elenca tutti gli strumenti MCP (Model Context Protocol) esposti dalle API dell'applicazione.

## Endpoint MCP Principali

### `/mcp` - Endpoint Principale
Include tre categorie di strumenti: **General**, **Studio**, e **Code**.

### `/mcp/company` - Endpoint Aziendale  
Include due categorie di strumenti: **General** e **Studio** con funzionalità specifiche per aziende.

---

## 📋 General Tools

### Endpoint: `/mcp` e `/mcp/company`

#### 🗂️ **Projects**
- **`list_projects`**
  - **Descrizione**: Elenca tutti i progetti accessibili all'utente/azienda
  - **Parametri**: Nessuno
  - **Ritorna**: Lista di progetti con `project_id` e nome
  - **Caso d'uso**: Prima operazione per ottenere ID progetto per altri tools

#### 📎 **Attachments** *(Solo `/mcp`)*
- **`list_user_attachments_by_project`**
  - **Descrizione**: Elenca tutti gli allegati dell'utente in un progetto specifico
  - **Parametri**: `project_id`, `architect` (opzionale)
  - **Ritorna**: Lista di allegati con metadati

- **`get_document_content`**
  - **Descrizione**: Ottiene il contenuto di un documento per ID allegato con limitazione range righe
  - **Parametri**: `document_id`, `start_line` (default: 0), `end_line` (default: 200), `architect` (opzionale)
  - **Ritorna**: Contenuto del documento con metadati

#### 🔍 **RAG (Retrieval Augmented Generation)** *(Solo `/mcp`)*
- **`rag_retrieve_documents`**
  - **Descrizione**: Recupera documenti dal sistema RAG tramite query
  - **Parametri**: `query`, `projectId`, `k` (default: 20), `score_threshold` (default: 0.5)
  - **Ritorna**: Documenti rilevanti con punteggi di similarità
  - **Limiti**: k (7-30), score_threshold (0.4-0.7)

- **`rag_retrieve_specific_documents`**
  - **Descrizione**: Recupera documenti specifici dal RAG con parametri di focus
  - **Parametri**: `query`, `projectId`, `k`, `score_threshold`, `focus_params` (opzionale)
  - **Ritorna**: Documenti filtrati con criteri specifici
  - **Caratteristiche**: Esclude automaticamente certi tipi di documenti

---

## 🎯 Studio Tools

### Endpoint: `/mcp` e `/mcp/company`

#### 🎯 **Needs (Bisogni)**
- **`list_needs_by_project`**
  - **Descrizione**: Elenca tutti i bisogni associati a un progetto specifico
  - **Parametri**: `project_id`
  - **Ritorna**: Lista di bisogni con dettagli (need_id, titolo, descrizione)

- **`get_need`**
  - **Descrizione**: Ottiene informazioni dettagliate per un bisogno specifico
  - **Parametri**: `need_id`
  - **Ritorna**: Dettagli completi del bisogno

#### 📖 **User Stories**
- **`list_user_stories_by_project`**
  - **Descrizione**: Elenca tutte le user story per un progetto specifico
  - **Parametri**: `project_id`
  - **Ritorna**: Lista di user story con dettagli

- **`list_user_stories_by_need`**
  - **Descrizione**: Elenca user story collegate a un bisogno specifico
  - **Parametri**: `need_id`
  - **Ritorna**: User story correlate al bisogno

- **`list_user_stories_by_role`**
  - **Descrizione**: Elenca user story associate a un ruolo specifico
  - **Parametri**: `role_id`
  - **Ritorna**: User story per il ruolo specificato

- **`get_user_story`**
  - **Descrizione**: Ottiene informazioni dettagliate per una user story specifica
  - **Parametri**: `user_story_id`
  - **Ritorna**: Dettagli completi della user story

#### ✅ **Tasks (Attività)**
- **`list_tasks_by_project`**
  - **Descrizione**: Elenca tutte le attività per un progetto specifico
  - **Parametri**: `project_id`
  - **Ritorna**: Lista di attività con dettagli

- **`get_task`**
  - **Descrizione**: Ottiene informazioni dettagliate per un'attività specifica
  - **Parametri**: `task_id`
  - **Ritorna**: Dettagli completi dell'attività

#### 📋 **Requirements (Requisiti)**
- **`list_requirements_by_project`**
  - **Descrizione**: Elenca tutti i requisiti per un progetto specifico
  - **Parametri**: `project_id`
  - **Ritorna**: Lista di requisiti con dettagli

- **`get_requirement`**
  - **Descrizione**: Ottiene informazioni dettagliate per un requisito specifico
  - **Parametri**: `requirement_id`
  - **Ritorna**: Dettagli completi del requisito

#### 🧪 **Test Cases**
- **`list_tests_by_userstory`**
  - **Descrizione**: Elenca tutti i test case per una user story specifica
  - **Parametri**: `user_story_id`
  - **Ritorna**: Lista di test case per la user story

- **`list_tests_by_project`**
  - **Descrizione**: Elenca tutti i test case per un progetto specifico
  - **Parametri**: `projectId`
  - **Ritorna**: Lista di test case per il progetto

---

## 💻 Code Tools

### Endpoint: Solo `/mcp`

#### 📁 **Repository Management**
- **`list_repositories`**
  - **Descrizione**: Elenca tutti i repository associati a un progetto specifico
  - **Parametri**: `project_id`
  - **Ritorna**: Lista di repository con dettagli (repository_id, nome, descrizione)

- **`get_directory_structure`**
  - **Descrizione**: Ottiene la struttura completa di directory e file di un repository
  - **Parametri**: `project_id`, `repository_id`
  - **Ritorna**: Struttura gerarchica di cartelle e file

#### 🔍 **Code Search & Analysis**
- **`find_relevant_code_snippets`**
  - **Descrizione**: Trova snippet di codice rilevanti usando ricerca in linguaggio naturale
  - **Parametri**: `natural_language_query`, `project_id`, `repository_id` (opzionale), `top_k` (default: 10)
  - **Ritorna**: Snippet di codice con path, numeri di riga, punteggi di rilevanza
  - **Funzionalità**: Ricerca semantica cross-repository

- **`find_usages`**
  - **Descrizione**: Trova tutti i luoghi dove un'entità di codice specifica è utilizzata
  - **Parametri**: `project_id`, `repository_id`, `entity_id`
  - **Ritorna**: Informazioni sull'entità e tutti i suoi utilizzi
  - **Utilità**: Analisi delle dipendenze e pianificazione refactoring

- **`get_file`**
  - **Descrizione**: Recupera il contenuto completo di un file specifico
  - **Parametri**: `project_id`, `repository_id`, `entity_id` O `file_path` (mutuamente esclusivi)
  - **Ritorna**: Contenuto completo del file con metadati
  - **Nota**: Richiede esattamente uno tra entity_id o file_path

---

## 🔑 Differenze tra Endpoint

### `/mcp` (User-based)
- **Autenticazione**: Basata su utente individuale
- **Accesso**: Richiede `userId` e `company` per tutte le operazioni
- **Funzionalità complete**: Include General, Studio, Code e RAG tools

### `/mcp/company` (Company-based)
- **Autenticazione**: Basata su azienda
- **Accesso**: Richiede solo `company`, userId impostato a `null`
- **Funzionalità limitate**: Include solo General e Studio tools (no Code, no RAG)

---

## 🛡️ Sicurezza e Autenticazione

- **JWT Tokens**: Tutti gli endpoint richiedono autenticazione JWT valida
- **Multi-tenancy**: Isolamento dei dati per azienda garantito
- **Authorization Headers**: Passati attraverso alle API esterne (Code Ingestion Service)
- **Timeout**: Richieste HTTP con timeout configurabile (default: 30s)

---

## 🔗 Servizi Esterni

### Code Ingestion Service
- **Base URL**: Configurabile via `CODE_INGESTION_BASE_URL`
- **Funzioni**: Analisi del codice, ricerca semantica, struttura repository
- **Autenticazione**: Header Authorization passato through

### RAG Service
- **Funzioni**: Ricerca documenti, embeddings, similarità semantica
- **Database**: Weaviate per ricerca vettoriale
- **AI**: Together AI per generazione embeddings

---

## 📝 Note d'Uso

1. **Flusso tipico**: `list_projects` → `list_*_by_project` → `get_*` per dettagli specifici
2. **ID Management**: Tutti gli strumenti ritornano ID che possono essere usati con altri strumenti
3. **Error Handling**: Gestione errors consistente across tutti gli endpoints
4. **Performance**: Parametri configurabili per bilanciare performance e quantità di risultati