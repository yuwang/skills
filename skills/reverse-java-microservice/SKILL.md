---
name: reverse-java-microservice
description: 逆向梳理 Java/Spring 微服务项目中某个功能或模块的完整链路，生成带 Mermaid 图的中文技术文档。当用户提到"梳理链路"、"逆向文档"、"追踪调用链"、"搞清楚这个功能怎么跑的"、"这个接口的完整流程"、"从模型出发追踪"、"老项目的代码逻辑"、"微服务调用关系"、"legacy code 理解"时，即使没有明确提到本 skill，也应该触发。适用于 Spring Boot / Spring Cloud 微服务、MyBatis/MyBatis-Plus、Feign/Kafka/RabbitMQ 等 Java 技术栈。
---

# 逆向梳理 Java 微服务链路

将一个你不熟悉的 Java/Spring 微服务功能，从"完全看不懂"变成"一张清晰的全链路文档"。

## 什么时候用这个 Skill

用户想搞清楚一个老项目（或不熟悉的项目）里某个功能的完整调用链路时。典型场景：

- "帮我梳理一下这个项目里【支付】功能的完整链路"
- "从 Order 这个模型出发，追踪它在所有服务里的调用关系"
- "科拓道闸系统的数据流是怎么走的？"
- "这个 Kafka 消息从发出到消费，中间经过了哪些服务？"

## 核心方法论：三阶段渐进式逆向

### 第一阶段：发现（5 分钟搞清楚范围）

**目标**：找出跟目标功能相关的所有文件，确定涉及哪些微服务模块。

1. **项目结构扫描** — 先看 `pom.xml` 或 `build.gradle` 了解模块划分：
   ```
   find . -name "pom.xml" -maxdepth 2  # Maven 多模块项目
   find . -name "build.gradle" -maxdepth 2  # Gradle 项目
   ```
   快速掌握有哪些子模块及依赖关系。

2. **关键词搜索** — 用 grep 搜索项目根目录，关键词包括：
   - 功能名称的中文/英文/拼音（如"支付"、"payment"、"pay"）
   - 外部系统的品牌名（如"科拓"、"KeyTop"、"keytop"）
   - 已知的表名、配置 key、Topic 名称
   - 用 `--glob "*.java"` 限定 Java 文件，避免 target/build 目录的噪音
   - **至少用 3 组关键词**：驼峰（`keyTop`）、下划线（`key_top`）、全大写（`KEYTOP`）

3. **模块定位** — 从搜索结果识别涉及的微服务模块：
   ```
   grep 结果 → 按目录前缀分组 → 每个目录前缀 = 一个微服务模块
   ```

4. **产出**：一张"模块 × 相关文件数"的表格，发给用户确认范围

### 第二阶段：深挖（并行分析每个模块）

**目标**：理解每个模块内部的类关系和职责。

为每个涉及到的微服务模块启动一个 **explore agent**（如果可用），给它明确的分析任务：

```
分析 {模块路径} 中与 {功能关键词} 相关的所有 Java 文件。
对每个相关的类，记录：
1. 类名、文件路径、所在层次（Entity/Mapper/Service/Controller/Feign/Config/Job）
2. 关键方法签名及职责（一句话）
3. 它调用了谁（下游依赖）
4. 谁调用了它（上游调用方，如果能看出来）
5. 涉及的数据库表、Kafka Topic、Feign 接口
特别关注：枚举类、常量类、配置类 — 它们是理解业务语义的关键。
```

> **为什么要并行**：微服务项目通常有 3-8 个模块，串行分析太慢。各模块的内部分析是独立的，完全可以并行。

**没有 explore agent 时**：按模块逐个分析。优先看关键词命中最多的模块。

**大文件处理**：微服务项目里经常有 300KB+ 的 ServiceImpl（业务逻辑堆积）。不要试图一次性读完，用 `view_range` 分段读取，先扫方法签名（搜 `public.*{` 或 `void\|List\|Map\|String`），再定点看关键方法的实现。

### 第三阶段：综合（生成结构化文档）

**目标**：把散落在各模块的分析结果，综合成一份完整的链路文档。

文档结构遵循固定模板（见 `references/document-template.md`），核心章节包括：

1. **系统架构总览** — 一张 Mermaid 图展示所有相关模块的关系
2. **模块职责划分** — 表格，每个模块一行
3. **核心数据模型** — ER 图 + 枚举值表
4. **从模型出发的完整链路追踪** — 最重要的章节，详见下文
5. **完整数据流链路** — 南向（下发命令）、北向（上报数据）、定时同步
6. **各模块详细分析** — 每个微服务一节
7. **关键业务时序图** — Mermaid sequence diagram
8. **参考速查** — 枚举、配置、API 一览表

## 从模型出发的链路追踪（核心技巧）

这是区分"表面搜索"和"深度理解"的关键方法。

**思路**：选择 3-5 个核心 Entity 作为起点，对每一个沿着 Java 分层架构向上追踪：

```
Entity（字段含义）
   → Mapper（SQL 操作）
      → Service（业务逻辑、事务边界）
         → Controller（HTTP 端点） / Kafka Consumer（消息入口）
            → Feign Client（跨服务调用）
               → 外部系统 API
```

**对每个 Entity 产出**：

1. **一张 Mermaid 分层图** — 从数据层到外部系统，每层列出关键类和方法
2. **一张链路总结表** — 按数据流方向（写入/读取/同步）列出完整链路

**如何选择核心 Entity**：
- 字段最多、关联最多的 Entity 通常最核心
- 被最多 Service 依赖的 Entity
- 跟外部系统直接相关的 Entity
- 用户特别提到的模型

> 参考 `references/model-first-tracing.md` 获取完整的 Mermaid 模板和示例。

## 图表规范

所有图表一律使用 Mermaid，不使用 ASCII 艺术图。常用图表类型：

| 场景 | Mermaid 图类型 | 示例 |
|------|---------------|------|
| 架构总览 | `graph TB` | 模块方框 + 连线 |
| 数据流 | `graph TD` / `graph LR` | 从入口到终点 |
| 模型链路 | `graph TB` + subgraph | 分层展示，每层一个 subgraph |
| 时序图 | `sequenceDiagram` | 请求的完整时序 |
| ER 图 | `erDiagram` | 实体关系 |
| 消息路由 | `graph LR` + decision | 按条件分发 |

**Mermaid 布局规则（重要！节点多时必须遵守）**：

1. **流向一致性**：`graph TD` 意味着入口在顶部、存储在底部。所有箭头顺流向下，**绝对不要出现逆向箭头**。如果发现大量箭头从下往上指，说明层次顺序反了。

2. **禁用双向箭头 `<-->`**：它会严重干扰 Mermaid 的排版引擎，导致线条交叉。改用单向 `-->`。

3. **慎用 `direction LR`**：仅当子图内 ≤3 个节点且文字短时使用。4+ 个节点或长文字的子图用了 `direction LR` 会撑得极宽。

4. **用 `~~~` 隐形链接强制排序**：子图内没有连接关系的节点会被 Mermaid 挤到同一行。用 `A ~~~ B` 创建不可见的排序关系，强制纵向排列。

5. **用 `<br/>` 让节点变高不变宽**：长文本用 `<br/>` 换行（2-3行），避免单行撑宽整个图。

6. **短 ID + 描述标签**：节点 ID 用短前缀（如 `C1`、`A2`），标签文本写描述。这让 Mermaid 源码更易维护。

7. **子图内部连接**：把链式调用写在 subgraph 定义内部（如 `A1 --> A2`），帮助 Mermaid 理解内部流向并正确排版。

8. **间距调参**：多行节点时加上 config 头控制间距：
   ```
   ---
   config:
      flowchart:
         nodeSpacing: 20
         rankSpacing: 40
   ---
   ```

**样式与可读性**：
- 用 `subgraph` 分层，加 emoji 提升可读性（🗄️ 数据层、⚙️ 服务层、🌐 控制层、📨 消息层、🚧 外部系统）
- 用 `style` 给每层上不同的背景色
- 连线上标注协议/格式（"Feign HTTP"、"Kafka JSON"）

**渲染注意事项**：
- Mermaid 代码块前后必须有空行，否则部分 Markdown 渲染器（如 GitLab）不识别
- 表格与 `**粗体标题**` 之间也必须有空行
- 生成完文档后，快速检查一遍所有 Mermaid 块的前后空行

## 搜索策略速查

在 Java/Spring 项目里搜索功能相关代码的常用模式：

| 要找什么 | 搜索模式 |
|---------|---------|
| Entity/模型类 | `grep "class.*{功能名}" --glob "*.java"` |
| Mapper 接口 | `grep "{Entity名}Mapper" --glob "*.java"` |
| Service 实现 | `grep "{功能名}Service" --glob "*.java"` |
| Controller 端点 | `grep "@RequestMapping.*{路径关键词}" --glob "*.java"` |
| Feign 客户端 | `grep "@FeignClient" --glob "*.java"` + 搜服务名 |
| Kafka Consumer | `grep "@KafkaListener" --glob "*.java"` + 搜 Topic |
| Kafka Producer | `grep "kafkaTemplate\|KafkaSender" --glob "*.java"` |
| 定时任务 | `grep "@Scheduled\|@XxlJob\|implements Job" --glob "*.java"` |
| 配置项 | `grep "{功能名}" --glob "*.yml" --glob "*.yaml" --glob "*.properties"` |
| 枚举/常量 | `grep "enum.*{功能名}\|{功能名}.*=" --glob "*.java"` |

> 更多搜索模式见 `references/search-patterns.md`。

## 文档输出规范

- **语言**：中文（代码引用保持英文原名）
- **格式**：单个 Markdown 文件，保存到项目的 `docs/` 目录下
- **命名**：`{功能名}完整链路梳理.md`
- **必须包含目录**：用 Markdown 锚点链接
- **每个核心 Entity 必须有**：Mermaid 分层图 + 链路总结表
- **关键业务场景必须有**：Mermaid 时序图

## 参考文件

| 文件 | 何时查阅 |
|------|---------|
| `references/document-template.md` | 生成文档时，获取完整的章节模板和 Mermaid 模板 |
| `references/model-first-tracing.md` | 做模型链路追踪时，获取 Mermaid 分层图的详细模板和示例 |
| `references/search-patterns.md` | 搜索阶段，获取 Spring 生态各组件的搜索模式 |
