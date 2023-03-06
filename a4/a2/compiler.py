from typing import List, Set, Dict, Tuple
import sys
import traceback

from cs202_support.python import *
import cs202_support.x86 as x86

# Input Language: LVar
# op ::= "add"
# Expr ::= Var(x) | Constant(n) | Prim(op, [Expr])
# Stmt ::= Assign(x, Expr) | Print(Expr)
# LVar ::= Program([Stmt])

gensym_num = 0

def gensym(x):
    """
    Constructs a new variable name guaranteed to be unique.
    :param x: A "base" variable name (e.g. "x")
    :return: A unique variable name (e.g. "x_1")
    """

    global gensym_num
    gensym_num = gensym_num + 1
    return f'{x}_{gensym_num}'


##################################################
# remove-complex-opera*
##################################################

def rco(prog: Program) -> Program:
    """
    Removes complex operands. After this pass, the arguments to operators (unary and binary
    operators, and function calls like "print") will be atomic.
    :param prog: An Lvar program
    :return: An Lvar program with atomic operator arguments.
    """

    # This should always return an atomic expression
    def rco_exp(e: Expr, bindings: Dict[str, Expr]) -> Expr:
        match e:
            case Constant(n):
                return Constant(n)
            case Var(x):
                return Var(x)
            case Prim(op, args):
                # Recursive call to rco_exp should make the argument atomic

                ### short way
                new_args = [rco_exp(a, bindings) for a in args]

                ### long way
                # new_args = []
                # for a in args:
                #    new_args.append(rco_exp(a))

                tmp = gensym('tmp')
                # bind tmp to Prim(op, new_args)
                bindings[tmp] = Prim(op, new_args)
                return Var(tmp)

    def rco_stmt(s: Stmt, bindings: Dict[str, Expr]) -> Stmt:
        match s:
            # compile the subexpression(s)
            #
            case Assign(x, e):
                new_e = rco_exp(e, bindings)
                return Assign(x, new_e)
            case Print(e):
                new_e = rco_exp(e, bindings)
                return Print(new_e)

    def rco_stmts(stmts: List[Stmt]) -> List[Stmt]:
        new_stmts = []

        for stmt in stmts:
            bindings = {}
            new_stmt = rco_stmt(stmt, bindings)

            # TODO: Turn each binding into an assignment statement
            # x -> e ====> Assign(x, e)
            for var in bindings:
                # Here we turn each binding into a statement
                new_stmts.append(Assign(var, bindings[var]))

            # TODO: add each binding assignment statement to new_stmts
            new_stmts.append(new_stmt)

        return new_stmts

    #print(Program(rco_stmts(prog.stmts)))
    return Program(rco_stmts(prog.stmts))


##################################################
# select-instructions
##################################################

# Output language: pseudo-x86
# ATM ::= Immediate(n) | Var(x) | Reg(str)
# instr_name ::= "movq" | "addq"
# Instr ::= NamedInstr(instr_name, [Atm]) | Callq(str) | Retq()
# X86 ::= X86Program(Dict[str, [Instr]])

def select_instructions(prog: Program) -> x86.X86Program:
    """
    Transforms a Lvar program into a pseudo-x86 assembly program.
    :param prog: a Lvar program
    :return: a pseudo-x86 program
    """
    def si_atm(atm):
        match atm:
            case Var(x):
                return x86.Var(x)
            case Constant(n):
                return x86.Immediate(n)

    def si_stmt(statement: Stmt) -> List[x86.Instr]:
        match statement:
            case Assign(x, Prim('add', [amt1, amt2])):
                return [x86.NamedInstr('movq', [si_atm(amt1), x86.Reg('rax')]), x86.NamedInstr('addq', [si_atm(amt2), x86.Reg('rax')]), x86.NamedInstr('movq', [x86.Reg('rax'), x86.Var(x)])]
            case Assign(x, Atm):
                return [x86.NamedInstr('movq', [si_atm(Atm)])]
            case Print(x):
                return [x86.NamedInstr('movq', [si_atm(x), x86.Reg('rdi')]), x86.Callq('print_int')]

    def si_stmts(statements: List[Stmt]):
        instructs = []
        for stmt in statements:
            instructs.extend(si_stmt(stmt))
        return instructs

    prg = {}
    prg['main'] = si_stmts(prog.stmts)

    #print(x86.X86Program(prg))
    return x86.X86Program(prg)


##################################################
# assign-homes
##################################################

def assign_homes(program: x86.X86Program) -> x86.X86Program:
    """
    Assigns homes to variables in the input program. Allocates a stack location for each
    variable in the program.
    :param program: A pseudo-x86 program.
    :return: An x86 program, annotated with the amount of stack space used
    """
    homes: Dict[str, x86.Deref] = {}

    # Should replace variable with their homes
    def ah_arg(a: x86.Arg) -> x86.Arg:
        match a:
            case x86.Immediate(i):
                return a
            case x86.Var(x):
                # replace var with deref
                # returns x86.Deref('rbp', ???)
                # if home exisits return, else allocate
                if x in homes:
                    return homes[x]
                else:
                    new_home = x86.Deref('rbp', -8 * (len(homes) + 1))
                    homes[x] = new_home
                    return new_home
            case x86.Reg(r):
                return a

    #Should call ah_arg on NamedInstr
    def ah_instr(i: x86.Instr) -> x86.Instr:
        match i:
            case x86.NamedInstr(op, args):
                new_args = [ah_arg(arg) for arg in args]
                return x86.NamedInstr(op, new_args)
            case _:
                return i

    # Call ah_instr on each instruction
    def ah_block(instrs: List[x86.Instr]) -> List[x86.Instr]:
        new_instrs = []
        for instr in instrs:
            new_instrs.append(ah_instr(instr))
        return new_instrs

    blocks = program.blocks
    new_blocks = {}
    for label, instrs in blocks.items():
        new_blocks[label] = ah_block(instrs)

    print(x86.X86Program(new_blocks))
    return x86.X86Program(new_blocks)

##################################################
# patch-instructions
##################################################

def patch_instructions(program: x86.X86Program) -> x86.X86Program:
    """
    Patches instructions with two memory location inputs, using %rax as a temporary location.
    :param program: An x86 program.
    :return: A patched x86 program.
    """

    def pi_instr(i: x86.Instr) -> List[x86.Instr]:
        match i:
            case x86.NamedInstr('movq', [x86.Deref(r1, o1), x86.Deref(r2, o2)]):
                pass
            case x86.NamedInstr('addq', [x86.Deref(r1, o1), x86.Deref(r2, o2)]):
                pass
            case _:
                return [i]

    def pi_block(instrs: List[x86.Instr]) -> List[x86.Instr]:
        new_instrs = []
        for i in instrs:
            new_instrs.extend(pi_instr(i))

        return new_instrs

    # call pi_block for each block of the program
    new_blocks = {}

    for label, instrs in program.blocks.items():
        new_blocks[label] = pi_block(instrs)

    return x86.X86Program(new_blocks)


##################################################
# prelude-and-conclusion
##################################################

def prelude_and_conclusion(program: x86.X86Program) -> x86.X86Program:
    """
    Adds the prelude and conclusion for the program.
    :param program: An x86 program.
    :return: An x86 program, with prelude and conclusion.
    """

    prelude_instructions = [x86.NamedInstr('pushq', [x86.Reg('rbp')]), x86.NamedInstr('movq', [x86.Reg('rsp'), x86.Reg('rbp')]), x86.NamedInstr('subq', [x86.Immediate(16), x86.Reg('rbp')])]
    conclusion_instructions = [x86.NamedInstr('addq', [x86.Immediate(16), x86.Reg('rsp')]), x86.NamedInstr('popq', [x86.Reg('rbp')]), x86.Retq()]
    
    main_instrs = program.blocks['main']

    #print(prelude_instructions + main_instrs + conclusion_instructions)
    program.blocks['main'] = prelude_instructions + main_instrs + conclusion_instructions
    return program


##################################################
# Compiler definition
##################################################

compiler_passes = {
    'remove complex opera*': rco,
    'select instructions': select_instructions,
    'assign homes': assign_homes,
    'patch instructions': patch_instructions,
    'prelude & conclusion': prelude_and_conclusion,
    'print x86': x86.print_x86
}


def run_compiler(s, logging=False):
    def print_prog(current_program):
        print('Concrete syntax:')
        if isinstance(current_program, x86.X86Program):
            print(x86.print_x86(current_program))
        elif isinstance(current_program, Program):
            print(print_program(current_program))

        print()
        print('Abstract syntax:')
        print(print_ast(current_program))

    current_program = parse(s)

    if logging == True:
        print()
        print('==================================================')
        print(' Input program')
        print('==================================================')
        print()
        print_prog(current_program)

    for pass_name, pass_fn in compiler_passes.items():
        current_program = pass_fn(current_program)

        if logging == True:
            print()
            print('==================================================')
            print(f' Output of pass: {pass_name}')
            print('==================================================')
            print()
            print_prog(current_program)

    return current_program


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python compiler.py <source filename>')
    else:
        file_name = sys.argv[1]
        with open(file_name) as f:
            print(f'Compiling program {file_name}...')

            try:
                program = f.read()
                x86_program = run_compiler(program, logging=True)

                with open(file_name + '.s', 'w') as output_file:
                    output_file.write(x86_program)

            except:
                print('Error during compilation! **************************************************')
                traceback.print_exception(*sys.exc_info())
