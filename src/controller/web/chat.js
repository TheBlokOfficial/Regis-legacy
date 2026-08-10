/**
 * Regis — Panel Kontrolny | chat.js
 *
 * Moduł czatu i obsługi sesji konwersacyjnych z Kontrolerem Regis.
 * Wspiera odczytywanie pełnej historii sesji (zarówno głosu z Satelit jak i tekstu z Web UI)
 * oraz strumieniowanie odpowiedzi w czasie rzeczywistym.
 */

import { escHtml } from './utils.js';
import { showToast, withLoadingState } from './renderer.js';

let _activeSatelliteId = "web_ui";
let _activeRoom = "";
export let isChatStreaming = false;

export function initChat() {
    _bindTabs();
    _bindChatForm();
    _bindSatelliteSelect();
    _bindChatEvents();
    loadSatellitesForSelect();
    loadSessionHistory(_activeSatelliteId);
}

export function resolveToolDisplayName(toolName, args) {
    if (!toolName) return "Akcja agenta";

    let parsedArgs = args || {};
    if (typeof parsedArgs === "string") {
        try { parsedArgs = JSON.parse(parsedArgs); } catch (_) {}
    }

    if (toolName === "execute_action") {
        const act = parsedArgs.action || "akcja";
        let entStr = "";
        if (parsedArgs.entity_id) {
            entStr = Array.isArray(parsedArgs.entity_id) ? parsedArgs.entity_id.join(", ") : String(parsedArgs.entity_id);
        }
        return `Wykonanie akcji: ${act}${entStr ? ` na ${entStr}` : ""}`;
    }

    if (toolName === "get_device_state") {
        let entStr = "";
        if (parsedArgs.entity_id) {
            entStr = Array.isArray(parsedArgs.entity_id) ? parsedArgs.entity_id.join(", ") : String(parsedArgs.entity_id);
        }
        return `Odczyt stanu urządzeń${entStr ? `: ${entStr}` : ""}`;
    }

    if (toolName === "search_devices") {
        const q = parsedArgs.query || parsedArgs.text || "";
        return `Wyszukiwanie urządzeń${q ? `: ${q}` : ""}`;
    }

    if (toolName === "get_system_status") {
        return "Sprawdzenie statusu systemu i węzłów";
    }

    const cleanName = toolName.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
    return `Akcja: ${cleanName}`;
}

export function createToolChipHtml(name, args, result) {
    const friendlyTitle = resolveToolDisplayName(name, args);
    
    let argsJsonStr = "";
    try {
        argsJsonStr = typeof args === "object" ? JSON.stringify(args, null, 2) : String(args);
    } catch (_) { argsJsonStr = String(args); }

    let resultJsonStr = "";
    if (result !== null && result !== undefined) {
        try {
            const parsed = typeof result === "string" ? JSON.parse(result) : result;
            resultJsonStr = JSON.stringify(parsed, null, 2);
        } catch (_) { resultJsonStr = String(result); }
    }

    const svgIcon = `<svg class="icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;

    return `
        <div class="tool-call-line">
            <span class="tool-line-icon">${svgIcon}</span>
            <button type="button" class="tool-chip-pill" 
                data-tool-name="${escHtml(name)}"
                data-friendly-title="${escHtml(friendlyTitle)}"
                data-input-payload="${escHtml(argsJsonStr)}"
                data-output-result="${escHtml(resultJsonStr || 'Oczekiwanie na wynik...')}">
                ${escHtml(friendlyTitle)} ↗
            </button>
        </div>
    `;
}

function _bindChatEvents() {
    const container = document.getElementById("chat-messages");
    if (container) {
        container.addEventListener("click", (e) => {
            const chip = e.target.closest(".suggestion-chip");
            const retryBtn = e.target.closest(".btn-retry-turn");
            const toolPill = e.target.closest(".tool-chip-pill");

            if (toolPill) {
                _openInspector(toolPill);
                return;
            }

            const target = chip || retryBtn;
            if (!target) return;

            const prompt = target.getAttribute("data-prompt");
            const input = document.getElementById("chat-input");
            const form = document.getElementById("chat-form");
            if (input && form && prompt) {
                input.value = prompt;
                form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
            }
        });
    }

    const closeBtn = document.getElementById("btn-close-inspector");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            _closeInspector();
        });
    }
}

function _openInspector(chip) {
    const panel = document.getElementById("chat-inspector-panel");
    const badge = document.getElementById("inspector-badge");
    const title = document.getElementById("inspector-title");
    const inputCode = document.getElementById("inspector-input-code");
    const outputCode = document.getElementById("inspector-output-code");

    if (!panel) return;

    const name = chip.getAttribute("data-tool-name") || "tool";
    const friendlyTitle = chip.getAttribute("data-friendly-title") || "Szczegóły Wykonania";
    const inputPayload = chip.getAttribute("data-input-payload") || "{}";
    const outputResult = chip.getAttribute("data-output-result") || "{}";

    if (badge) badge.textContent = name;
    if (title) title.textContent = friendlyTitle;
    if (inputCode) inputCode.textContent = inputPayload;
    if (outputCode) outputCode.textContent = outputResult;

    panel.classList.add("open");
}

function _closeInspector() {
    const panel = document.getElementById("chat-inspector-panel");
    if (panel) panel.classList.remove("open");
}

function _renderAssistantError(container, text, errorMsg) {
    const errDiv = document.createElement("div");
    errDiv.className = "msg-wrapper assistant-error";
    errDiv.innerHTML = `
        <div class="engine-error-card">
            <span class="engine-error-text">Błąd silnika agenta: ${escHtml(errorMsg)}</span>
            <button type="button" class="btn-retry-turn" data-prompt="${escHtml(text)}">Ponów zapytanie do agenta</button>
        </div>
    `;
    container.appendChild(errDiv);
    _scrollToBottom();
}

function _bindTabs() {
    const btnDashboard = document.getElementById("tab-btn-dashboard");
    const btnChat      = document.getElementById("tab-btn-chat");
    const viewDash     = document.getElementById("view-dashboard");
    const viewChat     = document.getElementById("view-chat");

    if (btnDashboard && btnChat) {
        btnDashboard.addEventListener("click", () => {
            btnDashboard.classList.add("active");
            btnChat.classList.remove("active");
            viewDash.style.display = "flex";
            viewChat.style.display = "none";
        });

        btnChat.addEventListener("click", () => {
            btnChat.classList.add("active");
            btnDashboard.classList.remove("active");
            viewDash.style.display = "none";
            viewChat.style.display = "flex";
            loadSatellitesForSelect();
            loadSessionHistory(_activeSatelliteId);
        });
    }
}

function _bindSatelliteSelect() {
    const container = document.getElementById("chat-session-pills");
    if (!container) return;

    container.addEventListener("click", (e) => {
        const pill = e.target.closest(".session-pill");
        if (!pill || pill.classList.contains("active")) return;

        const allPills = container.querySelectorAll(".session-pill");
        allPills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");

        _activeSatelliteId = pill.getAttribute("data-value") || "web_ui";
        _activeRoom = pill.getAttribute("data-room") || "";
        loadSessionHistory(_activeSatelliteId);
    });
}

/**
 * Ładuje aktywne sesje i zarejestrowane satelity do przełącznika pigułkowego.
 */
export async function loadSatellitesForSelect() {
    const container = document.getElementById("chat-session-pills");
    if (!container) return;

    try {
        const [statusResp, sessionsResp] = await Promise.all([
            fetch("/api/status").catch(() => null),
            fetch("/v1/sessions").catch(() => null)
        ]);

        let satellitesList = [];
        if (statusResp && statusResp.ok) {
            const statusData = await statusResp.json();
            satellitesList = statusData.satellites || [];
        }

        let activeSessionsList = [];
        if (sessionsResp && sessionsResp.ok) {
            const sessionsData = await sessionsResp.json();
            activeSessionsList = sessionsData.sessions || [];
        }

        const satMap = {};
        satellitesList.forEach(s => { satMap[s.id] = s; });

        const sessionMap = {};
        activeSessionsList.forEach(sess => {
            const sId = sess.satellite_id || sess.id;
            if (sId) sessionMap[sId] = sess;
        });

        const allIds = new Set([...Object.keys(satMap), ...Object.keys(sessionMap)]);
        allIds.delete("web_ui");

        container.innerHTML = "";

        // Pigułka Domyślna: Web UI
        const webPill = document.createElement("button");
        webPill.className = `session-pill${_activeSatelliteId === "web_ui" ? " active" : ""}`;
        webPill.setAttribute("data-value", "web_ui");
        webPill.setAttribute("data-room", "");
        webPill.innerHTML = `<svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/></svg> Web UI`;
        container.appendChild(webPill);

        allIds.forEach(id => {
            const satInfo = satMap[id];
            const roomStr = satInfo && satInfo.room ? satInfo.room : id;

            const pill = document.createElement("button");
            pill.className = `session-pill${_activeSatelliteId === id ? " active" : ""}`;
            pill.setAttribute("data-value", id);
            pill.setAttribute("data-room", satInfo ? satInfo.room || "" : "");
            pill.innerHTML = `<svg class="icon-svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg> ${escHtml(roomStr)}`;
            container.appendChild(pill);
        });

        if (!container.querySelector(".session-pill.active")) {
            webPill.classList.add("active");
            _activeSatelliteId = "web_ui";
        }
    } catch (e) {
        console.error("Błąd pobierania listy sesji/satelit:", e);
    }
}

/**
 * Pobiera i renderuje pełną historię wiadomości danej sesji z Kontrolera.
 */
export async function loadSessionHistory(satelliteId) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    try {
        const resp = await fetch(`/v1/chat/history?satellite_id=${encodeURIComponent(satelliteId)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const history = data.history || [];

        renderFullHistory(history);
    } catch (e) {
        console.error("Błąd ładowania historii:", e);
    }
}

/**
 * Renderuje całą listę komunikatów sesji.
 * Scalają akcje narządzi z ich wynikami i eliminuje puste czarne ramki.
 */
export function renderFullHistory(history) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    container.innerHTML = "";
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="chat-hero-section">
                <div class="hero-icon">
                    <svg class="hero-svg" viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="#666666" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4M8 15h.01M16 15h.01"/></svg>
                </div>
                <h1 class="hero-title">REGIS AI</h1>
                <p class="hero-subtitle">Asystent Domowy &amp; Agent Voice-First</p>
                <div class="hero-suggestions">
                    <button class="suggestion-chip" data-prompt="Włącz światło w salonie">
                        <svg class="chip-svg" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.8.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6M10 22h4"/></svg>
                        Włącz światło
                    </button>
                    <button class="suggestion-chip" data-prompt="Jaka jest dzisiaj pogoda i temperatura?">
                        <svg class="chip-svg" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
                        Stan pogody
                    </button>
                    <button class="suggestion-chip" data-prompt="Pokaż status zarejestrowanych klientów i satelit">
                        <svg class="chip-svg" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                        Status węzłów
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // 1. Dwuprzebiegowe zbieranie wyników z komunikatów role === "tool" (obsługujące id oraz kolejkę nazw)
    const toolResultsMap = {};
    const toolResultsQueue = {};
    history.forEach(msg => {
        if (msg && msg.role === "tool") {
            if (msg.tool_call_id) toolResultsMap[msg.tool_call_id] = msg.content;
            const name = msg.name || "tool";
            if (!toolResultsQueue[name]) toolResultsQueue[name] = [];
            toolResultsQueue[name].push(msg.content);
        }
    });

    // 2. Renderowanie wiadomości dokładnie w kolejności chronologicznej
    history.forEach(msg => {
        if (!msg || !msg.role) return;

        if (msg.role === "user") {
            const uMsg = document.createElement("div");
            uMsg.className = "msg-wrapper user";
            const roomStr = msg.room ? ` · ${msg.room}` : "";
            uMsg.innerHTML = `
                <div class="msg-user-card">
                    <span class="msg-user-text">${escHtml(msg.content || "")}</span>
                    <span class="msg-user-meta">${escHtml(formatTimestamp(msg.timestamp) + roomStr)}</span>
                </div>
            `;
            container.appendChild(uMsg);
        } else if (msg.role === "assistant") {
            // A. Wywołania narzędzi jako eleganckie pojedyncze chipy
            if (msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
                msg.tool_calls.forEach(tc => {
                    const fn = tc.function || tc || {};
                    const name = fn.name || tc.name || "tool";
                    const args = fn.arguments || tc.arguments || {};
                    const callId = tc.id || tc.tool_call_id || name;
                    let result = callId ? toolResultsMap[callId] : null;
                    if (!result && toolResultsQueue[name] && toolResultsQueue[name].length > 0) {
                        result = toolResultsQueue[name].shift();
                    }

                    const tMsg = document.createElement("div");
                    tMsg.className = "msg-wrapper assistant-tools";
                    tMsg.innerHTML = createToolChipHtml(name, args, result);
                    container.appendChild(tMsg);
                });
            }

            // B. Treść odpowiedzi agenta
            if (msg.content && msg.content.trim()) {
                const aMsg = document.createElement("div");
                aMsg.className = "msg-wrapper assistant";
                aMsg.innerHTML = `<div class="msg-assistant-content">${escHtml(msg.content)}</div>`;
                container.appendChild(aMsg);
            }
        }
    });

    _scrollToBottom();
}

function _formatDuration(ms) {
    if (!ms || ms <= 0) return "";
    return ms >= 1000 ? (ms / 1000).toFixed(1) + "s" : ms + "ms";
}

export function formatAssistantMeta(turn) {
    const parts = [];

    const modelStr = turn.model ? ` (${turn.model})` : "";
    parts.push(`Regis${modelStr}`);

    const toolCount = turn.tools ? turn.tools.length : (turn.tool_count || 0);
    if (toolCount > 0) {
        const label = toolCount === 1 ? "narzędzie" : (toolCount < 5 ? "narzędzia" : "narzędzi");
        parts.push(`${toolCount} ${label}`);
    }

    if (turn.elapsed_ms) {
        parts.push(_formatDuration(turn.elapsed_ms));
    }

    const profiler = turn.profiler || {};
    const profParts = [];
    if (profiler.stt) profParts.push(`STT: ${_formatDuration(profiler.stt)}`);
    if (profiler.llm_ttft) profParts.push(`TTFT: ${_formatDuration(profiler.llm_ttft)}`);
    if (profiler.llm_gen) profParts.push(`Gen: ${_formatDuration(profiler.llm_gen)}`);
    if (profiler.tools) profParts.push(`Narzędzia: ${_formatDuration(profiler.tools)}`);

    if (profParts.length > 0) {
        parts.push(`[${profParts.join(" | ")}]`);
    }

    if (turn.timestamp) {
        parts.push(turn.timestamp);
    }

    return parts.join(" · ");
}

export function getActiveSatelliteId() {
    return _activeSatelliteId;
}

export function formatTimestamp(ts) {
    if (!ts) return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    try {
        if (typeof ts === "string" && ts.includes(":")) {
            const parts = ts.split("T").pop().split(":");
            if (parts.length >= 2) {
                return `${parts[0]}:${parts[1]}`;
            }
        }
        const d = new Date(ts);
        if (!isNaN(d.getTime())) {
            const hrs = String(d.getHours()).padStart(2, "0");
            const mins = String(d.getMinutes()).padStart(2, "0");
            return `${hrs}:${mins}`;
        }
    } catch (_) {}
    return String(ts).slice(0, 5);
}

/**
 * Elastyczne dodawanie wiadomości/tury do aktywnego widoku czatu.
 */
export function appendTurnToChat(turn) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    const hero = container.querySelector(".chat-hero-section");
    if (hero) hero.remove();
    const empty = container.querySelector(".empty-state");
    if (empty) empty.remove();

    // Jeśli otrzymujemy pojedynczy obiekt wiadomości sesji (role: user/assistant)
    if (turn.role) {
        renderFullHistory([turn]);
        return;
    }

    // Jeśli otrzymujemy zbiorczy obiekt tury
    if (turn.user) {
        const uMsg = document.createElement("div");
        uMsg.className = "msg-wrapper user";
        uMsg.innerHTML = `
            <div class="msg-user-card">
                <span class="msg-user-text">${escHtml(turn.user)}</span>
                <span class="msg-user-meta">${escHtml(formatTimestamp(turn.timestamp))}</span>
            </div>
        `;
        container.appendChild(uMsg);
    }

    if (turn.assistant) {
        const aMsg = document.createElement("div");
        aMsg.className = "msg-wrapper assistant";
        const metaStr = formatAssistantMeta(turn);
        const hasContent = Boolean(turn.assistant && turn.assistant.trim());
        const contentHtml = hasContent ? `<div class="msg-assistant-content">${escHtml(turn.assistant)}</div>` : "";

        aMsg.innerHTML = `
            ${contentHtml}
            <div class="msg-meta">${escHtml(metaStr)}</div>
        `;
        container.appendChild(aMsg);
    }

    _scrollToBottom();
}

function _bindChatForm() {
    const form  = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    if (!form || !input) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        const sendBtn = document.getElementById("chat-send-btn");
        
        await withLoadingState(sendBtn, async () => {
            input.disabled = true;
            input.value = "";
            const now = new Date().toLocaleTimeString();

            // 1. Dodaj kartę komendy użytkownika
            appendTurnToChat({ user: text, timestamp: now });

            const container = document.getElementById("chat-messages");
            let streamingBubble = null;
            let fullText = "";
            let pendingToolChips = [];

            isChatStreaming = true;

            try {
                const resp = await fetch("/v1/chat/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        message: text,
                        satellite_id: _activeSatelliteId,
                        room: _activeRoom || null
                    })
                });

                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

                const reader = resp.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        if (buffer.trim()) {
                            let line = buffer.trim();
                            if (line.startsWith("data: ")) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    if (data.type === "done") {
                                        if (streamingBubble && !fullText) streamingBubble.textContent = data.content;
                                    }
                                } catch (_) {}
                            }
                        }
                        break;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop();

                    for (let line of lines) {
                        line = line.trim();
                        if (line.startsWith("data: ")) {
                            try {
                                const data = JSON.parse(line.slice(6));

                                if (data.type === "tool_call") {
                                    const tcData = data.content || {};
                                    const fnName = tcData.name || "tool";
                                    const fnArgs = tcData.arguments || {};

                                    const tMsg = document.createElement("div");
                                    tMsg.className = "msg-wrapper assistant-tools";
                                    tMsg.innerHTML = createToolChipHtml(fnName, fnArgs, null);
                                    container.appendChild(tMsg);
                                    const pill = tMsg.querySelector(".tool-chip-pill");
                                    if (pill) pendingToolChips.push({ name: fnName, pill });
                                    _scrollToBottom();
                                } else if (data.type === "tool_result") {
                                    const trData = data.content || {};
                                    const fnName = trData.name || "tool";
                                    const resStr = trData.result || trData.content || "";

                                    const matchIdx = pendingToolChips.findIndex(item => item.name === fnName);
                                    const item = matchIdx !== -1 ? pendingToolChips.splice(matchIdx, 1)[0] : pendingToolChips.shift();

                                    if (item && item.pill) {
                                        let parsedStr = resStr;
                                        try {
                                            const parsed = typeof resStr === "string" ? JSON.parse(resStr) : resStr;
                                            parsedStr = JSON.stringify(parsed, null, 2);
                                        } catch (_) {}
                                        item.pill.setAttribute("data-output-result", parsedStr);
                                    }
                                } else if (data.type === "content") {
                                    // Tworzymy wiersz tekstowy odpowiedzi agenta przy pierwszej porcji tekstu
                                    if (!streamingBubble) {
                                        const aMsg = document.createElement("div");
                                        aMsg.className = "msg-wrapper assistant";
                                        streamingBubble = document.createElement("div");
                                        streamingBubble.className = "msg-assistant-content";
                                        aMsg.appendChild(streamingBubble);
                                        container.appendChild(aMsg);
                                    }
                                    fullText += data.content;
                                    streamingBubble.textContent = fullText;
                                    _scrollToBottom();
                                } else if (data.type === "error") {
                                    if (streamingBubble) {
                                        streamingBubble.textContent = `[Błąd: ${data.content}]`;
                                    } else {
                                        _renderAssistantError(container, text, data.content || "Awaria silnika agenta");
                                    }
                                    showToast(`Błąd silnika agenta: ${data.content}`, "error");
                                } else if (data.type === "done") {
                                    if (streamingBubble && !fullText) streamingBubble.textContent = data.content || fullText;
                                }
                            } catch (_) {}
                        }
                    }
                }
            } catch (e) {
                if (streamingBubble) {
                    streamingBubble.textContent = `[Błąd: ${e.message}]`;
                } else {
                    _renderAssistantError(container, text, e.message || "Brak połączenia z silnikiem LLM");
                }
                showToast(`Błąd wykonania silnika agenta: ${e.message}`, "error");
            } finally {
                isChatStreaming = false;
                input.disabled = false;
                input.focus();
                loadSatellitesForSelect();
            }
        });
    });
}

function _bindClearButton() {
    const btn = document.getElementById("clear-chat-btn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
        if (!confirm("Czy na pewno chcesz wyczyścić historię tej sesji?")) return;
        await withLoadingState(btn, async () => {
            try {
                const resp = await fetch(`/v1/clear_history?satellite_id=${encodeURIComponent(_activeSatelliteId)}`, { method: "POST" });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                showToast("Historia sesji została wyczyszczona.", "success");
                await loadSessionHistory(_activeSatelliteId);
                await loadSatellitesForSelect();
            } catch (e) {
                showToast(`Błąd czyszczenia historii: ${e.message}`, "error");
            }
        });
    });
}

function _scrollToBottom() {
    const container = document.getElementById("chat-messages");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}
