-- Native GovernmentScreen remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("GovernmentScreen")
BaiqiUILoader.ReadOnly()
