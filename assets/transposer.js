// Transposer page: paste a song, choose a key, get the song back.
(function () {
  const C = window.Chords;
  const input = document.getElementById("transpose-input");
  if (!input) return;
  const output = document.getElementById("transpose-output");
  const from = document.getElementById("transpose-from");
  const to = document.getElementById("transpose-to");
  const shiftLabel = document.getElementById("transpose-shift");

  function fillKeys(select, keys) {
    select.innerHTML = "";
    keys.forEach((k) => {
      const o = document.createElement("option");
      o.value = o.textContent = k;
      select.appendChild(o);
    });
  }

  function setFrom(key) {
    const minor = C.parseKey(key).minor;
    const keys = minor ? C.MINOR_KEYS : C.MAJOR_KEYS;
    const keep = to.value;
    fillKeys(from, keys);
    fillKeys(to, keys);
    from.value = key;
    to.value = keys.includes(keep) ? keep : key;
  }

  function run() {
    const shift = C.semitonesBetween(from.value, to.value);
    output.value = C.transposeText(input.value, shift, C.spelling(to.value));
    const down = 12 - shift;
    shiftLabel.textContent = shift === 0 ? "No change" :
      shift <= 6 ? `Up ${shift} semitone${shift > 1 ? "s" : ""}` : `Down ${down} semitone${down > 1 ? "s" : ""}`;
  }

  function detect() {
    const guess = C.guessKey(input.value);
    if (guess && C.parseKey(guess)) {
      const k = C.parseKey(guess);
      const list = k.minor ? C.MINOR_KEYS : C.MAJOR_KEYS;
      setFrom(list.find((x) => C.parseKey(x).pitch === k.pitch));
    }
  }

  setFrom("C");
  detect();
  input.addEventListener("input", run);
  input.addEventListener("change", () => { detect(); run(); });
  from.addEventListener("change", run);
  to.addEventListener("change", run);
  document.getElementById("transpose-down").addEventListener("click", () => { to.value = C.shiftKey(to.value, -1); run(); });
  document.getElementById("transpose-up").addEventListener("click", () => { to.value = C.shiftKey(to.value, 1); run(); });
  document.getElementById("transpose-copy").addEventListener("click", () => {
    output.select();
    navigator.clipboard && navigator.clipboard.writeText(output.value);
  });
  run();
})();
