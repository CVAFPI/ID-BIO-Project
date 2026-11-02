(() => {
    const prefixInput = document.getElementById('settingNotificationPrefix');
    const institutionInput = document.getElementById('settingInstitution');
    if (!prefixInput || !institutionInput) return;

    let customPrefix = false;
    const derivePrefix = name => {
        const words = String(name || '').toUpperCase().match(/[A-Z0-9]+/g) || [];
        return (words.length === 1
            ? words[0].slice(0, 3)
            : words.map(word => word[0]).join('').slice(0, 3)) || 'CVA';
    };

    institutionInput.addEventListener('input', () => {
        if (!customPrefix) prefixInput.value = derivePrefix(institutionInput.value);
    });
    prefixInput.addEventListener('input', () => {
        customPrefix = true;
    });

    const originalFetch = window.fetch.bind(window);
    window.fetch = async (url, options = {}) => {
        const isSettingsRequest = url === '/api/settings';
        const method = (options.method || 'GET').toUpperCase();

        if (isSettingsRequest && method === 'POST' && options.body) {
            const payload = JSON.parse(options.body);
            payload.notification_topic_prefix = prefixInput.value.trim();
            options = { ...options, body: JSON.stringify(payload) };
        }

        const response = await originalFetch(url, options);
        if (isSettingsRequest && method === 'GET' && response.ok) {
            try {
                const settings = await response.clone().json();
                if (document.activeElement !== prefixInput) {
                    prefixInput.value = settings.notification_topic_prefix
                        || derivePrefix(settings.institution_name || institutionInput.value);
                    customPrefix = false;
                }
            } catch (error) {
                // The caller handles malformed settings responses.
            }
        }
        return response;
    };
})();