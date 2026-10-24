"""Evaluation must use the same temporal suppression as the live detector."""
import unittest
from audio.benchmark import LABELS, score
from audio.events import Detector

class BenchmarkParityTests(unittest.TestCase):
    def test_alarm_tail_replay_matches_live_rule(self):
        rule={'labels':{'Bell':1},'threshold':.75,
              'suppressors':{'Alarm clock':.3},'suppressor_hold_seconds':2}
        frames=[{'Bell':.8,'Alarm clock':.9},{'Bell':.8},{'Bell':.7}]
        row={'windows':[[frame.get(label,0) for label in LABELS] for frame in frames],
             'hop_seconds':1,'scores':{'Bell':.8,'Alarm clock':.9}}
        self.assertAlmostEqual(score(row,rule),.7)
        detector=Detector(policy={'rules':{'bell':rule}})
        emitted=[event for index,frame in enumerate(frames)
                 for event in detector.detect(frame,'simulation',now=index)]
        self.assertEqual(emitted,[])

if __name__=='__main__':
    unittest.main()
