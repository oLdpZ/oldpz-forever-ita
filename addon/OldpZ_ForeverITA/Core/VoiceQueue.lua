-- Core/VoiceQueue.lua: the order voice lines play in. Pure tables: no frames, no sound calls; the voice player (UI)
-- plays the head and the voice panel draws the list.
--   * The head (items[1]) is the line playing, or paused; the rest wait their turn.
--   * A line already queued (same pack key) is not added again.
--   * An item is { key = pack key, window = the window that showed it, ... }: the player keeps what it needs.
local _, WFJ = ...
local Q = {}
WFJ.VoiceQueue = Q

Q.items = {}
Q.paused = false

function Q.size() return #Q.items end
function Q.current() return Q.items[1] end
function Q.waiting() return math.max(#Q.items - 1, 0) end

function Q.has(key)
  for _, it in ipairs(Q.items) do
    if it.key == key then return true end
  end
  return false
end

-- → true when added at the end
function Q.push(item)
  if Q.has(item.key) then return false end
  Q.items[#Q.items + 1] = item
  return true
end

-- Puts `item` at the head (a replay), dropping any other copy of it.
function Q.front(item)
  for i = #Q.items, 1, -1 do
    if Q.items[i].key == item.key then table.remove(Q.items, i) end
  end
  table.insert(Q.items, 1, item)
end

-- → the head, removed
function Q.pop()
  return table.remove(Q.items, 1)
end

-- Drops every line shown in `window`. → whether the head was one of them
function Q.dropWindow(window)
  local head = Q.items[1]
  for i = #Q.items, 1, -1 do
    if Q.items[i].window == window then table.remove(Q.items, i) end
  end
  return head ~= nil and head.window == window
end

function Q.clear()
  Q.items = {}
  Q.paused = false
end
