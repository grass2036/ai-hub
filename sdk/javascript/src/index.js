/**
 * AI Hub Platform JavaScript SDK
 * 企业级AI应用平台的JavaScript/Node.js开发工具包
 */

import { AIHubClient } from './client.js';
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

export {
    // Main client
    AIHubClient,

    // Exceptions
    AIHubError,
    APIError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    InsufficientQuotaError,
    ModelNotFoundError,
    ConnectionError,
    TimeoutError
};

// Default export
export default AIHubClient;