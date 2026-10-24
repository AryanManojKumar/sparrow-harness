/* sparrow preview picker — injected into /projects/{id}/preview HTML.
   Speaks only via postMessage { channel: "sparrow", type, payload }.
   No-ops when the page is not framed (opened in its own tab). */
(function () {
  if (window.__sparrowPicker) return;
  window.__sparrowPicker = true;
  if (window.parent === window) return;

  var CHANNEL = "sparrow";
  var enabled = false;
  var selected = null;

  var box = document.createElement("div");
  box.setAttribute("data-sparrow-picker", "overlay");
  box.style.cssText =
    "position:fixed;pointer-events:none;z-index:2147483647;display:none;" +
    "box-sizing:border-box;border:2px dashed #4f7cff;" +
    "background:rgba(79,124,255,.14);border-radius:2px;";
  document.documentElement.appendChild(box);

  function post(type, payload) {
    window.parent.postMessage({ channel: CHANNEL, type: type, payload: payload }, "*");
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function fileHint(id) {
    if (!id) return null;
    var name = id
      .split(/[-_\s]+/)
      .filter(Boolean)
      .map(function (w) {
        return w.charAt(0).toUpperCase() + w.slice(1);
      })
      .join("");
    return "src/components/sections/" + name + ".tsx";
  }

  function selectorFor(el) {
    var parts = [];
    var node = el;
    for (var i = 0; i < 5 && node && node !== document.body && node.nodeType === 1; i++) {
      if (node.id) {
        parts.unshift("#" + cssEscape(node.id));
        break;
      }
      var tag = node.tagName.toLowerCase();
      var cls = [];
      if (node.classList) {
        for (var c = 0; c < node.classList.length && cls.length < 2; c++) {
          var name = node.classList[c];
          if (name && name.length < 40 && name.indexOf("__") !== 0) cls.push(cssEscape(name));
        }
      }
      var piece = tag + (cls.length ? "." + cls.join(".") : "");
      var parent = node.parentElement;
      if (parent) {
        var same = [];
        for (var k = 0; k < parent.children.length; k++) {
          if (parent.children[k].tagName === node.tagName) same.push(parent.children[k]);
        }
        if (same.length > 1) piece += ":nth-of-type(" + (same.indexOf(node) + 1) + ")";
      }
      parts.unshift(piece);
      node = node.parentElement;
    }
    return parts.join(" > ");
  }

  function sectionId(el) {
    var sec = el.closest && el.closest("section[id]");
    if (sec && sec.id) return sec.id;
    var any = el.closest && el.closest("[id]");
    return any && any.id ? any.id : null;
  }

  function describe(el) {
    var text = ((el.innerText || el.textContent || "") + "")
      .trim()
      .replace(/\s+/g, " ")
      .slice(0, 180);
    var sid = sectionId(el);
    var labelled = el.closest ? el.closest("[aria-label]") : null;
    var r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      text: text,
      ariaLabel: el.getAttribute("aria-label") || (labelled && labelled.getAttribute("aria-label")) || null,
      sectionId: sid,
      selector: selectorFor(el),
      fileHint: fileHint(sid),
      rect: { top: r.top, left: r.left, width: r.width, height: r.height },
    };
  }

  function paint(el, solid) {
    if (!el) {
      box.style.display = "none";
      return;
    }
    var r = el.getBoundingClientRect();
    box.style.display = "block";
    box.style.top = r.top + "px";
    box.style.left = r.left + "px";
    box.style.width = r.width + "px";
    box.style.height = r.height + "px";
    box.style.borderStyle = solid ? "solid" : "dashed";
  }

  function targetFromEvent(e) {
    var el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || el === box || (el.getAttribute && el.getAttribute("data-sparrow-picker"))) return null;
    if (el === document.documentElement || el === document.body) return null;
    return el;
  }

  function onMove(e) {
    if (!enabled) return;
    var el = targetFromEvent(e);
    if (el && el !== selected) paint(el, false);
  }

  function onClick(e) {
    if (!enabled) return;
    e.preventDefault();
    e.stopPropagation();
    var el = targetFromEvent(e);
    if (!el) return;
    if (e.shiftKey && el.parentElement && el.parentElement !== document.body) {
      el = el.parentElement;
    }
    selected = el;
    paint(el, true);
    post("element-select", describe(el));
  }

  function onKey(e) {
    if (!enabled) return;
    if (e.key === "Escape") {
      selected = null;
      paint(null);
      post("element-clear", null);
    }
  }

  function block(e) {
    if (!enabled) return;
    e.preventDefault();
    e.stopPropagation();
  }

  function enable() {
    if (enabled) return;
    enabled = true;
    document.documentElement.style.cursor = "crosshair";
    document.addEventListener("mousemove", onMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("submit", block, true);
  }

  function disable() {
    enabled = false;
    selected = null;
    paint(null);
    document.documentElement.style.cursor = "";
    document.removeEventListener("mousemove", onMove, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("submit", block, true);
  }

  window.addEventListener("message", function (ev) {
    var d = ev.data;
    if (!d || d.channel !== CHANNEL) return;
    if (d.type === "select-enable") enable();
    if (d.type === "select-disable") disable();
  });

  post("ready", null);
})();
