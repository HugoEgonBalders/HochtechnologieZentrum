import unittest

import aiml.utils


class UtilTests(unittest.TestCase):

    def test_sentences(self):
        sents = aiml.utils.sentences("First.  Second, still?  Third and Final!  Well, not really")
        self.assertEqual(len(sents), 4)
