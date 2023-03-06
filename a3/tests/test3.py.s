  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $34, %rax
  addq $3, %rax
  movq %rax, %r15
  movq %r15, %r15
  movq %r15, %rax
  addq $5, %rax
  movq %rax, %r14
  movq %r14, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
