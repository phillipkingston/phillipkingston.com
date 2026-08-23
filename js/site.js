/* phillipkingston.com — progressive enhancements. The page is fully usable
   without this file: rail links are plain anchors and the theme follows the OS. */
(function () {
  "use strict";

  var root = document.documentElement;

  /* --- Theme toggle: auto -> light -> dark ------------------------------- */

  var btn = document.getElementById("theme-toggle");
  var label = document.getElementById("theme-label");

  function read() {
    try {
      var v = localStorage.getItem("theme");
      return v === "light" || v === "dark" ? v : "auto";
    } catch (e) {
      return "auto";
    }
  }

  function apply(mode) {
    if (mode === "auto") {
      delete root.dataset.theme;
      try { localStorage.removeItem("theme"); } catch (e) {}
    } else {
      root.dataset.theme = mode;
      try { localStorage.setItem("theme", mode); } catch (e) {}
    }
    if (label) label.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
    if (btn) btn.setAttribute("aria-label", "Colour theme: " + mode + ". Click to change.");
  }

  if (btn) {
    var order = ["auto", "light", "dark"];
    apply(read());
    btn.hidden = false;
    btn.addEventListener("click", function () {
      apply(order[(order.indexOf(read()) + 1) % order.length]);
    });
  }

  /* --- Reading progress -------------------------------------------------- */

  var bar = document.querySelector(".progress");
  var ticking = false;

  function progress() {
    ticking = false;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    bar.style.setProperty("--p", Math.min(100, Math.max(0, pct)).toFixed(2) + "%");
  }

  if (bar) {
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(progress); }
    }, { passive: true });
    progress();
  }

  /* --- Scroll-spy for the contents rail ---------------------------------- */

  var links = Array.prototype.slice.call(document.querySelectorAll(".rail__list a"));
  if (!links.length || !("IntersectionObserver" in window)) return;

  var byId = {};
  var targets = [];
  links.forEach(function (a) {
    var el = document.getElementById(a.hash.slice(1));
    if (!el) return;
    byId[el.id] = a;
    targets.push(el);
  });

  var visible = new Set();

  function mark() {
    var current = null;
    targets.forEach(function (el) {
      if (visible.has(el.id)) current = current || el.id;
    });
    links.forEach(function (a) {
      if (byId[current] === a) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) visible.add(e.target.id);
      else visible.delete(e.target.id);
    });
    mark();
  }, { rootMargin: "-10% 0px -70% 0px", threshold: 0 });

  targets.forEach(function (el) { io.observe(el); });
})();
