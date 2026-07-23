"use strict"

// Create-time "a word like this already exists" warning on the Word
// add/change form (issue #531). Purely informational: it never blocks
// saving and never persists anything — that's a separate, durable "accept"
// flow on the Duplicated vocabulary analysis page, not this one.

interface DuplicateMatch {
    pk: number
    display: string
    url: string
}

function _currentWordPk(): string | null {
    const match = window.location.pathname.match(/\/word\/(\d+)\/change\/?$/)
    return match ? match[1] : null
}

function _debounce<Args extends unknown[]>(
    fn: (...args: Args) => void,
    delayMs: number,
): (...args: Args) => void {
    let timer: ReturnType<typeof setTimeout> | undefined
    return (...args: Args) => {
        if (timer) {
            clearTimeout(timer)
        }
        timer = setTimeout(() => fn(...args), delayMs)
    }
}

function _renderMatches(box: HTMLElement, matches: DuplicateMatch[]): void {
    box.innerHTML = ""
    if (matches.length === 0) {
        box.classList.add("is-hidden")
        return
    }

    // Built via DOM nodes rather than an HTML template string: `match.display`
    // embeds the other word's raw, user-supplied text (via Word.__str__), so
    // it must never be interpolated into innerHTML unescaped.
    const text = document.createElement("span")
    text.textContent = `${gettext("A word with this name already exists:")} `
    matches.forEach((match, index) => {
        if (index > 0) {
            text.appendChild(document.createTextNode(", "))
        }
        const link = document.createElement("a")
        link.href = match.url
        link.target = "_blank"
        link.textContent = match.display
        text.appendChild(link)
    })
    box.appendChild(text)

    box.classList.remove("is-hidden")
}

function _checkDuplicate(input: HTMLInputElement, box: HTMLElement): void {
    const word = input.value.trim()
    if (!word) {
        box.classList.add("is-hidden")
        box.innerHTML = ""
        return
    }
    const params = new URLSearchParams({ word })
    const excludePk = _currentWordPk()
    if (excludePk) {
        params.set("exclude_pk", excludePk)
    }
    fetch(`${input.dataset.checkUrl}?${params.toString()}`, {
        credentials: "same-origin",
    })
        .then((response) => response.json() as Promise<{ matches: DuplicateMatch[] }>)
        .then((data) => _renderMatches(box, data.matches))
        .catch(() => {
            // A failed check is silently ignored: it's a soft warning, not a
            // requirement to save, so a network hiccup shouldn't block anything.
        })
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("id_word") as HTMLInputElement | null
    if (!input || !input.dataset.checkUrl) {
        return
    }

    const box = document.createElement("div")
    box.className = "alert alert-warning word-duplicate-warning my-4 is-hidden"
    input.insertAdjacentElement("afterend", box)

    const debouncedCheck = _debounce(() => _checkDuplicate(input, box), 400)
    input.addEventListener("input", debouncedCheck)
    input.addEventListener("blur", () => _checkDuplicate(input, box))

    if (input.value.trim()) {
        _checkDuplicate(input, box)
    }
})
