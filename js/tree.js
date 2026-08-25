/* Family tree for the heritage page. Progressive: the page ships a nested <ol>
   that reads fine on its own, and this replaces it with a pan/zoom SVG. If the
   fetch or the parse fails, the outline stays. */
(function () {
  "use strict";

  var root = document.querySelector(".tree");
  if (!root || !window.fetch || !document.createElementNS) return;

  var stage = root.querySelector(".tree__stage");
  var panel = root.querySelector(".tree__panel");
  var fallback = root.querySelector(".tree__fallback");
  if (!stage || !panel) return;

  var NS = "http://www.w3.org/2000/svg";
  var BOX_W = 210, BOX_H = 44, GAP_X = 22, GAP_Y = 58;

  function el(name, attrs) {
    var node = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs[k] != null) node.setAttribute(k, attrs[k]);
    return node;
  }

  /* --- Layout: tidy tree, one pass down for x, one up for parent centring --- */

  function layout(data) {
    var seen = {}, nodes = [], cursor = 0, placed = {}, merges = [];

    function walk(id, depth, parentId) {
      if (!data.people[id]) return null;
      if (seen[id]) {                       // lines converging on one descendant
        if (parentId) merges.push([parentId, id]);
        return null;
      }
      seen[id] = true;
      var person = data.people[id];
      var kids = (person.children || [])
        .map(function (c) { return walk(c, depth + 1, id); })
        .filter(Boolean);
      var x;
      if (kids.length) {
        x = (kids[0].x + kids[kids.length - 1].x) / 2;   // centre over children
      } else {
        x = cursor;
        cursor += BOX_W + GAP_X;                          // next free column
      }
      var node = { id: id, person: person, depth: depth, x: x, y: depth * (BOX_H + GAP_Y), kids: kids };
      nodes.push(node);
      placed[id] = node;
      return node;
    }

    var trees = data.roots.map(function (r) {
      var before = cursor;
      var t = walk(r, 0, null);
      if (t && cursor === before) cursor += BOX_W + GAP_X;
      cursor += BOX_W;                                    // gap between roots
      return t;
    }).filter(Boolean);

    var joins = merges.map(function (pair) {
      return { from: placed[pair[0]], to: placed[pair[1]] };
    }).filter(function (j) { return j.from && j.to; });

    return { nodes: nodes, trees: trees, joins: joins };
  }

  /* --- Render ------------------------------------------------------------- */

  function draw(data) {
    var laid = layout(data);
    if (!laid.nodes.length) return false;

    var xs = laid.nodes.map(function (n) { return n.x; });
    var ys = laid.nodes.map(function (n) { return n.y; });
    var minX = Math.min.apply(null, xs) - 30;
    var maxX = Math.max.apply(null, xs) + BOX_W + 30;
    var maxY = Math.max.apply(null, ys) + BOX_H + 30;

    var svg = el("svg", {
      viewBox: minX + " -30 " + (maxX - minX) + " " + (maxY + 30),
      role: "group",
      "aria-label": "Descendant tree"
    });
    var camera = el("g", {});
    svg.appendChild(camera);

    var edges = el("g", {});
    var boxes = el("g", {});
    camera.appendChild(edges);
    camera.appendChild(boxes);

    laid.nodes.forEach(function (n) {
      n.kids.forEach(function (k) {
        var y1 = n.y + BOX_H, y2 = k.y, mid = y1 + (y2 - y1) / 2;
        edges.appendChild(el("path", {
          class: "tree__edge",
          d: "M" + (n.x + BOX_W / 2) + "," + y1 +
             " V" + mid + " H" + (k.x + BOX_W / 2) + " V" + y2
        }));
      });
    });

    (laid.joins || []).forEach(function (j) {
      var y1 = j.from.y + BOX_H, y2 = j.to.y, mid = y1 + (y2 - y1) / 2;
      edges.appendChild(el("path", {
        class: "tree__edge tree__edge--join",
        d: "M" + (j.from.x + BOX_W / 2) + "," + y1 +
           " V" + mid + " H" + (j.to.x + BOX_W / 2) + " V" + y2
      }));
    });

    laid.nodes.forEach(function (n) {
      var p = n.person;
      var kind = p.living ? "living" : (p.kind || "documented");
      var g = el("g", {
        class: "tree__node",
        "data-kind": kind,
        "data-id": n.id,
        transform: "translate(" + n.x + "," + n.y + ")",
        tabindex: "0",
        role: "button",
        "aria-label": p.name + (p.birth || p.death ? ", " + (p.birth || "?") + " to " + (p.death || "?") : "")
      });
      g.appendChild(el("rect", { width: BOX_W, height: BOX_H }));

      var name = el("text", { x: 10, y: 19 });
      name.textContent = fit(p.name, 30);
      g.appendChild(name);

      if (p.birth || p.death) {
        var dates = el("text", { x: 10, y: 34, class: "n-dates" });
        dates.textContent = (p.birth || "?") + "–" + (p.death || "?");
        g.appendChild(dates);
      } else if (kind !== "documented") {
        var tag = el("text", { x: 10, y: 34, class: "n-dates" });
        tag.textContent = kind === "living" ? "WITHHELD" : "PLACEHOLDER";
        g.appendChild(tag);
      }
      boxes.appendChild(g);
    });

    stage.textContent = "";
    stage.appendChild(svg);
    if (fallback) fallback.hidden = true;

    wire(svg, camera, root, data);
    return true;
  }

  function fit(text, max) {
    return text && text.length > max ? text.slice(0, max - 1) + "…" : (text || "");
  }

  /* --- Interaction: pan, zoom, select ------------------------------------- */

  function wire(svg, camera, root, data) {
    var scale = 1, tx = 0, ty = 0, dragging = false, lastX = 0, lastY = 0;

    function apply() {
      camera.setAttribute("transform",
        "translate(" + tx + "," + ty + ") scale(" + scale + ")");
    }
    function zoom(factor) {
      scale = Math.min(2.5, Math.max(0.3, scale * factor));
      apply();
    }
    function reset() { scale = 1; tx = 0; ty = 0; apply(); }

    stage.addEventListener("pointerdown", function (e) {
      if (e.target.closest(".tree__node")) return;
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      stage.classList.add("is-panning");
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      tx += e.clientX - lastX; ty += e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      apply();
    });
    ["pointerup", "pointercancel"].forEach(function (evt) {
      stage.addEventListener(evt, function () {
        dragging = false; stage.classList.remove("is-panning");
      });
    });
    stage.addEventListener("wheel", function (e) {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12);
    }, { passive: false });

    root.querySelectorAll("[data-tree-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var a = btn.getAttribute("data-tree-action");
        if (a === "in") zoom(1.2);
        else if (a === "out") zoom(1 / 1.2);
        else reset();
      });
    });

    function select(g) {
      svg.querySelectorAll(".tree__node.is-selected").forEach(function (n) {
        n.classList.remove("is-selected");
      });
      g.classList.add("is-selected");
      show(data.people[g.getAttribute("data-id")]);
    }

    svg.addEventListener("click", function (e) {
      var g = e.target.closest(".tree__node");
      if (g) select(g);
    });
    svg.addEventListener("focusin", function (e) {
      var g = e.target.closest(".tree__node");
      if (g) select(g);
    });
    svg.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      var g = e.target.closest(".tree__node");
      if (g) { e.preventDefault(); select(g); }
    });

    apply();
  }

  function show(p) {
    if (!p) return;
    panel.textContent = "";
    var h = document.createElement("h3");
    h.textContent = p.name;
    panel.appendChild(h);

    var bits = [];
    if (p.birth || p.death) bits.push((p.birth || "?") + "–" + (p.death || "?"));
    if (p.living) bits.push("details withheld");
    else if (p.kind === "placeholder") bits.push("placeholder");
    if (p.place) bits.push(p.place);
    if (bits.length) {
      var m = document.createElement("p");
      m.className = "meta";
      m.textContent = bits.join("  ·  ");
      panel.appendChild(m);
    }
    var note = document.createElement("p");
    if (p.living) {
      note.className = "empty";
      note.textContent = "Living individuals are withheld from this page. " +
        "Their names and dates are not present in the published data.";
    } else {
      note.textContent = p.note || "";
    }
    if (note.textContent) panel.appendChild(note);
  }

  /* --- Boot --------------------------------------------------------------- */

  fetch("/data/tree.json", { credentials: "omit" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      if (!draw(data)) return;
      var hint = root.querySelector(".tree__hint");
      if (hint) hint.textContent = "drag to pan · scroll to zoom";
    })
    .catch(function () { /* outline stays; nothing to do */ });
})();
