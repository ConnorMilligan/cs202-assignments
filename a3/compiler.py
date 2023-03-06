from collections import defaultdict

from typing import List, Set, Dict, Tuple, DefaultDict
import sys
import itertools
import traceback

from cs202_support.python import *
import cs202_support.x86 as x86
import constants
from interference_graph import InterferenceGraph

gensym_num = 0
global_logging = False


def log(label, value):
    if global_logging:
        print()
        print(f'--------------------------------------------------')
        print(f'Logging: {label}')
        print(value)
        print(f'--------------------------------------------------')


def log_ast(label, value):
    log(label, print_ast(value))


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

    def rco_stmt(stmt: Stmt, bindings: Dict[str, Expr]) -> Stmt:
        match stmt:
            case Assign(x, e1):
                new_e1 = rco_exp(e1, bindings)
                return Assign(x, new_e1)
            case Print(e1):
                new_e1 = rco_exp(e1, bindings)
                return Print(new_e1)
            case _:
                raise Exception('rco_stmt', stmt)

    def rco_stmts(stmts: List[Stmt]) -> List[Stmt]:
        new_stmts = []

        for stmt in stmts:
            bindings = {}
            # (1) compile the statement
            new_stmt = rco_stmt(stmt, bindings)
            # (2) add the new bindings created by rco_exp
            new_stmts.extend([Assign(x, e) for x, e in bindings.items()])
            # (3) add the compiled statement itself
            new_stmts.append(new_stmt)

        return new_stmts

    def rco_exp(e: Expr, bindings: Dict[str, Expr]) -> Expr:
        match e:
            case Var(x):
                return Var(x)
            case Constant(i):
                return Constant(i)
            case Prim(op, args):
                new_args = [rco_exp(e, bindings) for e in args]
                new_e = Prim(op, new_args)
                new_v = gensym('tmp')
                bindings[new_v] = new_e
                return Var(new_v)
            case _:
                raise Exception('rco_exp', e)

    return Program(rco_stmts(prog.stmts))


##################################################
# select-instructions
##################################################

# Output language: pseudo-x86
# Arg ::= Immediate(n) | Var(x) | Reg(str)
# instr_name ::= "movq" | "addq"
# Instr ::= NamedInstr(instr_name, [Arg]) | Callq(str) | Retq()
# X86 ::= X86Program(Dict[str, [Instr]])

def select_instructions(prog: Program) -> x86.X86Program:
    """
    Transforms a Lvar program into a pseudo-x86 assembly program.
    :param prog: a Lvar program
    :return: a pseudo-x86 program
    """

    def si_atm(a: Expr) -> x86.Arg:
        match a:
            case Constant(i):
                return x86.Immediate(i)
            case Var(x):
                return x86.Var(x)
            case _:
                raise Exception('si_atm', a)

    def si_stmts(stmts: List[Stmt]) -> List[x86.Instr]:
        instrs = []

        for stmt in stmts:
            instrs.extend(si_stmt(stmt))

        return instrs

    def si_stmt(stmt: Stmt) -> List[x86.Instr]:
        match stmt:
            case Assign(x, Prim('add', [atm1, atm2])):
                return [x86.NamedInstr('movq', [si_atm(atm1), x86.Reg('rax')]),
                        x86.NamedInstr('addq', [si_atm(atm2), x86.Reg('rax')]),
                        x86.NamedInstr('movq', [x86.Reg('rax'), x86.Var(x)])]
            case Assign(x, atm1):
                return [x86.NamedInstr('movq', [si_atm(atm1), x86.Var(x)])]
            case Print(atm1):
                return [x86.NamedInstr('movq', [si_atm(atm1), x86.Reg('rdi')]),
                        x86.Callq('print_int')]
            case _:
                raise Exception('si_stmt', stmt)

    instrs: List[x86.Instr] = si_stmts(prog.stmts)
    return x86.X86Program({'main': instrs})


##################################################
# allocate-registers
##################################################

Color = int
Coloring = Dict[x86.Var, Color]
Saturation = Set[Color]


# Input and Output language: pseudo-x86
# Arg ::= Immediate(n) | Var(x) | Reg(str)
# instr_name ::= "movq" | "addq"
# Instr ::= NamedInstr(instr_name, [Arg]) | Callq(str) | Retq()
# X86 ::= X86Program(Dict[str, [Instr]])

def allocate_registers(program: x86.X86Program) -> x86.X86Program:
    """
    Assigns homes to variables in the input program. Allocates registers and
    stack locations as needed, based on a graph-coloring register allocation
    algorithm.
    :param program: A pseudo-x86 program.
    :return: An x86 program, annotated with the number of bytes needed in stack
    locations.
    """

    homes: Dict[x86.Var, x86.Arg] = {}
    # --------------------------------------------------
    # utilities
    # --------------------------------------------------
    all_vars = set()

    def vars_of(a: x86.Arg) -> Set[x86.Var]:
        match a:
            case x86.Var(x):
                all_vars.add(a)
                return {x86.Var(x)}
            case _:
                return set()

    def reads_of(i: x86.Instr) -> Set[x86.Var]:
        # returns the set of variables read by instruction i
        match i:
            case x86.NamedInstr('addq', [a1, a2]):
                # addq reads both args, so return the set of vars in a1 and a2
                return vars_of(a1).union(vars_of(a2))
            case x86.NamedInstr('movq', [a1, a2]):
                # movq reads only a2, so return the set of vars in a2
                return vars_of(a2)
            case _:
                return set()
            # TODO: other cases go here

    def writes_of(i: x86.Instr) -> Set[x86.Var]:
        # returns the set of variables written by instruction i
        match i:
            case x86.NamedInstr('addq', [a1, a2]):
                # addq writes only to a1, so return the set of vars in a1
                return vars_of(a1)
            case x86.NamedInstr('movq', [a1, a2]):
                # movq writes only to a1, so return the set of vars in a1
                return vars_of(a1)
            case _:
                return set()


    # --------------------------------------------------
    # liveness analysis
    # --------------------------------------------------
    def ul_instr(i: x86.Instr, live_after: Set[x86.Var]) -> Set[x86.Var]:
        # given instruction k+1 and the live-after set for instruction k+1,
        # produce the live-after set for instruction k
        # 𝐿𝑎𝑓𝑡𝑒𝑟(𝑘)=(𝐿𝑎𝑓𝑡𝑒𝑟(𝑘+1)−𝑊(𝑘+1))∪𝑅(𝑘+1)
        return live_after.difference(writes_of(i)).union(reads_of(i))

    def ul_block(instrs: List[x86.Instr]) -> List[Set[x86.Var]]:
        # start with empty list of live-after sets
        live_after_sets = []
        # start with empty current live-after set
        current_live_after = set()
        # loop over instructions in reverse order
        for i in reversed(instrs):
            # TODO: add it to the list
            live_after_sets.append(current_live_after)

            # TODO: call ul_instr to get the next live-after set
            current_live_after = ul_instr(i, current_live_after)

        # at the end, reverse the list of live-after sets and return it
        return list(reversed(live_after_sets))

    # --------------------------------------------------
    # interference graph
    # --------------------------------------------------
    def bi_instr(i: x86.Instr, live_after: Set[x86.Var], graph: InterferenceGraph):
        writes = writes_of(i)
        for v1 in writes:
            for v2 in live_after:
                if v1 != v2:
                    graph.add_edge(v1, v2)

    def bi_block(instrs: List[x86.Instr], live_afters: List[Set[x86.Var]], graph: InterferenceGraph):
        for i, (instr, live_after) in enumerate(zip(instrs, live_afters)):
            bi_instr(instr, live_after, graph)

    # --------------------------------------------------
    # graph coloring
    # --------------------------------------------------
    def color_graph(local_vars: Set[x86.Var], interference_graph: InterferenceGraph) -> Coloring:
        saturation_sets: Dict[x86.Var, Saturation] = {}
        for v in local_vars:
            saturation_sets[v] = set()

        coloring = {}
        vars_to_color = local_vars.copy()
        # loop unntil there are no more vars to color
        while len(vars_to_color) > 0:
            # Find the variable with the largest saturation set
            max_saturation = -1
            var_to_color = None
            for v in vars_to_color:
                saturation = saturation_sets[v]
                if len(saturation) > max_saturation:
                    max_saturation = len(saturation)
                    var_to_color = v

            # Pick the lowest color that is not in the saturation set
            x_color = 0
            while x_color in saturation_sets[var_to_color]:
                x_color += 1
            coloring[var_to_color] = x_color

            # Update the saturation sets of neighboring variables
            for y in interference_graph.neighbors(var_to_color):
                if isinstance(y, x86.Var):
                    saturation_sets[y].add(x_color)

            # Remove var_to_color from vars_to_color
            vars_to_color.remove(var_to_color)
        return coloring

    # --------------------------------------------------
    # assigning homes
    # --------------------------------------------------
    def ah_arg(a: x86.Arg) -> x86.Arg:
        match a:
            case x86.Immediate(i):
                return a
            case x86.Reg(r):
                return a
            case x86.Var(x):
                # we will *always* know the home for x
                # the whole point of register allocation was to pre-populate `homes`
                # with a home for every single variable
                # you can delete the else case
                return homes[x86.Var(x)]

            case _:
                raise Exception('ah_arg', a)

    # stays the same
    def ah_instr(e: x86.Instr) -> x86.Instr:
        match e:
            case x86.NamedInstr(i, args):
                return x86.NamedInstr(i, [ah_arg(a) for a in args])
            case _:
                if isinstance(e, (x86.Callq, x86.Retq, x86.Jmp)):
                    return e
                else:
                    raise Exception('ah_instr', e)

    # stays the same
    def ah_block(instrs: List[x86.Instr]) -> List[x86.Instr]:
        return [ah_instr(i) for i in instrs]

    # --------------------------------------------------
    # main body of the pass
    # --------------------------------------------------

    # Step 1: Perform liveness analysis
    blocks = program.blocks
    main_instrs = blocks['main']
    # TODO: run the liveness analysis
    live_after_sets = ul_block(main_instrs)  # call ul_block
    log_ast('live-after sets', live_after_sets)

    # Step 2: Build the interference graph
    interference_graph = InterferenceGraph()

    # TODO: build the interference graph
    # call bi_block to build the interference graph
    bi_block(main_instrs, live_after_sets, interference_graph)

    log_ast('interference graph', interference_graph)

    # Step 3: Color the graph
    coloring = color_graph(all_vars, interference_graph)
    log('coloring', coloring)

    # Defines the set of registers to use
    available_registers = constants.caller_saved_registers + constants.callee_saved_registers

    # Step 4: map variables to homes
    color_map = {}
    stack_locations_used = 0

    # Step 4.1: Map colors to locations (the "color map")
    # TODO: step 4.1
    # for each color in `coloring`, add a mapping in `color_map` to a location
    for color in set(coloring.values()):
        # start with registers, use stack locations when you run out
        if color < len(available_registers):
            # this is messy, do not look :)
            color_map[color] = available_registers[len(available_registers) - 1 - color]
        else:
            # allocate stack location
            stack_location = x86.Deref('rbp', -8 * (stack_locations_used + 1))
            stack_locations_used += 1
            color_map[color] = stack_location

    # Step 4.2: Compose the "coloring" with the "color map" to get "homes"
    # TODO: step 4.2
    for v in all_vars:
        homes[v] = x86.Reg(color_map[coloring[v]])
    log('homes', homes)
    # Step 5: replace variables with their homes
    # TODO: step 5
    blocks = program.blocks
    new_blocks = {label: ah_block(block) for label, block in blocks.items()}
    stack_space = 8 * stack_locations_used # something based on stack_locations_used
    return x86.X86Program(new_blocks, stack_space=stack_space)


##################################################
# patch-instructions
##################################################

def patch_instructions(program: x86.X86Program) -> x86.X86Program:
    """
    Patches instructions with two memory location inputs, using %rax as a temporary location.
    :param program: An x86 program.
    :return: A patched x86 program.
    """

    def pi_instr(e: x86.Instr) -> List[x86.Instr]:
        match e:
            case x86.NamedInstr('movq', [x86.Deref(_, _), x86.Deref(_, _)]):
                return [x86.NamedInstr('movq', [e.args[0], x86.Reg('rax')]),
                        x86.NamedInstr('movq', [x86.Reg('rax'), e.args[1]])]
            case x86.NamedInstr('addq', [x86.Deref(_, _), x86.Deref(_, _)]):
                return [x86.NamedInstr('movq', [e.args[0], x86.Reg('rax')]),
                        x86.NamedInstr('addq', [x86.Reg('rax'), e.args[1]])]
            case _:
                if isinstance(e, (x86.Callq, x86.Retq, x86.Jmp, x86.NamedInstr)):
                    return [e]
                else:
                    raise Exception('pi_instr', e)

    def pi_block(instrs: List[x86.Instr]) -> List[x86.Instr]:
        new_instrs = [pi_instr(i) for i in instrs]
        flattened = [val for sublist in new_instrs for val in sublist]
        return flattened

    blocks = program.blocks
    new_blocks = {label: pi_block(block) for label, block in blocks.items()}
    return x86.X86Program(new_blocks, stack_space=program.stack_space)


##################################################
# prelude-and-conclusion
##################################################

def prelude_and_conclusion(program: x86.X86Program) -> x86.X86Program:
    """
    Adds the prelude and conclusion for the program.
    :param program: An x86 program.
    :return: An x86 program, with prelude and conclusion.
    """

    prelude = [x86.NamedInstr('pushq', [x86.Reg('rbp')]),
               x86.NamedInstr('movq', [x86.Reg('rsp'), x86.Reg('rbp')]),
               x86.NamedInstr('subq', [x86.Immediate(program.stack_space),
                                       x86.Reg('rsp')])]

    conclusion = [x86.NamedInstr('addq', [x86.Immediate(program.stack_space),
                                          x86.Reg('rsp')]),
                  x86.NamedInstr('popq', [x86.Reg('rbp')]),
                  x86.Retq()]

    new_blocks = {'main': prelude + program.blocks['main'] + conclusion}
    return x86.X86Program(new_blocks, stack_space=program.stack_space)


##################################################
# Compiler definition
##################################################

compiler_passes = {
    'remove complex opera*': rco,
    'select instructions': select_instructions,
    'allocate registers': allocate_registers,
    'patch instructions': patch_instructions,
    'prelude & conclusion': prelude_and_conclusion,
    'print x86': x86.print_x86
}


def run_compiler(s, logging=False):
    global global_logging
    global_logging = logging

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
