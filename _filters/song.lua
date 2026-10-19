-- Render a song page.
--
-- A ```{.song} block becomes HTML: one row per line, lyrics with chords on the
-- left and melody on the right. The song's details from the front matter
-- (artist, key, Andy's voice, links) go in a box above it. assets/song.js
-- adds the toolbar: melody switch, key menu and chord layout.

local function esc(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function str(v)
  if v == nil then return nil end
  local s = pandoc.utils.stringify(v)
  if s == "" then return nil end
  return s
end

-- A chord is a root note and any suffix; [x], [riff], [Chorus] are notes.
local function is_chord(inside)
  for part in inside:gmatch("[^,;%s]+") do
    if not part:match("^[A-G][#b]?[^%s,;]*$") then return false end
  end
  return inside:match("%S") ~= nil
end

local function lyrics_html(text)
  local out, pos = {}, 1
  local chunk_open = false
  local function close()
    if chunk_open then
      out[#out + 1] = "</span></span>"
      chunk_open = false
    end
  end
  while true do
    local s, e, inside = text:find("%[([^%]]*)%]", pos)
    local before = text:sub(pos, (s or 0) - 1)
    if s == nil then before = text:sub(pos) end
    if before ~= "" then
      if not chunk_open then out[#out + 1] = '<span class="ch"><span class="ly">' chunk_open = true end
      out[#out + 1] = esc(before)
    end
    if s == nil then break end
    if is_chord(inside) then
      close()
      out[#out + 1] = '<span class="ch"><span class="chord" data-chord="' .. esc(inside) .. '">'
        .. esc(inside) .. '</span><span class="ly">'
      chunk_open = true
    else
      if not chunk_open then out[#out + 1] = '<span class="ch"><span class="ly">' chunk_open = true end
      out[#out + 1] = '<span class="mark">[' .. esc(inside) .. ']</span>'
    end
    pos = e + 1
  end
  close()
  return table.concat(out)
end

local function is_label(line)
  return line:match(":$") and not line:find("%[")
end

local function song_html(code)
  local out = {}
  local has_melody = false
  for raw in (code .. "\n"):gmatch("([^\n]*)\n") do
    local line = raw:gsub("%s+$", "")
    if line == "" then
      out[#out + 1] = '<div class="song-gap"></div>'
    elseif line:match("^#") then
      out[#out + 1] = '<div class="song-note">' .. esc(line:gsub("^#%s*", "")) .. '</div>'
    elseif is_label(line) then
      out[#out + 1] = '<div class="song-label">' .. esc(line:sub(1, -2)) .. '</div>'
    else
      line = line:gsub("^\\#", "#")
      local lyr, mel = line:match("^(.-)%s*|%s+(.*)$")
      if lyr == nil then lyr, mel = line, nil end
      if mel then has_melody = true end
      out[#out + 1] = '<div class="song-line"><div class="song-lyrics">' .. lyrics_html(lyr)
        .. '</div><div class="song-melody">' .. esc(mel or "") .. '</div></div>'
    end
  end
  local cls = has_melody and "song has-melody" or "song"
  return '<div class="' .. cls .. '">' .. table.concat(out, "\n") .. '</div>'
end

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
