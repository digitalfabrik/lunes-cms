document.addEventListener("DOMContentLoaded", function () {
    initAudioPlayers()

    if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery(document).on("change", ".action-checkbox, #action-toggle", function () {
            setTimeout(initAudioPlayers, 100)
        })
    }
})

function initAudioPlayers(): void {
    const audioContainers = document.querySelectorAll<HTMLElement>(".audio-player-container")

    audioContainers.forEach((container) => {
        const audio = container.querySelector<HTMLAudioElement>(".minimal-audio-player")
        const playBtn = container.querySelector<HTMLElement>(".play-btn")
        const pauseBtn = container.querySelector<HTMLElement>(".pause-btn")

        if (!audio || !playBtn || !pauseBtn) {
            return
        }

        const newPlayBtn = playBtn.cloneNode(true) as HTMLElement
        const newPauseBtn = pauseBtn.cloneNode(true) as HTMLElement

        playBtn.parentNode?.replaceChild(newPlayBtn, playBtn)
        pauseBtn.parentNode?.replaceChild(newPauseBtn, pauseBtn)

        newPlayBtn.addEventListener("click", function () {
            document
                .querySelectorAll<HTMLAudioElement>(".minimal-audio-player")
                .forEach((otherAudio) => {
                    if (otherAudio !== audio) {
                        otherAudio.pause()

                        // Reset all other play/pause buttons
                        const otherContainer =
                            otherAudio.closest<HTMLElement>(".audio-player-container")
                        if (otherContainer) {
                            const otherPlayBtn =
                                otherContainer.querySelector<HTMLElement>(".play-btn")
                            const otherPauseBtn =
                                otherContainer.querySelector<HTMLElement>(".pause-btn")
                            if (otherPlayBtn) {
                                otherPlayBtn.style.display = "inline-block"
                            }
                            if (otherPauseBtn) {
                                otherPauseBtn.style.display = "none"
                            }
                        }
                    }
                })

            audio.play()
            newPlayBtn.style.display = "none"
            newPauseBtn.style.display = "inline-block"
        })

        newPauseBtn.addEventListener("click", function () {
            audio.pause()
            newPauseBtn.style.display = "none"
            newPlayBtn.style.display = "inline-block"
        })

        audio.addEventListener("ended", function () {
            newPauseBtn.style.display = "none"
            newPlayBtn.style.display = "inline-block"
        })
    })
}
