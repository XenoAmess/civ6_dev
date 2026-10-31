INSERT INTO Types (Type, Kind) VALUES
  ('LEADER_BAIQI', 'KIND_LEADER'),
  ('TRAIT_LEADER_BAIQI_FORERUNNER', 'KIND_TRAIT');
INSERT INTO Leaders (LeaderType, Name, InheritFrom, SceneLayers)
VALUES ('LEADER_BAIQI', 'LOC_LEADER_BAIQI_NAME', 'LEADER_DEFAULT', 4);
INSERT INTO Traits (TraitType, Name, Description)
VALUES ('TRAIT_LEADER_BAIQI_FORERUNNER', 'LOC_TRAIT_LEADER_BAIQI_FORERUNNER_NAME',
        'LOC_TRAIT_LEADER_BAIQI_FORERUNNER_DESCRIPTION');
INSERT INTO LeaderTraits (LeaderType, TraitType)
VALUES ('LEADER_BAIQI', 'TRAIT_LEADER_BAIQI_FORERUNNER');
INSERT INTO CivilizationLeaders (CivilizationType, LeaderType, CapitalName)
SELECT CivilizationType, 'LEADER_BAIQI', CapitalName
FROM CivilizationLeaders WHERE LeaderType = 'LEADER_QIN';
-- Reference installed base-game presentation; no art or audio is redistributed.
INSERT INTO LoadingInfo (LeaderType, ForegroundImage, BackgroundImage, LeaderText, DawnOfManLeaderId)
SELECT 'LEADER_BAIQI', ForegroundImage, BackgroundImage, 'LOC_LOADING_INFO_LEADER_BAIQI', DawnOfManLeaderId
FROM LoadingInfo WHERE LeaderType = 'LEADER_QIN';
INSERT INTO LeaderQuotes (LeaderType, Quote)
VALUES ('LEADER_BAIQI', 'LOC_BAIQI_QUOTE');
