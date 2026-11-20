// Edmonton charities map. Plain script, no libraries.
// Every string from the data is written with textContent or an attribute, never
// parsed as HTML: descriptions are free text from CRA (tests/test_build_site.py).
(function () {
  "use strict";

  const DATA_URL = document.currentScript.dataset.orgs;

  // CRA's four heads of charity, as its Codes Lists PDF (section 2.2) groups the
  // category codes: 0001-0002, 0010-0015, 0030-0090, 0100-0215.
  const HEADS = [
    { id: "poverty", label: "Relief of poverty", has: (c) => c < 10 },
    { id: "education", label: "Education", has: (c) => c >= 10 && c < 30 },
    { id: "religion", label: "Religion", has: (c) => c >= 30 && c < 100 },
    { id: "community", label: "Other community purposes", has: (c) => c >= 100 },
  ];
  const REVENUE = [
    ["under_50k", "Under $50k"], ["50k_250k", "$50k–250k"], ["250k_1m", "$250k–1M"],
    ["1m_5m", "$1M–5M"], ["5m_plus", "$5M and over"],
  ];
  const REVENUE_LABEL = Object.fromEntries(REVENUE);
  const FLAG_TEXT = {
    revenue_not_reported: "Revenue not reported on the T3010.",
    revenue_negative: "Reported a negative total revenue, so it has no revenue band.",
    staff_not_reported: "Staff numbers not reported.",
    paid_staff_not_reported: "Did not say whether it has paid staff.",
    paid_staff_zero_positions: "Says it has paid staff but reports no positions.",
    no_financial_row: "No financial return in the 2024 file.",
    no_general_info_row: "No general-information return in the 2024 file.",
    no_compensation_row: "Says it has paid staff but filed no staff schedule.",
    multiple_periods: "Filed for more than one period; the latest is shown.",
    periods_differ: "Its 2024 files cover different fiscal periods.",
    short_description: "Very short description, so its position is uncertain.",
    shared_description: "Shares its exact description with other charities.",
    website_unusable: "CRA's website field for this charity is not a web address.",
    category_not_decoded: "Its CRA category code is not in CRA's code list.",
    sub_category_not_decoded: "Its CRA sub-category code is not in CRA's code list.",
    designation_not_decoded: "Its CRA designation code is not in CRA's code list.",
    no_other_description: "It is the only charity with a description, so it has no position.",
  };
  const CRA_PAGE = "https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/chrtydtls/";
  const PAGE_SIZE = 100;

  const $ = (id) => document.getElementById(id);
  const canvas = $("map");
  const ctx = canvas.getContext("2d");
  const fmt = new Intl.NumberFormat("en-CA");

  let orgs = [];
  let byBn = new Map();
  let placed = [];
  let sharedText = new Map();
  const state = { q: "", area: "", muni: "", cat: "", rev: "", staff: "", head: "", selected: null, shown: PAGE_SIZE, list: null };
  // Screen = (tx + x * scale, ty - y * scale): one scale for both axes, y up.
  const view = { w: 0, h: 0, scale: 1, tx: 0, ty: 0, fit: 1 };
  let mainBox = null, allBox = null;
  let colors = {};

  // ---- DOM helpers: text only -------------------------------------------------
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "onclick") node.addEventListener("click", v);
      else if (k === "className") node.className = v;
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    for (const c of children.flat()) {
      if (c === null || c === undefined || c === false) continue;
      node.append(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    }
    return node;
  }
  function add(node, ...children) { node.append(...children.flat().filter((c) => c !== null && c !== undefined && c !== false)); }
  // The charity a link points at (#<BN>), or "" for none or a malformed hash.
  function hashBn() {
    try { return decodeURIComponent(location.hash.slice(1)); } catch (_) { return ""; }
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function headOf(o) { const c = Number(o.category_code); return HEADS.find((h) => h.has(c)); }
  function externalLink(href, text) {
    return el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text);
  }

  // ---- filtering ------------------------------------------------------------------
  function matches(o) {
    if (state.area && o.area !== state.area) return false;
    if (state.muni && o.municipality !== state.muni) return false;
    if (state.cat && o.category_code !== state.cat) return false;
    if (state.rev && (o.revenue_band || "none") !== state.rev) return false;
    if (state.staff && o.has_paid_staff !== state.staff) return false;
    return true;
  }
  function nameHit(o) {
    if (!state.q) return false;
    return o._search.includes(state.q);
  }
  function filtering() { return Boolean(state.area || state.muni || state.cat || state.rev || state.staff); }

  // ---- map ------------------------------------------------------------------------
  function readColors() {
    const s = getComputedStyle(document.documentElement);
    const v = (n) => s.getPropertyValue(n).trim();
    colors = { surface: v("--surface"), dot: v("--dot"), dim: v("--dot-dim"), ring: v("--ring"), hairline: v("--hairline"), muted: v("--muted") };
  }
  // The default view fits the bulk of the dots (2.5th to 97.5th percentile on
  // each axis), so a small far group doesn't shrink everything else; the status
  // line counts what is outside the view and "All" fits every dot.
  function boxes() {
    const q = (a, p) => a[Math.min(a.length - 1, Math.max(0, Math.round(p * (a.length - 1))))];
    const xs = placed.map((o) => o.x).sort((a, b) => a - b), ys = placed.map((o) => o.y).sort((a, b) => a - b);
    allBox = [xs[0], ys[0], xs[xs.length - 1], ys[ys.length - 1]];
    const b = [q(xs, 0.025), q(ys, 0.025), q(xs, 0.975), q(ys, 0.975)];
    const px = (b[2] - b[0]) * 0.08 || 0.05, py = (b[3] - b[1]) * 0.08 || 0.05;
    mainBox = [b[0] - px, b[1] - py, b[2] + px, b[3] + py];
  }
  function scaleFor(box) {
    return Math.max(1, Math.min((view.w - 40) / Math.max(1e-6, box[2] - box[0]), (view.h - 40) / Math.max(1e-6, box[3] - box[1])));
  }
  function fitBox(box) {
    view.scale = scaleFor(box);
    centreOn((box[0] + box[2]) / 2, (box[1] + box[3]) / 2);
  }
  function fitMain() { fitBox(mainBox); }
  function resize(keepCentre) {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const centre = keepCentre && view.w ? toWorld(view.w / 2, view.h / 2) : null;
    const zoom = view.scale / view.fit;
    view.w = r.width; view.h = r.height;
    canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    view.fit = scaleFor(mainBox);
    if (centre) { view.scale = view.fit * zoom; centreOn(centre[0], centre[1]); } else fitMain();
  }
  function toScreen(x, y) { return [view.tx + x * view.scale, view.ty - y * view.scale]; }
  function toWorld(sx, sy) { return [(sx - view.tx) / view.scale, (view.ty - sy) / view.scale]; }
  function centreOn(x, y) {
    view.tx = view.w / 2 - x * view.scale;
    view.ty = view.h / 2 + y * view.scale;
  }
  function zoomAt(sx, sy, factor) {
    const ns = Math.min(view.fit * 40, Math.max(scaleFor(allBox) * 0.8, view.scale * factor));
    const [wx, wy] = toWorld(sx, sy);
    view.scale = ns;
    view.tx = sx - wx * ns; view.ty = sy + wy * ns;
    draw();
  }
  function radius() { return Math.max(1.6, Math.min(7, 2.6 * Math.sqrt(view.scale / view.fit))); }

  let frame = 0;
  function draw() {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = 0; paint(); });
  }
  function paint() {
    ctx.fillStyle = colors.surface;
    ctx.fillRect(0, 0, view.w, view.h);
    updateOutside();
    const r = radius();
    const head = HEADS.find((h) => h.id === state.head);
    const on = [], off = [];
    for (const o of placed) {
      const lit = matches(o) && (!head || head.has(Number(o.category_code)));
      (lit ? on : off).push(o);
    }
    const dot = (o) => { const [x, y] = toScreen(o.x, o.y); ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2); };
    ctx.fillStyle = colors.dim; ctx.beginPath(); off.forEach(dot); ctx.fill();
    ctx.fillStyle = colors.dot; ctx.beginPath(); on.forEach(dot); ctx.fill();
    // A thin surface ring keeps overlapping dots apart.
    ctx.lineWidth = 1; ctx.strokeStyle = colors.surface; ctx.beginPath(); on.forEach(dot); ctx.stroke();

    const sel = state.selected && byBn.get(state.selected);
    if (sel && sel.x !== null) {
      const [sx, sy] = toScreen(sel.x, sel.y);
      ctx.strokeStyle = colors.muted; ctx.lineWidth = 1; ctx.beginPath();
      for (const [bn] of sel.neighbours) {
        const n = byBn.get(bn); if (!n || n.x === null) continue;
        const [nx, ny] = toScreen(n.x, n.y); ctx.moveTo(sx, sy); ctx.lineTo(nx, ny);
      }
      ctx.stroke();
      ctx.strokeStyle = colors.ring; ctx.lineWidth = 1.5; ctx.beginPath();
      for (const [bn] of sel.neighbours) {
        const n = byBn.get(bn); if (!n || n.x === null) continue;
        const [nx, ny] = toScreen(n.x, n.y); ctx.moveTo(nx + r + 2, ny); ctx.arc(nx, ny, r + 2, 0, Math.PI * 2);
      }
      ctx.stroke();
      ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(sx + r + 4, sy); ctx.arc(sx, sy, r + 4, 0, Math.PI * 2); ctx.stroke();
    }
    if (state.q) {
      ctx.strokeStyle = colors.ring; ctx.lineWidth = 2; ctx.beginPath();
      for (const o of placed) {
        if (!nameHit(o) || !matches(o)) continue;
        const [x, y] = toScreen(o.x, o.y); ctx.moveTo(x + r + 3, y); ctx.arc(x, y, r + 3, 0, Math.PI * 2);
      }
      ctx.stroke();
    }
  }
  function hit(sx, sy) {
    const lim = Math.max(10, radius() + 4);
    let best = null, bd = lim * lim;
    for (const o of placed) {
      const [x, y] = toScreen(o.x, o.y);
      const d = (x - sx) ** 2 + (y - sy) ** 2;
      if (d < bd) { bd = d; best = o; }
    }
    return best;
  }

  // ---- pointer interaction: drag to pan, wheel or pinch to zoom, tap to select -----
  const pointers = new Map();
  let drag = null, pinch = null;
  function local(e) { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, local(e));
    if (pointers.size === 1) {
      const [x, y] = local(e);
      drag = { x, y, tx: view.tx, ty: view.ty, moved: false };
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), scale: view.scale };
      drag = null;
    }
  });
  canvas.addEventListener("pointermove", (e) => {
    const p = local(e);
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, p);
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      zoomAt(mx, my, (pinch.scale * d / pinch.d) / view.scale);
      return;
    }
    if (drag) {
      const dx = p[0] - drag.x, dy = p[1] - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) > 4) { drag.moved = true; canvas.classList.add("dragging"); hideTip(); }
      if (drag.moved) { view.tx = drag.tx + dx; view.ty = drag.ty + dy; draw(); }
      return;
    }
    if (e.pointerType === "mouse") showTip(hit(p[0], p[1]), p);
  });
  function endPointer(e) {
    const p = local(e);
    if (drag && !drag.moved && pointers.size === 1) {
      const o = hit(p[0], p[1]);
      if (o) select(o.bn, false);
    }
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) { drag = null; canvas.classList.remove("dragging"); }
  }
  canvas.addEventListener("pointerup", endPointer);
  canvas.addEventListener("pointercancel", (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) { drag = null; canvas.classList.remove("dragging"); }
  });
  canvas.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hideTip(); });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const [x, y] = local(e);
    zoomAt(x, y, Math.exp(-e.deltaY * 0.0015));
  }, { passive: false });
  $("zoom-in").addEventListener("click", () => zoomAt(view.w / 2, view.h / 2, 1.6));
  $("zoom-out").addEventListener("click", () => zoomAt(view.w / 2, view.h / 2, 1 / 1.6));
  $("zoom-fit").addEventListener("click", () => { fitBox(allBox); draw(); });
  $("show-all").addEventListener("click", () => { fitBox(allBox); draw(); });

  const tip = $("tip");
  function showTip(o, p) {
    if (!o) return hideTip();
    tip.textContent = o.name;
    tip.hidden = false;
    const left = Math.min(p[0] + 12, view.w - tip.offsetWidth - 4);
    const top = p[1] + 14 + tip.offsetHeight > view.h ? p[1] - tip.offsetHeight - 8 : p[1] + 14;
    tip.style.left = Math.max(4, left) + "px";
    tip.style.top = Math.max(4, top) + "px";
    canvas.style.cursor = "pointer";
  }
  function hideTip() { tip.hidden = true; canvas.style.cursor = ""; }

  // ---- panel: list of matches, or a charity's card ---------------------------------
  const results = $("results"), card = $("card");

  function orgButton(o, extra) {
    const sub = o.x === null ? "not on the map" : extra || o.municipality;
    return el("li", null, el("button", { type: "button", onclick: () => select(o.bn, true) },
      el("span", null, o.name), el("span", { className: "sub" }, sub)));
  }
  function renderList() {
    card.hidden = true; results.hidden = false; clear(results);
    let items = null, title = null;
    if (state.list === "unplaced") {
      items = orgs.filter((o) => o.x === null && matches(o) && (!state.q || nameHit(o)));
      title = `${fmt.format(items.length)} charities not on the map`;
      results.append(el("button", { type: "button", className: "link-button back", onclick: () => { state.list = null; renderList(); } }, "← Back"),
        el("h2", null, title),
        el("p", { className: "note" }, "These charities filed no program description, so there is nothing to place them by. They are listed and searchable but have no dot."));
    } else if (state.q || filtering()) {
      items = orgs.filter((o) => matches(o) && (!state.q || nameHit(o)));
      title = `${fmt.format(items.length)} of ${fmt.format(orgs.length)} charities match`;
      results.append(el("h2", null, title));
    } else {
      const unplaced = orgs.filter((o) => o.x === null).length;
      results.append(
        el("h2", null, `${fmt.format(orgs.length)} registered charities`),
        el("p", null, `${fmt.format(placed.length)} are on the map. Dots close together describe similar work; the lines from a selected dot go to its ten most similar charities.`),
        el("p", null, "Search by name, filter by area, size or category, or highlight one of CRA's four groups of charitable purposes."),
        el("p", null, el("button", { type: "button", className: "link-button", onclick: () => { state.list = "unplaced"; state.shown = PAGE_SIZE; renderList(); } },
          `${fmt.format(unplaced)} charities with no description, not on the map`)));
      return;
    }
    items.sort((a, b) => a.name.localeCompare(b.name, "en-CA"));
    const ul = el("ul", { className: "list" }, items.slice(0, state.shown).map((o) => orgButton(o)));
    results.append(ul);
    if (items.length > state.shown) {
      results.append(el("button", { type: "button", className: "link-button", onclick: () => { state.shown += PAGE_SIZE; renderList(); } },
        `Show ${Math.min(PAGE_SIZE, items.length - state.shown)} more`));
    }
  }

  function revenueText(o) {
    if (o.revenue_band) return REVENUE_LABEL[o.revenue_band];
    return o.flags.includes("revenue_negative") ? "negative (no band)" : "not reported";
  }
  function staffText(o) {
    if (o.has_paid_staff === "no") return "No paid staff";
    if (o.has_paid_staff !== "yes") return "Paid staff not reported";
    const parts = [];
    if (o.staff_full_time !== null) parts.push(`${fmt.format(o.staff_full_time)} full-time`);
    if (o.staff_part_time !== null) parts.push(`${fmt.format(o.staff_part_time)} part-time`);
    return parts.length ? `Paid staff: ${parts.join(", ")}` : "Has paid staff (numbers not reported)";
  }
  function renderCard(o) {
    results.hidden = true; card.hidden = false; clear(card);
    const head = headOf(o);
    add(card, 
      el("button", { type: "button", className: "link-button back", onclick: closeCard }, "← Back to list"),
      el("h2", null, o.name),
      o.legal_name ? el("p", { className: "meta" }, `Legal name: ${o.legal_name}`) : null,
      el("p", { className: "meta" }, [o.category, o.sub_category].filter(Boolean).join(" · ") + (head ? ` (${head.label})` : "")),
      el("p", { className: "meta" }, `${o.area === "edmonton" ? "Edmonton" : `${o.municipality} (metro ring)`} · ${o.designation}`),
      el("p", { className: "meta" }, `Revenue: ${revenueText(o)} · ${staffText(o)}` + (o.fpe ? ` · fiscal year ending ${o.fpe}` : "")),
      el("div", { className: "links" },
        externalLink(CRA_PAGE + encodeURIComponent(o.bn), "CRA charity page"),
        o.website ? externalLink(o.website, "Website") : null),
    );
    add(card, el("h3", null, "What it does"));
    if (o.description) add(card, el("p", { className: "desc" }, o.description));
    else add(card, el("p", { className: "note" }, "No program description was filed, so this charity is not on the map."));

    const twins = o.description ? (sharedText.get(o.description) || []).filter((bn) => bn !== o.bn) : [];
    if (twins.length) {
      add(card, el("h3", null, `Same description, word for word (${twins.length})`),
        el("ul", { className: "list" }, twins.map((bn) => orgButton(byBn.get(bn)))));
    }
    if (o.neighbours.length) {
      add(card, el("h3", null, "Most similar descriptions"),
        el("ul", { className: "list" }, o.neighbours.map(([bn, s]) => orgButton(byBn.get(bn), `similarity ${s.toFixed(2)}`))));
    }
    // no_description is said in the card's description section already.
    const notes = o.flags.filter((f) => f !== "no_description").map((f) => FLAG_TEXT[f] || f);
    if (notes.length) add(card, el("h3", null, "Notes on the data"), el("ul", null, notes.map((t) => el("li", { className: "note" }, t))));
    card.scrollTop = 0; $("panel").scrollTop = 0;
  }

  function select(bn, fromList) {
    const o = byBn.get(bn);
    if (!o) return;
    state.selected = bn;
    try { history.replaceState(null, "", "#" + encodeURIComponent(bn)); } catch (_) { /* file:// or sandboxed */ }
    if (fromList && o.x !== null) {
      view.scale = Math.max(view.scale, view.fit * 3);
      centreOn(o.x, o.y);
    }
    renderCard(o);
    draw();
  }
  function deselect() {
    state.selected = null;
    try { history.replaceState(null, "", location.pathname + location.search); } catch (_) { /* ignore */ }
  }
  function closeCard() { deselect(); renderList(); draw(); }

  // ---- controls ----------------------------------------------------------------------
  function fillSelect(id, options) {
    const s = $(id);
    for (const [value, label, group] of options) {
      let parent = s;
      if (group) {
        parent = [...s.querySelectorAll("optgroup")].find((g) => g.label === group) || s.appendChild(el("optgroup", { label: group }));
      }
      parent.append(el("option", { value }, label));
    }
  }
  function buildControls() {
    const count = (key) => orgs.reduce((m, o) => m.set(o[key], (m.get(o[key]) || 0) + 1), new Map());
    const munis = [...count("municipality")].sort((a, b) => b[1] - a[1]);
    fillSelect("f-muni", munis.map(([m, n]) => [m, `${m} (${fmt.format(n)})`]));
    const cats = new Map();
    for (const o of orgs) {
      const c = cats.get(o.category_code) || { label: o.category, n: 0, head: headOf(o) };
      c.n += 1; cats.set(o.category_code, c);
    }
    fillSelect("f-cat", [...cats].sort((a, b) => a[0].localeCompare(b[0]))
      .map(([code, c]) => [code, `${c.label} (${fmt.format(c.n)})`, c.head ? c.head.label : "Other"]));
    const revs = count("revenue_band");
    fillSelect("f-rev", REVENUE.filter(([k]) => revs.has(k)).map(([k, label]) => [k, `${label} (${fmt.format(revs.get(k))})`])
      .concat(revs.has(null) ? [["none", `No band: not reported or negative (${fmt.format(revs.get(null))})`]] : []));

    const heads = $("heads");
    for (const h of HEADS) {
      const n = orgs.filter((o) => o.x !== null && headOf(o) === h).length;
      heads.append(el("button", { type: "button", className: "head", "aria-pressed": "false", "data-head": h.id,
        onclick: () => { state.head = state.head === h.id ? "" : h.id; syncHeads(); updateStatus(); draw(); } },
        h.label, el("span", { className: "n" }, fmt.format(n))));
    }
    const bind = (id, key) => $(id).addEventListener("input", (e) => {
      state[key] = key === "q" ? e.target.value.trim().toLowerCase() : e.target.value;
      state.shown = PAGE_SIZE;
      if (state.selected) deselect();
      renderList(); updateStatus(); draw();
    });
    bind("q", "q"); bind("f-area", "area"); bind("f-muni", "muni"); bind("f-cat", "cat"); bind("f-rev", "rev"); bind("f-staff", "staff");
    $("reset").addEventListener("click", () => {
      for (const [id, key] of [["q", "q"], ["f-area", "area"], ["f-muni", "muni"], ["f-cat", "cat"], ["f-rev", "rev"], ["f-staff", "staff"]]) { $(id).value = ""; state[key] = ""; }
      state.head = ""; state.list = null; state.selected = null; state.shown = PAGE_SIZE;
      syncHeads(); renderList(); updateStatus(); fitMain(); draw();
    });
  }
  function syncHeads() {
    for (const b of document.querySelectorAll(".head")) b.setAttribute("aria-pressed", String(b.dataset.head === state.head));
  }
  function updateOutside() {
    let out = 0;
    for (const o of placed) {
      const [x, y] = toScreen(o.x, o.y);
      if (x < 0 || y < 0 || x > view.w || y > view.h) out += 1;
    }
    $("outside").textContent = out ? `${fmt.format(out)} ${out === 1 ? "dot is" : "dots are"} outside this view.` : "";
    $("show-all").hidden = !out;
  }
  function updateStatus() {
    const head = HEADS.find((h) => h.id === state.head);
    const lit = placed.filter((o) => matches(o) && (!head || head.has(Number(o.category_code)))).length;
    const why = [filtering() ? "the filters" : "", head ? head.label.toLowerCase() : ""].filter(Boolean).join(" and ");
    $("status").textContent = why
      ? `${fmt.format(lit)} of ${fmt.format(placed.length)} dots lit (${why}).`
      : `${fmt.format(placed.length)} charities on the map.`;
  }

  // ---- start -------------------------------------------------------------------------
  function start(doc) {
    orgs = doc.orgs;
    for (const o of orgs) {
      o._search = (o.name + " " + (o.legal_name || "")).toLowerCase();
      byBn.set(o.bn, o);
      if (o.description) sharedText.set(o.description, (sharedText.get(o.description) || []).concat(o.bn));
    }
    for (const [t, bns] of sharedText) if (bns.length < 2) sharedText.delete(t);
    placed = orgs.filter((o) => o.x !== null);
    $("retrieved").textContent = doc.source.cra_retrieved_utc.slice(0, 10);
    buildControls();
    boxes(); readColors(); resize(false); updateStatus();
    const fromHash = hashBn();
    if (byBn.has(fromHash)) select(fromHash, true); else renderList();
    draw();
  }

  // Narrow screens start with the filters folded, so the map is above the fold.
  if (window.matchMedia("(max-width: 760px)").matches) $("filters").open = false;

  window.addEventListener("hashchange", () => {
    const bn = hashBn();
    if (byBn.has(bn) && bn !== state.selected) select(bn, true);
  });
  window.addEventListener("resize", () => { if (mainBox) { resize(true); draw(); } });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { readColors(); draw(); });

  fetch(DATA_URL)
    .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(start)
    .catch((err) => { $("status").textContent = `Could not load the data (${err.message}). Try reloading the page.`; });
})();
