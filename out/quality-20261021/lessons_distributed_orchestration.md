# 编排/容器运行时缺陷的复发模式（kubernetes / containerd / moby）

样本：30 条（样本里没有 temporal）。判定：真实缺陷 24，不是缺陷 2（#53006 功能改进、#114210 文档/弃用），存疑 4（#63371、#45419、#67777、#103500）。下面只用真实缺陷和根因明确的存疑项来归纳。

## 1. 守护进程重启 / live-restore 后状态没恢复全

**机制**：进程重启时，内存里的派生状态要靠持久化数据或外部探测重建。重建逻辑往往漏掉某个字段，或者在探测失败时一直等。moby 在 live-restore 时没把卷的活跃挂载计数恢复回来，计数一直是 0，容器停止时 uint64 下溢，卷就再也删不掉。containerd 在 bundle 的 `runtime` 文件里写入 shim 路径，和 BinaryName 的用途冲突，重启后容器被识别为不在运行。节点重启后 shim socket 已经不存在，containerd 却把 ENOENT 当作可以容忍的错误一直重试，每个死 shim 都耗到超时。

**测试思路**：前置条件是开启 live-restore，并有带命名卷或自定义 runtime 的运行中容器 → 重启运行时守护进程，或者删掉 shim socket 后再重启 → 检查三点：容器状态还是 running；之后 stop/rm 卷都成功；启动耗时不随死 shim 数量线性增长。

**依据**：https://github.com/moby/moby/issues/44422 、https://github.com/containerd/containerd/issues/6534 、https://github.com/containerd/containerd/issues/5597

## 2. 升级和版本偏斜：旧数据、新默认值、回归

**机制**：新版本读取旧版本写下的数据，或者上游组件开始下发新的默认字段，而下游没有做兼容。ipvlan 网络在 20.10 版本时不持久化 IpvlanFlag，升级到 23.0 后反序列化时类型断言 panic，守护进程起不来。kubelet 改成默认设置 swap 限制，containerd 不管节点是否支持都写 memsw，容器创建失败。重构还会让非默认路径悄悄回归：v28 版本里 slirp4netns 端口驱动失效；go-archive 不再为目录条目创建隐式父目录，导致缺 `etc/` 条目的层拉取失败。

**测试思路**：前置条件是用 N-1 版本创建各类持久化对象（网络、卷、镜像层），并准备好上游组件的新旧版本组合 → 原地升级，或换上新版上游组件 → 检查守护进程能启动、旧对象能 inspect 和使用。另外，对每个可选驱动或配置值、每种不规范但合法的输入（比如 tar 包缺父目录条目）各跑一遍冒烟测试。

**依据**：https://github.com/moby/moby/issues/44925 、https://github.com/containerd/containerd/issues/8855 、https://github.com/moby/moby/issues/49499 、https://github.com/moby/moby/issues/53257 、https://github.com/containerd/containerd/issues/9139

## 3. 失败路径不回滚，资源泄漏

**机制**：一个操作分好几步，中间某步失败时，前面已经占用的资源没有释放。cpumanager 已经分配了 CPU，但 updateContainerCPUSet 失败时状态没有回滚，节点越来越"缺 CPU"。v2 拉取时部分层下载失败，临时文件没关也没删，/var/lib/docker/tmp 涨到 20G 以上。Windows 上写层失败时 LayerWriter 句柄泄漏，层删不掉，prune 报告的可回收空间和实际不一致。

**测试思路**：前置条件是一个有 N 步、每步都会占用资源的操作 → 在第 k 步注入错误，k 取遍 1..N → 检查分配器的可用量、临时目录大小、句柄数都回到基线，并且后续 prune 或删除能成功。

**依据**：https://github.com/kubernetes/kubernetes/issues/63018 、https://github.com/moby/moby/issues/14506 、https://github.com/moby/moby/issues/31253 、https://github.com/moby/moby/issues/44422（引用计数）

## 4. 并发：锁竞争、阻塞的 I/O 和外部竞态

**机制**：为了保证事件顺序加了全局锁，高并发时就会严重退化。containerd 的 eventSendMu 让 30 个并发 exec 花了 19 秒。没有超时的阻塞 open 会把整个守护进程卡死：fifo 的另一端一直不打开，`docker ps` 就挂住了。和外部进程（udev）之间没有同步，块设备还没建好就去挂载。并发上限只在一条代码路径上生效：Unpack=true 时 MaxConcurrentDownloads 不起作用。

**测试思路**：前置条件是一个运行中的容器 → 并发发起 30 个以上的短命 exec，同时让部分 stdio 客户端不连接或中途断开 → 检查总耗时和串行执行相比在常数倍以内；start/exit 事件对每个进程都有序且成对出现；其他只读 API 照常响应。另外要在所有拉取路径上测量同时在途的 fetch 数，不能超过上限。

**依据**：https://github.com/containerd/containerd/issues/8557 、https://github.com/moby/moby/issues/26561 、https://github.com/moby/moby/issues/4036 、https://github.com/containerd/containerd/issues/6054

## 5. 临时值或过期的起算点被固化

**机制**：系统先用一个临时或初始值占位，之后真实值到了，但依赖方不会再更新。kubelet 在外部 cloud provider 设置地址之前，先用自己探测到的地址初始化节点，hostNetwork Pod 的 PodIPs 一旦写入就不再修改，于是一直是错的。CronJob 计算错过的周期时从 creationTimestamp 算起，修改 schedule 后会补跑更新之前的周期（这条是存疑项，评论认为是设计如此）。累积计数在容器删除时回落到 0，按差值算速率就溢出成天文数字。

**测试思路**：前置条件是一个先由组件 A 临时赋值、之后由组件 B 覆盖的字段，或一个累积计数器 → 让 B 晚到，或在资源删除过程中读取 → 检查依赖方最终和 B 的值一致；计数器回退时速率被截断成 0 或者跳过，不会出现溢出值；修改配置后不会补跑过去的周期。

**依据**：https://github.com/kubernetes/kubernetes/issues/120720 、https://github.com/kubernetes/kubernetes/issues/114057 、https://github.com/kubernetes/kubernetes/issues/63371

## 6. 降级和回退判断太窄，单点失败扩散

**机制**：错误处理只覆盖了作者预想的那一种失败。镜像源回退只在 404 时生效，遇到 503 直接失败。插件注册了 readiness 之后又初始化失败，整个守护进程永远等不到 READY（/etc 只读时就会触发）。一个 Pod 带着非法 label 就能让调度器 nil 指针 panic，影响整个集群。

**测试思路**：前置条件是配置了多个 fallback 源或可选插件 → 依次注入 5xx、超时、连接拒绝、只读文件系统、畸形输入 → 检查请求会切到下一个源；守护进程能在部分插件降级的情况下完成启动；坏输入只影响它自己的对象，组件不崩溃。

**依据**：https://github.com/containerd/containerd/issues/4531 、https://github.com/containerd/containerd/issues/9139 、https://github.com/kubernetes/kubernetes/issues/107415

## 7. 能力和权限语义与实际不符

**机制**：报告的能力和实际能力用的是不同的判断依据，或者某个权限边界设得过宽。`docker info` 只看内核是否支持 seccomp，没看编译时有没有启用。moby 在 entrypoint 执行前清空了 effective/permitted 能力集，非 root 加 no-new-privileges 的组合下 cap_add 失效，containerd 和 crio 没有这个问题。kube-proxy 全局设置 route_localnet=1，同网段的主机可以访问只监听 localhost 的端口。

**测试思路**：前置条件是同一份安全配置（非 root、NNP、cap_add），以及一个只监听 127.0.0.1 的服务 → 分别在多种运行时和多种构建标签下运行，再从同网段主机伪造指向 127.0.0.1 的路由 → 检查 /proc/1/status 的能力位在各运行时之间一致；info 报告的能力确实可用；localhost 端口从外部不可达。

**依据**：https://github.com/moby/moby/issues/24374 、https://github.com/moby/moby/issues/45491 、https://github.com/kubernetes/kubernetes/issues/90259

## 决定

- **采用**：模式 1（重启恢复）、2（升级偏斜）、3（失败路径回滚）、4（并发与阻塞）。这四类各有 3 到 5 条根因明确的 issue 支撑，可以直接转成故障注入用例。
- **待验证**：模式 5 只有 2 条确定的缺陷，CronJob 那条是存疑项。模式 7 偏向安全或能力报告，跨产品能否迁移要看具体系统。
- 样本里没有 temporal 的 issue，所以这些结论不覆盖工作流引擎特有的问题（重放确定性、历史版本兼容等）。
