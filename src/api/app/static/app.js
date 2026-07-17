const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
let conversationId = null;

loadPublicConfig();

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
  });
});

async function loadPublicConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) return;
    const config = await response.json();
    const institutionName = config.institution_name || "University";
    document.querySelector("#institution-name").textContent = institutionName;
    document.querySelector("#brand-mark").textContent = institutionName
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase();
    if (config.university_website) {
      const source = document.querySelector("#university-source");
      source.href = config.university_website;
      source.textContent = "University website";
      source.hidden = false;
    }
  } catch {
    // Static defaults keep the workshop usable when configuration is unavailable.
  }
}

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 144)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user", message);
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  const pending = appendMessage("assistant", "Searching approved university content…", true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
    if (!response.ok) throw new Error("The assistant is temporarily unavailable.");
    const payload = await response.json();
    conversationId = payload.conversation_id;
    pending.remove();
    appendAssistantResponse(payload);
  } catch (error) {
    pending.remove();
    appendMessage("assistant", error.message || "The assistant is temporarily unavailable.");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
});

function appendMessage(role, text, pending = false) {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;
  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "S";
    article.appendChild(avatar);
  }
  const content = document.createElement("div");
  content.className = `message-content${pending ? " typing" : ""}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  content.appendChild(paragraph);
  article.appendChild(content);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function appendAssistantResponse(payload) {
  const article = appendMessage("assistant", payload.answer);
  const content = article.querySelector(".message-content");

  if (payload.escalation.required) {
    const escalation = document.createElement("p");
    escalation.className = "escalation";
    escalation.textContent = `Handoff: ${payload.escalation.destination}`;
    content.appendChild(escalation);
  }

  if (payload.citations.length) {
    const citations = document.createElement("div");
    citations.className = "citations";
    payload.citations.forEach((citation) => {
      const link = document.createElement("a");
      link.className = "citation-link";
      link.textContent = citation.title;
      link.href = citation.source_url || "#";
      link.target = "_blank";
      link.rel = "noreferrer";
      citations.appendChild(link);
    });
    content.appendChild(citations);
  }
}
