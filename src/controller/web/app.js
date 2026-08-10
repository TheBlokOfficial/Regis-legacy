/**
 * Regis — Panel Kontrolny | app.js
 *
 * Punkt startowy — orchestruje inicjalizację modułów.
 * Nie zawiera logiki biznesowej.
 */

import { initClock, renderCloudProvidersList } from './renderer.js';
import { init, connectSSE, sendNodeCommand } from './api.js';
import { initChat } from './chat.js';
import { initModals } from './modals.js';

window.sendNodeCommand = sendNodeCommand;

async function loadViewComponents() {
    const mainEl = document.getElementById("main");
    if (!mainEl) return;

    const views = [
        "/views/dashboard.html",
        "/views/logs.html",
        "/views/chat.html"
    ];

    const modals = [
        "/modals/node_config.html",
        "/modals/cloud_provider.html"
    ];

    try {
        const viewTemplates = await Promise.all(
            views.map(url => fetch(url).then(r => r.text()))
        );
        viewTemplates.forEach(html => mainEl.insertAdjacentHTML("beforeend", html));

        const modalTemplates = await Promise.all(
            modals.map(url => fetch(url).then(r => r.text()))
        );
        modalTemplates.forEach(html => document.body.insertAdjacentHTML("beforeend", html));
    } catch (err) {
        console.error("[Regis] Błąd ładowania komponentów widoków:", err);
    }
}

function initRouting() {
    const navButtons = document.querySelectorAll('.sidebar-nav .nav-btn');
    const viewSections = document.querySelectorAll('.view-section');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetView = btn.getAttribute('data-view');

            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            viewSections.forEach(section => {
                if (section.id === `view-${targetView}`) {
                    section.style.display = (targetView === 'chat' || targetView === 'logs') ? 'flex' : 'block';
                    section.classList.add('active');
                } else {
                    section.style.display = 'none';
                    section.classList.remove('active');
                }
            });
        });
    });
}

// ── Inicjalizacja Aplikacji ───────────────────────────────────────────────

async function startApp() {
    await loadViewComponents();
    initRouting();
    initClock();
    init();
    connectSSE();
    initChat();
    initModals();
    renderCloudProvidersList();
}

startApp();
