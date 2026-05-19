/** Crisis console: favicon, theme CSS, recommendation review styling */
(function () {
  var CSS_HREF = "/public/crisis.css?v=crisis9";
  var APP_TITLE = "Smart City Crisis Management";
  var APP_SUBTITLE =
    "Emergency Operations Center \u2014 Incident Analysis Console";

  function ensureStyles() {
    var existing = document.getElementById("crisis-theme-css");
    if (existing) {
      return;
    }
    var link = document.createElement("link");
    link.id = "crisis-theme-css";
    link.rel = "stylesheet";
    link.href = CSS_HREF;
    document.head.appendChild(link);
  }

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

  function syncRecCardActions() {
    document.querySelectorAll(".crisis-rec-card").forEach(function (card) {
      var root =
        card.closest('[class*="step"]') ||
        card.closest('[class*="message"]') ||
        card.parentElement;
      if (!root) return;

      var buttons = [];
      root.querySelectorAll("button").forEach(function (btn) {
        var label = (btn.textContent || "").trim();
        if (ACTION_COLORS[label]) buttons.push({ btn: btn, label: label });
      });
      if (!buttons.length) return;

      var hasUndoApprove = buttons.some(function (b) {
        return b.label === "Undo Approve";
      });
      var hasUndoReject = buttons.some(function (b) {
        return b.label === "Undo Reject";
      });

      if (hasUndoApprove) {
        buttons.forEach(function (b) {
          b.btn.style.display = b.label === "Undo Approve" ? "" : "none";
        });
        return;
      }
      if (hasUndoReject) {
        buttons.forEach(function (b) {
          b.btn.style.display = b.label === "Undo Reject" ? "" : "none";
        });
        return;
      }

      var lastApprove = null;
      var lastReject = null;
      buttons.forEach(function (b) {
        if (b.label === "Approve") lastApprove = b.btn;
        if (b.label === "Reject") lastReject = b.btn;
      });
      buttons.forEach(function (b) {
        if (b.label === "Approve") {
          b.btn.style.display = b.btn === lastApprove ? "" : "none";
        } else if (b.label === "Reject") {
          b.btn.style.display = b.btn === lastReject ? "" : "none";
        } else {
          b.btn.style.display = "none";
        }
      });
    });
  }

  function styleRecCards() {
    ensureStyles();

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

    document.querySelectorAll(".crisis-rec-card").forEach(function (card) {
      var root =
        card.closest('[class*="step"]') ||
        card.closest('[class*="message"]') ||
        card.parentElement;
      if (!root) return;
      root.querySelectorAll("button").forEach(function (btn) {
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
    });

    syncRecCardActions();
  }

  function applyHeaderBranding() {
    var header = document.querySelector("header");
    if (!header) {
      return;
    }
    var existingDetails = header.querySelector(".crisis-header-details");
    if (existingDetails && existingDetails.textContent === APP_SUBTITLE) {
      return;
    }
    var logoLink = header.querySelector('a[href="/"]');
    if (!logoLink) {
      return;
    }

    var titleEl =
      header.querySelector(".crisis-header-main") ||
      header.querySelector(".crisis-header-title") ||
      header.querySelector(".truncate") ||
      header.querySelector("span.font-medium") ||
      logoLink.nextElementSibling;

    if (!titleEl || titleEl.tagName === "IMG") {
      var parent = logoLink.parentElement;
      if (parent) {
        titleEl = document.createElement("div");
        titleEl.className = "flex flex-col";
        logoLink.insertAdjacentElement("afterend", titleEl);
      }
    }

    var brand = header.querySelector(".crisis-header-brand");
    if (!brand) {
      brand = document.createElement("div");
      brand.className = "crisis-header-brand flex flex-col";
      if (titleEl && titleEl.parentElement) {
        titleEl.parentElement.insertBefore(brand, titleEl);
        brand.appendChild(titleEl);
      } else {
        logoLink.insertAdjacentElement("afterend", brand);
      }
    }

    titleEl = brand.querySelector(".crisis-header-main") || titleEl;
    if (titleEl) {
      titleEl.classList.add("crisis-header-main");
      titleEl.classList.remove("truncate");
      titleEl.textContent = APP_TITLE;
      titleEl.style.overflow = "visible";
      titleEl.style.textOverflow = "clip";
      titleEl.style.maxWidth = "none";
    }

    var details = brand.querySelector(".crisis-header-details");
    if (!details) {
      details = document.createElement("span");
      details.className = "crisis-header-details";
      brand.appendChild(details);
    }
    details.textContent = APP_SUBTITLE;
  }

  function hideConversationStarters() {
    document.querySelectorAll('[data-testid="starter"]').forEach(function (btn) {
      var row = btn.closest("div.flex") || btn.parentElement;
      if (row) row.style.display = "none";
    });
  }

  function initSidebarTabs() {
    document.querySelectorAll(".crisis-sidebar-tabs").forEach(function (root) {
      if (root.dataset.crisisTabsBound) return;
      root.dataset.crisisTabsBound = "1";
      var buttons = root.querySelectorAll("[data-crisis-tab]");
      var panels = root.querySelectorAll("[data-crisis-panel]");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var tab = btn.getAttribute("data-crisis-tab");
          buttons.forEach(function (b) {
            b.classList.toggle("active", b === btn);
          });
          panels.forEach(function (panel) {
            var show = panel.getAttribute("data-crisis-panel") === tab;
            if (show) {
              panel.removeAttribute("hidden");
              panel.classList.add("active");
            } else {
              panel.setAttribute("hidden", "hidden");
              panel.classList.remove("active");
            }
          });
        });
      });
    });
  }

  function run() {
    ensureStyles();
    applyFavicon();
    applyHeaderBranding();
    hideConversationStarters();
    styleRecCards();
    initSidebarTabs();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }

  var obs = new MutationObserver(function () {
    applyHeaderBranding();
    hideConversationStarters();
    styleRecCards();
    initSidebarTabs();
  });
  obs.observe(document.body, { childList: true, subtree: true });
})();
