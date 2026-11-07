(function () {
    'use strict';

    const tokenElement = document.querySelector('meta[name="cvafpi-control-token"]');
    const controlToken = tokenElement?.content;
    if (!controlToken) {
        throw new Error('The application control token is missing from this page.');
    }

    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
        const request = input instanceof Request ? input : null;
        const method = String(init.method || request?.method || 'GET').toUpperCase();
        if (method !== 'POST') {
            return nativeFetch(input, init);
        }

        const headers = new Headers(request?.headers);
        new Headers(init.headers).forEach((value, name) => headers.set(name, value));
        headers.set('X-CVAFPI-Control-Token', controlToken);
        return nativeFetch(input, { ...init, headers });
    };
})();
