  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $38, %rax
  addq $4, %rax
  movq %rax, %r15
  movq %r15, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
