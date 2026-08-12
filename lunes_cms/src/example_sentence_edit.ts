"use strict"

// Inline text editing for a word's example sentence in the admin list view:
// the edit button toggles the display text into a textarea with save/cancel
// controls, mirroring the audio/image asset controls in the same list.

function _findContainer(el: HTMLElement): HTMLElement | null {
    return el.closest<HTMLElement>(".word-example-sentence-container")
}

function _showEditForm(container: HTMLElement): void {
    const display = container.querySelector<HTMLElement>(".example-sentence-display")
    const editForm = container.querySelector<HTMLElement>(".example-sentence-edit-form")
    const textarea = container.querySelector<HTMLTextAreaElement>(".example-sentence-textarea")
    if (!display || !editForm) {
        return
    }
    display.style.display = "none"
    editForm.style.display = "block"
    textarea?.focus()
}

function _hideEditForm(container: HTMLElement): void {
    const display = container.querySelector<HTMLElement>(".example-sentence-display")
    const editForm = container.querySelector<HTMLElement>(".example-sentence-edit-form")
    if (!display || !editForm) {
        return
    }
    display.style.display = "block"
    editForm.style.display = "none"
}

function _handleCancel(button: HTMLButtonElement): void {
    const container = _findContainer(button)
    if (!container) {
        return
    }
    const textarea = container.querySelector<HTMLTextAreaElement>(".example-sentence-textarea")
    if (textarea) {
        textarea.value = textarea.dataset.originalValue ?? ""
    }
    _hideEditForm(container)
}

function _setEditFormDisabled(container: HTMLElement, disabled: boolean): void {
    container
        .querySelectorAll<
            HTMLButtonElement | HTMLTextAreaElement
        >(".example-sentence-edit-form button, .example-sentence-textarea")
        .forEach((el) => {
            el.disabled = disabled
        })
}

function _handleSave(button: HTMLButtonElement): void {
    const container = _findContainer(button)
    const storeUrl = button.dataset.storeUrl
    const textarea = container?.querySelector<HTMLTextAreaElement>(".example-sentence-textarea")
    if (!container || !storeUrl || !textarea) {
        return
    }

    _setEditFormDisabled(container, true)

    const formData = new FormData()
    formData.append("example_sentence", textarea.value)

    fetch(storeUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": window.getCookie("csrftoken") ?? "",
            "X-Requested-With": "XMLHttpRequest",
        },
    })
        .then(async (response) => {
            const data = (await response.json()) as { status?: string; message?: string }
            if (!response.ok || data.status !== "success") {
                throw new Error(data.message ?? `HTTP error! status: ${response.status}`)
            }
            return data
        })
        .then(() => {
            // Reload so the reset check status and cleared audio are reflected.
            window.location.reload()
        })
        .catch((error: unknown) => {
            _setEditFormDisabled(container, false)
            alert(`${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`)
        })
}

document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", (event) => {
        const target = event.target as HTMLElement

        const editButton = target.closest<HTMLButtonElement>(".edit-example-sentence-btn")
        if (editButton) {
            event.preventDefault()
            const container = _findContainer(editButton)
            if (container) {
                _showEditForm(container)
            }
            return
        }

        const saveButton = target.closest<HTMLButtonElement>(".save-example-sentence-btn")
        if (saveButton) {
            event.preventDefault()
            _handleSave(saveButton)
            return
        }

        const cancelButton = target.closest<HTMLButtonElement>(".cancel-example-sentence-btn")
        if (cancelButton) {
            event.preventDefault()
            _handleCancel(cancelButton)
        }
    })
})
