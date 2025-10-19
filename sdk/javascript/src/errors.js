/**
 * AI Hub SDK 异常类定义
 */

/**
 * AI Hub SDK 基���异常类
 */
export class AIHubError extends Error {
    /**
     * @param {string} message - 错误消息
     * @param {string} errorCode - 错误代码
     * @param {number} statusCode - HTTP状态码
     */
    constructor(message, errorCode = null, statusCode = null) {
        super(message);
        this.name = 'AIHubError';
        this.message = message;
        this.errorCode = errorCode;
        this.statusCode = statusCode;
    }
}

/**
 * API请求错误
 */
export class APIError extends AIHubError {
    /**
     * @param {string} message - 错误消息
     * @param {string} errorCode - 错误代码
     * @param {number} statusCode - HTTP状态码
     * @param {Response} response - HTTP响应对象
     */
    constructor(message, errorCode = null, statusCode = null, response = null) {
        super(message, errorCode, statusCode);
        this.name = 'APIError';
        this.response = response;
    }
}

/**
 * 认证错误
 */
export class AuthenticationError extends AIHubError {
    constructor(message = 'Authentication failed') {
        super(message, 'authentication_error', 401);
        this.name = 'AuthenticationError';
    }
}

/**
 * 速率限制错误
 */
export class RateLimitError extends AIHubError {
    /**
     * @param {string} message - 错误消息
     * @param {number} retryAfter - 重试等待时间（秒）
     */
    constructor(message = 'Rate limit exceeded', retryAfter = null) {
        super(message, 'rate_limit_exceeded', 429);
        this.name = 'RateLimitError';
        this.retryAfter = retryAfter;
    }
}

/**
 * 无效请求错误
 */
export class InvalidRequestError extends AIHubError {
    /**
     * @param {string} message - 错误消息
     * @param {string} param - 错误参数
     */
    constructor(message, param = null) {
        super(message, 'invalid_request_error', 400);
        this.name = 'InvalidRequestError';
        this.param = param;
    }
}

/**
 * 配额不足错误
 */
export class InsufficientQuotaError extends AIHubError {
    constructor(message = 'Insufficient quota') {
        super(message, 'insufficient_quota', 403);
        this.name = 'InsufficientQuotaError';
    }
}

/**
 * 模型未找到错误
 */
export class ModelNotFoundError extends AIHubError {
    /**
     * @param {string} model - 模型名称
     */
    constructor(model) {
        const message = `Model '${model}' not found`;
        super(message, 'model_not_found', 404);
        this.name = 'ModelNotFoundError';
        this.model = model;
    }
}

/**
 * 连接错误
 */
export class ConnectionError extends AIHubError {
    constructor(message = 'Failed to connect to AI Hub API') {
        super(message, 'connection_error');
        this.name = 'ConnectionError';
    }
}

/**
 * 超时错误
 */
export class TimeoutError extends AIHubError {
    constructor(message = 'Request timed out') {
        super(message, 'timeout_error');
        this.name = 'TimeoutError';
    }
}