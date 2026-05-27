/*
 * Function to preview a document image before it's uploaded
 */
function previewImage(event: JQuery.ChangeEvent): void {
    // Get file which is to be uploaded
    let file: File | undefined
    const files = (event.target as HTMLInputElement).files
    if (files) {
        file = files[0]
    }
    // Get image tag
    let img: HTMLImageElement = $(event.target as HTMLElement)
        .closest(".card-body")
        .find(".field-image_tag")
        .find("img")[0]
    // If the file is set and is either a jpg or png, update the preview
    if (file && ["image/jpg", "image/jpeg", "image/png"].includes(file.type)) {
        let reader = new FileReader()
        reader.onload = function () {
            $(img).attr("src", reader.result as string)
            $(img).attr("height", "auto")
            $(img).removeClass("hidden")
        }
        reader.readAsDataURL(file)
    } else {
        // Otherwise, clear the preview and hide the image
        $(img).attr("src", "")
        $(img).addClass("hidden")
    }
}

/*
 * Function to hide the preview when the image should be deleted
 */
function resetPreview(event: JQuery.ChangeEvent): void {
    // If the deletion checkbox is activated, clear the file field and the preview
    if ((event.target as HTMLInputElement).checked) {
        let fileInput: HTMLInputElement = $(event.target as HTMLElement)
            .closest(".card")
            .find("input[type='file']")[0] as HTMLInputElement
        fileInput.value = ""
        $(fileInput).trigger("change")
    }
}

$(document).ready(function () {
    $("input[type='file']").each(function (_index: number, element: HTMLElement) {
        $(element).change(previewImage)
    })
    $("input[name^='document_image-'][name$='-DELETE'],input[name='icon-clear']").each(function (
        _index: number,
        element: HTMLElement,
    ) {
        $(element).change(resetPreview)
    })
})
