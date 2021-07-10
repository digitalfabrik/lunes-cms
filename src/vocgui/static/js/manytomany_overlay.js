var doc;

/*
Function to fetch a document for a given id.
*/
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


/*
Function to display a small thumbnail when a document within
the training set many to many selector is selected. It shows
one image and one audio.
*/
function display_thumbnail() {
    var overlay = new Overlay();

    /*Header*/
    var header1 = document.createElement("h1");
    header1.innerText = doc["word"];
    header1.textAlign = "left";
    overlay.content.appendChild(header1);

    /*Free Space*/
    space = document.createElement("div");
    space.className += "col-xs-12";
    space.style.height = "30px";
    overlay.content.appendChild(space);

    /*Image*/
    if (doc["document_image"].length >0) {
        var img = document.createElement("img");
        img.style.width = "600px";
        img.src = doc["document_image"][0]["image"];
        img.className += "img-fluid rounded";
        overlay.content.appendChild(img);
    } else {
        var text = document.createElement("div");
        text.className = "alert alert-secondary";
        text.innerText = "No image available";
        overlay.content.appendChild(text);

    }
   
    /*Free Space*/
    overlay.content.appendChild(space);

    /*Audio*/
    if (doc["audio"]) {
        var audio = document.createElement("audio");
        audio.id       = "audio-player";
        audio.controls = "controls";
        audio.src      = doc["audio"];
        audio.type     = "audio/mpeg";
        audio.style.width = "100%";
        overlay.content.appendChild(audio);
    } else {
        var text = document.createElement("div");
        text.className += "alert alert-secondary";
        text.innerText = "No audio available";
        overlay.content.appendChild(text);
    }

    overlay.open();
}

/*
Function that gets called when selection of many to many selector
in training set module changes. It fetches the specific document
and displays a thumbnail.
*/
function document_overlay(event) {
    if (event.altKey) {
        get_document(event.target.value);
        display_thumbnail();
    }
}
