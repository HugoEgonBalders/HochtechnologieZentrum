"""
This module implements the WordSub class, modelled after a recipe
in "Python Cookbook" (Recipe 3.14, "Replacing Multiple Patterns in a
Single Pass" by Xavier Defrang).

Usage:
Use this class like a dictionary to add before/after pairs:
    > subber = TextSub()
    > subber["before"] = "after"
    > subber["begin"] = "end"
Use the sub() method to perform the substitution:
    > print subber.sub("before we begin")
    after we end
All matching is intelligently case-insensitive:
    > print subber.sub("Before we BEGIN")
    After we END
The 'before' words must be complete words -- no prefixes.
The following example illustrates this point:
    > subber["he"] = "she"
    > print subber.sub("he says he'd like to help her")
    she says she'd like to help her
Note that "he" and "he'd" were replaced, but "help" and "her" were
not.
"""

import re
import string


class WordSub(dict):
    """All-in-one multiple-string-substitution class.
    """
    def __init__(self, defaults={}):
        """Initialize the object, and populate it with the entries in
        the defaults dictionary.
        """
        self._regex = None
        self._regex_is_dirty = True
        for k, v in defaults.items():
            self[k] = v

    def _word_to_regex(self, word):
        """Convert a word to a regex object which matches the word.
        """
        if word != "" and word[0].isalpha() and word[-1].isalpha():
            return "\\b%s\\b" % re.escape(word)
        else:
            return r"\b%s\b" % re.escape(word)

    def _update_regex(self):
        """Build re object based on the keys of the current dictionary.
        """
        self._regex = re.compile("|".join(map(self._word_to_regex, self)))
        self._regex_is_dirty = False

    def __call__(self, match):
        """Handler invoked for each regex match.
        """
        return self[match.group(0)]

    def __setitem__(self, key, value):
        self._regex_is_dirty = True
        # for each entry the user adds, we actually add three entrys:
        super().__setitem__(key.lower(), value.lower())  # key = value
        super().__setitem__(string.capwords(key), string.capwords(value))  # Key = Value
        super().__setitem__(key.upper(), value.upper())  # KEY = VALUE

    def sub(self, text):
        """Translate text, returns the modified text.
        """
        if self._regex_is_dirty:
            self._update_regex()
        return self._regex.sub(self, text)
