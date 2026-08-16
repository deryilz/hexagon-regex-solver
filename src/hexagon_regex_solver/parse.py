from dataclasses import dataclass
from lark import Lark, Transformer, v_args

# the RegexNode implemented in this file isn't actually full regex support
# for example, it doesn't allow for nested captures or categories like \d or \s
# but it's enough to support the regexes seen in the puzzle

class RegexNode:
    pass

@dataclass
class Literal(RegexNode):
    char_code: int

@dataclass
class AnyChar(RegexNode):
    pass

@dataclass
class Range(RegexNode):
    low: int
    high: int

@dataclass
class CharClass(RegexNode):
    items: list[RegexNode]
    negated: bool = False

@dataclass
class SubPattern(RegexNode):
    data: list[RegexNode]

@dataclass
class Branch(RegexNode):
    options: list[RegexNode]

@dataclass
class Group(RegexNode):
    group_id: int
    content: RegexNode

@dataclass
class GroupRef(RegexNode):
    group_id: int

@dataclass
class Repeat(RegexNode):
    lower: int
    upper: int | None
    subvalue: SubPattern

REGEX_GRAMMAR = r"""
?start: regex

?regex: sequence ("|" sequence)*
sequence: item*

?item: atom
     | atom "*" -> star
     | atom "+" -> plus
     | atom "?" -> question_mark
     | atom "{" NUMBER "}" -> exact
     | atom "{" NUMBER "," "}" -> min_only
     | atom "{" NUMBER "," NUMBER "}" -> min_max

?atom: CHAR -> literal
     | ESCAPED -> escaped
     | "." -> any_char
     | "(" regex ")" -> group
     | BACKREF -> group_ref
     | "[" set_items "]" -> char_set
     | "[^" set_items "]" -> negated_set

set_items: set_item+
?set_item: SET_CHAR "-" SET_CHAR -> char_range
         | escaped_char "-" escaped_char -> char_range
         | SET_CHAR -> literal
         | escaped_char -> escaped

// Inside a set, \1 is treated as an escaped char, not a backreference
?escaped_char: ESCAPED | BACKREF

CHAR: /[^|*+?{}()[\]\\.]/
SET_CHAR: /[^\]\\-]/
BACKREF.2: /\\[1-9][0-9]*/
ESCAPED: /\\./

%import common.NUMBER
"""

class RegexASTBuilder(Transformer):
    def __init__(self):
        super().__init__()
        self.group_counter = 0

    @v_args(inline=True)
    def literal(self, char_token):
        return Literal(ord(str(char_token)))

    @v_args(inline=True)
    def escaped(self, char_token):
        return Literal(ord(str(char_token)[1]))

    @v_args(inline=True)
    def char_range(self, start_token, end_token):
        lower = ord(str(start_token))
        upper = ord(str(end_token))
        return Range(lower, upper)

    def set_items(self, args):
        return args

    @v_args(inline=True)
    def char_set(self, items):
        return CharClass(items, negated=False)

    @v_args(inline=True)
    def negated_set(self, items):
        return CharClass(items, negated=True)

    @v_args(inline=True)
    def any_char(self):
        return AnyChar()

    @v_args(inline=True)
    def group_ref(self, num_token):
        return GroupRef(int(str(num_token).replace("\\", "")))

    @v_args(inline=True)
    def group(self, regex_node):
        self.group_counter += 1
        return Group(self.group_counter, regex_node)

    def sequence(self, args):
        return SubPattern(args)

    def regex(self, args):
        if len(args) == 1:
            return args[0]
        return Branch(args)

    @v_args(inline=True)
    def star(self, atom):
        return Repeat(0, None, SubPattern([atom]))

    @v_args(inline=True)
    def plus(self, atom):
        return Repeat(1, None, SubPattern([atom]))

    @v_args(inline=True)
    def question_mark(self, atom):
        return Repeat(0, 1, SubPattern([atom]))

    @v_args(inline=True)
    def exact(self, atom, num):
        n = int(str(num))
        return Repeat(n, n, SubPattern([atom]))

    @v_args(inline=True)
    def min_only(self, atom, num):
        n = int(str(num))
        return Repeat(n, None, SubPattern([atom]))

    @v_args(inline=True)
    def min_max(self, atom, num1, num2):
        n1 = int(str(num1))
        n2 = int(str(num2))
        return Repeat(n1, n2, SubPattern([atom]))

def parse(regex):
    parser = Lark(REGEX_GRAMMAR, parser="lalr", lexer="contextual", start="regex")
    tree = parser.parse(regex)
    return RegexASTBuilder().transform(tree)
