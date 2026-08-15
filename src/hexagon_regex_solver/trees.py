# specific to python 3.12, might break but im too LAZY to fix
# if anyone knows an actual regex parser please open a pull request
from re._parser import parse, SubPattern
import re._constants as c

# this whole module is about simplifying regexes into equations
# some features aren't supported yet, including nested captures - they'd definitely break this
# feel free to open a pull request if you think anything's missing

# takes a variable-length regex and generates regexes whose lengths are known
# essentially expands all *, +, ? operations as well as |
# doesn't touch [] or . or \1 etc
def get_simpler_trees(regex_tree, limit, captures):
    if type(regex_tree) == SubPattern:
        if len(regex_tree.data) == 0:
            yield regex_tree
            return

        rest = SubPattern(None, regex_tree.data[1:])
        for tree in get_simpler_trees(regex_tree.data[0], limit, captures):
            length = simple_length(tree, captures)
            for seq in get_simpler_trees(rest, limit - length, captures.copy()):
                full = SubPattern(None, [tree] + seq.data)
                yield full
        return

    token, value = regex_tree
    match token:
        case c.LITERAL | c.NOT_LITERAL | c.ANY | c.IN:
            if limit >= 1:
                yield regex_tree

        case c.SUBPATTERN if value[0] is not None:
            for tree in get_simpler_trees(value[-1], limit, captures):
                captures[value[0]] = tree
                yield [token, value[:-1] + (tree,)] # wrap it up

        case c.BRANCH:
            for option in value[1]:
                yield from get_simpler_trees(option, limit, captures.copy())

        case c.GROUPREF:
            if simple_length(captures[value], captures) <= limit:
                yield regex_tree

        case c.MAX_REPEAT | c.MIN_REPEAT:
            lower, upper, subvalue = value

            if type(upper) != int or upper > limit:
                upper = limit

            for i in range(lower, upper + 1):
                pattern = SubPattern(None, subvalue.data * i)
                yield from get_simpler_trees(pattern, limit, captures.copy())

        case _:
            raise Exception(f"Unexpected regex type {token}")

# length of a simplified tree, or None if the tree isn't simplified
def simple_length(regex_tree, captures):
    if type(regex_tree) == SubPattern:
        length = 0
        for part in regex_tree.data:
            part_length = simple_length(part, captures)
            if part_length is None:
                return None
            else:
                length += part_length
        return length

    token, value = regex_tree
    match token:
        case c.LITERAL | c.NOT_LITERAL | c.ANY | c.IN:
            return 1
        case c.SUBPATTERN if value[0] is not None:
            captures[value[0]] = value[-1]
            return simple_length(value[-1], captures)
        case c.GROUPREF:
            return simple_length(captures[value], captures)
        case c.BRANCH | c.MAX_REPEAT | c.MIN_REPEAT:
            return None
        case _:
            raise Exception(f"Unexpected regex type {token}")

def show_simple(regex_tree, captures):
    if type(regex_tree) == SubPattern:
        return "".join(show_simple(part, captures) for part in regex_tree.data)

    token, value = regex_tree
    match token:
        case c.LITERAL:
            return chr(value)
        case c.NOT_LITERAL:
            return "^" # TODO
        case c.ANY:
            return "."
        case c.IN:
            return "?" # TODO
        case c.SUBPATTERN if value[0] is not None:
            captures[value[0]] = value[-1]
            return show_simple(value[-1], captures)
        case c.GROUPREF:
            return show_simple(captures[value], captures)
        case _:
            raise Exception(f"Expected simplified regex but got {token}")

def get_equations(regex, slots):
    from z3 import And, Or, Not

    good_simple_trees = []
    for tree in get_simpler_trees(parse(regex), len(slots), {}):
        if simple_length(tree, {}) == len(slots):
            good_simple_trees.append(tree)

    def equations(regex_tree, captures, locations, i):
        if type(regex_tree) == SubPattern:
            conds = []
            for tree in regex_tree.data:
                conds.append(equations(tree, captures, locations, i))
                i += simple_length(tree, captures)
            return And(conds) if conds else True

        token, value = regex_tree
        match token:
            case c.LITERAL:
                return slots[i] == value
            case c.NOT_LITERAL:
                return slots[i] != value
            case c.ANY:
                return True
            case c.IN:
                normal = [tree for tree in value if tree[0] != c.NEGATE]
                is_negated = len(normal) != len(value)
                eq = Or(equations(option, captures, locations, i) for option in normal)
                return Not(eq) if is_negated else eq
            case c.RANGE:
                low, high = value
                return And(slots[i] >= low, slots[i] <= high)
            case c.SUBPATTERN if value[0] is not None:
                captures[value[0]] = value[-1]
                locations[value[0]] = i
                return equations(value[-1], captures, locations, i)
            case c.GROUPREF:
                start = locations[value]
                length = simple_length(captures[value], captures)
                return And(slots[start+o] == slots[i+o] for o in range(length))
            case _:
                raise Exception(f"Expected simplified regex but got {token}")

    eqs = [Or(equations(tree, {}, {}, 0) for tree in good_simple_trees)]
    for slot in slots:
        eqs.append(ord("A") <= slot)
        eqs.append(slot <= ord("Z"))
    return And(eqs)
