# 数据库设计和API文档

## 1. 数据库设计

### 1.1 核心数据表

#### 1.1.1 用户表 (users)
```sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    avatar_url VARCHAR(255),
    role VARCHAR(20) DEFAULT 'USER', -- ADMIN, USER, GUEST
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, LOCKED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL
);
```

#### 1.1.2 菜单表 (menus)
```sql
CREATE TABLE menus (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    parent_id BIGINT NULL,
    menu_key VARCHAR(50) NOT NULL UNIQUE, -- 唯一标识符
    menu_name VARCHAR(100) NOT NULL, -- 显示名称
    menu_type VARCHAR(20) DEFAULT 'MENU', -- MENU, BUTTON, API
    icon VARCHAR(50),
    path VARCHAR(255), -- 路由路径
    component VARCHAR(255), -- 组件路径
    sort_order INT DEFAULT 0,
    is_hidden BOOLEAN DEFAULT FALSE,
    permission VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES menus(id) ON DELETE CASCADE
);
```

#### 1.1.3 技能表 (skills)
```sql
CREATE TABLE skills (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    skill_key VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50), -- AI, TOOLS, AUTOMATION等
    author_id BIGINT NOT NULL,
    version VARCHAR(20) DEFAULT '1.0.0',
    skill_content LONGTEXT NOT NULL, -- skill.md内容
    icon_url VARCHAR(255),
    tags JSON, -- 标签数组
    is_public BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    usage_count INT DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_category (category),
    INDEX idx_author (author_id)
);
```

#### 1.1.4 模型配置表 (model_configs)
```sql
CREATE TABLE model_configs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    config_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL, -- OPENAI, AZURE, CLAUDE, CUSTOM
    model_type VARCHAR(50), -- CHAT, COMPLETION, EMBEDDING
    base_url VARCHAR(500),
    api_key_encrypted TEXT NOT NULL,
    api_version VARCHAR(50),
    timeout_ms INT DEFAULT 30000,
    max_tokens INT DEFAULT 4096,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_config (user_id, config_name)
);
```

#### 1.1.5 API调用日志表 (api_logs)
```sql
CREATE TABLE api_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    model_config_id BIGINT NOT NULL,
    endpoint VARCHAR(100),
    request_method VARCHAR(10),
    request_body TEXT,
    response_status INT,
    response_body TEXT,
    tokens_used INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0.0,
    duration_ms INT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id) ON DELETE CASCADE,
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_model_time (model_config_id, created_at)
);
```

#### 1.1.6 本体表 (ontologies)
```sql
CREATE TABLE ontologies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    domain VARCHAR(100), -- 领域
    version VARCHAR(20) DEFAULT '1.0.0',
    schema_json JSON NOT NULL, -- 本体结构定义
    created_by BIGINT NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    entity_count INT DEFAULT 0,
    relation_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);
```

#### 1.1.7 数据集表 (datasets)
```sql
CREATE TABLE datasets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    ontology_id BIGINT NULL,
    file_type VARCHAR(20), -- CSV, JSON, EXCEL, PARQUET
    file_path VARCHAR(500),
    file_size BIGINT,
    row_count INT DEFAULT 0,
    column_count INT DEFAULT 0,
    schema_json JSON, -- 数据集结构定义
    tags JSON,
    is_processed BOOLEAN DEFAULT FALSE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ontology_id) REFERENCES ontologies(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_ontology (ontology_id)
);
```

### 1.2 关系表

#### 1.2.1 用户权限表 (user_permissions)
```sql
CREATE TABLE user_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    can_view BOOLEAN DEFAULT TRUE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_menu (user_id, menu_id)
);
```

#### 1.2.2 技能使用记录 (skill_usage)
```sql
CREATE TABLE skill_usage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    execution_result TEXT,
    success BOOLEAN DEFAULT TRUE,
    execution_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    INDEX idx_user_skill_time (user_id, skill_id, created_at)
);
```

## 2. API接口设计

### 2.1 认证相关API

#### 2.1.1 用户登录
```
POST /api/auth/login
Content-Type: application/json

请求体:
{
  "username": "admin",
  "password": "Admin@123456"
}

响应:
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "displayName": "管理员",
      "role": "ADMIN"
    }
  }
}
```

#### 2.1.2 刷新Token
```
POST /api/auth/refresh
Authorization: Bearer {refresh_token}

响应:
{
  "code": 200,
  "message": "Token刷新成功",
  "data": {
    "token": "new_access_token"
  }
}
```

### 2.2 菜单管理API

#### 2.2.1 获取菜单列表
```
GET /api/menus
Authorization: Bearer {token}
Params:
  - type: string (可选，过滤菜单类型)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "list": [
      {
        "id": 1,
        "menuKey": "agent-management",
        "menuName": "Agent管理",
        "icon": "RobotOutlined",
        "path": "/agent",
        "component": "AgentManagement",
        "children": [...]
      }
    ]
  }
}
```

#### 2.2.2 更新菜单名称
```
PUT /api/menus/{menuKey}
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "menuName": "Agent管理",
  "description": "Agent管理系统"
}

响应:
{
  "code": 200,
  "message": "菜单更新成功"
}
```

### 2.3 技能管理API

#### 2.3.1 获取技能列表
```
GET /api/skills
Authorization: Bearer {token}
Params:
  - page: int (页码)
  - size: int (每页数量)
  - category: string (分类)
  - search: string (搜索关键词)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "page": 1,
    "size": 20,
    "total": 100,
    "list": [
      {
        "id": 1,
        "skillKey": "weather-forecast",
        "name": "天气预报",
        "description": "获取指定城市的天气信息",
        "category": "TOOLS",
        "author": {
          "id": 1,
          "username": "admin"
        },
        "version": "1.0.0",
        "usageCount": 150,
        "rating": 4.5,
        "createdAt": "2026-03-17T08:00:00Z"
      }
    ]
  }
}
```

#### 2.3.2 创建技能
```
POST /api/skills
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "skillKey": "stock-analysis",
  "name": "股票分析",
  "description": "分析股票数据并生成报告",
  "category": "FINANCE",
  "skillContent": "# Stock Analysis Skill\n\n## Description\n...",
  "tags": ["finance", "analysis", "stock"],
  "isPublic": true
}

响应:
{
  "code": 201,
  "message": "技能创建成功",
  "data": {
    "id": 2,
    "skillKey": "stock-analysis",
    "name": "股票分析"
  }
}
```

#### 2.3.3 执行技能
```
POST /api/skills/{skillKey}/execute
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "parameters": {
    "symbol": "AAPL",
    "period": "1d"
  }
}

响应:
{
  "code": 200,
  "message": "执行成功",
  "data": {
    "result": "股票分析结果...",
    "executionTime": 1200,
    "success": true
  }
}
```

### 2.4 模型配置API

#### 2.4.1 获取模型配置列表
```
GET /api/model-configs
Authorization: Bearer {token}

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "id": 1,
      "configName": "OpenAI GPT-4",
      "provider": "OPENAI",
      "modelType": "CHAT",
      "baseUrl": "https://api.openai.com/v1",
      "isDefault": true,
      "isActive": true,
      "createdAt": "2026-03-17T08:00:00Z"
    }
  ]
}
```

#### 2.4.2 添加模型配置
```
POST /api/model-configs
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "configName": "Azure OpenAI",
  "provider": "AZURE",
  "modelType": "CHAT",
  "baseUrl": "https://your-resource.openai.azure.com",
  "apiKey": "your-api-key",
  "apiVersion": "2023-12-01-preview",
  "isDefault": false
}

响应:
{
  "code": 201,
  "message": "配置添加成功",
  "data": {
    "id": 2,
    "configName": "Azure OpenAI"
  }
}
```

#### 2.4.3 测试模型连接
```
POST /api/model-configs/{id}/test
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "testPrompt": "Hello, world!"
}

响应:
{
  "code": 200,
  "message": "连接测试成功",
  "data": {
    "connected": true,
    "response": "Hello! How can I help you today?",
    "latency": 450,
    "tokensUsed": 10
  }
}
```

#### 2.4.4 获取调用统计
```
GET /api/model-configs/{id}/stats
Authorization: Bearer {token}
Params:
  - startDate: string (开始日期)
  - endDate: string (结束日期)
  - interval: string (统计间隔: DAY, HOUR)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "totalCalls": 1500,
    "totalTokens": 1250000,
    "totalCost": 12.50,
    "dailyStats": [
      {
        "date": "2026-03-16",
        "callCount": 120,
        "tokenCount": 100000,
        "cost": 1.00
      }
    ]
  }
}
```

### 2.5 本体管理API

#### 2.5.1 获取本体列表
```
GET /api/ontologies
Authorization: Bearer {token}
Params:
  - domain: string (领域)
  - isPublic: boolean (是否公开)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "list": [
      {
        "id": 1,
        "name": "金融知识图谱",
        "description": "金融领域的本体定义",
        "domain": "FINANCE",
        "version": "1.0.0",
        "entityCount": 150,
        "relationCount": 300,
        "createdBy": {
          "id": 1,
          "username": "admin"
        },
        "createdAt": "2026-03-17T08:00:00Z"
      }
    ]
  }
}
```

#### 2.5.2 创建本体
```
POST /api/ontologies
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "name": "医疗本体",
  "description": "医疗领域的知识本体",
  "domain": "MEDICAL",
  "schemaJson": {
    "entities": [...],
    "relations": [...],
    "properties": [...]
  },
  "isPublic": true
}

响应:
{
  "code": 201,
  "message": "本体创建成功",
  "data": {
    "id": 2,
    "name": "医疗本体"
  }
}
```

### 2.6 数据集管理API

#### 2.6.1 上传数据集
```
POST /api/datasets/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

参数:
  - file: File (数据集文件)
  - name: string (数据集名称)
  - description: string (描述)
  - ontologyId: long (关联本体ID，可选)

响应:
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "datasetId": 1,
    "fileName": "stock_data.csv",
    "fileSize": 1048576,
    "rowCount": 10000,
    "uploadProgress": 100
  }
}
```

#### 2.6.2 获取数据集预览
```
GET /api/datasets/{id}/preview
Authorization: Bearer {token}
Params:
  - limit: int (预览行数，默认100)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "columns": ["date", "symbol", "open", "high", "low", "close", "volume"],
    "rows": [
      ["2026-03-17", "AAPL", 175.25, 176.80, 174.50, 176.10, 45210000],
      ...
    ],
    "totalRows": 10000,
    "sampleRows": 100
  }
}
```

#### 2.6.3 导出数据集
```
POST /api/datasets/{id}/export
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "format": "CSV", // CSV, JSON, EXCEL
  "columns": ["date", "symbol", "close"], // 可选，指定导出列
  "filters": { // 可选，过滤条件
    "symbol": "AAPL",
    "date": {
      "start": "2026-01-01",
      "end": "2026-03-17"
    }
  }
}

响应:
{
  "code": 200,
  "message": "导出任务已创建",
  "data": {
    "taskId": "export_123456",
    "status": "QUEUED",
    "estimatedTime": 30
  }
}
```

### 2.7 监控和统计API

#### 2.7.1 系统使用统计
```
GET /api/stats/system-usage
Authorization: Bearer {token}
Params:
  - period: string (统计周期: DAY, WEEK, MONTH)

响应:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "userCount": 50,
    "activeUserCount": 25,
    "skillExecutionCount": 1200,
    "apiCallCount": 8500,
    "dataStorage": 1024, // MB
    "dailyActivity": [
      {
        "date": "2026-03-16",
        "activeUsers": 20,
        "apiCalls": 450,
        "skillExecutions": 80
      }
    ]
  }
}
```

## 3. 前端组件设计

### 3.1 Vibe Coding页面组件结构
```typescript
// VibeCoding.tsx
const VibeCoding: React.FC = () => {
  return (
    <div className="vibe-coding">
      <VibeCodingToolbar />
      <div className="vibe-coding-content">
        <CodeEditor />
        <PreviewPanel />
        <DebugPanel />
      </div>
      <StatusBar />
    </div>
  );
};

// VibeCodingToolbar.tsx
const VibeCodingToolbar: React.FC = () => {
  const buttonGroups = [
    {
      name: '代码操作',
      buttons: [
        { key: 'generate', icon: <CodeOutlined />, label: '生成代码', onClick: handleGenerate },
        { key: 'format', icon: <FormOutlined />, label: '格式化', onClick: handleFormat },
        { key: 'analyze', icon: <SearchOutlined />, label: '代码分析', onClick: handleAnalyze }
      ]
    },
    {
      name: '调试部署',
      buttons: [
        { key: 'debug', icon: <BugOutlined />, label: '调试', onClick: handleDebug },
        { key: 'test', icon: <ExperimentOutlined />, label: '运行测试', onClick: handleTest },
        { key: 'deploy', icon: <RocketOutlined />, label: '部署', onClick: handleDeploy }
      ]
    }
  ];
  
  return (
    <div className="vibe-coding-toolbar">
      {buttonGroups.map(group => (
        <ButtonGroup key={group.name} title={group.name}>
          {group.buttons.map(btn => (
            <ToolbarButton
              key={btn.key}
              icon={btn.icon}
              label={btn.label}
              onClick={btn.onClick}
            />
          ))}
        </ButtonGroup>
      ))}
    </div>
  );
};
```

### 3.2 技能编辑器组件
```typescript
// SkillEditor.tsx
const SkillEditor: React.FC = () => {
  const [skillContent, setSkillContent] = useState('');
  
  return (
    <div className="skill-editor">
      <div className="editor-header">
        <SkillTabs />
        <EditorActions />
      </div>
      <div className="editor-content">
        <div className="code-editor">
          <MonacoEditor
            language="markdown"
            value={skillContent}
            onChange={setSkillContent}
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              wordWrap: 'on'
            }}
          />
        </div>
        <div className="preview-panel">
          <MarkdownPreview content={skillContent} />
        </div>
      </div>
      <div className="editor-footer">
        <ParameterConfig />
        <TestConsole />
      </div>
    </div>
  );
};
```

## 4. 安全设计

### 4.1 API Key加密存储
```java
@Service
public class ApiKeyEncryptionService {
    
    @Value("${encryption.aes-key}")
    private String aesKey;
    
    public String encryptApiKey(String apiKey) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            SecretKeySpec keySpec = new SecretKeySpec(aesKey.getBytes(), "AES");
            cipher.init(Cipher.ENCRYPT_MODE, keySpec);
            
            byte[] encrypted = cipher.doFinal(apiKey.getBytes());
            return Base64.getEncoder().encodeToString(encrypted);
        } catch (Exception e) {
            throw new RuntimeException("API Key加密失败", e);
        }
    }
    
    public String decryptApiKey(String encryptedKey) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            SecretKeySpec keySpec = new SecretKeySpec(aesKey.getBytes(), "AES");
            cipher.init(Cipher.DECRYPT_MODE, keySpec);
            
            byte[] decoded = Base64.getDecoder().decode(encryptedKey);
            byte[] decrypted = cipher.doFinal(decoded);
            return new String(decrypted);
        } catch (Exception e) {
            throw new RuntimeException("API Key解密失败", e);
        }
    }
}
```

### 4.2 请求频率限制
```java
@Configuration
public class RateLimitConfig {
    
    @Bean
    public RateLimiterRegistry rateLimiterRegistry() {
        return RateLimiterRegistry.custom()
            .addRateLimiterConfig("api-calls", 
                RateLimiterConfig.custom()
                    .limitForPeriod(100) // 每分钟100次
                    .limitRefreshPeriod(Duration.ofMinutes(1))
                    .timeoutDuration(Duration.ofSeconds(5))
                    .build())
            .addRateLimiterConfig("skill-executions",
                RateLimiterConfig.custom()
                    .limitForPeriod(50) // 每分钟50次
                    .limitRefreshPeriod(Duration.ofMinutes(1))
                    .timeoutDuration(Duration.ofSeconds(3))
                    .build())
            .build();
    }
}
```

## 5. 部署配置

### 5.1 Docker Compose配置
```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    
  redis:
    image: redis:7.0-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    
  backend:
    build: ./backend
    depends_on:
      - mysql
      - redis
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/${MYSQL_DATABASE}
      SPRING_DATASOURCE_USERNAME: ${MYSQL_USER}
      SPRING_DATASOURCE_PASSWORD: ${MYSQL_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
    ports:
      - "8080:8080"
    
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    
  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"

volumes:
  mysql_data:
  redis_data:
  grafana_data:
```

这份文档提供了完整的数据库设计和API接口规范，可以作为开发团队的详细技术参考。