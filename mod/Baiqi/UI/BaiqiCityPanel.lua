-- Native CityPanel remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("CityPanel")
BaiqiUILoader.ReadOnly()
local nativeViewMain=ViewMain
ViewMain=function(...)
  nativeViewMain(...)
  if BaiqiUIGuard.PlayerID()~=nil then
    for _,name in ipairs({"ChangeProductionCheck","PurchaseTileCheck","ManageCitizensCheck","PurchaseGoldCheck","PurchaseFaithCheck","FoodCheck","ProductionCheck","GoldCheck","ScienceCheck","CultureCheck","FaithCheck"}) do
      local control=Controls[name]
      if control then control:SetDisabled(true);control:SetToolTipString("白绮内政由AI执行，只可查看。") end
    end
  end
end
