from typing import List, Set, Dict, Tuple
import sys

from cs202_support.python import *
import cs202_support.x86 as x86


##################################################
# select-instructions
##################################################

def select_instructions(program: Program) -> x86.X86Program:
    """
    Transforms a Lmin program into a pseudo-x86 assembly program.
    :param program: a Lmin program
    :return: a pseudo-x86 program
    """

    # - si_atm converts an LVar atomic into an x86 atomic
    def si_atm(atm: Expr) -> x86.Arg:
        pass

    # - si_stmt converts an LVar statement into one or more x86 instructions
    def si_stmt(stmt: Stmt) -> List[x86.Instr]:
        match stmt:
            case Assign(x, Prim('add', [atm1, atm2])):
                pass
            case Assign(x, stm1):
                pass
            case Print(atm1):
                pass

    # - si_stmts compiles a list of statements
    def si_starts(stmts: List[Stmt]) -> List[x86.Instr]:
        instrs = []

        for stmt in stmts:
            i = si_stmt(stmt)
            instrs.extend(i)

        return instrs

    pass


##################################################
# Compiler definition
##################################################

compiler_passes = {
    'select instructions': select_instructions,
    'print x86': x86.print_x86
}


def run_compiler(s, logging=False):
    current_program = parse(s)

    if logging == True:
        print()
        print('==================================================')
        print(' Input program')
        print('==================================================')
        print()
        print(print_ast(current_program))

    for pass_name, pass_fn in compiler_passes.items():
        current_program = pass_fn(current_program)

        if logging == True:
            print()
            print('==================================================')
            print(f' Output of pass: {pass_name}')
            print('==================================================')
            print()
            print(print_ast(current_program))

    return current_program


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python compiler.py <source filename>')
    else:
        file_name = sys.argv[1]
        with open(file_name) as f:
            print(f'Compiling program {file_name}...')

            try:
                input_program = f.read()
                x86_program = run_compiler(input_program, logging=True)

                with open(file_name + '.s', 'w') as output_file:
                    output_file.write(x86_program)

            except Exception as e:
                raise Exception('Error during compilation:', e)
