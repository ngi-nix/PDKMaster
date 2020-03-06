"""
A modgrammar for Cadence SKILL files

Top Grammar is SkillFile.
This grammar wants to parse all valid SKILL scripts, including Cadence text technology files,
Assura rules etc. This parser may parse invalid SKILL scripts.
"""

import re
from collections import OrderedDict

__all__ = ["SkillContext", "SkillFile"]

from modgrammar import (
    Grammar, L, NOT_FOLLOWED_BY, WORD, REF, OPTIONAL, WHITESPACE, ZERO_OR_MORE, ONE_OR_MORE,
)
from modgrammar.extras import RE

grammar_whitespace_mode = "explicit"
# Include comments in whitespace
grammar_whitespace = re.compile(r'(\s+|;.*?\n|/\*(.|\n)*?\*/)+')

# Override this value to True in user code to enable parser debug output.
_debug = False


#
# Data support functions
# Function value generation lookup table
#


#
# SKILL builtin functions
#
def _skill_let(elems, **kwargs):
    return {
        "vars": elems[0],
        "statements": elems[1],
    }

def _skill_for(elems, **kwargs):
    assert len(elems) > 3
    return {
        "var": elems[0],
        "begin": elems[1],
        "end": elems[2],
        "statements": elems[3:],
    }

def _skill_foreach(elems, **kwargs):
    assert len(elems) > 2
    return {
        "var": elems[0],
        "list": elems[1],
        "statements": elems[2:],
    }

def _skill_if(elems, **kwargs):
    thenidx = None
    elseidx = None
    for i, item in enumerate(elems):
        if type(item) is str:
            if item == "then":
                thenidx = i
            if item == "else":
                elseidx = i
    cond = elems[0]
    while isinstance(cond, list) and len(cond) == 1:
        cond = cond[0]
    value = {"cond": cond}
    if thenidx is not None:
        assert thenidx == 1
        value["then"] = elems[thenidx+1:elseidx]
        if elseidx is not None:
            value["else"] = elems[elseidx+1:]
    else:
        assert elseidx is None
        assert 2 <= len(elems) <= 3
        value["then"] = elems[1]
        if len(elems) > 2:
            value["else"] = elems[2]

    return value

def _skill_when(elems, **kwargs):
    assert len(elems) > 1
    cond = elems[0]
    while isinstance(cond, list) and len(cond) == 1:
        cond = cond[0]

    return {
        "cond": cond,
        "then": elems[1:],
    }

_builtins = {
    "let": _skill_let,
    "prog": _skill_let, # Dont make distinction in return() handling
    "for": _skill_for,
    "foreach": _skill_foreach,
    "if": _skill_if,
    "when": _skill_when,
}


#
# SKILL Grammar
#
class _BaseGrammar(Grammar):
    def __init__(self, *args):
        super().__init__(*args)
        if _debug:
            start = self._str_info[1]
            end = self._str_info[2]
            print("{}: {}-{}".format(self.__class__.__name__, start, end))

class Symbol(_BaseGrammar):
    grammar = RE(r"'[a-zA-Z_][a-zA-Z0-9_]*")

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:]
        self.ast = {"Symbol": self.value}

class Bool(_BaseGrammar):
    grammar = L("t")|L("nil"), NOT_FOLLOWED_BY(WORD("a-zA-Z0-9_"))

    def grammar_elem_init(self, sessiondata):
        self.value = self.string == "t"
        self.ast = {"Bool": self.value}

class Identifier(_BaseGrammar):
    grammar = WORD("a-zA-Z_?@", "a-zA-Z0-9_?@."), NOT_FOLLOWED_BY(L("("))

    def grammar_elem_init(self, sessiondata):
        self.ast = {"Identifier": self.string}
        self.value = self.string

class Number(_BaseGrammar):
    grammar = RE(r"(\+|\-)?([0-9]+(\.[0-9]*)?|\.[0-9]+)(e(\+|-)?[0-9]+)?")

    def grammar_elem_init(self, sessiondata):
        isfloat = ("." in self.string) or ("e" in self.string)
        self.value = float(self.string) if isfloat else int(self.string)
        self.ast = {"Number": self.value}

class String(_BaseGrammar):
    grammar = RE(r'"([^"\\]+|\\(.|\n))*"')

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:-1]
        self.ast = {"String": self.value}

class SignSymbol(_BaseGrammar):
    # +/- followed by a digit
    grammar_whitespace_mode = "explicit"
    grammar = RE(r"[\+\-](?=[0-9])")

class SignOperator(_BaseGrammar):
    # +/- not followed by a digit
    grammar = RE(r"[\+\-](?![\+\-0-9])")

class PrefixOperator(_BaseGrammar):
    grammar = L("!") | RE(r"\+(?!\+)") | RE(r"\-(?!-)")

class PostfixOperator(_BaseGrammar):
    grammar = L("++") | L("--")

class BinaryOperator(_BaseGrammar):
    grammar = (
        L("=") | L(":") | L("<") | L(">") | L("<=") | L(">=") | L("==") | L("!=") | L("<>") |
        SignOperator |
        L("*") | L("/") |
        L("&") | L("|") | L("&&") | L("||") |
        L(",")
    )

class FieldOperator(_BaseGrammar):
    grammar = L("->") | L("~>")

class ItemBase(_BaseGrammar):
    grammar = (
        (
            REF("Function") | REF("ArrayElement") | REF("List") | REF("SymbolList") | REF("CurlyList") |
            Bool | Identifier | Symbol | Number | String
        ),
        ZERO_OR_MORE(OPTIONAL(WHITESPACE), FieldOperator, OPTIONAL(WHITESPACE), Identifier),
        ZERO_OR_MORE(SignSymbol, REF("ItemBase")),
    )

    def grammar_elem_init(self, sessiondata):
        if (len(self[1].elements) + len(self[2].elements)) == 0:
            ast = self[0].ast
            value = self[0].value
        else:
            ast = [self[0].ast]
            value = [self[0].value]
            for _, op, _, ident in self[1]:
                ast += [op.string, ident.ast]
                value += [op.string, ident.value]
            for op, ident in self[2]:
                ast += [op.string, ident.ast]
                value += [op.string, ident.value]
        self.ast = {"ItemBase": ast}
        self.value = value

class Item(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = ZERO_OR_MORE(PrefixOperator), ItemBase, ZERO_OR_MORE(PostfixOperator)

    def grammar_elem_init(self, sessiondata):
        if len(self[0].elements) == 0 and len(self[2].elements) == 0:
            ast = self[1].ast
            value = self[1].value
        else:
            ast = [*[op.string for op in self[0]], self[1].ast, *[op.string for op in self[2]]]
            value = [*[op.string for op in self[0]], self[1].value, *[op.string for op in self[2]]]
            # Collapse a sign with a number
            for i in range(len(value)-1):
                v = value[i]
                v2 = value[i+1]
                # Join sign with number
                if (v in ("+", "-")) and isinstance(v2, (int, float)):
                    value[i:i+2] = [v2 if v == "+" else -v2]
                    if len(value) == 1:
                        value = value[0]
                    break
        self.ast = {"Item": ast}
        self.value = value

class Expression(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = Item, ZERO_OR_MORE(BinaryOperator, Item)

    def grammar_elem_init(self, sessiondata):
        if len(self[1].elements) == 0:
            ast = self[0].ast
            value = self[0].value
        else:
            ast = [self[0].ast]
            value = [self[0].value]
            for op, item in self[1]:
                ast += [op.string, item.ast]
                value += [op.string, item.value]
        self.ast = {"Expression": ast}
        self.value = value

class List(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = L("("), ZERO_OR_MORE(Expression), L(")")

    def grammar_elem_init(self, sessiondata):
        # Convert list to function if name of first identifier is in _value4function_table
        # and not in the _dont_convert_list
        isfunction = (
            (len(self[1].elements) > 0)
            and (type(self[1][0].value) is str)
            and (self[1][0].value in sessiondata["value4funcs"])
            and (self[1][0].value not in sessiondata["dont_convert"])
        )
        if not isfunction:
            self.value = [elem.value for elem in self[1]]
            self.ast = {"List": [elem.ast for elem in self[1]]}
        else:
            name = self[1][0].value
            elems = [elem.value for elem in self[1].elements[1:]]
            func = sessiondata["value4funcs"][name]
            if type(func) == tuple:
                func, kwargs = func
            else:
                kwargs = {}
            self.value = {name: func(elems, functionname=name, **kwargs)}

            self.ast = {"ListFunction": {
                "name": name,
                "args": [elem.ast for elem in self[1].elements[1:]],
            }}

class SymbolList(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = L("'("), ZERO_OR_MORE(Expression), L(")")

    def grammar_elem_init(self, sessiondata):
        self.value = [elem.value for elem in self[1]]
        self.ast = {"SymbolList": [elem.ast for elem in self[1]]}

class CurlyList(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = L("{"), ZERO_OR_MORE(Expression), L("}")

    def grammar_elem_init(self, sessiondata):
        self.value = {"{}": [elem.value for elem in self[1]]}
        self.ast = {"CurlyList": [elem.ast for elem in self[1]]}

class Function(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\("), ZERO_OR_MORE(Expression), L(')')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        elems = [elem.value for elem in self[1]]
        try:
            func = sessiondata["value4funcs"][name]
        except KeyError:
            self.value = {name: elems}
        else:
            if type(func) == tuple:
                func, kwargs = func
            else:
                kwargs = {}
            self.value = {name: func(elems, functionname=name, **kwargs)}

        self.ast = {"Function": {
            "name": name,
            "args": [elem.ast for elem in self[1]]
        }}

class ArrayElement(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\["), Expression, L(']')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        self.value = {"Array:"+name: self[1].value}
        self.ast = {"ArrayElem": {
            "name": name,
            "elem": self[1].ast
        }}

class SkillFile(_BaseGrammar):
    grammar_whitespace_mode = "optional"
    grammar = ONE_OR_MORE(Expression), OPTIONAL(WHITESPACE)

    def grammar_elem_init(self, sessiondata):
        self.ast = {"SkillFile": [elem.ast for elem in self[0]]}
        self.value = {"SkillFile": [elem.value for elem in self[0]]}

    @classmethod
    def parser(cls, sessiondata=None, *args, **kwargs):
        if ((sessiondata is None)
            or not all(s in sessiondata for s in ("value4funcs", "dont_convert"))
        ):
            raise Exception("{0}.parser() called directly; use {0}.parse_string()".format(
                cls.__name__
            ))
        return super(SkillFile, cls).parser(sessiondata=sessiondata, *args, **kwargs)

    @classmethod
    def parse_string(cls, text, *, value4funcs={}, dont_convert=[]):
        fs = _builtins.copy()
        fs.update(value4funcs)
        sessiondata = {
            "value4funcs": fs,
            "dont_convert": dont_convert,
        }

        p = cls.parser(sessiondata=sessiondata)
        return p.parse_string(text)
