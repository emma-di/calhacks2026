import unittest
from audio.events import Detector,load_policy

class DogParentGateTests(unittest.TestCase):
    def test_specific_dog_parent_and_bark_evidence_must_coincide(self):
        for scores,expected in [({'Dog':.828,'Yip':.089},True),({'Dog':.712,'Yip':.173},True),
                                ({'Dog':.822,'Yip':.0128},False),({'Domestic animals, pets':.99},False),
                                ({'Dog':.623,'Yip':.123},False),({'Bark':.3},True)]:
            with self.subTest(scores=scores):
                events=Detector(policy=load_policy(model_name='zipformer')).detect(scores,'simulation',now=0)
                self.assertEqual(any(e['type']=='dog_bark' for e in events),expected)

    def test_parent_from_previous_window_cannot_support_current_vocal_score(self):
        detector=Detector(policy=load_policy(model_name='zipformer'))
        self.assertEqual(detector.detect({'Dog':.9},'simulation',now=0),[])
        self.assertEqual(detector.detect({'Yip':.1},'simulation',now=1),[])

    def test_generic_pet_label_alone_is_not_a_dog(self):
        # The temporary "all Domestic animals, pets = Dog barking" demo override fired on cats, pigs,
        # horses and chewing in live use, so it was removed from both models.
        for model in ('zipformer','yamnet'):
            policy=load_policy(model_name=model)
            self.assertNotIn('demo_override',policy['rules']['dog_bark'])
            self.assertEqual(Detector(policy=policy).detect({'Domestic animals, pets':.9},'simulation',now=0),[])
