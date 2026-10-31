-- The executor has its own unguarded context; this native screen is read-only.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("ReligionScreen")
BaiqiUILoader.ReadOnly()
