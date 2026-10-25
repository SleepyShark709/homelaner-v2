-- UE4SS Lua runtime probe for UNDEFEATED.
-- Prints the gameplay Pawn / PlayerCameraManager transform once per second.
-- Install as Mods/CoordDump/Scripts/main.lua and enable CoordDump in mods.txt.
local UEHelpers = require("UEHelpers")

LoopAsync(1000, function()
    local ok, pc = pcall(UEHelpers.GetPlayerController)
    if not ok or not pc or not pc:IsValid() then return end
    local pawn = pc.Pawn
    if not pawn or not pawn:IsValid() then return end
    local l = pawn:K2_GetActorLocation()
    local r = pawn:K2_GetActorRotation()
    local cm = pc.PlayerCameraManager
    local cl, cr = nil, nil
    if cm and cm:IsValid() then
        cl = cm:GetCameraLocation()
        cr = cm:GetCameraRotation()
    end
    local function f(x) return x and string.format("%.3f", x) or "?" end
    print(string.format("COORD loc=(%s,%s,%s) rot=(%s,%s,%s) cam=(%s,%s,%s) crot=(%s,%s,%s)",
        f(l.X), f(l.Y), f(l.Z), f(r.Pitch), f(r.Yaw), f(r.Roll),
        f(cl and cl.X), f(cl and cl.Y), f(cl and cl.Z),
        f(cr and cr.Pitch), f(cr and cr.Yaw), f(cr and cr.Roll)))
end)
