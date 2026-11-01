-- Temporary emblem references an installed atlas; the portrait is not final art.
INSERT INTO IconDefinitions (Name, Atlas, "Index")
SELECT 'ICON_LEADER_BAIQI', Atlas, "Index"
FROM IconDefinitions WHERE Name = 'ICON_CIVILIZATION_CHINA';

INSERT INTO IconDefinitions (Name, Atlas, "Index")
SELECT 'ICON_PROJECT_BAIQI_STANDBY', Atlas, "Index"
FROM IconDefinitions WHERE Name = 'ICON_PROJECT_ENHANCE_DISTRICT_ENCAMPMENT';
