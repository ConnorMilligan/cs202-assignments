  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $5, %r15
  movq %r15, %r14
  movq %r14, %r15
  movq $10, %r14
  movq %r14, %rax
  addq %r15, %rax
  movq %rax, %r13
  movq %r13, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
