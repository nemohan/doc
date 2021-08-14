# influxql

[TOC]

原打算分析0.9.1版本的influxdb实现，所以

## scanner

scanner 之所以没有直接消耗掉空白字符，而是将其作为token返回给parser。是因为parser对空白字符有比较严格的限制。如 `db .retention_policy.measurement`是非法的。估计golang的scanner将空白字符直接消耗了，`fmt.     Printf("xx")`也是合法的 :(。

## parser

parser采用的是`递归下降(recursive-descent)` 算法



#### 解析表达式

##### Parser.parseUnaryExpr 解析一元表达式

~~~go
// parseUnaryExpr parses an non-binary expression.
func (p *Parser) parseUnaryExpr() (Expr, error) {
	// If the first token is a LPAREN then parse it as its own grouped expression.
	if tok, _, _ := p.scanIgnoreWhitespace(); tok == LPAREN {
		expr, err := p.ParseExpr()
		if err != nil {
			return nil, err
		}

		// Expect an RPAREN at the end.
		if tok, pos, lit := p.scanIgnoreWhitespace(); tok != RPAREN {
			return nil, newParseError(tokstr(tok, lit), []string{")"}, pos)
		}

		return &ParenExpr{Expr: expr}, nil
	}
	p.unscan()

	// Read next token.
	tok, pos, lit := p.scanIgnoreWhitespace()
	switch tok {
	case IDENT:
		// If the next immediate token is a left parentheses, parse as function call.
		// Otherwise parse as a variable reference.
		if tok0, _, _ := p.scan(); tok0 == LPAREN {
			return p.parseCall(lit)
		}

		p.unscan() // unscan the last token (wasn't an LPAREN)
		p.unscan() // unscan the IDENT token

		// Parse it as a VarRef.
		return p.parseVarRef()
	case DISTINCT:
		// If the next immediate token is a left parentheses, parse as function call.
		// Otherwise parse as a Distinct expression.
		tok0, pos, lit := p.scan()
		if tok0 == LPAREN {
			return p.parseCall("distinct")
		} else if tok0 == WS {
			tok1, pos, lit := p.scanIgnoreWhitespace()
			if tok1 != IDENT {
				return nil, newParseError(tokstr(tok1, lit), []string{"identifier"}, pos)
			}
			return &Distinct{Val: lit}, nil
		}

		return nil, newParseError(tokstr(tok0, lit), []string{"(", "identifier"}, pos)
	case STRING:
		// If literal looks like a date time then parse it as a time literal.
		if isDateTimeString(lit) {
			t, err := time.Parse(DateTimeFormat, lit)
			if err != nil {
				// try to parse it as an RFCNano time
				t, err := time.Parse(time.RFC3339Nano, lit)
				if err != nil {
					return nil, &ParseError{Message: "unable to parse datetime", Pos: pos}
				}
				return &TimeLiteral{Val: t}, nil
			}
			return &TimeLiteral{Val: t}, nil
		} else if isDateString(lit) {
			t, err := time.Parse(DateFormat, lit)
			if err != nil {
				return nil, &ParseError{Message: "unable to parse date", Pos: pos}
			}
			return &TimeLiteral{Val: t}, nil
		}
		return &StringLiteral{Val: lit}, nil
	case NUMBER:
		v, err := strconv.ParseFloat(lit, 64)
		if err != nil {
			return nil, &ParseError{Message: "unable to parse number", Pos: pos}
		}
		return &NumberLiteral{Val: v}, nil
	case TRUE, FALSE:
		return &BooleanLiteral{Val: (tok == TRUE)}, nil
	case DURATION_VAL:
		v, _ := ParseDuration(lit)
		return &DurationLiteral{Val: v}, nil
	case MUL:
		return &Wildcard{}, nil
	case REGEX:
		re, err := regexp.Compile(lit)
		if err != nil {
			return nil, &ParseError{Message: err.Error(), Pos: pos}
		}
		return &RegexLiteral{Val: re}, nil
	default:
		return nil, newParseError(tokstr(tok, lit), []string{"identifier", "string", "number", "bool"}, pos)
	}
}
~~~



##### Parser.parseCall 解析函数调用

~~~go
// parseCall parses a function call.
// This function assumes the function name and LPAREN have been consumed.
func (p *Parser) parseCall(name string) (*Call, error) {
	name = strings.ToLower(name)
	// If there's a right paren then just return immediately.
	if tok, _, _ := p.scan(); tok == RPAREN {
		return &Call{Name: name}, nil
	}
	p.unscan()

	// Otherwise parse function call arguments.
	var args []Expr
	for {
		// Parse an expression argument.
		arg, err := p.ParseExpr()
		if err != nil {
			return nil, err
		}
		args = append(args, arg)

		// If there's not a comma next then stop parsing arguments.
		if tok, _, _ := p.scan(); tok != COMMA {
			p.unscan()
			break
		}
	}

	// There should be a right parentheses at the end.
	if tok, pos, lit := p.scan(); tok != RPAREN {
		return nil, newParseError(tokstr(tok, lit), []string{")"}, pos)
	}

	return &Call{Name: name, Args: args}, nil
}
~~~



##### Parser.ParseExpr 解析表达式

~~~go
// ParseExpr parses an expression.
func (p *Parser) ParseExpr() (Expr, error) {
	var err error
	// Dummy root node.
	root := &BinaryExpr{}

	// Parse a non-binary expression type to start.
	// This variable will always be the root of the expression tree.
	root.RHS, err = p.parseUnaryExpr()
	if err != nil {
		return nil, err
	}

	// Loop over operations and unary exprs and build a tree based on precendence.
	for {
		// If the next token is NOT an operator then return the expression.
		op, _, _ := p.scanIgnoreWhitespace()
		if !op.isOperator() {
			p.unscan()
			return root.RHS, nil
		}

		// Otherwise parse the next expression.
		var rhs Expr
		if IsRegexOp(op) {
			// RHS of a regex operator must be a regular expression.
			p.consumeWhitespace()
			if rhs, err = p.parseRegex(); err != nil {
				return nil, err
			}
		} else {
			if rhs, err = p.parseUnaryExpr(); err != nil {
				return nil, err
			}
		}

		// Find the right spot in the tree to add the new expression by
		// descending the RHS of the expression tree until we reach the last
		// BinaryExpr or a BinaryExpr whose RHS has an operator with
		// precedence >= the operator being added.
		for node := root; ; {
			r, ok := node.RHS.(*BinaryExpr)
			if !ok || r.Op.Precedence() >= op.Precedence() {
				// Add the new expression here and break.
				node.RHS = &BinaryExpr{LHS: node.RHS, RHS: rhs, Op: op}
				break
			}
			node = r
		}
	}
}
~~~



#### 解析语句

##### Parser.parseCreateStatement 解析CREATE语句

相对简单，不再赘述

~~~go
// parseCreateStatement parses a string and returns a create statement.
// This function assumes the CREATE token has already been consumed.
func (p *Parser) parseCreateStatement() (Statement, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == CONTINUOUS {
		return p.parseCreateContinuousQueryStatement()
	} else if tok == DATABASE {
		return p.parseCreateDatabaseStatement()
	} else if tok == USER {
		return p.parseCreateUserStatement()
	} else if tok == RETENTION {
		tok, pos, lit = p.scanIgnoreWhitespace()
		if tok != POLICY {
			return nil, newParseError(tokstr(tok, lit), []string{"POLICY"}, pos)
		}
		return p.parseCreateRetentionPolicyStatement()
	}

	return nil, newParseError(tokstr(tok, lit), []string{"CONTINUOUS", "DATABASE", "USER", "RETENTION"}, pos)
}
~~~



##### Parser.parseDropSeriesStatement  DROP SERIES语句

格式: DROP SERIES FROM 

~~~go
// parseDropSeriesStatement parses a string and returns a DropSeriesStatement.
// This function assumes the "DROP SERIES" tokens have already been consumed.
func (p *Parser) parseDropSeriesStatement() (*DropSeriesStatement, error) {
	stmt := &DropSeriesStatement{}
	var err error

	tok, pos, lit := p.scanIgnoreWhitespace()

	if tok == FROM {
		// Parse source.
		if stmt.Sources, err = p.parseSources(); err != nil {
			return nil, err
		}
	} else {
		p.unscan()
	}

	// Parse condition: "WHERE EXPR".
	if stmt.Condition, err = p.parseCondition(); err != nil {
		return nil, err
	}

	// If they didn't provide a FROM or a WHERE, this query is invalid
	if stmt.Condition == nil && stmt.Sources == nil {
		return nil, newParseError(tokstr(tok, lit), []string{"FROM", "WHERE"}, pos)
	}

	return stmt, nil
}
~~~



##### Parser.parseDropStatement 解析drop语句

* DROP MEASUREMENT

* DROP DATABASE

* DROP CONTINUOUS

* DROP USER

* DROP RETENTION POLICY

  上面这些语句的解析都比较简单，不赘述

~~~go
// parseDropStatement parses a string and returns a drop statement.
// This function assumes the DROP token has already been consumed.
func (p *Parser) parseDropStatement() (Statement, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == SERIES {
		return p.parseDropSeriesStatement()
	} else if tok == MEASUREMENT {
		return p.parseDropMeasurementStatement()
	} else if tok == CONTINUOUS {
		return p.parseDropContinuousQueryStatement()
	} else if tok == DATABASE {
		return p.parseDropDatabaseStatement()
	} else if tok == RETENTION {
		if tok, pos, lit := p.scanIgnoreWhitespace(); tok != POLICY {
			return nil, newParseError(tokstr(tok, lit), []string{"POLICY"}, pos)
		}
		return p.parseDropRetentionPolicyStatement()
	} else if tok == USER {
		return p.parseDropUserStatement()
	}

	return nil, newParseError(tokstr(tok, lit), []string{"SERIES", "CONTINUOUS", "MEASUREMENT"}, pos)
}
~~~





##### Parser.parseGrantStatement 解析赋予用户权限的 GRANT 语句

格式: GRANT  privilege ON xx TO xx

~~~go
// parseGrantStatement parses a string and returns a grant statement.
// This function assumes the GRANT token has already been consumed.
func (p *Parser) parseGrantStatement() (*GrantStatement, error) {
	stmt := &GrantStatement{}

	// Parse the privilege to be granted.
	priv, err := p.parsePrivilege()
	if err != nil {
		return nil, err
	}
	stmt.Privilege = priv

	// Parse ON clause.
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == ON {
		// Parse the name of the thing we're granting a privilege to use.
		lit, err := p.parseIdent()
		if err != nil {
			return nil, err
		}
		stmt.On = lit

		tok, pos, lit = p.scanIgnoreWhitespace()
	} else if priv != AllPrivileges {
		// ALL PRIVILEGES is the only privilege allowed cluster-wide.
		// No ON clause means query is requesting cluster-wide.
		return nil, newParseError(tokstr(tok, lit), []string{"ON"}, pos)
	}

	// Check for required TO token.
	if tok != TO {
		return nil, newParseError(tokstr(tok, lit), []string{"TO"}, pos)
	}

	// Parse the name of the user we're granting the privilege to.
	lit, err = p.parseIdent()
	if err != nil {
		return nil, err
	}
	stmt.User = lit

	return stmt, nil
}
~~~



##### Parser.parseRevokeStatement 解析撤销用户权限的revoke语句

语句格式: REVOKE (READ, WRITE, ALL ) ON  name FROM  user

~~~go
// parseRevokeStatement parses a string and returns a revoke statement.
// This function assumes the REVOKE token has already been consumend.
func (p *Parser) parseRevokeStatement() (*RevokeStatement, error) {
	stmt := &RevokeStatement{}

	// Parse the privilege to be revoked.
	priv, err := p.parsePrivilege()
	if err != nil {
		return nil, err
	}
	stmt.Privilege = priv

	// Parse ON clause.
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == ON {
		// Parse the name of the thing we're revoking a privilege to use.
		lit, err := p.parseIdent()
		if err != nil {
			return nil, err
		}
		stmt.On = lit

		tok, pos, lit = p.scanIgnoreWhitespace()
	} else if priv != AllPrivileges {
		// ALL PRIVILEGES is the only privilege allowed cluster-wide.
		// No ON clause means query is requesting cluster-wide.
		return nil, newParseError(tokstr(tok, lit), []string{"ON"}, pos)
	}

	// Check for required FROM token.
	if tok != FROM {
		return nil, newParseError(tokstr(tok, lit), []string{"FROM"}, pos)
	}

	// Parse the name of the user we're revoking the privilege from.
	lit, err = p.parseIdent()
	if err != nil {
		return nil, err
	}
	stmt.User = lit

	return stmt, nil
}
~~~



##### Parser.parseAlterStatement 解析alter语句

完整的语句格式i: ALTER RETENTION POLICY name (DURATION xx, REPLICATION number， DEFAULT)



Parser.parseAlterRetentionPolicyStatement 有个bug在处理switch语句的default分支时，`return nil, newParseError(tokstr(tok, lit), []string{"DURATION", "RETENTION", "DEFAULT"}, pos)`应该是

`return nil, newParseError(tokstr(tok, lit), []string{"DURATION", "REPLICATION", "DEFAULT"}, pos)`

~~~go
// parseAlterStatement parses a string and returns an alter statement.
// This function assumes the ALTER token has already been consumed.
func (p *Parser) parseAlterStatement() (Statement, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == RETENTION {
		if tok, pos, lit = p.scanIgnoreWhitespace(); tok != POLICY {
			return nil, newParseError(tokstr(tok, lit), []string{"POLICY"}, pos)
		}
		return p.parseAlterRetentionPolicyStatement()
	}

	return nil, newParseError(tokstr(tok, lit), []string{"RETENTION"}, pos)
}

// parseAlterRetentionPolicyStatement parses a string and returns an alter retention policy statement.
// This function assumes the ALTER RETENTION POLICY tokens have already been consumned.
func (p *Parser) parseAlterRetentionPolicyStatement() (*AlterRetentionPolicyStatement, error) {
	stmt := &AlterRetentionPolicyStatement{}

	// Parse the retention policy name.
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok == DEFAULT {
		stmt.Name = "default"
	} else if tok == IDENT {
		stmt.Name = lit
	} else {
		return nil, newParseError(tokstr(tok, lit), []string{"identifier"}, pos)
	}

	// Consume the required ON token.
	if tok, pos, lit = p.scanIgnoreWhitespace(); tok != ON {
		return nil, newParseError(tokstr(tok, lit), []string{"ON"}, pos)
	}

	// Parse the database name.
	ident, err := p.parseIdent()
	if err != nil {
		return nil, err
	}
	stmt.Database = ident

	// Loop through option tokens (DURATION, REPLICATION, DEFAULT, etc.).
	maxNumOptions := 3
Loop:
	for i := 0; i < maxNumOptions; i++ {
		tok, pos, lit := p.scanIgnoreWhitespace()
		switch tok {
		case DURATION:
			d, err := p.parseDuration()
			if err != nil {
				return nil, err
			}
			stmt.Duration = &d
		case REPLICATION:
			n, err := p.parseInt(1, math.MaxInt32)
			if err != nil {
				return nil, err
			}
			stmt.Replication = &n
		case DEFAULT:
			stmt.Default = true
		default:
			if i < 1 {
				return nil, newParseError(tokstr(tok, lit), []string{"DURATION", "RETENTION", "DEFAULT"}, pos)
			}
			p.unscan()
			break Loop
		}
	}

	return stmt, nil
}
~~~



##### Parser.parseSetPasswordUserStatement 解析设置用户名密码的语句

语句格式: SET PASSWORD FOR username = 'password'

~~~go
//完整的语法应该是: SET PASSWORD FOR username = "password"
// parseSetPasswordUserStatement parses a string and returns a set statement.
// This function assumes the SET token has already been consumed.
func (p *Parser) parseSetPasswordUserStatement() (*SetPasswordUserStatement, error) {
	stmt := &SetPasswordUserStatement{}

	// Consume the required PASSWORD FOR tokens.
	if err := p.parseTokens([]Token{PASSWORD, FOR}); err != nil {
		return nil, err
	}

	// Parse username
	ident, err := p.parseIdent()

	if err != nil {
		return nil, err
	}
	stmt.Name = ident

	// Consume the required = token.
	if tok, pos, lit := p.scanIgnoreWhitespace(); tok != EQ {
		return nil, newParseError(tokstr(tok, lit), []string{"="}, pos)
	}

	// Parse new user's password
	if ident, err = p.parseString(); err != nil {
		return nil, err
	}
	stmt.Password = ident

	return stmt, nil
}
~~~

##### 一些公用的函数

###### Parser.parseString 确定下一个token是不是字符串

~~~go
// parserString parses a string.
func (p *Parser) parseString() (string, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok != STRING {
		return "", newParseError(tokstr(tok, lit), []string{"string"}, pos)
	}
	return lit, nil
}
~~~

###### Parser.parseTokens 确定后面的token是不是要求的token序列

~~~go
// parseTokens consumes an expected sequence of tokens.
func (p *Parser) parseTokens(toks []Token) error {
	for _, expected := range toks {
		if tok, pos, lit := p.scanIgnoreWhitespace(); tok != expected {
			return newParseError(tokstr(tok, lit), []string{tokens[expected]}, pos)
		}
	}
	return nil
}
~~~

###### Parser.parseDuration 解析时间类型token

~~~go
// parseDuration parses a string and returns a duration literal.
// This function assumes the DURATION token has already been consumed.
func (p *Parser) parseDuration() (time.Duration, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok != DURATION_VAL && tok != INF {
		return 0, newParseError(tokstr(tok, lit), []string{"duration"}, pos)
	}

	if tok == INF {
		return 0, nil
	}

	d, err := ParseDuration(lit)
	if err != nil {
		return 0, &ParseError{Message: err.Error(), Pos: pos}
	}

	return d, nil
}
~~~

###### Parser.parseInt 解析整型值token

~~~go
// parseInt parses a string and returns an integer literal.
func (p *Parser) parseInt(min, max int) (int, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	if tok != NUMBER {
		return 0, newParseError(tokstr(tok, lit), []string{"number"}, pos)
	}

	// Return an error if the number has a fractional part.
	if strings.Contains(lit, ".") {
		return 0, &ParseError{Message: "number must be an integer", Pos: pos}
	}

	// Convert string to int.
	n, err := strconv.Atoi(lit)
	if err != nil {
		return 0, &ParseError{Message: err.Error(), Pos: pos}
	} else if min > n || n > max {
		return 0, &ParseError{
			Message: fmt.Sprintf("invalid value %d: must be %d <= n <= %d", n, min, max),
			Pos:     pos,
		}
	}

	return n, nil
}
~~~

###### Parser.parsePrivilege 解析权限token

~~~go
func (p *Parser) parsePrivilege() (Privilege, error) {
	tok, pos, lit := p.scanIgnoreWhitespace()
	switch tok {
	case READ:
		return ReadPrivilege, nil
	case WRITE:
		return WritePrivilege, nil
	case ALL:
		// Consume optional PRIVILEGES token
		tok, pos, lit = p.scanIgnoreWhitespace()
		if tok != PRIVILEGES {
			p.unscan()
		}
		return AllPrivileges, nil
	}
	return 0, newParseError(tokstr(tok, lit), []string{"READ", "WRITE", "ALL [PRIVILEGES]"}, pos)
}
~~~

###### Parser.parseSource 解析 db.retention_policy.measurement

~~~go
func (p *Parser) parseSource() (Source, error) {
	m := &Measurement{}

	// Attempt to parse a regex.
	re, err := p.parseRegex()
	if err != nil {
		return nil, err
	} else if re != nil {
		m.Regex = re
		// Regex is always last so we're done.
		return m, nil
	}

	// Didn't find a regex so parse segmented identifiers.
	idents, err := p.parseSegmentedIdents()
	if err != nil {
		return nil, err
	}

	// If we already have the max allowed idents, we're done.
	if len(idents) == 3 {
		m.Database, m.RetentionPolicy, m.Name = idents[0], idents[1], idents[2]
		return m, nil
	}
	// Check again for regex.
	re, err = p.parseRegex()
	if err != nil {
		return nil, err
	} else if re != nil {
		m.Regex = re
	}

	// Assign identifiers to their proper locations.
	switch len(idents) {
	case 1:
		if re != nil {
			m.RetentionPolicy = idents[0]
		} else {
			m.Name = idents[0]
		}
	case 2:
		if re != nil {
			m.Database, m.RetentionPolicy = idents[0], idents[1]
		} else {
			m.RetentionPolicy, m.Name = idents[0], idents[1]
		}
	}

	return m, nil
}
~~~



###### Parser.parseSegementedIdents 解析数据表限定 db.retention_policy.measurement

* 调用p.parseIdent获取表示db的标识符
* 解析

下面为何直接调用p.scan和p.peekRune，而不是调用p.scanIgnoreWhitespace。因为p.scanIgnoreWhitespace会忽略掉空白字符。而`db.retention_policy.measurement`不允许空白字符出现

~~~go
// parseSegmentedIdents parses a segmented identifiers.
// e.g.,  "db"."rp".measurement  or  "db"..measurement
func (p *Parser) parseSegmentedIdents() ([]string, error) {
	ident, err := p.parseIdent()
	if err != nil {
		return nil, err
	}
	idents := []string{ident}

	// Parse remaining (optional) identifiers.
	for {
		if tok, _, _ := p.scan(); tok != DOT {
			// No more segments so we're done.
			p.unscan()
			break
		}
        //为什么
		if ch := p.peekRune(); ch == '/' {
			// Next segment is a regex so we're done.
			break
		} else if ch == '.' {
			// Add an empty identifier.
			idents = append(idents, "")
			continue
		}

		// Parse the next identifier.
		if ident, err = p.parseIdent(); err != nil {
			return nil, err
		}

		idents = append(idents, ident)
	}

	if len(idents) > 3 {
		msg := fmt.Sprintf("too many segments in %s", QuoteIdent(idents...))
		return nil, &ParseError{Message: msg}
	}

	return idents, nil
}
~~~



###### Parser.parseOrderBy

~~~go
// parseOrderBy parses the "ORDER BY" clause of a query, if it exists.
func (p *Parser) parseOrderBy() (SortFields, error) {
	// Return nil result and nil error if no ORDER token at this position.
	if tok, _, _ := p.scanIgnoreWhitespace(); tok != ORDER {
		p.unscan()
		return nil, nil
	}

	// Parse the required BY token.
	if tok, pos, lit := p.scanIgnoreWhitespace(); tok != BY {
		return nil, newParseError(tokstr(tok, lit), []string{"BY"}, pos)
	}

	// Parse the ORDER BY fields.
	fields, err := p.parseSortFields()
	if err != nil {
		return nil, err
	}

	return fields, nil
}
~~~



## ast

influxql的抽象语法树(Abstract syntax tree)，按《language implementation pattern》的说法是异构的（Heterogeneous）

##### Node接口

~~~go
// Node represents a node in the InfluxDB abstract syntax tree.
type Node interface {
	node()
	String() string
}
~~~



##### Statement

~~~go
// Statement represents a single command in InfluxQL.
type Statement interface {
	Node
	stmt()
	RequiredPrivileges() ExecutionPrivileges
}
~~~



##### Expr接口

~~~go
type Expr interface {
	Node
	expr()
}
~~~



## engine



## functions



