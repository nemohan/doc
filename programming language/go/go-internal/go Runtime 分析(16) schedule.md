# schedule

### 总结：

本地线程的run queue或者全局的runqueue,都是存放的可运行的gorutine.当取出一个可运行的gorutine运行

时，如果该gorutine阻塞，改gorutine会放在具体的阻塞队列。如通过channel接收消息阻塞，那么就会放在channel的阻塞队列中。待条件满足时，再放入runqueue中





~~~assembly
0806db30 <runtime.schedule>:
runtime.schedule():
/usr/local/lib/go/src/runtime/proc.go:2172

// One round of scheduler: find a runnable goroutine and execute it.
// Never returns.
func schedule() {
 806db30:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806db37:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806db3d:	3b 61 08             	cmp    0x8(%ecx),%esp
 806db40:	0f 86 b5 02 00 00    	jbe    806ddfb <runtime.schedule+0x2cb>
 806db46:	83 ec 18             	sub    $0x18,%esp
/usr/local/lib/go/src/runtime/proc.go:2173
	_g_ := getg()
 806db49:	65 8b 0d 00 00 00 00 	mov    %gs:0x0,%ecx
 806db50:	8b 89 fc ff ff ff    	mov    -0x4(%ecx),%ecx
 806db56:	89 4c 24 14          	mov    %ecx,0x14(%esp)
/usr/local/lib/go/src/runtime/proc.go:2175

	if _g_.m.locks != 0 {
 806db5a:	8b 51 18             	mov    0x18(%ecx),%edx
 806db5d:	8b 5a 78             	mov    0x78(%edx),%ebx
 806db60:	85 db                	test   %ebx,%ebx
 806db62:	0f 85 7b 02 00 00    	jne    806dde3 <runtime.schedule+0x2b3>
/usr/local/lib/go/src/runtime/proc.go:2179
		throw("schedule: holding locks")
	}

	if _g_.m.lockedg != nil {
 806db68:	8b 92 bc 00 00 00    	mov    0xbc(%edx),%edx
 806db6e:	85 d2                	test   %edx,%edx
 806db70:	0f 85 45 02 00 00    	jne    806ddbb <runtime.schedule+0x28b>
/usr/local/lib/go/src/runtime/proc.go:2185
		stoplockedm()
		execute(_g_.m.lockedg, false) // Never returns.
	}

top:
	if sched.gcwaiting != 0 {
 806db76:	8b 15 94 92 0c 08    	mov    0x80c9294,%edx
 806db7c:	85 d2                	test   %edx,%edx
 806db7e:	0f 85 93 00 00 00    	jne    806dc17 <runtime.schedule+0xe7>
/usr/local/lib/go/src/runtime/proc.go:2189
		gcstopm()
		goto top
	}
	if _g_.m.p.ptr().runSafePointFn != 0 {
 806db84:	8b 51 18             	mov    0x18(%ecx),%edx
 806db87:	8b 52 5c             	mov    0x5c(%edx),%edx
 806db8a:	8b 92 44 09 00 00    	mov    0x944(%edx),%edx
 806db90:	85 d2                	test   %edx,%edx
 806db92:	0f 85 15 02 00 00    	jne    806ddad <runtime.schedule+0x27d>
/usr/local/lib/go/src/runtime/proc.go:2195
		runSafePointFn()
	}

	var gp *g
	var inheritTime bool
	if trace.enabled || trace.shutdown {
 806db98:	0f b6 15 a8 0c 0d 08 	movzbl 0x80d0ca8,%edx
 806db9f:	84 d2                	test   %dl,%dl
 806dba1:	0f 84 f0 01 00 00    	je     806dd97 <runtime.schedule+0x267>
/usr/local/lib/go/src/runtime/proc.go:2196
		gp = traceReader()
 806dba7:	e8 94 ec 00 00       	call   807c840 <runtime.traceReader>
 806dbac:	8b 04 24             	mov    (%esp),%eax
 806dbaf:	89 44 24 10          	mov    %eax,0x10(%esp)
/usr/local/lib/go/src/runtime/proc.go:2197
		if gp != nil {
 806dbb3:	85 c0                	test   %eax,%eax
 806dbb5:	0f 85 a7 01 00 00    	jne    806dd62 <runtime.schedule+0x232>
/usr/local/lib/go/src/runtime/proc.go:2202
			casgstatus(gp, _Gwaiting, _Grunnable)
			traceGoUnpark(gp, 0)
		}
	}
	if gp == nil && gcBlackenEnabled != 0 {
 806dbbb:	85 c0                	test   %eax,%eax
 806dbbd:	0f 84 6b 01 00 00    	je     806dd2e <runtime.schedule+0x1fe>
/usr/local/lib/go/src/runtime/proc.go:2205
		gp = gcController.findRunnableGCWorker(_g_.m.p.ptr())
	}
	if gp == nil {
 806dbc3:	85 c0                	test   %eax,%eax
 806dbc5:	0f 84 e4 00 00 00    	je     806dcaf <runtime.schedule+0x17f>
/usr/local/lib/go/src/runtime/proc.go:2215
			lock(&sched.lock)
			gp = globrunqget(_g_.m.p.ptr(), 1)
			unlock(&sched.lock)
		}
	}
	if gp == nil {
 806dbcb:	85 c0                	test   %eax,%eax
 806dbcd:	0f 84 85 00 00 00    	je     806dc58 <runtime.schedule+0x128>
/usr/local/lib/go/src/runtime/proc.go:2181
		execute(_g_.m.lockedg, false) // Never returns.
 806dbd3:	31 c9                	xor    %ecx,%ecx
/usr/local/lib/go/src/runtime/proc.go:2221
		gp, inheritTime = runqget(_g_.m.p.ptr())
		if gp != nil && _g_.m.spinning {
			throw("schedule: spinning with local work")
		}
	}
	if gp == nil {
 806dbd5:	85 c0                	test   %eax,%eax
 806dbd7:	74 70                	je     806dc49 <runtime.schedule+0x119>
/usr/local/lib/go/src/runtime/proc.go:2232
	// start a new spinning M.
	if _g_.m.spinning {
		resetspinning()
	}

	if gp.lockedm != nil {
 806dbd9:	89 44 24 10          	mov    %eax,0x10(%esp)
/usr/local/lib/go/src/runtime/proc.go:2239
		// then blocks waiting for a new p.
		startlockedm(gp)
		goto top
	}

	execute(gp, inheritTime)
 806dbdd:	88 4c 24 0f          	mov    %cl,0xf(%esp)
/usr/local/lib/go/src/runtime/proc.go:2228
	if _g_.m.spinning {
 806dbe1:	8b 54 24 14          	mov    0x14(%esp),%edx
 806dbe5:	8b 5a 18             	mov    0x18(%edx),%ebx
 806dbe8:	0f b6 9b 8c 00 00 00 	movzbl 0x8c(%ebx),%ebx
 806dbef:	84 db                	test   %bl,%bl
 806dbf1:	75 42                	jne    806dc35 <runtime.schedule+0x105>
/usr/local/lib/go/src/runtime/proc.go:2232
	if gp.lockedm != nil {
 806dbf3:	8b 98 9c 00 00 00    	mov    0x9c(%eax),%ebx
 806dbf9:	85 db                	test   %ebx,%ebx
 806dbfb:	74 28                	je     806dc25 <runtime.schedule+0xf5>
/usr/local/lib/go/src/runtime/proc.go:2235
		startlockedm(gp)
 806dbfd:	89 04 24             	mov    %eax,(%esp)
 806dc00:	e8 2b f0 ff ff       	call   806cc30 <runtime.startlockedm>
/usr/local/lib/go/src/runtime/proc.go:2189
	if _g_.m.p.ptr().runSafePointFn != 0 {
 806dc05:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2185
	if sched.gcwaiting != 0 {
 806dc09:	8b 15 94 92 0c 08    	mov    0x80c9294,%edx
 806dc0f:	85 d2                	test   %edx,%edx
 806dc11:	0f 84 6d ff ff ff    	je     806db84 <runtime.schedule+0x54>
/usr/local/lib/go/src/runtime/proc.go:2186
		gcstopm()
 806dc17:	e8 d4 f0 ff ff       	call   806ccf0 <runtime.gcstopm>
/usr/local/lib/go/src/runtime/proc.go:2189
	if _g_.m.p.ptr().runSafePointFn != 0 {
 806dc1c:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2185
	if sched.gcwaiting != 0 {
 806dc20:	e9 51 ff ff ff       	jmp    806db76 <runtime.schedule+0x46>
/usr/local/lib/go/src/runtime/proc.go:2239
	execute(gp, inheritTime)
 806dc25:	89 04 24             	mov    %eax,(%esp)
 806dc28:	88 4c 24 04          	mov    %cl,0x4(%esp)
 806dc2c:	e8 cf f1 ff ff       	call   806ce00 <runtime.execute>
/usr/local/lib/go/src/runtime/proc.go:2240
}
 806dc31:	83 c4 18             	add    $0x18,%esp
 806dc34:	c3                   	ret    
/usr/local/lib/go/src/runtime/proc.go:2229
		resetspinning()
 806dc35:	e8 c6 fc ff ff       	call   806d900 <runtime.resetspinning>
/usr/local/lib/go/src/runtime/proc.go:2232
	if gp.lockedm != nil {
 806dc3a:	8b 44 24 10          	mov    0x10(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2239
	execute(gp, inheritTime)
 806dc3e:	0f b6 4c 24 0f       	movzbl 0xf(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2189
	if _g_.m.p.ptr().runSafePointFn != 0 {
 806dc43:	8b 54 24 14          	mov    0x14(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:2232
	if gp.lockedm != nil {
 806dc47:	eb aa                	jmp    806dbf3 <runtime.schedule+0xc3>
/usr/local/lib/go/src/runtime/proc.go:2222
		gp, inheritTime = findrunnable() // blocks until work is available
 806dc49:	e8 22 f3 ff ff       	call   806cf70 <runtime.findrunnable>
 806dc4e:	8b 04 24             	mov    (%esp),%eax
 806dc51:	0f b6 4c 24 04       	movzbl 0x4(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2232
	if gp.lockedm != nil {
 806dc56:	eb 81                	jmp    806dbd9 <runtime.schedule+0xa9>
/usr/local/lib/go/src/runtime/proc.go:2216
		gp, inheritTime = runqget(_g_.m.p.ptr())
 806dc58:	8b 44 24 14          	mov    0x14(%esp),%eax
 806dc5c:	8b 48 18             	mov    0x18(%eax),%ecx
 806dc5f:	8b 49 5c             	mov    0x5c(%ecx),%ecx
 806dc62:	89 0c 24             	mov    %ecx,(%esp)
 806dc65:	e8 96 53 00 00       	call   8073000 <runtime.runqget>
 806dc6a:	8b 44 24 04          	mov    0x4(%esp),%eax
 806dc6e:	0f b6 4c 24 08       	movzbl 0x8(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2217
		if gp != nil && _g_.m.spinning {
 806dc73:	85 c0                	test   %eax,%eax
 806dc75:	74 2f                	je     806dca6 <runtime.schedule+0x176>
 806dc77:	8b 54 24 14          	mov    0x14(%esp),%edx
 806dc7b:	8b 5a 18             	mov    0x18(%edx),%ebx
 806dc7e:	0f b6 9b 8c 00 00 00 	movzbl 0x8c(%ebx),%ebx
 806dc85:	84 db                	test   %bl,%bl
 806dc87:	75 05                	jne    806dc8e <runtime.schedule+0x15e>
/usr/local/lib/go/src/runtime/proc.go:2221
	if gp == nil {
 806dc89:	e9 47 ff ff ff       	jmp    806dbd5 <runtime.schedule+0xa5>
/usr/local/lib/go/src/runtime/proc.go:2218
			throw("schedule: spinning with local work")
 806dc8e:	8d 05 3c 13 0a 08    	lea    0x80a133c,%eax
 806dc94:	89 04 24             	mov    %eax,(%esp)
 806dc97:	c7 44 24 04 22 00 00 	movl   $0x22,0x4(%esp)
 806dc9e:	00 
 806dc9f:	e8 ec 9c ff ff       	call   8067990 <runtime.throw>
 806dca4:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2228
	if _g_.m.spinning {
 806dca6:	8b 54 24 14          	mov    0x14(%esp),%edx
/usr/local/lib/go/src/runtime/proc.go:2221
	if gp == nil {
 806dcaa:	e9 26 ff ff ff       	jmp    806dbd5 <runtime.schedule+0xa5>
/usr/local/lib/go/src/runtime/proc.go:2209
		if _g_.m.p.ptr().schedtick%61 == 0 && sched.runqsize > 0 {
 806dcaf:	8b 4c 24 14          	mov    0x14(%esp),%ecx
 806dcb3:	8b 51 18             	mov    0x18(%ecx),%edx
 806dcb6:	8b 52 5c             	mov    0x5c(%edx),%edx
 806dcb9:	8b 52 10             	mov    0x10(%edx),%edx
/usr/local/lib/go/src/runtime/proc.go:2205
	if gp == nil {
 806dcbc:	89 c3                	mov    %eax,%ebx
/usr/local/lib/go/src/runtime/proc.go:2209
		if _g_.m.p.ptr().schedtick%61 == 0 && sched.runqsize > 0 {
 806dcbe:	89 d0                	mov    %edx,%eax
 806dcc0:	bd 3f c5 25 43       	mov    $0x4325c53f,%ebp
 806dcc5:	89 d6                	mov    %edx,%esi
 806dcc7:	f7 e5                	mul    %ebp
 806dcc9:	c1 ea 04             	shr    $0x4,%edx
 806dccc:	6b d2 3d             	imul   $0x3d,%edx,%edx
 806dccf:	29 d6                	sub    %edx,%esi
 806dcd1:	85 f6                	test   %esi,%esi
 806dcd3:	75 0a                	jne    806dcdf <runtime.schedule+0x1af>
 806dcd5:	8b 05 60 92 0c 08    	mov    0x80c9260,%eax
 806dcdb:	85 c0                	test   %eax,%eax
 806dcdd:	7f 07                	jg     806dce6 <runtime.schedule+0x1b6>
/usr/local/lib/go/src/runtime/proc.go:2215
	if gp == nil {
 806dcdf:	89 d8                	mov    %ebx,%eax
 806dce1:	e9 e5 fe ff ff       	jmp    806dbcb <runtime.schedule+0x9b>
/usr/local/lib/go/src/runtime/proc.go:2210
			lock(&sched.lock)
 806dce6:	8d 05 30 92 0c 08    	lea    0x80c9230,%eax
 806dcec:	89 04 24             	mov    %eax,(%esp)
 806dcef:	e8 8c 26 fe ff       	call   8050380 <runtime.lock>
/usr/local/lib/go/src/runtime/proc.go:2211
			gp = globrunqget(_g_.m.p.ptr(), 1)
 806dcf4:	8b 44 24 14          	mov    0x14(%esp),%eax
 806dcf8:	8b 48 18             	mov    0x18(%eax),%ecx
 806dcfb:	8b 49 5c             	mov    0x5c(%ecx),%ecx
 806dcfe:	89 0c 24             	mov    %ecx,(%esp)
 806dd01:	c7 44 24 04 01 00 00 	movl   $0x1,0x4(%esp)
 806dd08:	00 
 806dd09:	e8 62 4d 00 00       	call   8072a70 <runtime.globrunqget>
 806dd0e:	8b 44 24 08          	mov    0x8(%esp),%eax
 806dd12:	89 44 24 10          	mov    %eax,0x10(%esp)
/usr/local/lib/go/src/runtime/proc.go:2210
			lock(&sched.lock)
 806dd16:	8d 0d 30 92 0c 08    	lea    0x80c9230,%ecx
/usr/local/lib/go/src/runtime/proc.go:2212
			unlock(&sched.lock)
 806dd1c:	89 0c 24             	mov    %ecx,(%esp)
 806dd1f:	e8 3c 28 fe ff       	call   8050560 <runtime.unlock>
/usr/local/lib/go/src/runtime/proc.go:2228
	if _g_.m.spinning {
 806dd24:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2215
	if gp == nil {
 806dd28:	8b 5c 24 10          	mov    0x10(%esp),%ebx
 806dd2c:	eb b1                	jmp    806dcdf <runtime.schedule+0x1af>
/usr/local/lib/go/src/runtime/proc.go:2202
	if gp == nil && gcBlackenEnabled != 0 {
 806dd2e:	8b 0d a8 8d 0d 08    	mov    0x80d8da8,%ecx
 806dd34:	85 c9                	test   %ecx,%ecx
 806dd36:	75 05                	jne    806dd3d <runtime.schedule+0x20d>
/usr/local/lib/go/src/runtime/proc.go:2205
	if gp == nil {
 806dd38:	e9 86 fe ff ff       	jmp    806dbc3 <runtime.schedule+0x93>
/usr/local/lib/go/src/runtime/proc.go:2203
		gp = gcController.findRunnableGCWorker(_g_.m.p.ptr())
 806dd3d:	8b 44 24 14          	mov    0x14(%esp),%eax
 806dd41:	8b 48 18             	mov    0x18(%eax),%ecx
 806dd44:	8b 49 5c             	mov    0x5c(%ecx),%ecx
 806dd47:	8d 15 00 84 0c 08    	lea    0x80c8400,%edx
 806dd4d:	89 14 24             	mov    %edx,(%esp)
 806dd50:	89 4c 24 04          	mov    %ecx,0x4(%esp)
 806dd54:	e8 f7 9a fe ff       	call   8057850 <runtime.(*gcControllerState).findRunnableGCWorker>
 806dd59:	8b 44 24 08          	mov    0x8(%esp),%eax
/usr/local/lib/go/src/runtime/proc.go:2205
	if gp == nil {
 806dd5d:	e9 61 fe ff ff       	jmp    806dbc3 <runtime.schedule+0x93>
/usr/local/lib/go/src/runtime/proc.go:2198
			casgstatus(gp, _Gwaiting, _Grunnable)
 806dd62:	89 04 24             	mov    %eax,(%esp)
 806dd65:	c7 44 24 04 04 00 00 	movl   $0x4,0x4(%esp)
 806dd6c:	00 
 806dd6d:	c7 44 24 08 01 00 00 	movl   $0x1,0x8(%esp)
 806dd74:	00 
 806dd75:	e8 86 cd ff ff       	call   806ab00 <runtime.casgstatus>
/usr/local/lib/go/src/runtime/proc.go:2199
			traceGoUnpark(gp, 0)
 806dd7a:	8b 44 24 10          	mov    0x10(%esp),%eax
 806dd7e:	89 04 24             	mov    %eax,(%esp)
 806dd81:	c7 44 24 04 00 00 00 	movl   $0x0,0x4(%esp)
 806dd88:	00 
 806dd89:	e8 82 ff 00 00       	call   807dd10 <runtime.traceGoUnpark>
/usr/local/lib/go/src/runtime/proc.go:2202
	if gp == nil && gcBlackenEnabled != 0 {
 806dd8e:	8b 44 24 10          	mov    0x10(%esp),%eax
 806dd92:	e9 24 fe ff ff       	jmp    806dbbb <runtime.schedule+0x8b>
/usr/local/lib/go/src/runtime/proc.go:2195
	if trace.enabled || trace.shutdown {
 806dd97:	0f b6 15 a9 0c 0d 08 	movzbl 0x80d0ca9,%edx
 806dd9e:	84 d2                	test   %dl,%dl
 806dda0:	0f 85 01 fe ff ff    	jne    806dba7 <runtime.schedule+0x77>
/usr/local/lib/go/src/runtime/proc.go:2179
	if _g_.m.lockedg != nil {
 806dda6:	31 c0                	xor    %eax,%eax
/usr/local/lib/go/src/runtime/proc.go:2202
	if gp == nil && gcBlackenEnabled != 0 {
 806dda8:	e9 0e fe ff ff       	jmp    806dbbb <runtime.schedule+0x8b>
/usr/local/lib/go/src/runtime/proc.go:2190
		runSafePointFn()
 806ddad:	e8 0e de ff ff       	call   806bbc0 <runtime.runSafePointFn>
/usr/local/lib/go/src/runtime/proc.go:2209
		if _g_.m.p.ptr().schedtick%61 == 0 && sched.runqsize > 0 {
 806ddb2:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2195
	if trace.enabled || trace.shutdown {
 806ddb6:	e9 dd fd ff ff       	jmp    806db98 <runtime.schedule+0x68>
/usr/local/lib/go/src/runtime/proc.go:2180
		stoplockedm()
 806ddbb:	e8 20 ed ff ff       	call   806cae0 <runtime.stoplockedm>
/usr/local/lib/go/src/runtime/proc.go:2181
		execute(_g_.m.lockedg, false) // Never returns.
 806ddc0:	8b 44 24 14          	mov    0x14(%esp),%eax
 806ddc4:	8b 48 18             	mov    0x18(%eax),%ecx
 806ddc7:	8b 89 bc 00 00 00    	mov    0xbc(%ecx),%ecx
 806ddcd:	89 0c 24             	mov    %ecx,(%esp)
 806ddd0:	c6 44 24 04 00       	movb   $0x0,0x4(%esp)
 806ddd5:	e8 26 f0 ff ff       	call   806ce00 <runtime.execute>
/usr/local/lib/go/src/runtime/proc.go:2189
	if _g_.m.p.ptr().runSafePointFn != 0 {
 806ddda:	8b 4c 24 14          	mov    0x14(%esp),%ecx
/usr/local/lib/go/src/runtime/proc.go:2185
	if sched.gcwaiting != 0 {
 806ddde:	e9 93 fd ff ff       	jmp    806db76 <runtime.schedule+0x46>
/usr/local/lib/go/src/runtime/proc.go:2176
		throw("schedule: holding locks")
 806dde3:	8d 05 18 fe 09 08    	lea    0x809fe18,%eax
 806dde9:	89 04 24             	mov    %eax,(%esp)
 806ddec:	c7 44 24 04 17 00 00 	movl   $0x17,0x4(%esp)
 806ddf3:	00 
 806ddf4:	e8 97 9b ff ff       	call   8067990 <runtime.throw>
 806ddf9:	0f 0b                	ud2    
/usr/local/lib/go/src/runtime/proc.go:2172
func schedule() {
 806ddfb:	e8 30 85 01 00       	call   8086330 <runtime.morestack_noctxt>
 806de00:	e9 2b fd ff ff       	jmp    806db30 <runtime.schedule>
 806de05:	cc                   	int3   
 806de06:	cc                   	int3   
 806de07:	cc                   	int3   
 806de08:	cc                   	int3   
 806de09:	cc                   	int3   
 806de0a:	cc                   	int3   
 806de0b:	cc                   	int3   
 806de0c:	cc                   	int3   
 806de0d:	cc                   	int3   
 806de0e:	cc                   	int3   
 806de0f:	cc                   	int3  

~~~







~~~
// One round of scheduler: find a runnable goroutine and execute it.
// Never returns.
func schedule() {
	_g_ := getg()

	if _g_.m.locks != 0 {
		throw("schedule: holding locks")
	}

	if _g_.m.lockedg != nil {
		stoplockedm()
		execute(_g_.m.lockedg, false) // Never returns.
	}

top:
	if sched.gcwaiting != 0 {
		gcstopm()
		goto top
	}
	if _g_.m.p.ptr().runSafePointFn != 0 {
		runSafePointFn()
	}

	var gp *g
	var inheritTime bool
	if trace.enabled || trace.shutdown {
		gp = traceReader()
		if gp != nil {
			casgstatus(gp, _Gwaiting, _Grunnable)
			traceGoUnpark(gp, 0)
		}
	}
	if gp == nil && gcBlackenEnabled != 0 {
		gp = gcController.findRunnableGCWorker(_g_.m.p.ptr())
	}
	if gp == nil {
		// Check the global runnable queue once in a while to ensure fairness.
		// Otherwise two goroutines can completely occupy the local runqueue
		// by constantly respawning each other.
		if _g_.m.p.ptr().schedtick%61 == 0 && sched.runqsize > 0 {
			lock(&sched.lock)
			gp = globrunqget(_g_.m.p.ptr(), 1)
			unlock(&sched.lock)
		}
	}
	if gp == nil {
		gp, inheritTime = runqget(_g_.m.p.ptr())
		if gp != nil && _g_.m.spinning {
			throw("schedule: spinning with local work")
		}
	}
	if gp == nil {
		gp, inheritTime = findrunnable() // blocks until work is available
	}

	// This thread is going to run a goroutine and is not spinning anymore,
	// so if it was marked as spinning we need to reset it now and potentially
	// start a new spinning M.
	if _g_.m.spinning {
		resetspinning()
	}

	if gp.lockedm != nil {
		// Hands off own p to the locked m,
		// then blocks waiting for a new p.
		startlockedm(gp)
		goto top
	}

	execute(gp, inheritTime)
}

~~~

