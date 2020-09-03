# explain解读

mysql 5.6

MySQL resolves all joins using a nested-loop join method. This means that MySQL reads a row from the first table, and then finds a matching row in the second table, the third table, and so on. 

~~~mysql
mysql> explain select * from weibo_id \G
*************************** 1. row ***************************
           id: 1
  select_type: SIMPLE
        table: weibo_id
         type: ALL
possible_keys: NULL
          key: NULL
      key_len: NULL
          ref: NULL
         rows: 5
        Extra: NULL
1 row in set (0.00 sec)

Extra: using where 代表在server端而不是在存储引擎端使用where条件过滤了不符合条件的数据
Extra: using index 代表使用了覆盖索引
rows: 代表最终的结果集有多少行， 还是为了得到结果集mysql处理了多少行
key: 代表使用的索引
type: all 代表全表扫描
~~~





### 8.8.2 EXPLAIN Output Format

地址: https://dev.mysql.com/doc/refman/5.6/en/explain-output.html

The [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) statement provides information about how MySQL executes statements. [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) works with [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html), [`DELETE`](https://dev.mysql.com/doc/refman/5.6/en/delete.html), [`INSERT`](https://dev.mysql.com/doc/refman/5.6/en/insert.html), [`REPLACE`](https://dev.mysql.com/doc/refman/5.6/en/replace.html), and [`UPDATE`](https://dev.mysql.com/doc/refman/5.6/en/update.html)statements.

[`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) returns a row of information for each table used in the [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statement. It lists the tables in the output in the order that MySQL would read them while processing the statement. MySQL resolves all joins using a nested-loop join method. This means that MySQL reads a row from the first table, and then finds a matching row in the second table, the third table, and so on. When all tables are processed, MySQL outputs the selected columns and backtracks through the table list until a table is found for which there are more matching rows. The next row is read from this table and the process continues with the next table.

When the `EXTENDED` keyword is used, [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) produces extra information that can be viewed by issuing a [`SHOW WARNINGS`](https://dev.mysql.com/doc/refman/5.6/en/show-warnings.html) statement following the [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html)statement. [`EXPLAIN EXTENDED`](https://dev.mysql.com/doc/refman/5.6/en/explain-extended.html) also displays the `filtered` column. See [Section 8.8.3, “Extended EXPLAIN Output Format”](https://dev.mysql.com/doc/refman/5.6/en/explain-extended.html).

Note

You cannot use the `EXTENDED` and `PARTITIONS` keywords together in the same [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) statement. Neither of these keywords can be used together with the `FORMAT` option. (`FORMAT=JSON` causes `EXPLAIN` to display extended and partition information automatically; using`FORMAT=TRADITIONAL` has no effect on `EXPLAIN` output.)

Note

MySQL Workbench has a Visual Explain capability that provides a visual representation of [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output. See [Tutorial: Using Explain to Improve Query Performance](https://dev.mysql.com/doc/workbench/en/wb-tutorial-visual-explain-dbt3.html).

- [EXPLAIN Output Columns](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-output-columns)
- [EXPLAIN Join Types](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-join-types)
- [EXPLAIN Extra Information](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-extra-information)
- [EXPLAIN Output Interpretation](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-output-interpretation)

#### EXPLAIN Output Columns

This section describes the output columns produced by [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html). Later sections provide additional information about the [`type`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-join-types) and [`Extra`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-extra-information) columns.

Each output row from [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) provides information about one table. Each row contains the values summarized in [Table 8.1, “EXPLAIN Output Columns”](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-output-column-table), and described in more detail following the table. Column names are shown in the table's first column; the second column provides the equivalent property name shown in the output when `FORMAT=JSON` is used.



**Table 8.1 EXPLAIN Output Columns**

| Column                                                       | JSON Name       | Meaning                                          |
| ------------------------------------------------------------ | --------------- | ------------------------------------------------ |
| [`id`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_id) | `select_id`     | The `SELECT` identifier                          |
| [`select_type`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_select_type) | None            | The `SELECT` type                                |
| [`table`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_table) | `table_name`    | The table for the output row                     |
| [`partitions`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_partitions) | `partitions`    | The matching partitions                          |
| [`type`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_type) | `access_type`   | The join type                                    |
| [`possible_keys`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_possible_keys) | `possible_keys` | The possible indexes to choose                   |
| [`key`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_key) | `key`           | The index actually chosen                        |
| [`key_len`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_key_len) | `key_length`    | The length of the chosen key                     |
| [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_ref) | `ref`           | The columns compared to the index 和索引对比的列 |
| [`rows`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_rows) | `rows`          | Estimate of rows to be examined                  |
| [`filtered`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_filtered) | `filtered`      | Percentage of rows filtered by table condition   |
| [`Extra`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain_extra) | None            | Additional information                           |





Note

JSON properties which are `NULL` are not displayed in JSON-formatted `EXPLAIN` output.

- `id` (JSON name: `select_id`)

  The [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) identifier. This is the sequential number of the [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) within the query. The value can be `NULL` if the row refers to the union result of other rows. In this case, the `table` column shows a value like `<union*M*,*N*>` to indicate that the row refers to the union of the rows with `id` values of *M* and *N*.

  ~~~mysql
  EXPLAIN (SELECT finance_statement.out_trade_no FROM finance_statement )
  	UNION ALL(SELECT outTradeNo FROM pos_order ) LIMIT 20;
  ~~~

  执行上面语句得到的结果：

- | id     | select_type  | table             | type  | possible_keys | key        | key_len | ref    | rows   | Extra           |
  | ------ | ------------ | ----------------- | ----- | ------------- | ---------- | ------- | ------ | ------ | --------------- |
  | (NULL) | UNION RESULT | <union1,2>        | ALL   | (NULL)        | (NULL)     | (NULL)  | (NULL) | (NULL) | Using temporary |
  | 1      | PRIMARY      | finance_statement | ALL   | (NULL)        | (NULL)     | (NULL)  | (NULL) | 5664   | (NULL)          |
  | 2      | UNION        | pos_order         | index | (NULL)        | outTradeNo | 258     | (NULL) | 4872   | Using index     |

- `select_type` (JSON name: none)

  The type of [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html), which can be any of those shown in the following table. A JSON-formatted `EXPLAIN` exposes the `SELECT` type as a property of a`query_block`, unless it is `SIMPLE` or `PRIMARY`. The JSON names (where applicable) are also shown in the table.

  | `select_type` Value                                          | JSON Name                    | Meaning                                                      |
  | ------------------------------------------------------------ | ---------------------------- | ------------------------------------------------------------ |
  | `SIMPLE`                                                     | None                         | Simple [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) (not using [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html) or subqueries) |
  | `PRIMARY`                                                    | None                         | Outermost [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) 什么是outermost select |
  | [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html) | None                         | Second or later [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statement in a [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html) |
  | `DEPENDENT UNION`                                            | `dependent` (`true`)         | Second or later [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statement in a [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html), dependent on outer query |
  | `UNION RESULT`                                               | `union_result`               | Result of a [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html). |
  | `SUBQUERY`                                                   | None                         | First [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) in subquery |
  | `DEPENDENT SUBQUERY`                                         | `dependent` (`true`)         | First [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) in subquery, dependent on outer query |
  | `DERIVED`                                                    | None                         | Derived table                                                |
  | `MATERIALIZED`                                               | `materialized_from_subquery` | Materialized subquery 物化的子查询                           |
  | `UNCACHEABLE SUBQUERY`                                       | `cacheable` (`false`)        | A subquery for which the result cannot be cached and must be re-evaluated for each row of the outer query |
  | `UNCACHEABLE UNION`                                          | `cacheable` (`false`)        | The second or later select in a [`UNION`](https://dev.mysql.com/doc/refman/5.6/en/union.html) that belongs to an uncacheable subquery (see `UNCACHEABLE SUBQUERY`) |

  

  `DEPENDENT` typically signifies the use of a correlated subquery. See [Section 13.2.10.7, “Correlated Subqueries”](https://dev.mysql.com/doc/refman/5.6/en/correlated-subqueries.html).

  `DEPENDENT SUBQUERY` evaluation differs from `UNCACHEABLE SUBQUERY` evaluation. For `DEPENDENT SUBQUERY`, the subquery is re-evaluated only once for each set of different values of the variables from its outer context. For `UNCACHEABLE SUBQUERY`, the subquery is re-evaluated for each row of the outer context.

  *Cacheability of subqueries differs from caching of query results in the query cache (which is described in [Section 8.10.3.1, “How the Query Cache Operates”](https://dev.mysql.com/doc/refman/5.6/en/query-cache-operation.html)). Subquery caching occurs during query execution, whereas the query cache is used to store results only after query execution finishes.*

  When you specify `FORMAT=JSON` with `EXPLAIN`, the output has no single property directly equivalent to `select_type`; the `query_block` property corresponds to a given `SELECT`. Properties equivalent to most of the `SELECT` subquery types just shown are available (an example being`materialized_from_subquery` for `MATERIALIZED`), and are displayed when appropriate. There are no JSON equivalents for `SIMPLE` or `PRIMARY`.

- `table` (JSON name: `table_name`)

  The name of the table to which the row of output refers. This can also be one of the following values:

  - `<union*M*,*N*>`: The row refers to the union of the rows with `id` values of *M* and *N*.
  - `<derived*N*>`: The row refers to the derived table result for the row with an `id` value of *N*. A derived table may result, for example, from a subquery in the `FROM` clause.
  - `<subquery*N*>`: The row refers to the result of a materialized subquery for the row with an `id` value of *N*. See [Section 8.2.2.2, “Optimizing Subqueries with Materialization”](https://dev.mysql.com/doc/refman/5.6/en/subquery-materialization.html).

- `partitions` (JSON name: `partitions`)

  The partitions from which records would be matched by the query. This column is displayed only if the `PARTITIONS` keyword is used. The value is `NULL` for nonpartitioned tables. See [Section 19.3.5, “Obtaining Information About Partitions”](https://dev.mysql.com/doc/refman/5.6/en/partitioning-info.html).

- `type` (JSON name: `access_type`)

  The join type. For descriptions of the different types, see [`EXPLAIN` Join Types](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-join-types).

- `possible_keys` (JSON name: `possible_keys`)

  The `possible_keys` column indicates the indexes from which MySQL can choose to find the rows in this table. Note that this column is totally independent of the order of the tables as displayed in the output from [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html). That means that some of the keys in `possible_keys` might not be usable in practice with the generated table order.

  If this column is `NULL` (or undefined in JSON-formatted output), there are no relevant indexes. In this case, you may be able to improve the performance of your query by examining the `WHERE` clause to check whether it refers to some column or columns that would be suitable for indexing. If so, create an appropriate index and check the query with [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) again. See [Section 13.1.7, “ALTER TABLE Syntax”](https://dev.mysql.com/doc/refman/5.6/en/alter-table.html).

  To see what indexes a table has, use `SHOW INDEX FROM *tbl_name*`.

- `key` (JSON name: `key`)

  The `key` column indicates the key (index) that MySQL actually decided to use. If MySQL decides to use one of the `possible_keys` indexes to look up rows, that index is listed as the key value.

  It is possible that `key` will name an index that is not present in the `possible_keys` value. This can happen if none of the `possible_keys` indexes are suitable for looking up rows, but all the columns selected by the query are columns of some other index. That is, the named index covers the selected columns, so although it is not used to determine which rows to retrieve, an index scan is more efficient than a data row scan.

  For `InnoDB`, a secondary index might cover the selected columns even if the query also selects the primary key because `InnoDB` stores the primary key value with each secondary index. If `key` is `NULL`, MySQL found no index to use for executing the query more efficiently.

  To force MySQL to use or ignore an index listed in the `possible_keys` column, use `FORCE INDEX`, `USE INDEX`, or `IGNORE INDEX` in your query. See [Section 8.9.3, “Index Hints”](https://dev.mysql.com/doc/refman/5.6/en/index-hints.html).

  For `MyISAM` and `NDB` tables, running [`ANALYZE TABLE`](https://dev.mysql.com/doc/refman/5.6/en/analyze-table.html) helps the optimizer choose better indexes. For `NDB` tables, this also improves performance of distributed pushed-down joins. For `MyISAM` tables, [**myisamchk --analyze**](https://dev.mysql.com/doc/refman/5.6/en/myisamchk.html) does the same as [`ANALYZE TABLE`](https://dev.mysql.com/doc/refman/5.6/en/analyze-table.html). See [Section 7.6, “MyISAM Table Maintenance and Crash Recovery”](https://dev.mysql.com/doc/refman/5.6/en/myisam-table-maintenance.html).

- `key_len` (JSON name: `key_length`)

  The `key_len` column indicates the length of the key that MySQL decided to use. The value of `key_len` enables you to determine how many parts of a multiple-part key MySQL actually uses. If the `key` column says `NULL`, the `len_len` column also says `NULL`.

  Due to the key storage format, the key length is one greater for a column that can be `NULL` than for a `NOT NULL` column.

- `ref` (JSON name: `ref`)

  The `ref` column shows which columns or constants are compared to the index named in the `key` column to select rows from the table.(ref 说明哪一列或常量和索引进行比较)

  If the value is `func`, the value used is the result of some function. To see which function, use [`SHOW WARNINGS`](https://dev.mysql.com/doc/refman/5.6/en/show-warnings.html) following [`EXPLAIN EXTENDED`](https://dev.mysql.com/doc/refman/5.6/en/explain-extended.html) to see the extended [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output. The function might actually be an operator such as an arithmetic operator.

- `rows` (JSON name: `rows`)

  The `rows` column indicates the number of rows MySQL believes it must examine to execute the query.

  For [`InnoDB`](https://dev.mysql.com/doc/refman/5.6/en/innodb-storage-engine.html) tables, this number is an estimate, and may not always be exact.

- `filtered` (JSON name: `filtered`)

  The `filtered` column indicates an estimated percentage of table rows that will be filtered by the table condition. The maximum value is 100, which means no filtering of rows occurred. Values decreasing from 100 indicate increasing amounts of filtering. `rows` shows the estimated number of rows examined and `rows` × `filtered` shows the number of rows that will be joined with the following table. For example, if `rows` is 1000 and `filtered` is 50.00 (50%), the number of rows to be joined with the following table is 1000 × 50% = 500. This column is displayed if you use [`EXPLAIN EXTENDED`](https://dev.mysql.com/doc/refman/5.6/en/explain-extended.html).

- `Extra` (JSON name: none)

  This column contains additional information about how MySQL resolves the query. For descriptions of the different values, see [`EXPLAIN` Extra Information](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#explain-extra-information).

  There is no single JSON property corresponding to the `Extra` column; however, values that can occur in this column are exposed as JSON properties, or as the text of the `message` property.

#### EXPLAIN Join Types

**The `type` column of [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output describes how tables are joined. In JSON-formatted output, these are found as values of the `access_type` property. The following list describes the join types, ordered from the best type to the worst:**

- [`system`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_system)

  The table has only one row (= system table). This is a special case of the [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) join type.

- [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const)

  The table has at most one matching row, which is read at the start of the query. Because there is only one row, values from the column in this row can be regarded as constants by the rest of the optimizer. [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) tables are very fast because they are read only once.

  [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) is used when you compare all parts of a `PRIMARY KEY` or `UNIQUE` index to constant values. In the following queries, *tbl_name* can be used as a [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) table:

  ```sql
  SELECT * FROM tbl_name WHERE primary_key=1;
  
  SELECT * FROM tbl_name
    WHERE primary_key_part1=1 AND primary_key_part2=2;
  ```

- [`eq_ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_eq_ref)

  One row is read from this table for each combination of rows from the previous tables. Other than the [`system`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_system) and [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) types, this is the best possible join type. It is used when all parts of an index are used by the join and the index is a `PRIMARY KEY` or `UNIQUE NOT NULL` index.

  [`eq_ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_eq_ref) can be used for indexed columns that are compared using the `=` operator. The comparison value can be a constant or an expression that uses columns from tables that are read before this table. In the following examples, MySQL can use an [`eq_ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_eq_ref) join to process *ref_table*:

  ```sql
  SELECT * FROM ref_table,other_table
    WHERE ref_table.key_column=other_table.column;
  
  SELECT * FROM ref_table,other_table
    WHERE ref_table.key_column_part1=other_table.column
    AND ref_table.key_column_part2=1;
  ```

- [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref)

  All rows with matching index values are read from this table for each combination of rows from the previous tables. [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref) is used if the join uses only a leftmost prefix of the key or if the key is not a `PRIMARY KEY` or `UNIQUE` index (in other words, if the join cannot select a single row based on the key value). If the key that is used matches only a few rows, this is a good join type.

  [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref) can be used for indexed columns that are compared using the `=` or `<=>` operator. In the following examples, MySQL can use a [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref) join to process*ref_table*:

  ```sql
  SELECT * FROM ref_table WHERE key_column=expr;
  
  SELECT * FROM ref_table,other_table
    WHERE ref_table.key_column=other_table.column;
  
  SELECT * FROM ref_table,other_table
    WHERE ref_table.key_column_part1=other_table.column
    AND ref_table.key_column_part2=1;
  ```

- [`fulltext`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_fulltext)

  The join is performed using a `FULLTEXT` index.

- [`ref_or_null`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref_or_null)

  This join type is like [`ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref), but with the addition that MySQL does an extra search for rows that contain `NULL` values. This join type optimization is used most often in resolving subqueries. In the following examples, MySQL can use a [`ref_or_null`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_ref_or_null) join to process *ref_table*:

  ```sql
  SELECT * FROM ref_table
    WHERE key_column=expr OR key_column IS NULL;
  ```

  See [Section 8.2.1.12, “IS NULL Optimization”](https://dev.mysql.com/doc/refman/5.6/en/is-null-optimization.html).

- [`index_merge`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index_merge)

  This join type indicates that the Index Merge optimization is used. In this case, the `key` column in the output row contains a list of indexes used, and`key_len` contains a list of the longest key parts for the indexes used. For more information, see [Section 8.2.1.3, “Index Merge Optimization”](https://dev.mysql.com/doc/refman/5.6/en/index-merge-optimization.html).

- [`unique_subquery`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_unique_subquery)

  This type replaces [`eq_ref`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_eq_ref) for some `IN` subqueries of the following form:

  ```sql
  value IN (SELECT primary_key FROM single_table WHERE some_expr)
  ```

  [`unique_subquery`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_unique_subquery) is just an index lookup function that replaces the subquery completely for better efficiency.

- [`index_subquery`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index_subquery)

  This join type is similar to [`unique_subquery`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_unique_subquery). It replaces `IN` subqueries, but it works for nonunique indexes in subqueries of the following form:

  ```sql
  value IN (SELECT key_column FROM single_table WHERE some_expr)
  ```

- [`range`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_range)

  Only rows that are in a given range are retrieved, using an index to select the rows. The `key` column in the output row indicates which index is used. The `key_len` contains the longest key part that was used. The `ref` column is `NULL` for this type.

  [`range`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_range) can be used when a key column is compared to a constant using any of the [`=`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_equal), [`<>`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_not-equal), [`>`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_greater-than), [`>=`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_greater-than-or-equal), [`<`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_less-than), [`<=`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_less-than-or-equal), [`IS NULL`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_is-null), [`<=>`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_equal-to), [`BETWEEN`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_between), [`LIKE`](https://dev.mysql.com/doc/refman/5.6/en/string-comparison-functions.html#operator_like), or [`IN()`](https://dev.mysql.com/doc/refman/5.6/en/comparison-operators.html#operator_in) operators:

  ```sql
  SELECT * FROM tbl_name
    WHERE key_column = 10;
  
  SELECT * FROM tbl_name
    WHERE key_column BETWEEN 10 and 20;
  
  SELECT * FROM tbl_name
    WHERE key_column IN (10,20,30);
  
  SELECT * FROM tbl_name
    WHERE key_part1 = 10 AND key_part2 IN (10,20,30);
  ```

- [`index`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index)(索引扫描, 扫描整个索引树)

  The `index` join type is the same as [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all), except that the index tree is scanned. This occurs two ways:

  - If the index is a covering index for the queries and can be used to satisfy all data required from the table, only the index tree is scanned. In this case, the `Extra` column says `Using index`. An index-only scan usually is faster than [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all) because the size of the index usually is smaller than the table data.
  - A full table scan is performed using reads from the index to look up data rows in index order. `Uses index` does not appear in the `Extra` column.（所选数据没有被cover index覆盖到, cluster index)

  MySQL can use this join type when the query uses only columns that are part of a single index.

- [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all)（全表扫描)

  每处理前一个表的一行，都要扫描本表（前一个表？？？ select id在此之前的）

  A full table scan is done for each combination of rows from the previous tables. This is normally not good if the table is the first table not marked [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const), and usually *very* bad in all other cases. Normally, you can avoid [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all) by adding indexes that enable row retrieval from the table based on constant values or column values from earlier tables.

#### EXPLAIN Extra Information

The `Extra` column of [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output contains additional information about how MySQL resolves the query. The following list explains the values that can appear in this column. Each item also indicates for JSON-formatted output which property displays the `Extra` value. For some of these, there is a specific property. The others display as the text of the `message` property.

<font color="red">If you want to make your queries as fast as possible, look out for `Extra` column values of `Using filesort` and `Using temporary`, or, in JSON-formatted `EXPLAIN` output, for `using_filesort` and `using_temporary_table` properties equal to `true`</font>

- `Child of '*table*' pushed join@1` (JSON: `message` text)

  This table is referenced as the child of *table* in a join that can be pushed down to the NDB kernel. Applies only in NDB Cluster, when pushed-down joins are enabled. See the description of the [`ndb_join_pushdown`](https://dev.mysql.com/doc/refman/5.6/en/mysql-cluster-options-variables.html#sysvar_ndb_join_pushdown) server system variable for more information and examples.

- `const row not found` (JSON property: `const_row_not_found`)

  For a query such as `SELECT ... FROM *tbl_name*`, the table was empty.

- `Deleting all rows` (JSON property: `message`)

  For [`DELETE`](https://dev.mysql.com/doc/refman/5.6/en/delete.html), some storage engines (such as [`MyISAM`](https://dev.mysql.com/doc/refman/5.6/en/myisam-storage-engine.html)) support a handler method that removes all table rows in a simple and fast way. This `Extra` value is displayed if the engine uses this optimization.

- `Distinct` (JSON property: `distinct`)

  MySQL is looking for distinct values, so it stops searching for more rows for the current row combination after it has found the first matching row.

- `FirstMatch(*tbl_name*)` (JSON property: `first_match`)

  The semijoin FirstMatch join shortcutting strategy is used for *tbl_name*.

- `Full scan on NULL key` (JSON property: `message`)

  This occurs for subquery optimization as a fallback strategy when the optimizer cannot use an index-lookup access method.

- `Impossible HAVING` (JSON property: `message`)

  The `HAVING` clause is always false and cannot select any rows.

- `Impossible WHERE` (JSON property: `message`)

  The `WHERE` clause is always false and cannot select any rows.

- `Impossible WHERE noticed after reading const tables` (JSON property: `message`)

  MySQL has read all [`const`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_const) (and [`system`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_system)) tables and notice that the `WHERE` clause is always false.

- `LooseScan(*m*..*n*)` (JSON property: `message`)

  The semijoin LooseScan strategy is used. *m* and *n* are key part numbers.

- `No matching min/max row` (JSON property: `message`)

  No row satisfies the condition for a query such as `SELECT MIN(...) FROM ... WHERE *condition*`.

- `no matching row in const table` (JSON property: `message`)

  For a query with a join, there was an empty table or a table with no rows satisfying a unique index condition.

- `No matching rows after partition pruning` (JSON property: `message`)

  For [`DELETE`](https://dev.mysql.com/doc/refman/5.6/en/delete.html) or [`UPDATE`](https://dev.mysql.com/doc/refman/5.6/en/update.html), the optimizer found nothing to delete or update after partition pruning. It is similar in meaning to `Impossible WHERE` for [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html)statements.

- `No tables used` (JSON property: `message`)

  The query has no `FROM` clause, or has a `FROM DUAL` clause.

  For [`INSERT`](https://dev.mysql.com/doc/refman/5.6/en/insert.html) or [`REPLACE`](https://dev.mysql.com/doc/refman/5.6/en/replace.html) statements, [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) displays this value when there is no [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) part. For example, it appears for `EXPLAIN INSERT INTO t VALUES(10)` because that is equivalent to `EXPLAIN INSERT INTO t SELECT 10 FROM DUAL`.

- `Not exists` (JSON property: `message`)

  MySQL was able to do a `LEFT JOIN` optimization on the query and does not examine more rows in this table for the previous row combination after it finds one row that matches the `LEFT JOIN` criteria. Here is an example of the type of query that can be optimized this way:

  ```sql
  SELECT * FROM t1 LEFT JOIN t2 ON t1.id=t2.id
    WHERE t2.id IS NULL;
  ```

  Assume that `t2.id` is defined as `NOT NULL`. In this case, MySQL scans `t1` and looks up the rows in `t2` using the values of `t1.id`. If MySQL finds a matching row in `t2`, it knows that `t2.id` can never be `NULL`, and does not scan through the rest of the rows in `t2` that have the same `id` value. In other words, for each row in `t1`, MySQL needs to do only a single lookup in `t2`, regardless of how many rows actually match in `t2`.

- `Range checked for each record (index map: *N*)` (JSON property: `message`)

  MySQL found no good index to use, but found that some of indexes might be used after column values from preceding tables are known. For each row combination in the preceding tables, MySQL checks whether it is possible to use a [`range`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_range) or [`index_merge`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index_merge) access method to retrieve rows. This is not very fast, but is faster than performing a join with no index at all. The applicability criteria are as described in [Section 8.2.1.2, “Range Optimization”](https://dev.mysql.com/doc/refman/5.6/en/range-optimization.html), and[Section 8.2.1.3, “Index Merge Optimization”](https://dev.mysql.com/doc/refman/5.6/en/index-merge-optimization.html), with the exception that all column values for the preceding table are known and considered to be constants.

  Indexes are numbered beginning with 1, in the same order as shown by [`SHOW INDEX`](https://dev.mysql.com/doc/refman/5.6/en/show-index.html) for the table. The index map value *N* is a bitmask value that indicates which indexes are candidates. For example, a value of `0x19` (binary 11001) means that indexes 1, 4, and 5 will be considered.

- `Scanned *N* databases` (JSON property: `message`)

  This indicates how many directory scans the server performs when processing a query for `INFORMATION_SCHEMA` tables, as described in [Section 8.2.3, “Optimizing INFORMATION_SCHEMA Queries”](https://dev.mysql.com/doc/refman/5.6/en/information-schema-optimization.html). The value of *N* can be 0, 1, or `all`.

- `Select tables optimized away` (JSON property: `message`)

  The optimizer determined 1) that at most one row should be returned, and 2) that to produce this row, a deterministic set of rows must be read. When the rows to be read can be read during the optimization phase (for example, by reading index rows), there is no need to read any tables during query execution.

  The first condition is fulfilled when the query is implicitly grouped (contains an aggregate function but no `GROUP BY` clause). The second condition is fulfilled when one row lookup is performed per index used. The number of indexes read determines the number of rows to read.

  Consider the following implicitly grouped query:

  ```sql
  SELECT MIN(c1), MIN(c2) FROM t1;
  ```

  Suppose that `MIN(c1)` can be retrieved by reading one index row and `MIN(c2)` can be retrieved by reading one row from a different index. That is, for each column `c1` and `c2`, there exists an index where the column is the first column of the index. In this case, one row is returned, produced by reading two deterministic rows.

  This `Extra` value does not occur if the rows to read are not deterministic. Consider this query:

  ```sql
  SELECT MIN(c2) FROM t1 WHERE c1 <= 10;
  ```

  Suppose that `(c1, c2)` is a covering index. Using this index, all rows with `c1 <= 10` must be scanned to find the minimum `c2` value. By contrast, consider this query:

  ```sql
  SELECT MIN(c2) FROM t1 WHERE c1 = 10;
  ```

  In this case, the first index row with `c1 = 10` contains the minimum `c2` value. Only one row must be read to produce the returned row.

  For storage engines that maintain an exact row count per table (such as `MyISAM`, but not `InnoDB`), this `Extra` value can occur for `COUNT(*)` queries for which the `WHERE` clause is missing or always true and there is no `GROUP BY` clause. (This is an instance of an implicitly grouped query where the storage engine influences whether a deterministic number of rows can be read.)

- `Skip_open_table`, `Open_frm_only`, `Open_full_table` (JSON property: `message`)

  These values indicate file-opening optimizations that apply to queries for `INFORMATION_SCHEMA` tables, as described in [Section 8.2.3, “Optimizing INFORMATION_SCHEMA Queries”](https://dev.mysql.com/doc/refman/5.6/en/information-schema-optimization.html).

  - `Skip_open_table`: Table files do not need to be opened. The information has already become available within the query by scanning the database directory.
  - `Open_frm_only`: Only the table's `.frm` file need be opened.
  - `Open_full_table`: The unoptimized information lookup. The `.frm`, `.MYD`, and `.MYI` files must be opened.

- `Start temporary`, `End temporary` (JSON property: `message`)

  This indicates temporary table use for the semijoin Duplicate Weedout strategy.

- `unique row not found` (JSON property: `message`)

  For a query such as `SELECT ... FROM *tbl_name*`, no rows satisfy the condition for a `UNIQUE` index or `PRIMARY KEY` on the table.

- `Using filesort` (JSON property: `using_filesort`)

  MySQL must do an extra pass to find out how to retrieve the rows in sorted order. The sort is done by going through all rows according to the join type and storing the sort key and pointer to the row for all rows that match the `WHERE` clause. The keys then are sorted and the rows are retrieved in sorted order. See [Section 8.2.1.13, “ORDER BY Optimization”](https://dev.mysql.com/doc/refman/5.6/en/order-by-optimization.html).

- `Using index` (JSON property: `using_index`)

  <font color="red">The column information is retrieved from the table using only information in the index tree without having to do an additional seek to read the actual row. This strategy can be used when the query uses only columns that are part of a single index.</font>

  For `InnoDB` tables that have a user-defined clustered index, that index can be used even when `Using index` is absent from the `Extra` column. This is the case if `type` is [`index`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index) and `key` is `PRIMARY`.

  

- `Using index condition` (JSON property: `using_index_condition`)

  Tables are read by accessing index tuples and testing them first to determine whether to read full table rows. In this way, index information is used to defer (“push down”) reading full table rows unless it is necessary. See [Section 8.2.1.5, “Index Condition Pushdown Optimization”](https://dev.mysql.com/doc/refman/5.6/en/index-condition-pushdown-optimization.html).

- `Using index for group-by` (JSON property: `using_index_for_group_by`)

  Similar to the `Using index` table access method, `Using index for group-by` indicates that MySQL found an index that can be used to retrieve all columns of a `GROUP BY` or `DISTINCT` query without any extra disk access to the actual table. Additionally, the index is used in the most efficient way so that for each group, only a few index entries are read. For details, see [Section 8.2.1.14, “GROUP BY Optimization”](https://dev.mysql.com/doc/refman/5.6/en/group-by-optimization.html).

- `Using join buffer (Block Nested Loop)`, `Using join buffer (Batched Key Access)` (JSON property: `using_join_buffer`)

  Tables from earlier joins are read in portions into the join buffer, and then their rows are used from the buffer to perform the join with the current table.`(Block Nested Loop)` indicates use of the Block Nested-Loop algorithm and `(Batched Key Access)` indicates use of the Batched Key Access algorithm. That is, the keys from the table on the preceding line of the [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output will be buffered, and the matching rows will be fetched in batches from the table represented by the line in which `Using join buffer` appears.

  In JSON-formatted output, the value of `using_join_buffer` is always either one of `Block Nested Loop` or `Batched Key Access`.

- `Using MRR` (JSON property: `message`)

  Tables are read using the Multi-Range Read optimization strategy. See [Section 8.2.1.10, “Multi-Range Read Optimization”](https://dev.mysql.com/doc/refman/5.6/en/mrr-optimization.html).

- `Using sort_union(...)`, `Using union(...)`, `Using intersect(...)` (JSON property: `message`)

  These indicate the particular algorithm showing how index scans are merged for the [`index_merge`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index_merge) join type. See [Section 8.2.1.3, “Index Merge Optimization”](https://dev.mysql.com/doc/refman/5.6/en/index-merge-optimization.html).

- `Using temporary` (JSON property: `using_temporary_table`)

  <font color="red"> To resolve the query, MySQL needs to create a temporary table to hold the result. This typically happens if the query contains `GROUP BY` and `ORDER BY`clauses that list columns differently.</font>

- `Using where` (JSON property: `attached_condition`)

  <font color="red">A `WHERE` clause is used to restrict which rows to match against the next table or send to the client. Unless you specifically intend to fetch or examine all rows from the table, you may have something wrong in your query if the `Extra` value is not `Using where` and the table join type is [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all) or [`index`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_index).</font>

  `Using where` has no direct counterpart in JSON-formatted output; the `attached_condition` property contains any `WHERE` condition used.

- `Using where with pushed condition` (JSON property: `message`)

  This item applies to [`NDB`](https://dev.mysql.com/doc/refman/5.6/en/mysql-cluster.html) tables *only*. It means that NDB Cluster is using the Condition Pushdown optimization to improve the efficiency of a direct comparison between a nonindexed column and a constant. In such cases, the condition is “pushed down” to the cluster's data nodes and is evaluated on all data nodes simultaneously. This eliminates the need to send nonmatching rows over the network, and can speed up such queries by a factor of 5 to 10 times over cases where Condition Pushdown could be but is not used. For more information, see [Section 8.2.1.4, “Engine Condition Pushdown Optimization”](https://dev.mysql.com/doc/refman/5.6/en/condition-pushdown-optimization.html).

#### EXPLAIN Output Interpretation

You can get a good indication of how good a join is by taking the product of the values in the `rows` column of the [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) output. This should tell you roughly how many rows MySQL must examine to execute the query. If you restrict queries with the [`max_join_size`](https://dev.mysql.com/doc/refman/5.6/en/server-system-variables.html#sysvar_max_join_size) system variable, this row product also is used to determine which multiple-table [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statements to execute and which to abort. See [Section 5.1.1, “Configuring the Server”](https://dev.mysql.com/doc/refman/5.6/en/server-configuration.html).

The following example shows how a multiple-table join can be optimized progressively based on the information provided by [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html).

Suppose that you have the [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statement shown here and that you plan to examine it using [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html):

```sql
EXPLAIN SELECT tt.TicketNumber, tt.TimeIn,
               tt.ProjectReference, tt.EstimatedShipDate,
               tt.ActualShipDate, tt.ClientID,
               tt.ServiceCodes, tt.RepetitiveID,
               tt.CurrentProcess, tt.CurrentDPPerson,
               tt.RecordVolume, tt.DPPrinted, et.COUNTRY,
               et_1.COUNTRY, do.CUSTNAME
        FROM tt, et, et AS et_1, do
        WHERE tt.SubmitTime IS NULL
          AND tt.ActualPC = et.EMPLOYID
          AND tt.AssignedPC = et_1.EMPLOYID
          AND tt.ClientID = do.CUSTNMBR;
```

For this example, make the following assumptions:

- The columns being compared have been declared as follows.

  | Table | Column       | Data Type  |
  | ----- | ------------ | ---------- |
  | `tt`  | `ActualPC`   | `CHAR(10)` |
  | `tt`  | `AssignedPC` | `CHAR(10)` |
  | `tt`  | `ClientID`   | `CHAR(10)` |
  | `et`  | `EMPLOYID`   | `CHAR(15)` |
  | `do`  | `CUSTNMBR`   | `CHAR(15)` |

- The tables have the following indexes.

  | Table | Index                    |
  | ----- | ------------------------ |
  | `tt`  | `ActualPC`               |
  | `tt`  | `AssignedPC`             |
  | `tt`  | `ClientID`               |
  | `et`  | `EMPLOYID` (primary key) |
  | `do`  | `CUSTNMBR` (primary key) |

- The `tt.ActualPC` values are not evenly distributed.

Initially, before any optimizations have been performed, the [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) statement produces the following information:

```none
table type possible_keys key  key_len ref  rows  Extra
et    ALL  PRIMARY       NULL NULL    NULL 74
do    ALL  PRIMARY       NULL NULL    NULL 2135
et_1  ALL  PRIMARY       NULL NULL    NULL 74
tt    ALL  AssignedPC,   NULL NULL    NULL 3872
           ClientID,
           ActualPC
      Range checked for each record (index map: 0x23)
```

Because `type` is [`ALL`](https://dev.mysql.com/doc/refman/5.6/en/explain-output.html#jointype_all) for each table, this output indicates that MySQL is generating a Cartesian product of all the tables; that is, every combination of rows. This takes quite a long time, because the product of the number of rows in each table must be examined. For the case at hand, this product is 74 × 2135 × 74 × 3872 = 45,268,558,720 rows. If the tables were bigger, you can only imagine how long it would take.

One problem here is that MySQL can use indexes on columns more efficiently if they are declared as the same type and size. In this context, [`VARCHAR`](https://dev.mysql.com/doc/refman/5.6/en/char.html) and [`CHAR`](https://dev.mysql.com/doc/refman/5.6/en/char.html)are considered the same if they are declared as the same size. `tt.ActualPC` is declared as `CHAR(10)` and `et.EMPLOYID` is `CHAR(15)`, so there is a length mismatch.

To fix this disparity between column lengths, use [`ALTER TABLE`](https://dev.mysql.com/doc/refman/5.6/en/alter-table.html) to lengthen `ActualPC` from 10 characters to 15 characters:

```sql
mysql> ALTER TABLE tt MODIFY ActualPC VARCHAR(15);
```

Now `tt.ActualPC` and `et.EMPLOYID` are both `VARCHAR(15)`. Executing the [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) statement again produces this result:

```none
table type   possible_keys key     key_len ref         rows    Extra
tt    ALL    AssignedPC,   NULL    NULL    NULL        3872    Using
             ClientID,                                         where
             ActualPC
do    ALL    PRIMARY       NULL    NULL    NULL        2135
      Range checked for each record (index map: 0x1)
et_1  ALL    PRIMARY       NULL    NULL    NULL        74
      Range checked for each record (index map: 0x1)
et    eq_ref PRIMARY       PRIMARY 15      tt.ActualPC 1
```

This is not perfect, but is much better: The product of the `rows` values is less by a factor of 74. This version executes in a couple of seconds.

A second alteration can be made to eliminate the column length mismatches for the `tt.AssignedPC = et_1.EMPLOYID` and `tt.ClientID = do.CUSTNMBR`comparisons:

```sql
mysql> ALTER TABLE tt MODIFY AssignedPC VARCHAR(15),
                      MODIFY ClientID   VARCHAR(15);
```

After that modification, [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) produces the output shown here:

```none
table type   possible_keys key      key_len ref           rows Extra
et    ALL    PRIMARY       NULL     NULL    NULL          74
tt    ref    AssignedPC,   ActualPC 15      et.EMPLOYID   52   Using
             ClientID,                                         where
             ActualPC
et_1  eq_ref PRIMARY       PRIMARY  15      tt.AssignedPC 1
do    eq_ref PRIMARY       PRIMARY  15      tt.ClientID   1
```

At this point, the query is optimized almost as well as possible. The remaining problem is that, by default, MySQL assumes that values in the `tt.ActualPC`column are evenly distributed, and that is not the case for the `tt` table. Fortunately, it is easy to tell MySQL to analyze the key distribution:

```sql
mysql> ANALYZE TABLE tt;
```

With the additional index information, the join is perfect and [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) produces this result:

```none
table type   possible_keys key     key_len ref           rows Extra
tt    ALL    AssignedPC    NULL    NULL    NULL          3872 Using
             ClientID,                                        where
             ActualPC
et    eq_ref PRIMARY       PRIMARY 15      tt.ActualPC   1
et_1  eq_ref PRIMARY       PRIMARY 15      tt.AssignedPC 1
do    eq_ref PRIMARY       PRIMARY 15      tt.ClientID   1
```

The `rows` column in the output from [`EXPLAIN`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) is an educated guess from the MySQL join optimizer. Check whether the numbers are even close to the truth by comparing the `rows` product with the actual number of rows that the query returns. If the numbers are quite different, you might get better performance by using `STRAIGHT_JOIN` in your [`SELECT`](https://dev.mysql.com/doc/refman/5.6/en/select.html) statement and trying to list the tables in a different order in the `FROM` clause. (However, `STRAIGHT_JOIN` may prevent indexes from being used because it disables semijoin transformations. See [Section 8.2.2.1, “Optimizing Subqueries with Semijoin Transformations”](https://dev.mysql.com/doc/refman/5.6/en/semijoins.html).)

It is possible in some cases to execute statements that modify data when [`EXPLAIN SELECT`](https://dev.mysql.com/doc/refman/5.6/en/explain.html) is used with a subquery; for more information, see 