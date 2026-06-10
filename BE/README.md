# FastAPI RAG Chatbot Backend

This backend lets you upload documents, indexes their text, and answers chatbot questions using retrieved document context.

## Setup

```powershell
cd C:\AI_project\ChatBot_Solution_With_uploaded_doc_and_generic\BE
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your OpenAI API key in `.env`.

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the API docs at:

```text
http://127.0.0.1:8000/docs
```

## Main Endpoints

- `GET /health` - check service status.
- `POST /documents/upload` - upload `.txt`, `.pdf`, or `.docx` files into the RAG index.
- `GET /documents` - list indexed source documents.
- `POST /chat` - ask a question using retrieved document context.

Example chat request:

```json
{
  "question": "What does the uploaded policy say about refunds?",
  "top_k": 4,
  "use_documents": true
}
```

Set `use_documents` to `false` for generic chat without RAG retrieval.
