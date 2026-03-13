# 内存对齐

[TOC]



用下面的程序测试，感觉内存是否对齐对性能影响不大

~~~c
void Munge64( void *data, uint32_t size , void *src) {
    uint64_t *data64 = (uint64_t*) data;
    uint64_t *data64End = data64 + (size >> 3); /* Divide size by 8. */

    uint64_t *data64_src = (uint64_t*)src;

    uint8_t * data_src = (uint8_t*)src;
    uint8_t *data_end = src + size;
    uint32_t count =0;
    while( data64 != data64End ) {
        memcpy(data64++, src, 8);
        //内存对齐访问版本
        //memcpy(data64++, data64_src++, 8);
        src+=11;
        if((uint8_t*)(src) > data_end){
            src = data_src;
        }
    }
}

int main(int argc, char **argv){
    uint32_t size = 1024 * 1024 * 10;
    struct timeval begin, end;  
    uint32_t total = 0; 
    for (int i = 0; i < 500; i++){
        void *data = malloc(1024 * 1024 * 10);
        void * src = malloc(1024 * 1024 * 10);
        gettimeofday(&begin, NULL);
        //Munge8(data, size, src);
        Munge64(data, size, src);
        //Munge16(data, size);
        gettimeofday(&end, NULL);
        uint64_t begin_t = begin.tv_sec * 1000 * 1000 + begin.tv_usec; 
        uint64_t end_t = end.tv_sec * 1000 * 1000 +end.tv_usec;
        total +=  (end_t - begin_t);
        free(data);
    }
    printf("%dms\n", total / 500 / 1000);
    return 0;
}
~~~



* 在现代cpu上运行的应用，访问非对齐的内存对性能还有多大影响（怎么设计测试用例)

* 在什么情况下，必须确保内存地址对齐


~~~
/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_X86_BARRIER_H
#define _ASM_X86_BARRIER_H

#include <asm/alternative.h>
#include <asm/nops.h>

/*
 * Force strict CPU ordering.
 * And yes, this might be required on UP too when we're talking
 * to devices.
 */

#ifdef CONFIG_X86_32
#define mb() asm volatile(ALTERNATIVE("lock; addl $0,-4(%%esp)", "mfence", \
				      X86_FEATURE_XMM2) ::: "memory", "cc")
#define rmb() asm volatile(ALTERNATIVE("lock; addl $0,-4(%%esp)", "lfence", \
				       X86_FEATURE_XMM2) ::: "memory", "cc")
#define wmb() asm volatile(ALTERNATIVE("lock; addl $0,-4(%%esp)", "sfence", \
				       X86_FEATURE_XMM2) ::: "memory", "cc")
#else
#define mb() 	asm volatile("mfence":::"memory")
#define rmb()	asm volatile("lfence":::"memory")
#define wmb()	asm volatile("sfence" ::: "memory")
#endif

/**
 * array_index_mask_nospec() - generate a mask that is ~0UL when the
 * 	bounds check succeeds and 0 otherwise
 * @index: array element index
 * @size: number of elements in array
 *
 * Returns:
 *     0 - (index < size)
 */
static inline unsigned long array_index_mask_nospec(unsigned long index,
		unsigned long size)
{
	unsigned long mask;

	asm volatile ("cmp %1,%2; sbb %0,%0;"
			:"=r" (mask)
			:"g"(size),"r" (index)
			:"cc");
	return mask;
}

/* Override the default implementation from linux/nospec.h. */
#define array_index_mask_nospec array_index_mask_nospec

/* Prevent speculative execution past this barrier. */
#define barrier_nospec() alternative("", "lfence", X86_FEATURE_LFENCE_RDTSC)

#define dma_rmb()	barrier()
#define dma_wmb()	barrier()

#ifdef CONFIG_X86_32
#define __smp_mb()	asm volatile("lock; addl $0,-4(%%esp)" ::: "memory", "cc")
#else
#define __smp_mb()	asm volatile("lock; addl $0,-4(%%rsp)" ::: "memory", "cc")
#endif
#define __smp_rmb()	dma_rmb()
#define __smp_wmb()	barrier()
#define __smp_store_mb(var, value) do { (void)xchg(&var, value); } while (0)

#define __smp_store_release(p, v)					\
do {									\
	compiletime_assert_atomic_type(*p);				\
	barrier();							\
	WRITE_ONCE(*p, v);						\
} while (0)

#define __smp_load_acquire(p)						\
({									\
	typeof(*p) ___p1 = READ_ONCE(*p);				\
	compiletime_assert_atomic_type(*p);				\
	barrier();							\
	___p1;								\
})

/* Atomic operations are already serializing on x86 */
#define __smp_mb__before_atomic()	do { } while (0)
#define __smp_mb__after_atomic()	do { } while (0)

#include <asm-generic/barrier.h>

/*
 * Make previous memory operations globally visible before
 * a WRMSR.
 *
 * MFENCE makes writes visible, but only affects load/store
 * instructions.  WRMSR is unfortunately not a load/store
 * instruction and is unaffected by MFENCE.  The LFENCE ensures
 * that the WRMSR is not reordered.
 *
 * Most WRMSRs are full serializing instructions themselves and
 * do not require this barrier.  This is only required for the
 * IA32_TSC_DEADLINE and X2APIC MSRs.
 */
static inline void weak_wrmsr_fence(void)
{
	asm volatile("mfence; lfence" : : : "memory");
}

#endif /* _ASM_X86_BARRIER_H */
~~~



## 参考

* https://programmerclick.com/article/76132676395/
* https://lemire.me/blog/2012/05/31/data-alignment-for-speed-myth-or-reality/
* https://stackoverflow.com/questions/381244/purpose-of-memory-alignment/381368#381368