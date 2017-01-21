"""
This file contains the public interface to the aiml module.
"""
import configparser
import copy
import glob
import os
import random
import re
import string
import time
import threading
import xml.sax
import logging

from . import aiml_parser
from . import default_subs
from . import utils
from . import pattern_mgr
from . import word_sub
from . import __version__

import numpy as np
from . import big5
import datetime

logger = logging.getLogger(__name__)


class Kernel():
    # module constants
    _GLOBAL_SESSION_ID = "_global"  # key of the global session (duh)
    _MAX_HISTORY_SIZE = 10  # maximum length of the _inputs and _responses lists
    _MAX_RECURSION_DEPTH = 100  # maximum number of recursive <srai>/<sr> tags before the response is aborted.
    # special predicate keys
    _INPUT_HISTORY = "_inputHistory"  # keys to a queue (list) of recent user input
    _OUTPUT_HISTORY = "_outputHistory"  # keys to a queue (list) of recent responses.
    _INPUT_STACK = "_inputStack"  # Should always be empty in between calls to respond()

    def __init__(self):
        self._brain = pattern_mgr.PatternMgr()
        self._respond_lock = threading.RLock()

        # set up the sessions        
        self._sessions = {}
        self._add_session(self._GLOBAL_SESSION_ID)

        # Set up the bot predicates
        self._bot_predicates = {}
        self.set_bot_predicate("name", "Nameless")

        # set up the word substitutors (subbers):
        self._subbers = {}
        self._subbers['gender'] = word_sub.WordSub(default_subs.default_gender)
        self._subbers['person'] = word_sub.WordSub(default_subs.default_person)
        self._subbers['person2'] = word_sub.WordSub(default_subs.default_person2)
        self._subbers['normal'] = word_sub.WordSub(default_subs.default_normal)

        # set up the element processors
        self._element_processors = {
            "bot": self._process_bot,
            "condition": self._process_сondition,
            "date": self._process_date,
            "formal": self._process_formal,
            "gender": self._process_gender,
            "get": self._process_get,
            "gossip": self._process_gossip,
            "id": self._process_id,
            "input": self._process_input,
            "javascript": self._process_javascript,
            "learn": self._process_learn,
            "li": self._process_li,
            "lowercase": self._process_lowercase,
            "person": self._process_person,
            "person2": self._process_person_2,
            "random": self._process_random,
            "text": self._process_text,
            "sentence": self._process_sentence,
            "set": self._process_set,
            "size": self._process_size,
            "sr": self._process_sr,
            "srai": self._process_srai,
            "star": self._process_star,
            "system": self._process_system,
            "template": self._process_template,
            "that": self._process_that,
            "thatstar": self._process_that_star,
            "think": self._process_think,
            "topicstar": self._process_topicstar,
            "uppercase": self._process_uppercase,
            "version": self._process_version,
        }

    def bootstrap(self, brain_file_path='', learn_file_paths=(), commands=()):
        """Prepare a Kernel object for use.

        Args:
            brain_file_path (str): if provided, the Kernel attempts to load the brain at the
                specified filename
            learn_file_paths (list, tuple): list of AIML files to load by the Kernel
            commands (list, tuple): input strings to pass to respond()
        """
        start = time.clock()
        if brain_file_path:
            self.load_brain(brain_file_path)

        # learnFiles might be a string, in which case it should be
        # turned into a single-element list.
        if not isinstance(learn_file_paths, (list, tuple)):
            learn_file_paths = [learn_file_paths]
        for file_path in learn_file_paths:
            self.learn(file_path)

        if not isinstance(commands, (list, tuple)):
            commands = [commands]
        for cmd in commands:
            logger.info(self._respond(cmd, self._GLOBAL_SESSION_ID))

        logger.debug("Kernel bootstrap completed in %.2f seconds", time.clock() - start)

    def version(self):
        """Return the Kernel's version string.
        """
        return "PyAIML %s" % __version__

    def num_categories(self):
        """Return the number of categories the Kernel has learned.
        """
        # there's a one-to-one mapping between templates and categories
        return self._brain.num_templates()

    def load_brain(self, filename):
        """Attempt to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!

        """
        logger.debug("Loading brain from %s...", filename)
        start = time.clock()
        self._brain.restore(filename)

        logger.debug("done (%d categories in %.2f seconds)",
                     self._brain.num_templates(), time.clock() - start)

    def save_brain(self, filename):
        """Dump the contents of the bot's brain to a file on disk."""
        logger.info("Saving brain to %s...", filename)
        start = time.clock()
        self._brain.save(filename)
        logger.info("done (%.2f seconds)", time.clock() - start)

    def get_predicate(self, name, session_id=_GLOBAL_SESSION_ID):
        """Retrieve the current value of the predicate 'name' from the
        specified session.

        If name is not a valid predicate in the session, the empty
        string is returned.

        """
        if name == "result":
            return big5.best_match(np.array([
                float(self._sessions[session_id].get("neuroticism",0)),
                float(self._sessions[session_id].get("extraversion",0)),
                float(self._sessions[session_id].get("openness",0)),
                float(self._sessions[session_id].get("agreeableness",0)),
                float(self._sessions[session_id].get("conscientiousness",0)),
                ])) 
        elif name == "resultdebug":
            return str([float(self._sessions[session_id].get("neuroticism",0)),
                    float(self._sessions[session_id].get("extraversion",0)),
                    float(self._sessions[session_id].get("openness",0)),
                    float(self._sessions[session_id].get("agreeableness",0)),
                    float(self._sessions[session_id].get("conscientiousness",0))])
        elif name == "tageszeit":
            h = datetime.datetime.now().time().hour
            if h < 12:
                return "Morgen"
            elif h >= 12 and h <= 18:
                return "Tag"
            elif h > 18:
                return "Abend"
        elif name == "zeit":
            h = datetime.datetime.now().time().hour
            m = datetime.datetime.now().time().minute
            return str(h) + ":" + str(m)
        else:
            try:
                return self._sessions[session_id][name]
            except KeyError:
                return ""

    def set_predicate(self, name, value, session_id=_GLOBAL_SESSION_ID):
        """Set the value of the predicate 'name' in the specified
        session.

        If session_id is not a valid session, it will be created. If
        name is not a valid predicate in the session, it will be
        created.
        """
        self._add_session(session_id)  # add the session, if it doesn't already exist.
        if name == "neuroticism" or name == "extraversion" or name == "openness" or name == "agreeableness" or name == "conscientiousness": 
            if not name in self._sessions[session_id]:
                self._sessions[session_id][name] = "0"
            #print(self._sessions[session_id][name])
            #print(float(value))
            #print(float(self._sessions[session_id][name]) +  float(value))
            self._sessions[session_id][name] = str(float(self._sessions[session_id][name]) +  float(value))
        elif name[:6] == "ignore":
            big5.ignore_subject(name[7:])
        else:
            self._sessions[session_id][name] = value

    def get_bot_predicate(self, name):
        """Retrieve the value of the specified bot predicate.
        If name is not a valid bot predicate, the empty string is returned.
        """
        return self._bot_predicates.get(name, "")

    def set_bot_predicate(self, name, value):
        """Set the value of the specified bot predicate.
        If name is not a valid bot predicate, it will be created.
        """
        self._bot_predicates[name] = value
        # Clumsy hack: if updating the bot name, we must update the name in the brain as well
        if name == "name":
            self._brain.set_bot_name(self.get_bot_predicate("name"))

    def load_subs(self, filename):
        """Load a substitutions file.
        The file must be in the Windows-style INI format (see the
        standard ConfigParser module docs for information on this
        format).  Each section of the file is loaded into its own
        substituter.
        """
        parser = configparser.ConfigParser()
        parser.read(filename)
        for s in parser.sections():
            # Add a new WordSub instance for this section.  If one already exists, delete it.
            if s in self._subbers:
                del (self._subbers[s])
            self._subbers[s] = word_sub.WordSub()
            # iterate over the key,value pairs and add them to the subber
            for k, v in parser.items(s):
                self._subbers[s][k] = v

    def _add_session(self, session_id):
        """Create a new session with the specified ID string.
        """
        if session_id in self._sessions:
            return
        # Create the session.
        self._sessions[session_id] = {
            # Initialize the special reserved predicates
            self._INPUT_HISTORY: [],
            self._OUTPUT_HISTORY: [],
            self._INPUT_STACK: []
        }

    def _delete_session(self, session_id):
        """Delete the specified session.
        """
        if session_id in self._sessions:
            self._sessions.pop(session_id)

    def get_session_data(self, session_id=None):
        """Return a copy of the session data dictionary for the specified session.
        If no session_id is specified, return a dictionary containing *all* of the individual
        session dictionaries.
        """
        if session_id is not None:
            session = self._sessions.get(session_id, {})
        else:
            session = self._sessions
        return copy.deepcopy(session)

    def learn(self, file_path):
        """Load and learn the contents of the specified AIML file.
        If filename includes wildcard characters, all matching files will be loaded and learned.
        """
        file_path = os.path.abspath(file_path)
        file_dir = os.path.dirname(file_path)
        for f in glob.iglob(file_path):
            logger.debug("Loading %s...", f)
            start = time.clock()
            # Load and parse the AIML file.
            parser = aiml_parser.create_parser()
            handler = parser.getContentHandler()
            try:
                parser.parse(f)
            except xml.sax.SAXParseException as msg:
                logger.error("Parse error: %s", msg)
                continue
            # store the pattern/template pairs in the PatternMgr.
            for (pattern, that, topic), tem in handler.categories.items():
                # make path to learn files absolute
                for elem_name, _, *elem_children in tem[2:]:
                    if elem_name == 'learn':
                        elem_children[0][2] = os.path.join(file_dir, elem_children[0][2])

                self._brain.add(pattern, that, topic, tem)
            # Parsing was successful.
            logger.debug("done (%.2f seconds)", time.clock() - start)

    def respond(self, input, session_id=_GLOBAL_SESSION_ID):
        """Return the Kernel's response to the input string.
        """
        if len(input) == 0:
            return ""

        # prevent other threads from stomping all over us.
        self._respond_lock.acquire()

        # Add the session, if it doesn't already exist
        self._add_session(session_id)

        # split the input into discrete sentences
        sentences = utils.sentences(input)
        final_response = ""
        for s in sentences:
            # Add the input to the history list before fetching the
            # response, so that <input/> tags work properly.
            input_history = self.get_predicate(self._INPUT_HISTORY, session_id)
            input_history.append(s)
            del input_history[:-self._MAX_HISTORY_SIZE]

            # Fetch the response
            response = self._respond(s, session_id)

            # add the data from this exchange to the history lists
            output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
            output_history.append(response)
            del output_history[:-self._MAX_HISTORY_SIZE]

            # append this response to the final response.
            final_response += (response + "  ")
        final_response = final_response.strip()

        assert len(self.get_predicate(self._INPUT_STACK, session_id)) == 0

        # release the lock and return
        self._respond_lock.release()
        return final_response

    # This version of _respond() just fetches the response for some input.
    # It does not mess with the input and output histories.  Recursive calls to respond() spawned
    # from tags like <srai> should call this function instead of respond().
    def _respond(self, input, session_id):
        """Private version of respond(), does the real work.
        """
        if len(input) == 0:
            return ""

        # guard against infinite recursion
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        if len(input_stack) > self._MAX_RECURSION_DEPTH:
            logger.warning("Maximum recursion depth exceeded (input='%s')", input)
            return ""

        # push the input onto the input stack
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        input_stack.append(input)
        self.set_predicate(self._INPUT_STACK, input_stack, session_id)

        # run the input through the 'normal' subber
        subbed_input = self._subbers['normal'].sub(input)

        # fetch the bot's previous response, to pass to the match() function as 'that'.
        output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
        that = output_history[-1] if output_history else ""
        subbed_that = self._subbers['normal'].sub(that)

        # fetch the current topic
        topic = self.get_predicate("topic", session_id)
        subbed_topic = self._subbers['normal'].sub(topic)

        # Determine the final response.
        response = ""
        elem = self._brain.match(subbed_input, subbed_that, subbed_topic)
        if elem is None:
            logger.warning("No match found for input: %s", input)
        else:
            # Process the element into a response string.
            response += self._process_element(elem, session_id).strip()
            response += " "
        response = response.strip()

        # pop the top entry off the input stack.
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        input_stack.pop()
        self.set_predicate(self._INPUT_STACK, input_stack, session_id)

        return response

    def _process_element(self, elem, session_id):
        """Process an AIML element.
        The first item of the elem list is the name of the element's XML tag.  The second item is a
        dictionary containing any attributes passed to that tag, and their values.  Any further
        items in the list are the elements enclosed by the current element's begin and end tags;
        they are handled by each element's handler function.
        """
        try:
            handler_func = self._element_processors[elem[0]]
        except KeyError:
            # Oops -- there's no handler function for this element type!
            logger.warning("No handler found for <%s> element", elem[0])
            return ""
        return handler_func(elem, session_id)

    #----------------------------------------------------------------------------------------------
    # Individual element-processing functions follow
    #----------------------------------------------------------------------------------------------

    # <bot>
    def _process_bot(self, elem, session_id):
        """Process a <bot> AIML element.
        Required element attributes:
            name: The name of the bot predicate to retrieve.
        <bot> elements are used to fetch the value of global, read-only "bot predicates."  These
        predicates cannot be set from within AIML; you must use the setBotPredicate() function.
        """
        attr_тame = elem[1]['name']
        return self.get_bot_predicate(attr_тame)

    # <condition>
    def _process_сondition(self, elem, session_id):
        """Process a <condition> AIML element.

        Optional element attributes:
            name: The name of a predicate to test.
            value: The value to test the predicate for.

        <condition> elements come in three flavors.  Each has different
        attributes, and each handles their contents differently.

        The simplest case is when the <condition> tag has both a 'name'
        and a 'value' attribute.  In this case, if the predicate
        'name' has the value 'value', then the contents of the element
        are processed and returned.
        
        If the <condition> element has only a 'name' attribute, then
        its contents are a series of <li> elements, each of which has
        a 'value' attribute.  The list is scanned from top to bottom
        until a match is found.  Optionally, the last <li> element can
        have no 'value' attribute, in which case it is processed and
        returned if no other match is found.

        If the <condition> element has neither a 'name' nor a 'value'
        attribute, then it behaves almost exactly like the previous
        case, except that each <li> subelement (except the optional
        last entry) must now include both 'name' and 'value'
        attributes.
        """
        response = ""
        attr = elem[1]

        # Case #1: test the value of a specific predicate for a
        # specific value.
        if 'name' in attr and 'value' in attr:
            val = self.get_predicate(attr['name'], session_id)
            if val == attr['value']:
                for e in elem[2:]:
                    response += self._process_element(e, session_id)
                return response
        else:
            # Case #2 and #3: Cycle through <li> contents, testing a
            # name and value pair for each one.
            try:
                name = None
                if 'name' in attr:
                    name = attr['name']
                # Get the list of <li> elemnents
                list_items = []
                for e in elem[2:]:
                    if e[0] == 'li':
                        list_items.append(e)
                # if list_items is empty, return the empty string
                if len(list_items) == 0:
                    return ""
                # iterate through the list looking for a condition that matches.
                found_match = False
                for li in list_items:
                    try:
                        li_attr = li[1]
                        # if this is the last list item, it's allowed
                        # to have no attributes.  We just skip it for now.
                        if not li_attr and li == list_items[-1]:
                            continue
                        # get the name of the predicate to test
                        li_name = name
                        if li_name is None:
                            li_name = li_attr['name']
                        # get the value to check against
                        li_value = li_attr['value']
                        # do the test
                        if self.get_predicate(li_name, session_id) == li_value:
                            found_match = True
                            response += self._process_element(li, session_id)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        logger.exception("Something amiss -- skipping listitem %r", li)
                        raise
                if not found_match:
                    # Check the last element of list_items.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = list_items[-1]
                        li_attr = li[1]
                        if not ('name' in li_attr or 'value' in li_attr):
                            response += self._process_element(li, session_id)
                    except:
                        # list_items was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        logger.exception("error in default listitem")
                        raise
            except:
                # Some other catastrophic cataclysm
                logger.fatal("Catastrophic condition failure")
                raise
        return response

    # <date>
    def _process_date(self, elem, session_id):
        """Process a <date> AIML element.
        <date> elements resolve to the current date and time. The AIML specification doesn't
        require any particular format for this information, so I go with whatever's simplest.
        """
        return time.asctime()

    # <formal>
    def _process_formal(self, elem, session_id):
        """Process a <formal> AIML element.
        <formal> elements process their contents recursively, and then capitalize the first letter
        of each word of the result.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return string.capwords(response)

    # <gender>
    def _process_gender(self, elem, session_id):
        """Process a <gender> AIML element.
        <gender> elements process their contents, and then swap the gender of any third-person
        singular pronouns in the result. This subsitution is handled by the aiml.word_sub module.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return self._subbers['gender'].sub(response)

    # <get>
    def _process_get(self, elem, session_id):
        """Process a <get> AIML element.
        Required element attributes:
            name: The name of the predicate whose value should be
            retrieved from the specified session and returned.  If the
            predicate doesn't exist, the empty string is returned.
        <get> elements return the value of a predicate from the
        specified session.

        """
        return self.get_predicate(elem[1]['name'], session_id)

    # <gossip>
    def _process_gossip(self, elem, session_id):
        """Process a <gossip> AIML element.
        <gossip> elements are used to capture and store user input in an implementation-defined
        manner, theoretically allowing the bot to learn from the people it chats with.  I haven't
        decided how to define my implementation, so right now <gossip> behaves identically to
        <think>.
        """
        return self._process_think(elem, session_id)

    # <id>
    def _process_id(self, elem, session_id):
        """ Process an <id> AIML element.
        <id> elements return a unique "user id" for a specific conversation.  In PyAIML, the user
        id is the name of the current session.
        """
        return session_id

    # <input>
    def _process_input(self, elem, session_id):
        """Process an <input> AIML element.
        Optional attribute elements:
            index: The index of the element from the history list to
            return. 1 means the most recent item, 2 means the one
            before that, and so on.

        <input> elements return an entry from the input history for the current session.
        """
        input_history = self.get_predicate(self._INPUT_HISTORY, session_id)
        try:
            index = int(elem[1]['index'])
        except:
            index = 1
        try:
            return input_history[-index]
        except IndexError:
            logger.warning("No such index %d while processing <input> element.", index)
            return ""

    # <javascript>
    def _process_javascript(self, elem, session_id):
        """Process a <javascript> AIML element.
        <javascript> elements process their contents recursively, and then run the results through
        a server-side Javascript interpreter to compute the final response.  Implementations are
        not required to provide an actual Javascript interpreter, and right now PyAIML doesn't;
        <javascript> elements are behave exactly like <think> elements.
        """
        return self._process_think(elem, session_id)

    # <learn>
    def _process_learn(self, elem, session_id):
        """Process a <learn> AIML element.
        <learn> elements process their contents recursively, and then treat the result as an AIML
        file to open and learn.
        """
        file_path = ""
        for e in elem[2:]:
            file_path += self._process_element(e, session_id)
        self.learn(file_path)
        return ""

    # <li>
    def _process_li(self, elem, session_id):
        """Process an <li> AIML element.
        Optional attribute elements:
            name: the name of a predicate to query.
            value: the value to check that predicate for.
        <li> elements process their contents recursively and return the results. They can only
        appear inside <condition> and <random> elements.  See _processCondition() and
        _processRandom() for details of their usage.
         """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return response

    # <lowercase>
    def _process_lowercase(self, elem, session_id):
        """Process a <lowercase> AIML element.
        <lowercase> elements process their contents recursively, and then convert the results to
        all-lowercase.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return response.lower()

    # <person>
    def _process_person(self, elem, session_id):
        """Process a <person> AIML element.
        <person> elements process their contents recursively, and then convert all pronouns in the
        results from 1st person to 2nd person, and vice versa. This subsitution is handled by the
        aiml.word_sub module.
        If the <person> tag is used atomically (e.g. <person/>), it is a shortcut for
        <person><star/></person>.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        if len(elem[2:]) == 0:  # atomic <person/> = <person><star/></person>
            response = self._process_element(['star', {}], session_id)
        return self._subbers['person'].sub(response)

    # <person2>
    def _process_person_2(self, elem, session_id):
        """Process a <person2> AIML element.
        <person2> elements process their contents recursively, and then convert all pronouns in the
        results from 1st person to 3rd person, and vice versa.  This subsitution is handled by the
        aiml.word_sub module.
        If the <person2> tag is used atomically (e.g. <person2/>), it is a shortcut for
        <person2><star/></person2>.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        if len(elem[2:]) == 0:  # atomic <person2/> = <person2><star/></person2>
            response = self._process_element(['star', {}], session_id)
        return self._subbers['person2'].sub(response)

    # <random>
    def _process_random(self, elem, session_id):
        """Process a <random> AIML element.
        <random> elements contain zero or more <li> elements.  If
        none, the empty string is returned.  If one or more <li>
        elements are present, one of them is selected randomly to be
        processed recursively and have its results returned.  Only the
        chosen <li> element's contents are processed.  Any non-<li> contents are
        ignored.
        """
        listitems = []
        for e in elem[2:]:
            if e[0] == 'li':
                listitems.append(e)
        if len(listitems) == 0:
            return ""

        # select and process a random listitem.
        random.shuffle(listitems)
        return self._process_element(listitems[0], session_id)

    # <sentence>
    def _process_sentence(self, elem, session_id):
        """Process a <sentence> AIML element.
        <sentence> elements process their contents recursively, and
        then capitalize the first letter of the results.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        # TODO: response = response.strip().capitalize()
        try:
            response = response.strip()
            words = response.split(" ", 1)
            words[0] = words[0].capitalize()
            response = ' '.join(words)
            return response
        except IndexError:  # response was empty
            return ""

    # <set>
    def _process_set(self, elem, session_id):
        """Process a <set> AIML element.
        Required element attributes:
            name: The name of the predicate to set.
        <set> elements process their contents recursively, and assign the results to a predicate
        (given by their 'name' attribute) in the current session.  The contents of the element
        are also returned.
        """
        value = ""
        for e in elem[2:]:
            value += self._process_element(e, session_id)
        self.set_predicate(elem[1]['name'], value, session_id)
        return value

    # <size>
    def _process_size(self, elem, session_id):
        """Process a <size> AIML element.
        <size> elements return the number of AIML categories currently in the bot's brain.
        """
        return str(self.num_categories())

    # <sr>
    def _process_sr(self, elem, session_id):
        """Process an <sr> AIML element.
        <sr> elements are shortcuts for <srai><star/></srai>.
        """
        star = self._process_element(['star', {}], session_id)
        response = self._respond(star, session_id)
        return response

    # <srai>
    def _process_srai(self, elem, session_id):
        """Process a <srai> AIML element.
        <srai> elements recursively process their contents, and then
        pass the results right back into the AIML interpreter as a new
        piece of input.  The results of this new input string are
        returned.
        """
        new_input = ""
        for e in elem[2:]:
            new_input += self._process_element(e, session_id)
        return self._respond(new_input, session_id)

    # <star>
    def _process_star(self, elem, session_id):
        """Process a <star> AIML element.
        Optional attribute elements:
            index: Which "*" character in the current pattern should
            be matched?
        <star> elements return the text fragment matched by the "*"
        character in the current input pattern.  For example, if the
        input "Hello Tom Smith, how are you?" matched the pattern
        "HELLO * HOW ARE YOU", then a <star> element in the template
        would evaluate to "Tom Smith".
        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        response = self._brain.star("star", input, that, topic, index)
        return response

    # <system>
    def _process_system(self, elem, session_id):
        """Process a <system> AIML element.
        <system> elements process their contents recursively, and then
        attempt to execute the results as a shell command on the
        server.  The AIML interpreter blocks until the command is
        complete, and then returns the command's output.

        For cross-platform compatibility, any file paths inside
        <system> tags should use Unix-style forward slashes ("/") as a
        directory separator.
        """
        # build up the command string
        command = ""
        for e in elem[2:]:
            command += self._process_element(e, session_id)

        # normalize the path to the command.  Under Windows, this switches forward-slashes to
        # back-slashes; all system elements should use unix-style paths for cross-platform
        # compatibility.
        # executable,args = command.split(" ", 1)
        #executable = os.path.normpath(executable)
        #command = executable + " " + args
        command = os.path.normpath(command)

        # execute the command.
        response = ""
        try:
            out = os.popen(command)
        except RuntimeError as msg:
            logger.warning("RuntimeError while processing \"system\" element:\n%s", msg)
            return "There was an error while computing my response.  Please inform my botmaster."
        time.sleep(0.01)  # I'm told this works around a potential IOError exception.
        for line in out:
            response += line + "\n"
        response = ' '.join(response.splitlines()).strip()
        return response

    # <template>
    def _process_template(self, elem, session_id):
        """Process a <template> AIML element.
        <template> elements recursively process their contents, and return the results.
        <template> is the root node of any AIML response tree.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return response

    # text
    def _process_text(self, elem, session_id):
        """Process a raw text element.
        Raw text elements aren't really AIML tags. Text elements cannot contain
        other elements; instead, the third item of the 'elem' list is a text
        string, which is immediately returned. They have a single attribute,
        automatically inserted by the parser, which indicates whether whitespace
        in the text should be preserved or not.
        """
        try:
            elem[2] + ""
        except TypeError:
            raise TypeError("Text element contents are not text")

        # If the the whitespace behavior for this element is "default", we reduce all stretches of
        # >1 whitespace characters to a single space.  To improve performance, we do this only once
        # for each text element encountered, and save the results for the future.
        if elem[1]["xml:space"] == "default":
            elem[2] = re.sub("\s+", " ", elem[2])
            elem[1]["xml:space"] = "preserve"
        return elem[2]

    # <that>
    def _process_that(self, elem, session_id):
        """Process a <that> AIML element.
        Optional element attributes:
            index: Specifies which element from the output history to
            return.  1 is the most recent response, 2 is the next most
            recent, and so on.
        <that> elements (when they appear inside <template> elements)
        are the output equivilant of <input> elements; they return one
        of the Kernel's previous responses.
        """
        output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
        index = 1
        try:
            # According to the AIML spec, the optional index attribute can either have the form "x"
            # or "x,y". x refers to how far back in the output history to go.  y refers to which
            # sentence of the specified response to return.
            index = int(elem[1]['index'].split(',')[0])
        except:
            pass
        try:
            return output_history[-index]
        except IndexError:
            logger.warning("No such index %d while processing <that> element.", index)
            return ""

    # <thatstar>
    def _process_that_star(self, elem, session_id):
        """Process a <thatstar> AIML element.
        Optional element attributes:
            index: Specifies which "*" in the <that> pattern to match.
        <thatstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <thatstar/> returns
        the portion of the previous input string that was matched by a
        "*" in the current category's <that> pattern.
        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        response = self._brain.star("thatstar", input, that, topic, index)
        return response

    # <think>
    def _process_think(self, elem, session_id):
        """Process a <think> AIML element.
        <think> elements process their contents recursively, and then
        discard the results and return the empty string.  They're
        useful for setting predicates and learning AIML files without
        generating any output.
        """
        for e in elem[2:]:
            self._process_element(e, session_id)
        return ""

    # <topicstar>
    def _process_topicstar(self, elem, session_id):
        """Process a <topicstar> AIML element.
        Optional element attributes:
            index: Specifies which "*" in the <topic> pattern to match.
        <topicstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <topicstar/>
        returns the portion of current topic string that was matched
        by a "*" in the current category's <topic> pattern.
        """
        try:
            index = int(elem[1]['index'])
        except KeyError:
            index = 1
        # fetch the user's last input
        input_stack = self.get_predicate(self._INPUT_STACK, session_id)
        input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Kernel's last response (for 'that' context)
        output_history = self.get_predicate(self._OUTPUT_HISTORY, session_id)
        try:
            that = self._subbers['normal'].sub(output_history[-1])
        except:
            that = ""  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        response = self._brain.star("topicstar", input, that, topic, index)
        return response

    # <uppercase>
    def _process_uppercase(self, elem, session_id):
        """Process an <uppercase> AIML element.
        <uppercase> elements process their contents recursively, and return the results with all
        lower-case characters converted to upper-case.
        """
        response = ""
        for e in elem[2:]:
            response += self._process_element(e, session_id)
        return response.upper()

    # <version>
    def _process_version(self, elem, session_id):
        """Process a <version> AIML element.
        <version> elements return the version number of the AIML interpreter.
        """
        return self.version()
