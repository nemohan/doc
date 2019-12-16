# go runtime emptyfunc



~~~assembly

080877c0 <runtime.emptyfunc>:
runtime.emptyfunc():
/usr/local/lib/go/src/runtime/asm_386.s:865

TEXT runtime·emptyfunc(SB),0,$0-0
 80877c0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx				
 // ###    gs:0x0里面的内容也是个地址
 
 80877c7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx        
 //######## ecx 里面的是g0的地址
 
 80877cd:	3b 61 08             	cmp    0x8(%ecx),%esp
 // ##### 如果当前的esp指向的栈地址 小于 0x8(%ecx) 的某个值， 0x8(%ecx)即
 //###### g0.stackguard0 也就是栈顶，是个低地址，小于现在的esp
 // ##### 也就是如果 esp < g0.stackguard0 则跳转。 
 
 80877d0:	76 01                	jbe    80877d3 <runtime.emptyfunc+0x13>
/usr/local/lib/go/src/runtime/asm_386.s:866
	RET
 80877d2:	c3                   	ret 
 
 
 
/usr/local/lib/go/src/runtime/asm_386.s:865
TEXT runtime·emptyfunc(SB),0,$0-0
 80877d3:	e8 58 eb ff ff       	call   8086330 <runtime.morestack_noctxt>
 80877d8:	eb e6                	jmp    80877c0 <runtime.emptyfunc>
 80877da:	cc                   	int3   
 80877db:	cc                   	int3   
 80877dc:	cc                   	int3   
 80877dd:	cc                   	int3   
 80877de:	cc                   	int3   
 80877df:	cc                   	int3   
 
 //===================================================
 
08086330 <runtime.morestack_noctxt>:
runtime.morestack_noctxt():
/usr/local/lib/go/src/runtime/asm_386.s:415

TEXT runtime·morestack_noctxt(SB),NOSPLIT,$0-0
	MOVL	$0, DX
 8086330:	31 d2                	xor    %edx,%edx
/usr/local/lib/go/src/runtime/asm_386.s:416
	JMP runtime·morestack(SB)
 8086332:	e9 69 ff ff ff       	jmp    80862a0 <runtime.morestack>
 
	见第三篇

~~~

