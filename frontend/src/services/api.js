const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data?.error || data?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}

export async function registerUser({ name, email, password }) {
  return request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
}

export async function loginUser({ email, password }) {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function uploadDocument(userId, file) {
  const formData = new FormData();
  formData.append("user_id", String(userId));
  formData.append("file", file);

  return request("/upload/", {
    method: "POST",
    body: formData,
  });
}

export async function fetchDocuments(userId) {
  return request(`/upload/documents/${userId}`);
}

export async function askQuestion({ userId, question, topK, documentId }) {
  const payload = {
    user_id: userId,
    question,
    top_k: topK,
  };

  if (typeof documentId === "number") {
    payload.document_id = documentId;
  }

  return request("/query/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function fetchHistory(userId, limit = 50) {
  return request(`/history/${userId}?limit=${limit}`);
}

export async function deleteHistoryItem(userId, historyId) {
  return request(`/history/${userId}/${historyId}`, {
    method: "DELETE",
  });
}

export async function clearHistory(userId) {
  return request(`/history/${userId}`, {
    method: "DELETE",
  });
}
