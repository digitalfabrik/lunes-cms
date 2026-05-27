/*
 * Function to highlight unread feedback with bold letters
 */

// index of comment column in the feedback list
const commentIndex: number = 1

function markUnreadFeedback(): void {
    const readByEntries = document.querySelectorAll<HTMLElement>(".field-read_by")
    if (readByEntries.length > 0) {
        readByEntries.forEach((entry) => {
            if (entry.textContent == "-") {
                ;(entry.parentNode as HTMLElement).style.fontWeight = "bold"
            } else {
                ;(entry.parentNode as HTMLElement).style.fontWeight = "normal"
                ;(entry.parentNode as HTMLElement).children.item(commentIndex) as HTMLElement
                ;(
                    (entry.parentNode as HTMLElement).children.item(commentIndex) as HTMLElement
                ).style.fontWeight = "normal"
            }
        })
    }
}

document.addEventListener("DOMContentLoaded", markUnreadFeedback)
