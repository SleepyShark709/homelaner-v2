local done = false
LoopAsync(5000, function()
    if done then return end
    done = true
    local function val(obj, name)
        local ok, v = pcall(function() return obj[name] end)
        if not ok or v == nil then return "?" end
        if type(v) == "table" or type(v) == "userdata" then
            local r = pcall(function() return v.R end)
            local g = pcall(function() return v.G end)
            local b = pcall(function() return v.B end)
            if r then return string.format("%s,%s,%s", tostring(v.R), tostring(v.G), tostring(v.B)) end
        end
        return tostring(v)
    end
    for _, light in ipairs(FindAllOf("DirectionalLight") or {}) do
        local okn, name = pcall(function() return light:GetFullName() end)
        local okr, rot = pcall(function() return light:K2_GetActorRotation() end)
        local rotS = "?"
        if okr and rot then rotS = string.format("%.2f,%.2f,%.2f", rot.Pitch, rot.Yaw, rot.Roll) end
        print(string.format("LIGHTDUMP dir %s intensity=%s color=%s rot=%s", tostring(name), val(light,"Intensity"), val(light,"LightColor"), rotS))
    end
    for _, light in ipairs(FindAllOf("SkyLight") or {}) do
        local okn, name = pcall(function() return light:GetFullName() end)
        print("LIGHTDUMP sky " .. tostring(name) .. " intensity=" .. val(light,"Intensity") .. " color=" .. val(light,"LightColor"))
    end
    for _, pp in ipairs(FindAllOf("PostProcessVolume") or {}) do
        local okn, name = pcall(function() return pp:GetFullName() end)
        print("LIGHTDUMP pp " .. tostring(name) .. " enabled=" .. tostring(pp.enabled) .. " unbound=" .. tostring(pp.unbound))
        local oks, settings = pcall(function() return pp.Settings end)
        if oks and settings then
            print("LIGHTDUMP pp exposure min=" .. val(settings,"AutoExposureMinBrightness") .. " max=" .. val(settings,"AutoExposureMaxBrightness") .. " comp=" .. val(settings,"AutoExposureBias") .. " bloom=" .. val(settings,"BloomIntensity"))
        end
    end
    print("LIGHTDUMP done")
end)
