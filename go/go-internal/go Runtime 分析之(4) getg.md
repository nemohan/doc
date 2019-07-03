# getg 的实现



~~~assembly

8079010:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 8079017:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 807901d:	8d 44 24 cc          	lea    -0x34(%esp),%eax
 //###########??
 
 8079021:	3b 41 08             	cmp    0x8(%ecx),%eax
 //######## eax - g.stackguard0
 
 8079024:	0f 86 2c 0b 00 00    	jbe    8079b56 <runtime.newstack+0xb46>
 
 807902a:	81 ec b4 00 00 00    	sub    $0xb4,%esp
 
 //#############上面是做些检查  
/usr/local/lib/go/src/runtime/stack.go:962
	thisg := getg()
 8079030:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 8079037:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax
 807903d:	89 44 24 44          	mov    %eax,0x44(%esp)
 
 
 //############# getg() 的实现 
 8079030:	65 8b 05 00 00 00 00 	mov    %gs:0x0,%eax
 8079037:	8b 80 fc ff ff ff    	mov    -0x4(%eax),%eax

~~~

