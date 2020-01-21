"""
A modgrammar for Cadence SKILL files

Top Grammar is SkillFile.
This grammar wants to parse all valid SKILL scripts, including Cadence text technology files,
Assura rules etc. This parser may parse invalid SKILL scripts.
"""

import re
from collections import OrderedDict

from modgrammar import *
from modgrammar.extras import *

grammar_whitespace_mode = "optional"
# Include comments in whitespace
grammar_whitespace = re.compile(r'(\s+|;.*?\n|/\*(.|\n)*?\*/)+')

# Override this value to True in user code to enable parser debug output.
_debug = False


class _BaseGrammar(Grammar):
    def __init__(self, *args):
        super().__init__(*args)
        self._start = start = args[1]
        self._end = end = args[2]
        if _debug:
            print("{}: {}-{}".format(self.__class__.__name__, start, end))

class Symbol(_BaseGrammar):
    grammar = RE(r"'[a-zA-Z_][a-zA-Z0-9_]*")

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:]
        self.ast = {"Symbol": self.value}

class Identifier(_BaseGrammar):
    grammar = WORD("a-zA-Z_?@", "a-zA-Z0-9_?@.")

    def grammar_elem_init(self, sessiondata):
        self.ast = {"Identifier": self.string}
        self.value = self.string

class Number(_BaseGrammar):
    grammar = RE(r"(\+|-)?([0-9]+(\.[0-9]*)?|\.[0-9]+)(e(\+|-)?[0-9]+)?")

    def grammar_elem_init(self, sessiondata):
        isfloat = ("." in self.string) or ("e" in self.string)
        self.value = float(self.string) if isfloat else int(self.string)
        self.ast = {"Number": self.value}

class String(_BaseGrammar):
    grammar = RE(r'"([^"\\]+|\\(.|\n))*"')

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:-1]
        self.ast = {"String": self.value}

class OperatorSymbol(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar_collapse = True
    grammar = (
        L("=") | L(":") | L("!") | L("<") | L(">") | L("<=") | L(">=") | L("==") | L("!=") | L("<>") |
        L("+") | L("-") | L("*") | L("/") | L("++") | L("--") |
        L("&") | L("|") | L("&&") | L("||") |
        L(",") |
        L("->") | L("~>")
    )

class Operator(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = OperatorSymbol, NOT_FOLLOWED_BY(OperatorSymbol)

    def grammar_elem_init(self, sessiondata):
        self.ast = {"Operator": self.string}
        self.value = self.string

class Item(_BaseGrammar):
    grammar = (
        REF("Function") | REF("ArrayElement") | REF("List") | REF("SymbolList") | REF("CurlyList") |
        Identifier | Symbol | Number | String | Operator
    )

    def grammar_elem_init(self, sessiondata):
        self.ast = self[0].ast
        self.value = self[0].value

class List(_BaseGrammar):
    grammar = L("("), ZERO_OR_MORE(Item), L(")")

    def grammar_elem_init(self, sessiondata):
        self.value = [elem.value for elem in self[1]]
        self.ast = {"List": [elem.ast for elem in self[1]]}

class SymbolList(_BaseGrammar):
    grammar = L("'("), ZERO_OR_MORE(Item), L(")")

    def grammar_elem_init(self, sessiondata):
        self.value = [elem.value for elem in self[1]]
        self.ast = {"SymbolList": [elem.ast for elem in self[1]]}

class CurlyList(_BaseGrammar):
    grammar = L("{"), ZERO_OR_MORE(Item), L("}")

    def grammar_elem_init(self, sessiondata):
        self.value = {"{}": [elem.value for elem in self[1]]}
        self.ast = {"CurlyList": [elem.ast for elem in self[1]]}

class Function(_BaseGrammar):
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\("), ZERO_OR_MORE(Item), L(')')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        self.value = {name: [elem.value for elem in self[1]]}
        self.ast = {"Function": {
            "name": name,
            "args": [elem.ast for elem in self[1]]
        }}

class ArrayElement(_BaseGrammar):
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\["), Item, L(']')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        self.value = {"Array:"+name: self[1].value}
        self.ast = {"ArrayElem": {
            "name": name,
            "elem": self[1].ast
        }}

class SkillFile(_BaseGrammar):
    grammar = G(ONE_OR_MORE(Item), OPTIONAL(WHITESPACE))

    def grammar_elem_init(self, sessiondata):
        self.ast = {"SkillFile": [elem.ast for elem in self[0][0]]}
        self.value = {"SkillFile": [elem.value for elem in self[0][0]]}
