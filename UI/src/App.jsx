import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Check,
  ChevronDown,
  FileText,
  History,
  Loader2,
  MessageSquarePlus,
  Paperclip,
  Search,
  Send,
  Settings2,
  Sparkles,
  Upload,
  UserRound,
  X,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const starterMessages = [
  {
    id: 1,
    role: "assistant",
    text: "Hi, I can answer general questions or use an uploaded document as context. Add a file, choose a mode, and ask away.",
    time: "Now",
  },
];

const suggestions = [
  "Summarize the uploaded document",
  "Find key risks and assumptions",
  "Draft a customer-ready answer",
  "Explain this in simpler language",
];

function App() {
  const fileInputRef = useRef(null);
  const sessionIdRef = useRef(crypto.randomUUID());
  const [messages, setMessages] = useState(starterMessages);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("document");
  const [isLoading, setIsLoading] = useState(false);
  const [uploads, setUploads] = useState([]);
  const [uploadError, setUploadError] = useState("");
  const [userName, setUserName] = useState("");
  const [pendingUserName, setPendingUserName] = useState("");
  const [userStats, setUserStats] = useState(null);
  const [historyError, setHistoryError] = useState("");

  const activeContext = useMemo(() => {
    if (!userName) return "Enter your name to start";
    if (mode === "document" && uploads.length === 0) return "Waiting for a document";
    if (mode === "document") return `${uploads.length} document${uploads.length > 1 ? "s" : ""} ready`;
    return "Generic chat enabled";
  }, [mode, uploads.length, userName]);

  const loadUserHistory = async () => {
    try {
      setHistoryError("");
      const response = await fetch(`${API_BASE_URL}/analytics/users`);
      if (!response.ok) {
        const error = await readApiError(response);
        throw new Error(error);
      }
      const result = await response.json();
      setUserStats(result);
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "Unable to load user history");
    }
  };

  useEffect(() => {
    loadUserHistory();
  }, []);

  const handleUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setUploadError("");
    event.target.value = "";

    for (const file of files) {
      const localId = `${file.name}-${file.lastModified}-${crypto.randomUUID()}`;
      const pendingFile = {
        id: localId,
        name: file.name,
        size: formatSize(file.size),
        status: "Uploading",
      };

      setUploads((current) => [...current, pendingFile]);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const error = await readApiError(response);
          throw new Error(error);
        }

        const result = await response.json();
        setUploads((current) =>
          current.map((item) =>
            item.id === localId
              ? {
                  ...item,
                  id: result.document_id,
                  status: `${result.chunks_added} chunk${result.chunks_added === 1 ? "" : "s"} indexed`,
                }
              : item,
          ),
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Upload failed";
        setUploadError(message);
        setUploads((current) => current.filter((item) => item.id !== localId));
      }
    }
  };

  const removeUpload = (id) => {
    setUploads((current) => current.filter((file) => file.id !== id));
  };

  const sendMessage = async (messageText = prompt) => {
    const text = messageText.trim();
    if (!text || isLoading || !userName) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text,
      time: getTime(),
    };

    setMessages((current) => [...current, userMessage]);
    setPrompt("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: text,
          top_k: mode === "document" ? 4 : 1,
          use_documents: mode === "document",
          session_id: sessionIdRef.current,
          user_name: userName,
        }),
      });

      if (!response.ok) {
        const error = await readApiError(response);
        throw new Error(error);
      }

      const result = await response.json();
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: result.answer,
          sources: result.sources || [],
          time: getTime(),
        },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach the chatbot API";
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `I could not get a response from the API. ${message}`,
          time: getTime(),
        },
      ]);
    } finally {
      setIsLoading(false);
      loadUserHistory();
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage();
  };

  const handleNameSubmit = (event) => {
    event.preventDefault();
    const nextUserName = pendingUserName.trim();
    if (!nextUserName) return;
    setUserName(nextUserName);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Chat controls">
        <div className="brand">
          <span className="brand-icon">
            <Bot size={22} />
          </span>
          <div>
            <h1>DocuChat</h1>
            <p>Uploaded document and generic assistant</p>
          </div>
        </div>

        <button
          className="new-chat"
          type="button"
          onClick={() => {
            sessionIdRef.current = crypto.randomUUID();
            setMessages(starterMessages);
          }}
        >
          <MessageSquarePlus size={18} />
          New chat
        </button>

        {userName && (
          <section className="panel user-panel">
            <div className="panel-title">
              <UserRound size={17} />
              User
            </div>
            <div className="user-chip">
              <strong>{userName}</strong>
              <button
                type="button"
                onClick={() => {
                  setPendingUserName(userName);
                  setUserName("");
                }}
              >
                Change
              </button>
            </div>
          </section>
        )}

        <section className="panel">
          <div className="panel-title">
            <Settings2 size={17} />
            Mode
          </div>
          <div className="mode-switch" role="tablist" aria-label="Chat mode">
            <button
              className={mode === "document" ? "active" : ""}
              type="button"
              onClick={() => setMode("document")}
            >
              <FileText size={16} />
              Document
            </button>
            <button className={mode === "generic" ? "active" : ""} type="button" onClick={() => setMode("generic")}>
              <Sparkles size={16} />
              Generic
            </button>
          </div>
        </section>

        <section className="panel upload-panel">
          <div className="panel-title">
            <Paperclip size={17} />
            Documents
          </div>
          <button className="upload-drop" type="button" onClick={() => fileInputRef.current?.click()}>
            <Upload size={22} />
            <span>Upload PDF, DOCX, or TXT</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={handleUpload}
            hidden
          />

          {uploadError && <p className="upload-error">{uploadError}</p>}

          <div className="file-list" aria-live="polite">
            {uploads.map((file) => (
              <div className="file-row" key={file.id}>
                <FileText size={16} />
                <div>
                  <strong>{file.name}</strong>
                  <span>
                    {file.size}
                    {file.status ? ` - ${file.status}` : ""}
                  </span>
                </div>
                <button type="button" aria-label={`Remove ${file.name}`} onClick={() => removeUpload(file.id)}>
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="panel history-panel">
          <div className="panel-title">
            <History size={17} />
            Recent
          </div>
          {historyError && <p className="history-note">{historyError}</p>}
          {userStats?.recent_activity?.length ? (
            userStats.recent_activity.slice(0, 4).map((activity) => (
              <button type="button" key={`${activity.timestamp}-${activity.question}`}>
                <strong>{activity.user_name || "Unknown user"}</strong>
                <span>{activity.question}</span>
              </button>
            ))
          ) : (
            <p className="history-note">No chat history yet</p>
          )}
        </section>
      </aside>

      <section className="chat-area" aria-label="Chat workspace">
        <header className="topbar">
          <div className="search-box">
            <Search size={18} />
            <input type="search" placeholder="Search current conversation" />
          </div>
          <div className="status-pill">
            <Check size={15} />
            {activeContext}
          </div>
          <button className="icon-button" type="button" aria-label="Open settings">
            <ChevronDown size={18} />
          </button>
        </header>

        <div className="conversation">
          {!userName && (
            <section className="name-gate" aria-label="User name">
              <div>
                <Bot size={24} />
                <h2>Start your chat</h2>
                <p>Enter your name so Keli Assistant can save this conversation in backend history.</p>
              </div>
              <form onSubmit={handleNameSubmit}>
                <input
                  type="text"
                  value={pendingUserName}
                  placeholder="Your name"
                  onChange={(event) => setPendingUserName(event.target.value)}
                  autoFocus
                />
                <button type="submit" disabled={!pendingUserName.trim()}>
                  Continue
                </button>
              </form>
            </section>
          )}

          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <div className="avatar" aria-hidden="true">
                {message.role === "assistant" ? <Bot size={18} /> : <UserRound size={18} />}
              </div>
              <div className="bubble">
                <div className="message-meta">
                  <strong>{message.role === "assistant" ? "Keli Assistant" : userName || "You"}</strong>
                  <span>{message.time}</span>
                </div>
                <p>{message.text}</p>
                {message.sources?.length > 0 && (
                  <div className="source-list">
                    {message.sources.map((source) => (
                      <details key={`${source.document_id}-${source.chunk_id}`}>
                        <summary>
                          {source.filename} - chunk {source.chunk_id} - score {source.score}
                        </summary>
                        <p>{source.text}</p>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}

          {isLoading && (
            <article className="message assistant">
              <div className="avatar" aria-hidden="true">
                <Bot size={18} />
              </div>
              <div className="bubble loading">
                <Loader2 size={18} />
                Thinking through the context
              </div>
            </article>
          )}
        </div>

        {mode === "document" && (
          <div className="suggestions" aria-label="Prompt suggestions">
            {suggestions.map((suggestion) => (
              <button type="button" key={suggestion} onClick={() => sendMessage(suggestion)} disabled={!userName}>
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <form className="composer" onSubmit={handleSubmit}>
          <button className="icon-button" type="button" aria-label="Attach document" onClick={() => fileInputRef.current?.click()}>
            <Paperclip size={19} />
          </button>
          <textarea
            value={prompt}
            placeholder={
              userName
                ? mode === "document"
                  ? "Ask about your uploaded document..."
                  : "Ask a general question..."
                : "Enter your name before starting the chat"
            }
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
              }
            }}
            rows={1}
          />
          <button className="send-button" type="submit" disabled={!prompt.trim() || isLoading || !userName} aria-label="Send message">
            <Send size={19} />
          </button>
        </form>
      </section>
    </main>
  );
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getTime() {
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
}

async function readApiError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.message || response.statusText;
  } catch {
    return response.statusText;
  }
}

export default App;
