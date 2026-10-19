-- Shared by song.lua and songbook.lua: turn a ```{.song} block into HTML.

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
      out[#out + 1] = esc(before):gsub("\1", '<span class="chord-hyphen">-</span>')
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

-- opts.melody = false leaves the melody out (used by the printable pages).
local function song_html(code, opts)
  opts = opts or {}
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
      if opts.melody == false then mel = nil end
      if mel then has_melody = true end
      -- A line with only chords on it (and maybe "x2") and no melody is hidden
      -- with the chords.
      local words = lyr:gsub("%[[^%]]*%]", ""):gsub("[xX]%d+", "")
      local line_cls = (words:match("%a") or mel) and "song-line" or "song-line chords-only"
      -- re-[Em]-member: the second hyphen is only there for the chord.
      lyr = lyr:gsub("%-(%[[^%]]*%])%-", "-%1\1")
      out[#out + 1] = '<div class="' .. line_cls .. '"><div class="song-lyrics">' .. lyrics_html(lyr)
        .. '</div><div class="song-melody">' .. esc(mel or "") .. '</div></div>'
    end
  end
  local cls = has_melody and "song has-melody" or "song"
  return '<div class="' .. cls .. '">' .. table.concat(out, "\n") .. '</div>'
end

return { esc = esc, str = str, song_html = song_html }
