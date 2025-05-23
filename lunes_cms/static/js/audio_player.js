document.addEventListener("DOMContentLoaded", function() {
    initAudioPlayers()

    if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery(document).on("change", ".action-checkbox, #action-toggle", function() {
            setTimeout(initAudioPlayers, 100)
        })
    }
})

function initAudioPlayers() {
    const audioContainers = document.querySelectorAll(".audio-player-container")
    
    audioContainers.forEach(container => {
        const audio = container.querySelector(".minimal-audio-player")
        const playBtn = container.querySelector(".play-btn")
        const pauseBtn = container.querySelector(".pause-btn")
        
        const newPlayBtn = playBtn.cloneNode(true)
        const newPauseBtn = pauseBtn.cloneNode(true)
        
        playBtn.parentNode.replaceChild(newPlayBtn, playBtn)
        pauseBtn.parentNode.replaceChild(newPauseBtn, pauseBtn)
        
        newPlayBtn.addEventListener("click", function() {
            document.querySelectorAll(".minimal-audio-player").forEach(otherAudio => {
                if (otherAudio !== audio) {
                    otherAudio.pause()
                    
                    // Reset all other play/pause buttons
                    const otherContainer = otherAudio.closest(".audio-player-container")
                    if (otherContainer) {
                        otherContainer.querySelector(".play-btn").style.display = "inline-block"
                        otherContainer.querySelector(".pause-btn").style.display = "none"
                    }
                }
            })
            
            audio.play()
            newPlayBtn.style.display = "none"
            newPauseBtn.style.display = "inline-block"
        })
        
        newPauseBtn.addEventListener("click", function() {
            audio.pause()
            newPauseBtn.style.display = "none"
            newPlayBtn.style.display = "inline-block"
        })
        
        audio.addEventListener("ended", function() {
            newPauseBtn.style.display = "none"
            newPlayBtn.style.display = "inline-block"
        })
    })
}