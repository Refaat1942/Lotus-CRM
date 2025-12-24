// Lotus CRM client helpers
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => el.style.opacity = '0', 5000);
    });
});
