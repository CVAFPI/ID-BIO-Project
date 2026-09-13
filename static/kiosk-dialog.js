(function () {
    const overlay = document.createElement('div');
    overlay.className = 'kiosk-dialog-overlay';
    overlay.innerHTML = `<section class="kiosk-dialog" role="dialog" aria-modal="true" aria-labelledby="kioskDialogTitle">
        <header class="kiosk-dialog-head"><h2 id="kioskDialogTitle">System message</h2><button class="kiosk-dialog-close" type="button" aria-label="Close">&times;</button></header>
        <div class="kiosk-dialog-body"><p class="kiosk-dialog-message"></p><div class="kiosk-dialog-input-wrap" hidden><input class="kiosk-dialog-input" autocomplete="off"><button class="kiosk-dialog-toggle" type="button" hidden>Show PIN</button></div><div class="kiosk-keypad" hidden></div></div>
        <footer class="kiosk-dialog-foot"><button class="kiosk-dialog-button secondary" data-action="cancel" type="button">Cancel</button><button class="kiosk-dialog-button primary" data-action="ok" type="button">OK</button></footer>
    </section>`;
    document.addEventListener('DOMContentLoaded', () => document.body.appendChild(overlay));

    let finish = null;
    const query = selector => overlay.querySelector(selector);
    function close(value) { overlay.classList.remove('is-open'); document.removeEventListener('keydown', onKeydown); const callback = finish; finish = null; if (callback) callback(value); }
    function onKeydown(event) { if (event.key === 'Escape') close(null); if (event.key === 'Enter' && !query('[data-action="cancel"]').hidden) close(query('.kiosk-dialog-input').value); }
    function open(options) {
        query('#kioskDialogTitle').textContent = options.title || 'System message';
        query('.kiosk-dialog-message').textContent = options.message || '';
        query('.kiosk-dialog-input-wrap').hidden = !options.input;
        query('.kiosk-keypad').hidden = !options.keypad;
        query('.kiosk-dialog-toggle').hidden = !options.pin;
        query('.kiosk-dialog-input').type = options.pin ? 'password' : 'text';
        query('.kiosk-dialog-input').inputMode = options.pin ? 'numeric' : 'text';
        query('.kiosk-dialog-input').value = '';
        query('[data-action="cancel"]').hidden = options.kind === 'alert';
        query('[data-action="cancel"]').textContent = options.cancelText || 'Cancel';
        query('[data-action="ok"]').textContent = options.okText || 'OK';
        query('.kiosk-keypad').innerHTML = '';
        if (options.keypad) ['1','2','3','4','5','6','7','8','9','Clear','0','Backspace'].forEach(key => {
            const button = document.createElement('button'); button.className = 'kiosk-key'; button.type = 'button'; button.textContent = key;
            button.onclick = () => { const field = query('.kiosk-dialog-input'); if (key === 'Clear') field.value = ''; else if (key === 'Backspace') field.value = field.value.slice(0, -1); else field.value += key; field.focus(); };
            query('.kiosk-keypad').appendChild(button);
        });
        query('.kiosk-dialog-toggle').onclick = () => { const field = query('.kiosk-dialog-input'); field.type = field.type === 'password' ? 'text' : 'password'; query('.kiosk-dialog-toggle').textContent = field.type === 'password' ? 'Show PIN' : 'Mask PIN'; };
        query('[data-action="ok"]').onclick = () => close(options.input ? query('.kiosk-dialog-input').value : true);
        query('[data-action="cancel"]').onclick = () => close(null); query('.kiosk-dialog-close').onclick = () => close(null);
        overlay.classList.add('is-open'); document.addEventListener('keydown', onKeydown); setTimeout(() => query('.kiosk-dialog-input').focus(), 0);
        return new Promise(resolve => { finish = resolve; });
    }
    window.appAlert = message => open({ message, kind:'alert' });
    window.appConfirm = message => open({ message, kind:'confirm' });
    window.appPrompt = (message, options = {}) => open({ message, input:true, pin:!!options.pin, keypad:!!options.keypad, title:options.title || 'Enter value', okText:options.okText || 'Continue' });
})();
