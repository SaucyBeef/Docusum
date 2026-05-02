import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import {
  askQuestion,
  clearHistory,
  deleteHistoryItem,
  fetchDocuments,
  fetchHistory,
  loginUser,
  registerUser,
  uploadDocument,
} from "./services/api";

const USER_STORAGE_KEY = "docusum_user";

const PAGES = {
  SPLASH: "splash",
  SERVICE: "service",
  HISTORY: "history",
  MANAGEMENT: "management",
};

function parseContexts(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

function toHistoryViewRecord(record) {
  return {
    id: record.id,
    question: record.question,
    answer: record.answer,
    contexts: parseContexts(record.contexts_json),
    documentId: record.document_id,
    createdAt: record.created_at,
  };
}

function formatDate(isoDate) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return date.toLocaleString();
}

export default function App() {
  const [page, setPage] = useState(PAGES.SPLASH);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  });

  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [historyRecords, setHistoryRecords] = useState([]);
  const [bootLoading, setBootLoading] = useState(false);
  const [globalError, setGlobalError] = useState("");

  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [answer, setAnswer] = useState("");
  const [contexts, setContexts] = useState([]);
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  const [menuOpen, setMenuOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(null);
  const [clearHistoryConfirmOpen, setClearHistoryConfirmOpen] = useState(false);
  const [clearHistoryBusy, setClearHistoryBusy] = useState(false);

  const fileInputRef = useRef(null);

  const isAuthenticated = Boolean(user?.id);
  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === Number(selectedDocumentId)) || null,
    [documents, selectedDocumentId],
  );

  useEffect(() => {
    if (!isAuthenticated) return;
    loadUserData(user.id);
    setPage(PAGES.SERVICE);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function closeOnOutsideClick(event) {
      if (!menuOpen) return;
      if (!event.target.closest(".account-menu-wrap")) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("click", closeOnOutsideClick);
    return () => document.removeEventListener("click", closeOnOutsideClick);
  }, [menuOpen]);

  async function loadUserData(userId) {
    setBootLoading(true);
    setGlobalError("");
    try {
      const [docs, history] = await Promise.all([fetchDocuments(userId), fetchHistory(userId, 50)]);
      setDocuments(Array.isArray(docs) ? docs : []);
      setHistoryRecords((Array.isArray(history) ? history : []).map(toHistoryViewRecord));
    } catch (error) {
      setGlobalError(error.message || "Could not load account data.");
    } finally {
      setBootLoading(false);
    }
  }

  function resetConversation() {
    setQuestion("");
    setAnswer("");
    setContexts([]);
    setQueryError("");
    setActiveHistoryId(null);
  }

  function persistUser(nextUser) {
    setUser(nextUser);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(nextUser));
  }

  function clearUser() {
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    setDocuments([]);
    setHistoryRecords([]);
    setSelectedDocumentId("");
  }

  function handleAuthInput(field, value) {
    setAuthForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      const action = authMode === "register" ? registerUser : loginUser;
      const nextUser = await action(authForm);
      persistUser(nextUser);
      setAuthForm({ name: "", email: "", password: "" });
      await loadUserData(nextUser.id);
      setPage(PAGES.SERVICE);
    } catch (error) {
      setAuthError(error.message || "Authentication failed.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadError("");
    setUploadMessage("");

    if (!isAuthenticated) {
      setUploadError("You must log in before uploading documents.");
      event.target.value = "";
      return;
    }

    setUploading(true);
    try {
      const result = await uploadDocument(user.id, file);
      const docs = await fetchDocuments(user.id);
      setDocuments(Array.isArray(docs) ? docs : []);
      if (typeof result.document_id === "number") {
        setSelectedDocumentId(String(result.document_id));
      }
      setUploadMessage(`Uploaded ${result.file_name} with ${result.chunk_count} chunks.`);
    } catch (error) {
      setUploadError(error.message || "Upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    setQueryError("");

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setQueryError("Enter a question.");
      return;
    }

    if (!isAuthenticated) {
      setQueryError("Log in to query your documents.");
      return;
    }

    setQueryLoading(true);
    try {
      const payload = {
        userId: user.id,
        question: trimmedQuestion,
        topK,
        documentId: selectedDocumentId ? Number(selectedDocumentId) : undefined,
      };

      const result = await askQuestion(payload);
      setAnswer(result.answer || "");
      setContexts(Array.isArray(result.contexts) ? result.contexts : []);
      setActiveHistoryId(result.history_id ?? null);

      setHistoryRecords((prev) => [
        {
          id: result.history_id,
          question: trimmedQuestion,
          answer: result.answer || "",
          contexts: (Array.isArray(result.contexts) ? result.contexts : []).map((row) => row.chunk_text),
          documentId: selectedDocumentId ? Number(selectedDocumentId) : null,
          createdAt: new Date().toISOString(),
        },
        ...prev,
      ]);
    } catch (error) {
      setQueryError(error.message || "Could not process query.");
    } finally {
      setQueryLoading(false);
    }
  }

  function handleUseHistory(record) {
    setQuestion(record.question || "");
    setAnswer(record.answer || "");
    setContexts(
      (record.contexts || []).map((text, index) => ({
        chunk_id: `history-${record.id}-${index}`,
        chunk_text: text,
        distance: null,
        document_id: record.documentId,
        chunk_index: index,
      })),
    );
    if (record.documentId) {
      setSelectedDocumentId(String(record.documentId));
    } else {
      setSelectedDocumentId("");
    }
    setActiveHistoryId(record.id || null);
    setPage(PAGES.SERVICE);
  }

  async function handleDeleteHistoryItem(historyId) {
    if (!isAuthenticated) return;
    setDeleteBusy(historyId);
    try {
      await deleteHistoryItem(user.id, historyId);
      setHistoryRecords((prev) => prev.filter((row) => row.id !== historyId));
      if (activeHistoryId === historyId) {
        resetConversation();
      }
    } catch (error) {
      setGlobalError(error.message || "Could not delete history record.");
    } finally {
      setDeleteBusy(null);
    }
  }

  async function handleClearHistory() {
    if (!isAuthenticated) return;
    setClearHistoryBusy(true);
    try {
      await clearHistory(user.id);
      setHistoryRecords([]);
      resetConversation();
      setClearHistoryConfirmOpen(false);
    } catch (error) {
      setGlobalError(error.message || "Could not clear history.");
    } finally {
      setClearHistoryBusy(false);
    }
  }

  function handleLogout() {
    clearUser();
    resetConversation();
    setAuthError("");
    setGlobalError("");
    setMenuOpen(false);
    setPage(PAGES.SPLASH);
  }

  function renderSplash() {
    return (
      <section className="splash">
        <div className="splash-main">
          <h1>Docusum</h1>
          <p className="subtitle">Document-grounded answers for your uploaded files.</p>

          <div className="auth-toggle" role="tablist" aria-label="Authentication Mode">
            <button
              type="button"
              className={authMode === "login" ? "toggle-btn active" : "toggle-btn"}
              onClick={() => setAuthMode("login")}
            >
              Log In
            </button>
            <button
              type="button"
              className={authMode === "register" ? "toggle-btn active" : "toggle-btn"}
              onClick={() => setAuthMode("register")}
            >
              Register
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {authMode === "register" && (
              <label>
                Name
                <input
                  type="text"
                  value={authForm.name}
                  onChange={(event) => handleAuthInput("name", event.target.value)}
                  autoComplete="name"
                />
              </label>
            )}

            <label>
              Email
              <input
                type="email"
                value={authForm.email}
                onChange={(event) => handleAuthInput("email", event.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={authForm.password}
                onChange={(event) => handleAuthInput("password", event.target.value)}
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
                required
              />
            </label>

            {authError && <p className="error-text">{authError}</p>}

            <button type="submit" className="primary-btn" disabled={authLoading}>
              {authLoading ? "Processing..." : authMode === "login" ? "Log In" : "Create Account"}
            </button>
          </form>

          <button
            type="button"
            className="ghost-btn"
            onClick={() => {
              setPage(PAGES.SERVICE);
              setAuthError("");
            }}
          >
            Continue As Guest
          </button>
        </div>
      </section>
    );
  }

  function renderHeader() {
    return (
      <header className="topbar">
        <div>
          <h2>Docusum Service</h2>
          <p>Upload documents, ask questions, and review grounded context.</p>
        </div>

        <div className="topbar-actions">
          <button type="button" className="ghost-btn" onClick={resetConversation}>
            New Conversation
          </button>

          {isAuthenticated ? (
            <div className="account-menu-wrap">
              <button
                type="button"
                className="primary-btn account-btn"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((prev) => !prev)}
              >
                Account
              </button>
              {menuOpen && (
                <div className="menu-panel">
                  <button type="button" onClick={() => setPage(PAGES.HISTORY)}>
                    History
                  </button>
                  <button type="button" onClick={() => setPage(PAGES.MANAGEMENT)}>
                    Management
                  </button>
                  <button type="button" onClick={handleLogout}>
                    Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                setPage(PAGES.SPLASH);
                setAuthMode("login");
              }}
            >
              Log In
            </button>
          )}
        </div>
      </header>
    );
  }

  function renderService() {
    return (
      <section className="layout">
        {renderHeader()}

        {globalError && <p className="error-text">{globalError}</p>}
        {uploadMessage && <p className="ok-text">{uploadMessage}</p>}
        {uploadError && <p className="error-text">{uploadError}</p>}

        {bootLoading ? (
          <div className="loading-panel">
            <p>Loading account data...</p>
          </div>
        ) : (
          <>
            <div className="service-controls">
              <div>
                <label htmlFor="documentSelect">Document Scope</label>
                <select
                  id="documentSelect"
                  value={selectedDocumentId}
                  onChange={(event) => setSelectedDocumentId(event.target.value)}
                  disabled={!isAuthenticated}
                >
                  <option value="">All Documents</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.file_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="topK">Top K Chunks</label>
                <input
                  id="topK"
                  type="number"
                  min={1}
                  max={20}
                  value={topK}
                  onChange={(event) => setTopK(Math.max(1, Math.min(20, Number(event.target.value) || 1)))}
                />
              </div>

              <div>
                <label htmlFor="uploadInput">Attach Document</label>
                <div className="file-row">
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? "Uploading..." : "Choose File"}
                  </button>
                  <input
                    id="uploadInput"
                    ref={fileInputRef}
                    type="file"
                    onChange={handleUpload}
                    hidden
                    accept=".pdf,.doc,.docx,.txt,.md"
                  />
                </div>
              </div>
            </div>

            <form className="query-form" onSubmit={handleAsk}>
              <label htmlFor="queryText">Question</label>
              <textarea
                id="queryText"
                rows={4}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  isAuthenticated
                    ? "Ask a question about your uploaded content..."
                    : "Log in to upload documents and run queries..."
                }
              />

              {queryError && <p className="error-text">{queryError}</p>}

              <button type="submit" className="primary-btn" disabled={queryLoading}>
                {queryLoading ? "Processing..." : "Run Query"}
              </button>
            </form>

            <div className="result-grid">
              <section className="result-panel">
                <h3>Answer</h3>
                {answer ? <p>{answer}</p> : <p className="muted">No answer yet.</p>}
                {activeHistoryId && <p className="meta">History ID: {activeHistoryId}</p>}
              </section>

              <section className="result-panel">
                <h3>Retrieved Context</h3>
                {contexts.length === 0 && <p className="muted">No context chunks yet.</p>}
                {contexts.length > 0 && (
                  <ul className="context-list">
                    {contexts.map((chunk) => (
                      <li key={chunk.chunk_id}>
                        <p>{chunk.chunk_text}</p>
                        <p className="meta">
                          Doc {chunk.document_id ?? selectedDocument?.id ?? "n/a"} | Chunk {chunk.chunk_index}{" "}
                          {typeof chunk.distance === "number" ? `| Distance ${chunk.distance.toFixed(4)}` : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        )}
      </section>
    );
  }

  function renderHistory() {
    return (
      <section className="layout">
        {renderHeader()}
        <div className="section-head">
          <h3>Conversation History</h3>
          <button type="button" className="ghost-btn" onClick={() => setPage(PAGES.SERVICE)}>
            Return
          </button>
        </div>

        {historyRecords.length === 0 ? (
          <p className="muted">No saved history entries.</p>
        ) : (
          <ul className="history-list">
            {historyRecords.map((record) => (
              <li key={record.id}>
                <div>
                  <p className="history-question">{record.question}</p>
                  <p className="meta">{formatDate(record.createdAt)}</p>
                </div>
                <div className="history-actions">
                  <button type="button" className="ghost-btn" onClick={() => handleUseHistory(record)}>
                    Use
                  </button>
                  <button
                    type="button"
                    className="danger-btn"
                    onClick={() => handleDeleteHistoryItem(record.id)}
                    disabled={deleteBusy === record.id}
                  >
                    {deleteBusy === record.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    );
  }

  function renderManagement() {
    return (
      <section className="layout">
        {renderHeader()}
        <div className="section-head">
          <h3>Account Management</h3>
          <button type="button" className="ghost-btn" onClick={() => setPage(PAGES.SERVICE)}>
            Return
          </button>
        </div>

        <section className="management-panel">
          <h4>History Data</h4>
          <p className="muted">Erase all saved conversation history for this account.</p>
          <button type="button" className="danger-btn" onClick={() => setClearHistoryConfirmOpen(true)}>
            Erase History
          </button>
        </section>

        <section className="management-panel">
          <h4>Account Data</h4>
          <p className="muted">Delete account is not available yet because no backend endpoint exists.</p>
          <button type="button" className="danger-btn" disabled>
            Delete Account
          </button>
        </section>

        {clearHistoryConfirmOpen && (
          <div className="confirm-overlay" role="dialog" aria-modal="true">
            <div className="confirm-panel">
              <h4>Confirm History Erase</h4>
              <p>This permanently removes all history records for this account.</p>
              <div className="confirm-actions">
                <button type="button" className="ghost-btn" onClick={() => setClearHistoryConfirmOpen(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="danger-btn"
                  onClick={handleClearHistory}
                  disabled={clearHistoryBusy}
                >
                  {clearHistoryBusy ? "Erasing..." : "Confirm"}
                </button>
              </div>
            </div>
          </div>
        )}
      </section>
    );
  }

  if (page === PAGES.SPLASH) return renderSplash();
  if (page === PAGES.HISTORY) return renderHistory();
  if (page === PAGES.MANAGEMENT) return renderManagement();
  return renderService();
}
