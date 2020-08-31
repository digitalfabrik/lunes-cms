var documents;
var documents_correct;
var documents_almost_correct;
var documents_wrong;
var current_document;
var matrix;

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
* Get available alternative words from API for a given document.
*/
function get_alternative_words(document){
  var result;
  $.ajax({
    type: 'GET',
    url: 'alternative_words/' + document["pk"],
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
 * Render HTML code that shows the user a new image, a new audio and input text field. 
 */
function render_question(new_document) {
  var html =  '<img class="img-fluid rounded" style="max-width: 90%;" src="/media/' + new_document["fields"]["image"] + '">' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              ((new_document["fields"]["audio"]) ? '<audio controls><source src="/media/'+ new_document["fields"]["audio"] +'" type="audio/ogg">Dein Browser unterstützt kein Audio.</audio>' +
              '<div class="col-xs-12" style="height:30px;"></div>' : '') +
              '<input id="input_word" class="form-control" type="text" placeholder="Wort eingeben" onkeypress="input_keypress(event);">' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              '<button type="button" class="btn btn-warning" onclick="solve_document();">Lösung</button> ' +
              '<button type="button" class="btn btn-success" onclick="check_current_document();">Überprüfen</button>';
  return html;
}

/*
 * Render HTML code that shows the user the current image, the current audio and text field with given input which is read-only.
 */
function render_question_solved(current_document, content_textfield) {
  var html =  '<img class="img-fluid rounded" style="max-width: 90%;" src="/media/' + current_document["fields"]["image"] + '">' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              ((current_document["fields"]["audio"]) ? '<audio controls><source src="/media/'+ current_document["fields"]["audio"] +'" type="audio/ogg">Dein Browser unterstützt kein Audio.</audio>' +
              '<div class="col-xs-12" style="height:30px;"></div>' : '') +
              '<input id="input_word" class="form-control" type="text" placeholder="'+ content_textfield + '" onkeypress="input_keypress(event);" readonly><br><br>' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              '<button type="button" class="btn btn-warning" onclick="load_new_document();">Nächstes Wort</button> '; 
  
  return html;
}

/*load
 * Show results (correct/wrong) for training set and provide buttons for new training sessions.
 */
function render_end_result() {
  var html =  '<p>Gratulation, du hast die Lektion abgeschlossen. Dein Resultat:</p><p>' + documents_correct.length + ' Wörter waren korrekt.</p><p>' + documents_almost_correct.length + ' Wörter waren fast richtig.</p><p>' +
              documents_wrong.length + ' Wörter waren falsch.</p><p>Quote: ' + Math.round((documents_correct.length+documents_almost_correct.length)/(documents_correct.length+documents_almost_correct.length+documents_wrong.length)*100) + '%</p>' +
              '<button type="button" class="btn btn-primary" onclick="mistake_training_session();">Fehler üben</button>' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              '<button type="button" class="btn btn-primary" onclick="new_training_session();">Neu starten</button>' +
              '<div class="col-xs-12" style="height:30px;"></div>' +
              '<button type="button" class="btn btn-primary" onclick="generatePDF();">Zusammenfassung</button>'
              ;

  return html;
}

/*
* Shows next image or end results.
*/
function load_new_document(){
  if (documents.length == 0) {
    var html = render_end_result();
  } else {
    current_document = get_random_document();;
    var html = render_question(current_document );
  }
  $("#div_ask_document").html(html);
}

/*
* Verifies the word the user wrote and calls functions to adapt UI fitting to verification.
*/
function check_current_document(){
  var word_status = verify_document(current_document);
  var content_textfield ;
  var styleClass ;
  switch(word_status){
    case 0:
      documents_wrong.push(current_document);
      content_textfield = $("#input_word").val();
      styleClass =  "invalid";
      break;
    case 2:
      documents_almost_correct.push(current_document);
      content_textfield = current_document["fields"]["word"];
      styleClass = "almost_valid";
      break;
    default:
      documents_correct.push(current_document);
      content_textfield = $("#input_word").val();
      styleClass = "valid";
    
  }
  var html = render_question_solved(current_document, content_textfield);
  $("#div_ask_document").html(html);
  $("#input_word").addClass(styleClass); 
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

  // increment each column in the first row.
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
 * Verify if user input matches word.
 */
function verify_document(old_document) {
  var new_document = $("#input_word").val();
  var alternive_words = get_alternative_words(old_document)
  var distance = getEditDistance(old_document["fields"]["word"], new_document);
  alternive_words.forEach(element => {
    if(distance > getEditDistance(element["fields"]["alt_word"], new_document))
      distance = getEditDistance(element["fields"]["alt_word"], new_document)
  })
  
  if (distance == 0) {
    return 1;
  } else if (distance == 1) {
    return 2;
  } else {
    return 0;
  }
}

/*
 * Provide answer if user does not know and calls functions to adapt UI.
 */
function solve_document() {
  documents_wrong.push(current_document);
  var html = render_question_solved(current_document, current_document["fields"] ["word"]);
  $("#div_ask_document").html(html);
  $("#input_word").addClass("solved");
}

/*
 * Start a new training session. Either on training set select change or after session end.
 */
function new_training_session() {
  if (documents.length > 0) {
    if (!confirm('Bist du sicher, dass du eine neue Einheit starten möchtest?')) {
      return;
    }
  }
  if ( $("#select_training_set").val() >= 0) {
    reset_env();
    documents = get_documents();
    load_new_document();
  }
}

/*
 * Start new training session with wrong words only.
 */

function mistake_training_session() {
  documents = documents_wrong.concat(documents_almost_correct);
  documents_correct = [];
  documents_almost_correct = [];
  documents_wrong = [];
  current_document = false;

  load_new_document();

}

/*
 * Reset global training session variables
 */
function reset_env() {
  documents = [];
  documents_correct = [];
  documents_almost_correct = [];
  documents_wrong = [];
  current_document = false;
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
    solve_document() ;
    return false;
  }
};

/*
* Load report template
*/
function get_report_template() {
  var report_template;
  $.ajax({
    type: 'GET',
    url: '/report',
    dataType: "html",
    async:false,
    success: function(data) {
      report_template = data
    }
  });
  return report_template
}

/*
* Create timestamp
*/
function get_timestamp() {
  var today = new Date();
  var date = today.getDate()+'.'+(today.getMonth()+1)+'.'+today.getFullYear();
  var minutes = today.getMinutes();
  if (String(minutes).length==1) {
    minutes = '0' + minutes
  }
  var time = today.getHours() + ":" + minutes;
  var dateTime = 'Erstellt am ' + date +' um '+ time +' Uhr';
  return dateTime
}
/*
* Prepare report
*/
function prepare_report(report_html) {
  var $report_html = $(report_html)

  //Timestamp
  $report_html.find('#timestamp').text(get_timestamp());

  //Trainingsset
  selected_set_id = '#' + $("#select_training_set").val();
  selected_set = $(selected_set_id).text()
  $report_html.find('#trainingsset').text('Bearbeitetes Set: ' + selected_set);

  //Allgemeine Ergebnise
  $report_html.find('#amt_correct').text(documents_correct.length)
  $report_html.find('#amt_alm_correct').text(documents_almost_correct.length)
  $report_html.find('#amt_wrong').text(documents_wrong.length)

  //Detaillierte Aufführung
  // yet to come
  return $report_html
}

/*
* Display the results as PDF
*/
function generatePDF() {
  var html = get_report_template();
  html = prepare_report(html);
  html = $('<div>').append(html.clone()).html();
  newWindow = window.open('about:blank', '_blank');
  newWindow.document.write(html)
  tab.document.close();
}
