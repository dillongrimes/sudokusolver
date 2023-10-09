from copy import deepcopy
from flask import Flask, request


app = Flask(__name__)


class IllegalValue(Exception):
    pass


class Puzzle:

    def __init__(self):
        self.output = []

    def __iter__(self):
        return iter(self.output)

    def build(self):
        # Build a "puzzle" i.e. a list of 81 cells of rows 1-9 and cols 1-9
        self.output = []
        r = 1
        c = 0
        for i in range(1, 82):
            c += 1
            self.output.append(Cell(row=r, col=c))
            if i % 9 == 0:
                r += 1
                c = 0

    def get_cell(self, row, col):
        return [x for x in self.output if x.row == int(row) and x.col == int(col)][0]

    def get_quad(self, ref):
        return [x for x in self.output if x.quad == int(ref)]

    def get_row(self, ref):
        return [x for x in self.output if x.row == int(ref)]

    def get_col(self, ref):
        return [x for x in self.output if x.col == int(ref)]

    @property
    def is_solved(self):
        # determine if the puzzle is solved
        empty_cells = len([cell for cell in self.output if cell.value == ''])
        if empty_cells:
            return False
        return True

    def reduce_pairs_triples(self, sudoku_set):
        # Iterate through all items looking for matching pairs or matching triples
        # pairs and triples mean that the remaining cells can have these possibilities removed
        set_options = [x.poss for x in sudoku_set if len(x.poss) > 1]
        set_options.sort()
        set_matches = []
        for i, x in enumerate(set_options):
            if i > 0 and len(x) == 2 and x == set_options[i - 1]:
                set_matches.append(x)
            if i > 1 and len(x) == 3 and x == set_options[i - 1] and x == set_options[i - 2]:
                set_matches.append(x)

        # Now remove any matches from the other cells
        if set_matches:
            for x in sudoku_set:
                for match in set_matches:
                    if not x.poss == match:
                        for num in match:
                            if num in x.poss:
                                x.poss.remove(num)

    def reduce_unique_possibilities(self, sudoku_set):  # sudoku_set can be a col/row/quad
        # Look through the sudoku_set for a cell with a unique possibility
        # If only one cell within a col/row/quad contains a possibility then that must be the value of the cell
        # ex. only one cell within a column has a 2 as a possibility then that cell must be a 2
        total_poss = []
        total_freq = {}
        for cell in sudoku_set:
            for x in cell.poss:
                total_poss.append(x)
        # build a dictionary to capture the frequency of each possible value
        for x in total_poss:
            if x in total_freq:
                total_freq[x] += 1
            else:
                total_freq[x] = 1
        # get each unique value (where the frequency is 1)
        unique = [x for x, cnt in total_freq.items() if cnt == 1]
        if unique:
            unique = unique[0]
            for cell in sudoku_set:
                if unique in cell.poss:
                    cell.set_value(self, unique)
                    return 1  # return 1 as an update_count value
        return 0  # default value -- no cells were set

    def update(self, key, val):
        num = int(val)  # the passed number
        row, col = key.split('_')
        curr_cell = self.get_cell(row, col)
        curr_cell.set_value(self, num)

    def brute_force(self):
        # for each of the cells that only have two possibilities,
        # try sticking in a number to find out what happens
        for cell in self.output:
            if not cell.value and len(cell.poss) == 2:
                for num_option in cell.poss:
                    dc = deepcopy(self)  # make a copy of the puzzle object
                    dcell = dc.get_cell(cell.row, cell.col)  # get the candidate cell
                    dcell.set_value(dc, num_option)  # set the value to one of the 2 possibilities
                    dc.reduce()  # test the puzzle
                    if dc.is_solved:  # we found a solution
                        cell.set_value(self, num_option)  # set the cell to the known value
                        self.reduce()  # solve the puzzle
                        return

    def reduce(self):
        update_count = 0
        for n in range(1, 10):

            self.reduce_pairs_triples(self.get_col(n))
            self.reduce_pairs_triples(self.get_row(n))
            self.reduce_pairs_triples(self.get_quad(n))

            # Now that pairs and triples have been reduced, set values when a single possibility remains
            for cell in self.output:
                if len(cell.poss) == 1:
                    update_count += 1
                    cell.set_value(self, cell.poss[0])

            update_count += self.reduce_unique_possibilities(self.get_col(n))
            update_count += self.reduce_unique_possibilities(self.get_row(n))
            update_count += self.reduce_unique_possibilities(self.get_quad(n))

        if update_count > 0:
            self.reduce()


class Cell:
    def __init__(self, row, col):
        self.quad = self.quad_map(row, col)
        self.row = row
        self.col = col
        self.poss = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.value = ''
        self.error = False

    def __str__(self):
        return f'{self.quad}_{self.row}_{self.col} = {self.value}'

    @property
    def html_key(self):
        return f'{self.row}_{self.col}'

    @property
    def html_error(self):
        if self.error:
            return 'class="error"'
        return ''

    def test_value(self, puzzle, value):
        for cell in puzzle.get_row(self.row):
            if not self == cell and value == cell.value:
                self.error = True
                raise IllegalValue

        for cell in puzzle.get_col(self.col):
            if not self == cell and value == cell.value:
                self.error = True
                raise IllegalValue

        for cell in puzzle.get_quad(self.quad):
            if not self == cell and value == cell.value:
                self.error = True
                raise IllegalValue

    def set_value(self, puzzle, value):
        try:
            self.test_value(puzzle, value)
        except IllegalValue:
            # the value isn't valid so we don't set the value
            pass
        else:
            # the test passed, update the cell and remove the possibilities from its counterparts
            self.value = value
            self.poss = []

            for cell in puzzle.get_row(self.row):
                if self.value in cell.poss:
                    cell.poss.remove(self.value)

            for cell in puzzle.get_col(self.col):
                if self.value in cell.poss:
                    cell.poss.remove(self.value)

            for cell in puzzle.get_quad(self.quad):
                if self.value in cell.poss:
                    cell.poss.remove(self.value)

    def quad_map(self, row, col):
        # map the row & col value to the correct quadrant
        if row < 4:
            if col < 4: return 1
            if 4 <= col < 7: return 2
            if 7 <= col < 10: return 3
        if 4 <= row < 7:
            if col < 4: return 4
            if 4 <= col < 7: return 5
            if 7 <= col < 10: return 6
        if 7 <= row < 10:
            if col < 4: return 7
            if 4 <= col < 7: return 8
            if 7 <= col < 10: return 9


@app.route('/', methods=['POST', 'GET'])
def sudoku():

    puzzle = Puzzle()
    puzzle.build()

    if request.method == 'POST':
        for el, val in request.form.items():
            if val:
                puzzle.update(el, val)
        puzzle.reduce()
        if not puzzle.is_solved:
            puzzle.brute_force()

    html = """
    <html>
        <head>
            <style>
                body {
                    font-family: arial, helvetica, sans-serif;
                }
                #puzzle {
                    margin: 0 auto;
                }
                .q {
                    border: 2px solid lightskyblue;
                    padding: 5px;
                    margin: 5px;
                }
                .error {
                    border-color: red;
                }
                input {
                    width: 50px;
                    height: 50px;
                    font-size: 24px;
                    text-align: center;
                    border: 1px solid lightskyblue;
                }
                .button {
                    width: 100%;
                    height: auto;
                    background-color: lightskyblue;
                    padding: 5px 0;
                    margin: 0;
                    font-weight: bold;
                    font-size: 24px;
                    cursor: pointer;
                }
                .clear {
                    display: block;
                    width: 100%;
                    height: auto;
                    background-color: lightskyblue;
                    padding: 5px 0;
                    margin: 0;
                    font-weight: bold;
                    font-size: 24px;
                    text-decoration: none;
                    color: black;
                    text-align: center;
                }
            </style>
        </head>
        <body>
        <form method="post"><table id="puzzle"><tr>
    """
    row = 1
    col = 1
    for quad in range(1, 10):
        if quad > 1:
            col += 3
        if quad in [4, 7]:
            html += "</tr><tr>"
            col = 1
            row += 3

        ul_cell = puzzle.get_cell(row, col)
        uc_cell = puzzle.get_cell(row, col+1)
        ur_cell = puzzle.get_cell(row, col+2)
        ml_cell = puzzle.get_cell(row+1, col)
        mc_cell = puzzle.get_cell(row+1, col+1)
        mr_cell = puzzle.get_cell(row+1, col+2)
        ll_cell = puzzle.get_cell(row+2, col)
        lc_cell = puzzle.get_cell(row+2, col+1)
        lr_cell = puzzle.get_cell(row+2, col+2)

        html += f"""
            <td><table id="q{quad}" class="q">
                <tr>
                    <td><input {ul_cell.html_error} name="{ul_cell.html_key}" value="{ul_cell.value}"></td>
                    <td><input {uc_cell.html_error} name="{uc_cell.html_key}" value="{uc_cell.value}"></td>
                    <td><input {ur_cell.html_error} name="{ur_cell.html_key}" value="{ur_cell.value}"></td>
                </tr>
                <tr>
                    <td><input {ml_cell.html_error} name="{ml_cell.html_key}" value="{ml_cell.value}"></td>
                    <td><input {mc_cell.html_error} name="{mc_cell.html_key}" value="{mc_cell.value}"></td>
                    <td><input {mr_cell.html_error} name="{mr_cell.html_key}" value="{mr_cell.value}"></td>
                </tr>
                <tr>
                    <td><input {ll_cell.html_error} name="{ll_cell.html_key}" value="{ll_cell.value}"></td>
                    <td><input {lc_cell.html_error} name="{lc_cell.html_key}" value="{lc_cell.value}"></td>
                    <td><input {lr_cell.html_error} name="{lr_cell.html_key}" value="{lr_cell.value}"></td>
                </tr>
            </table></td>
        """

    html += """
        </tr>
        <tr>
            <td><input class="button" type="submit" value="solve"></td>
            <td></td>
            <td><a class="clear" href="">clear</a></td>
        </tr></table></form>
    </body></html>
    """
    return html


if __name__ == '__main__':
    app.run()
