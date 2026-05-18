/** Force crisis favicon (cache-bust; Chrome prefers .ico over cached Chainlit SVG). */
(function () {
  var href = "/favicon?v=crisis1";
  function apply() {
    document.querySelectorAll('link[rel*="icon"]').forEach(function (el) {
      el.remove();
    });
    var link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/x-icon";
    link.href = href;
    document.head.appendChild(link);
    var png = document.createElement("link");
    png.rel = "icon";
    png.type = "image/png";
    png.sizes = "32x32";
    png.href = "/public/favicon.png?v=crisis1";
    document.head.appendChild(png);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
