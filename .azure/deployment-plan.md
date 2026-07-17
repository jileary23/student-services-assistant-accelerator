# Student Services Assistant Accelerator - Deployment Plan

> **Status:** Approved

Generated: 2026-07-17

## 1. Project Overview

**Goal:** Create a reusable, deployment-ready accelerator that shows higher-education customers how to build a student services assistant with Microsoft Foundry, Azure AI Search, and supporting Azure services.

**Path:** New Project

## 2. Requirements

| Attribute | Value |
| --- | --- |
| Classification | POC |
| Scale | Small, fewer than 1,000 initial users |
| Budget | Cost-optimized |
| Compliance | FERPA-aware design; no authoritative admissions/aid decisions; approved content only; human handoff for sensitive or low-confidence requests |
| Subscription | Deferred until live deployment |
| Location | Configurable; must be confirmed against model availability and organizational policy before deployment |
| Network profile | Workshop public endpoints with managed identity/RBAC; private networking documented as the production path |

## 3. Components

| Component | Type | Technology | Planned path |
| --- | --- | --- | --- |
| Student Services web app | Frontend/API | Python, FastAPI, HTML/CSS/JavaScript | `src/api` |
| Agent behavior | Agent | Microsoft Agent Framework, Microsoft Foundry | `src/api/app/agent.py` |
| Search ingestion | Administration script | Python, Azure AI Search SDK | `scripts/ingest.py` |
| Website onboarding | Review-first administration script | Python standard library | `scripts/customize.py`, `scripts/website_source.py` |
| Approved content samples | Knowledge base | Markdown | `data/knowledge` |
| Infrastructure | IaC | Bicep, Azure Developer CLI | `infra`, `azure.yaml` |
| Evaluation | Quality | Pytest, Foundry evaluation-ready JSONL | `tests`, `evals` |

## 4. Recipe Selection

**Selected:** Azure Developer CLI (`azd`) with Bicep

**Rationale:** `azd` keeps application, model deployment, infrastructure, environment configuration, validation, and teardown in one repeatable customer workflow. Bicep provides reviewable Azure-native infrastructure and managed-identity role assignments.

## 5. Architecture

**Stack:** Containers

The POC uses one FastAPI container for the web UI and API. This is the smallest topology that supports local execution, scale-to-zero hosting, health checks, and a clean path to customer-owned integration adapters.

### Service Mapping

| Component | Azure service | Initial SKU/profile |
| --- | --- | --- |
| Web/API container | Azure Container Apps | Consumption, scale to zero |
| Container image | Azure Container Registry | Basic |
| Agent/model runtime | Microsoft Foundry project and model deployment | Configurable deployment; low-cost model default |
| Grounding index | Azure AI Search | Basic by default; Free supported for workshops where available |
| Telemetry | Application Insights and Log Analytics | Consumption-based |
| Identity | User-assigned managed identity | Passwordless service access |

### Request Flow

1. The student submits a question in the web chat.
2. The API classifies obvious high-risk requests and routes them to staff without model autonomy.
3. Azure AI Search performs hybrid retrieval over institution-approved content.
4. The Foundry-hosted model answers only from retrieved evidence and emits citations.
5. The API returns the answer, citations, confidence state, and optional escalation details.
6. Application Insights records privacy-conscious operational telemetry without message bodies by default.

### Safety Boundaries

- No final admissions, financial-aid, disciplinary, or policy interpretation decisions.
- No SIS/CRM write operation in the baseline; customer adapters require explicit authorization, confirmation, and audit design.
- Low-confidence, missing-evidence, account-specific, and sensitive requests offer human escalation.
- Retrieval is limited to approved indexed content and citations are visible to users.
- Managed identity replaces service keys in Azure; local development uses `DefaultAzureCredential`.

## 6. Provisioning Readiness

Live deployment is intentionally deferred, so subscription policy, regional model capacity, and quota cannot be truthfully queried yet. The accelerator will be generated with configurable parameters and no deployment will run in this phase.

### Planned Resource Inventory

| Resource type | Number | Deployment-time validation |
| --- | ---: | --- |
| `Microsoft.App/managedEnvironments` | 1 | Confirm Container Apps environment availability and policy |
| `Microsoft.App/containerApps` | 1 | Confirm environment workload profile limits |
| `Microsoft.ContainerRegistry/registries` | 1 | Confirm Basic SKU allowed |
| `Microsoft.CognitiveServices/accounts` | 1 | Confirm Foundry availability, model quota, and responsible AI policy |
| `Microsoft.Search/searchServices` | 1 | Confirm Search SKU availability and semantic ranker choice |
| `Microsoft.OperationalInsights/workspaces` | 1 | Confirm retention and data residency policy |
| `Microsoft.Insights/components` | 1 | Confirm workspace-based Application Insights policy |
| `Microsoft.ManagedIdentity/userAssignedIdentities` | 1 | Confirm identity and role-assignment permissions |

**Status:** Not applicable until a live deployment is requested. Before deployment, confirm subscription/location, inspect Azure Policy, invoke the Azure quota workflow one resource type at a time, and record evidence here.

## 7. Execution Checklist

### Planning

- [x] Analyze empty workspace
- [x] Gather classification, scale, budget, compliance, and networking choices
- [x] Select `azd` and Bicep recipe
- [x] Plan architecture and resource inventory
- [x] Obtain user approval
- [ ] Confirm subscription, location, policies, and quotas before live deployment

### Implementation

- [x] Scaffold Python application and customer-facing web chat
- [x] Implement Search retrieval, grounded response generation, citations, and escalation
- [x] Add sample content, website onboarding, and ingestion utilities
- [x] Add Bicep, `azure.yaml`, managed identity, RBAC, and observability
- [x] Add tests, evaluation assets, and implementation guidance
- [x] Run local and infrastructure validation
- [x] Set status to `Ready for Validation`

### Deployment

- [ ] Invoke `azure-validate` after Azure context is confirmed
- [ ] Record validation proof
- [ ] Obtain explicit deployment approval
- [ ] Invoke `azure-deploy`

## 8. Validation Proof

Preparation validation results will be recorded here. Azure preflight and deployment validation remain blocked until subscription and location are confirmed.

| Check | Result | Timestamp |
| --- | --- | --- |
| Deployment plan Markdown diagnostics | Pass | 2026-07-17 |
| Pytest, Ruff, mypy, and Bicep compile | Pass | 2026-07-17 |

## 9. Files To Generate

| File or path | Purpose | Status |
| --- | --- | --- |
| `.azure/deployment-plan.md` | Approved source of truth | Complete |
| `src/api` | FastAPI application and web UI | Complete |
| `scripts` | Website onboarding and knowledge indexing | Complete |
| `data/knowledge` | Sample approved content | Complete |
| `tests` and `evals` | Automated checks and quality baseline | Complete |
| `infra` and `azure.yaml` | Deployment configuration | Complete |
| `README.md` | Customer implementation guide | Complete |

## 10. Next Steps

1. Publish the locally validated accelerator.
2. Confirm Azure context and run Azure validation only when live deployment is requested.
