var doc;

function get_document(document_id) {
    $.ajax({
      type: 'GET',
      url: '/api/document_by_id' + '/' + document_id,
      dataType: "json",
      async:false,
      success: function(data) {
          doc = data[0];
      }
    });
  }

function display_thumbnail() {
    var overlay = document.createElement("div");
    overlay.style.paddingTop = "100px";
    var img = document.createElement("img");
    img.src = doc["document_image"][0]["image"];
    img.addEventListener('click', function () {
		document.body.removeChild(overlay);
        overlay = null;
	});
    overlay.appendChild(img);
    document.body.appendChild(overlay);

}
function document_overlay(value) {
    get_document(value);
    if (doc["document_image"].length > 0) {
        display_thumbnail();
    }
}
