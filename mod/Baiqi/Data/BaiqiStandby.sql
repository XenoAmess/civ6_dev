-- Last-resort normal production; it grants no yields, great-person points or units.
INSERT INTO Types (Type, Kind) VALUES
  ('PROJECT_BAIQI_STANDBY', 'KIND_PROJECT'),
  ('MODIFIER_BAIQI_ALLOW_STANDBY', 'KIND_MODIFIER');

INSERT INTO Projects
  (ProjectType, Name, ShortName, Description, Cost, PrereqDistrict, UnlocksFromEffect, AdvisorType)
VALUES
  ('PROJECT_BAIQI_STANDBY', 'LOC_PROJECT_BAIQI_STANDBY_NAME',
   'LOC_PROJECT_BAIQI_STANDBY_NAME', 'LOC_PROJECT_BAIQI_STANDBY_DESCRIPTION',
   30, 'DISTRICT_CITY_CENTER', 1, 'ADVISOR_GENERIC');

-- Define our own type; only the installed engine effect is referenced.
INSERT INTO DynamicModifiers (ModifierType, CollectionType, EffectType)
VALUES ('MODIFIER_BAIQI_ALLOW_STANDBY', 'COLLECTION_OWNER', 'EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY');
INSERT INTO Modifiers (ModifierId, ModifierType)
VALUES ('BAIQI_ENABLE_STANDBY', 'MODIFIER_BAIQI_ALLOW_STANDBY');
INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('BAIQI_ENABLE_STANDBY', 'ProjectType', 'PROJECT_BAIQI_STANDBY');
INSERT INTO TraitModifiers (TraitType, ModifierId)
VALUES ('TRAIT_LEADER_BAIQI_FORERUNNER', 'BAIQI_ENABLE_STANDBY');
