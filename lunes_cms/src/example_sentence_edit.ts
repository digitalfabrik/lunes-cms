"use strict"

// Inline text editing for a word's example sentence in the admin list view:
// the add/edit buttons toggle the display text into a textarea with save/cancel
// controls, the generate button fills that textarea with a sentence from OpenAI
// for review, and the delete button stores an empty sentence. This mirrors the
// audio/image asset controls in the same list.

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

function _listSentenceErrorText(error: unknown): string {
    return `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`
}

function _storeListSentence(storeUrl: string, sentence: string): Promise<void> {
    const formData = new FormData()
    formData.append("example_sentence", sentence)

    return window.postWithCsrf(storeUrl, formData).then(async (response) => {
        const data = await window.readJsonBody(response)
        if (!response.ok || data.status !== "success") {
            throw new Error(data.message ?? `HTTP error! status: ${response.status}`)
        }
        // Reload so the reset check status and cleared audio are reflected.
        window.location.reload()
    })
}

function _generateListSentence(button: HTMLButtonElement): void {
    const container = _findContainer(button)
    const controls = button.closest<HTMLElement>(".example-sentence-controls")
    const generateUrl = controls?.dataset.generateUrl
    const textarea = container?.querySelector<HTMLTextAreaElement>(".example-sentence-textarea")
    if (!container || !generateUrl || !textarea) {
        return
    }

    button.disabled = true
    window
        .postWithCsrf(generateUrl)
        .then(async (response) => {
            const data = await window.readJsonBody(response)
            const sentence = data.example_sentence
            if (!response.ok || data.error || typeof sentence !== "string" || !sentence) {
                throw new Error(
                    data.error ?? data.message ?? `HTTP error! status: ${response.status}`,
                )
            }
            // The generated sentence is only a proposal until it is saved.
            textarea.value = sentence
            _showEditForm(container)
        })
        .catch((error: unknown) => {
            alert(_listSentenceErrorText(error))
        })
        .finally(() => {
            button.disabled = false
        })
}

function _deleteListSentence(button: HTMLButtonElement): void {
    const controls = button.closest<HTMLElement>(".example-sentence-controls")
    const storeUrl = controls?.dataset.storeUrl
    if (!storeUrl || !confirm(gettext("Are you sure you want to delete this example sentence?"))) {
        return
    }

    button.disabled = true
    _storeListSentence(storeUrl, "").catch((error: unknown) => {
        button.disabled = false
        alert(_listSentenceErrorText(error))
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
    _storeListSentence(storeUrl, textarea.value).catch((error: unknown) => {
        _setEditFormDisabled(container, false)
        alert(_listSentenceErrorText(error))
    })
}

document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", (event) => {
        const target = event.target as HTMLElement

        const editButton = target.closest<HTMLButtonElement>(
            ".edit-example-sentence-btn, .add-example-sentence-btn",
        )
        if (editButton) {
            event.preventDefault()
            const container = _findContainer(editButton)
            if (container) {
                _showEditForm(container)
            }
            return
        }

        const generateButton = target.closest<HTMLButtonElement>(".replace-example-sentence-btn")
        if (generateButton) {
            event.preventDefault()
            _generateListSentence(generateButton)
            return
        }

        const deleteButton = target.closest<HTMLButtonElement>(".delete-example-sentence-btn")
        if (deleteButton) {
            event.preventDefault()
            _deleteListSentence(deleteButton)
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
