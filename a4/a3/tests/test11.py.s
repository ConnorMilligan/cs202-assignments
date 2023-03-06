  .globl main
main:
  pushq %rbp
  movq %rsp, %rbp
  subq $112, %rsp
  movq $5, %r15
  movq $6, %r11
  movq $7, %Deref(reg='rbp', offset=-56)
  movq $8, %Deref(reg='rbp', offset=-64)
  movq $9, %Deref(reg='rbp', offset=-48)
  movq $10, %Deref(reg='rbp', offset=-8)
  movq $11, %Deref(reg='rbp', offset=-72)
  movq $12, %r14
  movq $13, %r8
  movq $14, %Deref(reg='rbp', offset=-16)
  movq $15, %r12
  movq $16, %Deref(reg='rbp', offset=-96)
  movq $17, %Deref(reg='rbp', offset=-40)
  movq $18, %rdi
  movq %r15, %rax
  addq %r11, %rax
  movq %rax, %Deref(reg='rbp', offset=-104)
  movq %Deref(reg='rbp', offset=-104), %rax
  addq %Deref(reg='rbp', offset=-56), %rax
  movq %rax, %Deref(reg='rbp', offset=-80)
  movq %Deref(reg='rbp', offset=-80), %rax
  addq %Deref(reg='rbp', offset=-64), %rax
  movq %rax, %rbx
  movq %rbx, %rax
  addq %Deref(reg='rbp', offset=-48), %rax
  movq %rax, %rsi
  movq %rsi, %rax
  addq %Deref(reg='rbp', offset=-8), %rax
  movq %rax, %Deref(reg='rbp', offset=-88)
  movq %Deref(reg='rbp', offset=-88), %rax
  addq %Deref(reg='rbp', offset=-72), %rax
  movq %rax, %rdx
  movq %rdx, %rax
  addq %r14, %rax
  movq %rax, %Deref(reg='rbp', offset=-24)
  movq %Deref(reg='rbp', offset=-24), %rax
  addq %r8, %rax
  movq %rax, %Deref(reg='rbp', offset=-32)
  movq %Deref(reg='rbp', offset=-32), %rax
  addq %Deref(reg='rbp', offset=-16), %rax
  movq %rax, %r13
  movq %r13, %rax
  addq %r12, %rax
  movq %rax, %r9
  movq %r9, %rax
  addq %Deref(reg='rbp', offset=-96), %rax
  movq %rax, %r10
  movq %r10, %rax
  addq %Deref(reg='rbp', offset=-40), %rax
  movq %rax, %Deref(reg='rbp', offset=-112)
  movq %Deref(reg='rbp', offset=-112), %rax
  addq %rdi, %rax
  movq %rax, %rcx
  movq %rcx, %rdi
  callq print_int
  addq $112, %rsp
  popq %rbp
  retq
