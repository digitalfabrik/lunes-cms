if (!$) {
  $ = django.jQuery;
}

//Toggle the plural field depending on the chosen word type
$(document).ready(() => {
  $("#id_word_type").change((event) =>
    $("#id_plural")
      .closest("div.row")
      .toggle($(event.target).val() == "Nomen"),
  );
  $("#id_word_type").trigger("change");
});

//Toggle the drop down for grammatical gender depending on the chosen word type
$(document).ready(() => {
  $("#id_word_type").change((event) =>
    $("#id_grammatical_gender")
      .closest("div.row")
      .toggle($(event.target).val() == "Nomen"),
  );
  $("#id_word_type").trigger("change");
});

function removeDuplicationCheckMessage(){
  var existingMessage = document.getElementById("result");

  if (existingMessage) {
    existingMessage.remove();
  }
}

function showDuplicates(data, parent) {
  removeDuplicationCheckMessage();

  result = document.createElement("div");
  result.setAttribute("id", "result");


  if (data["word"]) {
    // If there is a duplicated word, use orange background
    result.style.backgroundColor = "#ffbb4a";
    result.style.padding = "25px"

    // Show alert message
    messageBox = document.createElement("div");
    message = document.createTextNode(data["message"]);
    messageBox.append(message);
    result.append(messageBox);
    // Show the duplicated word with its word type
    wordBox = document.createElement("div");
    word = document.createTextNode(data["word"]);
    wordBox.style.fontWeight = "bold";
    wordBox.append(word);
    result.append(wordBox);
    // Show its definition too for more detail
    definitionBox = document.createElement("div");
    definition = document.createTextNode(data["definition"]);
    definitionBox.append(definition);
    result.append(definitionBox);
    // Show related training sets
    trainingSetsBox = document.createElement("div");
    trainingSets = document.createTextNode(data["training_sets"]);
    trainingSetsBox.append(trainingSets);
    result.append(trainingSetsBox);
  } else {
    // If there is no duplicate, use green background
    result.style.backgroundColor = "#72f399";
    result.style.padding = "25px"
    // Show message that no duplicate was found
    messageBox = document.createElement("div");
    message = document.createTextNode(data["message"]);
    messageBox.append(message);
    result.append(messageBox);
  }
  
  parent.prepend(result);
}


$(document).ready(() => {
  $("#id_word").change((event) => {
    if ($(event.target).val().length > 0) {
      $.ajax({
        type: 'GET',
        url: '/api/search_duplicate/' + $(event.target).val(),
        dataType: "json",
        success: function(data) {
            showDuplicates(data, $(event.target).closest(".card-body"));
        }
      })
    } else {
      removeDuplicationCheckMessage();
    }
  });
  $("#id_word_type").trigger("change");
});