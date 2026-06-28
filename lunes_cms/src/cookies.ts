// Shared cookie helper used by the asset-manager and generation widgets to read
// the CSRF token. Loaded as a plain script before its consumers and exposed on
// `window` so every widget reuses the same parser instead of copying its own.

window.getCookie = function (name: string): string | null {
    if (!document.cookie || document.cookie === "") {
        return null
    }
    for (const rawCookie of document.cookie.split(";")) {
        const cookie = rawCookie.trim()
        if (cookie.substring(0, name.length + 1) === name + "=") {
            return decodeURIComponent(cookie.substring(name.length + 1))
        }
    }
    return null
}
