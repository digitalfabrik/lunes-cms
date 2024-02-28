/*
 * Function to highlight unread feedback with bold letters
*/


function markUnreadFeedback () {
    let readByEntries = document.querySelectorAll(".field-read_by");
    if (readByEntries.length != 0) {
        
        readByEntries.forEach((entry)=>{
            if (entry.textContent == "-") {
                //entry.parentNode.style.backgroundColor = "yellow";
                entry.parentNode.style.fontWeight = "bold";
            }
        })
    }
}

document.addEventListener("DOMContentLoaded", markUnreadFeedback);