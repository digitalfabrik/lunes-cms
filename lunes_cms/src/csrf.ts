// Loaded as a plain script before its consumers and exposed on `window`, so every
// widget posts through the same CSRF-aware helpers instead of copying its own.

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

window.postWithCsrf = function (url: string, body?: FormData): Promise<Response> {
    return fetch(url, {
        method: "POST",
        body: body,
        headers: {
            "X-CSRFToken": window.getCookie("csrftoken") ?? "",
        },
        credentials: "same-origin",
    })
}
