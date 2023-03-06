  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $1, %rax
  addq $2, %rax
  movq %rax, %r15
  movq %r15, %rax
  addq $3, %rax
  movq %rax, %r13
  movq %r13, %rax
  addq $4, %rax
  movq %rax, %r12
  movq %r12, %rax
  addq $5, %rax
  movq %rax, %r14
  movq %r14, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
