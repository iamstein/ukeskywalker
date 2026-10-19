// Chord parsing and transposing, shared by song pages, the transposer and
// the compressor. Exposes window.Chords.
(function () {
  const SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  // Keys such as C, G, D and A: sharps, except the usual Bb and Eb.
  const MIXED = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];
  const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

  // Keys whose chords are spelled with flats, and keys with so many sharps
  // that D# and A# are the usual names.
  const FLAT_KEYS = new Set(["F", "Bb", "Eb", "Ab", "Db", "Gb", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm"]);
  const SHARP_KEYS = new Set(["E", "B", "F#", "C#m", "G#m", "D#m"]);

  const MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  const MINOR_KEYS = ["Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"];

  // A chord token: a root, then any suffix (Andy's C', Fh, Bb* included).
  const CHORD_TOKEN = /^[A-G][#b]?[^\s,;[\]]*$/;

  function pitch(root) {
    let p = NOTE[root[0]];
    if (root[1] === "#") p += 1;
    if (root[1] === "b") p -= 1;
    return (p + 12) % 12;
  }

  function parseKey(key) {
    const m = /^([A-G][#b]?)(m?)/.exec(key || "");
    return m ? { root: m[1], minor: m[2] === "m", pitch: pitch(m[1]) } : null;
  }

  // How to spell chords in `key`: "flats", "sharps" or "mixed".
  function spelling(key) {
    if (FLAT_KEYS.has(key)) return "flats";
    if (SHARP_KEYS.has(key)) return "sharps";
    const k = parseKey(key);
    return k && k.root[1] === "b" ? "flats" : "mixed";
  }

  // Name of the key `semitones` above `key`, spelled the usual way.
  function shiftKey(key, semitones) {
    const k = parseKey(key);
    if (!k) return key;
    const list = k.minor ? MINOR_KEYS : MAJOR_KEYS;
    const p = (k.pitch + semitones + 120) % 12;
    return list.find((x) => parseKey(x).pitch === p);
  }

  function semitonesBetween(from, to) {
    const a = parseKey(from), b = parseKey(to);
    if (!a || !b) return 0;
    return (b.pitch - a.pitch + 12) % 12;
  }

  function isChord(text) {
    const parts = text.split(/[,;\s]+/).filter(Boolean);
    return parts.length > 0 && parts.every((p) => CHORD_TOKEN.test(p));
  }

  // Transpose every root in a chord or chord list ("G", "D/F#", "G,F,C"),
  // spelled for the target key (see spelling()).
  function transposeChord(text, semitones, spell) {
    if (!semitones) return text;
    const names = spell === "flats" ? FLATS : spell === "sharps" ? SHARPS : MIXED;
    return text.replace(/(^|[\s,;/])([A-G][#b]?)/g, (_, sep, root) =>
      sep + names[(pitch(root) + semitones + 120) % 12]);
  }

  // Transpose every [chord] in a block of inline-chord text, and chord-only
  // lines in chords-over-lyrics text.
  function transposeText(text, semitones, spell) {
    return text.split("\n").map((line) => {
      if (/\[/.test(line)) {
        return line.replace(/\[([^\]]*)\]/g, (whole, inside) =>
          isChord(inside) ? "[" + transposeChord(inside, semitones, spell) + "]" : whole);
      }
      if (lineType(line) === "chords") {
        // Keep each chord at its column so it stays over the right syllable.
        return line.replace(/\S+/g, (tok) => (CHORD_TOKEN.test(tok) ? transposeChord(tok, semitones, spell) : tok));
      }
      return line;
    }).join("\n");
  }

  // "blank", "chords" (a line of chord names only) or "lyrics".
  function lineType(line) {
    if (!line.trim()) return "blank";
    const tokens = line.trim().split(/\s+/);
    const chordish = tokens.filter((t) => CHORD_TOKEN.test(t.replace(/[()|]/g, "")) || /^[|/x\d.-]+$/.test(t));
    return chordish.length === tokens.length && tokens.some((t) => /^[A-G]/.test(t)) ? "chords" : "lyrics";
  }

  // First chord in the text, as a key guess.
  function guessKey(text) {
    const m = /\[([A-G][#b]?)(m(?!aj))?/.exec(text) || /(?:^|\s)([A-G][#b]?)(m(?!aj))?\S*(?=\s|$)/m.exec(text);
    return m ? m[1] + (m[2] || "") : null;
  }

  window.Chords = {
    MAJOR_KEYS, MINOR_KEYS, parseKey, spelling, shiftKey, semitonesBetween,
    isChord, transposeChord, transposeText, lineType, guessKey,
  };
})();
