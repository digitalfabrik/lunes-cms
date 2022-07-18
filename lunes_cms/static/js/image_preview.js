/*
 * Function to preview a document image before it's uploaded
*/
function previewImage(event){
  // Get file which is to be uploaded
  let file;
  if (event.target.files) {
    file = event.target.files[0];
  }
  // Get image tag
  let img = $(event.target).closest(".card-body").find(".field-image_tag").find("img")[0];
  // If the file is set and is either a jpg or png, update the preview
  if (file && ["image/jpg", "image/jpeg", "image/png"].includes(file.type)) {
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
}

/*
 * Function to hide the preview when the image should be deleted
*/
function resetPreview(event){
  // If the deletion checkbox is activated, clear the file field and the preview
  if (event.target.checked) {
    let fileInput = $(event.target).closest(".card").find("input[type='file']")[0];
    fileInput.value = "";
    $(fileInput).trigger("change");
  }
}

$(document).ready(() => {
  $("input[type='file']").each(() => {
    $(this).change(previewImage);
  });
  $("input[name^='document_image-'][name$='-DELETE'],input[name='icon-clear']").each(() => {
    $(this).change(resetPreview);
  });
});
