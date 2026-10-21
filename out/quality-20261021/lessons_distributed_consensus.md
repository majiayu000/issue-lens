# distributed_consensus 样本：可迁移的失败模式

样本 30 条，实际只来自 nomad（15）、consul（7）、nats-server（7）、etcd（2）；样本中没有 hashicorp/raft 或 openraft 的 issue，所以下面的模式只有共识系统周边控制面的证据，不涉及 Raft 内核（选举、日志复制、快照/压缩、成员变更）。这里只用 is_real_defect=yes 的条目，unclear 的条目单独注明。

## 1. 角色或连接切换后，旧角色的后台逻辑仍在运行

**机制**：一个组件只该在某个角色下工作（leader、当前心跳目标），但切换角色时没有门控，或者没把仍在使用的资源计入引用。Nomad 的 eval broker 在 follower 上被禁用，但 FSM 应用日志时延迟 eval 照样进 delayHeap，导致 follower 的计数和内存一直涨。客户端心跳换到另一台 server 后，连接池回收器只看 RPC 使用情况，把还有活跃 exec 流的连接当成空闲连接关掉了。

**测试思路**：先在 3 节点集群的 follower 上持续应用会产生"仅 leader 处理"副作用的日志，或者建立一条长流式会话；再做 leader 迁移或心跳目标切换；然后断言非 leader 的队列和内存指标不增长，长会话在切换后 N 分钟内不断开。

**证据**：https://github.com/hashicorp/nomad/issues/4670 、https://github.com/hashicorp/nomad/issues/10579

## 2. 重启、关闭、吊销等生命周期事件没有传到所有订阅方

**机制**：资源有了新状态，但只有一部分钩子或索引被通知到。alloc runner 的 Restart 不会触发 alloc 级 hook，所以分组服务的健康检查监视器在第一次重启后不再重新注册。NRG 内部客户端关闭时类型是 SYSTEM，没从账户里移除，造成泄漏。通过 auth callout 动态生成的用户没有被纳入吊销映射，账户 JWT 更新后，已有连接不会断开。

**测试思路**：先建立一个需要多个子系统协作的资源（服务+健康检查、连接+账户、用户+吊销表），再让它重复经历重启、关闭、吊销 N 次；断言第 2 次及之后的行为和第 1 次一致，连接或客户端数量和内存能回到基线，被吊销用户的连接立即关闭。

**证据**：https://github.com/hashicorp/nomad/issues/9176 、https://github.com/nats-io/nats-server/issues/5471 、https://github.com/nats-io/nats-server/issues/5477 。unclear：https://github.com/etcd-io/etcd/issues/17223 （关闭期间仍有在途的 Snapshot 请求访问已关闭的后端，最终靠 gRPC GracefulStop 等待在途请求、测试去抖解决）

## 3. 并发事件绕过限额或计数

**机制**：限流或计数逻辑按"当前状态的快照"判断，没有把正在进行中的转换算进去。drain 第二个节点时，第一个节点上已标记迁移的分配仍被算作健康，于是 max_parallel=1 被突破。system 调度器把"已在符合条件的节点上运行（ignored）"和"其余节点被约束过滤"放在一起算，当成放置失败。

**测试思路**：作业的 count 大于 1、max_parallel=1，分配分散在多个节点。在毫秒级间隔内连续 drain 多个节点，或者在已有分配的情况下重复执行 plan。断言任何时刻迁移中的分配数都不超过 max_parallel，重复 plan 时不报警告，退出码为 0。

**证据**：https://github.com/hashicorp/nomad/issues/25979 、https://github.com/hashicorp/nomad/issues/12748

## 4. 共享可变状态的并发竞态和内存别名

**机制**：热路径上的对象被多个 goroutine 共享，但它本身不是线程安全的；或者 append 复用了底层数组，改写了别处还在引用的字节。账户级 `*rand.Rand` 没加锁，在高并发加权映射下 panic。给 reply 追加 `$JS.ACK` 后缀时，如果切片还有剩余容量，就会覆盖相邻的协议字段，导致消息体混入路由协议元数据。

**测试思路**：开启 race detector，在带权重 subject mapping 的情况下用多连接压测，速率达到每秒数万条。另外用模糊测试构造 cap>len 的 reply 切片，对它执行后缀拼接，然后断言原 buffer 中其他字段的字节没有变化，消费到的 payload 与发布时逐字节一致。

**证据**：https://github.com/nats-io/nats-server/issues/4893 、https://github.com/nats-io/nats-server/issues/7842

## 5. 身份变更或重建后，系统仍按旧身份或旧序号推进

**机制**：系统用名字或单调序号来识别"同一个对象"，对象改名或重建后，旧身份记录会冲突，或者让新数据被跳过。Consul 节点保持 ID 不变只改 node_name 时，因为"别名已有节点"而注册失败。NATS source 流删除重建后序号从 1 开始，下游只接受高于旧最高序号的消息，于是悄悄丢掉一段数据；PR 最后用 stream identity（创建时间的哈希）来识别重建。

**测试思路**：先让下游或目录记录对象 X 的状态，然后在保持 ID 的情况下改名重启，或者删除重建 X 让序号归零，再写入新数据。断言目录里只剩一个条目且没有 failed 残留，下游完整收到重建后的全部消息，至少能识别重建并给出明确错误。

**证据**：https://github.com/hashicorp/consul/issues/3974 。unclear：https://github.com/nats-io/nats-server/issues/5847 （维护者起初认为这是预期行为，修复 PR 标为 [IMPROVED]）

## 6. 时间边界：DST 跳变

**机制**：周期调度在非 UTC 时区按本地时间计算下次触发时刻，cron 库不处理夏令时，跳变当晚 leader 上的周期调度器卡住，或者失控触发；重启 leader 后恢复。

**测试思路**：用可注入的假时钟，把周期任务的时区设为 America/New_York，将时钟推进跨越 3 月前跳和 11 月回拨两个边界。断言下次触发时间严格单调递增，前跳时缺失的时刻跳过，回拨时重复的时刻最多触发两次，调度循环不卡住、也不连续触发。

**证据**：https://github.com/hashicorp/nomad/issues/7289 。unclear：https://github.com/hashicorp/nomad/issues/5718 （固定拉取超时导致大镜像失败，修复是新增 pull_timeout 配置）

## 7. 只在某种模式、配置分支或输入形状下才走到的缺陷代码路径

**机制**：新功能只在主路径上测过，相邻模式没有覆盖。cgroup v2 的改动在 v1 模式下也设置了 CgroupParent，导致内存限制失效。默认代理配置只在 bridge 模式下生成，host 模式下拿到 nil 后 panic。mirror 只有一个 subject transform 时，没有转换成 FilterSubject，所以走不到细粒度的 consumer create API。反熵异步同步时只用 agent token，服务级 token 没有传过去。外部签发、缺少 revision claim 的 JWT 在类型断言时 panic。

**测试思路**：把影响代码路径的配置维度做成矩阵，例如 cgroup v1/v2、网络模式 host/bridge、过滤写法 单条/列表/transform、token 来源 agent/请求级，再加上缺字段的输入。对每个组合跑同一个端到端用例，断言要么行为正确（限制生效、同步成功），要么返回明确的校验错误，任何组合都不能 panic。

**证据**：https://github.com/hashicorp/nomad/issues/13031 、https://github.com/hashicorp/nomad/issues/11243 、https://github.com/nats-io/nats-server/issues/6751 、https://github.com/hashicorp/consul/issues/734 、https://github.com/etcd-io/etcd/issues/14931

## 结论

- **采用**：模式 1-5、7 有不少于 2 条有根因的真实缺陷支撑，可以作为测试设计清单。
- **待验证**：模式 6 只有 1 条确证；"共识内核"类模式（选举期间写入、快照+压缩、成员变更）在本样本中**没有证据**，需要重新抽样，确保 hashicorp/raft 和 openraft 的 issue 被抽到。
- 其余真实缺陷（UI、CLI 帮助、指标命名、HCL 插值、Windows 进程树递归、iptables 规则顺序、scaling 校验）是单点问题，不归入以上模式。
