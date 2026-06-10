# Chatbot UI

React chatbot interface for uploaded-document Q&A and generic chat.

## Run locally

Install Node.js with npm, then run:

```bash
npm install
copy .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://127.0.0.1:5173`.

## API connection

The UI calls the FastAPI backend using:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Uploaded files are sent to `POST /documents/upload`. Chat prompts are sent to `POST /chat`.
Document mode sends `use_documents: true`; generic mode sends `use_documents: false`.
