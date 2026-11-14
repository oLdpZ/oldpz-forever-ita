-- Core/VoiceIntro.lua: each race's intro cinematic, for the voice player. Pure data: no frames, no sound calls.
-- The game's English narration of an intro is one file that also carries the cinematic's music, on no channel a
-- setting turns off: while our Italian narrator reads the intro, the voice player silences that file
-- (MuteSoundFile) and plays the race's starting-zone music, a file of the game's own (PlayMusic), in its place.
-- Each race: the BroadcastText ids of its subtitles (`first`..`last`, the pack's `i-<id>` lines,
-- pipeline/voice_intros.tsv), the narration's file ids (sound/cinematicvoices/<race>narration.mp3 and its
-- streaming/ copy; the orc intro also in shots) and the music's. A race whose narration file is not known has no
-- `files`: its intro stays English.
local _, WFJ = ...
local VoiceIntro = {}
WFJ.VoiceIntro = VoiceIntro

VoiceIntro.RACES = {
  { race = "skyborne", first = 316345, last = 316358, files = {}, music = 53223 }, -- the main theme
  { race = "gnome", first = 329279, last = 329288, files = { 222760, 349057 }, music = 53577 }, -- Dun Morogh
  { race = "dwarf", first = 329301, last = 329308, files = { 222759, 349056 }, music = 53577 }, -- Dun Morogh
  { race = "human", first = 329309, last = 329317, files = { 222761, 349058 }, music = 53492 }, -- Elwynn
  { race = "nightelf", first = 329318, last = 329327, files = { 222762, 349053 }, music = 53453 }, -- Teldrassil
  { race = "orc", first = 329328, last = 329334, music = 53299, -- Durotar
    files = { 222763, 349061, 772571, 772572, 772573, 772574, 772575, 772576 } },
  { race = "tauren", first = 329335, last = 329342, files = { 222764, 349062 }, music = 53680 }, -- Mulgore
  { race = "troll", first = 329343, last = 329348, files = { 222765, 349059 }, music = 53299 }, -- Durotar
  { race = "undead", first = 329349, last = 329360, files = { 222766, 349060 }, music = 53486 }, -- Tirisfal
}

-- The race of an intro subtitle's BroadcastText id → its row, or nil (not an intro's).
function VoiceIntro.of(id)
  if type(id) ~= "number" then return nil end
  for _, r in ipairs(VoiceIntro.RACES) do
    if id >= r.first and id <= r.last then return r end
  end
  return nil
end
