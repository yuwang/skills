# 时序图 (Sequence Diagram) 参考

## 基本语法

```mermaid
sequenceDiagram
    participant A as 参与者A
    participant B as 参与者B
    A->>B: 请求
    B-->>A: 响应
```

## 消息类型

| 语法 | 含义 | 适用场景 |
|------|------|---------|
| `A->>B: msg` | 实线箭头（同步调用） | API 请求、方法调用 |
| `A-->>B: msg` | 虚线箭头（异步响应） | 返回结果、回调 |
| `A-)B: msg` | 实线开放箭头（异步发送） | 发消息、发事件 |
| `A--)B: msg` | 虚线开放箭头（异步通知） | 推送通知 |
| `A-xB: msg` | 带 × 的箭头（失败） | 请求失败 |

## 参与者声明

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as 前端
    participant GW as 网关
    participant SVC as 服务
    participant DB as 数据库
```

参与者从左到右按声明顺序排列，使用简短的中文别名提升可读性。

## 常见模式

### 模式1：标准 HTTP 请求-响应

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as 前端
    participant API as API Server
    participant DB as Database

    U->>FE: 点击提交
    FE->>API: POST /api/orders
    API->>DB: INSERT INTO orders
    DB-->>API: OK (id=123)
    API-->>FE: 201 Created {id: 123}
    FE-->>U: 显示成功提示
```

### 模式2：带认证的请求

```mermaid
sequenceDiagram
    participant C as Client
    participant Auth as Auth Server
    participant API as API Server

    C->>Auth: POST /oauth/token
    Auth-->>C: access_token
    C->>API: GET /api/data (Bearer token)
    API->>Auth: 验证 token
    Auth-->>API: token 有效
    API-->>C: 200 OK {data}
```

### 模式3：异步消息处理

```mermaid
sequenceDiagram
    participant P as Producer
    participant MQ as Kafka
    participant C as Consumer
    participant DB as Database

    P-)MQ: 发送消息
    Note over MQ: Topic: order.created
    MQ-)C: 消费消息
    C->>DB: 写入数据
    DB-->>C: OK
    C-)MQ: 提交 offset
```

### 模式4：微服务调用链

```mermaid
sequenceDiagram
    participant GW as Gateway
    participant US as UserService
    participant OS as OrderService
    participant PS as PaymentService
    participant NS as NotifyService

    GW->>OS: 创建订单
    OS->>US: 查询用户信息
    US-->>OS: 用户详情
    OS->>PS: 发起支付
    PS-->>OS: 支付结果
    OS-)NS: 发送通知(异步)
    OS-->>GW: 订单创建成功
```

## 高级语法

### 分组框 (rect)

用 `rect` 给一组消息加上背景色框，表示逻辑分组：

```mermaid
sequenceDiagram
    participant A as 服务A
    participant B as 服务B
    participant C as 服务C

    rect rgb(200, 230, 200)
        Note over A,B: 第一阶段：数据准备
        A->>B: 获取数据
        B-->>A: 返回数据
    end

    rect rgb(200, 200, 230)
        Note over A,C: 第二阶段：处理
        A->>C: 提交处理
        C-->>A: 处理完成
    end
```

### 循环 (loop)

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: 发起长轮询
    loop 每5秒
        S-->>C: 推送新消息
    end
```

### 条件 (alt/opt)

```mermaid
sequenceDiagram
    participant U as 用户
    participant S as 服务

    U->>S: 登录请求
    alt 密码正确
        S-->>U: 200 登录成功
    else 密码错误
        S-->>U: 401 认证失败
    end
```

```mermaid
sequenceDiagram
    participant A as 服务A
    participant Cache as 缓存
    participant DB as 数据库

    A->>Cache: 查缓存
    opt 缓存未命中
        A->>DB: 查数据库
        DB-->>A: 数据
        A->>Cache: 写入缓存
    end
    Cache-->>A: 返回数据
```

### 并行 (par)

```mermaid
sequenceDiagram
    participant API as API Server
    participant S1 as 服务1
    participant S2 as 服务2
    participant S3 as 服务3

    par 并行请求
        API->>S1: 请求A
    and
        API->>S2: 请求B
    and
        API->>S3: 请求C
    end
    S1-->>API: 响应A
    S2-->>API: 响应B
    S3-->>API: 响应C
```

### 注释 (Note)

```mermaid
sequenceDiagram
    participant A as 服务A
    participant B as 服务B

    Note over A: 内部处理逻辑
    A->>B: 请求
    Note over A,B: 这个调用可能超时
    Note right of B: 查询数据库
    B-->>A: 响应
```

### 激活 (activate/deactivate)

表示参与者的活跃期间：

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>+S: 请求
    S->>S: 处理中...
    S-->>-C: 响应
```

## 时序图最佳实践

1. **参与者不超过 7 个** — 超过时考虑拆分为多张图
2. **从左到右按调用顺序排列** — 让箭头尽量从左指向右
3. **用别名缩短长名称** — `participant OS as OrderService`
4. **标注关键信息** — 请求路径、HTTP 方法、错误码
5. **异步用开放箭头** — 区分同步调用和异步消息
6. **用 rect 分组逻辑阶段** — 比注释更清晰
