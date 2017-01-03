import unittest
import os
import time

from aiml import Kernel


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class KernelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kernel = Kernel()
        cls.kernel.bootstrap(learn_file_paths=os.path.join(BASE_DIR, "self-test.aiml"))

    def test_bot(self):
        self.assertIn(self.kernel.respond('test bot'), ["My name is Nameless"])
    
    def test_condition_test_1(self):
        self.kernel.set_predicate('gender', 'male')
        self.assertIn(self.kernel.respond('test condition name value'), ['You are handsome'])

    def test_condition_test_2(self):
        self.kernel.set_predicate('gender', 'female')
        self.assertIn(self.kernel.respond('test condition name value'), [''])

    def test_condition_test_3(self):
        self.assertIn(self.kernel.respond('test condition name'), ['You are beautiful'])

    def test_condition_test_4(self):
        self.kernel.set_predicate('gender', 'robot')
        self.assertIn(self.kernel.respond('test condition name'), ['You are genderless'])

    def test_condition_test_5(self):
        self.assertIn(self.kernel.respond('test condition'), ['You are genderless'])

    def test_condition_test_6(self):
        self.kernel.set_predicate('gender', 'male')
        self.assertIn(self.kernel.respond('test condition'), ['You are handsome'])

    def test_date(self):
        # the date test will occasionally fail if the original and "test"
        # times cross a second boundary.
        self.assertIn(self.kernel.respond('test date'), ["The date is %s" % time.asctime()])

    def _test_tag(self, tag, input, output_list):
        """Tests 'tag' by feeding the Kernel 'input'.  If the result
        matches any of the strings in 'outputList', the test passes.
        """
        response = self.kernel.respond(input)
        self.assertIn(response, output_list)

    def test_tags(self):
        self._test_tag('formal', 'test formal', ["Formal Test Passed"])
        self._test_tag('gender', 'test gender', ["He'd told her he heard that her hernia is history"])
        self._test_tag('get/set', 'test get and set', ["I like cheese. My favorite food is cheese"])
        self._test_tag('gossip', 'test gossip', ["Gossip is not yet implemented"])
        self._test_tag('id', 'test id', ["Your id is _global"])
        self._test_tag('input', 'test input', ['You just said: test input'])
        self._test_tag('javascript', 'test javascript', ["Javascript is not yet implemented"])
        self._test_tag('lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
        self._test_tag('person', 'test person', ['HE think i knows that my actions threaten him and his.'])
        self._test_tag('person2', 'test person2', ['YOU think me know that my actions threaten you and yours.'])
        self._test_tag('person2 (no contents)', 'test person2 I Love Lucy', ['YOU Love Lucy'])
        self._test_tag('random', 'test random', ["response #1", "response #2", "response #3"])
        self._test_tag('random empty', 'test random empty', ["Nothing here!"])
        self._test_tag('sentence', "test sentence", ["My first letter should be capitalized."])
        self._test_tag('size', "test size", ["I've learned %d categories" % self.kernel.num_categories()])
        self._test_tag('sr', "test sr test srai", ["srai results: srai test passed"])
        self._test_tag('sr nested', "test nested sr test srai", ["srai results: srai test passed"])
        self._test_tag('srai', "test srai", ["srai test passed"])
        self._test_tag('srai infinite', "test srai infinite", [""])
        self._test_tag('star test #1', 'You should test star begin', ['Begin star matched: You should'])
        self._test_tag('star test #2', 'test star creamy goodness middle', ['Middle star matched: creamy goodness'])
        self._test_tag('star test #3', 'test star end the credits roll', ['End star matched: the credits roll'])
        self._test_tag('star test #4', 'test star having multiple stars in a pattern makes me extremely happy',
                 ['Multiple stars matched: having, stars in a pattern, extremely happy'])
        self._test_tag('system', "test system", ["The system says hello!"])
        self._test_tag('that test #1', "test that", ["I just said: The system says hello!"])
        self._test_tag('that test #2', "test that", ["I have already answered this question"])
        self._test_tag('thatstar test #1', "test thatstar", ["I say beans"])
        self._test_tag('thatstar test #2', "test thatstar", ["I just said \"beans\""])
        self._test_tag('thatstar test #3', "test thatstar multiple", ['I say beans and franks for everybody'])
        self._test_tag('thatstar test #4', "test thatstar multiple", ['Yes, beans and franks for all!'])
        self._test_tag('think', "test think", [""])
        self.kernel.set_predicate("topic", "fruit")
        self._test_tag('topic', "test topic", ["We were discussing apples and oranges"])
        self.kernel.set_predicate("topic", "Soylent Green")
        self._test_tag('topicstar test #1', 'test topicstar', ["Solyent Green is made of people!"])
        self.kernel.set_predicate("topic", "Soylent Ham and Cheese")
        self._test_tag('topicstar test #2', 'test topicstar multiple', ["Both Soylents Ham and Cheese are made of people!"])
        self._test_tag('unicode support', "郧上好", ["Hey, you speak Chinese! 郧上好"])
        self._test_tag('uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
        self._test_tag('version', 'test version', ["PyAIML is version %s" % self.kernel.version()])
        self._test_tag('whitespace preservation', 'test whitespace', ["Extra   Spaces\n   Rule!   (but not in here!)    But   Here   They   Do!"])
