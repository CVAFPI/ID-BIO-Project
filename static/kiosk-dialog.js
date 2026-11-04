
(function () {
    'use strict';

    const overlay = document.createElement('div');
    overlay.className = 'kiosk-dialog-overlay';

    overlay.innerHTML = `
        <section class="kiosk-dialog"
                 role="dialog"
                 aria-modal="true"
                 aria-labelledby="kioskDialogTitle">
            <header class="kiosk-dialog-head">
                <h2 id="kioskDialogTitle">System message</h2>
                <button class="kiosk-dialog-close"
                        type="button"
                        aria-label="Close">&times;</button>
            </header>

            <div class="kiosk-dialog-body">
                <p class="kiosk-dialog-message"></p>

                <div class="kiosk-dialog-input-wrap" hidden>
                    <input class="kiosk-dialog-input"
                           autocomplete="off">
                    <button class="kiosk-dialog-toggle"
                            type="button"
                            hidden>Show passcode</button>
                </div>

                <div class="kiosk-keypad" hidden></div>
            </div>

            <footer class="kiosk-dialog-foot">
                <button class="kiosk-dialog-forgot"
                        data-action="forgot"
                        type="button"
                        hidden>Forgot Password</button>

                <button class="kiosk-dialog-button secondary"
                        data-action="cancel"
                        type="button">Cancel</button>

                <button class="kiosk-dialog-button primary"
                        data-action="ok"
                        type="button">OK</button>
            </footer>
        </section>
    `;

    function attachOverlay() {
        if (!overlay.isConnected && document.body) {
            document.body.appendChild(overlay);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachOverlay, {
            once: true
        });
    } else {
        attachOverlay();
    }

    let finish = null;
    let dialogOptions = null;

    const title = () => overlay.querySelector('#kioskDialogTitle');
    const message = () => overlay.querySelector('.kiosk-dialog-message');
    const inputWrap = () => overlay.querySelector('.kiosk-dialog-input-wrap');
    const input = () => overlay.querySelector('.kiosk-dialog-input');
    const toggle = () => overlay.querySelector('.kiosk-dialog-toggle');
    const keypad = () => overlay.querySelector('.kiosk-keypad');
    const cancel = () => overlay.querySelector('[data-action="cancel"]');
    const forgot = () => overlay.querySelector('[data-action="forgot"]');
    const ok = () => overlay.querySelector('[data-action="ok"]');

    // Parse API responses safely. Flask, a proxy, or a server error handler
    // may return HTML instead of JSON, so never blindly call response.json().
    async function readJsonResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        const body = await response.text();

        let result;

        if (body.trim()) {
            try {
                result = JSON.parse(body);
            } catch (_) {
                const detail = response.ok
                    ? 'The server returned an invalid response.'
                    : `The server returned an error page (HTTP ${response.status}).`;

                throw new Error(detail);
            }
        } else {
            result = {};
        }

        if (!contentType.toLowerCase().includes('application/json')) {
            if (!response.ok) {
                throw new Error(
                    result.message ||
                    `Request failed with HTTP ${response.status}.`
                );
            }

            throw new Error(
                'The server response was not JSON. Check the Flask route.'
            );
        }

        if (!response.ok) {
            throw new Error(
                result.message ||
                `Request failed with HTTP ${response.status}.`
            );
        }

        return result;
    }

    async function apiFetch(url, options = {}) {
        let response;

        try {
            response = await fetch(url, {
                ...options,
                headers: {
                    ...(options.body instanceof FormData
                        ? {}
                        : { 'Content-Type': 'application/json' }),
                    ...(options.headers || {})
                }
            });
        } catch (_) {
            throw new Error(
                'Could not connect to the server. Check that the ID-BIO ' +
                'server is running and try again.'
            );
        }

        return readJsonResponse(response);
    }

    function close(value) {
        overlay.classList.remove('is-open');
        document.removeEventListener('keydown', onKeydown);

        const callback = finish;
        finish = null;
        dialogOptions = null;

        if (callback) {
            callback(value);
        }
    }

    function onKeydown(event) {
        if (!overlay.classList.contains('is-open')) return;

        if (event.key === 'Escape') {
            event.preventDefault();

            if (dialogOptions && dialogOptions.kind !== 'alert') {
                close(null);
            }

            return;
        }

        if (event.key === 'Enter' && !event.isComposing) {
            event.preventDefault();

            if (dialogOptions && dialogOptions.kind === 'alert') {
                close(true);
            } else if (inputWrap().hidden) {
                close(true);
            } else if (input().value.length > 0) {
                close(input().value);
            }
        }
    }

    function open(options = {}) {
        attachOverlay();

        if (!overlay.isConnected) {
            return Promise.reject(
                new Error('The dialog could not be attached to the page.')
            );
        }

        // Avoid accidentally replacing a pending dialog promise.
        if (finish) {
            close(null);
        }

        dialogOptions = options;

        const hasInput = !!options.input;
        const isPasscode = !!options.passcode;

        title().textContent = options.title || 'System message';

        message().textContent = isPasscode
            ? `${options.message || ''}\nUse 4 to 12 characters with no spaces.`
            : (options.message || '');

        inputWrap().hidden = !hasInput;
        input().disabled = !hasInput;
        input().type = isPasscode ? 'password' : 'text';
        input().inputMode = 'text';
        input().maxLength = isPasscode ? 12 : 524288;
        input().autocomplete = 'off';
        input().value = '';
        input().oninput = null;
        input().onkeydown = null;

        keypad().hidden = true;
        keypad().replaceChildren();

        toggle().hidden = !isPasscode;
        toggle().textContent = 'Show passcode';

        cancel().hidden = options.kind === 'alert';
        cancel().textContent = options.cancelText || 'Cancel';

        ok().textContent = options.okText || 'OK';

        // Password recovery is only shown for dialogs that explicitly allow it.
        forgot().hidden = !options.allowForgot;
        forgot().textContent = 'Forgot Password';

        toggle().onclick = () => {
            const showing = input().type === 'password';
            input().type = showing ? 'text' : 'password';
            toggle().textContent = showing
                ? 'Mask passcode'
                : 'Show passcode';
        };

        ok().onclick = () => {
            close(hasInput ? input().value : true);
        };

        cancel().onclick = () => close(null);

        forgot().onclick = () => {
            close(null);
            window.setTimeout(recoverPassword, 0);
        };

        overlay.querySelector('.kiosk-dialog-close').onclick = () => {
            if (options.kind !== 'alert') {
                close(null);
            }
        };

        overlay.classList.add('is-open');
        document.removeEventListener('keydown', onKeydown);
        document.addEventListener('keydown', onKeydown);

        return new Promise(resolve => {
            finish = resolve;

            window.setTimeout(() => {
                if (hasInput) {
                    input().focus();
                } else {
                    ok().focus();
                }
            }, 0);
        });
    }

    window.appAlert = text => open({
        message: String(text ?? ''),
        kind: 'alert'
    });

    window.appConfirm = text => open({
        message: String(text ?? ''),
        kind: 'confirm'
    });

    window.appPrompt = (text, options = {}) => open({
        message: String(text ?? ''),
        kind: 'prompt',
        input: true,
        passcode: !!options.passcode || !!options.pin,
        title: options.title || 'Enter value',
        okText: options.okText || 'Continue',
        allowForgot: !!options.allowForgot
    });

    async function recoverPassword() {
        try {
            const config = await apiFetch('/api/security/config');

            if (!config.security_question) {
                await window.appAlert(
                    'No security question is configured. Set one during ' +
                    'initial setup before using password recovery.'
                );
                return;
            }

            const answer = await window.appPrompt(
                config.security_question,
                {
                    title: 'Password recovery answer',
                    okText: 'Continue'
                }
            );

            if (answer === null) return;

            const newPin = await window.appPrompt(
                'Enter a new passcode:',
                {
                    title: 'New passcode',
                    passcode: true,
                    okText: 'Reset passcode'
                }
            );

            if (newPin === null) return;

            if (!/^\S{4,12}$/.test(newPin)) {
                await window.appAlert(
                    'Passcode must be 4 to 12 characters with no spaces.'
                );
                return;
            }

            await apiFetch('/api/security/recover', {
                method: 'POST',
                body: JSON.stringify({
                    security_answer: answer,
                    new_pin: newPin
                })
            });

            await window.appAlert(
                'Passcode reset successfully. Use your new passcode.'
            );

        } catch (error) {
            await window.appAlert(
                error.message || 'Could not reset the passcode.'
            );
        }
    }

    // Optional helper for other frontend code that needs the same safe
    // response parsing behavior.
    window.kioskApiFetch = apiFetch;
})();
