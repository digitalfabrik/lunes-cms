/*
 * Function to highlight unread feedback with bold letters
*/

// index of comment column in the feedback list
const commentIndex = 1;

function markUnreadFeedback () {
    const readByEntries = document.querySelectorAll(".field-read_by");
    if (readByEntries.length > 0) {
        
        readByEntries.forEach((entry)=>{
            if (entry.textContent == "-") {
                entry.parentNode.style.fontWeight = "bold";
            } else {
                entry.parentNode.style.fontWeight = "normal";
                entry.parentNode.children.item(commentIndex).style.fontWeight = "normal";
           }
        })
    }
}

document.addEventListener("DOMContentLoaded", markUnreadFeedback);