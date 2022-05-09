/*
 * Function to preview a document image before it's uploaded
*/
function previewImage(event){
  if (event.target.name.endsWith("-image")) {
    // Get file which is to be uploaded
    let file = event.target.files[0];
    // Get image tag
    let img = $(event.target).closest(".card-body").find(".field-image_tag").find("img")[0];
    // If the file is set and is either a jpg or png, update the preview
    if (file && ["image/jpg", "image/jpeg", "image/png"].includes(file.type)){
      let reader = new FileReader();
      reader.onload = function(){
        $(img).attr("src", reader.result);
        $(img).attr("height", "auto");
        $(img).removeClass("hidden");
      }
      reader.readAsDataURL(file);
    } else {
      // Otherwise, clear the preview and hide the image
      $(img).attr("src", "");
      $(img).addClass("hidden");
    }
  } else if (event.target.name.endsWith("DELETE")) {
    // If the deletion checkbox is activated, clear the file field and the preview
    if (event.target.checked) {
      let fileInput = $(event.target).closest(".card").find("input[name^='document_image-'][name$='-image']")[0];
      fileInput.value = "";
      $(fileInput).trigger("change");
    }
  }
}

$(document).ready(() => {
  $("input[name^='document_image-'][name$='-image']").each(() => {
    $(this).change(previewImage);
  });
});
