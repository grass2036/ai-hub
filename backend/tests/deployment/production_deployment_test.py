"""
Week 8 Day 6 - Production Environment Deployment Verification
Comprehensive production readiness testing and validation
"""

import pytest
import asyncio
import time
import json
import os
import subprocess
import socket
import ssl
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import aiohttp
from pathlib import Path

from fastapi.testclient import TestClient
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeploymentCheck:
    """Individual deployment check result"""
    name: str
    category: str
    status: str  # PASS, FAIL, WARNING
    description: str
    details: Optional[str] = None
    recommendation: str = ""
    execution_time: float = 0.0
    critical: bool = False


@dataclass
class EnvironmentConfiguration:
    """Environment configuration details"""
    environment_type: str  # development, staging, production
    base_url: str
    database_url: str
    redis_url: str
    ssl_enabled: bool
    monitoring_enabled: bool
    backup_enabled: bool
    health_check_interval: int


class ProductionDeploymentValidator:
    """Comprehensive production deployment validation"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = TestClient(app)
        self.deployment_checks = []
        self.env_config = None

        # Production requirements
        self.production_requirements = {
            "ssl_certificate": True,
            "security_headers": True,
            "rate_limiting": True,
            "monitoring": True,
            "backup_system": True,
            "error_handling": True,
            "resource_limits": True,
            "log_rotation": True,
            "health_checks": True,
            "environment_variables": True,
            "database_optimization": True,
            "cache_configuration": True
        }

    async def run_production_validation(self) -> Dict:
        """Run comprehensive production deployment validation"""
        logger.info("🚀 Starting Production Environment Deployment Validation")

        start_time = time.time()

        try:
            # Detect environment configuration
            await self._detect_environment_configuration()

            # Run all deployment checks
            await self._check_ssl_configuration()
            await self._check_security_headers()
            await self._check_rate_limiting()
            await self._check_monitoring_systems()
            await self._check_backup_systems()
            await self._check_error_handling()
            await self._check_resource_limits()
            await self._check_logging_configuration()
            await self._check_health_checks()
            await self._check_environment_variables()
            await self._check_database_optimization()
            await self._check_cache_configuration()
            await self._check_api_documentation()
            await self._check_load_balancer_configuration()
            await self._check_container_configuration()
            await self._check_network_connectivity()
            await self._check_disaster_recovery()

            # Generate comprehensive deployment report
            report = self._generate_deployment_report()

            end_time = time.time()
            report["execution_time"] = end_time - start_time
            report["timestamp"] = datetime.now().isoformat()

            logger.info(f"✅ Production deployment validation completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Deployment Readiness Score: {report['readiness_score']:.2f}/100")

            return report

        except Exception as e:
            logger.error(f"❌ Production deployment validation failed: {e}")
            raise

    async def _detect_environment_configuration(self):
        """Detect current environment configuration"""
        logger.info("🔍 Detecting Environment Configuration...")

        try:
            # Get environment variables
            env_type = os.getenv("ENVIRONMENT", "development")
            base_url = os.getenv("BASE_URL", "http://localhost:8001")
            database_url = os.getenv("DATABASE_URL", "sqlite:///./ai_hub.db")
            redis_url = os.getenv("REDIS_URL", "")

            # Detect configuration features
            ssl_enabled = base_url.startswith("https://")
            monitoring_enabled = bool(os.getenv("MONITORING_ENABLED", "false").lower() == "true")
            backup_enabled = bool(os.getenv("BACKUP_ENABLED", "false").lower() == "true")
            health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

            self.env_config = EnvironmentConfiguration(
                environment_type=env_type,
                base_url=base_url,
                database_url=database_url,
                redis_url=redis_url,
                ssl_enabled=ssl_enabled,
                monitoring_enabled=monitoring_enabled,
                backup_enabled=backup_enabled,
                health_check_interval=health_check_interval
            )

            logger.info(f"✅ Environment detected: {env_type}")
            logger.info(f"   SSL: {'Enabled' if ssl_enabled else 'Disabled'}")
            logger.info(f"   Monitoring: {'Enabled' if monitoring_enabled else 'Disabled'}")
            logger.info(f"   Backup: {'Enabled' if backup_enabled else 'Disabled'}")

        except Exception as e:
            logger.error(f"❌ Environment detection failed: {e}")
            self.env_config = EnvironmentConfiguration(
                environment_type="unknown",
                base_url=self.base_url,
                database_url="",
                redis_url="",
                ssl_enabled=False,
                monitoring_enabled=False,
                backup_enabled=False,
                health_check_interval=0
            )

    async def _check_ssl_configuration(self):
        """Check SSL/TLS configuration"""
        logger.info("🔒 Checking SSL/TLS Configuration...")

        check = DeploymentCheck(
            name="SSL/TLS Configuration",
            category="Security",
            status="PASS",
            description="Verify SSL certificate and TLS configuration"
        )
        start_time = time.time()

        try:
            if self.env_config.environment_type == "production":
                if not self.env_config.ssl_enabled:
                    check.status = "FAIL"
                    check.critical = True
                    check.details = "Production environment requires HTTPS"
                    check.recommendation = "Configure SSL/TLS certificate for production deployment"
                else:
                    # Test SSL certificate
                    hostname = self.env_config.base_url.replace("https://", "").replace("/", "")
                    try:
                        context = ssl.create_default_context()
                        with socket.create_connection((hostname, 443), timeout=10) as sock:
                            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                                cert = ssock.getpeercert()
                                check.details = f"SSL Certificate: {cert['subject']}"
                    except Exception as e:
                        check.status = "FAIL"
                        check.critical = True
                        check.details = f"SSL certificate validation failed: {str(e)}"
                        check.recommendation = "Install valid SSL certificate and verify configuration"

            else:
                check.status = "WARNING"
                check.details = "SSL not required for non-production environment"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"SSL check failed: {str(e)}"
            check.recommendation = "Fix SSL configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_security_headers(self):
        """Check security headers configuration"""
        logger.info("🛡️ Checking Security Headers...")

        check = DeploymentCheck(
            name="Security Headers",
            category="Security",
            status="PASS",
            description="Verify required security headers are present"
        )
        start_time = time.time()

        try:
            # Make a request to check headers
            response = self.client.get("/api/v1/health")

            required_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security" if self.env_config.ssl_enabled else None,
                "Content-Security-Policy"
            ]

            missing_headers = []
            for header in required_headers:
                if header and header.lower() not in response.headers:
                    missing_headers.append(header)

            if missing_headers:
                check.status = "FAIL" if self.env_config.environment_type == "production" else "WARNING"
                check.details = f"Missing security headers: {missing_headers}"
                check.recommendation = "Add missing security headers to server configuration"
            else:
                check.details = "All required security headers present"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Security headers check failed: {str(e)}"
            check.recommendation = "Fix server header configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_rate_limiting(self):
        """Check rate limiting configuration"""
        logger.info("⏱️ Checking Rate Limiting...")

        check = DeploymentCheck(
            name="Rate Limiting",
            category="Performance",
            status="PASS",
            description="Verify rate limiting is configured"
        )
        start_time = time.time()

        try:
            # Test rapid requests
            rapid_requests = []
            for i in range(20):
                response = self.client.get("/api/v1/health")
                rapid_requests.append(response.status_code)

            # Check for rate limit responses
            if 429 not in rapid_requests:
                check.status = "WARNING"
                check.details = "Rate limiting may not be configured"
                check.recommendation = "Implement rate limiting to protect against abuse"
            else:
                check.details = "Rate limiting is active"

            # Check rate limit headers
            last_response = self.client.get("/api/v1/health")
            rate_limit_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
            present_headers = [h for h in rate_limit_headers if h.lower() in last_response.headers]

            if not present_headers:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += " (Rate limit headers not found)"
                check.recommendation = "Add rate limit headers for better client experience"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Rate limiting check failed: {str(e)}"
            check.recommendation = "Fix rate limiting configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_monitoring_systems(self):
        """Check monitoring and alerting systems"""
        logger.info("📊 Checking Monitoring Systems...")

        check = DeploymentCheck(
            name="Monitoring Systems",
            category="Operations",
            status="PASS",
            description="Verify monitoring and alerting systems are operational"
        )
        start_time = time.time()

        try:
            monitoring_endpoints = [
                "/api/v1/monitoring-new/dashboard",
                "/api/v1/performance/stats",
                "/api/v1/performance-optimization/stats"
            ]

            operational_endpoints = 0
            for endpoint in monitoring_endpoints:
                try:
                    response = self.client.get(endpoint)
                    if response.status_code == 200:
                        operational_endpoints += 1
                except:
                    pass

            if operational_endpoints >= 2:
                check.details = f"{operational_endpoints}/{len(monitoring_endpoints)} monitoring endpoints operational"
            else:
                check.status = "FAIL" if self.env_config.environment_type == "production" else "WARNING"
                check.details = f"Only {operational_endpoints}/{len(monitoring_endpoints)} monitoring endpoints working"
                check.recommendation = "Fix monitoring system configuration"

            # Check if monitoring is enabled in environment
            if not self.env_config.monitoring_enabled:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += " (Monitoring disabled in environment variables)"
                check.recommendation += ". Enable monitoring in production environment"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Monitoring check failed: {str(e)}"
            check.recommendation = "Fix monitoring system configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_backup_systems(self):
        """Check backup and recovery systems"""
        logger.info("💾 Checking Backup Systems...")

        check = DeploymentCheck(
            name="Backup Systems",
            category="Operations",
            status="PASS",
            description="Verify backup and recovery systems are configured"
        )
        start_time = time.time()

        try:
            # Check backup-related endpoints
            backup_endpoints = [
                "/api/v1/backup/status",
                "/api/v1/backup/create",
                "/api/v1/backup/restore"
            ]

            backup_endpoints_working = 0
            for endpoint in backup_endpoints:
                try:
                    response = self.client.get(endpoint.replace("create", "status").replace("restore", "status"))
                    if response.status_code in [200, 201, 405]:  # 405 is acceptable for GET on POST endpoints
                        backup_endpoints_working += 1
                except:
                    pass

            # Check environment configuration
            if self.env_config.backup_enabled:
                if backup_endpoints_working >= 2:
                    check.details = "Backup systems operational and enabled"
                else:
                    check.status = "WARNING"
                    check.details = "Backup enabled but endpoints not fully operational"
                    check.recommendation = "Verify backup system configuration"
            else:
                check.status = "WARNING" if self.env_config.environment_type == "production" else "PASS"
                check.details = "Backup systems not enabled in environment"
                check.recommendation = "Enable backup system for production deployment"

            # Check for backup configuration files
            backup_config_files = [
                "docker-compose.backup.yml",
                "data/backups/",
                "scripts/backup.sh"
            ]

            found_backup_configs = 0
            for config_file in backup_config_files:
                if os.path.exists(config_file) or config_file.endswith("/") and os.path.isdir(config_file):
                    found_backup_configs += 1

            if found_backup_configs == 0:
                check.status = "FAIL" if self.env_config.environment_type == "production" else "WARNING"
                check.details += " (No backup configuration files found)"
                check.recommendation = "Set up backup configuration files"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Backup system check failed: {str(e)}"
            check.recommendation = "Configure backup and recovery systems"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_error_handling(self):
        """Check error handling configuration"""
        logger.info("⚠️ Checking Error Handling...")

        check = DeploymentCheck(
            name="Error Handling",
            category="Reliability",
            status="PASS",
            description="Verify proper error handling and logging"
        )
        start_time = time.time()

        try:
            # Test various error scenarios
            error_scenarios = [
                ("/api/v1/nonexistent", 404),
                ("/api/v1/models", 405)  # Wrong method
            ]

            proper_responses = 0
            for endpoint, expected_status in error_scenarios:
                try:
                    if expected_status == 405:
                        response = self.client.post(endpoint)  # POST to GET endpoint
                    else:
                        response = self.client.get(endpoint)

                    # Check for proper JSON error response
                    if response.status_code == expected_status:
                        try:
                            error_data = response.json()
                            if "detail" in error_data or "error" in error_data:
                                proper_responses += 1
                        except:
                            pass

                except:
                    pass

            # Check for stack trace exposure
            response = self.client.get("/api/v1/nonexistent")
            response_text = response.text.lower()
            stack_trace_indicators = ["traceback", "stack trace", "exception at", "file "]

            if any(indicator in response_text for indicator in stack_trace_indicators):
                check.status = "FAIL"
                check.critical = True
                check.details = "Stack traces exposed in error responses"
                check.recommendation = "Configure proper error handling without stack trace exposure"
            elif proper_responses >= len(error_scenarios):
                check.details = "Proper error handling implemented"
            else:
                check.status = "WARNING"
                check.details = f"Only {proper_responses}/{len(error_scenarios)} error scenarios handled properly"
                check.recommendation = "Improve error handling for all scenarios"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Error handling check failed: {str(e)}"
            check.recommendation = "Fix error handling configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_resource_limits(self):
        """Check resource limits and scaling configuration"""
        logger.info("📏 Checking Resource Limits...")

        check = DeploymentCheck(
            name="Resource Limits",
            category="Performance",
            status="PASS",
            description="Verify resource limits and scaling configuration"
        )
        start_time = time.time()

        try:
            # Check for resource limit configurations
            resource_checks = {
                "max_workers": os.getenv("MAX_WORKERS"),
                "max_concurrent_requests": os.getenv("MAX_CONCURRENT_REQUESTS"),
                "request_timeout": os.getenv("REQUEST_TIMEOUT"),
                "connection_pool_size": os.getenv("CONNECTION_POOL_SIZE")
            }

            configured_resources = sum(1 for value in resource_checks.values() if value is not None)

            if configured_resources >= 3:
                check.details = f"{configured_resources}/4 resource limits configured"
            else:
                check.status = "WARNING"
                check.details = f"Only {configured_resources}/4 resource limits configured"
                check.recommendation = "Configure resource limits for production deployment"

            # Check for container resource limits
            docker_compose_files = ["docker-compose.yml", "docker-compose.override.yml"]
            container_resources_found = False

            for compose_file in docker_compose_files:
                if os.path.exists(compose_file):
                    try:
                        with open(compose_file, 'r') as f:
                            compose_data = yaml.safe_load(f)

                        # Check for resource limits in services
                        if 'services' in compose_data:
                            for service_name, service_config in compose_data['services'].items():
                                if 'deploy' in service_config and 'resources' in service_config['deploy']:
                                    container_resources_found = True
                                    break
                                elif 'mem_limit' in service_config or 'cpus' in service_config:
                                    container_resources_found = True
                                    break
                    except:
                        pass

            if not container_resources_found and self.env_config.environment_type == "production":
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += " (No container resource limits found)"
                check.recommendation += ". Set container resource limits for production"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Resource limits check failed: {str(e)}"
            check.recommendation = "Configure resource limits"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_logging_configuration(self):
        """Check logging configuration"""
        logger.info("📋 Checking Logging Configuration...")

        check = DeploymentCheck(
            name="Logging Configuration",
            category="Operations",
            status="PASS",
            description="Verify logging and log rotation configuration"
        )
        start_time = time.time()

        try:
            # Check logging environment variables
            log_level = os.getenv("LOG_LEVEL", "INFO")
            log_file = os.getenv("LOG_FILE")
            log_rotation = os.getenv("LOG_ROTATION", "daily")

            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                check.details = f"Log level: {log_level}"
            else:
                check.status = "WARNING"
                check.details = f"Invalid log level: {log_level}"
                check.recommendation = "Set proper log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"

            # Check for log configuration files
            log_configs = [
                "logging.conf",
                "config/logging.yml",
                ".env"
            ]

            log_configs_found = sum(1 for config in log_configs if os.path.exists(config))

            if log_configs_found == 0:
                check.status = "WARNING"
                check.details += " (No log configuration files found)"
                check.recommendation = "Set up proper logging configuration"

            # Check log directory
            log_dir = "logs"
            if os.path.exists(log_dir):
                log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                check.details += f", {len(log_files)} log files found"
            else:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += " (No logs directory found)"
                check.recommendation += ". Create logs directory and configure log file output"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Logging configuration check failed: {str(e)}"
            check.recommendation = "Configure logging system"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_health_checks(self):
        """Check health check endpoints and monitoring"""
        logger.info("💓 Checking Health Checks...")

        check = DeploymentCheck(
            name="Health Checks",
            category="Reliability",
            status="PASS",
            description="Verify health check endpoints and monitoring"
        )
        start_time = time.time()

        try:
            # Test health check endpoints
            health_endpoints = [
                "/api/v1/health",
                "/api/v1/status",
                "/health"
            ]

            working_health_endpoints = 0
            for endpoint in health_endpoints:
                try:
                    response = self.client.get(endpoint)
                    if response.status_code == 200:
                        # Check if response contains health information
                        response_data = response.json()
                        if "status" in response_data or "healthy" in response_data:
                            working_health_endpoints += 1
                except:
                    pass

            if working_health_endpoints >= 1:
                check.details = f"{working_health_endpoints}/{len(health_endpoints)} health endpoints working"
            else:
                check.status = "FAIL"
                check.details = "No working health endpoints found"
                check.recommendation = "Implement proper health check endpoints"

            # Check health check interval configuration
            health_check_interval = self.env_config.health_check_interval
            if health_check_interval > 0 and health_check_interval <= 300:  # Max 5 minutes
                check.details += f", health check interval: {health_check_interval}s"
            elif health_check_interval == 0:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += " (Health check interval not configured)"
                check.recommendation = "Configure health check monitoring interval"
            else:
                check.status = "WARNING"
                check.details += f", health check interval too high: {health_check_interval}s"
                check.recommendation = "Reduce health check interval to reasonable value (30-60s)"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Health check validation failed: {str(e)}"
            check.recommendation = "Fix health check configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_environment_variables(self):
        """Check environment variable configuration"""
        logger.info("🔧 Checking Environment Variables...")

        check = DeploymentCheck(
            name="Environment Variables",
            category="Configuration",
            status="PASS",
            description="Verify critical environment variables are configured"
        )
        start_time = time.time()

        try:
            # Critical environment variables for production
            critical_env_vars = {
                "ENVIRONMENT": ["development", "staging", "production"],
                "SECRET_KEY": True,  # Required but value not checked
                "DATABASE_URL": True,
                "OPENROUTER_API_KEY": True,
                "LOG_LEVEL": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }

            missing_vars = []
            invalid_vars = []

            for var_name, validation in critical_env_vars.items():
                var_value = os.getenv(var_name)

                if not var_value:
                    missing_vars.append(var_name)
                elif isinstance(validation, list) and var_value not in validation:
                    invalid_vars.append(f"{var_name}={var_value}")

            if missing_vars:
                check.status = "FAIL" if self.env_config.environment_type == "production" else "WARNING"
                check.critical = True if self.env_config.environment_type == "production" else False
                check.details = f"Missing environment variables: {missing_vars}"
                check.recommendation = "Set missing environment variables before production deployment"
            elif invalid_vars:
                check.status = "WARNING"
                check.details = f"Invalid environment variables: {invalid_vars}"
                check.recommendation = "Fix invalid environment variable values"
            else:
                check.details = "All critical environment variables configured"

            # Check for sensitive data in environment files
            env_files = [".env", ".env.production", ".env.staging"]
            for env_file in env_files:
                if os.path.exists(env_file):
                    try:
                        with open(env_file, 'r') as f:
                            content = f.read()
                            if "password" in content.lower() and "test" not in content.lower():
                                if check.status == "PASS":
                                    check.status = "WARNING"
                                check.details += f" (Sensitive data found in {env_file})"
                                check.recommendation += ". Use secure secret management for production"
                    except:
                        pass

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Environment variables check failed: {str(e)}"
            check.recommendation = "Fix environment variable configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_database_optimization(self):
        """Check database optimization configuration"""
        logger.info("🗄️ Checking Database Optimization...")

        check = DeploymentCheck(
            name="Database Optimization",
            category="Performance",
            status="PASS",
            description="Verify database optimization settings"
        )
        start_time = time.time()

        try:
            # Check database URL and type
            db_url = self.env_config.database_url

            if "sqlite" in db_url.lower():
                check.status = "WARNING" if self.env_config.environment_type == "production" else "PASS"
                check.details = "Using SQLite in production environment"
                check.recommendation = "Consider PostgreSQL for production deployment"
            elif "postgresql" in db_url.lower() or "postgres" in db_url.lower():
                check.details = "Using PostgreSQL database"
            else:
                check.status = "WARNING"
                check.details = f"Unknown database type: {db_url.split('://')[0] if '://' in db_url else 'unknown'}"
                check.recommendation = "Verify database configuration"

            # Check database optimization endpoints
            try:
                response = self.client.get("/api/v1/database-optimization/stats")
                if response.status_code == 200:
                    check.details += ", database optimization available"
                else:
                    if check.status == "PASS":
                        check.status = "WARNING"
                    check.details += ", database optimization not available"
                    check.recommendation = "Enable database optimization features"
            except:
                check.details += ", database optimization endpoints not found"

            # Check for connection pool configuration
            pool_size = os.getenv("DB_POOL_SIZE")
            max_overflow = os.getenv("DB_MAX_OVERFLOW")

            if pool_size and max_overflow:
                check.details += f", connection pool configured"
            else:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += ", connection pool not configured"
                check.recommendation = "Configure database connection pool"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Database optimization check failed: {str(e)}"
            check.recommendation = "Fix database configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_cache_configuration(self):
        """Check cache system configuration"""
        logger.info("💾 Checking Cache Configuration...")

        check = DeploymentCheck(
            name="Cache Configuration",
            category="Performance",
            status="PASS",
            description="Verify cache system configuration"
        )
        start_time = time.time()

        try:
            # Check Redis configuration
            redis_url = self.env_config.redis_url

            if not redis_url:
                check.status = "WARNING" if self.env_config.environment_type == "production" else "PASS"
                check.details = "Redis cache not configured"
                check.recommendation = "Configure Redis cache for production deployment"
            else:
                check.details = "Redis cache configured"

            # Test cache endpoints
            try:
                response = self.client.get("/api/v1/cache/stats")
                if response.status_code == 200:
                    cache_stats = response.json()
                    check.details += f", cache status: {cache_stats.get('status', 'unknown')}"
                else:
                    if check.status == "PASS":
                        check.status = "WARNING"
                    check.details += ", cache endpoints not responding"
                    check.recommendation = "Fix cache system configuration"
            except:
                if redis_url:
                    check.status = "WARNING"
                    check.details += ", cache endpoints not found"
                    check.recommendation = "Verify cache endpoint configuration"

            # Check cache-related environment variables
            cache_ttl = os.getenv("CACHE_TTL")
            cache_size = os.getenv("CACHE_SIZE")

            if cache_ttl and cache_size:
                check.details += f", cache parameters configured"
            else:
                if redis_url:  # Only warn if Redis is configured
                    check.details += ", cache parameters not configured"
                    if check.status == "PASS":
                        check.status = "WARNING"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Cache configuration check failed: {str(e)}"
            check.recommendation = "Fix cache system configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_api_documentation(self):
        """Check API documentation availability"""
        logger.info("📚 Checking API Documentation...")

        check = DeploymentCheck(
            name="API Documentation",
            category="Documentation",
            status="PASS",
            description="Verify API documentation is available and accessible"
        )
        start_time = time.time()

        try:
            # Test documentation endpoints
            doc_endpoints = [
                "/api/v1/docs",
                "/api/v1/redoc",
                "/api/v1/openapi.json"
            ]

            working_doc_endpoints = 0
            for endpoint in doc_endpoints:
                try:
                    response = self.client.get(endpoint)
                    if response.status_code == 200:
                        working_doc_endpoints += 1
                except:
                    pass

            if working_doc_endpoints >= 2:
                check.details = f"{working_doc_endpoints}/{len(doc_endpoints)} documentation endpoints working"
            elif working_doc_endpoints >= 1:
                check.status = "WARNING"
                check.details = f"Only {working_doc_endpoints}/{len(doc_endpoints)} documentation endpoints working"
                check.recommendation = "Fix API documentation endpoints"
            else:
                check.status = "FAIL"
                check.details = "No API documentation endpoints found"
                check.recommendation = "Enable API documentation in production"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"API documentation check failed: {str(e)}"
            check.recommendation = "Fix API documentation configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_load_balancer_configuration(self):
        """Check load balancer configuration"""
        logger.info("⚖️ Checking Load Balancer Configuration...")

        check = DeploymentCheck(
            name="Load Balancer Configuration",
            category="Infrastructure",
            status="PASS",
            description="Verify load balancer configuration"
        )
        start_time = time.time()

        try:
            # Check for load balancer headers
            response = self.client.get("/api/v1/health")

            lb_headers = [
                "X-Forwarded-For",
                "X-Real-IP",
                "X-Forwarded-Proto",
                "X-Forwarded-Host"
            ]

            lb_headers_present = [h for h in lb_headers if h.lower() in response.headers]

            if lb_headers_present:
                check.details = f"Load balancer headers present: {lb_headers_present}"
            else:
                check.status = "INFO"
                check.details = "No load balancer headers detected"
                check.recommendation = "Configure load balancer if using multiple instances"

            # Check for multiple instance configuration
            docker_compose_files = ["docker-compose.yml", "docker-compose.production.yml"]
            multiple_instances = False

            for compose_file in docker_compose_files:
                if os.path.exists(compose_file):
                    try:
                        with open(compose_file, 'r') as f:
                            compose_data = yaml.safe_load(f)

                        if 'services' in compose_data and 'backend' in compose_data['services']:
                            backend_config = compose_data['services']['backend']
                            if 'deploy' in backend_config and 'replicas' in backend_config['deploy']:
                                replicas = backend_config['deploy']['replicas']
                                if replicas > 1:
                                    multiple_instances = True
                                    check.details += f", {replicas} instances configured"
                                    break
                    except:
                        pass

            if not multiple_instances and self.env_config.environment_type == "production":
                check.status = "WARNING"
                check.details += " (Single instance configuration)"
                check.recommendation = "Consider multiple instances with load balancer for production"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Load balancer check failed: {str(e)}"
            check.recommendation = "Verify load balancer configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_container_configuration(self):
        """Check container configuration"""
        logger.info("🐳 Checking Container Configuration...")

        check = DeploymentCheck(
            name="Container Configuration",
            category="Infrastructure",
            status="PASS",
            description="Verify Docker container configuration"
        )
        start_time = time.time()

        try:
            # Check Docker Compose configuration
            docker_compose_files = ["docker-compose.yml", "docker-compose.production.yml"]

            compose_files_found = 0
            for compose_file in docker_compose_files:
                if os.path.exists(compose_file):
                    compose_files_found += 1
                    try:
                        with open(compose_file, 'r') as f:
                            compose_data = yaml.safe_load(f)

                        # Check for required services
                        required_services = ["backend"]
                        if 'services' in compose_data:
                            services_found = sum(1 for service in required_services
                                               if service in compose_data['services'])

                            if services_found == len(required_services):
                                check.details = f"Docker Compose configured with required services"
                            else:
                                check.status = "WARNING"
                                check.details = f"Missing services in Docker Compose"
                                check.recommendation = "Add missing services to Docker Compose"

                    except Exception as e:
                        check.status = "FAIL"
                        check.details = f"Invalid Docker Compose file: {compose_file}"
                        check.recommendation = "Fix Docker Compose configuration"

            if compose_files_found == 0:
                check.status = "WARNING"
                check.details = "No Docker Compose files found"
                check.recommendation = "Create Docker Compose configuration for deployment"

            # Check for Dockerfile
            dockerfile_path = "Dockerfile"
            if os.path.exists(dockerfile_path):
                check.details += ", Dockerfile exists"
            else:
                check.status = "WARNING"
                check.details += ", Dockerfile not found"
                check.recommendation = check.recommendation + ". Create Dockerfile for containerization"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Container configuration check failed: {str(e)}"
            check.recommendation = "Fix container configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_network_connectivity(self):
        """Check network connectivity and DNS"""
        logger.info("🌐 Checking Network Connectivity...")

        check = DeploymentCheck(
            name="Network Connectivity",
            category="Infrastructure",
            status="PASS",
            description="Verify network connectivity and DNS configuration"
        )
        start_time = time.time()

        try:
            # Test DNS resolution
            try:
                import socket
                if "localhost" in self.env_config.base_url:
                    # Test local connectivity
                    host = "localhost"
                    port = 8001
                else:
                    # Extract hostname from URL
                    host = self.env_config.base_url.split("//")[1].split(":")[0]
                    port = 443 if self.env_config.ssl_enabled else 80

                socket.create_connection((host, port), timeout=10)
                check.details = f"Network connectivity to {host}:{port} successful"
            except Exception as e:
                check.status = "FAIL"
                check.details = f"Network connectivity failed: {str(e)}"
                check.recommendation = "Fix network configuration and DNS"

            # Test external connectivity (AI services)
            try:
                response = self.client.get("/api/v1/models")
                if response.status_code == 200:
                    check.details += ", external AI services accessible"
                else:
                    if check.status == "PASS":
                        check.status = "WARNING"
                    check.details += ", external AI services not accessible"
                    check.recommendation = "Verify AI service API keys and connectivity"
            except:
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += ", AI services connectivity check failed"
                check.recommendation = "Check AI service configuration"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Network connectivity check failed: {str(e)}"
            check.recommendation = "Fix network configuration"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    async def _check_disaster_recovery(self):
        """Check disaster recovery configuration"""
        logger.info("🆘 Checking Disaster Recovery...")

        check = DeploymentCheck(
            name="Disaster Recovery",
            category="Operations",
            status="PASS",
            description="Verify disaster recovery procedures and configuration"
        )
        start_time = time.time()

        try:
            # Check for disaster recovery documentation
            dr_docs = [
                "docs/deployment/disaster-recovery.md",
                "DISASTER_RECOVERY.md",
                "README.md"
            ]

            dr_docs_found = 0
            for doc in dr_docs:
                if os.path.exists(doc):
                    dr_docs_found += 1
                    try:
                        with open(doc, 'r') as f:
                            content = f.read().lower()
                            if "disaster" in content or "recovery" in content:
                                check.details = "Disaster recovery documentation found"
                    except:
                        pass

            if dr_docs_found == 0:
                check.status = "WARNING"
                check.details = "No disaster recovery documentation found"
                check.recommendation = "Create disaster recovery procedures and documentation"

            # Check for high availability configuration
            ha_endpoints = [
                "/api/v1/ha/status",
                "/api/v1/ha/health"
            ]

            ha_working = False
            for endpoint in ha_endpoints:
                try:
                    response = self.client.get(endpoint)
                    if response.status_code == 200:
                        ha_working = True
                        check.details += ", HA endpoints available"
                        break
                except:
                    pass

            if not ha_working and self.env_config.environment_type == "production":
                if check.status == "PASS":
                    check.status = "WARNING"
                check.details += ", HA configuration not found"
                check.recommendation = "Consider high availability configuration for production"

        except Exception as e:
            check.status = "FAIL"
            check.details = f"Disaster recovery check failed: {str(e)}"
            check.recommendation = "Configure disaster recovery procedures"

        check.execution_time = time.time() - start_time
        self.deployment_checks.append(check)

    def _generate_deployment_report(self) -> Dict:
        """Generate comprehensive deployment readiness report"""
        logger.info("📋 Generating Deployment Readiness Report...")

        # Categorize checks by status
        critical_checks = [c for c in self.deployment_checks if c.critical]
        failed_checks = [c for c in self.deployment_checks if c.status == "FAIL"]
        warning_checks = [c for c in self.deployment_checks if c.status == "WARNING"]
        passed_checks = [c for c in self.deployment_checks if c.status == "PASS"]

        # Calculate readiness score
        total_checks = len(self.deployment_checks)
        critical_failures = len([c for c in critical_checks if c.status == "FAIL"])
        total_failures = len(failed_checks)
        total_warnings = len(warning_checks)

        # Weight the score
        base_score = 100.0
        critical_penalty = critical_failures * 30.0
        failure_penalty = total_failures * 10.0
        warning_penalty = total_warnings * 2.0

        readiness_score = max(0, base_score - critical_penalty - failure_penalty - warning_penalty)

        # Determine deployment readiness
        if readiness_score >= 90 and critical_failures == 0:
            deployment_readiness = "READY"
        elif readiness_score >= 80 and critical_failures == 0:
            deployment_readiness = "MOSTLY_READY"
        elif readiness_score >= 70:
            deployment_readiness = "NEEDS_ATTENTION"
        else:
            deployment_readiness = "NOT_READY"

        # Generate recommendations
        recommendations = self._generate_deployment_recommendations(critical_checks, failed_checks, warning_checks)

        # Group checks by category
        checks_by_category = {}
        for check in self.deployment_checks:
            if check.category not in checks_by_category:
                checks_by_category[check.category] = []
            checks_by_category[check.category].append(check)

        category_status = {}
        for category, checks in checks_by_category.items():
            passed = len([c for c in checks if c.status == "PASS"])
            total = len(checks)
            category_status[category] = {
                "passed": passed,
                "total": total,
                "percentage": (passed / total * 100) if total > 0 else 0
            }

        return {
            "readiness_score": readiness_score,
            "deployment_readiness": deployment_readiness,
            "environment_info": {
                "environment_type": self.env_config.environment_type,
                "base_url": self.env_config.base_url,
                "ssl_enabled": self.env_config.ssl_enabled,
                "monitoring_enabled": self.env_config.monitoring_enabled,
                "backup_enabled": self.env_config.backup_enabled
            },
            "summary": {
                "total_checks": total_checks,
                "critical_checks": len(critical_checks),
                "failed_checks": total_failures,
                "warning_checks": total_warnings,
                "passed_checks": len(passed_checks),
                "critical_failures": critical_failures
            },
            "category_status": category_status,
            "critical_issues": [
                {
                    "name": check.name,
                    "category": check.category,
                    "description": check.details,
                    "recommendation": check.recommendation
                }
                for check in critical_checks if check.status == "FAIL"
            ],
            "all_checks": [
                {
                    "name": check.name,
                    "category": check.category,
                    "status": check.status,
                    "description": check.details,
                    "recommendation": check.recommendation,
                    "critical": check.critical,
                    "execution_time": check.execution_time
                }
                for check in self.deployment_checks
            ],
            "recommendations": recommendations
        }

    def _generate_deployment_recommendations(self, critical_checks, failed_checks, warning_checks) -> List[str]:
        """Generate deployment recommendations"""
        recommendations = []

        # Critical issues first
        if critical_checks:
            recommendations.append("🚨 CRITICAL: Address all critical issues before production deployment")

        # Security recommendations
        security_issues = [c for c in critical_checks + failed_checks if c.category == "Security"]
        if security_issues:
            recommendations.append("🔒 Fix all security-related issues including SSL configuration and security headers")

        # Infrastructure recommendations
        infrastructure_issues = [c for c in critical_checks + failed_checks if c.category == "Infrastructure"]
        if infrastructure_issues:
            recommendations.append("🏗️ Resolve infrastructure configuration issues (Docker, networking, load balancer)")

        # Operations recommendations
        operations_issues = [c for c in critical_checks + failed_checks if c.category == "Operations"]
        if operations_issues:
            recommendations.append("⚙️ Fix operational issues (monitoring, backup, logging)")

        # Performance recommendations
        performance_issues = [c for c in critical_checks + failed_checks if c.category == "Performance"]
        if performance_issues:
            recommendations.append("⚡ Address performance issues (database, caching, rate limiting)")

        # Database recommendations
        if not self.env_config.database_url or "sqlite" in self.env_config.database_url.lower():
            if self.env_config.environment_type == "production":
                recommendations.append("🗄️ Migrate from SQLite to PostgreSQL for production deployment")

        # Monitoring recommendations
        if not self.env_config.monitoring_enabled and self.env_config.environment_type == "production":
            recommendations.append("📊 Enable monitoring and alerting for production environment")

        # Backup recommendations
        if not self.env_config.backup_enabled and self.env_config.environment_type == "production":
            recommendations.append("💾 Enable backup and disaster recovery systems")

        # General recommendations
        if not critical_checks and not failed_checks:
            if len(warning_checks) > 0:
                recommendations.append("✅ System is mostly ready for deployment. Address warnings for optimal performance")
            else:
                recommendations.append("✅ System is fully ready for production deployment")

        recommendations.append("📝 Document deployment procedures and create rollback plan")
        recommendations.append("🧪 Perform final staging environment testing before production deployment")

        return recommendations


# Pytest test functions
@pytest.fixture
async def deployment_validator():
    """Fixture for deployment validator"""
    return ProductionDeploymentValidator()


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_production_deployment_readiness(deployment_validator):
    """Test production deployment readiness"""
    report = await deployment_validator.run_production_validation()

    # Basic production requirements
    assert report["readiness_score"] >= 70.0, f"Deployment readiness score too low: {report['readiness_score']}"
    assert report["summary"]["critical_failures"] == 0, "Critical failures must be resolved before deployment"

    # Critical production requirements
    if os.getenv("ENVIRONMENT") == "production":
        assert report["deployment_readiness"] in ["READY", "MOSTLY_READY"], f"Production not ready: {report['deployment_readiness']}"

    # Log deployment results
    logger.info(f"🚀 Production Deployment Readiness Results:")
    logger.info(f"   Readiness Score: {report['readiness_score']:.2f}/100")
    logger.info(f"   Deployment Readiness: {report['deployment_readiness']}")
    logger.info(f"   Critical Issues: {report['summary']['critical_failures']}")
    logger.info(f"   Failed Checks: {report['summary']['failed_checks']}")


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_critical_deployment_checks_only(deployment_validator):
    """Test only critical deployment checks for faster validation"""
    # Run only critical checks
    await deployment_validator._detect_environment_configuration()
    await deployment_validator._check_ssl_configuration()
    await deployment_validator._check_security_headers()
    await deployment_validator._check_environment_variables()
    await deployment_validator._check_error_handling()

    # Generate partial report
    critical_checks = [c for c in deployment_validator.deployment_checks if c.critical]
    critical_failures = [c for c in critical_checks if c.status == "FAIL"]

    # Must have no critical failures
    assert len(critical_failures) == 0, f"Critical deployment failures: {len(critical_failures)}"

    logger.info(f"⚡ Critical Deployment Checks - Issues: {len(critical_failures)}")


if __name__ == "__main__":
    # Run deployment validation directly
    async def main():
        print("🚀 Starting Production Deployment Validation")
        print("=" * 80)

        deployment_validator = ProductionDeploymentValidator()
        report = await deployment_validator.run_production_validation()

        print("\n🏁 PRODUCTION DEPLOYMENT READINESS REPORT")
        print("=" * 60)
        print(f"Readiness Score: {report['readiness_score']:.2f}/100")
        print(f"Deployment Readiness: {report['deployment_readiness']}")

        print(f"\n🔍 ENVIRONMENT INFO:")
        print(f"   Environment: {report['environment_info']['environment_type']}")
        print(f"   SSL Enabled: {'Yes' if report['environment_info']['ssl_enabled'] else 'No'}")
        print(f"   Monitoring: {'Yes' if report['environment_info']['monitoring_enabled'] else 'No'}")
        print(f"   Backup: {'Yes' if report['environment_info']['backup_enabled'] else 'No'}")

        print(f"\n📊 CHECK SUMMARY:")
        print(f"   Total Checks: {report['summary']['total_checks']}")
        print(f"   Passed: {report['summary']['passed_checks']}")
        print(f"   Warnings: {report['summary']['warning_checks']}")
        print(f"   Failed: {report['summary']['failed_checks']}")
        print(f"   Critical Failures: {report['summary']['critical_failures']}")

        print(f"\n📈 CATEGORY STATUS:")
        for category, status in report['category_status'].items():
            print(f"   {category}: {status['passed']}/{status['total']} ({status['percentage']:.1f}%)")

        if report['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in report['critical_issues']:
                print(f"   • {issue['name']}: {issue['description']}")
                print(f"     Recommendation: {issue['recommendation']}")

        if report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"   - {rec}")

        print("\n" + "=" * 80)
        if report['deployment_readiness'] == "READY":
            print("✅ SYSTEM READY FOR PRODUCTION DEPLOYMENT")
        elif report['deployment_readiness'] == "MOSTLY_READY":
            print("⚠️ SYSTEM MOSTLY READY - Minor issues to address")
        elif report['deployment_readiness'] == "NEEDS_ATTENTION":
            print("⚠️ SYSTEM NEEDS ATTENTION - Several issues to resolve")
        else:
            print("🚨 SYSTEM NOT READY - Critical issues must be resolved")

        # Save detailed deployment report
        report_file = f"data/deployment/deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed deployment report saved to: {report_file}")

    asyncio.run(main())