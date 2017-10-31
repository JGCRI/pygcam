// Keeps terminal scrolled to the bottom
function updateScroll() {
    var elt = document.getElementById("terminal");
     
    elt.scrollTop = elt.scrollHeight;
}

// each 1.5 secs
var foo = setInterval(updateScroll, 1500);