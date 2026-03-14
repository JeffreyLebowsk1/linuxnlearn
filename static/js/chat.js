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
        if (role === "assistant" && !isLoading) {
            bubble.innerHTML = formatAssistantMessage(text);
        } else {
            bubble.textContent = text;
        }
        wrapper.appendChild(bubble);
        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    function setAssistantBubbleText(bubble, text) {
        bubble.innerHTML = formatAssistantMessage(text);
    }

    function formatAssistantMessage(text) {
        const raw = String(text || "");
        // If provider returns HTML snippets, sanitize and render them.
        if (/<\/?[a-z][\s\S]*>/i.test(raw)) {
            return sanitizeAllowedHtml(raw);
        }
        return renderMarkdownLike(raw);
    }

    function renderMarkdownLike(text) {
        const codeBlocks = [];
        let content = String(text);

        // Preserve fenced code blocks before escaping everything else.
        content = content.replace(/```(?:\w+)?\n([\s\S]*?)```/g, (_, code) => {
            const token = `__CODE_BLOCK_${codeBlocks.length}__`;
            codeBlocks.push(`<pre><code>${escapeHtml(code.trim())}</code></pre>`);
            return token;
        });

        content = escapeHtml(content);
        content = content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        content = content.replace(/`([^`]+)`/g, "<code>$1</code>");

        let html = content
            .split(/\n\n+/)
            .map((block) => {
                const b = block.trim();
                if (!b) return "";
                if (b.startsWith("__CODE_BLOCK_")) return b;
                return `<p>${b.replace(/\n/g, "<br>")}</p>`;
            })
            .join("");

        codeBlocks.forEach((code, idx) => {
            html = html.replace(`__CODE_BLOCK_${idx}__`, code);
        });
        return html;
    }

    function sanitizeAllowedHtml(html) {
        const allowedTags = new Set([
            "p", "br", "strong", "em", "ul", "ol", "li", "blockquote",
            "pre", "code", "table", "thead", "tbody", "tr", "th", "td",
            "h1", "h2", "h3", "h4"
        ]);
        const template = document.createElement("template");
        template.innerHTML = html;

        const cleanNode = (node) => {
            if (node.nodeType === Node.TEXT_NODE) return;
            if (node.nodeType !== Node.ELEMENT_NODE) {
                node.remove();
                return;
            }

            const tag = node.tagName.toLowerCase();
            if (!allowedTags.has(tag)) {
                const parent = node.parentNode;
                while (node.firstChild) parent.insertBefore(node.firstChild, node);
                node.remove();
                return;
            }

            // Strip all attributes for safety.
            [...node.attributes].forEach((attr) => node.removeAttribute(attr.name));
            [...node.childNodes].forEach(cleanNode);
        };

        [...template.content.childNodes].forEach(cleanNode);
        return template.innerHTML;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
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
                setAssistantBubbleText(loadingBubble, data.reply || "No response.");
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
