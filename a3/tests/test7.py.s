  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $42, %r15
  movq %r15, %r15
  movq %r15, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
