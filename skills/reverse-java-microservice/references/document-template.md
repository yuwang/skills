# 逆向文档模板

生成的文档应遵循以下结构。每个 `##` 章节都是必要的，具体内容根据实际项目调整。

---

## 文档头部

```markdown
# {功能名}完整链路梳理

> **文档生成时间**: {日期}
> **涉及模块**: {模块1} / {模块2} / ...
> **关键词**: {中文名}、{英文名}、{品牌名}、{业务术语}

---

## 目录

- [1. 系统架构总览](#1-系统架构总览)
- [2. 模块职责划分](#2-模块职责划分)
- [3. 核心数据模型](#3-核心数据模型)
- [**4. 从模型出发的完整链路追踪**](#4-从模型出发的完整链路追踪)
- [5. 完整数据流链路](#5-完整数据流链路)
- [6-N. 各模块详细分析](#6-各模块详细分析)
- [N+1. 关键业务链路时序图](#关键业务链路时序图)
- [N+2. 定时任务体系](#定时任务体系)
- [N+3. 消息体系](#消息体系)
- [N+4. 枚举与常量速查](#枚举与常量速查)
- [N+5. 配置项清单](#配置项清单)
- [N+6. 关键算法与策略](#关键算法与策略)
- [N+7. API 接口速查表](#api-接口速查表)
```

---

## 第 1 章：系统架构总览

用一张 Mermaid `graph TB` 图展示所有相关微服务的关系。

> **布局关键**：用 `<br/>` 换行让节点变高不变宽；子图内无连接的节点用 `~~~` 隐形链接强制纵向排列；不要用 `direction LR`（除非子图只有 2-3 个短文字节点）。

````markdown
## 1. 系统架构总览

\```mermaid
---
config:
  flowchart:
    nodeSpacing: 20
    rankSpacing: 40
---
graph TB
    subgraph ExtSys["🚧 外部系统名称"]
        X1["外部系统描述"]
    end

    subgraph ModA["模块A · 职责"]
        A1["核心类1<br/>关键方法"]
        A2["核心类2<br/>关键方法"]
        A1 --> A2
    end

    subgraph ModB["模块B · 职责"]
        B1["核心类1<br/>关键方法"]
        B2["核心类2<br/>关键方法"]
        B1 ~~~ B2
    end

    subgraph Infra["🔧 基础设施"]
        S1[("MySQL")]
        S2["Kafka"]
        S3["Redis"]
        S1 ~~~ S2 ~~~ S3
    end

    X1 -->|"回调/推送"| A1
    A2 -->|"Feign HTTP"| ModB
    A2 -->|"Kafka Topic"| S2
    B1 --> S1

    style ExtSys fill:#ffebee,stroke:#c62828
    style ModA fill:#e3f2fd,stroke:#1565c0
    style ModB fill:#e8f5e9,stroke:#2e7d32
    style Infra fill:#f3e5f5,stroke:#7b1fa2
\```
````

**配色方案**（保持全文一致）：

| 层次           | 背景色    | 边框色    | 用途                   |
| -------------- | --------- | --------- | ---------------------- |
| 外部系统       | `#ffebee` | `#c62828` | 红色系，表示系统边界外 |
| IoT/对接层     | `#e3f2fd` | `#1565c0` | 蓝色系                 |
| 业务层         | `#e8f5e9` | `#2e7d32` | 绿色系                 |
| 数据层         | `#fff3e0` | `#f57c00` | 橙色系                 |
| 消息层         | `#fce4ec` | `#c62828` | 粉红色系               |
| 网关/控制层    | `#f3e5f5` | `#7b1fa2` | 紫色系                 |
| Feign/远程调用 | `#fffde7` | `#f9a825` | 黄色系                 |

---

## 第 2 章：模块职责划分

表格形式：

```markdown
## 2. 模块职责划分

| 模块       | 主要职责 | 关键类             | 与{功能}的关系   |
| ---------- | -------- | ------------------ | ---------------- |
| {module-a} | ...      | `ClassA`, `ClassB` | 直接对接外部系统 |
| {module-b} | ...      | `ClassC`, `ClassD` | 核心业务逻辑     |
```

---

## 第 3 章：核心数据模型

包含 ER 图 + 枚举值表：

````markdown
## 3. 核心数据模型

### 3.1 ER 关系图

\```mermaid
erDiagram
EntityA ||--o{ EntityB : "一对多关系"
EntityA {
Long id PK
String name "业务含义"
Integer type "1=类型A 2=类型B"
}
EntityB {
Long id PK
Long entityAId FK
String detail "详细说明"
}
\```

### 3.2 核心枚举值

| 枚举/字段    | 值  | 含义  |
| ------------ | --- | ----- |
| entityA.type | 1   | 类型A |
| entityA.type | 2   | 类型B |
````

---

## 第 4 章：从模型出发的完整链路追踪

这是最核心的章节。每个核心 Entity 按以下模板生成：

```markdown
## 4. 从模型出发的完整链路追踪

> 本节以每个核心 Entity 为起点，向上追踪到 Controller/API/外部系统，向下追踪到数据存储。

### 4.1 {EntityName}（{中文名} — {重要性说明}）

**文件位置**: `{module}/{package}/{EntityName}.java`
**数据库表**: `{table_name}`

{Mermaid 分层图 — 见 model-first-tracing.md}

**链路追踪总结**:

| 方向            | 链路                                                       |
| --------------- | ---------------------------------------------------------- |
| **写入(Web端)** | 用户 → `Controller` → `Service` → `FeignClient` → 外部系统 |
| **写入(消息)**  | 外部系统 → 消息队列 → `Consumer` → `Service` → DB          |
| **读取**        | `Controller.list()` → `Mapper` → DB                        |
| **跨服务**      | `其他服务` → `FeignClient` → `Service`                     |
```

每个 Entity 之间用 `---` 分隔。最后加一张模型关系全景图。

---

## 第 5 章：完整数据流链路

按数据流方向各画一张 Mermaid 图：

- **南向流（系统 → 外部）**：Web 操作 → Service → Feign → IoT → 外部设备
- **北向流（外部 → 系统）**：外部设备 → 回调/消息 → Consumer → Service → DB
- **定时同步流**：Job → 拉取外部数据 → Diff → 更新 DB → 推送消息

---

## 第 6~N 章：各模块详细分析

每个微服务模块一章，包含：

1. **核心类清单** — 表格（类名、路径、职责）
2. **关键接口枚举** — 如果有外部 API 枚举类，列出完整表格
3. **鉴权/签名流程** — 如有，画 Mermaid 图
4. **消息路由** — 如果有 Kafka/RabbitMQ 消息分发逻辑，画路由图

---

## 时序图章节

选 3-5 个最重要的业务场景，画 `sequenceDiagram`：

````markdown
## N+1. 关键业务链路时序图

### 场景1：{场景名称}

\```mermaid
sequenceDiagram
participant User as 👤 用户
participant BizCtrl as 📱 BusinessController
participant BizSvc as ⚙️ BusinessService
participant Feign as 🔗 FeignClient
participant IoT as 📡 IoTServer
participant Ext as 🚧 外部系统

    User->>BizCtrl: POST /api/xxx
    BizCtrl->>BizSvc: someMethod()
    BizSvc->>Feign: remotCall()
    Feign->>IoT: HTTP /feign/xxx
    IoT->>Ext: 签名 + HTTP POST
    Ext-->>IoT: 响应
    IoT-->>Feign: 返回结果
    Feign-->>BizSvc: 结果
    BizSvc->>BizSvc: 更新 DB
    BizSvc-->>BizCtrl: 成功
    BizCtrl-->>User: 200 OK

\```
````

---

## 速查表章节

### 配置项清单（按服务组织）

```markdown
## N+5. 配置项清单

### N+5.1 {服务名1}

| 配置项        | 默认值 | 说明 |
| ------------- | ------ | ---- |
| `xxx.yyy.zzz` | ...    | ...  |

### N+5.2 {服务名2}

...
```

### API 接口速查表

```markdown
## N+7. API 接口速查表

| 模块     | HTTP 方法 | 路径       | 用途 |
| -------- | --------- | ---------- | ---- |
| {module} | POST      | `/api/xxx` | ...  |
```
