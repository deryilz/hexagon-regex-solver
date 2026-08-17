from z3 import *

from . import trees, hexagon, parse

regexes = {
    "a": [
        r"(ND|ET|IN)[^X]*",
        r"[CHMNOR]*I[CHMNOR]*",
        r"P+(..)\1.*",
        r"(E|CR|MN)*",
        r"([^MC]|MM|CC)*",
        r"[AM]*CM(RC)*R?",
        r".*",
        r".*PRR.*DDC.*",
        r"(HHX|[^HX])*",
        r"([^EMC]|EM)*",
        r".*OXR.*",
        r".*LR.*RL.*",
        r".*SE.*UE.*"
    ],
"b": [
        r"(S|MM|HHH)*",
        r"[^M]*M[^M]*",
        r"(RX|[^R])*",
        r"[CEIMU]*OH[AEMOR]*",
        r".*(.)C\1X\1.*",
        r"[^C]*MMM[^C]*",
        r".*(IN|SE|HI)",
        r".*(.)(.)(.)(.)\4\3\2\1.*",
        r".*XHCR.*X.*",
        r".*DD.*CCM.*",
        r".*XEXM*",
        r"[CR]*",
        r".*G.*V.*H.*",
    ],
    "c": [
        r".*H.*H.*",
        r"(DI|NS|TH|OM)*",
        r"F.*[AO].*[AO].*",
        r"(O|RHH|MM)*",
        r".*",
        r"C*MC(CCC|MM)*",
        r"[^C]*[^R]*III.*",
        r"(...?)\1*",
        r"([^X]|XCC)*",
        r"(RR|HHH)*.?",
        r"N.*X.X.X.*E",
        r"R*D*M*",
        r".(C|HH)*"
    ],
}

def main():
    s = Solver()

    def default(r, c):
        var = Int(f"{r}-{c}")
        s.add(ord("A") <= var)
        s.add(var <= ord("Z"))
        return var

    puzzle = hexagon.HexCrossword(default)

    for axis in regexes.keys():
        for i, regex in enumerate(regexes[axis]):
            variables = puzzle.get_line(axis, i)

            def count_nodes(expr):
                if not z3.is_expr(expr) or expr.num_args() == 0:
                    return 0
                return 1 + sum(count_nodes(child) for child in expr.children())

            eq = simplify(trees.get_equations(regex, variables))
            print(f"Equation for {axis}{i} {regex} has size {count_nodes(eq)}")

            s.add(eq)

    if s.check() == sat:
        print("Solved!")

        model = s.model()

        # c is the originally horizontal axis
        print()
        for i, regex in enumerate(regexes["c"]):
            variables = puzzle.get_line(axis, i)
            padding = " " * (20 - puzzle.row_len(i))
            line = " ".join(chr(model[v].as_long()) for v in variables)
            print(padding + line)
        print()

    else:
        print("Couldn't solve...")
