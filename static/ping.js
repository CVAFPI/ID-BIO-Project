(() => {
    const status = document.getElementById('systemStatus');
    if (!status) return;

    const cloudflareUrl = 'https://1.1.1.1/cdn-cgi/trace';
    let active = true;
    let timer;
    let request;

    function setStatus(online, checking = false) {
        status.classList.toggle('offline', !online && !checking);
        status.classList.toggle('checking', checking);
        status.lastChild.textContent = checking ? 'Checking' : online ? 'Online' : 'Offline';
    }

    async function checkConnectivity() {
        if (!active || request) return;

        const controller = new AbortController();
        request = controller;
        const timeout = setTimeout(() => controller.abort(), 4000);

        try {
            // A resolved opaque response confirms reachability without requiring CORS access.
            await fetch(`${cloudflareUrl}?_=${Date.now()}`, {
                mode: 'no-cors',
                cache: 'no-store',
                signal: controller.signal
            });
            if (active) setStatus(true);
        } catch (error) {
            if (active) setStatus(false);
        } finally {
            clearTimeout(timeout);
            if (request === controller) request = null;
        }
    }

    setStatus(false, true);
    checkConnectivity();
    timer = setInterval(checkConnectivity, 5000);

    window.addEventListener('pagehide', () => {
        active = false;
        clearInterval(timer);
        request?.abort();
    });
    window.addEventListener('pageshow', event => {
        if (!event.persisted || active) return;
        active = true;
        setStatus(false, true);
        checkConnectivity();
        timer = setInterval(checkConnectivity, 5000);
    });
})();
