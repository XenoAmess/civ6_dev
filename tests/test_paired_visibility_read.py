import unittest
from unittest.mock import Mock, patch, call

from tools.paired_visibility_read import read_visibility
from tools.paired_player_callback import make_callback


def frames(value):
    return [{'tag': -1, 'payload': 'O\0DiplomacyActionView: PAIR142_DIPLO\t'+value},
            {'tag': 3, 'payload': ''}]


class TunerReadError(OSError):
    pass


class PairedVisibilityReadTest(unittest.TestCase):
    def assert_reads_only(self, query, count):
        self.assertEqual(query.call_args_list, [call('DiplomacyActionView',
                         "print('PAIR142_DIPLO',not ContextPtr:IsHidden())")]*count)

    def test_true_false_are_exact_booleans_with_one_query(self):
        for value, expected in [('true', True), ('false', False)]:
            with self.subTest(value=value):
                query, sleep = Mock(return_value=frames(value)), Mock()
                self.assertIs(read_visibility(query, sleep, Mock()), expected)
                self.assert_reads_only(query, 1)
                sleep.assert_not_called()

    def test_transport_and_eof_recovery_repeat_only_fixed_read(self):
        query = Mock(side_effect=[TunerReadError('empty frame'), EOFError('closed'), frames('false')])
        sleep, emit = Mock(), Mock()
        self.assertIs(read_visibility(query, sleep, emit), False)
        self.assert_reads_only(query, 3)
        self.assertEqual(sleep.call_args_list, [call(.25), call(.25)])
        self.assertEqual(emit.call_count, 2)
        self.assertIn('TunerReadError', emit.call_args_list[0].args[0])

    def test_exhaustion_preserves_last_exception_and_bound(self):
        for attempts in (1, 2, 3):
            with self.subTest(attempts=attempts):
                errors = [TunerReadError(str(i)) for i in range(attempts)]
                query, sleep = Mock(side_effect=errors), Mock()
                with self.assertRaises(TunerReadError) as caught:
                    read_visibility(query, sleep, Mock(), attempts=attempts)
                self.assertIs(caught.exception, errors[-1])
                self.assert_reads_only(query, attempts)
                self.assertEqual(sleep.call_count, attempts-1)

    def test_malformed_missing_duplicate_and_err_do_not_retry(self):
        for value in ([], frames('TRUE'), frames('false\textra'), frames('true')*2,
                      [{'tag': 3, 'payload': 'ERR: actual Native refusal'}]):
            with self.subTest(value=value):
                query, sleep = Mock(return_value=value), Mock()
                with self.assertRaises(RuntimeError):
                    read_visibility(query, sleep, Mock())
                self.assert_reads_only(query, 1)
                sleep.assert_not_called()

    def test_other_exceptions_propagate_without_retry(self):
        for error in (ValueError('bad data'), RuntimeError('Native ERR')):
            query, sleep = Mock(side_effect=error), Mock()
            with self.assertRaises(type(error)) as caught:
                read_visibility(query, sleep, Mock())
            self.assertIs(caught.exception, error)
            self.assert_reads_only(query, 1)
            sleep.assert_not_called()

    def test_invalid_counts_never_query(self):
        class IntSubclass(int):
            pass
        for attempts in (True, False, None, 0, 4, 1., IntSubclass(2)):
            query = Mock()
            with self.assertRaises(ValueError):
                read_visibility(query, Mock(), Mock(), attempts=attempts)
            query.assert_not_called()

    def test_invalid_dependencies_never_query(self):
        for index in range(3):
            query = Mock()
            args = [query, Mock(), Mock()]
            args[index] = None
            with self.assertRaises(TypeError):
                read_visibility(*args)
            query.assert_not_called()

    def test_real_player_callback_recovers_read_and_issues_end_once(self):
        query = Mock(side_effect=[TunerReadError('empty frame'), frames('false'),
                                  frames('false'), frames('false')])
        child = Mock(return_value='P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP')
        token = 'a'*32
        ack = dict(turn=6, token=token, initial_turn=6, source='baiqi142-pressure-paired-v1',
                   source_version=142, requested=True, forced=False)
        with patch('tools.paired_player_callback.request_pressure_end', return_value=ack) as end:
            callback = make_callback(query, child, Mock(),
                lambda: read_visibility(query, Mock(), Mock()), pressure_initial_turn=6)
            self.assertIs(callback(6, token), ack)
            end.assert_called_once_with(query, 6, token, initial_turn=6)
        self.assert_reads_only(query, 4)
        child.assert_called_once_with('select', 6, 1)

    def test_real_player_callback_stops_before_input_on_unknown_visibility(self):
        query, child = Mock(return_value=frames('unknown')), Mock()
        with patch('tools.paired_player_callback.request_pressure_end') as end:
            callback = make_callback(query, child, Mock(),
                lambda: read_visibility(query, Mock(), Mock()), pressure_initial_turn=6)
            with self.assertRaises(RuntimeError):
                callback(6, 'a'*32)
            end.assert_not_called()
        child.assert_not_called()
        self.assert_reads_only(query, 1)


if __name__ == '__main__':
    unittest.main()
