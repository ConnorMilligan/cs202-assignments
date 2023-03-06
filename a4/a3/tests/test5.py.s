  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $0, %rsp
  movq $5, %rax
  addq $6, %rax
  movq %rax, %r12
  movq %r12, %r12
  movq %r12, %rax
  addq $3, %rax
  movq %rax, %r13
  movq %r13, %r14
  movq %r12, %rax
  addq %r14, %rax
  movq %rax, %r15
  movq %r15, %rax
  addq $17, %rax
  movq %rax, %rbx
  movq %rbx, %rdi
  callq print_int
  addq $0, %rsp
  popq %rbp
  retq
