# Demo Deployment On Azure App Service

This repository is ready for a two-App-Service demo deployment:

- `BE` deploys as the FastAPI API.
- `UI` deploys as the React/Vite frontend.

## 1. Create Backend App Service

Create an Azure App Service with:

- Publish: Code
- Runtime stack: Python 3.11
- Operating system: Linux
- App name: `chatbot-rag-api-demo` or update `.github/workflows/deploy-backend-azure.yml`

In the backend App Service, set these configuration values:

```text
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

Set the startup command:

```bash
bash startup.sh
```

Download the backend publish profile from Azure Portal and add it to GitHub:

```text
Settings > Secrets and variables > Actions > New repository secret
Name: AZURE_WEBAPP_PUBLISH_PROFILE_BACKEND
Value: paste the backend publish profile XML
```

## 2. Create Frontend App Service

Create another Azure App Service with:

- Publish: Code
- Runtime stack: Node 20 LTS
- Operating system: Linux
- App name: `chatbot-rag-ui-demo` or update `.github/workflows/deploy-frontend-azure.yml`

Set the frontend startup command:

```bash
pm2 serve /home/site/wwwroot --no-daemon --spa
```

Download the frontend publish profile from Azure Portal and add it to GitHub:

```text
Settings > Secrets and variables > Actions > New repository secret
Name: AZURE_WEBAPP_PUBLISH_PROFILE_FRONTEND
Value: paste the frontend publish profile XML
```

Add this GitHub Actions repository variable:

```text
Settings > Secrets and variables > Actions > Variables > New repository variable
Name: VITE_API_BASE_URL
Value: https://your-backend-app-name.azurewebsites.net
```

## 3. Run Deployment

Push to `main`, or run both workflows manually:

```text
GitHub repo > Actions
Deploy Backend to Azure App Service > Run workflow
Deploy Frontend to Azure App Service > Run workflow
```

## Notes

The current demo stores uploaded documents and the local RAG index inside the backend App Service filesystem. This is acceptable for a demo, but production should use Azure Blob Storage and Azure AI Search or another persistent vector database.
