-- Render a song page.
--
-- A ```{.song} block becomes HTML: one row per line, lyrics with chords on the
-- left and melody on the right. The song's details from the front matter
-- (artist, key, Andy's voice, links) go in a box above it. assets/song.js
-- adds the toolbar: chords (inline, above, off), melody switch and key menu.

local R = dofile(pandoc.path.join({ pandoc.path.directory(PANDOC_SCRIPT_FILE), "song-render.lua" }))
local esc, str, song_html = R.esc, R.str, R.song_html

local LIBRARY_NAMES = {
  ["spiritual"] = "Spiritual Songs",
  ["andy-original"] = "Andy Originals",
  ["yeastbombs"] = "Trendy Wendy and the Yeastbombs",
  ["kids"] = "Kid Songs",
  ["kids-motions"] = "Kid Songs with Motions",
}
local LIBRARY_PAGES = {
  ["spiritual"] = "spiritual", ["andy-original"] = "andy-originals",
  ["yeastbombs"] = "yeastbombs", ["kids"] = "kids", ["kids-motions"] = "kids",
}

local function details(meta)
  local items = {}
  local function add(label, value)
    items[#items + 1] = '<span class="song-detail"><span class="song-detail-label">' .. label
      .. '</span> ' .. value .. '</span>'
  end
  local key = str(meta.key)
  if key then
    local note = str(meta.key_note)
    add("Key", esc(key) .. (note and (' <span class="song-detail-note">(' .. esc(note) .. ')</span>') or ""))
  end
  local low, high = str(meta.voice_low), str(meta.voice_high)
  if low or high then
    add("Andy's Voice", esc(low or "?") .. "–" .. esc(high or "?"))
  end
  if str(meta.difficulty) then add("Difficulty", esc(str(meta.difficulty))) end
  local links = {}
  if str(meta.youtube) then
    links[#links + 1] = '<a href="' .. esc(str(meta.youtube)) .. '"><i class="bi bi-youtube"></i> YouTube</a>'
  end
  if meta.files then
    for _, f in ipairs(meta.files) do
      local path = str(f)
      links[#links + 1] = '<a href="' .. esc(path) .. '" download><i class="bi bi-file-earmark-spreadsheet"></i> '
        .. esc(path:gsub("^files/", "")) .. '</a>'
    end
  end
  if meta.other_links then
    for _, l in ipairs(meta.other_links) do
      local url = str(l)
      local label = url:match("%.pdf$") and "PDF" or "Link"
      links[#links + 1] = '<a href="' .. esc(url) .. '"><i class="bi bi-box-arrow-up-right"></i> ' .. label .. '</a>'
    end
  end
  local libs = {}
  if meta.libraries then
    for _, l in ipairs(meta.libraries) do
      local id = str(l)
      if LIBRARY_NAMES[id] then
        libs[#libs + 1] = '<a class="song-library" href="../libraries/' .. LIBRARY_PAGES[id] .. '.html">'
          .. esc(LIBRARY_NAMES[id]) .. '</a>'
      end
    end
  end
  local html = '<div class="song-details">' .. table.concat(items, "")
  if #links > 0 then html = html .. '<span class="song-links">' .. table.concat(links, "") .. '</span>' end
  if #libs > 0 then html = html .. '<span class="song-libraries">' .. table.concat(libs, "") .. '</span>' end
  return html .. '</div>'
end

local function toolbar(meta)
  local keys = {}
  if meta.alt_keys then
    for _, k in ipairs(meta.alt_keys) do keys[#keys + 1] = str(k) end
  end
  return '<div class="song-toolbar" data-key="' .. esc(str(meta.key) or "") .. '" data-alt-keys="'
    .. esc(table.concat(keys, " ")) .. '"></div>'
end

function Pandoc(doc)
  if not FORMAT:match("html") then return doc end
  local found = false
  doc.blocks = doc.blocks:walk({
    CodeBlock = function(cb)
      if cb.classes:includes("song") then
        found = true
        return pandoc.RawBlock("html", song_html(cb.text))
      end
    end,
  })
  local artist = str(doc.meta.artist)
  if artist and not doc.meta.subtitle then
    doc.meta.subtitle = pandoc.MetaInlines({ pandoc.Str(artist) })
  end
  local top = { pandoc.RawBlock("html", details(doc.meta)) }
  if found then top[#top + 1] = pandoc.RawBlock("html", toolbar(doc.meta)) end
  if not found then
    top[#top + 1] = pandoc.Para({ pandoc.Emph({ pandoc.Str("No song text yet.") }) })
  end
  doc.blocks = pandoc.Blocks(top) .. doc.blocks
  return doc
end
