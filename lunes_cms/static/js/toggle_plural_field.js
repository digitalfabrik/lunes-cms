if (!$) {
  $ = django.jQuery;
}

$(document).ready(() => {
  $("#id_word_type").change((event) =>
    $("#id_plural")
      .closest("div.row")
      .toggle($(event.target).val() == "Nomen"),
  );
  $("#id_word_type").trigger("change");
});

$(document).ready(() => {
  $("#id_word_type").change((event) =>
    $("#id_grammatical_gender")
      .closest("div.row")
      .toggle($(event.target).val() == "Nomen"),
  );
  $("#id_word_type").trigger("change");
});
