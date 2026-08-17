from .parse import *

# takes a variable-length regex and generates regexes whose lengths are known
# essentially expands all *, +, ? operations as well as |
# doesn't touch [] or . or \1 etc
def get_simpler_nodes(regex_node, limit, groups):
    match regex_node:
        case SubPattern([]):
            yield regex_node

        case SubPattern(data):
            for node in get_simpler_nodes(data[0], limit, groups):
                length = simple_length(node, groups)
                rest = SubPattern(data[1:])
                for seq in get_simpler_nodes(rest, limit - length, groups.copy()):
                    full = SubPattern([node, *seq.data])
                    yield full
            return

        case Literal() | AnyChar() | Range() | CharClass():
            if limit >= 1:
                yield regex_node

        case Group(group_id, content):
            for node in get_simpler_nodes(content, limit, groups):
                groups[group_id] = node
                yield Group(group_id, node) # wrap it up

        case GroupRef(group_id):
            if simple_length(groups[group_id], groups) <= limit:
                yield regex_node

        case Branch(options):
            for option in options:
                yield from get_simpler_nodes(option, limit, groups.copy())

        case Repeat(lower, upper, subvalue):
            if type(upper) != int or upper > limit:
                upper = limit

            for i in range(lower, upper + 1):
                pattern = SubPattern(subvalue.data * i)
                yield from get_simpler_nodes(pattern, limit, groups.copy())

        case _:
            raise Exception(f"Unexpected regex type {regex_node}")

# length of a simplified node, or None if the node isn't simplified
def simple_length(regex_node, groups):
    match regex_node:
        case SubPattern(data):
            length = 0
            for part in data:
                part_length = simple_length(part, groups)
                if part_length is None:
                    return None
                else:
                    length += part_length
            return length

        case Literal() | AnyChar() | Range() | CharClass():
            return 1

        case Group(group_id, content):
            groups[group_id] = content
            return simple_length(content, groups)

        case GroupRef(group_id):
            return simple_length(groups[group_id], groups)

        case Branch() | Repeat():
            return None

        case _:
            raise Exception(f"Unexpected regex type {regex_node}")

def show_simple(regex_node, groups):
    match regex_node:
        case SubPattern(data):
            return "".join(show_simple(part, groups) for part in data)
        case Literal(char_code):
            return chr(char_code)
        case AnyChar():
            return "."
        case Range():
            return "?" # TODO
        case CharClass(items, negated):
            return "?" if not negated else "^" # TODO
        case Group(group_id, content):
            groups[group_id] = content
            return show_simple(content, groups)
        case GroupRef(group_id):
            return show_simple(groups[group_id], groups)
        case _:
            raise Exception(f"Expected simplified regex but got {regex_node}")

def get_equations(regex, slots):
    from z3 import And, Or, Not

    good_simple_nodes = []
    for node in get_simpler_nodes(parse(regex), len(slots), {}):
        if simple_length(node, {}) == len(slots):
            good_simple_nodes.append(node)

    def equations(regex_node, groups, locations, i):
        match regex_node:
            case SubPattern(data):
                conds = []
                for node in data:
                    conds.append(equations(node, groups, locations, i))
                    i += simple_length(node, groups)
                return And(conds) if conds else True

            case Literal(char_code):
                return slots[i] == char_code

            case AnyChar():
                return True

            case Range(low, high):
                return And(slots[i] >= low, slots[i] <= high)

            case CharClass(items, negated):
                eq = Or([equations(item, groups, locations, i) for item in items])
                return Not(eq) if negated else eq

            case Group(group_id, content):
                groups[group_id] = content
                locations[group_id] = i
                return equations(content, groups, locations, i)

            case GroupRef(group_id):
                start = locations[group_id]
                length = simple_length(groups[group_id], groups)
                return And([slots[start+o] == slots[i+o] for o in range(length)])

            case _:
                raise Exception(f"Expected simplified regex but got {regex_node}")

    eqs = [Or([equations(node, {}, {}, 0) for node in good_simple_nodes])]
    for slot in slots:
        eqs.append(ord("A") <= slot)
        eqs.append(slot <= ord("Z"))
    return And(eqs)
