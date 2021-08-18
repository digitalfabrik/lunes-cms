document
    .getElementsByTagName("footer")[0]
    .getElementsByTagName("div")[0]
    .innerHTML = "<b>Tür an Tür Digitalfabrik gGmbH</b>";

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