if (!$) {
  $ = django.jQuery;
}

$(document).ready(() => {
  $("#id_word_type").change((event) =>
    $("#id_plural")
      .closest("div.row")
      .toggle($(event.target).val() == "Nomen")
  );
  $("#id_word_type").trigger("change");
});

$(document).ready(() => {
  $("#id_job_title_feminin_singluar").closest("div.row").hide()
  $("#id_job_title_masculin_singluar").closest("div.row").hide()
  $("#id_job_title_neutrum_singluar").closest("div.row").hide()
  $("#id_word_type").change((event) =>
    $("#id_job_title_feminin_singluar,#id_job_title_masculin_singluar,#id_job_title_neutrum_singluar")
      .closest("div.row")
      .toggle($(event.target).val() == "Personenbezeichnung") 
  );
  $("#id_word_type").trigger("change");
});
