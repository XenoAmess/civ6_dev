-- Native GovernmentScreen remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("GovernmentScreen")
BaiqiUILoader.ReadOnly()

-- Closing inspection discards only the screen's pending card layout. The
-- native Yes/discard callback uses the same flag before its normal Close.
local NativeClose=Close
if type(NativeClose)=="function" then
  function Close(...)
    local confirm=Controls and Controls.ConfirmPolicies
    if BaiqiUIGuard.PlayerID()~=nil and confirm and type(confirm.SetDisabled)=="function" then
      confirm:SetDisabled(true)
    end
    return NativeClose(...)
  end
end
