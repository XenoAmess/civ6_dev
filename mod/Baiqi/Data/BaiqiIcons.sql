INSERT INTO IconTextureAtlases (Name, IconSize, IconsPerRow, IconsPerColumn, Filename) VALUES
  ('ICON_ATLAS_BAIQI_LEADER', 32, 1, 1, 'Baiqi_Leader32.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 45, 1, 1, 'Baiqi_Leader45.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 50, 1, 1, 'Baiqi_Leader50.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 55, 1, 1, 'Baiqi_Leader55.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 64, 1, 1, 'Baiqi_Leader64.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 80, 1, 1, 'Baiqi_Leader80.dds'),
  ('ICON_ATLAS_BAIQI_LEADER', 256, 1, 1, 'Baiqi_Leader256.dds');
INSERT INTO IconDefinitions (Name, Atlas, "Index")
VALUES ('ICON_LEADER_BAIQI', 'ICON_ATLAS_BAIQI_LEADER', 0);

INSERT INTO IconDefinitions (Name, Atlas, "Index")
SELECT 'ICON_PROJECT_BAIQI_STANDBY', Atlas, "Index"
FROM IconDefinitions WHERE Name = 'ICON_PROJECT_ENHANCE_DISTRICT_ENCAMPMENT';
