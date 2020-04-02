# schedinit  续

~~~assembly
// ======================== tracebackinit===================

0807e1d0 <runtime.tracebackinit>:
runtime.tracebackinit():
/usr/local/lib/go/src/runtime/traceback.go:62
	gogoPC uintptr

	externalthreadhandlerp uintptr // initialized elsewhere
)

func tracebackinit() {
 807e1d0:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 807e1d7:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 807e1dd:	8d 44 24 f8          	lea    -0x8(%esp),%eax
 807e1e1:	3b 41 08             	cmp    0x8(%ecx),%eax
 807e1e4:	0f 86 59 02 00 00    	jbe    807e443 <runtime.tracebackinit+0x273>
 807e1ea:	81 ec 88 00 00 00    	sub    $0x88,%esp
/usr/local/lib/go/src/runtime/traceback.go:67
	// Go variable initialization happens late during runtime startup.
	// Instead of initializing the variables above in the declarations,
	// schedinit calls this function so that the variables are
	// initialized and available earlier in the startup sequence.
	goexitPC = funcPC(goexit)
 807e1f0:	8d 05 60 29 09 08    	lea    0x8092960,%eax
 807e1f6:	89 44 24 28          	mov    %eax,0x28(%esp)
 //############# 这部分作何解释 上面两行???????????
 
 807e1fa:	8d 05 34 25 0a 08    	lea    0x80a2534,%eax
 807e200:	89 44 24 2c          	mov    %eax,0x2c(%esp)
 
 807e204:	8d 44 24 28          	lea    0x28(%esp),%eax
 807e208:	83 c0 04             	add    $0x4,%eax
 //############ eax =  esp + 0x2c 
 
 807e20b:	8b 00                	mov    (%eax),%eax
 // ########### eax = 0x80a2534
 
 807e20d:	8b 00                	mov    (%eax),%eax
 //############# eax = *(0x80a2534)
 807e20f:	89 05 b4 8d 0d 08    	mov    %eax,0x80d8db4
 //############ 0x80d8db4 为 全局变量goexitPC 的地址
 
 
/usr/local/lib/go/src/runtime/traceback.go:68
	jmpdeferPC = funcPC(jmpdefer)
 807e215:	8d 05 e0 3f 09 08    	lea    0x8093fe0,%eax
 807e21b:	89 44 24 58          	mov    %eax,0x58(%esp)
 
 807e21f:	8d 05 48 25 0a 08    	lea    0x80a2548,%eax
 807e225:	89 44 24 5c          	mov    %eax,0x5c(%esp)
 
 
 807e229:	8d 44 24 58          	lea    0x58(%esp),%eax
 807e22d:	83 c0 04             	add    $0x4,%eax
 807e230:	8b 00                	mov    (%eax),%eax
 807e232:	8b 00                	mov    (%eax),%eax
 807e234:	89 05 c4 8d 0d 08    	mov    %eax,0x80d8dc4
/usr/local/lib/go/src/runtime/traceback.go:69


	mcallPC = funcPC(mcall)
 807e23a:	8d 05 20 29 09 08    	lea    0x8092920,%eax
 807e240:	89 44 24 30          	mov    %eax,0x30(%esp)
 807e244:	8d 05 64 25 0a 08    	lea    0x80a2564,%eax
 807e24a:	89 44 24 34          	mov    %eax,0x34(%esp)
 807e24e:	8d 44 24 30          	lea    0x30(%esp),%eax
 807e252:	83 c0 04             	add    $0x4,%eax
 807e255:	8b 00                	mov    (%eax),%eax
 807e257:	8b 00                	mov    (%eax),%eax
 807e259:	89 05 c8 8d 0d 08    	mov    %eax,0x80d8dc8
/usr/local/lib/go/src/runtime/traceback.go:70
	morestackPC = funcPC(morestack)
 807e25f:	8d 05 80 25 09 08    	lea    0x8092580,%eax
 807e265:	89 44 24 08          	mov    %eax,0x8(%esp)
 807e269:	8d 0d a0 25 0a 08    	lea    0x80a25a0,%ecx
 807e26f:	89 4c 24 0c          	mov    %ecx,0xc(%esp)
 807e273:	8d 4c 24 08          	lea    0x8(%esp),%ecx
 807e277:	83 c1 04             	add    $0x4,%ecx
 807e27a:	8b 09                	mov    (%ecx),%ecx
 807e27c:	8b 09                	mov    (%ecx),%ecx
 807e27e:	89 0d cc 8d 0d 08    	mov    %ecx,0x80d8dcc
/usr/local/lib/go/src/runtime/traceback.go:71
	mstartPC = funcPC(mstart)
 807e284:	89 44 24 68          	mov    %eax,0x68(%esp)
 807e288:	8d 0d a8 25 0a 08    	lea    0x80a25a8,%ecx
 807e28e:	89 4c 24 6c          	mov    %ecx,0x6c(%esp)
 807e292:	8d 4c 24 68          	lea    0x68(%esp),%ecx
 807e296:	83 c1 04             	add    $0x4,%ecx
 807e299:	8b 09                	mov    (%ecx),%ecx
 807e29b:	8b 09                	mov    (%ecx),%ecx
 807e29d:	89 0d d0 8d 0d 08    	mov    %ecx,0x80d8dd0
/usr/local/lib/go/src/runtime/traceback.go:72
	rt0_goPC = funcPC(rt0_go)
 807e2a3:	89 44 24 50          	mov    %eax,0x50(%esp)
 807e2a7:	8d 0d d4 25 0a 08    	lea    0x80a25d4,%ecx
 807e2ad:	89 4c 24 54          	mov    %ecx,0x54(%esp)
 807e2b1:	8d 4c 24 50          	lea    0x50(%esp),%ecx
 807e2b5:	83 c1 04             	add    $0x4,%ecx
 807e2b8:	8b 09                	mov    (%ecx),%ecx
 807e2ba:	8b 09                	mov    (%ecx),%ecx
 807e2bc:	89 0d f4 8d 0d 08    	mov    %ecx,0x80d8df4
/usr/local/lib/go/src/runtime/traceback.go:73
	sigpanicPC = funcPC(sigpanic)
 807e2c2:	89 44 24 70          	mov    %eax,0x70(%esp)
 807e2c6:	8d 0d e4 25 0a 08    	lea    0x80a25e4,%ecx
 807e2cc:	89 4c 24 74          	mov    %ecx,0x74(%esp)
 807e2d0:	8d 4c 24 70          	lea    0x70(%esp),%ecx
 807e2d4:	83 c1 04             	add    $0x4,%ecx
 807e2d7:	8b 09                	mov    (%ecx),%ecx
 807e2d9:	8b 09                	mov    (%ecx),%ecx
 807e2db:	89 0d fc 8d 0d 08    	mov    %ecx,0x80d8dfc
/usr/local/lib/go/src/runtime/traceback.go:74
	runfinqPC = funcPC(runfinq)
 807e2e1:	89 04 24             	mov    %eax,(%esp)
 807e2e4:	8d 0d dc 25 0a 08    	lea    0x80a25dc,%ecx
 807e2ea:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 807e2ee:	8d 0c 24             	lea    (%esp),%ecx
 807e2f1:	83 c1 04             	add    $0x4,%ecx
 807e2f4:	8b 09                	mov    (%ecx),%ecx
 807e2f6:	8b 09                	mov    (%ecx),%ecx
 807e2f8:	89 0d f8 8d 0d 08    	mov    %ecx,0x80d8df8
/usr/local/lib/go/src/runtime/traceback.go:75
	bgsweepPC = funcPC(bgsweep)
 807e2fe:	8d 0d a0 28 09 08    	lea    0x80928a0,%ecx
 807e304:	89 4c 24 78          	mov    %ecx,0x78(%esp)
 807e308:	8d 0d b4 24 0a 08    	lea    0x80a24b4,%ecx
 807e30e:	89 4c 24 7c          	mov    %ecx,0x7c(%esp)
 807e312:	8d 4c 24 78          	lea    0x78(%esp),%ecx
 807e316:	83 c1 04             	add    $0x4,%ecx
 807e319:	8b 09                	mov    (%ecx),%ecx
 807e31b:	8b 09                	mov    (%ecx),%ecx
 807e31d:	89 0d 60 8d 0d 08    	mov    %ecx,0x80d8d60
/usr/local/lib/go/src/runtime/traceback.go:76
	forcegchelperPC = funcPC(forcegchelper)
 807e323:	89 44 24 60          	mov    %eax,0x60(%esp)
 807e327:	8d 0d 10 25 0a 08    	lea    0x80a2510,%ecx
 807e32d:	89 4c 24 64          	mov    %ecx,0x64(%esp)
 807e331:	8d 4c 24 60          	lea    0x60(%esp),%ecx
 807e335:	83 c1 04             	add    $0x4,%ecx
 807e338:	8b 09                	mov    (%ecx),%ecx
 807e33a:	8b 09                	mov    (%ecx),%ecx
 807e33c:	89 0d 9c 8d 0d 08    	mov    %ecx,0x80d8d9c
/usr/local/lib/go/src/runtime/traceback.go:77
	timerprocPC = funcPC(timerproc)
 807e342:	89 44 24 38          	mov    %eax,0x38(%esp)
 807e346:	8d 0d 14 26 0a 08    	lea    0x80a2614,%ecx
 807e34c:	89 4c 24 3c          	mov    %ecx,0x3c(%esp)
 807e350:	8d 4c 24 38          	lea    0x38(%esp),%ecx
 807e354:	83 c1 04             	add    $0x4,%ecx
 807e357:	8b 09                	mov    (%ecx),%ecx
 807e359:	8b 09                	mov    (%ecx),%ecx
 807e35b:	89 0d 10 8e 0d 08    	mov    %ecx,0x80d8e10
/usr/local/lib/go/src/runtime/traceback.go:78
	gcBgMarkWorkerPC = funcPC(gcBgMarkWorker)
 807e361:	8d 0d 60 28 09 08    	lea    0x8092860,%ecx
 807e367:	89 4c 24 10          	mov    %ecx,0x10(%esp)
 807e36b:	8d 0d 1c 25 0a 08    	lea    0x80a251c,%ecx
 807e371:	89 4c 24 14          	mov    %ecx,0x14(%esp)
 807e375:	8d 4c 24 10          	lea    0x10(%esp),%ecx
 807e379:	83 c1 04             	add    $0x4,%ecx
 807e37c:	8b 09                	mov    (%ecx),%ecx
 807e37e:	8b 09                	mov    (%ecx),%ecx
 807e380:	89 0d a4 8d 0d 08    	mov    %ecx,0x80d8da4
/usr/local/lib/go/src/runtime/traceback.go:79
	systemstack_switchPC = funcPC(systemstack_switch)
 807e386:	89 84 24 80 00 00 00 	mov    %eax,0x80(%esp)
 807e38d:	8d 0d 0c 26 0a 08    	lea    0x80a260c,%ecx
 807e393:	89 8c 24 84 00 00 00 	mov    %ecx,0x84(%esp)
 807e39a:	8d 8c 24 80 00 00 00 	lea    0x80(%esp),%ecx
 807e3a1:	83 c1 04             	add    $0x4,%ecx
 807e3a4:	8b 09                	mov    (%ecx),%ecx
 807e3a6:	8b 09                	mov    (%ecx),%ecx
 807e3a8:	89 0d 0c 8e 0d 08    	mov    %ecx,0x80d8e0c
/usr/local/lib/go/src/runtime/traceback.go:80
	systemstackPC = funcPC(systemstack)
 807e3ae:	8d 0d e0 28 09 08    	lea    0x80928e0,%ecx
 807e3b4:	89 4c 24 18          	mov    %ecx,0x18(%esp)
 807e3b8:	8d 0d 10 26 0a 08    	lea    0x80a2610,%ecx
 807e3be:	89 4c 24 1c          	mov    %ecx,0x1c(%esp)
 807e3c2:	8d 4c 24 18          	lea    0x18(%esp),%ecx
 807e3c6:	83 c1 04             	add    $0x4,%ecx
 807e3c9:	8b 09                	mov    (%ecx),%ecx
 807e3cb:	8b 09                	mov    (%ecx),%ecx
 807e3cd:	89 0d 08 8e 0d 08    	mov    %ecx,0x80d8e08
/usr/local/lib/go/src/runtime/traceback.go:81
	stackBarrierPC = funcPC(stackBarrier)
 807e3d3:	89 44 24 20          	mov    %eax,0x20(%esp)
 807e3d7:	8d 05 f0 25 0a 08    	lea    0x80a25f0,%eax
 807e3dd:	89 44 24 24          	mov    %eax,0x24(%esp)
 807e3e1:	8d 44 24 20          	lea    0x20(%esp),%eax
 807e3e5:	83 c0 04             	add    $0x4,%eax
 807e3e8:	8b 00                	mov    (%eax),%eax
 807e3ea:	8b 00                	mov    (%eax),%eax
 807e3ec:	89 05 00 8e 0d 08    	mov    %eax,0x80d8e00
/usr/local/lib/go/src/runtime/traceback.go:82
	cgocallback_gofuncPC = funcPC(cgocallback_gofunc)
 807e3f2:	8d 05 80 4d 09 08    	lea    0x8094d80,%eax
 807e3f8:	89 44 24 40          	mov    %eax,0x40(%esp)
 807e3fc:	8d 05 d8 24 0a 08    	lea    0x80a24d8,%eax
 807e402:	89 44 24 44          	mov    %eax,0x44(%esp)
 807e406:	8d 44 24 40          	lea    0x40(%esp),%eax
 807e40a:	83 c0 04             	add    $0x4,%eax
 807e40d:	8b 00                	mov    (%eax),%eax
 807e40f:	8b 00                	mov    (%eax),%eax
 807e411:	89 05 68 8d 0d 08    	mov    %eax,0x80d8d68
/usr/local/lib/go/src/runtime/traceback.go:85

	// used by sigprof handler
	gogoPC = funcPC(gogo)
 807e417:	8d 05 20 28 09 08    	lea    0x8092820,%eax
 807e41d:	89 44 24 48          	mov    %eax,0x48(%esp)
 807e421:	8d 05 38 25 0a 08    	lea    0x80a2538,%eax
 807e427:	89 44 24 4c          	mov    %eax,0x4c(%esp)
 807e42b:	8d 44 24 48          	lea    0x48(%esp),%eax
 807e42f:	83 c0 04             	add    $0x4,%eax
 807e432:	8b 00                	mov    (%eax),%eax
 807e434:	8b 00                	mov    (%eax),%eax
 807e436:	89 05 b8 8d 0d 08    	mov    %eax,0x80d8db8
/usr/local/lib/go/src/runtime/traceback.go:86
}
 807e43c:	81 c4 88 00 00 00    	add    $0x88,%esp
 807e442:	c3                   	ret    
/usr/local/lib/go/src/runtime/traceback.go:62
func tracebackinit() {
 807e443:	e8 e8 7e 00 00       	call   8086330 <runtime.morestack_noctxt>
 807e448:	e9 83 fd ff ff       	jmp    807e1d0 <runtime.tracebackinit>
 807e44d:	cc                   	int3   
 807e44e:	cc                   	int3   
 807e44f:	cc                   	int3   

~~~

~~~assembly


~~~

