# 其他图类型参考

## 状态图 (State Diagram)

### 基本语法

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Processing : 开始处理
    Processing --> Completed : 处理成功
    Processing --> Failed : 处理失败
    Failed --> Processing : 重试
    Completed --> [*]
```

### 复合状态

```mermaid
stateDiagram-v2
    [*] --> Active

    state Active {
        [*] --> Idle
        Idle --> Running : 接收任务
        Running --> Idle : 任务完成
        Running --> Error : 异常
        Error --> Idle : 恢复
    }

    Active --> Suspended : 暂停
    Suspended --> Active : 恢复
    Active --> [*] : 关闭
```

### 并发状态 (fork/join)

```mermaid
stateDiagram-v2
    [*] --> Init
    Init --> fork_state
    state fork_state <<fork>>
    fork_state --> TaskA
    fork_state --> TaskB
    fork_state --> TaskC
    TaskA --> join_state
    TaskB --> join_state
    TaskC --> join_state
    state join_state <<join>>
    join_state --> Complete
    Complete --> [*]
```

### 带条件的转换

```mermaid
stateDiagram-v2
    state check_result <<choice>>
    [*] --> Submitted
    Submitted --> Reviewing : 提交审核
    Reviewing --> check_result
    check_result --> Approved : 通过
    check_result --> Rejected : 拒绝
    Approved --> Published : 发布
    Rejected --> Draft : 退回修改
    Draft --> Submitted : 重新提交
```

### 完整示例：订单状态机

```mermaid
stateDiagram-v2
    [*] --> Created : 创建订单

    state Created {
        [*] --> WaitPay
        WaitPay --> Paying : 发起支付
    }

    Created --> Cancelled : 超时取消
    Paying --> Paid : 支付成功
    Paying --> Created : 支付失败

    state Fulfillment {
        [*] --> Picking
        Picking --> Packed : 拣货完成
        Packed --> Shipped : 发货
    }

    Paid --> Fulfillment : 进入履约
    Shipped --> Delivered : 签收
    Delivered --> Completed : 确认收货
    Delivered --> Refunding : 申请退款
    Refunding --> Refunded : 退款成功
    Completed --> [*]
    Refunded --> [*]
    Cancelled --> [*]

    note right of Created : 30分钟未支付自动取消
    note right of Refunding : 需人工审核
```

### 状态图最佳实践

1. **用 `[*]` 标记起止** — 让读者知道从哪开始、到哪结束
2. **转换标签用动词** — "提交"、"审核通过" 而非 "状态变为已审核"
3. **复杂状态用嵌套** — 把相关子状态收入复合状态中
4. **标注关键条件** — 超时、需审核等用 `note` 说明

---

## 甘特图 (Gantt)

### 基本语法

```mermaid
gantt
    title 项目开发计划
    dateFormat YYYY-MM-DD
    axisFormat %m/%d

    section 需求阶段
        需求分析     :a1, 2024-01-01, 5d
        需求评审     :a2, after a1, 2d

    section 设计阶段
        架构设计     :b1, after a2, 3d
        详细设计     :b2, after b1, 4d

    section 开发阶段
        前端开发     :c1, after b2, 10d
        后端开发     :c2, after b2, 12d
        联调测试     :c3, after c1, 5d
```

### 任务状态标记

```mermaid
gantt
    title Sprint 进度
    dateFormat YYYY-MM-DD

    section 用户模块
        登录功能     :done, login, 2024-01-01, 3d
        注册功能     :done, reg, after login, 2d
        权限管理     :active, perm, after reg, 4d
        用户中心     :uc, after perm, 3d

    section 订单模块
        创建订单     :crit, active, co, 2024-01-05, 5d
        支付集成     :crit, pay, after co, 4d
        退款流程     :refund, after pay, 3d
```

| 标记 | 含义 |
|------|------|
| `done` | 已完成 |
| `active` | 进行中 |
| `crit` | 关键路径(红色) |
| 无标记 | 待开始 |

### 里程碑

```mermaid
gantt
    title 版本发布计划
    dateFormat YYYY-MM-DD

    section v1.0
        功能开发     :v1dev, 2024-01-01, 20d
        测试         :v1test, after v1dev, 5d
        v1.0 发布    :milestone, v1rel, after v1test, 0d

    section v2.0
        功能开发     :v2dev, after v1rel, 25d
        v2.0 发布    :milestone, v2rel, after v2dev, 0d
```

---

## 旅程图 (User Journey)

### 基本语法

```mermaid
journey
    title 用户购物旅程
    section 浏览
        打开首页: 5: 用户
        搜索商品: 4: 用户
        查看详情: 4: 用户
    section 下单
        加入购物车: 5: 用户
        填写地址: 3: 用户
        选择支付方式: 3: 用户
        确认支付: 4: 用户, 系统
    section 售后
        等待发货: 2: 用户
        确认收货: 5: 用户
        评价: 3: 用户
```

数字 1-5 表示满意度（5=非常满意，1=非常不满意）。

---

## 思维导图 (Mindmap)

### 基本语法

```mermaid
mindmap
    root((系统设计))
        前端
            React
            Vue
            移动端
                Flutter
                React Native
        后端
            Java/Spring
            Node.js
            Go
        数据层
            MySQL
            Redis
            MongoDB
        基础设施
            Docker
            K8s
            CI/CD
```

### 带形状的节点

```mermaid
mindmap
    root((项目架构))
        [用户端]
            (Web App)
            (Mobile App)
            (小程序)
        [服务端]
            (API Gateway)
            (微服务集群)
                {{用户服务}}
                {{订单服务}}
                {{支付服务}}
        [数据层]
            )MySQL(
            )Redis(
```

节点形状：
- `(())` 圆形（根节点）
- `[]` 方框
- `()` 圆角框
- `{{}}` 六边形
- `))` 云朵形

### 常见陷阱：特殊字符

mindmap 中**无法通过引号转义特殊字符**（不像 flowchart 可以用 `["文本(含括号)"]`）。节点文本中的 `()[]{}` 会被强制解析为形状语法。

```mermaid
mindmap
    root((错误示例))
        固定车管理
            ❌ 固定车(月卡)管理
            ✅ 固定车-月卡管理
        视频系统
            ❌ 视频监控(IMS)
            ✅ 视频监控/IMS
```

**规则**：mindmap 节点文本中彻底避免 `()`、`[]`、`{}`，改用 `-`、`/`、`·`、`：` 等替代。

---

## Git 图 (GitGraph)

```mermaid
gitGraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "feat: user module"
    commit id: "feat: order module"
    branch feature/payment
    checkout feature/payment
    commit id: "feat: payment api"
    commit id: "feat: payment callback"
    checkout develop
    merge feature/payment id: "merge: payment"
    checkout main
    merge develop id: "release: v1.0" tag: "v1.0"
    checkout develop
    commit id: "feat: new feature"
```

---

## 饼图 (Pie)

```mermaid
pie title 技术栈分布
    "Java" : 40
    "TypeScript" : 25
    "Python" : 20
    "Go" : 10
    "Other" : 5
```

---

## 象限图 (Quadrant)

```mermaid
quadrantChart
    title 技术选型评估
    x-axis "学习成本低" --> "学习成本高"
    y-axis "性能一般" --> "性能优秀"
    quadrant-1 "值得投入"
    quadrant-2 "首选方案"
    quadrant-3 "备选方案"
    quadrant-4 "谨慎选择"
    Go: [0.7, 0.8]
    Rust: [0.9, 0.95]
    Java: [0.5, 0.7]
    Python: [0.2, 0.4]
    Node.js: [0.3, 0.5]
```
