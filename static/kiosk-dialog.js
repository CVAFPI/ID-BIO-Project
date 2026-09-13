(function () {
    const overlay = document.createElement('div');
    overlay.className = 'kiosk-dialog-overlay';
    overlay.innerHTML = `<section class="kiosk-dialog" role="dialog" aria-modal="true" aria-labelledby="kioskDialogTitle">
        <header class="kiosk-dialog-head"><h2 id="kioskDialogTitle">System message</h2><button class="kiosk-dialog-close" type="button" aria-label="Close">&times;</button></header>
        <div class="kiosk-dialog-body"><p class="kiosk-dialog-message"></p><div class="kiosk-dialog-input-wrap" hidden><input class="kiosk-dialog-input" autocomplete="off"><button class="kiosk-dialog-toggle" type="button" hidden>Show passcode</button></div><div class="kiosk-keypad" hidden></div></div>
        <footer class="kiosk-dialog-foot"><button class="kiosk-dialog-button secondary" data-action="cancel" type="button">Cancel</button><button class="kiosk-dialog-button primary" data-action="ok" type="button">OK</button></footer>
    </section>`;
    document.addEventListener('DOMContentLoaded', () => document.body.appendChild(overlay));

    let finish = null;
    const title = () => overlay.querySelector('#kioskDialogTitle');
    const message = () => overlay.querySelector('.kiosk-dialog-message');
    const inputWrap = () => overlay.querySelector('.kiosk-dialog-input-wrap');
    const input = () => overlay.querySelector('.kiosk-dialog-input');
    const toggle = () => overlay.querySelector('.kiosk-dialog-toggle');
    const keypad = () => overlay.querySelector('.kiosk-keypad');
    const cancel = () => overlay.querySelector('[data-action="cancel"]');

    function close(value) {
        overlay.classList.remove('is-open');
        document.removeEventListener('keydown', onKeydown);
        const callback = finish;
        finish = null;
        if (callback) callback(value);
    }

    function onKeydown(event) {
        if (event.key === 'Escape') close(null);
        if (event.key === 'Enter' && !cancel().hidden) close(input().value);
    }

    function open(options) {
        title().textContent = options.title || 'System message';
        message().textContent = options.passcode
            ? `${options.message || ''}\nUse 4 to 12 letters, numbers, or symbols.`
            : options.message || '';
        inputWrap().hidden = !options.input;
        keypad().hidden = true;
        toggle().hidden = !options.passcode;
        input().type = options.passcode ? 'password' : 'text';
        input().inputMode = 'text';
        input().pattern = '';
        input().maxLength = options.passcode ? 12 : 524288;
        input().autocomplete = 'off';
        input().oninput = null;
        input().onkeydown = null;
        input().value = '';
        cancel().hidden = options.kind === 'alert';
        cancel().textContent = options.cancelText || 'Cancel';
        overlay.querySelector('[data-action="ok"]').textContent = options.okText || 'OK';
        keypad().innerHTML = '';
        toggle().onclick = () => { input().type = input().type === 'password' ? 'text' : 'password'; toggle().textContent = input().type === 'password' ? 'Show passcode' : 'Mask passcode'; };
        overlay.querySelector('[data-action="ok"]').onclick = () => close(options.input ? input().value : true);
        cancel().onclick = () => close(null);
        overlay.querySelector('.kiosk-dialog-close').onclick = () => close(null);
        overlay.classList.add('is-open');
        document.addEventListener('keydown', onKeydown);
        setTimeout(() => input().focus(), 0);
        return new Promise(resolve => { finish = resolve; });
    }

    window.appAlert = message => open({ message, kind: 'alert' });
    window.appConfirm = message => open({ message, kind: 'confirm' });
    window.appPrompt = (message, options = {}) => open({ message, input: true, passcode: !!options.passcode || !!options.pin, title: options.title || 'Enter value', okText: options.okText || 'Continue' });
})();
