-- Frozen prototype profile BAIQI_P2. These are design choices, not balance results.
BaiqiConfig = {
  version = 1, leader = "LEADER_BAIQI", stateKey = "BAIQI_STATE_V1",
  interval = 0.35, requestsPerTurn = 64, candidatesPerCity = 512,
  goldReserve = 100, netGoldMin = 2, settlerMinPop = 4,
  maxSettlers = 1, buildersPerCity = 0.5, armyPerCity = 2,
  pathLimit = 48, threatRadius = 2,
  cityRequisition = true, cityCostBase = 200, cityCostPerPopulation = 100,
  cityHealthPercent = 35, requisitionKey = "BAIQI_REQUISITION_V1",
  granaryCost = 150, maxRights = 16, rightsKey = "BAIQI_RIGHTS_V1",
}
