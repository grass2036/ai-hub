# Week 2 API Documentation
# Week 2 API 文档

## 概述

本文档详细描述了AI Hub平台Week 2开发的企业多租户架构API接口，包括企业管理、团队管理、预算控制、权限系统等核心功能。

## 基础信息

- **Base URL**: `http://localhost:8001/api/v1`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

### 获取访问令牌

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 使用访问令牌

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 企业管理 API

### 获取企业列表

```http
GET /organizations
Authorization: Bearer {token}
```

**响应:**
```json
{
  "organizations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Acme Corporation",
      "slug": "acme-corp",
      "description": "A technology company",
      "logo_url": "https://example.com/logo.png",
      "plan": "pro",
      "status": "active",
      "member_count": 15,
      "team_count": 5,
      "current_month_spend": 1250.50,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-20T15:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 创建企业

```http
POST /organizations
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Company",
  "slug": "new-company",
  "description": "A new technology company",
  "plan": "pro",
  "logo_url": "https://example.com/logo.png"
}
```

**响应 (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "New Company",
  "slug": "new-company",
  "description": "A new technology company",
  "logo_url": "https://example.com/logo.png",
  "plan": "pro",
  "status": "active",
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:00:00Z"
}
```

### 获取企业详情

```http
GET /organizations/{organization_id}
Authorization: Bearer {token}
```

**响应:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "description": "A technology company",
  "logo_url": "https://example.com/logo.png",
  "plan": "pro",
  "status": "active",
  "settings": {
    "timezone": "UTC",
    "language": "en"
  },
  "member_count": 15,
  "team_count": 5,
  "api_key_count": 3,
  "current_month_spend": 1250.50,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-20T15:30:00Z"
}
```

### 更新企业信息

```http
PUT /organizations/{organization_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Company Name",
  "description": "Updated description",
  "logo_url": "https://example.com/new-logo.png",
  "plan": "enterprise"
}
```

### 删除企业

```http
DELETE /organizations/{organization_id}
Authorization: Bearer {token}
```

**响应 (204 No Content)**

## 团队管理 API

### 获取企业团队列表

```http
GET /organizations/{organization_id}/teams
Authorization: Bearer {token}
```

**响应:**
```json
{
  "teams": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "organization_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Engineering Team",
      "description": "Software development team",
      "parent_team_id": null,
      "member_count": 8,
      "sub_team_count": 2,
      "current_month_spend": 750.25,
      "created_at": "2025-01-16T09:00:00Z",
      "updated_at": "2025-01-19T14:20:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 创建团队

```http
POST /organizations/{organization_id}/teams
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Marketing Team",
  "description": "Digital marketing team",
  "parent_team_id": null
}
```

### 获取团队详情

```http
GET /teams/{team_id}
Authorization: Bearer {token}
```

**响应:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Engineering Team",
  "description": "Software development team",
  "parent_team_id": null,
  "settings": {
    "auto_assign_new_members": false
  },
  "member_count": 8,
  "sub_team_count": 2,
  "current_month_spend": 750.25,
  "created_at": "2025-01-16T09:00:00Z",
  "updated_at": "2025-01-19T14:20:00Z"
}
```

### 更新团队信息

```http
PUT /teams/{team_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Team Name",
  "description": "Updated description",
  "parent_team_id": "parent-team-id"
}
```

### 删除团队

```http
DELETE /teams/{team_id}
Authorization: Bearer {token}
```

## 成员管理 API

### 获取企业成员列表

```http
GET /organizations/{organization_id}/members
Authorization: Bearer {token}
```

**响应:**
```json
{
  "members": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "user_id": "880e8400-e29b-41d4-a716-446655440000",
      "organization_id": "550e8400-e29b-41d4-a716-446655440000",
      "team_id": "660e8400-e29b-41d4-a716-446655440000",
      "role": "owner",
      "user_name": "John Doe",
      "user_email": "john.doe@example.com",
      "team_name": "Engineering Team",
      "joined_at": "2025-01-15T10:00:00Z",
      "invited_by": "880e8400-e29b-41d4-a716-446655440001"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 邀请成员

```http
POST /organizations/{organization_id}/invite
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "newmember@example.com",
  "role": "member",
  "team_id": "660e8400-e29b-41d4-a716-446655440000",
  "permissions": {
    "teams:view": true,
    "usage:view": true
  }
}
```

### 更新成员角色

```http
PUT /organizations/{organization_id}/members/{member_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "role": "admin",
  "team_id": "660e8400-e29b-41d4-a716-446655440001",
  "permissions": {
    "teams:create": true,
    "teams:edit": true,
    "members:invite": true
  }
}
```

### 移除成员

```http
DELETE /organizations/{organization_id}/members/{member_id}
Authorization: Bearer {token}
```

## 预算管理 API

### 获取企业预算列表

```http
GET /organizations/{organization_id}/budgets
Authorization: Bearer {token}
```

**响应:**
```json
{
  "budgets": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "organization_id": "550e8400-e29b-41d4-a716-446655440000",
      "monthly_limit": 5000.00,
      "current_spend": 1250.50,
      "alert_threshold": 80.0,
      "currency": "USD",
      "status": "active",
      "usage_percentage": 25.01,
      "remaining_budget": 3749.50,
      "is_alert_threshold_reached": false,
      "is_budget_exceeded": false,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-20T15:30:00Z"
    }
  ],
  "total": 1
}
```

### 创建预算

```http
POST /organizations/{organization_id}/budgets
Authorization: Bearer {token}
Content-Type: application/json

{
  "monthly_limit": 3000.00,
  "alert_threshold": 75.0,
  "currency": "USD"
}
```

### 更新预算设置

```http
PUT /organizations/{organization_id}/budgets/{budget_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "monthly_limit": 4000.00,
  "alert_threshold": 85.0,
  "status": "active"
}
```

### 获取预算使用统计

```http
GET /organizations/{organization_id}/budgets/usage
Authorization: Bearer {token}
Query Parameters:
  - period: "today" | "yesterday" | "this_week" | "last_week" | "this_month" | "last_month" | "last_30_days"
```

**响应:**
```json
{
  "period": "this_month",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-31T23:59:59Z",
  "total_spend": 1250.50,
  "monthly_limit": 5000.00,
  "usage_percentage": 25.01,
  "remaining_budget": 3749.50,
  "daily_average": 62.53,
  "projected_monthly_spend": 1875.75,
  "days_remaining_in_month": 11,
  "budget_status": "healthy",
  "alerts": [],
  "spending_by_day": [
    {
      "date": "2025-01-15",
      "spend": 45.25,
      "requests": 23
    }
  ],
  "spending_by_service": [
    {
      "service": "openrouter",
      "spend": 950.30,
      "percentage": 76.02
    }
  ],
  "spending_by_team": [
    {
      "team_id": "660e8400-e29b-41d4-a716-446655440000",
      "team_name": "Engineering Team",
      "spend": 750.25,
      "percentage": 60.00
    }
  ]
}
```

## API密钥管理 API

### 获取企业API密钥列表

```http
GET /organizations/{organization_id}/api-keys
Authorization: Bearer {token}
```

**响应:**
```json
{
  "api_keys": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440000",
      "organization_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Production API Key",
      "key_prefix": "org_abc123",
      "status": "active",
      "permissions": {
        "chat": ["read", "write"],
        "models": ["read"]
      },
      "rate_limit": 100,
      "monthly_quota": 100000,
      "current_month_usage": 15420,
      "daily_average_usage": 514.0,
      "quota_usage_percentage": 15.42,
      "is_active": true,
      "is_expired": false,
      "last_used_at": "2025-01-20T14:30:00Z",
      "created_by": "880e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-01-15T10:00:00Z",
      "expires_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 创建API密钥

```http
POST /organizations/{organization_id}/api-keys
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New API Key",
  "permissions": {
    "chat": ["read", "write"],
    "models": ["read"]
  },
  "rate_limit": 200,
  "monthly_quota": 500000,
  "expires_at": "2026-01-20T10:00:00Z"
}
```

**响应 (包含实际密钥，仅显示一次):**
```json
{
  "api_key": "org_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",
  "key_details": {
    "id": "bb0e8400-e29b-41d4-a716-446655440001",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "New API Key",
    "key_prefix": "org_abc123",
    "status": "active",
    "permissions": {
      "chat": ["read", "write"],
      "models": ["read"]
    },
    "rate_limit": 200,
    "monthly_quota": 500000,
    "created_at": "2025-01-20T16:00:00Z",
    "expires_at": "2026-01-20T10:00:00Z"
  }
}
```

### 更新API密钥

```http
PUT /api-keys/{api_key_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated API Key",
  "permissions": {
    "chat": ["read"],
    "models": ["read"]
  },
  "rate_limit": 150,
  "status": "suspended"
}
```

### 撤销API密钥

```http
POST /api-keys/{api_key_id}/revoke
Authorization: Bearer {token}
```

### 获取API密钥使用统计

```http
GET /organizations/{organization_id}/api-keys/usage
Authorization: Bearer {token}
Query Parameters:
  - period: "today" | "yesterday" | "this_week" | "this_month" | "last_month" | "last_30_days"
```

## 使用统计 API

### 获取企业使用统计

```http
GET /organizations/{organization_id}/usage-stats
Authorization: Bearer {token}
Query Parameters:
  - period: "today" | "yesterday" | "this_week" | "this_month" | "last_month" | "last_30_days"
  - granularity: "hour" | "day" | "week" | "month"
```

**响应:**
```json
{
  "period": "this_month",
  "granularity": "day",
  "summary": {
    "total_requests": 15420,
    "total_tokens": 2345678,
    "total_cost": 1250.50,
    "average_tokens_per_request": 152.15,
    "most_used_model": "gpt-4",
    "most_used_service": "openrouter"
  },
  "time_series": [
    {
      "timestamp": "2025-01-15T00:00:00Z",
      "requests": 523,
      "tokens": 79845,
      "cost": 42.50
    }
  ],
  "model_breakdown": [
    {
      "model": "gpt-4",
      "requests": 8234,
      "tokens": 1234567,
      "cost": 856.30,
      "percentage": 68.49
    }
  ],
  "service_breakdown": [
    {
      "service": "openrouter",
      "requests": 12345,
      "tokens": 1987654,
      "cost": 950.30,
      "percentage": 76.02
    }
  ],
  "team_breakdown": [
    {
      "team_id": "660e8400-e29b-41d4-a716-446655440000",
      "team_name": "Engineering Team",
      "requests": 9876,
      "tokens": 1543210,
      "cost": 750.25,
      "percentage": 60.00
    }
  ]
}
```

## 权限系统

### 角色定义

| 角色 | 权限级别 | 描述 |
|------|----------|------|
| `owner` | 最高 | 拥有所有权限，包括删除组织 |
| `admin` | 高 | 管理权限，但不能删除组织 |
| `member` | 中 | 基础成员权限 |
| `viewer` | 低 | 只读权限 |

### 权限列表

#### 组织权限
- `organization:delete` - 删除组织
- `organization:edit` - 编辑组织信息
- `members:invite` - 邀请成员
- `members:remove` - 移除成员
- `members:edit` - 编辑成员权限
- `teams:create` - 创建团队
- `teams:edit` - 编辑团队
- `teams:delete` - 删除团队
- `budgets:edit` - 编辑预算
- `api_keys:create` - 创建API密钥
- `api_keys:delete` - 删除API密钥
- `billing:view` - 查看账单
- `billing:edit` - 编辑账单
- `usage:view` - 查看使用统计

### 权限验证

API会自动验证用户的权限。如果用户没有所需权限，将返回403 Forbidden错误。

**错误响应示例:**
```json
{
  "error": {
    "message": "User does not have permission to delete organization",
    "error_code": "PERMISSION_DENIED",
    "details": {
      "user_id": "880e8400-e29b-41d4-a716-446655440000",
      "resource": "organization",
      "action": "delete",
      "required_role": "owner",
      "current_role": "admin"
    }
  }
}
```

## 错误处理

### 标准错误格式

```json
{
  "error": {
    "message": "Error description",
    "error_code": "ERROR_CODE",
    "details": {
      "field": "additional_error_details"
    }
  }
}
```

### 常见HTTP状态码

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器内部错误 |

### 具体错误代码

| 错误代码 | 描述 |
|----------|------|
| `ORG_NOT_FOUND` | 组织不存在 |
| `TEAM_NOT_FOUND` | 团队不存在 |
| `USER_NOT_FOUND` | 用户不存在 |
| `PERMISSION_DENIED` | 权限不足 |
| `INSUFFICIENT_ROLE` | 角色权限不足 |
| `BUDGET_EXCEEDED` | 预算超限 |
| `QUOTA_EXCEEDED` | 配额超限 |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 |
| `API_KEY_EXPIRED` | API密钥已过期 |
| `API_KEY_REVOKED` | API密钥已撤销 |
| `VALIDATION_ERROR` | 数据验证错误 |

## 速率限制

### 全局限速
- **限制**: 每分钟1000次请求
- **窗口**: 1分钟滑动窗口

### API密钥限速
- **默认**: 每分钟100次请求
- **可配置**: 1-10,000次/分钟
- **执行**: 基于API密钥独立计算

### 响应头
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

## 分页

### 请求参数
- `page`: 页码 (1-based，默认1)
- `page_size`: 每页数量 (默认20，最大100)

### 响应格式
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "has_next": true,
  "has_prev": false
}
```

## 版本控制

API使用语义化版本控制，当前版本为`v1`。

### 版本策略
- `v1.x.x`: 稳定版本，向后兼容
- `v2.x.x`: 重大变更，可能不兼容

### 向后兼容
- 新增字段不会破坏兼容性
- 删除字段会通过版本控制处理
- 字段类型变更会通过版本控制处理

## SDK和示例代码

### Python SDK示例

```python
import requests

class AIHubClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def get_organizations(self):
        response = requests.get(
            f"{self.base_url}/organizations",
            headers=self.headers
        )
        return response.json()

    def create_organization(self, name, slug, description=""):
        data = {
            "name": name,
            "slug": slug,
            "description": description
        }
        response = requests.post(
            f"{self.base_url}/organizations",
            json=data,
            headers=self.headers
        )
        return response.json()

# 使用示例
client = AIHubClient("http://localhost:8001/api/v1", "your-api-key")
orgs = client.get_organizations()
new_org = client.create_organization("My Company", "my-company")
```

### JavaScript SDK示例

```javascript
class AIHubClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async getOrganizations() {
        const response = await fetch(`${this.baseUrl}/organizations`, {
            headers: this.headers
        });
        return response.json();
    }

    async createOrganization(name, slug, description = '') {
        const data = { name, slug, description };
        const response = await fetch(`${this.baseUrl}/organizations`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }
}

// 使用示例
const client = new AIHubClient('http://localhost:8001/api/v1', 'your-api-key');
const orgs = await client.getOrganizations();
const newOrg = await client.createOrganization('My Company', 'my-company');
```

## 最佳实践

### 1. 认证和安全
- 使用HTTPS进行所有API调用
- 安全存储API密钥
- 定期轮换API密钥
- 使用最小权限原则

### 2. 错误处理
- 实现指数退避重试机制
- 记录详细的错误日志
- 优雅处理网络错误
- 验证API响应数据

### 3. 性能优化
- 使用适当的缓存策略
- 实现请求批处理
- 监控API使用情况
- 遵循速率限制

### 4. 数据验证
- 验证输入数据格式
- 处理边界情况
- 实现客户端验证
- 检查API响应数据

## 更新日志

### v1.0.0 (2025-01-20)
- 初始版本发布
- 实现基础多租户架构
- 支持企业管理、团队管理、预算控制
- 完整的权限系统
- API密钥管理
- 使用统计和监控

---

此文档将随着API的更新而持续维护。如有问题或建议，请联系开发团队。