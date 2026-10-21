# 分布式数据库缺陷模式（30 条抽样，26 条确认真实缺陷）

样本：cockroach / tikv / tidb / vitess / yugabyte / scylladb 的 bug 标签、带关联 PR 关闭的 issue（rocksdb 没有抽到样本，#34212 是 cockroach 通过升级 RocksDB 修的）。下面只归纳 issue、评论和 PR 里写明的机制。不纳入模式的条目：#129464、#131695（测试本身的问题），#170697（作为重复关闭，改的是测试），#11228（结论是“只是警告”）。

## 1. 领导权/成员变更时残留旧状态

**机制**：leader、lease 或成员配置切换时，旧任期留下的请求或状态没有被清掉，新任期把它当成有效的来处理。CockroachDB #104709：一个 conf change 在旧 leaseholder 上评估完成，lease 随后转走，新 leaseholder 又提交了另一个 conf change；raft 把这个过时的提案悄悄换成空条目，提案和它持有的 latch 永远不会释放，熔断器跳闸，副本不可用。TiKV #18453：follower 在别处已经选出新 leader 后，没有重置 transfer-leader 预热状态，还对旧 leader 的过期请求做了应答，结果在内存引擎（IME）预热完成前就发起选举，滚动重启时 P999 延迟涨到 1 秒。CockroachDB #120395 是反过来的情况：DistSender 熔断器在 lease 或 quorum 短暂丢失时就取消进行中的写请求，而写请求不能自动重试，只能以 ambiguous result 返回给客户端。

**测试思路**：前提是 3 副本 range 持续有写入。故障/时序：在提案“已评估、未提交”的窗口里转移 lease，并让新 leader 提交一个冲突的成员变更；或者在一次 transfer-leader 进行中再发一次，并让第三个节点当选；或者让 lease 丢失 5–10 秒。预期：旧提案以明确的失败或 ambiguous 结束，latch 被释放；follower 只响应当前 leader 的请求；短于选举超时加 lease 间隔的抖动不会导致写请求被取消。

**支撑**：https://github.com/cockroachdb/cockroach/issues/104709 、https://github.com/tikv/tikv/issues/18453 、https://github.com/cockroachdb/cockroach/issues/120395

## 2. 异步组件之间循环等待或消息顺序颠倒（死锁/挂起）

**机制**：多个后台任务、RPC 或回调之间存在隐含的先后依赖，某个时序一出现就会形成环，或者消息先于注册到达。RocksDB ingest（CockroachDB #34212）：ingest 等 memtable flush，flush 因 L0 过大等 compaction，compaction 又等 ingest。Scylla #10950：服务端把 RPC 流注册放到后台执行，客户端已经发出带 stream id 的数据，服务端反序列化时找不到这个流，抛出异常，repair 挂住 2 小时。TiKV #11549：`poll_future_notify` 在 poll 过程中被立刻唤醒时会重入加锁，PD worker 死锁，节点被判定为 down。Scylla #8790：关闭时 `apply_in_memory` 没有持有 gate，写路径和关闭流程发生竞态。

**测试思路**：前提是有一条依赖后台任务的路径（ingest、repair 流、future 唤醒、关闭流程）。时序：用很小的 chunk 一次产生几十个 SST；在流协商和第一条数据之间给服务端注入延迟；让 future 在 poll 内同步唤醒；在 16 个以上 shard、写入进行中触发关闭。预期：在有界时间内完成或明确报错，没有永久挂起；用看门狗加 goroutine/线程栈采样检查是否出现等待环。

**支撑**：https://github.com/cockroachdb/cockroach/issues/34212 、https://github.com/scylladb/scylladb/issues/10950 、https://github.com/tikv/tikv/issues/11549 、https://github.com/scylladb/scylladb/issues/8790

## 3. 在线 schema 变更时缓存或租约没有失效/释放

**机制**：从 schema 派生出来的缓存对象、元数据租约，没有跟着 schema 版本一起更新或释放。Scylla #10026：物化视图在 `view_info` 里缓存的 `select_statement` 在基表 schema 变化后没有重新生成。按指针比较列定义得出“不是同一列”的结论，取到错误的值，节点段错误。nyh 后来确认，不需要任何并发，ALTER 基表（哪怕只改注释）再写一行就能复现。CockroachDB #76927：不带 sink 的 changefeed 在规划阶段拿到 descriptor lease 后没有释放，之后相关的 GRANT/ALTER 要等 5 分钟 lease 过期才能执行，看起来像整个集群被锁住。YugabyteDB #9970：`ADD COLUMN ... DEFAULT 1 NOT NULL` 在已有数据上直接成功，没有回填，也没有报错，而拆成两步执行会报错（根因只部分说明）。

**测试思路**：前提是有带过滤条件（基表普通列成为视图键）的视图、长时间运行的 changefeed，或已有数据的表。操作：对基表做无害的 ALTER（改注释）后立即写一行；changefeed 启动后马上执行依赖同一 descriptor 的 DDL；对非空表执行 ADD COLUMN DEFAULT NOT NULL。预期：视图更新正确且不崩溃；DDL 不需要等 lease 过期；一步和两步的结果一致。

**支撑**：https://github.com/scylladb/scylladb/issues/10026 、https://github.com/cockroachdb/cockroach/issues/76927 、https://github.com/yugabyte/yugabyte-db/issues/9970

## 4. MVCC 版本、墓碑、GC 与读可见性冲突

**机制**：直接删除或改写历史版本的操作，与 GC、compaction filter、读缓存这些假设“版本单调”的组件发生冲突，导致数据丢失或漏读。TiKV #13448：flashback 直接删除旧的 MVCC key，GC safepoint 推进后，compaction filter 把删除标记处理错，事务报 `DefaultNotFound`；修复改成用 MVCC 覆盖写来实现 flashback。Scylla #11239：扫描读在填充缓存期间，区间上界的行被驱逐，`advance_to()` 里用的 `no_clustering_row_between` 按定义不包含起点，读路径误以为游标没有移动，漏掉这一行，还把区间标记成连续，后续读也会一直漏。

**测试思路**：前提是同一个 key 有多个版本，或缓存里有相邻的 dummy 行。操作：flashback 到时间点 A 后，把 GC 生命周期调短，并强制 compaction；或者用小键空间（16 个 key）的随机变更生成器，并发跑扫描读和缓存驱逐。预期：flashback 前后的快照读和基准一致，GC 之后不出现 NotFound；有缓存时的读结果和直接读 sstable 的结果逐行相同。

**支撑**：https://github.com/tikv/tikv/issues/13448 、https://github.com/scylladb/scylladb/issues/11239

## 5. 持久化格式或线上格式跨版本、跨崩溃不兼容

**机制**：落盘格式或 RPC/IDL 格式变了，但没有兼容旧数据、对端旧版本或写了一半的记录。Scylla #4855：为解决 Y2038 问题把 `gc_clock::duration` 改成 64 位，而 IDL 直接引用了这个类型，TTL 的序列化格式随之改变，3.0/3.1 混合集群里带 TTL 的更新无法复制（报错 “deserialization buffer underflow” / “Truncated frame”）。TiDB #17952：旧版本把分区边界 `LESS THAN (TO_SECONDS('...'))` 存成原始表达式，新版本断言它是整数，升级后 schema 加载失败，tidb 启动不起来。TiKV #9886：磁盘满时加密 file dict 的追加写只写了一半，重启时 CRC 校验失败，panic，扩容磁盘之后仍然启动不了。

**测试思路**：前提是用旧版本创建过各种 DDL 形态（表达式分区、TTL 列）并写入数据，或者开启了加密。操作：滚动升级一个节点后双向读写；在元数据日志追加时注入 ENOSPC 或截断写，然后重启。预期：混合版本期间双向的 mutation、hint、commitlog 都能解析；升级后 schema 能加载；不完整的尾记录被安全丢弃，节点能启动。

**支撑**：https://github.com/scylladb/scylladb/issues/4855 、https://github.com/pingcap/tidb/issues/17952 、https://github.com/tikv/tikv/issues/9886

## 6. 空集合、特殊字符等边界输入破坏查询或工具语义

**机制**：协调层或工具链默认“至少有一个分片、一行、一个合法 token”。Scylla #12475：`p IN ()` 或 `p = null` 不命中任何分区，聚合请求没有发给任何节点，`forward_aggregates::finalize()` 因参数个数不匹配抛出内部错误。Scylla #12477：GROUP BY 加聚合在零匹配时返回一行 null，而 Cassandra 返回空结果（根因未写明）。Scylla #9061：toppartitions 输出的 JSON 没有转义分区键，键里的字符提前闭合了 JSON。TiDB #46989：plan replayer 按 `;` 切分 schema 文件，列注释里的分号把语句切断。TiDB #38699：DDL 警告按错误码只保存第一条，`SHOW WARNINGS` 的消息和计数对不上。Scylla #7095：CDC `delta=keys` 模式的后处理把 `cdc$operation`、`cdc$ttl` 也裁掉了。

**测试思路**：前提是有分布式聚合、导出/回放工具或 CDC。输入：空 IN、`= NULL`、零匹配加 GROUP BY；分区键或注释里含 `"`、`}`、`;`；遍历 CDC 的每种 delta 模式。预期：和参考实现（Cassandra/MySQL）做差分时结果一致；工具输出可以被标准解析器解析，dump→load 能往返；元数据列始终存在。

**支撑**：https://github.com/scylladb/scylladb/issues/12475 、https://github.com/scylladb/scylladb/issues/12477 、https://github.com/scylladb/scylladb/issues/9061 、https://github.com/pingcap/tidb/issues/46989 、https://github.com/pingcap/tidb/issues/38699 、https://github.com/scylladb/scylladb/issues/7095

## 7. 长时间运行或数据堆积导致的无界开销

**机制**：某种开销与调用次数或堆积量成正比，却没有上限。Vitess #15095：`VtMySQLRoot()` 每次调用都往 `PATH` 前面再加一次 `/usr/sbin:`，vtorc 每 15 秒调用一次 FullStatus，几小时后环境变量超过 execve 上限（E2BIG），内存也在增长。Scylla #7933：墓碑不计入分页上限，两条存活行之间有一百万个墓碑时，一页要扫完全部墓碑才返回，延迟没有上限；修复引入墓碑上限，并允许返回空页加续传位置。

**测试思路**：前提是有周期性的后台 RPC，或者存在大量删除的分区。操作：连续调用状态 RPC 数小时（可以加速成百万次循环）；在两条存活行之间写入一百万个行墓碑或分区墓碑，然后分页扫描。预期：进程环境变量和 RSS 不随调用次数增长；每页的耗时和扫描量有上限，能返回空页和有效的续传键，并且继续往前推进。

**支撑**：https://github.com/vitessio/vitess/issues/15095 、https://github.com/scylladb/scylladb/issues/7933

## 未归类的单例

TiDB #18150（表达式索引没有拒绝行值，MySQL 兼容性校验缺失）、Vitess #10020（vtexplain 没有检查所有 keyspace 是否加载成功就开始使用，约 80% 的运行报 table not found）、TiKV #10377（`tikv_channel_full` 指标早已被移除，监控面板一直为空）。

## 决定

- **采用**：模式 1–5 的样本里都有 PR 或评论写明的机制，而且至少 2 条，可以直接转成故障注入测试用例。
- **待验证**：模式 6、7 偏单节点或语义层问题，单条样本可以迁移，但是否算“分布式特有”的风险还需要更多样本确认。
- **否定**：roachtest/logictest 自动生成的失败 issue（#129464、#131695、#170697）不适合当缺陷来源，3 条里有 2 条是测试本身的问题，1 条作为重复关闭。
