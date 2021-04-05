# Data

[TOC]

## Data

Data是数据元数据的内存表示

Data包含以下几部分：

* ClusterID 集群节点ID
* Databases 数据库
* Users 用户信息
* MaxShardGroupID 最大分片组ID
* MaxShardID 最大分片ID

~~~go
// Data represents the top level collection of all metadata.
type Data struct {
	Term      uint64 // associated raft term
	Index     uint64 // associated raft index
	ClusterID uint64
	Databases []DatabaseInfo
	Users     []UserInfo

	// adminUserExists provides a constant time mechanism for determining
	// if there is at least one admin user.
	adminUserExists bool

	MaxShardGroupID uint64
	MaxShardID      uint64
}
~~~



##### Data.UnmarshalBinary

~~~go
// UnmarshalBinary decodes the object from a binary format.
func (data *Data) UnmarshalBinary(buf []byte) error {
	var pb internal.Data
	if err := proto.Unmarshal(buf, &pb); err != nil {
		return err
	}
	data.unmarshal(&pb)
	return nil
}
~~~



##### Data.unmarshal 从protobuf转换为Data

~~~go
// unmarshal deserializes from a protobuf representation.
func (data *Data) unmarshal(pb *internal.Data) {
	data.Term = pb.GetTerm()
	data.Index = pb.GetIndex()
	data.ClusterID = pb.GetClusterID()

	data.MaxShardGroupID = pb.GetMaxShardGroupID()
	data.MaxShardID = pb.GetMaxShardID()

	data.Databases = make([]DatabaseInfo, len(pb.GetDatabases()))
	for i, x := range pb.GetDatabases() {
		data.Databases[i].unmarshal(x)
	}

	data.Users = make([]UserInfo, len(pb.GetUsers()))
	for i, x := range pb.GetUsers() {
		data.Users[i].unmarshal(x)
	}

	// Exhaustively determine if there is an admin user. The marshalled cache
	// value may not be correct.
	data.adminUserExists = data.hasAdminUser()
}
~~~



##### Data.CreateDatabase 创建数据库

~~~go
// CreateDatabase creates a new database.
// It returns an error if name is blank or if a database with the same name already exists.
func (data *Data) CreateDatabase(name string) error {
	if name == "" {
		return ErrDatabaseNameRequired
	} else if len(name) > MaxNameLen {
		return ErrNameTooLong
	} else if data.Database(name) != nil {
		return nil
	}

	// Append new node.
	data.Databases = append(data.Databases, DatabaseInfo{Name: name})

	return nil
}
~~~



##### Data.DropDatabase 删除数据库

~~~go
// DropDatabase removes a database by name. It does not return an error
// if the database cannot be found.
func (data *Data) DropDatabase(name string) error {
	for i := range data.Databases {
		if data.Databases[i].Name == name {
			data.Databases = append(data.Databases[:i], data.Databases[i+1:]...)

			// Remove all user privileges associated with this database.
			for i := range data.Users {
				delete(data.Users[i].Privileges, name)
			}
			break
		}
	}
	return nil
}
~~~



##### Data.Database 根据数据库名称获取数据库信息

~~~go
// Database returns a DatabaseInfo by the database name.
func (data *Data) Database(name string) *DatabaseInfo {
	for i := range data.Databases {
		if data.Databases[i].Name == name {
			return &data.Databases[i]
		}
	}
	return nil
}
~~~



##### Data.CreateRentionPolicy 为数据库创建持久化策略

* 约束性检查，持久化策略名称必须不为空、长度比需小于MaxNameLen、副本数量必须大于等于1

~~~go
// CreateRetentionPolicy creates a new retention policy on a database.
// It returns an error if name is blank or if the database does not exist.
func (data *Data) CreateRetentionPolicy(database string, rpi *RetentionPolicyInfo, makeDefault bool) error {
	// Validate retention policy.
	if rpi == nil {
		return ErrRetentionPolicyRequired
	} else if rpi.Name == "" {
		return ErrRetentionPolicyNameRequired
	} else if len(rpi.Name) > MaxNameLen {
		return ErrNameTooLong
	} else if rpi.ReplicaN < 1 {
		return ErrReplicationFactorTooLow
	}

	// Normalise ShardDuration before comparing to any existing
	// retention policies. The client is supposed to do this, but
	// do it again to verify input.
	rpi.ShardGroupDuration = normalisedShardDuration(rpi.ShardGroupDuration, rpi.Duration)

	if rpi.Duration > 0 && rpi.Duration < rpi.ShardGroupDuration {
		return ErrIncompatibleDurations
	}

	// Find database.
	di := data.Database(database)
	if di == nil {
		return influxdb.ErrDatabaseNotFound(database)
	} else if rp := di.RetentionPolicy(rpi.Name); rp != nil {
		// RP with that name already exists. Make sure they're the same.
		if rp.ReplicaN != rpi.ReplicaN || rp.Duration != rpi.Duration || rp.ShardGroupDuration != rpi.ShardGroupDuration {
			return ErrRetentionPolicyExists
		}
		// if they want to make it default, and it's not the default, it's not an identical command so it's an error
		if makeDefault && di.DefaultRetentionPolicy != rpi.Name {
			return ErrRetentionPolicyConflict
		}
		return nil
	}

	// Append copy of new policy.
	di.RetentionPolicies = append(di.RetentionPolicies, *rpi)

	// Set the default if needed
	if makeDefault {
		di.DefaultRetentionPolicy = rpi.Name
	}

	return nil
}
~~~



## DatabaseInfo 定义数据库

数据库的元数据包含以下几部分：

* 数据库名称
* 默认的持久化策略
* 其他持久化策略(RetentionPolicyInfo)
* 连续查询(ContinuousQueryInfo)

~~~go
// DatabaseInfo represents information about a database in the system.
type DatabaseInfo struct {
	Name                   string
	DefaultRetentionPolicy string
	RetentionPolicies      []RetentionPolicyInfo
	ContinuousQueries      []ContinuousQueryInfo
}
~~~



##### DatabaseInfo.unmarshal

~~~go
// unmarshal deserializes from a protobuf representation.
func (di *DatabaseInfo) unmarshal(pb *internal.DatabaseInfo) {
	di.Name = pb.GetName()
	di.DefaultRetentionPolicy = pb.GetDefaultRetentionPolicy()

	if len(pb.GetRetentionPolicies()) > 0 {
		di.RetentionPolicies = make([]RetentionPolicyInfo, len(pb.GetRetentionPolicies()))
		for i, x := range pb.GetRetentionPolicies() {
			di.RetentionPolicies[i].unmarshal(x)
		}
	}

	if len(pb.GetContinuousQueries()) > 0 {
		di.ContinuousQueries = make([]ContinuousQueryInfo, len(pb.GetContinuousQueries()))
		for i, x := range pb.GetContinuousQueries() {
			di.ContinuousQueries[i].unmarshal(x)
		}
	}
}
~~~



### ContinuousQueryInfo 连续查询

~~~go
// ContinuousQueryInfo represents metadata about a continuous query.
type ContinuousQueryInfo struct {
	Name  string
	Query string
}
~~~



## RetentionPolicyInfo 定义持久化策略

持久化策略由下面几部分组成：

* 名称
* 副本数目
* 持久化时间
* 分片持久化时间
* 分片组

~~~go
const (
	// DefaultRetentionPolicyReplicaN is the default value of RetentionPolicyInfo.ReplicaN.
	DefaultRetentionPolicyReplicaN = 1

	// DefaultRetentionPolicyDuration is the default value of RetentionPolicyInfo.Duration.
	DefaultRetentionPolicyDuration = time.Duration(0)

	// DefaultRetentionPolicyName is the default name for auto generated retention policies.
	DefaultRetentionPolicyName = "autogen"

	// MinRetentionPolicyDuration represents the minimum duration for a policy.
	MinRetentionPolicyDuration = time.Hour

	// MaxNameLen is the maximum length of a database or retention policy name.
	// InfluxDB uses the name for the directory name on disk.
	MaxNameLen = 255
)

// RetentionPolicyInfo represents metadata about a retention policy.
type RetentionPolicyInfo struct {
	Name               string
	ReplicaN           int
	Duration           time.Duration
	ShardGroupDuration time.Duration
	ShardGroups        []ShardGroupInfo
	Subscriptions      []SubscriptionInfo
}
~~~



##### NewRetentionPolicyInfo

~~~go
// NewRetentionPolicyInfo returns a new instance of RetentionPolicyInfo
// with default replication and duration.
func NewRetentionPolicyInfo(name string) *RetentionPolicyInfo {
	return &RetentionPolicyInfo{
		Name:     name,
		ReplicaN: DefaultRetentionPolicyReplicaN, //默认值是1
		Duration: DefaultRetentionPolicyDuration, //默认值是0
	}
}



// Apply applies a specification to the retention policy info.
func (rpi *RetentionPolicyInfo) Apply(spec *RetentionPolicySpec) *RetentionPolicyInfo {
	rp := &RetentionPolicyInfo{
		Name:               rpi.Name,
		ReplicaN:           rpi.ReplicaN,
		Duration:           rpi.Duration,
		ShardGroupDuration: rpi.ShardGroupDuration,
	}
	if spec.Name != "" {
		rp.Name = spec.Name
	}
	if spec.ReplicaN != nil {
		rp.ReplicaN = *spec.ReplicaN
	}
	if spec.Duration != nil {
		rp.Duration = *spec.Duration
	}
	rp.ShardGroupDuration = normalisedShardDuration(spec.ShardGroupDuration, rp.Duration)
	return rp
}

// ShardGroupB
~~~



##### DefaultRetentionPolicyInfo 默认的持久化策略autogen

~~~go
// DefaultRetentionPolicyInfo returns a new instance of RetentionPolicyInfo
// with default name, replication, and duration.
func DefaultRetentionPolicyInfo() *RetentionPolicyInfo {
	return NewRetentionPolicyInfo(DefaultRetentionPolicyName)
}
~~~



##### RetentionPolicyInfo.ShardGroupByTimestam 根据时间戳查找分片

~~~go
// ShardGroupByTimestamp returns the shard group in the policy that contains the timestamp,
// or nil if no shard group matches.
func (rpi *RetentionPolicyInfo) ShardGroupByTimestamp(timestamp time.Time) *ShardGroupInfo {
	for i := range rpi.ShardGroups {
		sgi := &rpi.ShardGroups[i]
		if sgi.Contains(timestamp) && !sgi.Deleted() && (!sgi.Truncated() || timestamp.Before(sgi.TruncatedAt)) {
			return &rpi.ShardGroups[i]
		}
	}

	return nil
}
~~~



#### RetentionPolicySpec

~~~go
// RetentionPolicySpec represents the specification for a new retention policy.
type RetentionPolicySpec struct {
	Name               string
	ReplicaN           *int
	Duration           *time.Duration
	ShardGroupDuration time.Duration
}

// NewRetentionPolicyInfo creates a new retention policy info from the specification.
func (s *RetentionPolicySpec) NewRetentionPolicyInfo() *RetentionPolicyInfo {
	return DefaultRetentionPolicyInfo().Apply(s)
}
~~~



##### Data.RetentionPolicy  根据数据库名称、持久化策略名称查找持久化策略

~~~go
// RetentionPolicy returns a retention policy for a database by name.
func (data *Data) RetentionPolicy(database, name string) (*RetentionPolicyInfo, error) {
	di := data.Database(database)
	if di == nil {
		return nil, influxdb.ErrDatabaseNotFound(database)
	}

	for i := range di.RetentionPolicies {
		if di.RetentionPolicies[i].Name == name {
			return &di.RetentionPolicies[i], nil
		}
	}
	return nil, nil
}
~~~



## ShardGroupInfo 分片组

<font color="red">一个分片组包含几个分片是由什么决定的, 分片组又是何时创建的</font>

* 创建持久化策略时，并不会立即创建分片组。在写入数据时才会创建
* 

ShardGroupInfo 包含了分片组的相关元数据：

* 分片组所覆盖的时间StartTime、EndTime
* 删除时间DeletedAt
* 分片组Shards

~~~go
// ShardGroupInfo represents metadata about a shard group. The DeletedAt field is important
// because it makes it clear that a ShardGroup has been marked as deleted, and allow the system
// to be sure that a ShardGroup is not simply missing. If the DeletedAt is set, the system can
// safely delete any associated shards.
type ShardGroupInfo struct {
	ID          uint64
	StartTime   time.Time
	EndTime     time.Time
	DeletedAt   time.Time
	Shards      []ShardInfo
	TruncatedAt time.Time
}

// ShardInfo represents metadata about a shard.
type ShardInfo struct {
	ID     uint64
	Owners []ShardOwner
}

// ShardOwner represents a node that owns a shard.
type ShardOwner struct {
	NodeID uint64
}
~~~



#### ShardGroupInfos

~~~go
// ShardGroupInfos implements sort.Interface on []ShardGroupInfo, based
// on the StartTime field.
type ShardGroupInfos []ShardGroupInfo
~~~





##### Data.CreateShardGroup 创建分片组

~~~go
// CreateShardGroup creates a shard group on a database and policy for a given timestamp.
func (data *Data) CreateShardGroup(database, policy string, timestamp time.Time) error {
	// Find retention policy.
	rpi, err := data.RetentionPolicy(database, policy)
	if err != nil {
		return err
	} else if rpi == nil {
		return influxdb.ErrRetentionPolicyNotFound(policy)
	}

	// Verify that shard group doesn't already exist for this timestamp.
	if rpi.ShardGroupByTimestamp(timestamp) != nil {
		return nil
	}

	// Create the shard group.
	data.MaxShardGroupID++
	sgi := ShardGroupInfo{}
	sgi.ID = data.MaxShardGroupID
    //取边界， 比如timestamp的值是 2020-1-11 08:08:08。分片组的持久化时间是1小时。 
    //StartTime的值就是2020-1-11 08:EndTime就是
	sgi.StartTime = timestamp.Truncate(rpi.ShardGroupDuration).UTC()
	sgi.EndTime = sgi.StartTime.Add(rpi.ShardGroupDuration).UTC()
	if sgi.EndTime.After(time.Unix(0, models.MaxNanoTime)) {
		// Shard group range is [start, end) so add one to the max time.
		sgi.EndTime = time.Unix(0, models.MaxNanoTime+1)
	}

	data.MaxShardID++
	sgi.Shards = []ShardInfo{
		{ID: data.MaxShardID},
	}

	// Retention policy has a new shard group, so update the policy. Shard
	// Groups must be stored in sorted order, as other parts of the system
	// assume this to be the case.
	rpi.ShardGroups = append(rpi.ShardGroups, sgi)
	sort.Sort(ShardGroupInfos(rpi.ShardGroups))

	return nil
}
~~~



##### Data.ShardGroupByTimestamp 根据时间戳查找分片组

Client.CreateShardGroup 会调用此函数

~~~go
// ShardGroupByTimestamp returns the shard group on a database and policy for a given timestamp.
func (data *Data) ShardGroupByTimestamp(database, policy string, timestamp time.Time) (*ShardGroupInfo, error) {
	// Find retention policy.
	rpi, err := data.RetentionPolicy(database, policy)
	if err != nil {
		return nil, err
	} else if rpi == nil {
		return nil, influxdb.ErrRetentionPolicyNotFound(policy)
	}

	return rpi.ShardGroupByTimestamp(timestamp), nil
}

~~~



##### normalizeShardDuration 标准化分片时间

shardGroupDuration根据持久化策略的持久时间，确定分片组的持久化时间。

* 若持久化策略的持久时间超过6个月或0。则分片组的最大持续化时间为一周
* 若持久化策略的持久时间小于6个月大于2天。则分片组的持久化时间为1天
* 其他， 分片组的持久化时间为1小时



normallisedShardDuration 根据策略持久化时间和分片组持久化时间确定分片组的持久化时间

* 分片组时间为0。根据持久化策略时间来确定。规则见上
* 分片组时间小于最小的持久化策略时间（1小时)。根据默认的最小持久化策略时间来确定，规则见上
* 其他，即分片组持久化时间

~~~go
//根据持久化策略的持久时间，确定分片组的持久化时间
// shardGroupDuration returns the default duration for a shard group based on a policy duration.
func shardGroupDuration(d time.Duration) time.Duration {
	if d >= 180*24*time.Hour || d == 0 { // 6 months or 0
		return 7 * 24 * time.Hour
	} else if d >= 2*24*time.Hour { // 2 days
		return 1 * 24 * time.Hour
	}
	return 1 * time.Hour
}

// normalisedShardDuration returns normalised shard duration based on a policy duration.
func normalisedShardDuration(sgd, d time.Duration) time.Duration {
	// If it is zero, it likely wasn't specified, so we default to the shard group duration
    //sgd 是分片组的持久化时间， d 是持久化策略的持久时间
	if sgd == 0 {
		return shardGroupDuration(d)
	}
    
    //MinRetentionPolicyDuration 的默认值是1小时
	// If it was specified, but it's less than the MinRetentionPolicyDuration, then normalize
	// to the MinRetentionPolicyDuration
	if sgd < MinRetentionPolicyDuration {
		return shardGroupDuration(MinRetentionPolicyDuration)
	}
	return sgd
}
~~~



##### ShardGroupInfo.ShardFor  根据point的key的哈希值确定分片

key 由measurement name 和tags构成(已排序)

~~~go
// ShardFor returns the ShardInfo for a Point hash.
func (sgi *ShardGroupInfo) ShardFor(hash uint64) ShardInfo {
	return sgi.Shards[hash%uint64(len(sgi.Shards))]
}
~~~



## UserInfo

UserInfo 实现了query.Authorizer接口

~~~go
// UserInfo represents metadata about a user in the system.
type UserInfo struct {
	// User's name.
	Name string

	// Hashed password.
	Hash string

	// Whether the user is an admin, i.e. allowed to do everything.
	Admin bool

	// Map of database name to granted privilege.
	Privileges map[string]influxql.Privilege
}

type User interface {
	query.Authorizer
	ID() string
	AuthorizeUnrestricted() bool
}
~~~

