-- Replace []{.song-count} with the number of song files in songs/.

local function count()
  local n = 0
  local dir = pandoc.path.join({ quarto.project.directory, "songs" })
  for _, name in ipairs(pandoc.system.list_directory(dir)) do
    if name:match("%.qmd$") then n = n + 1 end
  end
  return n
end

function Span(el)
  if el.classes:includes("song-count") then
    return pandoc.Str(tostring(count()))
  end
end
