# 加速

acceler.c

~~~c
//遍历所有的DFA
void
PyGrammar_AddAccelerators(grammar *g)
{
	dfa *d;
	int i;
	d = g->g_dfa;
	for (i = g->g_ndfas; --i >= 0; d++)
		fixdfa(g, d);
	g->g_accel = 1;
}

void
PyGrammar_RemoveAccelerators(grammar *g)
{
	dfa *d;
	int i;
	g->g_accel = 0;
	d = g->g_dfa;
	for (i = g->g_ndfas; --i >= 0; d++) {
		state *s;
		int j;
		s = d->d_state;
		for (j = 0; j < d->d_nstates; j++, s++) {
			if (s->s_accel)
				PyObject_FREE(s->s_accel);
			s->s_accel = NULL;
		}
	}
}

//遍历DFA的所有状态， DFA包含起始状态，接受状态
static void
fixdfa(grammar *g, dfa *d)
{
	state *s;
	int j;
	s = d->d_state;
	for (j = 0; j < d->d_nstates; j++, s++)
		fixstate(g, s);
}

//就目前来说，知道DFA有哪些状态，有哪些label(输入),
//将所有的DFA整合成一个大的DFA
static void
fixstate(grammar *g, state *s)
{
	arc *a;
	int k;
	int *accel;

	//所有输入集合(terminal, nonterminal)
	int nl = g->g_ll.ll_nlabels;
	s->s_accept = 0;
	accel = (int *) PyObject_MALLOC(nl * sizeof(int));
	if (accel == NULL) {
		fprintf(stderr, "no mem to build parser accelerators\n");
		exit(1);
	}

	//nl 为所有输入集合数组，大小为168
	for (k = 0; k < nl; k++)
		accel[k] = -1;

	// s_arc 当前状态拥有的arc(弧)
	a = s->s_arc;
	for (k = s->s_narcs; --k >= 0; a++) {

		//a_lbl 弧上对应的输入所在的下标
		int lbl = a->a_lbl;

		//对应的输入类型
		label *l = &g->g_ll.ll_label[lbl];
		int type = l->lb_type;

		
		if (a->a_arrow >= (1 << 7)) {
			printf("XXX too many states!\n");
			continue;
		}

		//输入类型是nonterminal
		if (ISNONTERMINAL(type)) {
			//找到nonterminal对应的DFA
			dfa *d1 = PyGrammar_FindDFA(g, type);
			int ibit;
			if (type - NT_OFFSET >= (1 << 7)) {
				printf("XXX too high nonterminal number!\n");
				continue;
			}

			//所有的输入, 
			//TODO: accel 内的东西有什么作用, type - NT_OFFSET,是d1 在DFA数组中的下标
			for (ibit = 0; ibit < g->g_ll.ll_nlabels; ibit++) {
				if (testbit(d1->d_first, ibit)) {
					if (accel[ibit] != -1)
						printf("XXX ambiguity!\n");
					accel[ibit] = a->a_arrow | (1 << 7) |
						((type - NT_OFFSET) << 8);
				}
			}
		}//如果下标为0，s->s_accept 设置1
		else if (lbl == EMPTY)
			s->s_accept = 1;
		else if (lbl >= 0 && lbl < nl)
			accel[lbl] = a->a_arrow;
	}

	//缩小搜索范围
	while (nl > 0 && accel[nl-1] == -1)
		nl--;
	for (k = 0; k < nl && accel[k] == -1;)
		k++;
	if (k < nl) {
		int i;
		s->s_accel = (int *) PyObject_MALLOC((nl-k) * sizeof(int));
		if (s->s_accel == NULL) {
			fprintf(stderr, "no mem to add parser accelerators\n");
			exit(1);
		}
		s->s_lower = k;
		s->s_upper = nl;
		for (i = 0; k < nl; i++, k++)
			s->s_accel[i] = accel[k];
	}
	PyObject_FREE(accel);
}

~~~

