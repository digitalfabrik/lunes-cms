/*
Adapting the footer to display "Tür an Tür Digitalfabrik gGmbH" instead
of "Jazzmin Version".
*/
document
    .getElementsByTagName("footer")[0]
    .getElementsByTagName("div")[0]
    .innerHTML = "<b>Tür an Tür Digitalfabrik gGmbH</b>";

/*
Display a custom avatar image which is available in /static/images/
*/
document
    .getElementsByClassName("sidebar")[0]
    .getElementsByTagName("img")[0]
    .src = "/static/images/user-avatar.png";
    
document
    .getElementsByClassName("sidebar")[0]
    .getElementsByTagName("img")[0]
    .style.height = "30px";

document
    .getElementsByClassName("sidebar")[0]
    .getElementsByTagName("img")[0]
    .style.width = "23px";