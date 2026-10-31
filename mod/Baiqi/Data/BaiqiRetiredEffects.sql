-- Inert old-save compatibility only. No building/district attachment links.
-- Saved instances need their original IDs and requirements; all amounts are zero.
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType)
VALUES ('BAIQI_GRANARY_OUT_REQS', 'REQUIREMENTSET_TEST_ALL');
INSERT INTO Requirements (RequirementId, RequirementType)
VALUES ('BAIQI_GRANARY_OUT_REQ', 'REQUIREMENT_PLOT_PROPERTY_MATCHES');
INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId)
VALUES ('BAIQI_GRANARY_OUT_REQS', 'BAIQI_GRANARY_OUT_REQ');
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('BAIQI_GRANARY_OUT_REQ','PropertyName','BAIQI_GRANARY_OUT'),
('BAIQI_GRANARY_OUT_REQ','PropertyMinimum','1');
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId) VALUES
('BAIQI_GRANARY_OUT_FOOD','MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE','BAIQI_GRANARY_OUT_REQS'),
('BAIQI_GRANARY_OUT_HOUSING','MODIFIER_SINGLE_CITY_ADJUST_CITY_HOUSING_FROM_GREAT_PEOPLE','BAIQI_GRANARY_OUT_REQS');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('BAIQI_GRANARY_OUT_FOOD','YieldType','YIELD_FOOD'),('BAIQI_GRANARY_OUT_FOOD','Amount','0'),
('BAIQI_GRANARY_OUT_HOUSING','Amount','0');


WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType)
SELECT 'BAIQI_GRANARY_IN_'||i||'_REQS','REQUIREMENTSET_TEST_ALL' FROM slots;
WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO Requirements (RequirementId, RequirementType)
SELECT 'BAIQI_GRANARY_IN_'||i||'_REQ','REQUIREMENT_PLOT_PROPERTY_MATCHES' FROM slots;
WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId)
SELECT 'BAIQI_GRANARY_IN_'||i||'_REQS','BAIQI_GRANARY_IN_'||i||'_REQ' FROM slots;
WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO RequirementArguments (RequirementId, Name, Value)
SELECT 'BAIQI_GRANARY_IN_'||i||'_REQ','PropertyName','BAIQI_GRANARY_IN' FROM slots
UNION ALL SELECT 'BAIQI_GRANARY_IN_'||i||'_REQ','PropertyMinimum',CAST(i AS TEXT) FROM slots;
WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId)
SELECT 'BAIQI_GRANARY_IN_'||i||'_FOOD','MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE','BAIQI_GRANARY_IN_'||i||'_REQS' FROM slots
UNION ALL SELECT 'BAIQI_GRANARY_IN_'||i||'_HOUSING','MODIFIER_SINGLE_CITY_ADJUST_CITY_HOUSING_FROM_GREAT_PEOPLE','BAIQI_GRANARY_IN_'||i||'_REQS' FROM slots;
WITH RECURSIVE slots(i) AS (VALUES(1) UNION ALL SELECT i+1 FROM slots WHERE i<16)
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT 'BAIQI_GRANARY_IN_'||i||'_FOOD','YieldType','YIELD_FOOD' FROM slots
UNION ALL SELECT 'BAIQI_GRANARY_IN_'||i||'_FOOD','Amount','0' FROM slots
UNION ALL SELECT 'BAIQI_GRANARY_IN_'||i||'_HOUSING','Amount','0' FROM slots;
