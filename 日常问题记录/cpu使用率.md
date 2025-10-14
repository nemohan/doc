# cpu使用率

linux系统环境下，使用top或pidstat查看cpu使用率，在IRIX mode和 Solaris mode模式下，cpu的使用率计算方式不同

ubuntu top命令默认IRIX mode on模式

top命令:

IRIX mode off时，cpu使用率不超过100%

IRIX mode on时，cpu使用率会超过100%

pidstat命令：

默认IRIX mode on模式

进程的cpu使用率计算方式:



pidstat计算cpu使用率的方式:

~~~c

//参数itv为两次计算之间的uptime差值
// deltot_jiffies为两次计算之间的 /proc/stat cpu all 的总和的差值
//默认情况下 IRIX_MODE_OFF(pidflags) 返回false
void write_plain_pid_task_cpu_data(int disp_avg,
				   struct pid_stats *pstc, struct pid_stats *pstp,
				   unsigned long long itv,
				   unsigned long long deltot_jiffies)
{
	cprintf_xpc(DISPLAY_UNIT(pidflag), XHIGH, 5, 7, 2,
		    (pstc->utime - pstc->gtime) < (pstp->utime - pstp->gtime) ||
		    (pstc->utime < pstc->gtime) || (pstp->utime < pstp->gtime) ?
		    0.0 :
		    SP_VALUE(pstp->utime - pstp->gtime,
			     pstc->utime - pstc->gtime, itv * HZ / 100),
		    SP_VALUE(pstp->stime, pstc->stime, itv * HZ / 100),
		    SP_VALUE(pstp->gtime, pstc->gtime, itv * HZ / 100),
		    SP_VALUE(pstp->wtime, pstc->wtime, itv * HZ / 100),
		    /* User time already includes guest time */
		    IRIX_MODE_OFF(pidflag) ?
		    SP_VALUE(pstp->utime + pstp->stime,
			     pstc->utime + pstc->stime, deltot_jiffies) :
			     SP_VALUE(pstp->utime + pstp->stime,
				      pstc->utime + pstc->stime, itv * HZ / 100));

    
	if (!disp_avg) {
		cprintf_in(IS_INT, "   %3d", "", pstc->processor);
	}
	else {
		cprintf_in(IS_STR, "%s", "     -", 0);
	}
}

~~~



## 其他

* github.com/shirou/gopsutil/v4/process 中的Process.CPUPercent 的计算逻辑不同于pidstat/top

## 参考

* https://www.howtosop.com/irix-mode-vs-solaris-mode-in-top-command/