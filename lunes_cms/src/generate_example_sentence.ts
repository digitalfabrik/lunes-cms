"use strict"

function _getSentenceCookie(name: string): string | null {
    let cookieValue = null
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";")
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim()
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                break
            }
        }
    }
    return cookieValue
}

function _findSentenceTextarea(button: HTMLButtonElement): HTMLTextAreaElement | null {
    if (button.dataset.target) {
        return document.getElementById(button.dataset.target) as HTMLTextAreaElement | null
    }
    // Inline rows: the textarea lives in a sibling cell of the same row.
    const row = button.closest("tr")
    return row?.querySelector<HTMLTextAreaElement>('textarea[name$="-example_sentence"]') ?? null
}

document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", (event) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>(
            ".generate-example-sentence-btn",
        )
        if (!button || !button.dataset.url) {
            return
        }
        event.preventDefault()

        const container = button.parentElement
        const spinner = container?.querySelector<HTMLElement>(".generate-example-sentence-spinner")
        const messageArea = container?.querySelector<HTMLElement>(
            ".generate-example-sentence-message",
        )
        const textarea = _findSentenceTextarea(button)

        const showMessage = (text: string, color: string) => {
            if (messageArea) {
                messageArea.textContent = text
                messageArea.style.color = color
            }
        }

        if (!textarea) {
            showMessage(gettext("Could not find the example sentence field."), "red")
            return
        }

        button.disabled = true
        if (spinner) {
            spinner.style.display = "inline-block"
        }
        showMessage(gettext("Generating example sentence..."), "inherit")

        fetch(button.dataset.url, {
            method: "POST",
            headers: {
                "X-CSRFToken": _getSentenceCookie("csrftoken") ?? "",
            },
        })
            .then(async (response) => {
                const data = (await response.json()) as {
                    message?: string
                    example_sentence?: string
                    error?: string
                }
                if (!response.ok || data.error || !data.example_sentence) {
                    throw new Error(data.error ?? `HTTP error! status: ${response.status}`)
                }
                return data
            })
            .then((data) => {
                textarea.value = data.example_sentence ?? ""
                textarea.dispatchEvent(new Event("change", { bubbles: true }))
                showMessage(data.message ?? gettext("Example sentence generated!"), "green")
            })
            .catch((error) => {
                console.error("Example sentence generation error:", error)
                showMessage(
                    `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`,
                    "red",
                )
            })
            .finally(() => {
                button.disabled = false
                if (spinner) {
                    spinner.style.display = "none"
                }
            })
    })
})
