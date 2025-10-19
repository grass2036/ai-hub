/**
 * AI Hub Platform JavaScript SDK 客户端
 * 提供与AI Hub API的完整交互功能
 */

import {
    AIHubError,
    APIError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    InsufficientQuotaError,
    ModelNotFoundError,
    ConnectionError,
    TimeoutError
} from './errors.js';

/**
 * AI Hub API 客户端
 */
export class AIHubClient {
    /**
     * @param {Object} options - 配置选项
     * @param {string} options.apiKey - API密钥
     * @param {string} options.baseURL - API基础URL
     * @param {number} options.timeout - 请求超时时间（毫秒）
     * @param {number} options.maxRetries - 最大重试次数
     * @param {string} options.userAgent - 用户代理字符串
     */
    constructor(options = {}) {
        const {
            apiKey,
            baseURL = 'https://api.aihub.com/api/v1',
            timeout = 60000,
            maxRetries = 3,
            userAgent = null
        } = options;

        if (!apiKey) {
            throw new AIHubError('API key is required');
        }

        this.apiKey = apiKey;
        this.baseURL = baseURL.replace(/\/$/, '');
        this.timeout = timeout;
        this.maxRetries = maxRetries;

        // 默认请求头
        this.defaultHeaders = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            'User-Agent': userAgent || `ai-hub-javascript/1.0.0`
        };

        // 子API客户端
        this.chat = new ChatAPI(this);
        this.models = new ModelsAPI(this);
        this.usage = new UsageAPI(this);
        this.keys = new KeysAPI(this);
    }

    /**
     * 发送HTTP请求
     * @param {string} method - HTTP方法
     * @param {string} endpoint - API端点
     * @param {Object} options - 请求选项
     * @param {Object} options.json - JSON数据
     * @param {Object} options.params - 查询参数
     * @param {boolean} options.stream - 是否流式响应
     * @param {Object} options.headers - 额外的请求头
     * @returns {Promise<Response|AsyncIterator>} 响应对象或流式迭代器
     */
    async makeRequest(method, endpoint, options = {}) {
        const {
            json = null,
            params = null,
            stream = false,
            headers = {}
        } = options;

        const url = new URL(endpoint.startsWith('/') ? endpoint.slice(1) : endpoint, this.baseURL + '/');

        // 添加查询参数
        if (params) {
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });
        }

        const requestOptions = {
            method,
            headers: { ...this.defaultHeaders, ...headers },
            signal: AbortSignal.timeout(this.timeout)
        };

        if (json) {
            requestOptions.body = JSON.stringify(json);
        }

        try {
            const response = await fetch(url.toString(), requestOptions);

            // 检查HTTP状态码
            if (response.status === 401) {
                throw new AuthenticationError();
            } else if (response.status === 403) {
                throw new InsufficientQuotaError();
            } else if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After');
                throw new RateLimitError(
                    'Rate limit exceeded',
                    retryAfter ? parseInt(retryAfter) : null
                );
            } else if (response.status === 404) {
                const modelName = json?.model || 'Unknown';
                throw new ModelNotFoundError(modelName);
            } else if (!response.ok) {
                await this.handleAPIError(response);
            }

            if (stream) {
                return this.createStreamIterator(response);
            } else {
                return response;
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new TimeoutError();
            } else if (error instanceof TypeError) {
                throw new ConnectionError(error.message);
            }
            throw error;
        }
    }

    /**
     * 处理API错误响应
     * @param {Response} response - HTTP响应
     */
    async handleAPIError(response) {
        let errorData;
        try {
            errorData = await response.json();
        } catch {
            errorData = {};
        }

        const error = errorData.error || {};
        const message = error.message || response.statusText || 'Unknown error';
        const errorCode = error.code || 'unknown_error';

        throw new APIError(
            message,
            errorCode,
            response.status,
            response
        );
    }

    /**
     * 创建流式响应迭代器
     * @param {Response} response - HTTP响应
     * @returns {AsyncIterator} 流式迭代器
     */
    async *createStreamIterator(response) {
        if (!response.body) {
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留最后一行（可能不完整）

                for (const line of lines) {
                    const chunk = this.parseStreamChunk(line);
                    if (chunk) {
                        yield chunk;
                    }
                }
            }

            // 处理最后的buffer
            if (buffer.trim()) {
                const chunk = this.parseStreamChunk(buffer);
                if (chunk) {
                    yield chunk;
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * 解析流式响应块
     * @param {string} line - 数据行
     * @returns {Object|null} 解析后的数据块
     */
    parseStreamChunk(line) {
        if (!line || !line.trim()) {
            return null;
        }

        const trimmedLine = line.trim();

        if (trimmedLine === 'data: [DONE]') {
            return null;
        }

        if (trimmedLine.startsWith('data: ')) {
            try {
                const dataStr = trimmedLine.slice(6); // 移除 'data: ' 前缀
                const data = JSON.parse(dataStr);

                // 处理不同的响应格式
                if (data.data) {
                    return data.data;
                }
                return data;
            } catch (error) {
                // 忽略解析错误的行
            }
        }

        return null;
    }

    /**
     * 解析响应数据
     * @param {Response} response - HTTP响应
     * @param {Class} ModelClass - 数据模型类
     * @returns {Promise<Object>} 解析后的数据
     */
    async parseResponse(response, ModelClass) {
        try {
            const data = await response.json();

            // 处理不同的响应格式
            if (data.data) {
                return new ModelClass(data.data);
            }
            return new ModelClass(data);
        } catch (error) {
            throw new APIError(`Failed to parse response: ${error.message}`);
        }
    }

    /**
     * 关闭客户端连接
     */
    close() {
        // 如果有需要清理的资源，在这里处理
    }
}

/**
 * 对话API
 */
class ChatAPI {
    constructor(client) {
        this.client = client;
    }

    /**
     * 创建对话完成
     * @param {Object} options - 请求选项
     * @param {string} options.model - 模型名称
     * @param {Array} options.messages - 消息列表
     * @param {number} options.temperature - 温度参数
     * @param {number} options.maxTokens - 最大token数
     * @param {number} options.topP - 核采样参数
     * @param {number} options.frequencyPenalty - 频率惩罚
     * @param {number} options.presencePenalty - 存在惩罚
     * @param {string|Array} options.stop - 停止词
     * @returns {Promise<ChatCompletionResponse>} 对话完成响应
     */
    async create(options) {
        const {
            model,
            messages,
            temperature,
            maxTokens,
            topP,
            frequencyPenalty,
            presencePenalty,
            stop,
            ...otherOptions
        } = options;

        const requestData = {
            model,
            messages,
            ...(temperature !== undefined && { temperature }),
            ...(maxTokens !== undefined && { max_tokens: maxTokens }),
            ...(topP !== undefined && { top_p: topP }),
            ...(frequencyPenalty !== undefined && { frequency_penalty: frequencyPenalty }),
            ...(presencePenalty !== undefined && { presence_penalty: presencePenalty }),
            ...(stop !== undefined && { stop }),
            ...otherOptions
        };

        const response = await this.client.makeRequest('POST', '/chat/completions', {
            json: requestData
        });

        return await this.client.parseResponse(response, ChatCompletionResponse);
    }

    /**
     * 流式对话完成
     * @param {Object} options - 请求选项（同create方法）
     * @returns {AsyncGenerator<ChatCompletionChunk>} 流式响应块生成器
     */
    async *stream(options) {
        const {
            model,
            messages,
            temperature,
            maxTokens,
            topP,
            frequencyPenalty,
            presencePenalty,
            stop,
            ...otherOptions
        } = options;

        const requestData = {
            model,
            messages,
            stream: true,
            ...(temperature !== undefined && { temperature }),
            ...(maxTokens !== undefined && { max_tokens: maxTokens }),
            ...(topP !== undefined && { top_p: topP }),
            ...(frequencyPenalty !== undefined && { frequency_penalty: frequencyPenalty }),
            ...(presencePenalty !== undefined && { presence_penalty: presencePenalty }),
            ...(stop !== undefined && { stop }),
            ...otherOptions
        };

        const stream = this.client.makeRequest('POST', '/chat/stream', {
            json: requestData,
            stream: true
        });

        for await (const chunk of stream) {
            yield new ChatCompletionChunk(chunk);
        }
    }
}

/**
 * 模型API
 */
class ModelsAPI {
    constructor(client) {
        this.client = client;
    }

    /**
     * 获取可用模型列表
     * @returns {Promise<Array<Model>>} 模型列表
     */
    async list() {
        const response = await this.client.makeRequest('GET', '/models');
        const data = await response.json();

        let modelsData;
        if (data.data) {
            modelsData = data.data;
        } else if (data.models) {
            modelsData = data.models;
        } else {
            modelsData = data;
        }

        return modelsData.map(modelData => new Model(modelData));
    }

    /**
     * 获取特定模型信息
     * @param {string} modelId - 模型ID
     * @returns {Promise<Model>} 模型信息
     */
    async retrieve(modelId) {
        const response = await this.client.makeRequest('GET', `/models/${modelId}`);
        return await this.client.parseResponse(response, Model);
    }
}

/**
 * 使用统计API
 */
class UsageAPI {
    constructor(client) {
        this.client = client;
    }

    /**
     * 获取配额信息
     * @returns {Promise<QuotaInfo>} 配额信息
     */
    async quota() {
        const response = await this.client.makeRequest('GET', '/developer/keys/quota');
        return await this.client.parseResponse(response, QuotaInfo);
    }

    /**
     * 获取使用统计
     * @param {number} days - 统计天数
     * @returns {Promise<UsageStats>} 使用统计
     */
    async stats(days = 30) {
        const response = await this.client.makeRequest('GET', '/developer/usage', {
            params: { days }
        });
        return await this.client.parseResponse(response, UsageStats);
    }
}

/**
 * API密钥管理API
 */
class KeysAPI {
    constructor(client) {
        this.client = client;
    }

    /**
     * 获取API密钥列表
     * @param {boolean} includeInactive - 是否包含非活跃密钥
     * @returns {Promise<Array<APIKey>>} API密钥列表
     */
    async list(includeInactive = false) {
        const response = await this.client.makeRequest('GET', '/developer/keys/keys', {
            params: { include_inactive: includeInactive }
        });
        const data = await response.json();
        const keysData = data.data?.api_keys || [];
        return keysData.map(keyData => new APIKey(keyData));
    }

    /**
     * 创建API密钥
     * @param {Object} options - 创建选项
     * @param {string} options.name - 密钥名称
     * @param {Array} options.permissions - 权限列表
     * @param {number} options.rateLimit - 速率限制
     * @param {Array} options.allowedModels - 允许的模型
     * @param {number} options.expiresDays - 过期天数
     * @returns {Promise<APIKey>} 创建的API密钥
     */
    async create(options) {
        const {
            name,
            permissions,
            rateLimit,
            allowedModels,
            expiresDays
        } = options;

        const requestData = { name };

        if (permissions) requestData.permissions = permissions;
        if (rateLimit) requestData.rate_limit = rateLimit;
        if (allowedModels) requestData.allowed_models = allowedModels;
        if (expiresDays) requestData.expires_days = expiresDays;

        const response = await this.client.makeRequest('POST', '/developer/keys/keys', {
            json: requestData
        });
        const data = await response.json();
        return new APIKey(data.data);
    }

    /**
     * 删除API密钥
     * @param {string} keyId - 密钥ID
     * @returns {Promise<boolean>} 是否删除成功
     */
    async delete(keyId) {
        try {
            await this.client.makeRequest('DELETE', `/developer/keys/keys/${keyId}`);
            return true;
        } catch (error) {
            return false;
        }
    }
}

// 数据模型类
export class ChatCompletionResponse {
    constructor(data) {
        this.id = data.id;
        this.object = data.object || 'chat.completion';
        this.created = data.created;
        this.model = data.model;
        this.choices = (data.choices || []).map(choice => new Choice(choice));
        this.usage = data.usage ? new Usage(data.usage) : null;
        this.cost = data.cost;
    }

    get firstChoice() {
        return this.choices[0] || null;
    }

    get content() {
        return this.firstChoice?.get?.() || null;
    }
}

export class ChatCompletionChunk {
    constructor(data) {
        this.id = data.id;
        this.object = data.object || 'chat.completion.chunk';
        this.created = data.created;
        this.model = data.model;
        this.choices = (data.choices || []).map(choice => new Choice(choice));
    }

    get firstChoice() {
        return this.choices[0] || null;
    }

    get content() {
        return this.firstChoice?.get?.() || null;
    }
}

export class Choice {
    constructor(data) {
        this.index = data.index;
        this.message = data.message;
        this.delta = data.delta;
        this.finishReason = data.finish_reason;
    }

    get() {
        return this.message?.content || this.delta?.content || null;
    }
}

export class Usage {
    constructor(data) {
        this.promptTokens = data.prompt_tokens || 0;
        this.completionTokens = data.completion_tokens || 0;
        this.totalTokens = data.total_tokens || 0;
    }

    get cost() {
        // 简化的成本计算
        return this.totalTokens * 0.00001;
    }
}

export class Model {
    constructor(data) {
        this.id = data.id;
        this.object = data.object || 'model';
        this.created = data.created;
        this.ownedBy = data.owned_by;
        this.name = data.name;
        this.description = data.description;
        this.pricing = data.pricing;
        this.category = data.category;
    }
}

export class APIKey {
    constructor(data) {
        this.id = data.id;
        this.name = data.name;
        this.keyPrefix = data.key_prefix;
        this.permissions = data.permissions || [];
        this.rateLimit = data.rate_limit;
        this.allowedModels = data.allowed_models || [];
        this.isActive = data.is_active;
        this.expiresAt = data.expires_at ? new Date(data.expires_at) : null;
        this.lastUsedAt = data.last_used_at ? new Date(data.last_used_at) : null;
        this.usageCount = data.usage_count || 0;
        this.totalTokensUsed = data.total_tokens_used || 0;
        this.createdAt = data.created_at ? new Date(data.created_at) : null;
        this.apiKey = data.api_key; // 仅在创建时返回
    }
}

export class QuotaInfo {
    constructor(data) {
        this.monthlyQuota = data.monthly_quota;
        this.monthlyUsed = data.monthly_used;
        this.monthlyRemaining = data.monthly_remaining;
        this.monthlyUsagePercent = data.monthly_usage_percent;
        this.monthlyCost = data.monthly_cost;
        this.activeApiKeys = data.active_api_keys;
        this.maxApiKeys = data.max_api_keys;
        this.resetDate = data.reset_date;
    }
}

export class UsageStats {
    constructor(data) {
        this.periodDays = data.period_days;
        this.totalRequests = data.total_requests;
        this.totalTokens = data.total_tokens;
        this.totalCost = data.total_cost;
        this.avgResponseTime = data.avg_response_time;
        this.successRate = data.success_rate;
        this.modelUsage = data.model_usage || {};
        this.dailyUsage = data.daily_usage || {};
    }
}