"""Synthetic tests for the structural camera-binding validator.

Only minimal Lua registration metadata; no copyrighted game data.
"""
import copy
import unittest
from verify_interior_camera_binding import verify, MEMBER, NAMESPACE
from inspect_interior_camera import EXPECTED_SHA256


def fixture():
    pc = 427260
    return {
        'file_sha256': EXPECTED_SHA256,
        'root_closure_registration_windows': {
            '0.30688': [{
                'closure_pc': pc,
                'instructions': [
                    {'pc': pc-3, 'op': 'LOADK', 'a': 69, 'constant': NAMESPACE},
                    {'pc': pc-2, 'op': 'GETTABLE', 'a': 68, 'b': 68, 'c': 69},
                    {'pc': pc-1, 'op': 'LOADK', 'a': 69, 'constant': MEMBER},
                    {'pc': pc, 'op': 'CLOSURE', 'a': 70, 'child_path': '0.30688'},
                    {'pc': pc+1, 'op': 'SETTABLE', 'a': 68, 'b': 69, 'c': 70},
                ],
            }],
        },
        'candidate_controller_call': {
            'proto': '0.17567', 'namespace': NAMESPACE, 'member': MEMBER,
            'pc_namespace': 31, 'pc_member': 32, 'pc_call': 37,
            'four_arguments': True,
        },
        'member_uses': [
            {'proto': '0.18722', 'hits': [{'pc': 352, 'member': MEMBER}]},
        ],
    }


class StaticBindingTest(unittest.TestCase):
    def test_expected_registration(self):
        result = verify(fixture())
        self.assertEqual(result['static_registration_verified'],
                         f'{NAMESPACE}.{MEMBER} -> 0.30688')
        self.assertFalse(result['active_gameplay_patch'])

    def test_wrong_member_is_rejected(self):
        doc = fixture()
        doc['root_closure_registration_windows']['0.30688'][0]['instructions'][2]['constant'] = 'wrong'
        with self.assertRaises(ValueError):
            verify(doc)

    def test_wrong_register_is_rejected(self):
        doc = fixture()
        doc['root_closure_registration_windows']['0.30688'][0]['instructions'][1]['c'] = 70
        with self.assertRaises(ValueError):
            verify(doc)

    def test_missing_other_consumer_is_rejected(self):
        doc = fixture()
        doc['member_uses'] = []
        with self.assertRaises(ValueError):
            verify(doc)

    def test_wrong_closure_is_rejected(self):
        doc = fixture()
        doc['root_closure_registration_windows']['0.30688'][0]['instructions'][3]['child_path'] = '0.30689'
        with self.assertRaises(ValueError):
            verify(doc)


if __name__ == '__main__':
    unittest.main()
