// Printable song sheet: a key menu for each song. The sheet prints in
// whatever keys are chosen. Chord names come from assets/chords.js.
(function () {
  const C = window.Chords;
  document.querySelectorAll(".sheet-song").forEach((section, n) => {
    const label = section.querySelector(".sheet-key");
    const chords = Array.from(section.querySelectorAll(".chord"));
    const original = label && label.dataset.key;
    if (!chords.length || !original || !C.parseKey(original)) return;

    const id = "sheet-key-" + n;
    const select = document.createElement("select");
    Object.assign(select, { id, className: "form-select form-select-sm" });
    select.setAttribute("aria-label", "Key");
    (C.parseKey(original).minor ? C.MINOR_KEYS : C.MAJOR_KEYS).forEach((k) => {
      select.appendChild(new Option(k === original ? k + " (as written)" : k, k));
    });
    const button = (text, aria, step) => {
      const b = document.createElement("button");
      Object.assign(b, { type: "button", className: "btn btn-sm btn-outline-secondary", textContent: text });
      b.setAttribute("aria-label", aria);
      b.addEventListener("click", () => setKey(C.shiftKey(select.value, step)));
      return b;
    };
    const setKey = (key) => {
      const shift = C.semitonesBetween(original, key);
      const spell = C.spelling(key);
      chords.forEach((c) => { c.textContent = C.transposeChord(c.dataset.chord, shift, spell); });
      select.value = key;
      label.textContent = "Key of " + key;
    };
    select.addEventListener("change", () => setKey(select.value));

    const tool = document.createElement("span");
    tool.className = "sheet-key-tool song-key";
    const name = document.createElement("label");
    Object.assign(name, { htmlFor: id, textContent: "Key" });
    tool.append(name, button("−", "Down a semitone", -1), select, button("+", "Up a semitone", 1));
    label.after(tool);
    label.classList.add("has-tool");
    setKey(original);
  });
})();
