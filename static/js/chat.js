// LinuxNLearn — chat.js
// Handles the AI chat widget (sidebar) and the full chat page.

(function () {
    const messagesEl = document.getElementById("chat-messages");
    const inputEl    = document.getElementById("chat-input");
    const sendBtn    = document.getElementById("chat-send");

    if (!messagesEl || !inputEl || !sendBtn) return;

    // Context select is only on the full chat page
    const contextSelect = document.getElementById("context-select");

    function getCategory() {
        if (contextSelect) return contextSelect.value;
        return (typeof CHAT_CATEGORY !== "undefined") ? CHAT_CATEGORY : "";
    }

    function getLesson() {
        return (typeof CHAT_LESSON !== "undefined") ? CHAT_LESSON : "";
    }

    function appendMessage(role, text, isLoading) {
        const wrapper = document.createElement("div");
        wrapper.className = "chat-message " + role;
        const bubble = document.createElement("div");
        bubble.className = "message-bubble" + (isLoading ? " loading" : "");
        bubble.textContent = text;
        wrapper.appendChild(bubble);
        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    async function sendMessage() {
        const text = inputEl.value.trim();
        if (!text) return;

        inputEl.value = "";
        sendBtn.disabled = true;

        appendMessage("user", text);
        const loadingBubble = appendMessage("assistant", "Thinking…", true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    category: getCategory(),
                    lesson: getLesson(),
                }),
            });
            const data = await response.json();
            if (data.error) {
                loadingBubble.textContent = "⚠️ " + data.error;
            } else {
                loadingBubble.textContent = data.reply || "No response.";
            }
        } catch (err) {
            loadingBubble.textContent = "⚠️ Network error. Please try again.";
        } finally {
            loadingBubble.classList.remove("loading");
            sendBtn.disabled = false;
            inputEl.focus();
        }
    }

    sendBtn.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", function (e) {
        if (e.key === "Enter") sendMessage();
    });

    // On full chat page, update category when select changes
    if (contextSelect) {
        contextSelect.addEventListener("change", function () {
            // Category context is read dynamically in getCategory()
        });
    }
})();
