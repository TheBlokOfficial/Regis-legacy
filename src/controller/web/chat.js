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
    _bindClearButton();
    _bindSatelliteSelect();
    loadSatellitesForSelect();
    loadSessionHistory(_activeSatelliteId);
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
    const select = document.getElementById("chat-satellite-select");
    if (!select) return;

    select.addEventListener("change", (e) => {
        _activeSatelliteId = e.target.value;
        const opt = select.options[select.selectedIndex];
        _activeRoom = opt ? opt.getAttribute("data-room") || "" : "";
        loadSessionHistory(_activeSatelliteId);
    });
}

/**
 * Ładuje aktywne sesje i zarejestrowane satelity do ujednoliconej, bezpowtórzeniowej listy wyboru.
 */
export async function loadSatellitesForSelect() {
    const select = document.getElementById("chat-satellite-select");
    if (!select) return;

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

        const currentVal = select.value || _activeSatelliteId;
        select.innerHTML = `<option value="web_ui" data-room="">Wirtualna Satelita — Web UI (Klawiatura)</option>`;

        const allIds = new Set([...Object.keys(satMap), ...Object.keys(sessionMap)]);
        allIds.delete("web_ui");

        allIds.forEach(id => {
            const satInfo = satMap[id];
            const sessInfo = sessionMap[id];

            const roomStr = satInfo && satInfo.room ? ` (${satInfo.room})` : "";
            const countStr = sessInfo && sessInfo.turns_count ? ` [${sessInfo.turns_count} wiadomości]` : "";

            const opt = document.createElement("option");
            opt.value = id;
            opt.setAttribute("data-room", satInfo ? satInfo.room || "" : "");
            opt.textContent = `Satelita / Sesja: ${id}${roomStr}${countStr}`;
            select.appendChild(opt);
        });

        select.value = currentVal;
        if (select.selectedIndex === -1) {
            select.value = "web_ui";
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
        container.innerHTML = `<p class="empty-state" style="text-align:center; padding:30px 0;">Brak historii konwersacji w tej sesji.</p>`;
        return;
    }

    // 1. Indeksowanie wyników narzędzi po tool_call_id
    const toolResultsById = {};

    history.forEach(msg => {
        if (msg.role === "tool") {
            if (msg.tool_call_id) {
                toolResultsById[msg.tool_call_id] = msg.content;
            }
        }
    });

    const renderedToolMsgIndexes = new Set();

    // 2. Renderowanie wiadomości z podziałem na role
    history.forEach((msg, idx) => {
        if (!msg || !msg.role) return;

        if (msg.role === "user") {
            const uMsg = document.createElement("div");
            uMsg.className = "msg-wrapper user";
            const roomStr = msg.room ? ` · ${msg.room}` : "";
            uMsg.innerHTML = `
                <div class="msg-bubble">${escHtml(msg.content || "")}</div>
                <div class="msg-meta">${escHtml((msg.timestamp || "") + roomStr)}</div>
            `;
            container.appendChild(uMsg);
        } else if (msg.role === "assistant") {
            const aMsg = document.createElement("div");
            aMsg.className = "msg-wrapper assistant";

            let toolsHtml = "";
            if (msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
                const toolsList = msg.tool_calls.map(tc => {
                    const fn = tc.function || {};
                    const tcId = tc.id;
                    let resContent = tcId ? toolResultsById[tcId] : undefined;
                    
                    // Fallback: dopasowanie kolejnego komunikatu role="tool" o tej samej nazwie
                    if (resContent === undefined) {
                        const nextIdx = history.findIndex((m, i) => i > idx && m.role === "tool" && m.name === fn.name && !renderedToolMsgIndexes.has(i));
                        if (nextIdx !== -1) {
                            resContent = history[nextIdx].content;
                            renderedToolMsgIndexes.add(nextIdx);
                        }
                    }

                    return {
                        name: fn.name || "tool",
                        arguments: fn.arguments || {},
                        result: resContent
                    };
                });
                toolsHtml = renderToolsBlock(toolsList);
            }

            const hasContent = Boolean(msg.content && msg.content.trim());
            const bubbleHtml = hasContent ? `<div class="msg-bubble">${escHtml(msg.content)}</div>` : "";

            const metaStr = formatAssistantMeta({
                model: msg.model,
                worker_id: msg.worker_id,
                tool_count: msg.tool_calls ? msg.tool_calls.length : 0,
                timestamp: msg.timestamp
            });

            // Zapobieganie tworzeniu pustych ramek bez treści i bez narzędzi
            if (!hasContent && !toolsHtml) return;

            aMsg.innerHTML = `
                ${toolsHtml}
                ${bubbleHtml}
                <div class="msg-meta">${escHtml(metaStr)}</div>
            `;
            container.appendChild(aMsg);
        } else if (msg.role === "tool") {
            // Pomiń jeśli wynik narzędzia został już wyrenderowany wewnątrz bloku assistant
            if (renderedToolMsgIndexes.has(idx) || (msg.tool_call_id && toolResultsById[msg.tool_call_id])) {
                return;
            }

            const tMsg = document.createElement("div");
            tMsg.className = "msg-wrapper tool-result-wrapper";
            let resStr = msg.content || "";
            try {
                const parsed = JSON.parse(resStr);
                resStr = JSON.stringify(parsed, null, 2);
            } catch (_) {}

            tMsg.innerHTML = `
                <details class="tool-call-block" style="margin: 4px 0 8px 0; max-width: 85%;">
                    <summary class="tool-call-summary">
                        <span>⚙️ Wynik narzędzia: <strong>${escHtml(msg.name || "tool")}</strong></span>
                    </summary>
                    <div class="tool-call-result">
                        <div><strong>Wynik Kontrolera:</strong></div>
                        <pre class="result-content">${escHtml(resStr)}</pre>
                    </div>
                </details>
            `;
            container.appendChild(tMsg);
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

    // 1. Tożsamość + Model
    const modelStr = turn.model ? ` (${turn.model})` : "";
    parts.push(`Regis${modelStr}`);

    // 2. Liczba narzędzi
    const toolCount = turn.tools ? turn.tools.length : (turn.tool_count || 0);
    if (toolCount > 0) {
        const label = toolCount === 1 ? "narzędzie" : (toolCount < 5 ? "narzędzia" : "narzędzi");
        parts.push(`${toolCount} ${label}`);
    }

    // 3. Łączny czas wykonania
    if (turn.elapsed_ms) {
        parts.push(_formatDuration(turn.elapsed_ms));
    }

    // 4. Szczegóły telemetrii z Profilera
    const profiler = turn.profiler || {};
    const profParts = [];
    if (profiler.stt) profParts.push(`STT: ${_formatDuration(profiler.stt)}`);
    if (profiler.llm_ttft) profParts.push(`TTFT: ${_formatDuration(profiler.llm_ttft)}`);
    if (profiler.llm_gen) profParts.push(`Gen: ${_formatDuration(profiler.llm_gen)}`);
    if (profiler.tools) profParts.push(`Narzędzia: ${_formatDuration(profiler.tools)}`);

    if (profParts.length > 0) {
        parts.push(`[${profParts.join(" | ")}]`);
    }

    // 5. Timestamp
    if (turn.timestamp) {
        parts.push(turn.timestamp);
    }

    return parts.join(" · ");
}

export function renderToolsBlock(tools) {
    if (!tools || tools.length === 0) return "";

    let html = `<div class="tool-calls-container">`;
    tools.forEach(t => {
        if (!t) return;
        const name = t.name || "tool";
        const thought = t.thought || "";
        let argsStr = "";
        if (t.arguments) {
            if (typeof t.arguments === "object") {
                argsStr = Object.entries(t.arguments).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
            } else {
                argsStr = String(t.arguments);
            }
        }

        let resultHtml = "";
        if (t.result !== undefined && t.result !== null && String(t.result).trim() !== "") {
            const resultStr = typeof t.result === "object" ? JSON.stringify(t.result, null, 2) : String(t.result);
            resultHtml = `
                <div class="tool-call-result">
                    <div><strong>Wynik Kontrolera:</strong></div>
                    <pre class="result-content">${escHtml(resultStr)}</pre>
                </div>
            `;
        }

        let thoughtHtml = "";
        if (thought) {
            thoughtHtml = `
                <div class="tool-call-thought">
                    <div><strong>Monolog (Myśl):</strong></div>
                    <pre class="thought-content">${escHtml(thought)}</pre>
                </div>
            `;
        }

        html += `
            <details class="tool-call-block">
                <summary class="tool-call-summary">
                    <span>🛠️</span>
                    <span class="tool-call-name">${escHtml(name)}</span>
                    <span class="tool-call-args">(${escHtml(argsStr)})</span>
                </summary>
                ${thoughtHtml}
                ${resultHtml}
            </details>
        `;
    });
    html += `</div>`;
    return html;
}

export function getActiveSatelliteId() {
    return _activeSatelliteId;
}

/**
 * Elastyczne dodawanie wiadomości/tury do aktywnego widoku czatu.
 */
export function appendTurnToChat(turn) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

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
            <div class="msg-bubble">${escHtml(turn.user)}</div>
            <div class="msg-meta">${escHtml(turn.timestamp || "")}</div>
        `;
        container.appendChild(uMsg);
    }

    if (turn.assistant) {
        const aMsg = document.createElement("div");
        aMsg.className = "msg-wrapper assistant";
        const toolsHtml = renderToolsBlock(turn.tools);
        const metaStr = formatAssistantMeta(turn);
        const hasContent = Boolean(turn.assistant && turn.assistant.trim());
        const bubbleHtml = hasContent ? `<div class="msg-bubble">${escHtml(turn.assistant)}</div>` : "";

        aMsg.innerHTML = `
            ${toolsHtml}
            ${bubbleHtml}
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

            // 1. Pokaż dymek użytkownika
            appendTurnToChat({ user: text, timestamp: now });

            // 2. Przygotuj dymek odpowiedzi do strumieniowania
            const container = document.getElementById("chat-messages");
            const aMsg = document.createElement("div");
            aMsg.className = "msg-wrapper assistant";
            aMsg.innerHTML = `
                <div id="streaming-tools"></div>
                <div class="msg-bubble" id="streaming-bubble">...</div>
                <div class="msg-meta" id="streaming-meta">Regis · generowanie...</div>
            `;
            container.appendChild(aMsg);
            _scrollToBottom();

            const bubble = document.getElementById("streaming-bubble");
            const meta   = document.getElementById("streaming-meta");
            const toolsContainer = document.getElementById("streaming-tools");
            let fullText = "";
            let currentModel = "";
            let usedTools = [];
            let profilerData = {};
            let elapsedMs = null;

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
                                        elapsedMs = data.elapsed_ms || null;
                                        if (bubble && !fullText) bubble.textContent = data.content;
                                        const finalMetaStr = formatAssistantMeta({
                                            model: currentModel,
                                            tools: usedTools,
                                            elapsed_ms: elapsedMs,
                                            profiler: profilerData,
                                            timestamp: now
                                        });
                                        if (meta) meta.textContent = finalMetaStr;
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
                                if (data.type === "routing_info") {
                                    currentModel = data.model || "";
                                    if (meta) meta.textContent = formatAssistantMeta({ model: currentModel, timestamp: "generowanie..." });
                                } else if (data.type === "content") {
                                    fullText += data.content;
                                    if (bubble) bubble.textContent = fullText;
                                    _scrollToBottom();
                                } else if (data.type === "tool_call") {
                                    usedTools.push(data.content);
                                    if (toolsContainer) toolsContainer.innerHTML = renderToolsBlock(usedTools);
                                    _scrollToBottom();
                                } else if (data.type === "tool_result") {
                                    // Use standard array find logic instead of findLast for wider browser support
                                    let lastTool = null;
                                    for (let i = usedTools.length - 1; i >= 0; i--) {
                                        if (usedTools[i].name === data.content.name && !usedTools[i].result) {
                                            lastTool = usedTools[i];
                                            break;
                                        }
                                    }
                                    if (lastTool) {
                                        lastTool.result = data.content.result;
                                    } else {
                                        usedTools.push(data.content);
                                    }
                                    if (toolsContainer) toolsContainer.innerHTML = renderToolsBlock(usedTools);
                                    _scrollToBottom();
                                } else if (data.type === "error") {
                                    if (bubble) bubble.textContent = `[Błąd: ${data.content}]`;
                                    showToast(`Błąd: ${data.content}`, "error");
                                } else if (data.type === "profiler") {
                                    const m = data.content;
                                    if (m && m.metric) {
                                        profilerData[m.metric] = (profilerData[m.metric] || 0) + (m.value || 0);
                                    }
                                } else if (data.type === "done") {
                                    elapsedMs = data.elapsed_ms || null;
                                    if (bubble && !fullText) bubble.textContent = data.content || fullText;
                                    const finalMetaStr = formatAssistantMeta({
                                        model: currentModel,
                                        tools: usedTools,
                                        elapsed_ms: elapsedMs,
                                        profiler: profilerData,
                                        timestamp: now
                                    });
                                    if (meta) meta.textContent = finalMetaStr;
                                }
                            } catch (_) {}
                        }
                    }
                }
            } catch (e) {
                if (bubble) bubble.textContent = `[Błąd: ${e.message}]`;
                showToast(`Błąd generowania odpowiedzi: ${e.message}`, "error");
            } finally {
                isChatStreaming = false;
                if (bubble) bubble.removeAttribute("id");
                if (meta) meta.removeAttribute("id");
                if (toolsContainer) toolsContainer.removeAttribute("id");
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
