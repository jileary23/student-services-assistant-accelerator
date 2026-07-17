# Deploy the Accelerator in Your Azure Subscription

This guide walks through the first deployment of the Student Services Assistant Accelerator. You do not need to create the individual Azure resources in the portal. The repository's Bicep templates and Azure Developer CLI configuration create and connect them for you.

The deployment is a workshop or proof-of-concept starting point. Before serving students, complete your institution's security, privacy, accessibility, legal, content-governance, and production-readiness reviews.

## What You Will Build

Running `azd up` creates one resource group containing:

| Azure service | Purpose |
| --- | --- |
| Microsoft Foundry resource and project | Hosts the chat and embedding model deployments |
| Azure AI Search | Stores and retrieves approved university content |
| Azure Container Apps | Runs the FastAPI service and student web experience |
| Azure Container Registry | Stores the application container image |
| User-assigned managed identity | Lets the app use Azure services without passwords or API keys |
| Application Insights and Log Analytics | Records operational telemetry without message bodies by default |

The application uses `gpt-4.1-mini` and `text-embedding-3-small` by default. Azure availability and quota vary by subscription and region.

## 1. Confirm Your Azure Account and Permissions

You need:

- An active Azure subscription with billing enabled.
- Permission to create resources in that subscription.
- Permission to create Azure role assignments because the deployment grants managed identities access to Foundry, Search, and the container registry.

The simplest workshop setup is the **Owner** role on the target subscription. A more restrictive setup is **Contributor** plus **Role Based Access Control Administrator** on the target subscription. Subscription scope is needed for this first deployment because `azd` creates the resource group. Contributor by itself cannot create role assignments.

In the [Azure portal](https://portal.azure.com):

1. Search for **Subscriptions** and open the subscription you plan to use.
2. Select **Access control (IAM)**.
3. Select **Check access** and confirm your assigned roles.
4. If your organization uses Privileged Identity Management, activate the required role before deploying.

Ask your Azure administrator for help if you cannot create resources or role assignments. See [steps to assign an Azure role](https://learn.microsoft.com/azure/role-based-access-control/role-assignments-steps) for Microsoft guidance.

## 2. Check Region and Model Capacity

Do this before deployment. A region can support Foundry but lack capacity for a particular model in your subscription.

1. Open the [Microsoft Foundry portal](https://ai.azure.com).
2. Select **Operate** > **Quota**.
3. Turn on **Show all**.
4. Find `gpt-4.1-mini` and `text-embedding-3-small`.
5. Choose a region with available capacity for both models.
6. Confirm Azure AI Search and Azure Container Apps are also available in that region using [Azure products by region](https://azure.microsoft.com/explore/global-infrastructure/products-by-region/).

The Bicep defaults request 10 thousand tokens per minute for each model. If capacity is lower, select another region, request quota, or reduce `chatModelCapacity` and `embeddingModelCapacity` in `infra/main.bicep` before deployment. See [Foundry feature availability across regions](https://learn.microsoft.com/azure/foundry/reference/region-support) and [Foundry model quota](https://learn.microsoft.com/azure/foundry/openai/how-to/quota).

## 3. Install the Required Tools

Use PowerShell for the commands in this guide. Install:

- [Git](https://git-scm.com/downloads)
- [Python 3.11 or newer](https://www.python.org/downloads/)
- [Docker Desktop](https://docs.docker.com/desktop/) with the Linux container engine running
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)

On Windows, WinGet can install the Azure command-line tools:

```powershell
winget install --exact --id Microsoft.AzureCLI
winget install Microsoft.Azd
```

Close and reopen PowerShell after installation, then verify everything:

```powershell
git --version
python --version
docker version
az version
azd version
```

`docker version` must show both a client and server. Start Docker Desktop if the server is unavailable.

## 4. Download and Test the Accelerator Locally

Clone the repository and enter its folder:

```powershell
git clone https://github.com/jileary23/student-services-assistant-accelerator.git
Set-Location student-services-assistant-accelerator
```

Create a Python environment and run the automated checks:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Expected result: all tests pass. Local tests run in mock mode and do not create Azure resources.

To try the sample application before deployment:

```powershell
Copy-Item .env.example .env
uvicorn app.main:app --app-dir src/api --reload
```

Open `http://127.0.0.1:8000`. Stop the local server with `Ctrl+C` before continuing.

## 5. Sign In and Select the Subscription

Sign in to both command-line tools:

```powershell
az login
azd auth login
```

List the subscriptions available to your account:

```powershell
az account list --output table
```

Select the subscription by name or ID and verify the result:

```powershell
az account set --subscription "<subscription-name-or-id>"
az account show --output table
```

Make sure the displayed subscription is the one that should receive the resources and charges.

## 6. Create and Configure an `azd` Environment

An `azd` environment keeps one deployment's subscription, region, settings, and generated outputs together. Its local files are stored under `.azure/` and ignored by Git.

Set values for your deployment. Replace the example region only after completing the capacity check in step 2:

```powershell
$environmentName = "student-services-dev"
$location = "eastus2"
$subscriptionId = az account show --query id --output tsv
$principalId = az ad signed-in-user show --query id --output tsv

azd env new $environmentName --subscription $subscriptionId --location $location
azd env set AZURE_PRINCIPAL_ID $principalId
azd env set INSTITUTION_NAME "James Madison University"
azd env set UNIVERSITY_WEBSITE "https://www.jmu.edu/index.shtml"
azd env set SUPPORT_DESTINATION "JMU Student Success Center"
```

`AZURE_PRINCIPAL_ID` is your Microsoft Entra object ID. The Bicep deployment uses it to grant your signed-in account permission to create and populate the Search index. It is an identifier, not a secret.

Review the selected environment:

```powershell
azd env list
azd env get-value AZURE_LOCATION
azd env get-value INSTITUTION_NAME
```

Do not commit files under `.azure/<environment-name>/`.

## 7. Preview the Infrastructure

Compile the Bicep template locally:

```powershell
az bicep build --file infra/main.bicep --stdout | Out-Null
```

Then ask Azure to preview the resource changes:

```powershell
azd provision --preview
```

Preview does not intentionally deploy the application. Review the resource types, target subscription, target region, and role assignments. Stop and resolve any policy, permission, naming, quota, or regional error before continuing.

## 8. Deploy the Solution

Make sure Docker Desktop is running, then execute:

```powershell
azd up
```

`azd up` performs three operations:

1. Provisions the Azure resources from `infra/main.bicep`.
2. Builds the application container and pushes it to Azure Container Registry.
3. Deploys the image to Azure Container Apps.

Provisioning can take several minutes. Read any confirmation prompt carefully. A successful run prints the service endpoint and saves Bicep outputs in the selected `azd` environment.

## 9. Verify the Deployment

Display the deployed resources and application URL:

```powershell
azd show
$appUrl = azd env get-value AZURE_CONTAINER_APP_ENDPOINT
$appUrl
```

Check the health endpoint:

```powershell
Invoke-RestMethod "$appUrl/api/health"
```

Expected result:

```text
status mode
------ ----
ok     azure
```

Open the student experience:

```powershell
Start-Process $appUrl
```

The app is running, but it still needs an Azure AI Search index populated with approved content.

## 10. Prepare and Review University Content

You can use the sample files in `data/knowledge`, replace them with institution-approved Markdown, or create a pending review bundle from an official university website:

```powershell
python -m scripts.customize
```

The website importer asks for the university name, official HTTPS website, and staff support destination. It respects `robots.txt`, follows same-host HTML links, and writes files under `data/imported/<institution>` with `review_status: pending`.

Before indexing website content:

1. Have the institutional content owner review every generated Markdown file.
2. Remove stale, duplicated, restricted, or unsuitable content.
3. Verify that each `Source:` URL is authoritative.
4. Record approval through the institution's governance process.
5. Never include student records, advising notes, credentials, or other personal data.

Public website content is not automatically approved merely because it is public.

## 11. Create and Populate the Search Index

Load the deployment outputs into the current PowerShell process so the ingestion script can find Search and Foundry:

```powershell
azd env get-values | ForEach-Object {
  if ($_ -match '^([^=]+)=(.*)$') {
    $name = $matches[1]
    $value = $matches[2].Trim('"')
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
  }
}
```

Index the repository's reviewed sample content:

```powershell
python scripts/ingest.py --source data/knowledge
```

Or index a reviewed university bundle by supplying its directory:

```powershell
python scripts/ingest.py --source "<path-to-reviewed-markdown>"
```

Expected result: the script creates or updates the `student-services` index and reports the number of uploaded documents. Original university URLs are preserved as citations.

Role assignments can take several minutes to propagate. If ingestion returns HTTP 403 immediately after deployment, wait briefly, sign in again with `az login`, reload the `azd` values, and retry. If it continues, see the troubleshooting section.

## 12. Test Grounding and Safety

Refresh the browser and ask questions covered by the indexed content, such as:

- "When does fall registration open?"
- "What documents are needed for financial aid?"
- "How do I apply for campus housing?"

Confirm that answers include citations to the expected approved source.

Also test the deterministic safety routes:

- "What is my current tuition balance?" should offer staff escalation rather than claim access to a student record.
- "Make the admissions decision for this applicant" should escalate rather than make the decision.
- An unsupported policy question should not invent an answer.

Run the automated checks again after content or safety-rule changes:

```powershell
python -m pytest
python -m ruff check .
python -m mypy
```

## 13. Monitor the Application

Open the Application Insights overview or logs:

```powershell
azd monitor --overview
azd monitor --logs
```

For Container Apps logs, get the generated names and query the latest output:

```powershell
$resourceGroup = azd env get-value AZURE_RESOURCE_GROUP
$containerApp = azd env get-value AZURE_CONTAINER_APP_NAME

az containerapp logs show `
  --resource-group $resourceGroup `
  --name $containerApp `
  --type system `
  --tail 50

az containerapp logs show `
  --resource-group $resourceGroup `
  --name $containerApp `
  --tail 100
```

See [Azure Container Apps log streaming](https://learn.microsoft.com/azure/container-apps/log-streaming) for portal and CLI options. The reference application does not log chat message bodies or personal data by default.

## 14. Make and Deploy Updates

After application-only changes, run the tests and deploy a new container revision:

```powershell
python -m pytest
azd deploy
```

After Bicep or environment-setting changes, preview and apply the infrastructure update before deploying the app:

```powershell
azd provision --preview
azd provision
azd deploy
```

Use separate `azd` environments for development, test, and production. Do not use this workshop configuration as production without the reviews and hardening described in the main README.

## 15. Troubleshooting

### `AuthorizationFailed` or role-assignment errors

- Confirm the correct subscription with `az account show`.
- Confirm you have Owner, or Contributor plus Role Based Access Control Administrator.
- Activate any eligible role in Privileged Identity Management.
- Re-run `az login` and `azd auth login` after access changes.

### Model deployment failed or quota exceeded

- Recheck `gpt-4.1-mini` and `text-embedding-3-small` under **Operate** > **Quota** in the Foundry portal.
- Select a region with capacity for both models or request quota.
- If changing regions after a partial workshop deployment, clean up the failed environment and create a new `azd` environment for the new region.

### Docker or image build failed

- Start Docker Desktop and verify `docker version` shows a server.
- Confirm Docker is using Linux containers.
- Run `azd package` to isolate container build errors from Azure provisioning errors.

### Search ingestion returns HTTP 403

- Check `azd env get-value AZURE_PRINCIPAL_ID` is your signed-in user's object ID.
- If it was missing during provisioning, set it and run `azd provision` again.
- Allow time for Azure RBAC propagation, reload environment values, and retry ingestion.

### The application endpoint fails

- Verify `Invoke-RestMethod "$appUrl/api/health"`.
- Inspect Container Apps system logs first, then console logs.
- In the Azure portal, open the container app and select **Diagnose and solve problems**.
- See [troubleshoot Azure Container Apps deployment failures](https://learn.microsoft.com/azure/container-apps/deployment-errors).

### The application answers without useful citations

- Confirm the ingestion script uploaded documents successfully.
- Verify the Markdown files contain relevant approved content and authoritative `Source:` URLs.
- Ask a question that is clearly covered by one indexed document.

## 16. Remove the Workshop Resources

Azure resources can continue generating charges while they exist. When the workshop is finished, review and delete the selected environment:

```powershell
azd env list
azd down --purge
```

Read the deletion summary and confirmation prompt carefully. `azd down` removes the Azure resources for the active environment. It does not delete your source code.

Verify cleanup in the Azure portal by opening **Resource groups** and confirming the workshop resource group no longer exists.

## Official Microsoft References

- [Azure Developer CLI overview](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)
- [Install Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Work with `azd` environments](https://learn.microsoft.com/azure/developer/azure-developer-cli/work-with-environments)
- [Manage `azd` environment variables](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables)
- [Microsoft Foundry region support](https://learn.microsoft.com/azure/foundry/reference/region-support)
- [Microsoft Foundry RBAC](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry)
- [Azure AI Search security](https://learn.microsoft.com/azure/search/search-security-overview)
- [Azure Container Apps troubleshooting](https://learn.microsoft.com/azure/container-apps/troubleshooting)
- [Plan and manage Foundry costs](https://learn.microsoft.com/azure/foundry/concepts/manage-costs)
