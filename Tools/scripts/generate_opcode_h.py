# This script generates the opcode.h header file.

import sys
import tokenize

header = """
/* Auto-generated by Tools/scripts/generate_opcode_h.py from Lib/opcode.py */
#ifndef Py_OPCODE_H
#define Py_OPCODE_H
#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>


/* Instruction opcodes for compiled code */
""".lstrip()

footer = """
#define NB_SCALE offsetof(PyNumberMethods, nb_subtract)

#define HAS_ARG(op) ((op) >= HAVE_ARGUMENT)

/* Reserve some bytecodes for internal use in the compiler.
 * The value of 240 is arbitrary. */
#define IS_ARTIFICIAL(op) ((op) > 240)

#ifdef __cplusplus
}
#endif
#endif /* !Py_OPCODE_H */
"""

DEFINE = "#define {:<31} {:>3}\n"

UINT32_MASK = (1<<32)-1

def write_int_array_from_ops(name, ops, out):
    bits = 0
    for op in ops:
        bits |= 1<<op
    out.write(f"static uint32_t {name}[8] = {{\n")
    for i in range(8):
        out.write(f"    {bits & UINT32_MASK}U,\n")
        bits >>= 32
    assert bits == 0
    out.write(f"}};\n")

def main(opcode_py, outfile='Include/opcode.h'):
    opcode = {}
    if hasattr(tokenize, 'open'):
        fp = tokenize.open(opcode_py)   # Python 3.2+
    else:
        fp = open(opcode_py)            # Python 2.7
    with fp:
        code = fp.read()
    exec(code, opcode)
    opmap = opcode['opmap']
    hasconst = opcode['hasconst']
    hasjrel = opcode['hasjrel']
    hasjabs = opcode['hasjabs']
    used = [ False ] * 256
    next_op = 1
    for name, op in opmap.items():
        used[op] = True
    with open(outfile, 'w') as fobj:
        fobj.write(header)
        for name in opcode['opname']:
            if name in opmap:
                fobj.write(DEFINE.format(name, opmap[name]))
            if name == 'POP_EXCEPT': # Special entry for HAVE_ARGUMENT
                fobj.write(DEFINE.format("HAVE_ARGUMENT", opcode["HAVE_ARGUMENT"]))

        for name in opcode['_specialized_instructions']:
            while used[next_op]:
                next_op += 1
            fobj.write(DEFINE.format(name, next_op))
            used[next_op] = True
        fobj.write(DEFINE.format('DO_TRACING', 255))
        fobj.write("#ifdef NEED_OPCODE_JUMP_TABLES\n")
        write_int_array_from_ops("_PyOpcode_RelativeJump", opcode['hasjrel'], fobj)
        write_int_array_from_ops("_PyOpcode_Jump", opcode['hasjrel'] + opcode['hasjabs'], fobj)
        fobj.write("#endif /* OPCODE_TABLES */\n")

        fobj.write("\n")
        fobj.write("#define HAS_CONST(op) (false\\")
        for op in hasconst:
            fobj.write(f"\n    || ((op) == {op}) \\")
        fobj.write("\n    )\n")

        fobj.write("\n")
        for i, slot, _ in opcode["_nb_binop_slots"]:
            fobj.write(DEFINE.format(slot.upper(), i))
        
        fobj.write("\n")
        for _, slot, name in opcode["_nb_binop_slots"]:
            fobj.write(DEFINE.format(f"{slot.upper()}_NAME", f'"{name}"'))
        
        fobj.write("\n")
        fobj.write("#define HAVE_SANE_NB_OFFSETS ( \\\n")
        for _, slot, _ in opcode["_nb_binop_slots"]:
            fobj.write(f"    {slot.upper()} * NB_SCALE == offsetof(PyNumberMethods, {slot}) && \\\n")
        fobj.write("    true)\n")

        fobj.write(footer)


    print(f"{outfile} regenerated from {opcode_py}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
