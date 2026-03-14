// LinuxNLearn — chat.js
// Handles the AI chat widget (sidebar) and the full chat page.

(function () {
    const SETTINGS_STORAGE_KEY = "linuxnlearn.chat.settings.v1";

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

    function getChatSettings() {
        const searchModeEl = document.getElementById("search-mode-select");
        const recencyEl = document.getElementById("search-recency-select");
        const domainsEl = document.getElementById("search-domains-input");
        const safeSearchEl = document.getElementById("safe-search-toggle");

        const settings = {};

        if (searchModeEl && searchModeEl.value) {
            settings.search_mode = searchModeEl.value;
        }
        if (recencyEl && recencyEl.value) {
            settings.search_recency_filter = recencyEl.value;
        }
        if (domainsEl && domainsEl.value.trim()) {
            settings.search_domain_filter = domainsEl.value
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean);
        }
        if (safeSearchEl) {
            settings.safe_search = Boolean(safeSearchEl.checked);
        }

        return settings;
    }

    function saveChatSettings() {
        try {
            localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(getChatSettings()));
        } catch (e) {
            // Ignore storage errors (private mode, quota, etc.)
        }
    }

    function restoreChatSettings() {
        try {
            const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
            if (!raw) return;
            const settings = JSON.parse(raw);

            const searchModeEl = document.getElementById("search-mode-select");
            const recencyEl = document.getElementById("search-recency-select");
            const domainsEl = document.getElementById("search-domains-input");
            const safeSearchEl = document.getElementById("safe-search-toggle");

            if (searchModeEl && settings.search_mode) searchModeEl.value = settings.search_mode;
            if (recencyEl && settings.search_recency_filter) recencyEl.value = settings.search_recency_filter;
            if (domainsEl && Array.isArray(settings.search_domain_filter)) {
                domainsEl.value = settings.search_domain_filter.join(", ");
            }
            if (safeSearchEl && typeof settings.safe_search === "boolean") {
                safeSearchEl.checked = settings.safe_search;
            }
        } catch (e) {
            // Ignore parse/storage errors.
        }
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

    function setAssistantBubbleText(bubble, text, meta) {
        bubble.innerHTML = formatAssistantMessage(text) + renderAssistantMeta(meta);
    }

    function renderAssistantMeta(meta) {
        if (!meta) return "";

        const blocks = [];

        if (Array.isArray(meta.citations) && meta.citations.length) {
            const items = meta.citations
                .filter(Boolean)
                .map((url, idx) => {
                    const safeUrl = escapeHtml(String(url));
                    return `<li><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">Source ${idx + 1}</a></li>`;
                })
                .join("");
            if (items) {
                blocks.push(`<div class="ai-meta-block"><div class="ai-meta-title">Sources</div><ul class="ai-meta-list">${items}</ul></div>`);
            }
        }

        if (Array.isArray(meta.search_results) && meta.search_results.length) {
            const items = meta.search_results
                .slice(0, 5)
                .map((result) => {
                    const title = escapeHtml(String(result.title || result.url || "Search result"));
                    const url = escapeHtml(String(result.url || ""));
                    if (!url) return "";
                    return `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a></li>`;
                })
                .filter(Boolean)
                .join("");
            if (items) {
                blocks.push(`<div class="ai-meta-block"><div class="ai-meta-title">Search Results</div><ul class="ai-meta-list">${items}</ul></div>`);
            }
        }

        return blocks.length ? `<div class="ai-meta">${blocks.join("")}</div>` : "";
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
        let accumulated = "";

        try {
            const response = await fetch("/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    category: getCategory(),
                    lesson: getLesson(),
                    settings: getChatSettings(),
                }),
            });

            if (!response.ok || !response.body) {
                const fallbackText = await response.text();
                loadingBubble.textContent = `⚠️ ${fallbackText || `Request failed (${response.status})`}`;
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split("\n\n");
                buffer = events.pop() || "";

                for (const rawEvent of events) {
                    const parsed = parseSSEEvent(rawEvent);
                    if (!parsed) continue;

                    if (parsed.event === "delta") {
                        const piece = parsed.data && parsed.data.text ? String(parsed.data.text) : "";
                        if (piece) {
                            accumulated += piece;
                            setAssistantBubbleText(loadingBubble, accumulated);
                        }
                    } else if (parsed.event === "done") {
                        const finalReply = parsed.data && parsed.data.reply ? String(parsed.data.reply) : accumulated;
                        setAssistantBubbleText(loadingBubble, finalReply || "No response.", {
                            citations: parsed.data ? parsed.data.citations : undefined,
                            search_results: parsed.data ? parsed.data.search_results : undefined,
                        });
                    } else if (parsed.event === "error") {
                        const message = parsed.data && parsed.data.message ? String(parsed.data.message) : "Unknown error";
                        loadingBubble.textContent = "⚠️ " + message;
                    }
                }
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

    const settingsControls = [
        document.getElementById("search-mode-select"),
        document.getElementById("search-recency-select"),
        document.getElementById("search-domains-input"),
        document.getElementById("safe-search-toggle"),
    ].filter(Boolean);
    settingsControls.forEach((el) => {
        el.addEventListener("change", saveChatSettings);
        el.addEventListener("input", saveChatSettings);
    });

    restoreChatSettings();

    function parseSSEEvent(raw) {
        const lines = raw.split("\n");
        let event = "message";
        let data = "";

        for (const line of lines) {
            if (line.startsWith("event:")) {
                event = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
                data += line.slice(5).trim();
            }
        }

        if (!data) return null;
        try {
            return { event, data: JSON.parse(data) };
        } catch (e) {
            return { event, data: { text: data } };
        }
    }
})();
