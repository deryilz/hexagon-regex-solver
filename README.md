# regex-hexagon-solver
Z3 Python code to solve https://gregable.com/p/regexp-puzzle.html

The tough part of this is turning a regex with possible captures and backreferences into a bunch of Ands, Ors, and Notes
(Z3 has its own Regex library but it can't do backreferences)

<img width="506" height="425" alt="image" src="https://github.com/user-attachments/assets/07af95a8-6905-4c99-b182-37939b19e739" />
