var documents = [];
var documents_correct = 0;
var documents_almost_correct = 0;
var documents_wrong = 0;
var old_document;
var wrong_answer = false;

/*
 * Get available training sets from API and fill select
 */
function get_available_sets() {
  $.ajax({
    type: 'GET',
    url: '/sets',
    dataType: "json",
    async:false,
    success: function(data) {
      for (var i = 0; i < data.length; i++) {
        $("#select_training_set").append('<option id=' + data[i]["pk"] + ' value=' + data[i]["pk"] + '>' + data[i]["fields"]["title"] + '</option>');
      }
    }
  });
}

/*
 * If user has selected a training set, load its documents (words) and start training session
 */
function get_documents() {
  var result;
  $.ajax({
    type: 'GET',
    url: '/set/'+$("#select_training_set").val()+'/documents',
    dataType: "json",
    async:false,
    success: function(data) {
      result = data;
    }
  });
  return result;
}

/*
 * Select a random new document out of the array of existing documents and then remove it. Return removed element.
 */
function get_random_document() {
  var document_index = Math.floor(Math.random() * documents.length);
  var new_document = documents[document_index];
  documents.splice(document_index, 1);
  return new_document;
}

/*
 * Render HTML code that shows the user a new image and input text field
 */
function render_question(new_document) {
  var html =  '<img class="img-fluid rounded" style="max-width: 90%;" src="/media/' + new_document["fields"]["image"] + '">' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              ((new_document["fields"]["audio"]) ? '<audio controls><source src="/media/'+ new_document["fields"]["audio"] +'" type="audio/ogg">Dein Browser unterstützt kein Audio.</audio>' +
              '<div class="col-xs-12" style="height:30px;"></div>' : '') +
              '<input id="input_word" class="form-control" type="text" placeholder="Wort eingeben" onkeypress="input_keypress(event);">' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              '<button type="button" class="btn btn-warning" onclick="solve_document();">Lösung</button> ' +
              '<button type="button" class="btn btn-success" onclick="next_document();">Nächstes Wort</button>';
  return html;
}

/*
 * Show results (correct/wrong) for training set.
 */
function render_end_result() {
  var html =  '<p>Gratulation, du hast die Lektion abgeschlossen. Dein Resultat:</p><p>' + documents_correct + ' Wörter waren korrekt.</p><p>' + documents_almost_correct + ' Wörter waren fast richtig.</p><p>' +
              documents_wrong + ' Wörter waren falsch.</p><p>Quote: ' + Math.round((documents_correct+documents_almost_correct)/(documents_correct+documents_almost_correct+documents_wrong)*100) + '%</p>' +
              '<button type="button" class="btn btn-primary" onclick="new_training_session();">Neu starten</button>';
  return html;
}

/*
 * Triggered by user clicking 'next'. Verifies the word the user wrote, shows next image or end results.
 */
function next_document() {
  if(old_document) {
  	var word_status = verify_document(old_document);
    if (word_status == 0) {
      if(!wrong_answer) {
        documents_wrong = documents_wrong + 1;
      }
      $("#input_word").addClass("invalid");
      wrong_answer = true;
      return;
    } else if (word_status == 2 && !wrong_answer) { 
    	documents_almost_correct = documents_almost_correct + 1;
    	$("#input_word").addClass("almost_valid");
    	$("#input_word").val(old_document["fields"]["word"]);
    	documents_correct = documents_correct - 1;
    	return;
    } else {
      if(!wrong_answer) {
        documents_correct = documents_correct + 1;
      }
    }
  }
  wrong_answer = false;
  if (documents.length == 0) {
    var html = render_end_result();
    reset_env();
  } else {
    var new_document = get_random_document();
    old_document = new_document;
    var html = render_question(new_document);
  }
  $("#div_ask_document").html(html);
}

/*
 * Calculate Levenshtein distance between user input and right answer
 */
// Compute the edit distance between the two given strings
function getEditDistance(word_a, word_b){
  if(word_a.length == 0) return word_b.length; 
  if(word_b.length == 0) return word_a.length; 

  var matrix = [];

  // increment along the first column of each row
  var i;
  for(i = 0; i <= word_b.length; i++){
    matrix[i] = [i];
  }

  // increment each column in the first row
  var j;
  for(j = 0; j <= word_a.length; j++){
    matrix[0][j] = j;
  }

  // Fill in the rest of the matrix
  for(i = 1; i <= word_b.length; i++){
    for(j = 1; j <= word_a.length; j++){
      if(word_b.charAt(i-1) == word_a.charAt(j-1)){
        matrix[i][j] = matrix[i-1][j-1];
      } else {
        matrix[i][j] = Math.min(matrix[i-1][j-1] + 1, // substitution
                                Math.min(matrix[i][j-1] + 1, // insertion
                                         matrix[i-1][j] + 1)); // deletion
      }
    }
  }

  return matrix[word_b.length][word_a.length];
};
/*
 * Verify if user input matches word
 */
function verify_document(old_document) {
  new_document = $("#input_word").val();
  distance = getEditDistance(old_document["fields"]["word"], new_document);
  if (old_document["fields"]["word"] == new_document) {
    return 1;
  } else if (distance == 1) {
    return 2;
  } else {
    return 0;
  }
}

/*
 * Provide answer if user does not know
 */
function solve_document() {
  wrong_answer = true;
  documents_wrong = documents_wrong + 1;
  $("#input_word").val(old_document["fields"]["word"]);
}

/*
 * Start a new training session. Either on training set select change or after session end.
 */
function new_training_session() {
  new_session = true;
  if (documents.length > 0) {
    if (!confirm('Bist du sicher, dass du eine neue Einheit starten möchtest?')) {
      new_session = false;
    }
  }
  if( $("#select_training_set").val() >= 0 && new_session ) {
    reset_env();
    documents = get_documents();
    next_document();
  }
}

/*
 * Reset global training session variables
 */
function reset_env() {
  documents = [];
  documents_correct = 0;
  documents_almost_correct = 0;
  documents_wrong = 0;
  old_document = false;
  wrong_answer = false;
}

/*
 * If user selects a set, start training session
 */
$( "#select_training_set" ).change(function() {
  new_training_session();
});

/*
 * Load available training sets after page load
 */
$( document ).ready(function() {
  reset_env();
  get_available_sets();
});

/*
 * Continue if user presses Enter in text input
 */
function input_keypress(e) {
  if (e.which == 13) {
    next_document();
    return false;
  }
};
