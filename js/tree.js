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

  /* --- Layout ------------------------------------------------------------
     One tidy-tree engine, two directions. An Ancestry export is a pedigree:
     many single-child chains converging on one living descendant, so
     "ancestry" walks parents rightward from the focal person and is the
     default. "descent" walks children downward from every progenitor. */

  var CROSS_GAP = 14;

  function layout(data, mode) {
    var horizontal = mode === "ancestry";
    var edgeKey = horizontal ? "parents" : "children";
    var starts = horizontal
      ? (data.focal ? [data.focal] : data.roots)
      : data.roots;

    var seen = {}, nodes = [], placed = {}, merges = [], cursor = 0;
    var step = horizontal ? BOX_H + CROSS_GAP : BOX_W + GAP_X;
    var perGen = {};                     // rows already used in each generation

    function walk(id, gen, fromId) {
      if (!data.people[id]) return null;
      if (seen[id]) {
        if (fromId) merges.push([fromId, id]);
        return null;
      }
      seen[id] = true;
      var person = data.people[id];
      var myRow = null;
      if (horizontal) {                  // pack each generation column densely
        perGen[gen] = (perGen[gen] || 0);
        myRow = perGen[gen] * step;
        perGen[gen] += 1;
      }
      var next = (person[edgeKey] || [])
        .map(function (c) { return walk(c, gen + 1, id); })
        .filter(Boolean);

      var cross;
      if (horizontal) {
        cross = myRow;
      } else if (next.length) {
        cross = (next[0].cross + next[next.length - 1].cross) / 2;
      } else {
        cross = cursor;
        cursor += step;
      }
      var node = {
        id: id, person: person, gen: gen, cross: cross, kids: next,
        x: horizontal ? gen * (BOX_W + GAP_X) : cross,
        y: horizontal ? cross : gen * (BOX_H + GAP_Y)
      };
      nodes.push(node);
      placed[id] = node;
      return node;
    }

    starts.forEach(function (r) {
      var before = cursor;
      walk(r, 0, null);
      if (cursor === before) cursor += step;
      cursor += step;                                  // gap between lineages
    });

    var joins = merges.map(function (pair) {
      return { from: placed[pair[0]], to: placed[pair[1]] };
    }).filter(function (j) { return j.from && j.to; });

    return { nodes: nodes, joins: joins, horizontal: horizontal };
  }

  /* --- Render ------------------------------------------------------------- */

  function edgePath(a, b, horizontal) {
    if (horizontal) {
      var x1 = a.x + BOX_W, x2 = b.x, mx = x1 + (x2 - x1) / 2;
      return "M" + x1 + "," + (a.y + BOX_H / 2) +
             " H" + mx + " V" + (b.y + BOX_H / 2) + " H" + x2;
    }
    var y1 = a.y + BOX_H, y2 = b.y, my = y1 + (y2 - y1) / 2;
    return "M" + (a.x + BOX_W / 2) + "," + y1 +
           " V" + my + " H" + (b.x + BOX_W / 2) + " V" + y2;
  }

  function draw(data, mode) {
    var laid = layout(data, mode);
    if (!laid.nodes.length) return false;

    var pad = 34;
    var minX = Math.min.apply(null, laid.nodes.map(function (n) { return n.x; })) - pad;
    var maxX = Math.max.apply(null, laid.nodes.map(function (n) { return n.x; })) + BOX_W + pad;
    var minY = Math.min.apply(null, laid.nodes.map(function (n) { return n.y; })) - pad;
    var maxY = Math.max.apply(null, laid.nodes.map(function (n) { return n.y; })) + BOX_H + pad;

    var bounds = { minX: minX, minY: minY, maxX: maxX, maxY: maxY };
    var stageW = stage.clientWidth || 900, stageH = stage.clientHeight || 480;
    var svg = el("svg", {
      viewBox: "0 0 " + stageW + " " + stageH,
      preserveAspectRatio: "xMinYMin meet",
      role: "group",
      "aria-label": mode === "ancestry"
        ? "Ancestral pedigree, generations to the right"
        : "Descendant tree, generations downward"
    });
    var camera = el("g", {});
    svg.appendChild(camera);
    var edges = el("g", {});
    var boxes = el("g", {});
    camera.appendChild(edges);
    camera.appendChild(boxes);

    laid.nodes.forEach(function (n) {
      n.kids.forEach(function (k) {
        edges.appendChild(el("path", {
          class: "tree__edge", d: edgePath(n, k, laid.horizontal)
        }));
      });
    });
    laid.joins.forEach(function (j) {
      edges.appendChild(el("path", {
        class: "tree__edge tree__edge--join",
        d: edgePath(j.from, j.to, laid.horizontal)
      }));
    });

    laid.nodes.forEach(function (n) {
      var p = n.person;
      var kind = p.living ? "living" : (p.kind || "documented");
      var g = el("g", {
        class: "tree__node",
        "data-kind": kind,
        "data-sept": p.sept || null,
        "data-id": n.id,
        transform: "translate(" + n.x + "," + n.y + ")",
        tabindex: "0",
        role: "button",
        "aria-label": p.name +
          (p.birth || p.death ? ", " + (p.birth || "unknown") + " to " + (p.death || "unknown") : "")
      });
      g.appendChild(el("rect", { width: BOX_W, height: BOX_H }));
      if (p.sept) g.appendChild(el("rect", { class: "n-sept", width: 3, height: BOX_H }));

      var name = el("text", { x: 10, y: 19 });
      name.textContent = fit(p.name, 30);
      g.appendChild(name);

      var sub = el("text", { x: 10, y: 34, class: "n-dates" });
      if (p.birth || p.death) sub.textContent = (p.birth || "?") + "\u2013" + (p.death || "?");
      else if (kind === "living") sub.textContent = "WITHHELD";
      else if (kind === "placeholder") sub.textContent = "PLACEHOLDER";
      if (sub.textContent) g.appendChild(sub);

      boxes.appendChild(g);
    });

    stage.textContent = "";
    stage.appendChild(svg);
    if (fallback) fallback.hidden = true;

    wire(svg, camera, root, data, bounds, laid);
    return true;
  }

  function fit(text, max) {
    return text && text.length > max ? text.slice(0, max - 1) + "\u2026" : (text || "");
  }

  /* --- Interaction: pan, zoom, select ------------------------------------- */

  function wire(svg, camera, root, data, bounds, laid) {
    var scale = 1, tx = 0, ty = 0, dragging = false, lastX = 0, lastY = 0;
    var stageW = stage.clientWidth || 900, stageH = stage.clientHeight || 480;

    function apply() {
      camera.setAttribute("transform",
        "translate(" + tx + "," + ty + ") scale(" + scale + ")");
    }
    function zoom(factor, cx, cy) {
      var next = Math.min(2.5, Math.max(0.08, scale * factor));
      cx = cx == null ? stageW / 2 : cx;
      cy = cy == null ? stageH / 2 : cy;
      tx = cx - (cx - tx) * (next / scale);          // zoom about the cursor
      ty = cy - (cy - ty) * (next / scale);
      scale = next;
      apply();
    }
    function start() {                               // open on generation zero
      var first = laid.nodes.reduce(function (best, n) {
        return !best || n.gen < best.gen || (n.gen === best.gen && n.cross < best.cross)
          ? n : best;
      }, null) || laid.nodes[0];
      scale = 1;
      tx = 40 - first.x;
      ty = 28 - first.y;
      apply();
    }
    function fit() {
      var w = bounds.maxX - bounds.minX, h = bounds.maxY - bounds.minY;
      scale = Math.min(stageW / w, stageH / h, 1);
      tx = (stageW - w * scale) / 2 - bounds.minX * scale;
      ty = (stageH - h * scale) / 2 - bounds.minY * scale;
      apply();
    }

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
      var box = stage.getBoundingClientRect();
      zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - box.left, e.clientY - box.top);
    }, { passive: false });

    root.querySelectorAll("[data-tree-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var a = btn.getAttribute("data-tree-action");
        if (a === "in") zoom(1.2);
        else if (a === "out") zoom(1 / 1.2);
        else if (a === "fit") fit();
        else start();
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

    start();
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
    if (p.sept) bits.push("sept name: " + p.sept.replace(/^./, function (c) { return c.toUpperCase(); }));
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

  var TREE = null, MODE = "ancestry";

  function render(mode) {
    if (!TREE) return;
    MODE = mode;
    draw(TREE, mode);
    root.querySelectorAll("[data-tree-mode]").forEach(function (b) {
      var on = b.getAttribute("data-tree-mode") === mode;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("is-on", on);
    });
    panel.textContent = "";
    var hint = document.createElement("p");
    hint.className = "empty";
    hint.textContent = "Select a person to see their details.";
    panel.appendChild(hint);
  }

  fetch("/data/tree.json", { credentials: "omit" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      TREE = data;
      root.querySelectorAll("[data-tree-mode]").forEach(function (b) {
        b.hidden = false;
        b.addEventListener("click", function () {
          render(b.getAttribute("data-tree-mode"));
        });
      });
      render(data.focal ? "ancestry" : "descent");
      var hint = root.querySelector(".tree__hint");
      if (hint) hint.textContent = "drag to pan \u00b7 scroll to zoom";
    })
    .catch(function () { /* outline stays; nothing to do */ });
})();
