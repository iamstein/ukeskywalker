// Song page toolbar: melody switch, key menu, chord layout.
// The song HTML comes from _filters/song.lua; chord names from assets/chords.js.
(function () {
  const song = document.querySelector(".song");
  const bar = document.querySelector(".song-toolbar");
  if (!song || !bar) return;

  function load(name, fallback) {
    try { return localStorage.getItem("ukeskywalker." + name) ?? fallback; } catch (e) { return fallback; }
  }
  function save(name, value) {
    try { localStorage.setItem("ukeskywalker." + name, value); } catch (e) { /* private window */ }
  }

  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === "text") e.textContent = v; else e.setAttribute(k, v);
    });
    (children || []).forEach((c) => e.appendChild(c));
    return e;
  }

  // ---- melody switch ----
  if (song.classList.contains("has-melody")) {
    const input = el("input", { type: "checkbox", role: "switch", id: "melody-switch", class: "form-check-input" });
    input.checked = load("melody", "on") === "on";
    const apply = () => song.classList.toggle("hide-melody", !input.checked);
    input.addEventListener("change", () => { save("melody", input.checked ? "on" : "off"); apply(); });
    apply();
    bar.appendChild(el("div", { class: "form-check form-switch song-tool" }, [
      input, el("label", { class: "form-check-label", for: "melody-switch", text: "Melody" }),
    ]));
  }

  // ---- key menu ----
  const chords = Array.from(song.querySelectorAll(".chord"));
  const C = window.Chords;
  const original = bar.dataset.key || (chords[0] && C.guessKey("[" + chords[0].dataset.chord + "]"));
  if (chords.length && original && C.parseKey(original)) {
    const minor = C.parseKey(original).minor;
    const all = minor ? C.MINOR_KEYS : C.MAJOR_KEYS;
    const favourites = [original].concat((bar.dataset.altKeys || "").split(/\s+/).filter(Boolean));
    const select = el("select", { class: "form-select form-select-sm", id: "key-select", "aria-label": "Key" });
    const group = (label, keys) => {
      const g = el("optgroup", { label });
      keys.forEach((k) => g.appendChild(el("option", { value: k, text: k === original ? k + " (as written)" : k })));
      select.appendChild(g);
    };
    group("Song keys", favourites.filter((k, i) => favourites.indexOf(k) === i));
    group("All keys", all.filter((k) => !favourites.includes(k)));

    const setKey = (key) => {
      const shift = C.semitonesBetween(original, key);
      const spell = C.spelling(key);
      chords.forEach((c) => { c.textContent = C.transposeChord(c.dataset.chord, shift, spell); });
      select.value = key;
      song.dataset.key = key;
    };
    select.addEventListener("change", () => setKey(select.value));
    const down = el("button", { type: "button", class: "btn btn-sm btn-outline-secondary", "aria-label": "Down a semitone", text: "−" });
    const up = el("button", { type: "button", class: "btn btn-sm btn-outline-secondary", "aria-label": "Up a semitone", text: "+" });
    down.addEventListener("click", () => setKey(C.shiftKey(select.value, -1)));
    up.addEventListener("click", () => setKey(C.shiftKey(select.value, 1)));
    bar.appendChild(el("div", { class: "song-tool song-key" }, [
      el("label", { for: "key-select", text: "Key" }), down, select, up,
    ]));
    setKey(original);
  }

  // ---- chord layout ----
  if (chords.length) {
    const input = el("input", { type: "checkbox", role: "switch", id: "above-switch", class: "form-check-input" });
    input.checked = load("layout", "inline") === "above";
    const apply = () => song.classList.toggle("chords-above", input.checked);
    input.addEventListener("change", () => { save("layout", input.checked ? "above" : "inline"); apply(); });
    apply();
    bar.appendChild(el("div", { class: "form-check form-switch song-tool" }, [
      input, el("label", { class: "form-check-label", for: "above-switch", text: "Chords above lyrics" }),
    ]));
  }
})();
