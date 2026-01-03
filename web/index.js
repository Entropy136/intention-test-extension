const noMessagePrompt = document.getElementById('no-message');
const chatContainer = document.getElementById('chat-container');
const toolbar = document.getElementById('toolbar');
const statusPill = document.querySelector('.status-pill');
const body = document.body;
const SCROLL_IDLE_WINDOW_MS = 3000;
const defaultNoMessageMarkup = noMessagePrompt.innerHTML;
const waitingNoMessageMarkup = `
    <h1>Intention Test 🧪</h1>
    <div>正在等待新的响应...</div>
`.trim();
const SessionState = {
    IDLE: 'idle',
    RUNNING: 'running',
    STOPPING: 'stopping',
    STOPPED: 'stopped'
};

let messageCount = 0;
let lastUserScrollTime = Date.now();
let sessionState = SessionState.IDLE;
let scrollLockEnabled = false;

const canConnectToVsCode = typeof acquireVsCodeApi === 'function';
if (canConnectToVsCode) {
    window.vscode = acquireVsCodeApi();
}

// 初始化时将 lastUserScrollTime 设为过去，方便首条消息也能自动滚动
lastUserScrollTime = Date.now() - SCROLL_IDLE_WINDOW_MS - 100;

const toolbarHandlers = {
    'clear-chat': requestClearConversation,
    'stop-run': requestStopConversation,
    'jump-latest': scrollToLatest,
    'toggle-scroll-lock': toggleScrollLock
};

toolbar?.querySelectorAll('[data-action]').forEach((button) => {
    const action = button.dataset.action;
    const handler = action ? toolbarHandlers[action] : undefined;
    if (handler) {
        button.addEventListener('click', handler);
    }
});
updateToolbarState();
reflectStatusPill();
updatePlaceholderVisibility();

const updateLastScrollTime = () => {
    lastUserScrollTime = Date.now();
};

window.addEventListener('wheel', updateLastScrollTime, { passive: true });
window.addEventListener('mousedown', updateLastScrollTime);
window.addEventListener('scroll', updateLastScrollTime, { passive: true });
window.addEventListener('touchstart', updateLastScrollTime, { passive: true });

window.addEventListener('message', handleIncomingMessage);

function scrollToLatest() {
    window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: 'smooth'
    });
}

function maybeAutoScroll() {
    if (scrollLockEnabled) {
        return;
    }
    const nearBottom =
        window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 80;
    const userIdle = Date.now() - lastUserScrollTime > SCROLL_IDLE_WINDOW_MS;
    if (nearBottom || userIdle) {
        scrollToLatest();
    }
}

function trimConversationTo(targetCount = 0) {
    const normalized = Math.max(0, Number.isFinite(targetCount) ? Math.trunc(targetCount) : 0);
    messageCount = normalized;
    const nodesToKeep = normalized * 2;
    while (chatContainer.children.length > nodesToKeep) {
        chatContainer.removeChild(chatContainer.lastChild);
    }
    if (normalized === 0) {
        removeTypingAnimation();
    }
    updatePlaceholderVisibility();
}

function requestClearConversation() {
    window.vscode?.postMessage({ cmd: 'clear-chat' });
    trimConversationTo(0);
}

function requestStopConversation() {
    if (sessionState !== SessionState.RUNNING) {
        addSystemNotice('当前没有正在运行的请求。');
        return;
    }
    setSessionState(SessionState.STOPPING);
    addSystemNotice('正在尝试停止当前生成...');
    window.vscode?.postMessage({ cmd: 'stop-run' });
}

function toggleScrollLock() {
    scrollLockEnabled = !scrollLockEnabled;
    updateToolbarState();
    if (scrollLockEnabled) {
        addSystemNotice('已锁定阅读，停止自动滚动。');
    } else {
        addSystemNotice('已解除锁定，将自动滚动到最新。');
        maybeAutoScroll();
    }
}

function setSessionState(nextState) {
    if (!nextState) {
        return;
    }
    sessionState = nextState;
    if (nextState !== SessionState.RUNNING) {
        removeTypingAnimation();
    }
    updateToolbarState();
    updatePlaceholderVisibility();
    reflectStatusPill();
}

function updateToolbarState() {
    if (!toolbar) {
        return;
    }
    const stopButton = toolbar.querySelector('[data-action="stop-run"]');
    if (stopButton) {
        const isStopping = sessionState === SessionState.STOPPING;
        const canStop = sessionState === SessionState.RUNNING;
        stopButton.disabled = !canStop;
        stopButton.textContent = isStopping ? '停止中…' : '停止';
    }

    const scrollLockButton = toolbar.querySelector('[data-action="toggle-scroll-lock"]');
    if (scrollLockButton) {
        scrollLockButton.dataset.locked = String(scrollLockEnabled);
        scrollLockButton.textContent = scrollLockEnabled ? '解除锁定' : '阅读锁定';
    }
}

function updatePlaceholderVisibility() {
    const hasMessages = chatContainer.children.length > 0;
    if (hasMessages) {
        noMessagePrompt.style.display = 'none';
        return;
    }
    if (sessionState === SessionState.RUNNING || sessionState === SessionState.STOPPING) {
        noMessagePrompt.innerHTML = waitingNoMessageMarkup;
    } else {
        noMessagePrompt.innerHTML = defaultNoMessageMarkup;
    }
    noMessagePrompt.style.display = 'block';
}

function addSystemNotice(message) {
    addMessage(message, 'system', { senderType: 'system' });
}

function reflectStatusPill() {
    if (!statusPill) {
        return;
    }
    let text = 'Idle';
    let stateAttr = 'idle';
    if (sessionState === SessionState.RUNNING) {
        text = 'Running';
        stateAttr = 'running';
    } else if (sessionState === SessionState.STOPPING) {
        text = 'Stopping…';
        stateAttr = 'stopping';
    } else if (sessionState === SessionState.STOPPED) {
        text = 'Stopped';
        stateAttr = 'stopped';
    }
    statusPill.dataset.state = stateAttr;
    const textNode = statusPill.querySelector('.status-text');
    if (textNode) {
        textNode.textContent = text;
    }
}

function createMessageContent(message, isHtml) {
    const messageContentElement = document.createElement('div');
    messageContentElement.className = 'message-content';
    if (isHtml) {
        if (typeof DOMPurify === 'undefined') {
            messageContentElement.textContent = message;
        } else {
            messageContentElement.innerHTML = DOMPurify.sanitize(message, { USE_PROFILES: { html: true } });
        }
    } else {
        messageContentElement.textContent = message;
    }
    return messageContentElement;
}

function capitalize(label) {
    if (!label) {
        return '';
    }
    return label[0].toUpperCase() + label.substring(1);
}

function addMessage(message, sender, options = {}) {
    const {
        raw = '',
        isHtml = false,
        senderType,
        extraClasses = [],
        enhance = true
    } = options;

    const messageContentElement = createMessageContent(message, isHtml);

    const messageElement = document.createElement('div');
    messageElement.appendChild(messageContentElement);
    messageElement.dataset.raw = raw ?? '';

    const classNames = ['message', sender, ...extraClasses];
    messageElement.className = classNames.filter(Boolean).join(' ');

    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    const label = senderType ?? sender;
    messageHeader.textContent = capitalize(label);

    chatContainer.appendChild(messageHeader);
    chatContainer.appendChild(messageElement);

    messageElement.index = messageCount;

    if (enhance) {
        enhanceMessageElement(messageElement);
    }

    maybeAutoScroll();
    updatePlaceholderVisibility();
    return messageElement;
}

function enhanceMessageElement(messageElement) {
    const codeBlocks = messageElement.querySelectorAll('pre code');
    codeBlocks.forEach((block) => {
        hljs.highlightElement(block);
    });

    messageElement.querySelectorAll('code').forEach((inlineCode) => {
        if (inlineCode.parentElement?.tagName.toLowerCase() !== 'pre') {
            hljs.highlightElement(inlineCode);
        }
    });
}

function showTypingAnimation(sender) {
    addMessage('<div><span></span><span></span><span></span></div>', sender, {
        isHtml: true,
        senderType: sender,
        extraClasses: ['typing'],
        enhance: false
    });
}

function completeTypingAnimation(message, sender, options = {}) {
    const typingElement = document.querySelector('.message.typing');
    if (!typingElement) {
        return undefined;
    }

    typingElement.className = ['message', sender].join(' ').trim();
    typingElement.dataset.raw = options.raw ?? '';
    typingElement.innerHTML = '';

    const messageContentElement = createMessageContent(message, options.isHtml ?? false);
    typingElement.appendChild(messageContentElement);

    if (options.enhance !== false) {
        enhanceMessageElement(typingElement);
    }

    typingElement.index = messageCount;
    maybeAutoScroll();
    updatePlaceholderVisibility();
    return typingElement;
}

function removeTypingAnimation() {
    const typingElement = document.querySelector('.message.typing');
    if (typingElement) {
        const header = typingElement.previousSibling;
        if (header && header.classList?.contains('message-header')) {
            chatContainer.removeChild(header);
        }
        chatContainer.removeChild(typingElement);
        updatePlaceholderVisibility();
    }
}

function handleIncomingMessage(event) {
    const msg = event.data;
    if (msg?.role && msg?.content) {
        noMessagePrompt.style.display = 'none';

        const waitSuffix = '-wait';
        const isWaiting = msg.role.endsWith(waitSuffix);
        const senderRole = isWaiting ? msg.role.slice(0, -waitSuffix.length) : msg.role;

        if (isWaiting) {
            showTypingAnimation(senderRole);
            return;
        }

        const rawContent = typeof msg.raw === 'string' ? msg.raw : msg.content;
        const messageElement =
            completeTypingAnimation(msg.content, senderRole, { raw: rawContent, isHtml: true }) ??
            addMessage(msg.content, senderRole, {
                raw: rawContent,
                isHtml: true,
                senderType: msg.senderType ?? senderRole
            });

        if (messageElement) {
            messageCount += 1;
        }
        return;
    }

    if (!msg?.cmd) {
        return;
    }

    if (msg.cmd === 'session-state') {
        const nextState = msg.state ?? SessionState.IDLE;
        setSessionState(nextState);
        if (typeof msg.message === 'string' && msg.message.trim().length > 0) {
            addSystemNotice(msg.message);
        } else if (nextState === SessionState.STOPPED) {
            addSystemNotice('生成已停止，不再继续。');
        }
    } else if (msg.cmd === 'error') {
        console.error('[IntentionTest] Webview error message received:', msg);
    } else if (msg.cmd === 'clear') {
        trimConversationTo(msg.toIndex ?? 0);
    }
}
