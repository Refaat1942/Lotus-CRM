// Lotus CRM client helpers
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => { el.style.opacity = '0'; }, 5000);
    });

    initNotifications();
});

function initNotifications() {
    const bell = document.getElementById('notif-bell');
    const dropdown = document.getElementById('notif-dropdown');
    const list = document.getElementById('notif-list');
    const empty = document.getElementById('notif-empty');
    const countEl = document.getElementById('notif-count');
    if (!bell || !window.LOTUS_NOTIF_URL) return;

    const i18n = window.LOTUS_I18N || {};

    function msgFor(alert) {
        if (alert.message_key === 'notif_stale') {
            return `${i18n.notifStale || 'Open'} ${alert.extra}h — ${alert.serial}`;
        }
        const key = alert.message_key;
        const base = i18n.notifImmediate && key === 'notif_immediate' ? i18n.notifImmediate
            : i18n.notifUnassigned && key === 'notif_unassigned' ? i18n.notifUnassigned
            : alert.message_key;
        return `${base} — ${alert.serial}`;
    }

    async function loadNotifications() {
        try {
            const res = await fetch(window.LOTUS_NOTIF_URL);
            const data = await res.json();
            const alerts = data.alerts || [];
            if (countEl) {
                countEl.textContent = data.count || alerts.length;
                countEl.hidden = !(data.count || alerts.length);
            }
            if (!list) return;
            list.innerHTML = '';
            if (!alerts.length) {
                if (empty) empty.hidden = false;
                return;
            }
            if (empty) empty.hidden = true;
            alerts.forEach(a => {
                const li = document.createElement('li');
                li.className = `notif-item notif-${a.kind}`;
                li.innerHTML = `<a href="${a.url}"><strong>${a.serial}</strong><span>${msgFor(a)}</span><small>${a.status_label} · ${a.urgency_label}</small></a>`;
                list.appendChild(li);
            });
        } catch (e) {
            /* ignore network errors */
        }
    }

    bell.addEventListener('click', (e) => {
        e.stopPropagation();
        const open = !dropdown.hidden;
        dropdown.hidden = open;
        if (!open) loadNotifications();
    });

    document.addEventListener('click', () => { dropdown.hidden = true; });
    dropdown.addEventListener('click', e => e.stopPropagation());

    loadNotifications();
    setInterval(loadNotifications, 60000);
}
