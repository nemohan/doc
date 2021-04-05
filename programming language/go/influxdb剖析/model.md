# model

[TOC]

influxdb 协议:

以空格分隔tags和fields、fields和时间戳。measurement和tags以 ","分隔。

~~~
<measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
~~~



## Point

model定义了写入influxdb的数据模型

##### Point 接口的定义

~~~go
// Point defines the values that will be written to the database.
type Point interface {
	// Name return the measurement name for the point.
	Name() []byte

	// SetName updates the measurement name for the point.
	SetName(string)

	// Tags returns the tag set for the point.
	Tags() Tags

	// ForEachTag iterates over each tag invoking fn.  If fn return false, iteration stops.
	ForEachTag(fn func(k, v []byte) bool)

	// AddTag adds or replaces a tag value for a point.
	AddTag(key, value string)

	// SetTags replaces the tags for the point.
	SetTags(tags Tags)

	// HasTag returns true if the tag exists for the point.
	HasTag(tag []byte) bool

	// Fields returns the fields for the point.
	Fields() (Fields, error)

	// Time return the timestamp for the point.
	Time() time.Time

	// SetTime updates the timestamp for the point.
	SetTime(t time.Time)

	// UnixNano returns the timestamp of the point as nanoseconds since Unix epoch.
	UnixNano() int64

	// HashID returns a non-cryptographic checksum of the point's key.
	HashID() uint64

	// Key returns the key (measurement joined with tags) of the point.
	Key() []byte

	// String returns a string representation of the point. If there is a
	// timestamp associated with the point then it will be specified with the default
	// precision of nanoseconds.
	String() string

	// MarshalBinary returns a binary representation of the point.
	MarshalBinary() ([]byte, error)

	// PrecisionString returns a string representation of the point. If there
	// is a timestamp associated with the point then it will be specified in the
	// given unit.
	PrecisionString(precision string) string

	// RoundedString returns a string representation of the point. If there
	// is a timestamp associated with the point, then it will be rounded to the
	// given duration.
	RoundedString(d time.Duration) string

	// Split will attempt to return multiple points with the same timestamp whose
	// string representations are no longer than size. Points with a single field or
	// a point without a timestamp may exceed the requested size.
	Split(size int) []Point

	// Round will round the timestamp of the point to the given duration.
	Round(d time.Duration)

	// StringSize returns the length of the string that would be returned by String().
	StringSize() int

	// AppendString appends the result of String() to the provided buffer and returns
	// the result, potentially reducing string allocations.
	AppendString(buf []byte) []byte

	// FieldIterator returns a FieldIterator that can be used to traverse the
	// fields of a point without constructing the in-memory map.
	FieldIterator() FieldIterator
}
~~~



##### point的定义

point 实现了FieldIterator接口

* key  由measurement name 和tags构成(且已经排好序)，不允许有重复的tag

~~~go
// point is the default implementation of Point.
type point struct {
	time time.Time

	// text encoding of measurement and tags
	// key must always be stored sorted by tags, if the original line was not sorted,
	// we need to resort it
    //key 由measurement name 和tags构成且已经排好序
	key []byte

	// text encoding of field data
	fields []byte

	// text encoding of timestamp
	ts []byte

	// cached version of parsed fields from data
	cachedFields map[string]interface{}

	// cached version of parsed name from key
	cachedName string

	// cached version of parsed tags
	cachedTags Tags

	it fieldIterator
}
~~~



##### Tag 和Tags

~~~go
// Tag represents a single key/value tag pair.
type Tag struct {
	Key   []byte
	Value []byte
}

// Tags represents a sorted list of tags.
type Tags []Tag
~~~



##### ParsePointsWithPrecision 解析带时间精度的数据

~~~go

// ParsePointsWithPrecision is similar to ParsePoints, but allows the
// caller to provide a precision for time.
//
// NOTE: to minimize heap allocations, the returned Points will refer to subslices of buf.
// This can have the unintended effect preventing buf from being garbage collected.
func ParsePointsWithPrecision(buf []byte, defaultTime time.Time, precision string) ([]Point, error) {
	points := make([]Point, 0, bytes.Count(buf, []byte{'\n'})+1)
	var (
		pos    int
		block  []byte
		failed []string
	)
	for pos < len(buf) {
        //pos指向第一个"\n", block指向以第一个"\n"结尾的内容
        //block即一行完整的数据, 不包括"\n"
		pos, block = scanLine(buf, pos)
		pos++

		if len(block) == 0 {
			continue
		}

        //跳过空格
		start := skipWhitespace(block, 0)

		// If line is all whitespace, just skip it
		if start >= len(block) {
			continue
		}

		// lines which start with '#' are comments
		if block[start] == '#' {
			continue
		}

		// strip the newline if one is present
		if block[len(block)-1] == '\n' {
			block = block[:len(block)-1]
		}
		//解析数据
		pt, err := parsePoint(block[start:], defaultTime, precision)
		if err != nil {
			failed = append(failed, fmt.Sprintf("unable to parse '%s': %v", string(block[start:]), err))
		} else {
			points = append(points, pt)
		}

	}
	if len(failed) > 0 {
		return points, fmt.Errorf("%s", strings.Join(failed, "\n"))
	}
	return points, nil

}
~~~



##### parsePoint 解析数据

measurement name 和所有tags(已经排好序)的长度不超过65535。解析过程中会去除重复的tag

~~~go
func parsePoint(buf []byte, defaultTime time.Time, precision string) (Point, error) {
	// scan the first block which is measurement[,tag1=value1,tag2=value2...]
    //pos fields的起始位置，key指向包含: measurement和tags的切片
    //或者说 key由measurement 名称和tags构成， 且key中的tag已经排序
	pos, key, err := scanKey(buf, 0)
	if err != nil {
		return nil, err
	}

	// measurement name is required
	if len(key) == 0 {
		return nil, fmt.Errorf("missing measurement")
	}

    //key的长度不超过65535
	if len(key) > MaxKeyLength {
		return nil, fmt.Errorf("max key length exceeded: %v > %v", len(key), MaxKeyLength)
	}

    //解析field=value部分
    //pos 指向field部分的起始位置，fields包含fields
	// scan the second block is which is field1=value1[,field2=value2,...]
	pos, fields, err := scanFields(buf, pos)
	if err != nil {
		return nil, err
	}

	// at least one field is required
	if len(fields) == 0 {
		return nil, fmt.Errorf("missing fields")
	}

	var maxKeyErr error
	err = walkFields(fields, func(k, v []byte) bool {
        //seriesKeySize的定义是: len(key) + 4+ len(k)
        //意思是tag 和value 的长度不能超过65535
		if sz := seriesKeySize(key, k); sz > MaxKeyLength {
			maxKeyErr = fmt.Errorf("max key length exceeded: %v > %v", sz, MaxKeyLength)
			return false
		}
		return true
	})

	if err != nil {
		return nil, err
	}

	if maxKeyErr != nil {
		return nil, maxKeyErr
	}

    //解析时间戳
	// scan the last block which is an optional integer timestamp
	pos, ts, err := scanTime(buf, pos)
	if err != nil {
		return nil, err
	}

	pt := &point{
		key:    key,
		fields: fields,
		ts:     ts,
	}

	if len(ts) == 0 {
		pt.time = defaultTime
		pt.SetPrecision(precision)
	} else {
		ts, err := parseIntBytes(ts, 10, 64)
		if err != nil {
			return nil, err
		}
		pt.time, err = SafeCalcTime(ts, precision)
		if err != nil {
			return nil, err
		}

		// Determine if there are illegal non-whitespace characters after the
		// timestamp block.
		for pos < len(buf) {
			if buf[pos] != ' ' {
				return nil, ErrInvalidPoint
			}
			pos++
		}
	}
	return pt, nil
}
~~~



##### scanKey 扫描tags

scanKey返回measurement的起始位置、以及measurement name和tags所在的切片构成的key

通过使用key在buf中的位置索引，避免内存分配。值得借鉴

* 跳过空格
* 调用scanMeasurement解析表名(measurement)，scanMeasurement会返回一个状态、以及measurement的结束位置
* 调用scanTags 解析tags。返回每个tag在buf中的位置的数组

~~~go
// scanKey scans buf starting at i for the measurement and tag portion of the point.
// It returns the ending position and the byte slice of key within buf.  If there
// are tags, they will be sorted if they are not already.
func scanKey(buf []byte, i int) (int, []byte, error) {
	start := skipWhitespace(buf, i)

	i = start

	// Determines whether the tags are sort, assume they are
	sorted := true

	// indices holds the indexes within buf of the start of each tag.  For example,
	// a buf of 'cpu,host=a,region=b,zone=c' would have indices slice of [4,11,20]
	// which indicates that the first tag starts at buf[4], seconds at buf[11], and
	// last at buf[20]
	indices := make([]int, 100)

	// tracks how many commas we've seen so we know how many values are indices.
	// Since indices is an arbitrarily large slice,
	// we need to know how many values in the buffer are in use.
	commas := 0

    //解析measurement, i指明了measurement的结束位置
    //若下一个是tag, 则i指向 ","下一个位置
    //若下一个是field, 则i指向 " " 字符
    //state这指明下一步是应该扫描tags还是fields
	// First scan the Point's measurement.
	state, i, err := scanMeasurement(buf, i)
	if err != nil {
		return i, buf[start:i], err
	}

    //cpu,tag1=value1,tag2=value2 field1=value1
    //扫描tags,  indices 记录了每个tag 的起始位置，即key的第一个字符的位置
	// Optionally scan tags if needed.
	if state == tagKeyState {
        // 返回值依次是: i 指向字符" " 的位置。 commas 字符','的个数、indices tag的起始位置数组。但indicies的最后一个元素记录的是 i 指向的字符' '后面一个字符的位置
		i, commas, indices, err = scanTags(buf, i, indices)
		if err != nil {
			return i, buf[start:i], err
		}
	}

    //检查是否有重复的tag
	// Now we know where the key region is within buf, and the location of tags, we
	// need to determine if duplicate tags exist and if the tags are sorted. This iterates
	// over the list comparing each tag in the sequence with each other.
	for j := 0; j < commas-1; j++ {
		// get the left and right tags
		_, left := scanTo(buf[indices[j]:indices[j+1]-1], 0, '=')
		_, right := scanTo(buf[indices[j+1]:indices[j+2]-1], 0, '=')

		// If left is greater than right, the tags are not sorted. We do not have to
		// continue because the short path no longer works.
		// If the tags are equal, then there are duplicate tags, and we should abort.
		// If the tags are not sorted, this pass may not find duplicate tags and we
		// need to do a more exhaustive search later.
		if cmp := bytes.Compare(left, right); cmp > 0 {
			sorted = false
			break
		} else if cmp == 0 {
			return i, buf[start:i], fmt.Errorf("duplicate tags")
		}
	}

	// If the tags are not sorted, then sort them.  This sort is inline and
	// uses the tag indices we created earlier.  The actual buffer is not sorted, the
	// indices are using the buffer for value comparison.  After the indices are sorted,
	// the buffer is reconstructed from the sorted indices.
    //commas大于1才需要排序吧
	if !sorted && commas > 0 {
		// Get the measurement name for later 
		measurement := buf[start : indices[0]-1]

		// Sort the indices
		indices := indices[:commas]
		insertionSort(0, commas, buf, indices)

		// Create a new key using the measurement and sorted indices
		b := make([]byte, len(buf[start:i]))
		pos := copy(b, measurement)
		for _, i := range indices {
			b[pos] = ','
			pos++
			_, v := scanToSpaceOr(buf, i, ',')
			pos += copy(b[pos:], v)
		}

		// Check again for duplicate tags now that the tags are sorted.
		for j := 0; j < commas-1; j++ {
			// get the left and right tags
			_, left := scanTo(buf[indices[j]:], 0, '=')
			_, right := scanTo(buf[indices[j+1]:], 0, '=')

			// If the tags are equal, then there are duplicate tags, and we should abort.
			// If the tags are not sorted, this pass may not find duplicate tags and we
			// need to do a more exhaustive search later.
			if bytes.Equal(left, right) {
				return i, b, fmt.Errorf("duplicate tags")
			}
		}

		return i, b, nil
	}

	return i, buf[start:i], nil
}
~~~



##### scanMeasurement 解析表名

~~~go
// scanMeasurement examines the measurement part of a Point, returning
// the next state to move to, and the current location in the buffer.
func scanMeasurement(buf []byte, i int) (int, int, error) {
	// Check first byte of measurement, anything except a comma is fine.
	// It can't be a space, since whitespace is stripped prior to this
	// function call.
	if i >= len(buf) || buf[i] == ',' {
		return -1, i, fmt.Errorf("missing measurement")
	}

	for {
		i++
		if i >= len(buf) {
			// cpu
			return -1, i, fmt.Errorf("missing fields")
		}

		if buf[i-1] == '\\' {
			// Skip character (it's escaped).
			continue
		}

		// Unescaped comma; move onto scanning the tags.
		if buf[i] == ',' {
			return tagKeyState, i + 1, nil
		}

		// Unescaped space; move onto scanning the fields.
		if buf[i] == ' ' {
			// cpu value=1.0
			return fieldsState, i, nil
		}
	}
}
~~~



##### scanFields

~~~go
// scanFields scans buf, starting at i for the fields section of a point.  It returns
// the ending position and the byte slice of the fields within buf.
func scanFields(buf []byte, i int) (int, []byte, error) {
	start := skipWhitespace(buf, i)
	i = start
	quoted := false

	// tracks how many '=' we've seen
	equals := 0

	// tracks how many commas we've seen
	commas := 0

	for {
		// reached the end of buf?
		if i >= len(buf) {
			break
		}

		// escaped characters?
		if buf[i] == '\\' && i+1 < len(buf) {
			i += 2
			continue
		}

		// If the value is quoted, scan until we get to the end quote
		// Only quote values in the field value since quotes are not significant
		// in the field key
		if buf[i] == '"' && equals > commas {
			quoted = !quoted
			i++
			continue
		}

		// If we see an =, ensure that there is at least on char before and after it
		if buf[i] == '=' && !quoted {
			equals++

			// check for "... =123" but allow "a\ =123"
			if buf[i-1] == ' ' && buf[i-2] != '\\' {
				return i, buf[start:i], fmt.Errorf("missing field key")
			}

			// check for "...a=123,=456" but allow "a=123,a\,=456"
			if buf[i-1] == ',' && buf[i-2] != '\\' {
				return i, buf[start:i], fmt.Errorf("missing field key")
			}

			// check for "... value="
			if i+1 >= len(buf) {
				return i, buf[start:i], fmt.Errorf("missing field value")
			}

			// check for "... value=,value2=..."
			if buf[i+1] == ',' || buf[i+1] == ' ' {
				return i, buf[start:i], fmt.Errorf("missing field value")
			}

			if isNumeric(buf[i+1]) || buf[i+1] == '-' || buf[i+1] == 'N' || buf[i+1] == 'n' {
				var err error
				i, err = scanNumber(buf, i+1)
				if err != nil {
					return i, buf[start:i], err
				}
				continue
			}
			// If next byte is not a double-quote, the value must be a boolean
			if buf[i+1] != '"' {
				var err error
				i, _, err = scanBoolean(buf, i+1)
				if err != nil {
					return i, buf[start:i], err
				}
				continue
			}
		}

		if buf[i] == ',' && !quoted {
			commas++
		}

		// reached end of block?
		if buf[i] == ' ' && !quoted {
			break
		}
		i++
	}

	if quoted {
		return i, buf[start:i], fmt.Errorf("unbalanced quotes")
	}
	//field1=value1,fiedl2=value2
	// check that all field sections had key and values (e.g. prevent "a=1,b"
	if equals == 0 || commas != equals-1 {
		return i, buf[start:i], fmt.Errorf("invalid field format")
	}

	return i, buf[start:i], nil
}
~~~



## FieldIterator接口

~~~go
// FieldIterator provides a low-allocation interface to iterate through a point's fields.
type FieldIterator interface {
	// Next indicates whether there any fields remaining.
	Next() bool

	// FieldKey returns the key of the current field.
	FieldKey() []byte

	// Type returns the FieldType of the current field.
	Type() FieldType

	// StringValue returns the string value of the current field.
	StringValue() string

	// IntegerValue returns the integer value of the current field.
	IntegerValue() (int64, error)

	// UnsignedValue returns the unsigned value of the current field.
	UnsignedValue() (uint64, error)

	// BooleanValue returns the boolean value of the current field.
	BooleanValue() (bool, error)

	// FloatValue returns the float value of the current field.
	FloatValue() (float64, error)

	// Reset resets the iterator to its initial state.
	Reset()
}
~~~

