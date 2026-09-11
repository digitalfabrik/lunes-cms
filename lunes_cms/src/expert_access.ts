const initAudioPlayer = (): void => {
    const button = document.querySelector<HTMLButtonElement>("button.media__play")
    const audio = document.querySelector<HTMLAudioElement>("audio.media__player")
    const waveform = document.querySelector<HTMLElement>(".media__waveform")
    if (!button || !audio || !waveform) {
        return

    }
    let frame = 0

    // fills the waveform up to the position the recording is currently at
    const renderProgress = (): void => {
        let progress = 0
        if (audio.ended) {
            // the last frame can stop just short of the duration
            progress = 100
        } else if (Number.isFinite(audio.duration) && audio.duration > 0) {
            progress = (audio.currentTime / audio.duration) * 100
        }
        waveform.style.setProperty("--audio-progress", `${progress}%`)
    }

    const trackProgress = (): void => {
        renderProgress()
        frame = requestAnimationFrame(trackProgress)
    }

    const stopTracking = (): void => {
        cancelAnimationFrame(frame)
        renderProgress()
    }

    button.addEventListener("click", function () {
        audio.currentTime = 0
        void audio.play()
    })

    // dims the button for as long as the recording is running
    audio.addEventListener("play", function () {
        button.classList.add("media__play--playing")
        trackProgress()
    })
    audio.addEventListener("pause", function () {
        button.classList.remove("media__play--playing")
        stopTracking()
    })
    audio.addEventListener("ended", function () {
        button.classList.remove("media__play--playing")
        stopTracking()
    })
}

const initFeedbackDialog = (): void => {
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
}

document.addEventListener("DOMContentLoaded", function () {
    initAudioPlayer()
    initFeedbackDialog()
})
