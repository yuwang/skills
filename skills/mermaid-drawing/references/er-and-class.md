# ER 图和类图参考

## ER 图 (Entity Relationship Diagram)

### 基本语法

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : "下单"
    ORDER ||--|{ ORDER_LINE : "包含"
    PRODUCT ||--o{ ORDER_LINE : "属于"
```

### 关系类型

| 语法 | 含义 | 说明 |
|------|------|------|
| `\|\|--\|\|` | 一对一 | 两端都是恰好一个 |
| `\|\|--o{` | 一对多 | 左边一个，右边零或多个 |
| `\|{--\|\|` | 多对一 | 左边一个以上，右边恰好一个 |
| `o{--o{` | 多对多 | 两端都是零或多个 |
| `\|\|--o\|` | 一对零或一 | 左边恰好一个，右边零或一个 |

符号说明：
- `||` = 恰好一个 (exactly one)
- `o|` = 零或一 (zero or one)
- `}|` = 一个以上 (one or more)
- `o{` = 零或多个 (zero or more)

### 实体属性

```mermaid
erDiagram
    USER {
        bigint id PK "主键"
        varchar username UK "用户名，唯一"
        varchar email "邮箱"
        varchar password_hash "密码哈希"
        int status "状态: 0=禁用 1=正常"
        datetime created_at "创建时间"
    }

    ORDER {
        bigint id PK "主键"
        bigint user_id FK "关联用户"
        decimal total_amount "订单金额"
        int status "0=待付 1=已付 2=已发 3=完成"
        datetime created_at "创建时间"
    }

    USER ||--o{ ORDER : "拥有"
```

### 完整示例：电商系统

```mermaid
erDiagram
    USER ||--o{ ORDER : "下单"
    USER ||--o{ ADDRESS : "拥有"
    ORDER ||--|{ ORDER_ITEM : "包含"
    PRODUCT ||--o{ ORDER_ITEM : "被购买"
    PRODUCT }|--|| CATEGORY : "属于"
    ORDER ||--o| PAYMENT : "对应"

    USER {
        bigint id PK
        varchar username UK
        varchar phone UK
        int vip_level "0-5"
    }

    ORDER {
        bigint id PK
        bigint user_id FK
        decimal total_amount
        int status "0=待付 1=已付 2=已发"
        bigint address_id FK
    }

    PRODUCT {
        bigint id PK
        varchar name
        decimal price
        int stock
        bigint category_id FK
    }

    ORDER_ITEM {
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        int quantity
        decimal unit_price
    }
```

### ER 图最佳实践

1. **只画核心实体** — 不需要把所有表都放进去，聚焦业务核心
2. **标注关键字段** — PK、FK、UK 标记好，枚举值写在注释里
3. **关系标签用动词** — "下单"、"包含"、"属于" 比 "关联" 更清晰
4. **实体名用大写** — `USER`、`ORDER`（Mermaid ER 的惯例）

---

## 类图 (Class Diagram)

### 基本语法

```mermaid
classDiagram
    class Animal {
        +String name
        +int age
        +makeSound() void
    }

    class Dog {
        +String breed
        +fetch() void
    }

    Animal <|-- Dog : 继承
```

### 可见性修饰符

| 符号 | 含义 |
|------|------|
| `+` | public |
| `-` | private |
| `#` | protected |
| `~` | package/internal |

### 关系类型

```mermaid
classDiagram
    classA <|-- classB : 继承
    classC *-- classD : 组合
    classE o-- classF : 聚合
    classG --> classH : 关联
    classI ..> classJ : 依赖
    classK ..|> classL : 实现
```

| 语法 | 含义 | 说明 |
|------|------|------|
| `<\|--` | 继承 | 子类 → 父类 |
| `*--` | 组合 | 强拥有，生命周期一致 |
| `o--` | 聚合 | 弱拥有，可独立存在 |
| `-->` | 关联 | 引用关系 |
| `..>` | 依赖 | 使用关系 |
| `..\|>` | 实现 | 实现接口 |

### 完整示例：策略模式

```mermaid
classDiagram
    class PaymentService {
        -PaymentStrategy strategy
        +pay(amount) PayResult
        +setStrategy(strategy) void
    }

    class PaymentStrategy {
        <<interface>>
        +execute(amount) PayResult
        +supports(type) bool
    }

    class AlipayStrategy {
        -AlipayClient client
        +execute(amount) PayResult
        +supports(type) bool
    }

    class WechatPayStrategy {
        -WechatClient client
        +execute(amount) PayResult
        +supports(type) bool
    }

    class BankCardStrategy {
        -BankClient client
        +execute(amount) PayResult
        +supports(type) bool
    }

    PaymentService --> PaymentStrategy : 使用
    PaymentStrategy <|.. AlipayStrategy : 实现
    PaymentStrategy <|.. WechatPayStrategy : 实现
    PaymentStrategy <|.. BankCardStrategy : 实现
```

### 抽象类和接口

```mermaid
classDiagram
    class Shape {
        <<abstract>>
        #double x
        #double y
        +area()* double
        +perimeter()* double
        +move(dx, dy) void
    }

    class Serializable {
        <<interface>>
        +serialize() String
        +deserialize(data) void
    }

    class Circle {
        -double radius
        +area() double
        +perimeter() double
    }

    Shape <|-- Circle
    Serializable <|.. Circle
```

### 注解标记

```mermaid
classDiagram
    class UserController {
        <<RestController>>
        +getUser(id) User
        +createUser(dto) User
    }

    class UserService {
        <<Service>>
        -UserRepository repo
        +findById(id) User
    }

    class UserRepository {
        <<Repository>>
        +findById(id) Optional~User~
    }
```

### 泛型

```mermaid
classDiagram
    class List~T~ {
        +add(T item) void
        +get(int index) T
        +size() int
    }

    class BaseMapper~T~ {
        +selectById(id) T
        +insert(T entity) int
        +updateById(T entity) int
    }
```

### 类图最佳实践

1. **聚焦设计意图** — 不要把所有字段和方法都列出，只展示关键的
2. **标注设计模式** — 用 `<<interface>>`、`<<abstract>>`、`<<Service>>` 等注解
3. **关系不超过 10 条** — 太多关系线会变成蜘蛛网，拆分为多张图
4. **按层分组** — Controller → Service → Repository → Entity
