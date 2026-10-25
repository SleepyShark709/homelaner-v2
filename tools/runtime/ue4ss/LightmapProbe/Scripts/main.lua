LoopAsync(5000,function()
 for _,comp in ipairs(FindAllOf("StaticMeshComponent") or {}) do
  local ok,name=pcall(function() return comp:GetFullName() end)
  if ok and name and string.find(name,"Building_2_01_9") and string.find(name,"CommercialArea") then
   local target=comp.LightMap
   local ts=tostring(target)
   print("LM9 target="..ts)
   local n=0
   for _,tex in ipairs(FindAllOf("LightMapTexture2D") or {}) do
    n=n+1
    local t=tostring(tex)
    if t==ts then print("LM9 MATCH "..tostring(tex:GetFullName())) end
   end
   print("LM9 textures="..n)
   return
  end
 end
end)
