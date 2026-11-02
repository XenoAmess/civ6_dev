-- Mandatory administration profile BAIQI_P4. Army control stays with the player.
BaiqiConfig = {
  version = 2, leader = "LEADER_BAIQI",
  interval = 0.35, requestsPerTurn = 64, candidatesPerCity = 512,
  productionObservationSeconds = 2,
  goldReserve = 100, netGoldMin = 2, settlerMinPop = 4,
  maxSettlers = 1, buildersPerCity = 0.5, armyPerCity = 2, reconCitiesPerUnit = 4,
  pathLimit = 48, threatRadius = 2,
  cityRequisition = true, cityCostBase = 200, cityCostPerPopulation = 100,
  cityHealthPercent = 35, requisitionKey = "BAIQI_REQUISITION_V1",
  greatPersonIntentKey = "BAIQI_GREAT_PERSON_INTENTS_V1",
  creativeIntentKey = "BAIQI_CREATIVE_INTENTS_V1",
  religiousIntentKey = "BAIQI_RELIGIOUS_INTENTS_V1",
}
