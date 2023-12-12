# tracing



使用了CO-RE(compile once run everywhere)的跟踪点

| 类型                  | 挂载点            | SEC  |      |
| --------------------- | ----------------- | ---- | ---- |
| BPF_PROG_TYPE_TRACING | BPF_MODIFY_RETURN |      |      |
| BPF_PROG_TYPE_TRACING | BPF_TRACE_FENTRY  |      |      |
| BPF_PROG_TYPE_TRACING | BPF_TRACE_FEXIT   |      |      |
| BPF_PROG_TYPE_TRACING | BPF_TRACE_ITER    |      |      |
| BPF_PROG_TYPE_TRACING | BPF_TRACE_RAW_TP  |      |      |

