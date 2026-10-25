LoopAsync(5000,function()
 for _,comp in ipairs(FindAllOf("StaticMeshComponent") or {}) do
  local ok,name=pcall(function() return comp:GetFullName() end)
  if ok and name and string.find(name,"Building_2_01_9") and string.find(name,"CommercialArea") then
   print("LM6 comp")
   local lod=comp.LODData
   for i=0,1 do
    local oki,el=pcall(function() return lod[i] end)
    print("LM6 lod["..i.."] ok="..tostring(oki).." type="..type(el).." v="..tostring(el))
    if oki and el then
     local okb,base=pcall(function() return el:GetBaseAddress() end)
     local oks,sa=pcall(function() return el:GetStructAddress() end)
     print("LM6  base="..tostring(base).." struct="..tostring(sa))
     for _,k in ipairs({"LightMap","ShadowMap","LightMapIndex","LightMapUVBias"}) do
      local okl,v=pcall(function() return el[k] end)
      print("LM6  "..k.." ok="..tostring(okl).." type="..type(v).." v="..tostring(v))
     end
    end
   end
   return
  end
 end
end)
