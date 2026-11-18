import ctypes as C
import unittest
from tools import wpr_sessions as s


def fill(array, capacity, count, names):
    C.cast(count, C.POINTER(C.c_uint32))[0] = len(names)
    for i, name in enumerate(names[:capacity]):
        p = array[i].contents
        raw = name.encode("utf-16-le") + b"\0\0"
        C.memmove(C.addressof(p) + p.LoggerNameOffset, raw, len(raw))
    return 0


class EtwInventoryTests(unittest.TestCase):
    def test_abi_and_unicode_query_only(self):
        self.assertEqual((C.sizeof(s.Wnode), C.sizeof(s.Properties)), (48, 120))
        names = ["EventLog-System", "Steam Event Tracing", "原生只读跟踪"]
        rows = s.query_all(lambda a, n, c: fill(a, n, c, names))
        self.assertEqual([r["name"] for r in rows], names)
        self.assertEqual(s.wpr_conflicts(rows), [])
        self.assertEqual(s.query_all(lambda a, n, c: fill(a, n, c, [])), [])

    def test_more_data_discards_partial_and_retries_readonly(self):
        calls = []

        def api(a, n, c):
            calls.append(n)
            if n == 64:
                C.cast(c, C.POINTER(C.c_uint32))[0] = 65
                return 234
            return fill(a, n, c, ["FinalOnly"])

        self.assertEqual(s.query_all(api)[0]["name"], "FinalOnly")
        self.assertEqual(calls, [64, 65])

    def test_unknown_counts_errors_names_and_offsets_fail(self):
        def make(kind):
            def api(a, n, c):
                fill(a, n, c, ["Known"])
                if kind == "status":
                    return 5
                if kind in ("same_capacity", "too_many", "overflow_count"):
                    C.cast(c, C.POINTER(C.c_uint32))[0] = {"same_capacity": n, "too_many": 1025, "overflow_count": n + 1}[kind]
                    return 0 if kind == "overflow_count" else 234
                p = a[0].contents
                if kind == "odd":
                    p.LoggerNameOffset = 121
                elif kind == "header":
                    p.LoggerNameOffset = 0
                elif kind == "outside":
                    p.LoggerNameOffset = p.Wnode.BufferSize
                elif kind == "empty":
                    C.memset(C.addressof(p) + p.LoggerNameOffset, 0, 2)
                elif kind == "unterminated":
                    C.memset(C.addressof(p) + p.LoggerNameOffset, 65, p.Wnode.BufferSize - p.LoggerNameOffset)
                elif kind == "surrogate":
                    C.memmove(C.addressof(p) + p.LoggerNameOffset, b"\x00\xd8\x00\x00", 4)
                return 0
            return api

        for case in ("status", "same_capacity", "too_many", "overflow_count", "odd", "header", "outside", "empty", "unterminated", "surrogate"):
            with self.subTest(case=case), self.assertRaises((OSError, ValueError, UnicodeError)):
                s.query_all(make(case))
        with self.assertRaises(ValueError):
            s.query_all(lambda a, n, c: fill(a, n, c, ["Same", "sAME"]))

    def test_wpr_names_own_session_and_malformed_inventory(self):
        rows = [{"name": n} for n in ("EventLog-System", "WPR_initiated_Other_CPU", "WPR_initiated_civ6_diag_abc_CPU")]
        self.assertEqual(s.wpr_conflicts(rows, "civ6_diag_abc"), ["WPR_initiated_Other_CPU"])
        self.assertEqual(len(s.wpr_conflicts(rows)), 2)
        for bad in (None, {}, [{"name": ""}], [{"name": 1}], [{"name": "A"}, {"name": "a"}], [{}] * 1025):
            with self.subTest(value=repr(bad)[:50]), self.assertRaises(ValueError):
                s.wpr_conflicts(bad)


if __name__ == "__main__":
    unittest.main()
