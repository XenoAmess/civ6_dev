-- Native GovernorPanel remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("GovernorPanel")
BaiqiUILoader.ReadOnly()
