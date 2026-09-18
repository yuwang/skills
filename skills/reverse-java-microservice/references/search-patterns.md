# Java/Spring 微服务搜索模式速查

## 基础搜索原则

1. **多关键词**：一个功能在代码里有多种命名方式，至少用 3 组关键词
2. **大小写变体**：Java 用驼峰（`keyTop`），数据库用下划线（`key_top`），常量用全大写（`KEYTOP`）
3. **中英文混搜**：注释里可能有中文名，代码里用英文名
4. **限定 *.java**：避免 target/build 目录的编译产物干扰

## 按层次搜索

### Entity / 模型类

```bash
# 按类名搜索
grep "class {Name}" --glob "*.java"

# 按表名搜索（MyBatis-Plus）
grep "@TableName.*{表名}" --glob "*.java"

# 按 JPA 表名搜索
grep "@Table.*name.*{表名}" --glob "*.java"

# 搜索 MongoDB 实体
grep "@Document.*{集合名}" --glob "*.java"
```

### Mapper / Repository

```bash
# MyBatis-Plus Mapper
grep "extends BaseMapper<{Entity}>" --glob "*.java"

# MyBatis XML
grep "{Entity}" --glob "*Mapper.xml"

# JPA Repository
grep "extends.*Repository<{Entity}" --glob "*.java"

# MongoDB Repository
grep "MongoRepository<{Entity}\|MongoTemplate" --glob "*.java"
```

### Service

```bash
# Service 接口和实现
grep "{功能名}Service" --glob "*.java"

# 引用特定 Entity 的 Service
grep "private.*{Entity}Mapper\|@Autowired.*{Entity}" --glob "*ServiceImpl.java"

# 事务方法
grep "@Transactional" --glob "*{功能名}*ServiceImpl.java"
```

### Controller

```bash
# REST Controller
grep "@RestController\|@Controller" --glob "*{功能名}*.java"

# 特定路径
grep "@RequestMapping\|@GetMapping\|@PostMapping" --glob "*{功能名}*Controller.java"

# 按 URL 路径搜索
grep "\"/api/{路径关键词}\|\"/{路径关键词}" --glob "*.java"
```

### Feign Client（跨服务调用）

```bash
# 所有 Feign 客户端
grep "@FeignClient" --glob "*.java"

# 指向特定服务的 Feign
grep "@FeignClient.*name.*{服务名}" --glob "*.java"

# Feign 接口契约（通常在 api 模块）
grep "interface.*Client\|interface.*Api" --glob "*.java" | grep -i "{功能名}"

# Feign 的超时配置
grep "FeignConfig\|connectTimeout\|readTimeout" --glob "*.java" --glob "*.yml"
```

### Kafka / 消息队列

```bash
# Kafka Consumer
grep "@KafkaListener" --glob "*.java"

# 特定 Topic 的消费者
grep "topics.*{topic名}\|{topic名}" --glob "*Consumer*.java" --glob "*Listener*.java"

# Kafka Producer / 发送
grep "kafkaTemplate.send\|KafkaSender\|kafkaSender" --glob "*.java"

# Topic 定义
grep "topic\|TOPIC" --glob "*.java" --glob "*.yml" | grep -i "{功能名}"

# RabbitMQ
grep "@RabbitListener\|@RabbitHandler" --glob "*.java"
grep "rabbitTemplate.convertAndSend" --glob "*.java"
```

### 定时任务

```bash
# Spring @Scheduled
grep "@Scheduled" --glob "*.java"

# XXL-Job
grep "@XxlJob" --glob "*.java"

# Quartz
grep "implements Job\|extends QuartzJobBean" --glob "*.java"

# 包含特定功能的定时任务
grep "@Scheduled\|@XxlJob" --glob "*{功能名}*Job*.java" --glob "*{功能名}*Task*.java"
```

### 配置类和配置项

```bash
# Spring 配置类
grep "@Configuration\|@ConfigurationProperties" --glob "*{功能名}*.java"

# yml/yaml 配置
grep "{功能名}\|{英文名}" --glob "*.yml" --glob "*.yaml"

# properties 配置
grep "{功能名}" --glob "*.properties"

# 环境变量引用
grep "@Value.*{配置前缀}" --glob "*.java"
```

### 枚举和常量

```bash
# 枚举类
grep "enum {功能名}\|enum.*{功能名}" --glob "*.java"

# 常量类
grep "{功能名}.*=\|{FUNCTION_NAME}" --glob "*Constants*.java" --glob "*Const*.java" --glob "*Enum*.java"

# productKey / 产品标识（IoT 场景常见）
grep "productKey\|PRODUCT_KEY" --glob "*.java"
```

## 跨模块追踪

### 模块间通信发现

```bash
# 找出项目所有微服务模块
find . -name "pom.xml" -maxdepth 2 | head -20
# 或
find . -name "build.gradle" -maxdepth 2 | head -20

# 找出所有 Feign 客户端指向的服务
grep -r "@FeignClient" --include="*.java" | grep "name\|value"

# 找出所有 Kafka Topic
grep -r "topics\|@KafkaListener\|kafkaTemplate" --include="*.java" | grep -o '"[^"]*"' | sort -u
```

### 数据库层发现

```bash
# 找出所有实体类及其表名
grep -r "@TableName\|@Table\|@Document" --include="*.java"

# 找出 Flyway/Liquibase 迁移脚本
find . -name "*.sql" -path "*/migration*" -o -name "*.sql" -path "*/db/*"

# Redis 使用
grep "RedisTemplate\|StringRedisTemplate\|@Cacheable" --glob "*.java" | grep -i "{功能名}"
```

## 搜索结果的处理技巧

### 按模块分组

搜索结果通常很多，用目录前缀分组：

```bash
# 先搜索
grep "{关键词}" --glob "*.java"

# 然后在搜索结果中按模块分组查看
# 每个 {project}/src/main/java/... 前缀对应一个微服务模块
```

### 排除干扰

```bash
# 排除测试代码
grep "{关键词}" --glob "*.java"  # ripgrep 默认会排除 test

# 如果用 bash grep，需要手动排除
grep -r "{关键词}" --include="*.java" --exclude-dir=target --exclude-dir=test
```

### 确认文件层次

Java 文件的包路径直接反映了它的职责层次：

| 包路径包含 | 层次 |
|-----------|------|
| `entity` / `model` / `domain` / `po` | Entity |
| `mapper` / `dao` / `repository` | 数据访问 |
| `service` / `service/impl` | 业务逻辑 |
| `controller` / `rest` / `web` | HTTP 接口 |
| `feign` / `client` / `api` | 远程调用 |
| `config` / `configuration` | 配置 |
| `consumer` / `listener` / `handler` | 消息消费 |
| `job` / `task` / `schedule` | 定时任务 |
| `common` / `util` / `constant` | 工具/常量 |
| `dto` / `vo` / `request` / `response` | 传输对象 |
