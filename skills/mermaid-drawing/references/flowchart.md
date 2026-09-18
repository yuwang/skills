# 流程图 (Flowchart) 参考

## 基本语法

```mermaid
graph TD
    A[方框] --> B(圆角方框)
    B --> C{菱形/判断}
    C -->|是| D[结果1]
    C -->|否| E[结果2]
```

## 节点形状

| 语法 | 形状 | 适用场景 |
|------|------|---------|
| `A[文本]` | 方框 | 普通步骤 |
| `A(文本)` | 圆角框 | 起止/过程 |
| `A{文本}` | 菱形 | 判断/决策 |
| `A([文本])` | 体育场形 | 开始/结束 |
| `A[(文本)]` | 圆柱 | 数据库 |
| `A((文本))` | 圆形 | 连接点 |
| `A>文本]` | 旗形 | 信号/事件 |
| `A{{文本}}` | 六边形 | 准备/条件 |
| `A[/文本/]` | 平行四边形 | 输入/输出 |

## 连线类型

```mermaid
graph LR
    A --> B
    A --- C
    A -.-> D
    A ==> E
    A -->|标注| F
    A -.->|虚线标注| G
```

| 语法 | 含义 |
|------|------|
| `-->` | 实线箭头 |
| `---` | 实线无箭头 |
| `-.->` | 虚线箭头（可选/异步） |
| `==>` | 粗线箭头（强调/主流程） |
| `~~~` | 隐形连接（仅布局用） |

## 常见模式

### 模式1：决策分支

```mermaid
graph TD
    Start([开始]) --> Check{条件判断}
    Check -->|满足| Path1[执行路径A]
    Check -->|不满足| Path2[执行路径B]
    Path1 --> End([结束])
    Path2 --> End
```

### 模式2：并行处理

```mermaid
graph TD
    Input[输入] --> Fork{分发}
    Fork --> W1[Worker 1]
    Fork --> W2[Worker 2]
    Fork --> W3[Worker 3]
    W1 --> Join{汇聚}
    W2 --> Join
    W3 --> Join
    Join --> Output[输出]
```

### 模式3：循环/重试

```mermaid
graph TD
    Start([开始]) --> Do[执行操作]
    Do --> Check{成功?}
    Check -->|是| End([结束])
    Check -->|否| Retry{重试次数<3?}
    Retry -->|是| Do
    Retry -->|否| Fail[失败告警]
```

### 模式4：分层架构图

```mermaid
---
config:
  flowchart:
    nodeSpacing: 20
    rankSpacing: 40
---
graph TB
    subgraph Client["客户端"]
        C1["Web App<br/>React + Vite"]
        C2["Mobile App<br/>Flutter"]
        C1 ~~~ C2
    end

    subgraph Gateway["网关层"]
        GW["API Gateway<br/>Kong / Nginx"]
    end

    subgraph Services["⚙️ 业务服务"]
        S1["用户服务<br/>user-service"]
        S2["订单服务<br/>order-service"]
        S3["支付服务<br/>payment-service"]
        S1 ~~~ S2 ~~~ S3
    end

    subgraph Data["数据层"]
        DB1[("MySQL<br/>业务数据")]
        DB2[("MongoDB<br/>日志/文档")]
        RD["Redis<br/>缓存"]
        DB1 ~~~ DB2 ~~~ RD
    end

    C1 --> GW
    C2 --> GW
    GW --> S1
    GW --> S2
    GW --> S3
    S1 --> DB1
    S2 --> DB1
    S2 --> RD
    S3 --> DB2

    style Client fill:#ffebee,stroke:#c62828
    style Gateway fill:#f3e5f5,stroke:#7b1fa2
    style Services fill:#e8f5e9,stroke:#2e7d32
    style Data fill:#e3f2fd,stroke:#1565c0
```

### 模式5：消息驱动架构

```mermaid
graph LR
    subgraph Producers["生产者"]
        P1["订单服务"]
        P2["支付服务"]
    end

    subgraph MQ["消息队列"]
        T1["order.created"]
        T2["payment.completed"]
    end

    subgraph Consumers["消费者"]
        C1["库存服务"]
        C2["通知服务"]
        C3["积分服务"]
    end

    P1 -->|"发布"| T1
    P2 -->|"发布"| T2
    T1 -->|"订阅"| C1
    T1 -->|"订阅"| C2
    T2 -->|"订阅"| C2
    T2 -->|"订阅"| C3

    style Producers fill:#e8f5e9,stroke:#2e7d32
    style MQ fill:#fff3e0,stroke:#f57c00
    style Consumers fill:#e3f2fd,stroke:#1565c0
```

### 模式6：数据处理流水线 (Pipeline)

```mermaid
graph LR
    Raw[("原始数据<br/>S3/OSS")] --> Extract["抽取<br/>Extract"]
    Extract --> Transform["转换<br/>Transform"]
    Transform --> Load["加载<br/>Load"]
    Load --> DW[("数据仓库<br/>ClickHouse")]
    DW --> BI["BI 报表"]

    style Raw fill:#fff3e0,stroke:#f57c00
    style DW fill:#e3f2fd,stroke:#1565c0
```

## 高级技巧

### 用 click 添加交互链接

```mermaid
graph LR
    A[GitHub] --> B[CI/CD]
    click A "https://github.com" "打开GitHub"
```

### 用 class 批量设置样式

```mermaid
graph TD
    A:::success --> B:::warning --> C:::error
    classDef success fill:#d4edda,stroke:#28a745
    classDef warning fill:#fff3cd,stroke:#ffc107
    classDef error fill:#f8d7da,stroke:#dc3545
```

### 横向与纵向混合

当需要在纵向流程图中插入横向的子图时：

```mermaid
graph TB
    Start --> subgraph parallel["并行处理"]
        direction LR
        T1["任务1"]
        T2["任务2"]
        T3["任务3"]
    end
    parallel --> End
```

注意：`direction LR` 仅在子图节点 ≤3 个且文字短时使用。
