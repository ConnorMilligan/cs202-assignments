  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $5, %r15
  movq %r15, %rax
  addq $37, %rax
  movq %rax, %r14
  movq %r14, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
