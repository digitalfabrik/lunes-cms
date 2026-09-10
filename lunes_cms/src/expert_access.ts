document.addEventListener("DOMContentLoaded", function () {
    const dialog = document.querySelector<HTMLDialogElement>("dialog#expert-review-feedback")
    if (!dialog) {
        return
    }

    const statusInput = dialog.querySelector<HTMLInputElement>("input[name='review_status']")!
    const titleElement = dialog.querySelector<HTMLElement>("#dialog-title")!
    const subtitleElement = dialog.querySelector<HTMLElement>("#dialog-hint")!
    const submitLabelElement = dialog.querySelector<HTMLElement>("#dialog__submit-label")!

    /*
     * Opens the dialog for the decision of the given trigger button
     */
    const openDialog = (trigger: HTMLElement): void => {
        const status = trigger.getAttribute("data-review-status")!
        const label = trigger.getAttribute("data-label")!
        const subtitle = trigger.getAttribute("data-subtitle")!
        const submitText = trigger.getAttribute("data-submit")!
        statusInput.value = status
        titleElement.textContent = label
        subtitleElement.textContent = subtitle
        submitLabelElement.textContent = submitText

        // lets the stylesheet colour the dialog for this decision
        dialog.dataset.status = status

        dialog.showModal()
    }

    document.querySelectorAll<HTMLElement>("[data-review-status]").forEach(function (trigger) {
        trigger.addEventListener("click", function () {
            openDialog(trigger)
        })
    })

    dialog.querySelectorAll<HTMLElement>("[data-dialog-close]").forEach(function (button) {
        button.addEventListener("click", () => dialog.close())
    })
})
