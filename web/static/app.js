/* ===== AI Agent Client ===== */

/* --- AgentClient (API communication) --- */
class AgentClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.token = null;
        this.conversationId = 0;
        this.abortController = null;
        this._receivedDone = false;
    }

    async init() {
        try {
            const resp = await fetch(`${this.baseUrl}/api/v1/auth/dev-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            if (!resp.ok) throw new Error(`Login HTTP ${resp.status}`);
            const data = await resp.json();
            this.token = data.token;
            return true;
        } catch (e) {
            console.error('Auto-login failed:', e);
            return false;
        }
    }

    async sendMessage(message, handlers) {
        if (!this.token) {
            if (handlers.onError) handlers.onError('Not logged in');
            return;
        }

        this.abortController = new AbortController();
        this._receivedDone = false;

        try {
            const resp = await fetch(`${this.baseUrl}/api/v1/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`,
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                }),
                signal: this.abortController.signal,
            });

            if (!resp.ok) {
                const errText = await resp.text().catch(() => '');
                throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 200)}`);
            }

            if (!resp.body) {
                throw new Error('Response body unavailable');
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        try {
                            const data = JSON.parse(dataStr);
                            this._dispatch(data, handlers);
                        } catch (e) {
                            // non-JSON line, ignore
                        }
                    }
                    // ignore event: lines (ping, text, etc.) — data is in data: lines
                }
            }
        } catch (e) {
            if (e.name === 'AbortError') return;
            console.error('Chat error:', e);
            if (handlers.onError) handlers.onError(e.message);
        } finally {
            if (!this._receivedDone && handlers.onDone) {
                handlers.onDone({});
            }
            this.abortController = null;
        }
    }

    cancel() {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
    }

    _dispatch(event, handlers) {
        switch (event.type) {
        case 'text':
            if (handlers.onText) handlers.onText(event.content);
            break;
        case 'plan_created':
            if (handlers.onPlanCreated) handlers.onPlanCreated(event);
            break;
        case 'tool_progress':
            if (handlers.onToolProgress) handlers.onToolProgress(event);
            break;
        case 'tool_call':
            if (handlers.onToolCall) handlers.onToolCall(event);
            break;
        case 'tool_result':
            if (handlers.onToolResult) handlers.onToolResult(event);
            break;
        case 'thinking':
            if (handlers.onThinking) handlers.onThinking(event.content);
            break;
        case 'error':
            if (handlers.onError) handlers.onError(event.error);
            break;
        case 'done':
            this.conversationId = event.conversation_id || this.conversationId;
            if (handlers.onDone) handlers.onDone(event);
            this._receivedDone = true;
            break;
        }
    }
}


/* --- ToolProgressManager --- */
class ToolProgressManager {
    constructor(panelEl, listEl) {
        this.panel = panelEl;
        this.list = listEl;
        this.cards = new Map();
        this.toolCount = 0;
    }

    show() { this.panel.classList.add('visible'); }
    hide() { this.panel.classList.remove('visible'); }

    startTool(toolName, toolArgs, currentStep, totalSteps) {
        this.show();
        const card = this._createCard(toolName, toolArgs, currentStep, totalSteps, 'running');
        const id = `tool-${++this.toolCount}`;
        card.dataset.toolId = id;
        this.list.appendChild(card);
        this.cards.set(id, card);
        return id;
    }

    updateTool(toolName, currentStep, totalSteps, status) {
        for (const [, card] of this.cards) {
            const nameEl = card.querySelector('.tool-card-name');
            if (nameEl && nameEl.textContent === toolName) {
                this._setStatus(card, status, currentStep, totalSteps);
                return;
            }
        }
    }

    _createCard(toolName, toolArgs, currentStep, totalSteps, status) {
        const card = document.createElement('div');
        card.className = 'tool-card';
        const stepText = totalSteps > 0 ? `Step ${currentStep}/${totalSteps}` : `Step ${currentStep}`;
        card.innerHTML = `
            <div class="tool-card-header">
                <div class="tool-card-icon ${status}"></div>
                <span class="tool-card-name">${this._esc(toolName)}</span>
            </div>
            <div class="tool-card-step">${stepText}</div>
            <div class="tool-card-args">${this._formatArgs(toolArgs)}</div>
            <div class="tool-card-status ${status}">${this._statusLabel(status)}</div>
        `;
        return card;
    }

    _setStatus(card, status, currentStep, totalSteps) {
        const iconEl = card.querySelector('.tool-card-icon');
        const statusEl = card.querySelector('.tool-card-status');
        const stepEl = card.querySelector('.tool-card-step');
        iconEl.className = `tool-card-icon ${status}`;
        statusEl.className = `tool-card-status ${status}`;
        statusEl.textContent = this._statusLabel(status);
        const stepText = totalSteps > 0 ? `Step ${currentStep}/${totalSteps}` : `Step ${currentStep}`;
        stepEl.textContent = stepText;
        if (status === 'completed') iconEl.textContent = '✓';
        else if (status === 'failed') iconEl.textContent = '✗';
        else if (status === 'degraded') iconEl.textContent = '⚠';
        else iconEl.textContent = '';
    }

    _statusLabel(status) {
        switch (status) {
        case 'running': return 'Running...';
        case 'completed': return 'Completed';
        case 'failed': return 'Failed';
        case 'degraded': return 'Degraded';
        default: return status;
        }
    }

    _formatArgs(args) {
        if (!args || Object.keys(args).length === 0) return '';
        const parts = [];
        for (const [k, v] of Object.entries(args)) {
            const s = typeof v === 'string' ? v : JSON.stringify(v);
            parts.push(`${k}=${s.length > 40 ? s.slice(0, 40) + '...' : s}`);
        }
        return parts.join(', ');
    }

    _esc(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    clear() { this.list.innerHTML = ''; this.cards.clear(); }
}


/* ===== App Controller ===== */
const client = new AgentClient('');

// DOM refs
const messagesEl = document.getElementById('messages');
const welcomeScreen = document.getElementById('welcome-screen');
const chatInputBar = document.getElementById('chat-input-bar');
const contentArea = document.getElementById('content-area');
const toolPanel = document.getElementById('tool-panel');
const toolList = document.getElementById('tool-list');
const toolPanelClose = document.getElementById('tool-panel-close');
const toolManager = new ToolProgressManager(toolPanel, toolList);

// Inputs
const inputMain = document.getElementById('message-input');
const sendBtnMain = document.getElementById('send-btn');
const inputChat = document.getElementById('message-input-chat');
const sendBtnChat = document.getElementById('send-btn-chat');

// Model selector
const inputModelSelector = document.getElementById('input-model-selector');
const inputModelName = document.getElementById('input-model-name');
const modelDropdown = document.getElementById('model-dropdown');
let selectedModel = 'claude-sonnet-4.5';
let selectedProvider = 'default';

// Status
const statusIndicator = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');

// Buttons
const btnNewChat = document.getElementById('btn-new-chat');
const featureCards = document.querySelectorAll('.feature-card');

// State
let currentAssistantMsg = null;
let isStreaming = false;
let activeConversationId = 0;
let isInConversation = false;

/* --- Status --- */
function setStatus(state, text) {
    statusIndicator.className = `status-indicator ${state}`;
    statusText.textContent = text;
}

/* --- Messages --- */
function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.textContent = content;
    messagesEl.appendChild(div);
    contentArea.scrollTop = contentArea.scrollHeight;
    return div;
}

function resetAfterResponse() {
    isStreaming = false;
    setSendEnabled(true);
    setStatus('online', 'Ready');
}

function setSendEnabled(enabled) {
    sendBtnMain.disabled = !enabled;
    sendBtnChat.disabled = !enabled;
}

/* --- Conversation: enter chat mode --- */
function enterConversationMode() {
    if (!isInConversation) {
        isInConversation = true;
        welcomeScreen.style.display = 'none';
        messagesEl.style.display = 'flex';
        chatInputBar.style.display = 'block';
        messagesEl.innerHTML = '';
    }
}

function showWelcomeScreen() {
    isInConversation = false;
    activeConversationId = 0;
    client.conversationId = 0;
    messagesEl.style.display = 'none';
    chatInputBar.style.display = 'none';
    welcomeScreen.style.display = 'flex';
    messagesEl.innerHTML = '';
    inputMain.value = '';
    inputChat.value = '';
    toolManager.clear();
    toolManager.hide();
    currentAssistantMsg = null;
    setStatus('online', 'Ready');
}

/* --- Send message --- */
function sendMessage() {
    const input = isInConversation ? inputChat : inputMain;
    const msg = input.value.trim();
    if (!msg || isStreaming) return;

    input.value = '';
    isStreaming = true;
    setSendEnabled(false);
    setStatus('streaming', 'Processing...');
    toolManager.clear();
    toolManager.hide();
    currentAssistantMsg = null;

    enterConversationMode();

    addMessage('user', msg);

    client.sendMessage(msg, {
        onText(content) {
            if (!currentAssistantMsg) {
                currentAssistantMsg = addMessage('assistant', '');
            }
            currentAssistantMsg.textContent += content;
            contentArea.scrollTop = contentArea.scrollHeight;
        },

        onPlanCreated(event) {
            if (event.steps > 0) {
                toolManager.show();
            }
        },

        onToolProgress(event) {
            if (event.status === 'running') {
                toolManager.startTool(event.tool_name, event.tool_args, event.current_step, event.total_steps);
            } else {
                toolManager.updateTool(event.tool_name, event.current_step, event.total_steps, event.status);
            }
        },

        onToolCall(event) {},

        onToolResult(event) {},

        onThinking(content) {
            setStatus('streaming', 'Thinking...');
        },

        onError(error) {
            addMessage('error-message', `Error: ${error}`);
            resetAfterResponse();
        },

        onDone(event) {
            activeConversationId = event.conversation_id || activeConversationId;
            if (!currentAssistantMsg) {
                addMessage('assistant', '(Empty response)');
            }
            resetAfterResponse();
        },
    });
}

/* --- Event bindings --- */
sendBtnMain.addEventListener('click', sendMessage);
sendBtnChat.addEventListener('click', sendMessage);

inputMain.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

inputChat.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textareas
[inputMain, inputChat].forEach(input => {
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 160) + 'px';
    });
});

// New Chat button
btnNewChat.addEventListener('click', () => {
    if (isStreaming) client.cancel();
    showWelcomeScreen();
});

// Feature cards
featureCards.forEach(card => {
    card.addEventListener('click', () => {
        const action = card.dataset.action;
        const input = isInConversation ? inputChat : inputMain;
        input.value = action + ': ';
        input.focus();
    });
});

// Model selector dropdown
inputModelSelector.addEventListener('click', (e) => {
    e.stopPropagation();
    const isVisible = modelDropdown.style.display !== 'none';
    modelDropdown.style.display = isVisible ? 'none' : 'block';
});

document.querySelectorAll('.model-dropdown-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedModel = item.dataset.model;
        selectedProvider = item.dataset.provider;
        inputModelName.textContent = item.querySelector('.model-dropdown-label').textContent;

        // Update active state
        document.querySelectorAll('.model-dropdown-item').forEach(i => {
            i.classList.remove('active');
            i.querySelector('.model-dropdown-check').textContent = '';
        });
        item.classList.add('active');
        item.querySelector('.model-dropdown-check').textContent = '✓';

        modelDropdown.style.display = 'none';
    });
});

// Close dropdown on outside click
document.addEventListener('click', () => {
    modelDropdown.style.display = 'none';
});

// Tool panel close
toolPanelClose.addEventListener('click', () => {
    toolManager.hide();
});

// Sidebar navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
    });
});

// Sidebar history items
document.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        const title = item.querySelector('.history-title').textContent;
        if (isStreaming) client.cancel();
        enterConversationMode();
        addMessage('assistant', `Loaded conversation: "${title}"`);
        isInConversation = true;
        setStatus('online', 'Ready');
    });
});

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
    });
});

// Greeting text: update time-of-day
(function updateGreeting() {
    const hour = new Date().getHours();
    let timeOfDay = 'Morning';
    if (hour >= 12 && hour < 17) timeOfDay = 'Afternoon';
    else if (hour >= 17 || hour < 5) timeOfDay = 'Evening';
    const titleEl = document.getElementById('greeting-title');
    if (titleEl) {
        titleEl.textContent = `Good ${timeOfDay}`;
    }
})();

/* --- Auto-login --- */
(async () => {
    const ok = await client.init();
    if (ok) {
        setStatus('online', 'Ready');
        setSendEnabled(true);
    } else {
        setStatus('offline', 'Login failed');
    }
})();
