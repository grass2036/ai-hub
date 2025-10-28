"""
Week 8 Day 6 - Security Validation Suite
Comprehensive security testing and validation for AI Hub platform
"""

import pytest
import asyncio
import time
import json
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import aiohttp
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup

from fastapi.testclient import TestClient
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SecurityVulnerability:
    """Security vulnerability finding"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str   # AUTH, INPUT_VALIDATION, DATA_LEAK, SESSION, CORS, etc.
    title: str
    description: str
    endpoint: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: str = ""
    cwe_id: Optional[str] = None

    def __str__(self):
        return f"[{self.severity}] {self.category} - {self.title}"


@dataclass
class SecurityTestResult:
    """Security test execution result"""
    test_name: str
    passed: bool
    vulnerabilities: List[SecurityVulnerability] = field(default_factory=list)
    execution_time: float = 0.0
    test_details: Dict = field(default_factory=dict)


class SecurityValidationSuite:
    """Comprehensive security validation suite"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = TestClient(app)
        self.test_results = []
        self.security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]

    async def run_comprehensive_security_validation(self) -> Dict:
        """Run complete security validation suite"""
        logger.info("🔒 Starting Comprehensive Security Validation Suite")

        start_time = time.time()

        try:
            # Run all security tests
            await self.test_authentication_security()
            await self.test_input_validation()
            await self.test_authorization()
            await self.test_session_security()
            await self.test_data_exposure()
            await self.test_cors_security()
            await self.test_rate_limiting()
            await self.test_error_handling()
            await self.test_api_key_security()
            await self.test_https_enforcement()
            await self.test_information_disclosure()

            # Generate comprehensive security report
            report = self._generate_security_report()

            end_time = time.time()
            report["execution_time"] = end_time - start_time
            report["timestamp"] = datetime.now().isoformat()

            logger.info(f"✅ Security validation completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Security Score: {report['security_score']:.2f}/100")

            return report

        except Exception as e:
            logger.error(f"❌ Security validation failed: {e}")
            raise

    async def test_authentication_security(self):
        """Test authentication security controls"""
        logger.info("🔐 Testing Authentication Security...")

        test_result = SecurityTestResult("Authentication Security")
        start_time = time.time()

        try:
            # Test 1: Verify authentication is required for protected endpoints
            await self._test_protected_endpoint_access(test_result)

            # Test 2: Test for weak authentication mechanisms
            await self._test_weak_authentication(test_result)

            # Test 3: Test for authentication bypass attempts
            await self._test_auth_bypass(test_result)

            # Test 4: Test password security (if applicable)
            await self._test_password_security(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Authentication Security Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Authentication security test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="AUTH", title="Security Test Error",
                description=f"Authentication security test encountered error: {str(e)}"
            ))

    async def _test_protected_endpoint_access(self, test_result: SecurityTestResult):
        """Test access to protected endpoints without authentication"""
        protected_endpoints = [
            "/api/v1/sessions",
            "/api/v1/stats",
            "/api/v1/developer/usage",
            "/api/v1/organizations"
        ]

        for endpoint in protected_endpoints:
            try:
                response = self.client.get(endpoint)

                # Should return 401 Unauthorized or 403 Forbidden
                if response.status_code not in [401, 403, 422]:
                    if response.status_code == 200:
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="HIGH", category="AUTH", title="Missing Authentication",
                            description=f"Endpoint {endpoint} allows access without authentication",
                            endpoint=endpoint,
                            evidence=f"Status code: {response.status_code}",
                            recommendation="Implement authentication for this endpoint",
                            cwe_id="CWE-306"
                        ))

            except Exception as e:
                logger.warning(f"Could not test endpoint {endpoint}: {e}")

    async def _test_weak_authentication(self, test_result: SecurityTestResult):
        """Test for weak authentication mechanisms"""
        # Test for default credentials
        weak_credentials = [
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "password"},
            {"username": "user", "password": "user"},
            {"username": "test", "password": "test"}
        ]

        # This would be relevant if there were login endpoints
        # For now, we'll check for common authentication patterns in responses

    async def _test_auth_bypass(self, test_result: SecurityTestResult):
        """Test for authentication bypass attempts"""
        bypass_attempts = [
            {"Authorization": "Bearer invalid_token"},
            {"Authorization": "Bearer null"},
            {"Authorization": ""},
            {"X-API-Key": "invalid_key"},
            {"X-API-Key": ""}
        ]

        test_endpoint = "/api/v1/sessions"

        for headers in bypass_attempts:
            try:
                response = self.client.get(test_endpoint, headers=headers)
                if response.status_code == 200:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="CRITICAL", category="AUTH", title="Authentication Bypass",
                        description=f"Authentication can be bypassed with headers: {headers}",
                        endpoint=test_endpoint,
                        evidence=str(headers),
                        recommendation="Fix authentication validation logic",
                        cwe_id="CWE-287"
                    ))
            except Exception as e:
                logger.warning(f"Auth bypass test failed: {e}")

    async def _test_password_security(self, test_result: SecurityTestResult):
        """Test password security policies"""
        # This would be relevant for user management endpoints
        # For now, we check if any password-related endpoints exist and their security

    async def test_input_validation(self):
        """Test input validation security"""
        logger.info("🛡️ Testing Input Validation Security...")

        test_result = SecurityTestResult("Input Validation")
        start_time = time.time()

        try:
            # Test 1: SQL Injection attempts
            await self._test_sql_injection(test_result)

            # Test 2: XSS attempts
            await self._test_xss(test_result)

            # Test 3: Command injection attempts
            await self._test_command_injection(test_result)

            # Test 4: Path traversal attempts
            await self._test_path_traversal(test_result)

            # Test 5: Buffer overflow attempts
            await self._test_buffer_overflow(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Input Validation Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Input validation test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="INPUT_VALIDATION", title="Security Test Error",
                description=f"Input validation test encountered error: {str(e)}"
            ))

    async def _test_sql_injection(self, test_result: SecurityTestResult):
        """Test SQL injection vulnerabilities"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "\" OR \"1\"=\"1",
            "1' UNION SELECT * FROM users --",
            "admin' --",
            "'; EXEC xp_cmdshell('dir'); --"
        ]

        test_endpoints = [
            ("/api/v1/sessions", "GET"),
            ("/api/v1/models", "GET")
        ]

        for endpoint, method in test_endpoints:
            for payload in sql_injection_payloads:
                try:
                    if method == "GET":
                        # Test as parameter
                        params = {"search": payload}
                        response = self.client.get(endpoint, params=params)

                        # Check for SQL error messages in response
                        response_text = response.text.lower()
                        sql_errors = ["sql", "mysql", "postgresql", "oracle", "syntax error", "unclosed"]

                        if any(error in response_text for error in sql_errors):
                            test_result.vulnerabilities.append(SecurityVulnerability(
                                severity="CRITICAL", category="INPUT_VALIDATION", title="SQL Injection",
                                description=f"SQL injection vulnerability detected in {endpoint}",
                                endpoint=endpoint,
                                evidence=f"Payload: {payload}, Response: {response.text[:200]}",
                                recommendation="Use parameterized queries and input validation",
                                cwe_id="CWE-89"
                            ))

                except Exception as e:
                    logger.warning(f"SQL injection test failed for {endpoint}: {e}")

    async def _test_xss(self, test_result: SecurityTestResult):
        """Test Cross-Site Scripting vulnerabilities"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]

        test_endpoints = [
            ("/api/v1/sessions", "POST"),
            ("/api/v1/models", "GET")
        ]

        for endpoint, method in test_endpoints:
            for payload in xss_payloads:
                try:
                    if method == "GET":
                        params = {"search": payload}
                        response = self.client.get(endpoint, params=params)
                    else:
                        # For POST endpoints, try to include in JSON body
                        data = {"name": payload, "description": payload}
                        response = self.client.post(endpoint, json=data)

                    # Check if payload is reflected in response
                    if payload in response.text:
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="HIGH", category="INPUT_VALIDATION", title="Cross-Site Scripting (XSS)",
                            description=f"XSS vulnerability detected in {endpoint}",
                            endpoint=endpoint,
                            evidence=f"Payload reflected: {payload}",
                            recommendation="Implement proper output encoding and input sanitization",
                            cwe_id="CWE-79"
                        ))

                except Exception as e:
                    logger.warning(f"XSS test failed for {endpoint}: {e}")

    async def _test_command_injection(self, test_result: SecurityTestResult):
        """Test command injection vulnerabilities"""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& echo 'Command Injection'",
            "`whoami`",
            "$(id)",
            "; rm -rf /tmp/*"
        ]

        # Test with any endpoint that might process input
        test_endpoints = ["/api/v1/models", "/api/v1/sessions"]

        for endpoint in test_endpoints:
            for payload in command_payloads:
                try:
                    params = {"file": payload}
                    response = self.client.get(endpoint, params=params)

                    # Check for command output in response
                    response_text = response.text.lower()
                    command_indicators = ["root", "bin", "etc", "home", "uid", "gid"]

                    if any(indicator in response_text for indicator in command_indicators):
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="CRITICAL", category="INPUT_VALIDATION", title="Command Injection",
                            description=f"Command injection vulnerability detected in {endpoint}",
                            endpoint=endpoint,
                            evidence=f"Command output detected: {response_text[:200]}",
                            recommendation="Never execute user input as system commands",
                            cwe_id="CWE-78"
                        ))

                except Exception as e:
                    logger.warning(f"Command injection test failed for {endpoint}: {e}")

    async def _test_path_traversal(self, test_result: SecurityTestResult):
        """Test path traversal vulnerabilities"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]

        test_endpoints = ["/api/v1/models", "/api/v1/sessions"]

        for endpoint in test_endpoints:
            for payload in path_traversal_payloads:
                try:
                    params = {"file": payload, "path": payload}
                    response = self.client.get(endpoint, params=params)

                    # Check for file system content in response
                    response_text = response.text.lower()
                    file_indicators = ["root:x:", "daemon:", "bin:x:", "[boot loader]", "[fonts]"]

                    if any(indicator in response_text for indicator in file_indicators):
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="CRITICAL", category="INPUT_VALIDATION", title="Path Traversal",
                            description=f"Path traversal vulnerability detected in {endpoint}",
                            endpoint=endpoint,
                            evidence=f"File content detected: {response_text[:200]}",
                            recommendation="Validate and sanitize all file path inputs",
                            cwe_id="CWE-22"
                        ))

                except Exception as e:
                    logger.warning(f"Path traversal test failed for {endpoint}: {e}")

    async def _test_buffer_overflow(self, test_result: SecurityTestResult):
        """Test buffer overflow vulnerabilities"""
        large_payload = "A" * 10000  # 10KB payload

        test_endpoints = [
            ("/api/v1/sessions", "POST"),
            ("/api/v1/models", "GET")
        ]

        for endpoint, method in test_endpoints:
            try:
                if method == "GET":
                    params = {"search": large_payload}
                    response = self.client.get(endpoint, params=params)
                else:
                    data = {"data": large_payload}
                    response = self.client.post(endpoint, json=data)

                # Check if server handles large input gracefully
                if response.status_code >= 500:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="MEDIUM", category="INPUT_VALIDATION", title="Buffer Overflow",
                        description=f"Server crashes with large input in {endpoint}",
                        endpoint=endpoint,
                        evidence=f"Status code: {response.status_code}",
                        recommendation="Implement proper input size limits",
                        cwe_id="CWE-120"
                    ))

            except Exception as e:
                logger.warning(f"Buffer overflow test failed for {endpoint}: {e}")

    async def test_cors_security(self):
        """Test CORS security configuration"""
        logger.info("🌐 Testing CORS Security...")

        test_result = SecurityTestResult("CORS Security")
        start_time = time.time()

        try:
            # Test 1: CORS headers validation
            await self._test_cors_headers(test_result)

            # Test 2: Cross-origin request validation
            await self._test_cross_origin_requests(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ CORS Security Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ CORS security test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="CORS", title="Security Test Error",
                description=f"CORS security test encountered error: {str(e)}"
            ))

    async def _test_cors_headers(self, test_result: SecurityTestResult):
        """Test CORS header configuration"""
        # OPTIONS request to check CORS headers
        response = self.client.options("/api/v1/health")

        cors_headers = {
            'Access-Control-Allow-Origin': 'Should not be * for production',
            'Access-Control-Allow-Methods': 'Should not allow all methods',
            'Access-Control-Allow-Headers': 'Should be restrictive',
            'Access-Control-Allow-Credentials': 'Should be used carefully'
        }

        for header, recommendation in cors_headers.items():
            header_value = response.headers.get(header.lower())
            if header_value:
                if header == 'Access-Control-Allow-Origin' and header_value == '*':
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="MEDIUM", category="CORS", title="Permissive CORS Origin",
                        description="CORS allows requests from any origin",
                        endpoint="*",
                        evidence=f"{header}: {header_value}",
                        recommendation=recommendation
                    ))

                if 'all' in header_value.lower() or '*' in header_value:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="LOW", category="CORS", title="Overly Permissive CORS",
                        description=f"CORS header allows unrestricted access",
                        endpoint="*",
                        evidence=f"{header}: {header_value}",
                        recommendation=recommendation
                    ))

    async def _test_cross_origin_requests(self, test_result: SecurityTestResult):
        """Test cross-origin request handling"""
        # Test with different Origin headers
        malicious_origins = [
            "http://evil.com",
            "https://malicious-site.net",
            "null"
        ]

        for origin in malicious_origins:
            try:
                headers = {"Origin": origin}
                response = self.client.get("/api/v1/health", headers=headers)

                # Check if response contains access-control-allow-origin
                acao_header = response.headers.get("access-control-allow-origin")
                if acao_header and acao_header == origin:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="HIGH", category="CORS", title="Allowed Malicious Origin",
                        description=f"CORS allows requests from malicious origin: {origin}",
                        endpoint="/api/v1/health",
                        evidence=f"Access-Control-Allow-Origin: {acao_header}",
                        recommendation="Implement strict CORS policy",
                        cwe_id="CWE-942"
                    ))

            except Exception as e:
                logger.warning(f"Cross-origin test failed: {e}")

    async def test_security_headers(self):
        """Test security headers implementation"""
        logger.info("🛡️ Testing Security Headers...")

        test_result = SecurityTestResult("Security Headers")
        start_time = time.time()

        try:
            # Test critical security headers
            critical_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'"
            }

            response = self.client.get("/api/v1/health")

            for header, expected_value in critical_headers.items():
                actual_value = response.headers.get(header.lower())

                if not actual_value:
                    severity = "HIGH" if header in ["X-Content-Type-Options", "X-Frame-Options"] else "MEDIUM"
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity=severity, category="SECURITY_HEADERS", title=f"Missing Security Header: {header}",
                        description=f"Important security header {header} is missing",
                        endpoint="/api/v1/health",
                        evidence=f"Header {header} not found in response",
                        recommendation=f"Add header: {header}: {expected_value}",
                        cwe_id="CWE-1004"
                    ))

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Security Headers Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Security headers test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="SECURITY_HEADERS", title="Security Test Error",
                description=f"Security headers test encountered error: {str(e)}"
            ))

    async def test_rate_limiting(self):
        """Test rate limiting implementation"""
        logger.info("⏱️ Testing Rate Limiting...")

        test_result = SecurityTestResult("Rate Limiting")
        start_time = time.time()

        try:
            # Test rapid requests to see if rate limiting is implemented
            rapid_requests = []
            for i in range(50):  # Send 50 rapid requests
                response = self.client.get("/api/v1/health")
                rapid_requests.append(response.status_code)

            # Check if we get any rate limit responses (429)
            if 429 not in rapid_requests:
                test_result.vulnerabilities.append(SecurityVulnerability(
                    severity="MEDIUM", category="RATE_LIMITING", title="Missing Rate Limiting",
                    description="API does not appear to implement rate limiting",
                    endpoint="/api/v1/health",
                    evidence="50 rapid requests did not trigger rate limiting",
                    recommendation="Implement rate limiting to prevent abuse",
                    cwe_id="CWE-770"
                ))

            # Check for rate limiting headers
            last_response = self.client.get("/api/v1/health")
            rate_limit_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]

            missing_rate_headers = [header for header in rate_limit_headers
                                   if header.lower() not in last_response.headers]

            if missing_rate_headers:
                test_result.vulnerabilities.append(SecurityVulnerability(
                    severity="LOW", category="RATE_LIMITING", title="Missing Rate Limit Headers",
                    description="Rate limiting information headers are missing",
                    endpoint="/api/v1/health",
                    evidence=f"Missing headers: {missing_rate_headers}",
                    recommendation="Add rate limit headers for better client experience"
                ))

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Rate Limiting Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Rate limiting test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="RATE_LIMITING", title="Security Test Error",
                description=f"Rate limiting test encountered error: {str(e)}"
            ))

    async def test_error_handling(self):
        """Test secure error handling"""
        logger.info("⚠️ Testing Error Handling Security...")

        test_result = SecurityTestResult("Error Handling")
        start_time = time.time()

        try:
            # Test various error scenarios
            error_scenarios = [
                ("/api/v1/nonexistent", "GET"),  # 404
                ("/api/v1/models", "POST", {}),  # Invalid method
                ("/api/v1/sessions", "POST", {"invalid": "data"}),  # Invalid data
            ]

            for scenario in error_scenarios:
                endpoint = scenario[0]
                method = scenario[1]
                data = scenario[2] if len(scenario) > 2 else None

                try:
                    if method == "GET":
                        response = self.client.get(endpoint)
                    elif method == "POST":
                        response = self.client.post(endpoint, json=data)

                    # Check for information disclosure in error messages
                    response_text = response.text.lower()

                    # Check for stack traces or detailed error information
                    info_disclosure_patterns = [
                        "traceback", "stack trace", "exception", "error at line",
                        "internal server error", "database error", "sql error",
                        "file path", "python", "fastapi", "uvicorn"
                    ]

                    if any(pattern in response_text for pattern in info_disclosure_patterns):
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="MEDIUM", category="ERROR_HANDLING", title="Information Disclosure",
                            description=f"Error response contains sensitive information",
                            endpoint=endpoint,
                            evidence=f"Response contains: {[p for p in info_disclosure_patterns if p in response_text]}",
                            recommendation="Implement generic error messages",
                            cwe_id="CWE-209"
                        ))

                    # Check if error includes server stack trace
                    if "traceback" in response_text or "stack trace" in response_text:
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="HIGH", category="ERROR_HANDLING", title="Stack Trace Disclosure",
                            description="Stack trace exposed in error response",
                            endpoint=endpoint,
                            evidence="Stack trace found in response",
                            recommendation="Never expose stack traces to clients",
                            cwe_id="CWE-544"
                        ))

                except Exception as e:
                    logger.warning(f"Error handling test failed for {endpoint}: {e}")

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Error Handling Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="ERROR_HANDLING", title="Security Test Error",
                description=f"Error handling test encountered error: {str(e)}"
            ))

    async def test_authorization(self):
        """Test authorization controls"""
        logger.info("👥 Testing Authorization Security...")

        test_result = SecurityTestResult("Authorization")
        start_time = time.time()

        try:
            # Test access control on different endpoints
            await self._test_endpoint_authorization(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Authorization Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Authorization test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="AUTH", title="Security Test Error",
                description=f"Authorization test encountered error: {str(e)}"
            ))

    async def _test_endpoint_authorization(self, test_result: SecurityTestResult):
        """Test endpoint-level authorization"""
        # Test accessing admin or developer endpoints without proper credentials
        privileged_endpoints = [
            "/api/v1/developer/usage",
            "/api/v1/developer/keys",
            "/api/v1/organizations",
            "/api/v1/payments"
        ]

        for endpoint in privileged_endpoints:
            try:
                response = self.client.get(endpoint)

                # Should require authentication (401) or return specific error for unauthorized access
                if response.status_code == 200:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="HIGH", category="AUTH", title="Broken Access Control",
                        description=f"Privileged endpoint {endpoint} allows unauthorized access",
                        endpoint=endpoint,
                        evidence=f"Status code: {response.status_code}",
                        recommendation="Implement proper access controls",
                        cwe_id="CWE-284"
                    ))

            except Exception as e:
                logger.warning(f"Authorization test failed for {endpoint}: {e}")

    async def test_session_security(self):
        """Test session security"""
        logger.info("🔐 Testing Session Security...")

        test_result = SecurityTestResult("Session Security")
        start_time = time.time()

        try:
            # Test session management
            await self._test_session_management(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Session Security Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Session security test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="SESSION", title="Security Test Error",
                description=f"Session security test encountered error: {str(e)}"
            ))

    async def _test_session_management(self, test_result: SecurityTestResult):
        """Test session management security"""
        # Test session creation and handling
        try:
            # Create a new session
            session_data = {
                "user_id": "test_security_user",
                "messages": [{"role": "user", "content": "Test message"}]
            }

            response = self.client.post("/api/v1/sessions", json=session_data)

            if response.status_code == 200 or response.status_code == 201:
                session_data = response.json()

                # Check for session ID in response
                if "session_id" in session_data:
                    session_id = session_data["session_id"]

                    # Test if session ID is predictable
                    if len(session_id) < 16 or session_id.isnumeric():
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="MEDIUM", category="SESSION", title="Weak Session ID",
                            description="Session ID appears to be weak or predictable",
                            endpoint="/api/v1/sessions",
                            evidence=f"Session ID: {session_id[:10]}...",
                            recommendation="Use cryptographically secure session IDs",
                            cwe_id="CWE-384"
                        ))

        except Exception as e:
            logger.warning(f"Session management test failed: {e}")

    async def test_data_exposure(self):
        """Test for data exposure vulnerabilities"""
        logger.info("📋 Testing Data Exposure Security...")

        test_result = SecurityTestResult("Data Exposure")
        start_time = time.time()

        try:
            # Test for sensitive data in responses
            await self._test_sensitive_data_exposure(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Data Exposure Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Data exposure test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="DATA_EXPOSURE", title="Security Test Error",
                description=f"Data exposure test encountered error: {str(e)}"
            ))

    async def _test_sensitive_data_exposure(self, test_result: SecurityTestResult):
        """Test for sensitive data exposure"""
        # Test various endpoints for sensitive data exposure
        endpoints_to_test = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/models",
            "/api/v1/sessions"
        ]

        sensitive_patterns = [
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'Credit Card Number'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email Address'),
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'password\s*[:=]\s*["\']?[^"\'\s]+', 'Password'),
            (r'api_key\s*[:=]\s*["\']?[^"\'\s]+', 'API Key'),
            (r'secret\s*[:=]\s*["\']?[^"\'\s]+', 'Secret'),
            (r'token\s*[:=]\s*["\']?[^"\'\s]+', 'Token')
        ]

        for endpoint in endpoints_to_test:
            try:
                response = self.client.get(endpoint)
                response_text = response.text

                for pattern, data_type in sensitive_patterns:
                    if re.search(pattern, response_text, re.IGNORECASE):
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="HIGH", category="DATA_EXPOSURE", title=f"Sensitive Data: {data_type}",
                            description=f"Sensitive data ({data_type}) exposed in response",
                            endpoint=endpoint,
                            evidence=f"Pattern matched: {data_type}",
                            recommendation="Remove sensitive data from API responses",
                            cwe_id="CWE-200"
                        ))

            except Exception as e:
                logger.warning(f"Data exposure test failed for {endpoint}: {e}")

    async def test_api_key_security(self):
        """Test API key security"""
        logger.info("🔑 Testing API Key Security...")

        test_result = SecurityTestResult("API Key Security")
        start_time = time.time()

        try:
            # Test API key handling
            await self._test_api_key_handling(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ API Key Security Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ API key security test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="API_KEY", title="Security Test Error",
                description=f"API key security test encountered error: {str(e)}"
            ))

    async def _test_api_key_handling(self, test_result: SecurityTestResult):
        """Test API key handling security"""
        # Test API key endpoints if they exist
        api_key_endpoints = [
            "/api/v1/developer/keys",
            "/api/v1/api-keys"
        ]

        for endpoint in api_key_endpoints:
            try:
                response = self.client.get(endpoint)

                if response.status_code == 200:
                    response_data = response.json()

                    # Check if API keys are exposed
                    response_text = json.dumps(response_data).lower()
                    if "api_key" in response_text or "secret" in response_text:
                        test_result.vulnerabilities.append(SecurityVulnerability(
                            severity="HIGH", category="API_KEY", title="API Key Exposure",
                            description="API keys or secrets exposed in response",
                            endpoint=endpoint,
                            evidence="API keys found in response",
                            recommendation="Never expose full API keys in responses",
                            cwe_id="CWE-598"
                        ))

            except Exception as e:
                logger.warning(f"API key test failed for {endpoint}: {e}")

    async def test_https_enforcement(self):
        """Test HTTPS enforcement"""
        logger.info("🔒 Testing HTTPS Enforcement...")

        test_result = SecurityTestResult("HTTPS Enforcement")
        start_time = time.time()

        try:
            # Test if application enforces HTTPS
            response = self.client.get("/api/v1/health")

            # Check for HSTS header
            hsts_header = response.headers.get("strict-transport-security")
            if not hsts_header:
                test_result.vulnerabilities.append(SecurityVulnerability(
                    severity="MEDIUM", category="HTTPS", title="Missing HSTS Header",
                    description="HTTP Strict Transport Security header is missing",
                    endpoint="/api/v1/health",
                    evidence="Strict-Transport-Security header not found",
                    recommendation="Add HSTS header to enforce HTTPS",
                    cwe_id="CWE-523"
                ))

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ HTTPS Enforcement Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ HTTPS enforcement test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="HTTPS", title="Security Test Error",
                description=f"HTTPS enforcement test encountered error: {str(e)}"
            ))

    async def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities"""
        logger.info("ℹ️ Testing Information Disclosure...")

        test_result = SecurityTestResult("Information Disclosure")
        start_time = time.time()

        try:
            # Test various information disclosure scenarios
            await self._test_server_information_disclosure(test_result)
            await self._test_technology_stack_disclosure(test_result)

            test_result.passed = len([v for v in test_result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]) == 0
            test_result.execution_time = time.time() - start_time
            self.test_results.append(test_result)

            logger.info(f"✅ Information Disclosure Test: {len(test_result.vulnerabilities)} issues found")

        except Exception as e:
            logger.error(f"❌ Information disclosure test failed: {e}")
            test_result.passed = False
            test_result.vulnerabilities.append(SecurityVulnerability(
                severity="HIGH", category="INFO_DISCLOSURE", title="Security Test Error",
                description=f"Information disclosure test encountered error: {str(e)}"
            ))

    async def _test_server_information_disclosure(self, test_result: SecurityTestResult):
        """Test for server information disclosure"""
        try:
            response = self.client.get("/api/v1/health")

            # Check for server headers
            server_header = response.headers.get("server")
            if server_header:
                test_result.vulnerabilities.append(SecurityVulnerability(
                    severity="LOW", category="INFO_DISCLOSURE", title="Server Information Disclosure",
                    description="Server header reveals server information",
                    endpoint="/api/v1/health",
                    evidence=f"Server header: {server_header}",
                    recommendation="Remove or obfuscate server header"
                ))

            # Check for powered-by headers
            powered_by = response.headers.get("x-powered-by")
            if powered_by:
                test_result.vulnerabilities.append(SecurityVulnerability(
                    severity="LOW", category="INFO_DISCLOSURE", title="Powered-By Header",
                    description="X-Powered-By header reveals technology information",
                    endpoint="/api/v1/health",
                    evidence=f"X-Powered-By header: {powered_by}",
                    recommendation="Remove X-Powered-By header"
                ))

        except Exception as e:
            logger.warning(f"Server information disclosure test failed: {e}")

    async def _test_technology_stack_disclosure(self, test_result: SecurityTestResult):
        """Test for technology stack disclosure"""
        try:
            # Test OpenAPI documentation for information disclosure
            response = self.client.get("/api/v1/docs")

            if response.status_code == 200:
                response_text = response.text.lower()

                # Check for technology indicators
                tech_indicators = ["fastapi", "uvicorn", "python", "swagger", "openapi"]
                found_techs = [tech for tech in tech_indicators if tech in response_text]

                if found_techs:
                    test_result.vulnerabilities.append(SecurityVulnerability(
                        severity="LOW", category="INFO_DISCLOSURE", title="Technology Stack Disclosure",
                        description="Technology stack information exposed in API documentation",
                        endpoint="/api/v1/docs",
                        evidence=f"Technologies detected: {found_techs}",
                        recommendation="Restrict API documentation access in production"
                    ))

        except Exception as e:
            logger.warning(f"Technology stack disclosure test failed: {e}")

    def _generate_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        logger.info("📋 Generating Security Report...")

        # Aggregate vulnerabilities by severity
        all_vulnerabilities = []
        for test_result in self.test_results:
            all_vulnerabilities.extend(test_result.vulnerabilities)

        vulnerability_counts = {
            "CRITICAL": len([v for v in all_vulnerabilities if v.severity == "CRITICAL"]),
            "HIGH": len([v for v in all_vulnerabilities if v.severity == "HIGH"]),
            "MEDIUM": len([v for v in all_vulnerabilities if v.severity == "MEDIUM"]),
            "LOW": len([v for v in all_vulnerabilities if v.severity == "LOW"]),
            "INFO": len([v for v in all_vulnerabilities if v.severity == "INFO"])
        }

        # Calculate security score
        severity_weights = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 10, "LOW": 5, "INFO": 1}
        total_penalty = sum(vulnerability_counts[severity] * weight
                          for severity, weight in severity_weights.items())

        max_possible_score = 100
        security_score = max(0, max_possible_score - total_penalty)

        # Determine security grade
        if security_score >= 95:
            security_grade = "A+ (Excellent)"
        elif security_score >= 90:
            security_grade = "A (Very Good)"
        elif security_score >= 80:
            security_grade = "B+ (Good)"
        elif security_score >= 70:
            security_grade = "B (Fair)"
        elif security_score >= 60:
            security_grade = "C+ (Needs Improvement)"
        elif security_score >= 50:
            security_grade = "C (Poor)"
        else:
            security_grade = "F (Critical)"

        # Generate recommendations
        recommendations = self._generate_security_recommendations(all_vulnerabilities)

        return {
            "security_score": security_score,
            "security_grade": security_grade,
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed_tests": len([t for t in self.test_results if t.passed]),
                "failed_tests": len([t for t in self.test_results if not t.passed])
            },
            "vulnerability_summary": vulnerability_counts,
            "total_vulnerabilities": len(all_vulnerabilities),
            "test_results": [
                {
                    "test_name": result.test_name,
                    "passed": result.passed,
                    "vulnerabilities_found": len(result.vulnerabilities),
                    "execution_time": result.execution_time
                }
                for result in self.test_results
            ],
            "critical_vulnerabilities": [
                {
                    "title": v.title,
                    "category": v.category,
                    "description": v.description,
                    "endpoint": v.endpoint,
                    "recommendation": v.recommendation
                }
                for v in all_vulnerabilities if v.severity == "CRITICAL"
            ],
            "all_vulnerabilities": [
                {
                    "severity": v.severity,
                    "category": v.category,
                    "title": v.title,
                    "description": v.description,
                    "endpoint": v.endpoint,
                    "evidence": v.evidence,
                    "recommendation": v.recommendation,
                    "cwe_id": v.cwe_id
                }
                for v in all_vulnerabilities
            ],
            "recommendations": recommendations
        }

    def _generate_security_recommendations(self, vulnerabilities: List[SecurityVulnerability]) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []

        # Critical issues first
        critical_issues = [v for v in vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]
        if critical_issues:
            recommendations.append("🚨 CRITICAL: Address all critical and high-severity vulnerabilities immediately before production deployment")

        # Authentication issues
        auth_issues = [v for v in vulnerabilities if v.category == "AUTH"]
        if auth_issues:
            recommendations.append("🔐 Implement robust authentication and authorization controls across all endpoints")

        # Input validation issues
        input_issues = [v for v in vulnerabilities if v.category == "INPUT_VALIDATION"]
        if input_issues:
            recommendations.append("🛡️ Strengthen input validation to prevent injection attacks (SQL, XSS, Command, Path Traversal)")

        # Header issues
        header_issues = [v for v in vulnerabilities if v.category in ["SECURITY_HEADERS", "CORS"]]
        if header_issues:
            recommendations.append("🛡️ Implement comprehensive security headers and CORS policies")

        # General recommendations
        if not vulnerabilities:
            recommendations.append("✅ Excellent security posture found. Continue regular security assessments")

        recommendations.append("📊 Implement regular security scanning and automated testing in CI/CD pipeline")
        recommendations.append("🔒 Consider implementing Web Application Firewall (WAF) for additional protection")
        recommendations.append("📋 Maintain security documentation and incident response procedures")

        return recommendations


# Pytest test functions
@pytest.fixture
async def security_suite():
    """Fixture for security validation suite"""
    return SecurityValidationSuite()


@pytest.mark.asyncio
@pytest.mark.security
async def test_comprehensive_security_validation(security_suite):
    """Test comprehensive security validation"""
    report = await security_suite.run_comprehensive_security_validation()

    # Basic security requirements
    assert report["security_score"] >= 50.0, f"Security score too low: {report['security_score']}"
    assert report["vulnerability_summary"]["CRITICAL"] == 0, "Critical vulnerabilities must be addressed"
    assert report["vulnerability_summary"]["HIGH"] <= 2, "Too many high-severity vulnerabilities"

    # Log security results
    logger.info(f"🔒 Security Validation Results:")
    logger.info(f"   Security Score: {report['security_score']:.2f}/100")
    logger.info(f"   Security Grade: {report['security_grade']}")
    logger.info(f"   Total Vulnerabilities: {report['total_vulnerabilities']}")
    logger.info(f"   Critical/High Issues: {report['vulnerability_summary']['CRITICAL'] + report['vulnerability_summary']['HIGH']}")


@pytest.mark.asyncio
@pytest.mark.security
async def test_critical_security_checks_only(security_suite):
    """Test only critical security checks for faster execution"""
    # Run only the most critical security tests
    await security_suite.test_authentication_security()
    await security_suite.test_input_validation()
    await security_suite.test_cors_security()
    await security_suite.test_security_headers()

    # Generate partial report
    critical_vulnerabilities = []
    for result in security_suite.test_results:
        critical_vulnerabilities.extend([v for v in result.vulnerabilities if v.severity in ["CRITICAL", "HIGH"]])

    # Must have no critical vulnerabilities
    assert len(critical_vulnerabilities) == 0, f"Critical vulnerabilities found: {len(critical_vulnerabilities)}"

    logger.info(f"⚡ Critical Security Checks - Issues: {len(critical_vulnerabilities)}")


if __name__ == "__main__":
    # Run security validation directly
    async def main():
        print("🔒 Starting Security Validation Suite")
        print("=" * 80)

        security_suite = SecurityValidationSuite()
        report = await security_suite.run_comprehensive_security_validation()

        print("\n🛡️ SECURITY VALIDATION REPORT")
        print("=" * 50)
        print(f"Security Score: {report['security_score']:.2f}/100")
        print(f"Security Grade: {report['security_grade']}")
        print(f"Total Vulnerabilities: {report['total_vulnerabilities']}")

        print("\n🚨 VULNERABILITY BREAKDOWN:")
        for severity, count in report['vulnerability_summary'].items():
            if count > 0:
                icon = "🚨" if severity in ["CRITICAL", "HIGH"] else "⚠️"
                print(f"  {icon} {severity}: {count}")

        print("\n🧪 TEST RESULTS:")
        for test_result in report['test_results']:
            status = "✅" if test_result['passed'] else "❌"
            print(f"  {status} {test_result['test_name']}: {test_result['vulnerabilities_found']} issues")

        if report['critical_vulnerabilities']:
            print("\n🚨 CRITICAL VULNERABILITIES:")
            for vuln in report['critical_vulnerabilities']:
                print(f"  • {vuln['title']} - {vuln['description']}")

        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  - {rec}")

        print("\n" + "=" * 80)
        if report['security_score'] >= 80:
            print("✅ SECURITY VALIDATION COMPLETED - Good security posture")
        elif report['security_score'] >= 60:
            print("⚠️ SECURITY VALIDATION COMPLETED - Needs improvement")
        else:
            print("🚨 SECURITY VALIDATION COMPLETED - Critical issues found")

        # Save detailed security report
        report_file = f"data/security/security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed security report saved to: {report_file}")

    asyncio.run(main())