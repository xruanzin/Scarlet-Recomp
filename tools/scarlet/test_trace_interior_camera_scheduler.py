"""Synthetic guard tests for 0.17518; no game data is redistributed."""
import copy
import unittest

from inspect_lua_steps import OPS
from trace_interior_camera_scheduler import verify_scheduler


def ins(op, a=0, b=0, c=0, k=0):
    return (OPS.index(op) | (a << 7) | (k << 15) | (b << 16) | (c << 24))


def fixture():
    code = [ins('MOVE')] * 37
    code[32] = ins('SELF', 3, 0, 1, 1)
    code[33] = ins('MOVE', 5, 2)
    code[34] = ins('GETI', 6, 0, 22)
    code[35] = ins('CALL', 3, 4, 1)
    return {
        'code': code, 'params': 2, 'constants': [
            {'tag': 19, 'bits': '111111111111a13f', 'offset': 0x7efc05,
             'value': 1.0 / 30.0},
            {'tag': 4, 'bits': None, 'offset': 0x7efc15,
             'value': 'FC0150FC2959FFA71'},
        ],
    }


class SchedulerGuardTest(unittest.TestCase):
    def test_correct_dispatch(self):
        x = verify_scheduler(fixture())
        self.assertEqual(x['integer_count_argument'], 'scheduler self[22]')
        self.assertEqual(x['fixed_step_s'], 1 / 30)

    def test_wrong_member(self):
        p = fixture()
        p['constants'][1]['value'] = 'not-controller'
        with self.assertRaises(ValueError):
            verify_scheduler(p)

    def test_wrong_count_field(self):
        p = fixture()
        p['code'][34] = ins('GETI', 6, 0, 23)
        with self.assertRaises(ValueError):
            verify_scheduler(p)

    def test_wrong_timing_constant(self):
        p = fixture()
        p['constants'][0]['bits'] = '000000000000a03f'
        with self.assertRaises(ValueError):
            verify_scheduler(p)

    def test_wrong_call_arity(self):
        p = fixture()
        p['code'][35] = ins('CALL', 3, 3, 1)
        with self.assertRaises(ValueError):
            verify_scheduler(p)


if __name__ == '__main__':
    unittest.main()
