-- Native ProductionPanel remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("ProductionPanel")
BaiqiUILoader.ReadOnly()
