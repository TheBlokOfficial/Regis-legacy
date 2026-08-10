/**
 * Regis — Panel Kontrolny | renderer.js
 *
 * Warstwa DOM — jedyne miejsce modyfikujące interfejs użytkownika.
 * Nie zna sieci ani logiki zdarzeń biznesowych.
 *
 * Zależności: state.js (liczniki), utils.js (escapowanie)
 */

import { workerCount, satelliteCount } from './state.js';
import { escHtml } from './utils.js';
import { fetchCloudProviders } from './api.js';
import { setCloudProvidersCache, openClientConfigModal, openCloudProviderModal } from './modals.js';

// Maksymalna liczba wpisów w dzienniku (zapobiega rosnącemu DOM bez końca)
const LOG_MAX = 300;

// ── Zegar ──────────────────────────────────────────────────────────────────

export function initClock() {
    function tick() {
        document.getElementById("clock").textContent =
            new Date().toLocaleTimeString("pl-PL", { hour12: false });
    }
    setInterval(tick, 1000);
    tick();
}

// ── Karty integracji ────────────────────────────────────────────────────────

export function renderIntegrationCard(integration) {
    const id       = integration.id;
    const existing = document.getElementById(`integration-${id}`);
    const card     = existing || document.createElement("div");

    const status = integration.status || "unknown";
    const name   = integration.name || id;
    const type   = integration.type || "—";
    const detail = integration.detail || "—";

    const labels = { online: "Online", offline: "Offline", unknown: "—" };
    const badgeText = labels[status] || status;

    card.id        = `integration-${id}`;
    card.className = "list-row";
    card.innerHTML = `
        <span class="dot ${status}"></span>
        <div class="list-info">
            <span class="list-title">${escHtml(name)}</span>
            <span class="list-meta">${escHtml(type)} • ${escHtml(detail)}</span>
        </div>
        <div class="list-actions">
            <span class="badge ${status}">${badgeText}</span>
        </div>
    `;

    const body  = document.getElementById("integrations-tree-body");
    if (!body) return;
    const empty = body.querySelector(".empty-state");
    if (empty) empty.remove();

    if (!existing) body.appendChild(card);

    const countEl = document.getElementById("integration-count");
    if (countEl) {
        countEl.textContent = body.querySelectorAll(".list-row").length;
    }
}

export function renderIntegrationsList(integrations) {
    if (Array.isArray(integrations) && integrations.length > 0) {
        integrations.forEach(item => renderIntegrationCard(item));
    }
}

export function updateHAStatus(status) {
    renderIntegrationCard({
        id: "home_assistant",
        name: "Home Assistant",
        type: "Smart Home",
        detail: "Sterowanie urządzeniami & encjami",
        status: status || "unknown"
    });
}

// ── Karty Klientów (RegisDesktop) ──────────────────────────────────────────

export function renderNodeCard(node) {
    const id = node.id;
    const existing = document.getElementById(`node-${id}`);
    const card = existing || document.createElement("div");

    const name = node.name || id;
    const host = node.host ? (node.port ? `${node.host}:${node.port}` : node.host) : "—";
    const services = node.services || {};
    const isDict = typeof services === 'object' && !Array.isArray(services);

    let tagsHtml = '';
    const clientTitle = name.startsWith("desktop-") ? "Regis Desktop" : name;

    const ollamaConfig = isDict ? (services.ollama_worker || services.worker) : (Array.isArray(services) && services.includes("worker") ? node : null);
    if (ollamaConfig) {
        const model = ollamaConfig.model_name || node.model_name || "qwen2.5:7b";
        tagsHtml += `<span class="service-tag"><span class="tech-value">LLM: ${escHtml(model)}</span></span>`;
    }

    const sttConfig = isDict ? services.stt_worker : null;
    if (sttConfig) {
        const sttSize = sttConfig.stt_model_size || "small";
        tagsHtml += `<span class="service-tag"><span class="tech-value">STT: Whisper (${escHtml(sttSize)})</span></span>`;
    }

    const ttsConfig = isDict ? services.tts_worker : null;
    if (ttsConfig) {
        tagsHtml += `<span class="service-tag"><span class="tech-value">TTS: Piper</span></span>`;
    }

    const satConfig = isDict ? services.satellite : (Array.isArray(services) && services.includes("satellite") ? node : null);
    if (satConfig) {
        const room = satConfig.room || node.room;
        if (room && room !== "brak") {
            tagsHtml += `<span class="service-tag"><span class="tech-value">Satelita: ${escHtml(room)}</span></span>`;
        }
    }

    card.id = `node-${id}`;
    card.className = "list-row";
    card.setAttribute('title', host !== '—' ? `Adres: ${host}` : '');
    card.innerHTML = `
        <span class="dot online"></span>
        <div class="list-info">
            <div class="list-title-group">
                <span class="list-title">${escHtml(clientTitle)}</span>
            </div>
            <span class="list-meta">Połączony</span>
            <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">${tagsHtml}</div>
        </div>
        <div class="list-actions">
            <button class="btn btn-ghost" id="btn-config-${id}">
                Konfiguruj
            </button>
        </div>
    `;

    card.querySelector(`#btn-config-${id}`)
        .addEventListener("click", () => openClientConfigModal(id));

    const body = document.getElementById("nodes-tree-body");
    if (!body) return;
    const empty = body.querySelector(".empty-state");
    if (empty) empty.remove();

    if (!existing) body.appendChild(card);

    const countEl = document.getElementById("worker-count");
    if (countEl) {
        countEl.textContent = body.children.length;
    }
}

// ── Zmysły & Dostawcy (LLM, STT, TTS) ───────────────────────────────────────

export async function renderProvidersList(cloudProviders = [], llmWorkers = [], audioWorkers = []) {
    const container = document.getElementById("providers-tree-body");
    if (!container) return;

    let html = '';
    let totalCount = 0;

    // 1. Sekcja LLM (Mózg)
    const hasLlm = (cloudProviders && cloudProviders.length > 0) || (llmWorkers && llmWorkers.length > 0);
    if (hasLlm) {
        html += `<div class="category-subhead">Model Językowy (LLM)</div>`;
        
        (cloudProviders || []).forEach(cp => {
            totalCount++;
            html += `
                <div class="list-row">
                    <span class="dot online"></span>
                    <div class="list-info">
                        <div class="list-title-group">
                            <span class="list-title">${escHtml(cp.model)}</span>
                        </div>
                        <span class="list-meta">Dostawca: ${escHtml(cp.id)} (${escHtml(cp.type)})</span>
                    </div>
                    <div class="list-actions">
                        <span class="badge online" style="margin-right:4px;">Chmura</span>
                        <button class="btn btn-ghost btn-edit-cp" data-id="${escHtml(cp.id)}">Edytuj</button>
                    </div>
                </div>
            `;
        });

        (llmWorkers || []).forEach(w => {
            totalCount++;
            const modelName = w.model_name || "qwen2.5:7b";
            html += `
                <div class="list-row">
                    <span class="dot online"></span>
                    <div class="list-info">
                        <div class="list-title-group">
                            <span class="list-title">${escHtml(modelName)}</span>
                        </div>
                        <span class="list-meta">Silnik: Ollama • Regis Desktop</span>
                    </div>
                    <div class="list-actions">
                        <span class="badge online">Lokalny</span>
                    </div>
                </div>
            `;
        });
    }

    // 2. Sekcja STT (Słuch)
    const sttWorkers = (audioWorkers || []).filter(a => a.stt_model_size || a.services?.stt_worker);
    if (sttWorkers.length > 0) {
        html += `<div class="category-subhead">Transkrypcja Mowy (STT)</div>`;
        sttWorkers.forEach(a => {
            totalCount++;
            const sttSize = a.stt_model_size || "small";
            html += `
                <div class="list-row">
                    <span class="dot online"></span>
                    <div class="list-info">
                        <div class="list-title-group">
                            <span class="list-title">Faster-Whisper (${escHtml(sttSize)})</span>
                        </div>
                        <span class="list-meta">Silnik: Whisper • Transkrypcja mowy</span>
                    </div>
                    <div class="list-actions">
                        <span class="badge online">Lokalny</span>
                    </div>
                </div>
            `;
        });
    }

    // 3. Sekcja TTS (Mowa)
    const ttsWorkers = (audioWorkers || []).filter(a => a.tts_model_name || a.services?.tts_worker);
    if (ttsWorkers.length > 0) {
        html += `<div class="category-subhead">Synteza Mowy (TTS)</div>`;
        ttsWorkers.forEach(a => {
            totalCount++;
            const ttsModel = a.tts_model_name || "piper";
            html += `
                <div class="list-row">
                    <span class="dot online"></span>
                    <div class="list-info">
                        <div class="list-title-group">
                            <span class="list-title">Piper (${escHtml(ttsModel)})</span>
                        </div>
                        <span class="list-meta">Silnik: Piper • Synteza głosu</span>
                    </div>
                    <div class="list-actions">
                        <span class="badge online">Lokalny</span>
                    </div>
                </div>
            `;
        });
    }

    if (!html) {
        container.innerHTML = `
            <div class="empty-banner">
                <span class="banner-title">System działa w TRYBIE FALLBACK (Offline NLU)</span>
                <span class="banner-desc">Brak aktywnego dostawcy zmysłów. Uruchom aplikację <strong>RegisDesktop</strong> na komputerze lub dodaj dostawcę chmurowego, aby odblokować pełny tryb ReAct.</span>
                <div class="banner-actions">
                    <button class="btn btn-ghost" id="banner-add-cloud-btn">+ Dodaj Chmurę</button>
                </div>
            </div>
        `;
        const bannerBtn = container.querySelector('#banner-add-cloud-btn');
        if (bannerBtn) {
            bannerBtn.addEventListener('click', () => openCloudProviderModal());
        }
    } else {
        container.innerHTML = html;
        container.querySelectorAll('.btn-edit-cp').forEach(btn => {
            btn.addEventListener('click', () => {
                const providerId = btn.getAttribute('data-id');
                openCloudProviderModal(providerId);
            });
        });
    }

    const countEl = document.getElementById("providers-count");
    if (countEl) countEl.textContent = totalCount;
}

export async function renderCloudProvidersList() {
    const cloudProviders = await fetchCloudProviders();
    setCloudProvidersCache(cloudProviders);
    renderProvidersList(cloudProviders, [], []);
}

// ── Satelity (Kanały We/Wy) ────────────────────────────────────────────────

export function renderSatellitesList(satellites = []) {
    const container = document.getElementById("satellites-tree-body");
    if (!container) return;

    if (!satellites || satellites.length === 0) {
        container.innerHTML = '<div class="empty-state">Brak zarejestrowanych satelitów.</div>';
        const satCountEl = document.getElementById("satellite-count");
        if (satCountEl) satCountEl.textContent = "0";
        return;
    }

    container.innerHTML = satellites.map(sat => {
        const id = sat.id || "brak";
        const room = sat.room && sat.room !== "brak" ? sat.room : "";
        const type = sat.type || "desktop";
        
        let title = "Satelita Głosowa";
        if (type === "desktop") {
            title = room ? `Mikrofon Desktop (${room})` : "Mikrofon Desktop";
        } else if (room) {
            title = `Satelita (${room})`;
        }

        const typeLabel = type === "desktop" ? "Aplikacja Desktop" : `Urządzenie ${type.toUpperCase()}`;

        return `
            <div class="list-row satellite-card" id="sat-card-${escHtml(id)}">
                <span class="dot online"></span>
                <div class="list-info">
                    <div class="list-title-group">
                        <span class="list-title">${escHtml(title)}</span>
                    </div>
                    <span class="list-meta">${escHtml(typeLabel)} • Strumień Audio</span>
                </div>
                <div class="list-actions">
                    <span class="vad-status" id="vad-${escHtml(id)}">Cisza</span>
                </div>
            </div>
        `;
    }).join('');

    const satCountEl = document.getElementById("satellite-count");
    if (satCountEl) satCountEl.textContent = satellites.length;
}

export function renderWorkerCard(worker) {
    renderNodeCard(worker);
}

export function renderSatelliteCard(sat) {
    // Odświeżenie listy satelitów
}

export function markWorkerOffline(id) {
    const card = document.getElementById(`node-${id}`);
    if (!card) return;
    const dot = card.querySelector(".dot");
    if (dot) dot.className = "dot offline";
}

export function markSatelliteOffline(id) {
    const card = document.getElementById(`sat-card-${id}`);
    if (!card) return;
    const dot = card.querySelector(".dot");
    if (dot) dot.className = "dot offline";
}

export function updateSatelliteVAD(satId, eventType) {
    let el = document.getElementById(`vad-${satId}`);
    if (!el) {
        el = document.querySelector(".satellite-card .vad-status") || document.querySelector(".vad-status");
    }
    if (!el) return;

    if (eventType === "vad_speech") {
        el.textContent = "Mowa";
        el.className   = "vad-status active speech";
    } else if (eventType === "wakeword") {
        el.textContent = "Wakeword";
        el.className   = "vad-status active wakeword";
    } else if (eventType === "vad_silence") {
        el.textContent = "Cisza";
        el.className   = "vad-status";
    }
}

// ── Stan Gotowości Systemu (System Readiness) ───────────────────────────────

export function updateSystemReadiness(ctrlInfo = {}) {
    const badge = document.getElementById("system-readiness-badge");
    if (!badge) return;

    const fullMode = ctrlInfo.full_mode !== false;
    if (fullMode) {
        badge.className = "badge-readiness full-mode";
        badge.innerHTML = `<span class="dot online"></span> Tryb pełny`;
    } else {
        badge.className = "badge-readiness fallback-mode";
        badge.innerHTML = `<span class="dot offline"></span> Tryb awaryjny`;
    }
}

// ── Dziennik zdarzeń ───────────────────────────────────────────────────────

export function appendLog(timeStr, source, message, typeClass) {
    const list  = document.getElementById("log-list");
    const entry = document.createElement("div");

    entry.className = `log-entry type-${typeClass || "info"}`;
    entry.innerHTML = `
        <span class="log-time">${escHtml(timeStr)}</span>
        <span class="log-source">${escHtml(source)}</span>
        <span class="log-msg">${escHtml(message)}</span>
    `;

    list.appendChild(entry);

    // Usuń najstarsze wpisy gdy przekroczono limit
    while (list.children.length > LOG_MAX) {
        list.removeChild(list.firstChild);
    }

    // Auto-scroll na dół tylko jeśli użytkownik jest blisko dołu
    const threshold = 60;
    const atBottom  = list.scrollHeight - list.scrollTop - list.clientHeight < threshold;
    if (atBottom) list.scrollTop = list.scrollHeight;
}

// ── Toasty (Powiadomienia) ────────────────────────────────────────────────
export function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "❌";

    toast.innerHTML = `<span>${icon}</span> <span>${escHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("fade-out");
        toast.addEventListener("animationend", () => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        });
    }, 3000);
}

// ── Zarządzanie stanem ładowania ──────────────────────────────────────────
export async function withLoadingState(buttonElement, asyncCallback) {
    if (!buttonElement) return await asyncCallback();

    const originalText = buttonElement.innerHTML;
    buttonElement.classList.add("loading");
    buttonElement.disabled = true;
    buttonElement.innerHTML = "Przetwarzanie...";

    try {
        await asyncCallback();
    } finally {
        buttonElement.classList.remove("loading");
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}
