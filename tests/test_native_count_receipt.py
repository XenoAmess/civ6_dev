import unittest
from tools.native_count_receipt import require_count_receipt


class NativeCountReceiptTests(unittest.TestCase):
    marker = 'QUOTA184_RETIRED_OWN_QA_ANCHORS'

    def row(self, value='34'):
        return {'tag': -1, 'payload': 'O\0BaiqiExecutor: ' + self.marker + '\t' + value}

    def test_actual_counted_shape_accepts_34(self):
        messages = [{'tag': 4, 'payload': 'LSQ'}, self.row(), {'tag': 3, 'payload': ''}]
        self.assertEqual(require_count_receipt(messages, self.marker, 34), 34)

    def test_old_count_and_prefix_matches_are_rejected(self):
        for value in ('33', '340', '34.0', '34 extra', '34\t0', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_count_receipt([self.row(value)], self.marker, 34)

    def test_missing_duplicate_and_foreign_marker_are_rejected(self):
        for messages in ([], [self.row(), self.row()], [{'tag': -1, 'payload': 'OTHER\t34'}]):
            with self.subTest(messages=messages), self.assertRaises(ValueError):
                require_count_receipt(messages, self.marker, 34)

    def test_native_error_cannot_be_hidden_by_counted_print(self):
        with self.assertRaises(RuntimeError):
            require_count_receipt([self.row(), {'tag': 3, 'payload': 'ERR: failure'}], self.marker, 34)

    def test_invalid_count_marker_or_envelope_is_rejected(self):
        for count in (True, '34', 34.0, 0, 81):
            with self.subTest(count=count), self.assertRaises(ValueError):
                require_count_receipt([self.row()], self.marker, count)
        for marker in ('', 'BAD\tMARKER', 'lowercase'):
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                require_count_receipt([self.row()], marker, 34)
        for messages in (None, [None], [{'tag': True, 'payload': 'x'}], [{'tag': -1, 'payload': None}]):
            with self.subTest(messages=messages), self.assertRaises((TypeError, ValueError)):
                require_count_receipt(messages, self.marker, 34)


if __name__ == '__main__':
    unittest.main()
