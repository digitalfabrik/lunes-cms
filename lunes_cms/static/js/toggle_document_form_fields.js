if (!$) {
  $ = django.jQuery;
}

// Toggle the plural field depending on the chosen word type
$(document).ready(() => {
  const togglePluralWordInput = () => {
    const isNoun = $("#id_word_type").val() === "Nomen";
    $("#id_plural").closest("div.row").toggle(isNoun);
  };

  $("#id_word_type").change(togglePluralWordInput);
  togglePluralWordInput();
});

// Toggle the drop down for grammatical gender depending on the chosen word type
$(document).ready(() => {
  const toggleGenderDropdown = () => {
    const isNoun = $("#id_word_type").val() === "Nomen";
    $("#id_grammatical_gender").closest("div.row").toggle(isNoun);
  };

  $("#id_word_type").change(toggleGenderDropdown);
  toggleGenderDropdown();
});


// Detect changes in the "word" field and search for a duplicate
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

// Create and show message whether there is a possible duplicate
function showDuplicates(data, parent) {
  removeDuplicationCheckMessage();

  if (data["word"]) {
    // If there is a duplicated word, use orange background
    result = createSearchResultField("#ffbb4a");

    // Show alert message
    addDetailInfo(result, data["message"], "normal");

    // Show the duplicated word with its word type
    addDetailInfo(result, data["word"], "bold");

    // Show its definition too for more detail
    addDetailInfo(result, data["definition"], "normal");

    // Show related training sets
    addDetailInfo(result, data["training_sets"], "normal");
  } else {
    // If there is no duplicate, use green background
    result = createSearchResultField("#72f399");

    // Show message that no duplicate was found
    addDetailInfo(result, data["message"], "normal");
  }
  
  parent.prepend(result);
}

// Create a zone in which result duplicate search will be shown
function createSearchResultField(backgroundColor){
  messageField = document.createElement("div");
  messageField.setAttribute("id", "result");
  messageField.style.padding = "25px";
  messageField.style.backgroundColor = backgroundColor;

  return messageField;
}

// Create and add detail information
function addDetailInfo(resultField, info, fontWeight) {
  detailInfoField = document.createElement("div");
  detailInfoField.style.fontWeight = fontWeight;
  detailInfo = document.createTextNode(info);
  detailInfoField.append(detailInfo);
  resultField.append(detailInfoField);
}

// Remove the duplicate search result
function removeDuplicationCheckMessage(){
  const existingMessage = document.getElementById("result");

  if (existingMessage) {
    existingMessage.remove();
  }
}
