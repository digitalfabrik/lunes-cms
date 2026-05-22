if (!$) {
    $ = django.jQuery
}

// Toggle the plural field depending on the chosen word type
$(document).ready(function () {
    const togglePluralWordInput = () => {
        const isNoun = $("#id_word_type").val() === "Nomen"
        $("#id_plural").closest("div.row").toggle(isNoun)
    }

    $("#id_word_type").change(togglePluralWordInput)
    togglePluralWordInput()
})

// Toggle the drop down for grammatical gender depending on the chosen word type
$(document).ready(function () {
    const toggleGenderDropdown = () => {
        const isNoun = $("#id_word_type").val() === "Nomen"
        $("#id_grammatical_gender").closest("div.row").toggle(isNoun)
    }

    $("#id_word_type").change(toggleGenderDropdown)
    toggleGenderDropdown()
})

// Detect changes in the "word" field and search for a duplicate
$(document).ready(function () {
    $("#id_word").change((event: JQuery.ChangeEvent) => {
        const val = $(event.target as HTMLElement).val()
        if (typeof val === "string" && val.length > 0) {
            $.ajax({
                type: "GET",
                url: "/api/search_duplicate/" + val,
                dataType: "json",
                success: function (data: DuplicateData) {
                    showDuplicates(data, $(event.target as HTMLElement).closest(".card-body"))
                },
            })
        } else {
            removeDuplicationCheckMessage()
        }
    })
    $("#id_word_type").trigger("change")
})

type DuplicateData = {
    word?: string
    message: string
    definition?: string
    training_sets?: string
}

// Create and show message whether there is a possible duplicate
function showDuplicates(data: DuplicateData, parent: ReturnType<typeof $>): void {
    removeDuplicationCheckMessage()

    let result: HTMLElement
    if (data["word"]) {
        // If there is a duplicated word, use orange background
        result = createSearchResultField("#ffbb4a")

        // Show alert message
        addDetailInfo(result, data["message"], "normal")

        // Show the duplicated word with its word type
        addDetailInfo(result, data["word"], "bold")

        // Show its definition too for more detail
        if (data["definition"]) addDetailInfo(result, data["definition"], "normal")

        // Show related training sets
        if (data["training_sets"]) addDetailInfo(result, data["training_sets"], "normal")
    } else {
        // If there is no duplicate, use green background
        result = createSearchResultField("#72f399")

        // Show message that no duplicate was found
        addDetailInfo(result, data["message"], "normal")
    }

    parent.prepend(result)
}

// Create a zone in which result duplicate search will be shown
function createSearchResultField(backgroundColor: string): HTMLElement {
    let messageField = document.createElement("div")
    messageField.setAttribute("id", "result")
    messageField.style.padding = "25px"
    messageField.style.backgroundColor = backgroundColor

    return messageField
}

// Create and add detail information
function addDetailInfo(resultField: HTMLElement, info: string, fontWeight: string): void {
    let detailInfoField = document.createElement("div")
    detailInfoField.style.fontWeight = fontWeight
    let detailInfo = document.createTextNode(info)
    detailInfoField.append(detailInfo)
    resultField.append(detailInfoField)
}

// Remove the duplicate search result
function removeDuplicationCheckMessage(): void {
    const existingMessage = document.getElementById("result")

    if (existingMessage) {
        existingMessage.remove()
    }
}
