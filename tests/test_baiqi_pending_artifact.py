import unittest
from pending_artifact_harness import pending_runtime


class PendingArtifactTests(unittest.TestCase):
    def fixture(self, **overrides):
        values = pending_runtime()
        for key, value in overrides.items():
            values[-2][key] = value
        return values

    def inspect(self, values):
        _, inspect, player, game, game_info, configurations, _, _ = values
        return inspect(4, player, game, game_info, configurations)

    def test_actual_numeric_unit_type_and_complete_scalar_descriptor(self):
        values = self.fixture()
        descriptor, status = self.inspect(values)
        self.assertEqual(status, 'pending')
        self.assertEqual(dict(descriptor), {'unitID': 100001, 'unitType': 'UNIT_ARCHAEOLOGIST',
            'homeCityID': 65536, 'x': 8, 'y': 9, 'artifactIndex': 7,
            'artifactType': 3, 'actingPlayerID': 2, 'choicePlayerID': 2, 'targetPlayerID': 3})
        self.assertEqual((values[-1].component, values[-1].index, values[-1].artifact), (1, 1, 1))

    def test_no_pending_returns_before_touching_other_dependencies(self):
        values = self.fixture(pendingState='none', throwAt='artifact_lookup')
        lua, inspect, player, _, _, _, _, trace = values
        poison = lua.execute("return setmetatable({}, {__index=function() error('touched') end})")
        self.assertEqual(inspect(4, player, poison, poison, poison), (None, 'none'))
        self.assertEqual((trace.component, trace.index, trace.artifact), (0, 0, 0))
        self.assertEqual(self.inspect(self.fixture(pendingState='false')), (None, 'unavailable'))

    def test_other_unit_types_never_read_artifact_index(self):
        for kind in ('UNIT_NATURALIST', 'UNIT_APOSTLE', 'UNIT_INQUISITOR', 'UNIT_GURU', 'UNIT_MISSIONARY', 'UNIT_WARRIOR'):
            values = self.fixture(unitType=kind)
            self.assertEqual(self.inspect(values), (None, 'unavailable'))
            self.assertEqual((values[-1].component, values[-1].index, values[-1].artifact), (0, 0, 0))

    def test_id_owner_and_home_must_match_before_artifact_read(self):
        for override in ({'liveID': 2}, {'unitOwner': 3}, {'liveOwner': 3},
                         {'homeID': -1}, {'cityID': 3}, {'homeOwner': 2}, {'x': -1}):
            with self.subTest(override=override):
                values = self.fixture(**override)
                self.assertEqual(self.inspect(values), (None, 'unavailable'))
                self.assertEqual(values[-1].artifact, 0)

    def test_no_choice_artifacts_ignore_target(self):
        for kind in (1, 2, 5):
            descriptor, status = self.inspect(self.fixture(artifactType=kind, targetID=-1, configMissingID=3))
            self.assertEqual((status, descriptor.choicePlayerID), ('pending', 2))
            self.assertIsNone(descriptor.targetPlayerID)

    def test_artifact_and_configuration_validation(self):
        for override in ({'artifactIndex': -1}, {'artifactIndex': True}, {'artifactType': 6},
                         {'artifactType': 0.5}, {'actingID': -1}, {'configMissingID': 2},
                         {'targetID': -1}, {'configMissingID': 3}):
            with self.subTest(override=override):
                self.assertEqual(self.inspect(self.fixture(**override)), (None, 'unavailable'))

    def test_native_errors_never_escape(self):
        for point in ('get_pending', 'artifact_lookup', 'artifact_component', 'artifact_index', 'city_lookup'):
            self.assertEqual(self.inspect(self.fixture(throwAt=point)), (None, 'unavailable'))
        values = self.fixture()
        lua, inspect, _, game, game_info, configurations, _, _ = values
        poison = lua.execute("return setmetatable({}, {__index=function() error('member') end})")
        self.assertEqual(inspect(4, poison, game, game_info, configurations), (None, 'unavailable'))


if __name__ == '__main__':
    unittest.main()
