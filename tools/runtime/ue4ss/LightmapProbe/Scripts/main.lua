local done=false
LoopAsync(6000,function()
 if done then return end
 done=true
 local found=0
 for _,comp in ipairs(FindAllOf("StaticMeshComponent") or {}) do
  local ok,name=pcall(function() return comp:GetFullName() end)
  if ok and name and string.find(name,"Building_2_01_9") then
   found=found+1
   print("LMPROBE comp "..name)
   for _,prop in ipairs({"LightMap","LightMapCoordinateIndex","LightMapUVBias","LightmapType","LightMapResourceCluster","bUseAsOccluder"}) do
    local okp,val=pcall(function() return comp[prop] end)
    print("LMPROBE   "..prop.." ok="..tostring(okp).." val="..tostring(val))
   end
  end
 end
 print("LMPROBE components="..found)
 for _,actor in ipairs(FindAllOf("Actor") or {}) do
  local ok,name=pcall(function() return actor:GetFullName() end)
  if ok and name and string.find(name,"Building_2_01_9") then print("LMPROBE actor "..name) end
 end
 print("LMPROBE done")
end)
