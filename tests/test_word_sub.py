import unittest

import aiml.word_sub


class WordSubsTests(unittest.TestCase):

    def test_word_subs(self):
        subber = aiml.word_sub.WordSub()
        subber["apple"] = "banana"
        subber["orange"] = "pear"
        subber["banana"] = "apple"
        subber["he"] = "she"
        subber["I'd"] = "I would"

        # test case insensitivity
        self.assertEqual(
            subber.sub("I'd like one apple, one Orange and one BANANA."),
            "I Would like one banana, one Pear and one APPLE.")

        self.assertEqual(
            subber.sub("He said he'd like to go with me"),
            "She said she'd like to go with me")
