# pickle 反序列化导致的爆栈

2021/11/21

最近在负责一个python项目的杂活，主要是解决知识库脚本框架中的一些bug。遇到一个爆栈的bug，记录一下。看调用栈是 \_\_getattr__ 调用\_\_getattr, __getattr又调用get_dimension_value。get_dimension_value又触发了\_\_getattr\_\_的调用。\_\_getattr\_\_ 函数用于获取对象的一个属性值，若属性值不存在则会抛出AttributError异常。很显然是某个属性导致的，添加了一些输出后，确定是get_dimension_value获取self.\_cache属性导致的。但结合代码看在调用对象的构造函数时明明设置了self.\_cache属性，怎么会导致\_\_getattr\_\_的调用呢？经过一番查找，原来还有一处使用了pickle.loads()反序列化数据生成了一个对象。看来反序列化时并不会触发构造函数的调用所以才缺失了self.\_cache属性



~~~python
class TableObject:
    """维度对象"""

    def __init__(self, ds_id, table, dimensions, where) -> None:
        self.ds_id = ds_id
        self.table = table
        self.dimensions = dimensions
        self.where = where

        self._cache = {}

    def get_query(self):
        return Query(
            table=self.table, columns=copy.copy(self.dimensions), where=self.where
        )

    def __str__(self) -> str:
        return self.format()

    def __getitem__(self, name: str):
        return self.__getattr(name)

    #这里
    def __getattr__(self, name: str):
        print("++++++++++", name)
        return self.__getattr(name)

    def __getattr(self, name: str):
        if name.startswith("__"):
            raise AttributeError()

        format = True
        if name[0] == "$":
            format = False
            name = name[1:]

        rst = self.get_dimension_value(name, format)

        if rst is None:
            raise AttributeError(f"invalid attribute: {name}")

        return rst

    def __getstate__(self):
        return (self.ds_id, self.table, self.dimensions, self.where)

    def __setstate__(self, state):
        self.ds_id, self.table, self.dimensions, self.where = state

    def format(self):
        ds = get_datasource_by_id(self.ds_id)

        result = []
        for dimension in self.dimensions:
            title = ds.get_column_title(self.table, dimension)

            value = None
            for v in self.where["children"]:
                if v["operator"] == "=" and v["column"] == dimension:
                    value = ds.format_value(self.table, dimension, v["value"])

            if value:
                result.append(title + "=" + value)

        if not self.dimensions:
            for v in self.where["children"]:
                if v["operator"] == "=":
                    title = ds.get_column_title(self.table, v["column"])
                    value = ds.format_value(self.table, v["column"], v["value"])
                    if value:
                        result.append(title + "=" + value)

        return ",".join(result)

    def serialize(self):
        return pickle.dumps(self)

    """
    有问题的代码
    @staticmethod
    def unserialize(data):
        return pickle.loads(data)
      
    """
    @staticmethod
    def unserialize(data):
        b = pickle.loads(data)
        b._cache = {}
        return b

    def shortid(self):
        return hashlib.md5(self.serialize()).hexdigest()

    def dump(self):
        return {
            "ds_id": self.ds_id,
            "table": self.table,
            "dimensions": self.dimensions,
            "where": self.where,
            "name": self.format(),
        }

    def get_table_object(self, table):
        ds = get_datasource_by_id(self.ds_id)
        table = readable.parse_table(ds, table)

        if table != self.table:
            return TableObject(
                self.ds_id,
                table,
                copy.copy(self.dimensions),
                copy.deepcopy(self.where),
            )
            # raise ValueError("table not match")

        return self.copy()

    def copy(self):
        return TableObject(
            self.ds_id,
            self.table,
            copy.copy(self.dimensions),
            copy.deepcopy(self.where),
        )

    复制 = copy

    def get_dimension_value(self, name, format=True):
        cache_key = (name, format)
        if cache_key in self._cache:
            return self._cache[cache_key]

        ds = get_datasource_by_id(self.ds_id)

        _, name = readable.parse_column(ds, self.table, name)

        for v in reversed(self.where["children"]):
            if (
                v["operator"] == "="
                and v["column"] == name
                and type(v["value"]) != list
            ):
                if not format:
                    self._cache[cache_key] = v["value"]
                else:
                    self._cache[cache_key] = ds.format_value(
                        self.table, name, v["value"]
                    )
                return self._cache[cache_key]

        return None

    def 获取维度(self, 维度, 格式化=True):
        return self.get_dimension_value(维度, 格式化)

    def add_where(self, dimension, operator, value):
        self._cache = {}
        ds = get_datasource_by_id(self.ds_id)

        _, dimension = readable.parse_column(ds, self.table, dimension)

        # 去掉重复条件
        if operator == "=":
            self.where["children"] = [
                x for x in self.where["children"] if x["column"] != dimension
            ]

        self.where["children"].append(
            {
                "column": dimension,
                "operator": operator,
                "value": value,
            }
        )

    def 添加条件(self, 维度, 类型="=", 值=None):
        operator = readable.trans_value(类型, readable.TRANS_MAP_OPERATOR)
        self.add_where(维度, operator, 值)

    @property
    def obj_type(self):
        return 0

    @property
    def 类型(self):
        return "自定义"
~~~

