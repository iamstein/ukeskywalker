-- Render a printable song sheet.
--
-- The page's front matter lists the printed pages and the songs on each, by
-- the song file's name:
--
--   songbook:
--     - [love-will-hold-us-together]
--     - [the-rose, this-little-light-of-mine]
--
-- Each song is read from songs/<name>.qmd and printed with its chords but
-- without the melody. Each list item starts a new printed page.
-- assets/songbook.js adds a key menu to each song.

local R = dofile(pandoc.path.join({ pandoc.path.directory(PANDOC_SCRIPT_FILE), "song-render.lua" }))
local esc, str, song_html = R.esc, R.str, R.song_html

local function read_song(name)
  local path = pandoc.path.join({ quarto.project.directory, "songs", name .. ".qmd" })
  local f = io.open(path, "r")
  if not f then
    quarto.log.warning("songbook: no song file " .. path)
    return nil
  end
  local doc = pandoc.read(f:read("a"), "markdown")
  f:close()
  local code
  doc.blocks:walk({
    CodeBlock = function(cb)
      if cb.classes:includes("song") and not code then code = cb.text end
    end,
  })
  return doc.meta, code
end

local function song_section(name)
  local meta, code = read_song(name)
  if not meta then return "" end
  local about = {}
  local artist = str(meta.artist)
  if artist and artist ~= "-" then about[#about + 1] = '<span class="sheet-artist">' .. esc(artist) .. '</span>' end
  if str(meta.key) then
    about[#about + 1] = '<span class="sheet-key" data-key="' .. esc(str(meta.key)) .. '">Key of '
      .. esc(str(meta.key)) .. '</span>'
  end
  return '<section class="sheet-song">'
    .. '<h2 class="sheet-title"><a href="../songs/' .. esc(name) .. '.html">' .. esc(str(meta.title) or name) .. '</a></h2>'
    .. (#about > 0 and ('<div class="sheet-about">' .. table.concat(about, '<span class="sheet-sep"> · </span>') .. '</div>') or "")
    .. (code and song_html(code, { melody = false }) or "")
    .. '</section>'
end

function Pandoc(doc)
  if not FORMAT:match("html") or not doc.meta.songbook then return doc end
  local pages = {}
  for _, page in ipairs(doc.meta.songbook) do
    local songs = {}
    for _, name in ipairs(page) do songs[#songs + 1] = song_section(str(name)) end
    local cls = #songs > 1 and "sheet-page sheet-columns" or "sheet-page"
    pages[#pages + 1] = '<div class="' .. cls .. '">' .. table.concat(songs, "\n") .. '</div>'
  end
  doc.blocks:insert(pandoc.RawBlock("html", '<div class="songbook">' .. table.concat(pages, "\n") .. '</div>'))
  return doc
end
