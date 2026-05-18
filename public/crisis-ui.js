/** Crisis console: favicon + recommendation review styling */
(function () {
  function applyFavicon() {
    var href = "/favicon?v=crisis2";
    document.querySelectorAll('link[rel*="icon"]').forEach(function (el) {
      el.remove();
    });
    var link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/x-icon";
    link.href = href;
    document.head.appendChild(link);
  }

  var ACTION_COLORS = {
    Approve: "#16a34a",
    "Undo Approve": "#16a34a",
    Reject: "#dc2626",
    "Undo Reject": "#dc2626",
  };

  function styleRecCards() {
    document.querySelectorAll(".crisis-rec-card, .crisis-dispatch-wrap").forEach(function (card) {
      var step =
        card.closest('[class*="step"]') ||
        card.closest('[class*="message"]') ||
        card.closest("article");
      if (!step) return;
      step.querySelectorAll("img").forEach(function (img) {
        var alt = (img.getAttribute("alt") || "").toLowerCase();
        if (alt.indexOf("avatar") >= 0 || img.src.indexOf("/avatars/") >= 0) {
          img.style.display = "none";
        }
      });
      step.querySelectorAll('[class*="avatar"], [class*="Avatar"]').forEach(function (el) {
        el.style.display = "none";
      });
    });

    document.querySelectorAll("button").forEach(function (btn) {
      var label = (btn.textContent || "").trim();
      if (ACTION_COLORS[label]) {
        btn.style.color = ACTION_COLORS[label];
        btn.style.fontWeight = "600";
        btn.style.background = "transparent";
        btn.style.border = "none";
        btn.style.boxShadow = "none";
        btn.style.paddingLeft = "0";
        btn.style.paddingRight = "0.75rem";
        btn.style.pointerEvents = "auto";
        btn.style.cursor = "pointer";
      }
    });
  }

  function run() {
    applyFavicon();
    styleRecCards();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }

  var obs = new MutationObserver(function () {
    styleRecCards();
  });
  obs.observe(document.body, { childList: true, subtree: true });
})();
