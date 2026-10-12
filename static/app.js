
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-button");
const newChatButton = document.getElementById("new-chat");

const STORAGE_KEY = "edubot_conversation_id";

function createConversationId() {
    return crypto.randomUUID();
}

function isValidUUID(value) {
    return typeof value === "string" &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

let conversationId = localStorage.getItem(STORAGE_KEY);

if (!isValidUUID(conversationId)) {
    conversationId = createConversationId();
    localStorage.setItem(STORAGE_KEY, conversationId);
}


// Display the welcome screen
function showWelcome() {
    chatMessages.innerHTML = `
        <div id="welcome" class="welcome">
            <div class="welcome-icon">✦</div>
            <p class="eyebrow">YOUR AI STUDY PARTNER</p>
            <h1>What do you want to learn?</h1>
            <p class="welcome-description">
                Ask questions, understand concepts, write code,
                and prepare for your exams.
            </p>
        </div>
    `;
}


// Display a chat message safely
function addMessage(role, content) {
    document.getElementById("welcome")?.remove();

    const message = document.createElement("div");
    message.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "Y" : "E";

    const body = document.createElement("div");
    body.className = "message-body";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "You" : "EduBot";

    const text = document.createElement("div");
    text.className = "message-text";
    text.textContent = content;

    body.append(label, text);
    message.append(avatar, body);

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


// Show loading state
function setLoading(isLoading) {
    sendButton.disabled = isLoading;
    messageInput.disabled = isLoading;
    sendButton.textContent = isLoading ? "…" : "↑";
}


// Send a message to Flask
async function sendMessage(message) {
    addMessage("user", message);
    setLoading(true);

    const typing = document.createElement("div");
    typing.className = "message";
    typing.id = "typing-indicator";

    const typingText = document.createElement("div");
    typingText.className = "message-text";
    typingText.textContent = "EduBot is thinking...";

    typing.appendChild(typingText);
    chatMessages.appendChild(typing);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }

        addMessage("assistant", data.answer);

    } catch (error) {
        addMessage(
            "assistant",
            "Sorry, something went wrong: " + error.message
        );
    } finally {
        document.getElementById("typing-indicator")?.remove();

        setLoading(false);
        messageInput.focus();
    }
}


// Handle the send button
chatForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message || sendButton.disabled) {
        return;
    }

    messageInput.value = "";
    messageInput.style.height = "auto";

    await sendMessage(message);
});


// Automatically adjust the input height
messageInput.addEventListener("input", function() {
    messageInput.style.height = "auto";

    messageInput.style.height =
        Math.min(messageInput.scrollHeight, 150) + "px";
});


// Enter sends; Shift + Enter adds a new line
messageInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});


// Handle suggestion buttons
document.querySelectorAll("[data-prompt]").forEach(function(button) {
    button.addEventListener("click", function() {
        if (sendButton.disabled) return;

        messageInput.value = button.dataset.prompt;
        chatForm.requestSubmit();
    });
});


// Start a new conversation
newChatButton.addEventListener("click", function() {
    if (sendButton.disabled) return;

    conversationId = createConversationId();
    localStorage.setItem(STORAGE_KEY, conversationId);

    showWelcome();

    messageInput.value = "";
    messageInput.style.height = "auto";
    messageInput.focus();
});


// Load messages saved in the database
async function loadHistory() {
    try {
        const response = await fetch(
            `/api/history/${encodeURIComponent(conversationId)}`
        );

        if (!response.ok) {
            throw new Error("Could not load chat history.");
        }

        const data = await response.json();

        if (data.messages.length === 0) {
            return;
        }

        showWelcome();

        data.messages.forEach(function(message) {
            addMessage(message.role, message.content);
        });

    } catch (error) {
        console.error("History error:", error);
    }
}

loadHistory();

