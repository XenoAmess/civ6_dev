from collections import UserDict
from itertools import product
from types import MappingProxyType
import math
import unittest

from tools.clock_offsets import intersect_offsets


class ClockOffsetTests(unittest.TestCase):
    def test_negative_intersection_order_and_generator(self):
        samples=[(10,5,12),(20,15,25),(30,25,35)]
        expected={'samples':3,'lower_seconds':-7.0,'upper_seconds':-5.0,'consistent':True}
        self.assertEqual(intersect_offsets(samples),expected)
        self.assertEqual(intersect_offsets(reversed(samples)),expected)
        self.assertEqual(intersect_offsets(x for x in samples),expected)

    def test_disjoint_intervals_retain_ordered_conflict_bounds(self):
        result=intersect_offsets([(10,100,11),(20,200,21)])
        self.assertEqual(result,{'samples':2,'lower_seconds':179.0,'upper_seconds':90.0,'consistent':False})
        self.assertGreater(result['lower_seconds'],result['upper_seconds'])

    def test_binary_fraction_boundary_zero_and_exact_output_types(self):
        result=intersect_offsets([(0,.25,.5),(1,1.125,1.25)])
        self.assertEqual(result,{'samples':2,'lower_seconds':-.125,'upper_seconds':.125,'consistent':True})
        self.assertIs(type(result['samples']),int)
        self.assertIs(type(result['lower_seconds']),float)
        self.assertIs(type(result['upper_seconds']),float)
        self.assertIs(type(result['consistent']),bool)
        self.assertEqual(intersect_offsets([(0,0,0)])['lower_seconds'],0.0)

    def test_reject_outer_mapping_even_when_keys_are_valid_triples(self):
        mapping={(1,2,3):'not a sample'}
        for bad in (None,3,True,[],iter(()),'abc',b'abc',bytearray(b'abc'),mapping,UserDict(mapping),MappingProxyType(mapping)):
            with self.subTest(kind=type(bad)):
                with self.assertRaises(ValueError):intersect_offsets(bad)

    def test_reject_inner_shapes_and_all_invalid_endpoint_positions(self):
        for bad in (None,[],[0],[0,1],[0,1,2,3],'012',b'012',bytearray(b'012'),{0:1,1:2,2:3},UserDict({0:1}),MappingProxyType({0:1}),{0,1,2},iter((0,1,2))):
            with self.subTest(shape=type(bad)):
                with self.assertRaises(ValueError):intersect_offsets([bad])
        for bad in (True,False,None,'1',math.nan,math.inf,-math.inf,-1):
            for position in range(3):
                values=[1,2,3];values[position]=bad
                with self.subTest(value=bad,position=position):
                    with self.assertRaises(ValueError):intersect_offsets([values])
        with self.assertRaises(ValueError):intersect_offsets([(10**1000,10**1000,10**1000)])

    def test_raw_integer_order_precedes_lossy_float_conversion(self):
        with self.assertRaises(ValueError):intersect_offsets([(2**53+1,10,2**53)])
        self.assertTrue(intersect_offsets([(2**53,10,2**53+1)])['consistent'])
        self.assertEqual(intersect_offsets([(10,100,12)])['lower_seconds'],88.0)

    def test_integer_offset_oracle_for_all_5625_small_sample_pairs(self):
        samples=[(a,c,z) for a,c,z in product(range(5),repeat=3) if a<=z]
        self.assertEqual(len(samples)**2,5625)
        for first,second in product(samples,repeat=2):
            # Independently enumerate possible offset values by translating the
            # Core reading back into the UI interval, without constructing bounds.
            expected={d for d in range(-4,5) if all(a<=c-d<=z for a,c,z in (first,second))}
            result=intersect_offsets((first,second))
            actual={d for d in range(-4,5) if result['lower_seconds']<=d<=result['upper_seconds']}
            self.assertEqual(actual,expected,(first,second,result))
            self.assertIs(result['consistent'],bool(expected),(first,second,result))
            self.assertEqual(result['samples'],2)


if __name__=='__main__':
    unittest.main()
