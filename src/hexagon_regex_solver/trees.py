from .parse import *

# takes a variable-length regex and generates regexes whose lengths are known
# essentially removes all *, +, ? operations as well as some |
# doesn't touch [] or . or \1 etc
def get_simpler_nodes(regex_node, limit, groups):
    match regex_node:
        case SubPattern([]):
            yield regex_node

        case SubPattern(parts):
            for node in get_simpler_nodes(parts[0], limit, groups):
                length = simple_length(node, groups)
                rest = SubPattern(parts[1:])
                for seq in get_simpler_nodes(rest, limit - length, groups):
                    full = SubPattern([node, *seq.parts])
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
            sized_options = {}
            for option in options:
                length = simple_length(option, groups)
                if length is None:
                    yield from get_simpler_nodes(option, limit, groups)
                elif length <= limit:
                    if length not in sized_options:
                        sized_options[length] = []
                    sized_options[length].append(option)
            for value in sized_options.values():
                yield value[0] if len(value) == 1 else Branch(value)

        case Repeat(lower, upper, subvalue):
            length = simple_length(subvalue, groups)
            if lower == upper and length is not None:
                if length <= limit:
                    yield regex_node
                return
            if upper is None or upper > limit:
                upper = limit
            for i in range(lower, upper + 1):
                pattern = SubPattern([subvalue] * i)
                yield from get_simpler_nodes(pattern, limit, groups)

        case _:
            raise Exception(f"Unexpected Regex {regex_node}")

# fixed length of a regex if it has one
def simple_length(regex_node, groups):
    match regex_node:
        case SubPattern(parts):
            length = 0
            for part in parts:
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

        case Branch(options):
            size = None
            for option in options:
                length = simple_length(option, groups)
                if size == None:
                    size = length
                elif length != size:
                    return
            return size

        case Repeat(upper, lower, subvalue):
            if upper != lower:
                return None
            length = simple_length(subvalue, groups)
            if length is None:
                return None
            return lower * length

        case _:
            raise Exception(f"Unexpected Regex {regex_node}")

def get_equations(regex, slots):
    from z3 import And, Or, Not

    good_simple_nodes = []
    for node in get_simpler_nodes(parse(regex), len(slots), {}):
        if simple_length(node, {}) == len(slots):
            good_simple_nodes.append(node)

    def equations(regex_node, groups, locations, i):
        match regex_node:
            case SubPattern(parts):
                conds = []
                for part in parts:
                    conds.append(equations(part, groups, locations, i))
                    i += simple_length(part, groups)
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

            case Branch(options):
                return Or([equations(option, groups, locations, i) for option in options])

            # at this point we know (lower == upper) and that subvalue has a length
            case Repeat(lower, upper, subvalue):
                l = simple_length(subvalue, groups)
                return And([equations(subvalue, groups, locations, i+o*l) for o in range(lower)])

            case _:
                raise Exception(f"Unexpected Regex {regex_node}")

    return Or([equations(node, {}, {}, 0) for node in good_simple_nodes])
