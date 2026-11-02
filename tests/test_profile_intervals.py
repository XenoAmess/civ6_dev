import itertools
import math
import unittest
from collections import UserDict
from types import MappingProxyType

from tools.profile_intervals import union_seconds


class ProfileIntervalTests(unittest.TestCase):
    def test_empty_and_zero_length(self):
        self.assertEqual(union_seconds([]), 0.0)
        self.assertEqual(union_seconds([(2, 2)]), 0.0)

    def test_nested_intervals_are_not_double_counted(self):
        self.assertEqual(union_seconds([(0, 7), (1, 4), (2, 3), (0, 7)]), 7.0)

    def test_touching_and_disjoint_intervals(self):
        self.assertEqual(union_seconds([(0, 2), (2, 4), (6, 9)]), 7.0)

    def test_unordered_negative_endpoints(self):
        self.assertEqual(union_seconds([(5, 8), (-4, -2), (-3, 1), (10, 11)]), 9.0)

    def test_fractions_and_outer_iterator(self):
        self.assertEqual(union_seconds(iter([(1.25, 2.5), (2, 3.75)])), 2.5)

    def test_does_not_mutate_input(self):
        rows = [[5, 7], [0, 6]]
        before = [row[:] for row in rows]
        self.assertEqual(union_seconds(rows), 7.0)
        self.assertEqual(rows, before)

    def test_independent_integer_cell_oracle(self):
        choices = [(a, b) for a in range(-2, 3) for b in range(a, 3)]
        for rows in itertools.product(choices, repeat=3):
            expected = len({cell for a, b in rows for cell in range(a, b)})
            self.assertEqual(union_seconds(rows), expected, rows)

    def test_invalid_outer_input(self):
        for value in (None, 3, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                union_seconds(value)

    def test_invalid_pair_shapes(self):
        for pair in ([], [0], [0, 1, 2], '01', b'01', bytearray(b'01'),
                     {0: 1, 1: 2}, UserDict({0: 4, 1: 5}),
                     MappingProxyType({0: 4, 1: 5}), {0, 1}, frozenset({0, 1})):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                union_seconds([pair])
        with self.assertRaises(ValueError):
            union_seconds([(x for x in (0, 1))])

    def test_invalid_endpoint_values(self):
        for value in (True, False, None, '1', math.nan, math.inf, -math.inf):
            for pair in ((value, 2), (0, value)):
                with self.subTest(pair=pair), self.assertRaises(ValueError):
                    union_seconds([pair])

    def test_reversed_interval(self):
        with self.assertRaises(ValueError):
            union_seconds([(2, 1)])

    def test_float_representation_overflow_fails_closed(self):
        # Additional owner boundary: never emit inf or leak OverflowError.
        for rows in ([(0, 10**1000)], [(-1e308, 1e308)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                union_seconds(rows)
