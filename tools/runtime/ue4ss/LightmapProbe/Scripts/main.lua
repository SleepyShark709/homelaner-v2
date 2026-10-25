local last=-1
LoopAsync(5000,function()
 local found=0
 for _,comp in ipairs(FindAllOf("StaticMeshComponent") or {}) do
  local ok,name=pcall(function() return comp:GetFullName() end)
  if ok and name and string.find(name,"CommercialArea.%-?HeroGame")==nil and string.find(name,"CommercialArea") and string.find(name,"Building_2_01_9") then
   found=found+1
   print("LMPROBE comp "..name)
   for _,prop in ipairs({"LightMap","LightMapCoordinateIndex","LightMapUVBias","LightMapResourceCluster"}) do
    local okp,val=pcall(function() return comp[prop] end)
    print("LMPROBE   "..prop.." ok="..tostring(okp).." val="..tostring(val))
    if okp and val then
     for _,m in ipairs({"Get","GetValue","GetFullName","ToString"}) do
      local okm,res=pcall(function() return val[m](val) end)
      print("LMPROBE     "..prop..":"..m.." ok="..tostring(okm).." res="..tostring(res))
     end
    end
   end
  end
 end
 if found~=last then print("LMPROBE components="..found); last=found end
end)
