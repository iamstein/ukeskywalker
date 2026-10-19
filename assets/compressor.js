// Chord compressor: chords written on the line above the lyrics become
// inline [C] chords. Ported from the original compressTab.js.
(function () {
  const C = window.Chords;

  // Put each chord in front of the word it sits over.
  function mergeChordsWithLyrics(chords, lyrics) {
    const found = [];
    chords.replace(/\S+/g, (name, pos) => { found.push({ name, pos }); return name; });
    let s = lyrics;
    for (let i = found.length - 1; i >= 0; i--) {
      let j = Math.min(found[i].pos, lyrics.length);
      // Back up to the start of the word under the chord.
      while (j > 0 && !/\s/.test(lyrics.charAt(j - 1))) j--;
      s = s.substring(0, j) + "[" + found[i].name + "] " + s.substring(j);
    }
    return s.replace(/\s+/g, " ").trim();
  }

  function compress(text) {
    const lines = text.replace(/\r/g, "").split("\n");
    const types = lines.map(C.lineType);
    const out = [];
    for (let i = 0; i < lines.length; i++) {
      if (types[i] === "chords" && types[i + 1] === "lyrics") {
        out.push(mergeChordsWithLyrics(lines[i], lines[i + 1]));
        i++;
      } else if (types[i] === "chords") {
        // A chord line with no lyrics under it: keep the chords, bracketed.
        out.push(lines[i].trim().split(/\s+/).map((c) => "[" + c + "]").join(" "));
      } else {
        out.push(lines[i].trim());
      }
    }
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  // The compressed song as a new song file, ready to save in songs/.
  function asSongFile(body, title, artist) {
    const key = C.guessKey(body) || "";
    return [
      "---",
      `title: "${title || ""}"`,
      `artist: "${artist || ""}"`,
      `key: ${key}`,
      "youtube: \"\"",
      "libraries: [all]",
      "---",
      "",
      "```{.song}",
      body,
      "```",
      "",
    ].join("\n");
  }

  window.Compressor = { compress, mergeChordsWithLyrics, asSongFile };

  const input = document.getElementById("compress-input");
  const output = document.getElementById("compress-output");
  const asFile = document.getElementById("compress-as-file");
  const title = document.getElementById("compress-title");
  const artist = document.getElementById("compress-artist");
  if (!input) return;

  function run() {
    const body = compress(input.value);
    output.value = asFile.checked ? asSongFile(body, title.value, artist.value) : body;
    document.getElementById("compress-file-fields").hidden = !asFile.checked;
  }
  document.getElementById("compress-button").addEventListener("click", run);
  [asFile, title, artist].forEach((e) => e.addEventListener("input", run));
  document.getElementById("compress-copy").addEventListener("click", () => {
    output.select();
    navigator.clipboard && navigator.clipboard.writeText(output.value);
  });
  run();
})();
