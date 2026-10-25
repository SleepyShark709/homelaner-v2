LoopAsync(5000,function()
 for _,comp in ipairs(FindAllOf("StaticMeshComponent") or {}) do
  local ok,name=pcall(function() return comp:GetFullName() end)
  if ok and name and string.find(name,"Building_2_01_9") and string.find(name,"CommercialArea") then
   print("LM5 comp")
   local lod=comp.LODData
   lod:ForEach(function(idx,elem)
    for _,k in ipairs({"LightMap","ShadowMap","LightMapIndex","LightMapUVBias","LightMapCoordinateIndex"}) do
     local okl,v=pcall(function() return elem[k] end)
     print("LM5 elem."..k.." ok="..tostring(okl).." type="..type(v).." v="..tostring(v))
    end
    local oks,st=pcall(function() return elem:GetStruct() end)
    print("LM5 getstruct ok="..tostring(oks).." v="..tostring(st))
    if oks and st then st:ForEachProperty(function(p) print("LM5 field "..p:GetFName():ToString()) end) end
   end)
   return
  end
 end
end)
