-- Prototype association: China. Do not modify or replace another leader.
INSERT INTO Players
  (Domain, CivilizationType, LeaderType, LeaderName, LeaderIcon,
   CivilizationName, CivilizationIcon, LeaderAbilityName, LeaderAbilityDescription,
   LeaderAbilityIcon, CivilizationAbilityName, CivilizationAbilityDescription,
   CivilizationAbilityIcon, Portrait, PortraitBackground)
SELECT domains.Domain, CivilizationType, 'LEADER_BAIQI',
  'LOC_LEADER_BAIQI_NAME', 'ICON_LEADER_BAIQI', CivilizationName, CivilizationIcon,
  'LOC_TRAIT_LEADER_BAIQI_FORERUNNER_NAME', 'LOC_TRAIT_LEADER_BAIQI_FORERUNNER_DESCRIPTION',
  'ICON_LEADER_BAIQI', CivilizationAbilityName, CivilizationAbilityDescription,
  CivilizationAbilityIcon, Portrait, PortraitBackground
FROM Players CROSS JOIN (
  SELECT 'Players:StandardPlayers' AS Domain UNION ALL
  SELECT 'Players:Expansion1_Players' UNION ALL SELECT 'Players:Expansion2_Players'
) AS domains
WHERE LeaderType = 'LEADER_QIN' AND Players.Domain = 'Players:StandardPlayers';

INSERT INTO PlayerItems
  (Domain, CivilizationType, LeaderType, Type, Name, Description, Icon, SortIndex)
SELECT domains.Domain, CivilizationType, 'LEADER_BAIQI', Type, Name, Description, Icon, SortIndex
FROM PlayerItems CROSS JOIN (
  SELECT 'Players:StandardPlayers' AS Domain UNION ALL
  SELECT 'Players:Expansion1_Players' UNION ALL SELECT 'Players:Expansion2_Players'
) AS domains
WHERE LeaderType = 'LEADER_QIN' AND PlayerItems.Domain = 'Players:StandardPlayers';
