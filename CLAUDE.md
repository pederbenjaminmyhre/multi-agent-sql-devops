# Multi-Agent Inner Loop DevOps for SQL Server

## Project Overview

Autonomous multi-agent T-SQL review pipeline deployed to Azure. Agents lint, performance-analyze, document, and validate SQL scripts at the PR level using LangGraph for state-machine orchestration, exposed via FastAPI, and triggered by GitHub Actions.

---

## Directory Structure

```
.
├── CLAUDE.md
├── README.md
├── Polished Requirements/
│   └── requirements.html
├── Rough Requirements/
│   ├── Technical Requirements.txt
│   ├── Strategic Marketing.txt
│   └── deployment and hosting strategy.txt
│
├── src/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Settings via pydantic-settings (env vars, Key Vault)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── linter.py                # Agent A — T-SQL anti-pattern scanner
│   │   ├── performance.py           # Agent B — Index/parameter-sniffing analyzer
│   │   ├── doc_genie.py             # Agent C — Markdown & Extended Properties generator
│   │   ├── skeptic.py               # Agent D — Breaking-change validator
│   │   └── prompts/
│   │       ├── linter_system.md     # System prompt for Agent A
│   │       ├── performance_system.md
│   │       ├── doc_genie_system.md
│   │       └── skeptic_system.md
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                 # TypedDict defining the shared graph state
│   │   ├── nodes.py                 # Node functions (one per agent + router logic)
│   │   ├── edges.py                 # Conditional edge functions (critique-revise routing)
│   │   └── builder.py              # Assembles the StateGraph and compiles it
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── schema_checker.py        # Validates SQL against Schema.json
│   │   ├── sql_formatter.py         # Normalizes T-SQL formatting
│   │   └── changelog_writer.py      # Appends entries to ChangeLog.md
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── review_request.py        # Pydantic model for POST /review body
│   │   ├── review_report.py         # Pydantic model for the JSON response
│   │   └── agent_finding.py         # Individual finding schema (severity, message, suggestion)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cosmos_client.py         # Cosmos DB state persistence
│   │   └── keyvault_client.py       # Azure Key Vault secret retrieval
│   │
│   └── telemetry/
│       ├── __init__.py
│       └── tracing.py               # Application Insights setup + custom span helpers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures (sample SQL, mock schema)
│   ├── test_linter.py
│   ├── test_performance.py
│   ├── test_doc_genie.py
│   ├── test_skeptic.py
│   ├── test_graph_flow.py           # End-to-end graph execution tests
│   ├── test_api.py                  # FastAPI endpoint tests
│   └── fixtures/
│       ├── bad_query.sql            # Intentionally flawed SQL for testing
│       ├── good_query.sql           # Clean SQL that should pass all agents
│       └── schema.json              # Sample schema dictionary for tests
│
├── schema/
│   └── Schema.json                  # Production schema dictionary (tables, columns, indexes)
│
├── .github/
│   └── workflows/
│       └── sql-review.yml           # GitHub Actions workflow — triggers on PR with .sql files
│
├── infra/
│   ├── main.bicep                   # Azure Bicep — all resources (ACA, Cosmos, KV, ACR, AppInsights)
│   ├── parameters.json              # Environment-specific parameter values
│   └── deploy.sh                    # One-command deployment script (az cli)
│
├── Dockerfile
├── .dockerignore
├── pyproject.toml                   # Project metadata, dependencies, tool config
├── .env.example                     # Template for local dev environment variables
└── .gitignore
```

---

## Tech Stack & Versions

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Runtime |
| langgraph | latest | State-machine agent orchestration |
| langchain-core | latest | Base abstractions for tools/agents |
| langchain-openai or langchain-anthropic | latest | LLM provider integration |
| fastapi | 0.115+ | HTTP API framework |
| uvicorn | latest | ASGI server |
| pydantic | 2.x | Request/response validation |
| pydantic-settings | latest | Config from env vars |
| azure-cosmos | latest | Cosmos DB SDK |
| azure-keyvault-secrets | latest | Key Vault SDK |
| azure-identity | latest | Managed Identity / DefaultAzureCredential |
| opentelemetry-sdk | latest | Telemetry base |
| azure-monitor-opentelemetry | latest | Application Insights exporter |
| pytest | 8+ | Testing |
| pytest-asyncio | latest | Async test support |
| httpx | latest | Async test client for FastAPI |
| sqlparse | latest | T-SQL parsing and formatting |

---

## Implementation Plan

### Phase 1: Foundation — Local Agent Pipeline

#### Step 1.1: Project Scaffolding
- Initialize `pyproject.toml` with all dependencies
- Create the full directory structure shown above
- Create `.env.example` with placeholder values:
  ```
  LLM_PROVIDER=anthropic          # or "openai"
  LLM_API_KEY=sk-...
  LLM_MODEL=claude-sonnet-4-6
  COSMOS_ENDPOINT=               # blank for local dev (uses in-memory state)
  COSMOS_KEY=
  KEYVAULT_URL=
  APPINSIGHTS_CONNECTION_STRING=
  MAX_CRITIQUE_LOOPS=3
  ```
- Create `src/config.py` using pydantic-settings to load these values

#### Step 1.2: Define the Graph State
File: `src/graph/state.py`
```python
class ReviewState(TypedDict):
    sql_input: str                    # Original SQL from the developer
    schema_context: dict              # Parsed Schema.json
    linter_findings: list[Finding]    # Agent A output
    performance_findings: list[Finding]  # Agent B output
    proposed_fixes: str               # Cumulative rewritten SQL
    documentation: str                # Agent C output (markdown)
    skeptic_verdict: str              # "approved" | "rejected"
    skeptic_reasoning: str            # Why rejected (if applicable)
    iteration: int                    # Current critique-revise loop count
    max_iterations: int               # Configurable cap (default 3)
    changelog_entries: list[str]      # Human-readable change descriptions
    final_report: dict                # Structured JSON report for PR comment
```

#### Step 1.3: Build Agent Modules
Each agent in `src/agents/` follows this pattern:
1. Load its system prompt from `src/agents/prompts/`
2. Accept the current `ReviewState`
3. Invoke the LLM with relevant tools bound
4. Return state updates (never the full state)

**Agent A — Linter** (`src/agents/linter.py`):
- Tools: `sql_formatter`
- Scans for: `SELECT *`, missing `NOLOCK`, implicit conversions, deprecated syntax (`SET ROWCOUNT`, `@@IDENTITY`), missing `SET NOCOUNT ON` in procedures
- Output: List of `Finding` objects with severity (error/warning/info), line reference, message, and suggested fix
- Rewrites the SQL with fixes applied

**Agent B — Performance Critic** (`src/agents/performance.py`):
- Tools: `schema_checker`
- Analyzes: JOINs on unindexed columns, missing covering indexes, `LIKE '%...'` leading-wildcard scans, parameter sniffing risks on skewed columns, missing statistics
- Output: List of `Finding` objects + `CREATE INDEX` suggestions as T-SQL

**Agent C — Doc-Genie** (`src/agents/doc_genie.py`):
- No external tools — pure LLM generation
- Detects: `CREATE TABLE`, `CREATE PROCEDURE`, `ALTER TABLE ADD` statements
- Output: Markdown documentation block + `sp_addextendedproperty` T-SQL statements
- Only runs when new objects are detected (skip if pure DML/query changes)

**Agent D — Skeptic** (`src/agents/skeptic.py`):
- Tools: `schema_checker` (to verify suggested indexes/changes are valid)
- Reviews: All findings and proposed fixes from Agents A & B
- Checks: Would any fix break existing FK constraints? Does a suggested index already exist? Does a rewrite change query semantics?
- Output: Verdict (`"approved"` or `"rejected"`) + reasoning
- If rejected: sets `skeptic_verdict = "rejected"` which triggers the conditional edge back to the Linter

#### Step 1.4: Build Agent Tools
**Schema Checker** (`src/tools/schema_checker.py`):
- Loads `Schema.json` (tables, columns with types, existing indexes, FK relationships)
- Functions: `get_table_columns(table_name)`, `get_indexes(table_name)`, `check_column_exists(table, column)`, `get_foreign_keys(table_name)`
- Registered as LangChain `@tool` decorated functions

**SQL Formatter** (`src/tools/sql_formatter.py`):
- Uses `sqlparse` library for parsing
- Normalizes: uppercase keywords, consistent indentation (4 spaces), trailing semicolons, aligned `ON` clauses in JOINs
- Registered as a `@tool`

**Changelog Writer** (`src/tools/changelog_writer.py`):
- Accepts a list of change descriptions
- Formats them as timestamped markdown entries
- Not an LLM tool — called at the end of the pipeline by the final node

#### Step 1.5: Assemble the State Graph
File: `src/graph/builder.py`

```
Graph structure:

    START
      │
      ▼
   [linter_node]        ◄──────────┐
      │                             │
      ▼                             │
   [performance_node]               │
      │                             │
      ▼                             │
   [doc_genie_node]                 │
      │                             │
      ▼                             │
   [skeptic_node]                   │
      │                             │
      ▼                             │
   {route_after_skeptic}  ──rejected┘
      │ approved                    (if iteration < max)
      ▼
   [report_node]
      │
      ▼
     END
```

- `src/graph/nodes.py`: One function per node. Each takes `ReviewState`, calls the corresponding agent, returns partial state updates.
- `src/graph/edges.py`: `route_after_skeptic(state)` — returns `"linter_node"` if rejected and under iteration limit, otherwise `"report_node"`.
- `src/graph/builder.py`: Uses `StateGraph(ReviewState)` to wire nodes and conditional edges, then calls `.compile()`.

#### Step 1.6: Test Fixtures
- `tests/fixtures/bad_query.sql`: Contains `SELECT *`, JOIN on unindexed column, missing `NOCOUNT`, uses `@@IDENTITY`
- `tests/fixtures/good_query.sql`: Clean query that should pass all agents with zero findings
- `tests/fixtures/schema.json`: 3-4 tables with columns, types, indexes, and FK relationships

#### Step 1.7: Unit & Integration Tests
- `test_linter.py`: Feed bad SQL, assert findings include expected anti-patterns
- `test_performance.py`: Feed a JOIN on unindexed column, assert index suggestion
- `test_doc_genie.py`: Feed `CREATE TABLE`, assert markdown output contains table name and columns
- `test_skeptic.py`: Feed a fix that breaks an FK, assert rejection
- `test_graph_flow.py`: Run the full compiled graph end-to-end with `bad_query.sql`, assert final report is generated and SQL is cleaned

---

### Phase 2: API & Container

#### Step 2.1: FastAPI Application
File: `src/main.py`

Endpoints:
- `POST /review` — accepts `ReviewRequest` body:
  ```json
  {
    "sql": "SELECT * FROM Orders o JOIN Customers c ON o.CustID = c.ID",
    "schema_context": { ... },       // optional override; defaults to Schema.json
    "max_iterations": 3              // optional
  }
  ```
  Returns `ReviewReport`:
  ```json
  {
    "status": "approved",
    "iterations": 1,
    "findings": [...],
    "cleaned_sql": "...",
    "documentation": "...",
    "changelog": [...]
  }
  ```
- `GET /health` — returns `{"status": "healthy"}` for ACA liveness probes

Middleware:
- CORS (allow GitHub Actions callback origins)
- Request ID injection for trace correlation
- Error handler returning structured JSON on any unhandled exception

#### Step 2.2: Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ src/
COPY schema/ schema/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- Multi-stage build if image size becomes a concern
- `.dockerignore` excludes: tests/, Rough Requirements/, Polished Requirements/, .git/, .env, __pycache__/

#### Step 2.3: Local Docker Testing
- `docker build -t sql-review-agent .`
- `docker run -p 8000:8000 --env-file .env sql-review-agent`
- `curl -X POST http://localhost:8000/review -H "Content-Type: application/json" -d @tests/fixtures/bad_query_request.json`

---

### Phase 3: Azure Deployment

#### Step 3.1: Azure Bicep Infrastructure
File: `infra/main.bicep`

Resources to provision:
1. **Resource Group**: `rg-sql-devops-portfolio`
2. **Azure Container Registry** (Basic): `acrSqlDevops` — hosts the Docker image
3. **Azure Container Apps Environment** (Consumption): `cae-sql-devops` — serverless compute
4. **Azure Container App**: `ca-sql-review` — runs the FastAPI container
   - Min replicas: 0 (scale to zero)
   - Max replicas: 2
   - Ingress: external, port 8000, HTTPS only
   - Managed Identity: system-assigned
5. **Azure Cosmos DB** (Serverless, NoSQL API): `cosmos-sql-devops`
   - Database: `sql-review-db`
   - Container: `review-state` (partition key: `/session_id`)
6. **Azure Key Vault** (Standard): `kv-sql-devops`
   - Secrets: `llm-api-key`, `cosmos-connection-string`
   - Access policy: Container App managed identity gets `Secret:Get,List`
7. **Azure Application Insights**: `appi-sql-devops`
   - Connected to a Log Analytics workspace
   - Connection string injected into Container App as env var

#### Step 3.2: Deploy Script
File: `infra/deploy.sh`
```bash
#!/bin/bash
set -euo pipefail

RESOURCE_GROUP="rg-sql-devops-portfolio"
LOCATION="eastus"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy Bicep
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json

# Build and push container
ACR_NAME=$(az acr list -g $RESOURCE_GROUP --query "[0].name" -o tsv)
az acr build --registry $ACR_NAME --image sql-review-agent:latest .

# Update container app with new image
az containerapp update \
  --name ca-sql-review \
  --resource-group $RESOURCE_GROUP \
  --image "${ACR_NAME}.azurecr.io/sql-review-agent:latest"
```

#### Step 3.3: Service Principal for GitHub Actions
```bash
az ad sp create-for-rbac \
  --name "sp-sql-devops-github" \
  --role contributor \
  --scopes /subscriptions/{sub-id}/resourceGroups/rg-sql-devops-portfolio \
  --sdk-auth
```
Output JSON goes into GitHub repo secret `AZURE_CREDENTIALS`.

---

### Phase 4: CI/CD Integration

#### Step 4.1: GitHub Actions Workflow
File: `.github/workflows/sql-review.yml`

```yaml
name: SQL Review Agent
on:
  pull_request:
    paths: ['**/*.sql']

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Collect changed SQL files
        id: sql
        run: |
          FILES=$(git diff --name-only ${{ github.event.pull_request.base.sha }} \
                  ${{ github.sha }} -- '*.sql')
          echo "files=$FILES" >> $GITHUB_OUTPUT

      - name: Call Review API
        if: steps.sql.outputs.files != ''
        id: review
        run: |
          for f in ${{ steps.sql.outputs.files }}; do
            SQL_CONTENT=$(cat "$f")
            RESPONSE=$(curl -s -X POST "${{ secrets.REVIEW_API_URL }}/review" \
              -H "Content-Type: application/json" \
              -d "{\"sql\": $(echo "$SQL_CONTENT" | jq -Rs .)}")
            echo "$RESPONSE" > "review-$(basename $f).json"
          done

      - name: Post PR Comment
        if: steps.sql.outputs.files != ''
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const glob = require('glob');
            const files = glob.sync('review-*.json');
            let body = '## SQL Review Agent Report\n\n';
            for (const f of files) {
              const report = JSON.parse(fs.readFileSync(f, 'utf8'));
              body += `### ${f.replace('review-','').replace('.json','')}\n`;
              body += `**Status:** ${report.status}\n`;
              body += `**Iterations:** ${report.iterations}\n\n`;
              for (const finding of report.findings) {
                body += `- **[${finding.severity}]** ${finding.message}\n`;
              }
              body += '\n';
            }
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body
            });

      - name: Fail on critical findings
        run: |
          for f in review-*.json; do
            if jq -e '.findings[] | select(.severity == "error")' "$f" > /dev/null 2>&1; then
              echo "::error::Critical SQL issues found — merge blocked"
              exit 1
            fi
          done
```

---

### Phase 5: Observability & Telemetry

#### Step 5.1: OpenTelemetry Setup
File: `src/telemetry/tracing.py`
- Initialize `AzureMonitorTraceExporter` with the Application Insights connection string
- Create a `TracerProvider` and register it globally
- Export a helper: `trace_agent(agent_name, input_sql, output)` that creates a span per agent invocation with:
  - `agent.name` attribute
  - `agent.input` (truncated to 1000 chars)
  - `agent.findings_count`
  - `agent.verdict` (for Skeptic)

#### Step 5.2: Instrument the Graph
In each node function (`src/graph/nodes.py`), wrap the agent call in a `trace_agent` span. This produces a distributed trace per review request showing:
```
POST /review
  └── linter_node (Agent A)
  └── performance_node (Agent B)
  └── doc_genie_node (Agent C)
  └── skeptic_node (Agent D)
  └── [linter_node retry] (if rejected)
  └── report_node
```

---

## Coding Conventions

- **Python style**: Follow PEP 8. Use type hints on all function signatures.
- **Imports**: stdlib → third-party → local, separated by blank lines. Use absolute imports (`from src.agents.linter import ...`).
- **Agent prompts**: Store in markdown files under `src/agents/prompts/`, not as inline strings.
- **State updates**: Agent node functions return only the keys they modify, never the full `ReviewState`.
- **Error handling**: Validate at system boundaries (API input, external service calls). Internal functions trust typed inputs.
- **Testing**: Every agent has a unit test. The full graph has an integration test. API endpoints have endpoint tests.
- **No secrets in code**: All sensitive values come from environment variables or Key Vault. `.env` is gitignored.
- **Pydantic models**: Use for all API request/response shapes and for `Finding` objects shared between agents.

---

## Schema.json Format

```json
{
  "tables": {
    "Orders": {
      "columns": {
        "OrderID": { "type": "INT", "nullable": false, "is_pk": true },
        "CustomerID": { "type": "INT", "nullable": false },
        "OrderDate": { "type": "DATETIME2", "nullable": false },
        "TotalAmount": { "type": "DECIMAL(18,2)", "nullable": false }
      },
      "indexes": [
        { "name": "PK_Orders", "columns": ["OrderID"], "is_unique": true },
        { "name": "IX_Orders_CustomerID", "columns": ["CustomerID"], "is_unique": false }
      ],
      "foreign_keys": [
        { "column": "CustomerID", "references": { "table": "Customers", "column": "CustomerID" } }
      ]
    }
  }
}
```

---

## Key Design Decisions

1. **LangGraph over Semantic Kernel**: Python ecosystem is primary. LangGraph gives explicit state-machine control with conditional edges — ideal for the critique-revise loop.
2. **FastAPI over Flask**: Native async, Pydantic integration, auto-generated OpenAPI docs.
3. **Cosmos DB Serverless**: Pay-per-request pricing avoids baseline costs for a portfolio project. Partition on `session_id` for multi-tenant readiness.
4. **System prompts in .md files**: Keeps prompts version-controlled, diffable, and editable without touching Python code.
5. **Max iteration cap on critique loop**: Prevents infinite loops. Default 3. Configurable via API request or env var.
6. **Findings as structured objects**: Every agent returns `Finding(severity, message, line_ref, suggestion)` — enables consistent reporting, PR comments, and merge-blocking logic.

---

## Build & Run Commands

```bash
# Local development
pip install -e ".[dev]"             # Install with dev dependencies
cp .env.example .env                # Configure local env vars
uvicorn src.main:app --reload       # Start dev server on :8000

# Run tests
pytest tests/ -v

# Docker
docker build -t sql-review-agent .
docker run -p 8000:8000 --env-file .env sql-review-agent

# Azure deployment
chmod +x infra/deploy.sh
./infra/deploy.sh
```

---

## Definition of Done (Per Phase)

| Phase | Done When |
|---|---|
| Phase 1 | `pytest tests/test_graph_flow.py` passes — bad SQL goes in, cleaned SQL + report comes out |
| Phase 2 | `curl POST /review` returns valid JSON report from Docker container |
| Phase 3 | Container App responds to `/health` from public Azure URL |
| Phase 4 | Pushing a `.sql` file to a PR triggers an automated review comment |
| Phase 5 | Agent traces visible in Application Insights for a live review |
