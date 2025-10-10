"""
Performance Tests
性能测试 - 数据库查询和响应时间
"""

import pytest
import asyncio
import time
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import text, func, and_
from sqlalchemy.orm import selectinload

from backend.main import app
from backend.models.database import get_db
from backend.models.organization import Organization
from backend.models.team import Team
from backend.models.member import Member
from backend.models.budget import Budget
from backend.models.user import User
from backend.models.usage_record import UsageRecord
from backend.core.security import get_password_hash


class TestDatabasePerformance:
    """数据库性能测试"""

    @pytest.fixture
    async def performance_data(self):
        """创建性能测试数据"""
        async for db in get_db():
            # 创建多个组织和用户
            orgs = []
            users = []

            for i in range(10):
                # 创建组织
                org = Organization(
                    id=uuid4(),
                    name=f"Performance Organization {i}",
                    slug=f"perf-org-{i}",
                    plan="pro",
                    status="active",
                    created_at=datetime.utcnow()
                )
                orgs.append(org)
                db.add(org)

                # 创建用户
                user = User(
                    id=uuid4(),
                    email=f"perf_user_{i}@test.com",
                    password_hash=get_password_hash("password123"),
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                users.append(user)
                db.add(user)

            await db.commit()

            # 创建成员关系
            members = []
            for i, org in enumerate(orgs):
                for j in range(min(5, len(users))):  # 每个组织最多5个成员
                    member = Member(
                        id=uuid4(),
                        user_id=users[j].id,
                        organization_id=org.id,
                        role="member" if j > 0 else "owner",
                        created_at=datetime.utcnow()
                    )
                    members.append(member)
                    db.add(member)

            await db.commit()

            # 创建团队
            teams = []
            for i, org in enumerate(orgs):
                for j in range(3):  # 每个组织3个团队
                    team = Team(
                        id=uuid4(),
                        organization_id=org.id,
                        name=f"Team {i}-{j}",
                        description=f"Performance test team {i}-{j}",
                        created_at=datetime.utcnow()
                    )
                    teams.append(team)
                    db.add(team)

            await db.commit()

            # 创建预算
            budgets = []
            for org in orgs:
                budget = Budget(
                    id=uuid4(),
                    organization_id=org.id,
                    monthly_limit=1000.0 + (orgs.index(org) * 100),
                    current_spend=0.0,
                    currency="USD",
                    status="active",
                    created_at=datetime.utcnow()
                )
                budgets.append(budget)
                db.add(budget)

            await db.commit()

            # 创建使用记录
            usage_records = []
            for i in range(100):  # 100条使用记录
                record = UsageRecord(
                    id=uuid4(),
                    organization_id=orgs[i % len(orgs)].id,
                    team_id=teams[i % len(teams)].id if teams else None,
                    user_id=users[i % len(users)].id,
                    model="test-model",
                    total_tokens=100 + i,
                    estimated_cost=0.01 + (i * 0.001),
                    created_at=datetime.utcnow()
                )
                usage_records.append(record)
                db.add(record)

            await db.commit()

            yield {
                'orgs': orgs,
                'users': users,
                'members': members,
                'teams': teams,
                'budgets': budgets,
                'usage_records': usage_records
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM usage_records"))
            await db.execute(text("DELETE FROM budgets"))
            await db.execute(text("DELETE FROM teams"))
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    async def test_organization_query_performance(self, performance_data):
        """测试组织查询性能"""
        async for db in get_db():
            # 测试简单查询性能
            start_time = time.time()
            result = await db.execute(text("SELECT * FROM organizations LIMIT 10"))
            orgs = result.fetchall()
            query_time = time.time() - start_time

            assert len(orgs) <= 10
            assert query_time < 0.1  # 查询时间应小于100ms

            # 测试带条件的查询性能
            start_time = time.time()
            result = await db.execute(
                text("SELECT * FROM organizations WHERE plan = :plan"),
                {"plan": "pro"}
            )
            pro_orgs = result.fetchall()
            query_time = time.time() - start_time

            assert len(pro_orgs) > 0
            assert query_time < 0.1  # 查询时间应小于100ms

    async def test_join_query_performance(self, performance_data):
        """测试关联查询性能"""
        async for db in get_db():
            # 测试组织-成员关联查询
            start_time = time.time()
            result = await db.execute(text("""
                SELECT o.name, m.role, u.email
                FROM organizations o
                JOIN members m ON o.id = m.organization_id
                JOIN users u ON m.user_id = u.id
                WHERE o.plan = :plan
                LIMIT 20
            """), {"plan": "pro"})
            join_result = result.fetchall()
            query_time = time.time() - start_time

            assert len(join_result) > 0
            assert query_time < 0.2  # 关联查询时间应小于200ms

            # 测试聚合查询性能
            start_time = time.time()
            result = await db.execute(text("""
                SELECT
                    o.id,
                    o.name,
                    COUNT(m.id) as member_count,
                    COUNT(t.id) as team_count
                FROM organizations o
                LEFT JOIN members m ON o.id = m.organization_id
                LEFT JOIN teams t ON o.id = t.organization_id
                GROUP BY o.id, o.name
                ORDER BY member_count DESC
            """))
            agg_result = result.fetchall()
            query_time = time.time() - start_time

            assert len(agg_result) > 0
            assert query_time < 0.3  # 聚合查询时间应小于300ms

    async def test_usage_record_query_performance(self, performance_data):
        """测试使用记录查询性能"""
        async for db in get_db():
            # 测试按时间范围查询
            start_time = time.time()
            result = await db.execute(text("""
                SELECT organization_id, SUM(total_tokens) as total_tokens, SUM(estimated_cost) as total_cost
                FROM usage_records
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY organization_id
            """))
            usage_stats = result.fetchall()
            query_time = time.time() - start_time

            assert len(usage_stats) > 0
            assert query_time < 0.2  # 统计查询时间应小于200ms

            # 测试复杂的使用记录查询
            start_time = time.time()
            result = await db.execute(text("""
                SELECT
                    o.name as org_name,
                    t.name as team_name,
                    u.email as user_email,
                    ur.model,
                    ur.total_tokens,
                    ur.estimated_cost
                FROM usage_records ur
                JOIN organizations o ON ur.organization_id = o.id
                LEFT JOIN teams t ON ur.team_id = t.id
                JOIN users u ON ur.user_id = u.id
                WHERE ur.total_tokens > 100
                ORDER BY ur.created_at DESC
                LIMIT 50
            """))
            detailed_usage = result.fetchall()
            query_time = time.time() - start_time

            assert len(detailed_usage) > 0
            assert query_time < 0.3  # 复杂查询时间应小于300ms

    async def test_pagination_performance(self, performance_data):
        """测试分页查询性能"""
        async for db in get_db():
            # 测试第一页性能
            start_time = time.time()
            result = await db.execute(text("""
                SELECT * FROM usage_records
                ORDER BY created_at DESC
                LIMIT 20 OFFSET 0
            """))
            page1 = result.fetchall()
            page1_time = time.time() - start_time

            assert len(page1) <= 20
            assert page1_time < 0.1

            # 测试最后一页性能（OFFSET较大）
            start_time = time.time()
            result = await db.execute(text("""
                SELECT * FROM usage_records
                ORDER BY created_at DESC
                LIMIT 20 OFFSET 80
            """))
            page_last = result.fetchall()
            page_last_time = time.time() - start_time

            assert len(page_last) <= 20
            assert page_last_time < 0.2  # 即使OFFSET大，也应该相对较快

    async def test_concurrent_query_performance(self, performance_data):
        """测试并发查询性能"""
        async def run_query():
            async for db in get_db():
                result = await db.execute(text("SELECT COUNT(*) FROM organizations"))
                return result.scalar()

        # 并发执行10个查询
        start_time = time.time()
        tasks = [run_query() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        assert all(r > 0 for r in results)
        assert total_time < 1.0  # 10个并发查询应在1秒内完成

    async def test_index_effectiveness(self, performance_data):
        """测试索引有效性"""
        async for db in get_db():
            # 查看查询计划（如果是支持EXPLAIN的数据库）
            # 这里我们测试有索引和无索引的查询性能差异

            # 有索引的查询（organization_id）
            start_time = time.time()
            result = await db.execute(
                text("SELECT * FROM usage_records WHERE organization_id = :org_id"),
                {"org_id": performance_data['orgs'][0].id}
            )
            indexed_query = result.fetchall()
            indexed_time = time.time() - start_time

            # 模拟无索引查询（使用不常用的字段）
            start_time = time.time()
            result = await db.execute(
                text("SELECT * FROM usage_records WHERE model = :model"),
                {"model": "test-model"}
            )
            non_indexed_query = result.fetchall()
            non_indexed_time = time.time() - start_time

            # 有索引的查询应该更快
            assert indexed_time < non_indexed_time * 1.5  # 允许一定的误差

    async def test_bulk_operations_performance(self, performance_data):
        """测试批量操作性能"""
        async for db in get_db():
            # 批量插入测试
            start_time = time.time()

            # 准备批量插入的数据
            new_records = []
            for i in range(50):
                record = UsageRecord(
                    id=uuid4(),
                    organization_id=performance_data['orgs'][0].id,
                    user_id=performance_data['users'][0].id,
                    model="bulk-test-model",
                    total_tokens=50 + i,
                    estimated_cost=0.005 + (i * 0.0001),
                    created_at=datetime.utcnow()
                )
                new_records.append(record)
                db.add(record)

            await db.commit()
            bulk_insert_time = time.time() - start_time

            assert bulk_insert_time < 1.0  # 批量插入50条记录应在1秒内完成

            # 批量删除测试
            start_time = time.time()
            for record in new_records[:25]:  # 删除一半
                await db.delete(record)
            await db.commit()
            bulk_delete_time = time.time() - start_time

            assert bulk_delete_time < 0.5  # 批量删除应在0.5秒内完成


class TestAPIPerformance:
    """API性能测试"""

    @pytest.fixture
    async def api_performance_data(self):
        """创建API性能测试数据"""
        async for db in get_db():
            # 创建测试用户
            user = User(
                id=uuid4(),
                email="api_perf@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            await db.commit()

            # 创建测试组织
            org = Organization(
                id=uuid4(),
                name="API Performance Organization",
                slug="api-perf-org",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )
            db.add(org)
            await db.commit()

            # 创建成员关系
            member = Member(
                id=uuid4(),
                user_id=user.id,
                organization_id=org.id,
                role="owner",
                created_at=datetime.utcnow()
            )
            db.add(member)
            await db.commit()

            yield {
                'user': user,
                'org': org
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    def get_auth_headers(self, user):
        """获取认证头"""
        from backend.core.security import create_access_token
        token = create_access_token(data={"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    async def test_api_response_time(self, api_performance_data):
        """测试API响应时间"""
        user = api_performance_data['user']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试模型列表API响应时间
            start_time = time.time()
            response = await client.get("/api/v1/models")
            response_time = time.time() - start_time

            assert response.status_code == 200
            assert response_time < 2.0  # 响应时间应小于2秒

            # 测试组织列表API响应时间
            start_time = time.time()
            response = await client.get("/api/v1/organizations/", headers=headers)
            response_time = time.time() - start_time

            assert response.status_code == 200
            assert response_time < 1.0  # 组织列表响应时间应小于1秒

    async def test_concurrent_api_requests(self, api_performance_data):
        """测试并发API请求"""
        user = api_performance_data['user']
        headers = self.get_auth_headers(user)

        async def make_request():
            async with AsyncClient(app=app, base_url="http://test") as client:
                start_time = time.time()
                response = await client.get("/api/v1/models")
                return response.status_code, time.time() - start_time

        # 并发发送20个请求
        start_time = time.time()
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # 验证所有请求都成功
        status_codes, response_times = zip(*results)
        assert all(code == 200 for code in status_codes)

        # 验证平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2.0

        # 验证总时间合理
        assert total_time < 5.0  # 20个并发请求应在5秒内完成

    async def test_memory_usage(self, api_performance_data):
        """测试内存使用情况"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行一系列API请求
        user = api_performance_data['user']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            for _ in range(50):
                await client.get("/api/v1/models")
                await client.get("/api/v1/organizations/", headers=headers)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 内存增长应该控制在合理范围内
        assert memory_increase < 100  # 内存增长应小于100MB

    async def test_database_connection_pool(self, api_performance_data):
        """测试数据库连接池性能"""
        # 模拟多个并发数据库操作
        async def db_operation():
            async for db in get_db():
                result = await db.execute(text("SELECT 1"))
                return result.scalar()

        # 并发执行数据库操作
        start_time = time.time()
        tasks = [db_operation() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        assert all(r == 1 for r in results)
        assert total_time < 2.0  # 50个并发数据库操作应在2秒内完成


class TestCachePerformance:
    """缓存性能测试（如果有缓存实现）"""

    async def test_without_cache(self, performance_data):
        """测试无缓存的查询性能"""
        async for db in get_db():
            # 多次执行相同查询
            times = []
            for _ in range(5):
                start_time = time.time()
                result = await db.execute(text("""
                    SELECT o.name, COUNT(m.id) as member_count
                    FROM organizations o
                    LEFT JOIN members m ON o.id = m.organization_id
                    GROUP BY o.id, o.name
                """))
                result.fetchall()
                times.append(time.time() - start_time)

            avg_time = sum(times) / len(times)
            assert avg_time < 0.3  # 平均查询时间应小于300ms

    async def test_with_cache_simulation(self, performance_data):
        """模拟缓存测试"""
        # 这里可以模拟Redis缓存测试
        # 由于当前可能没有实现缓存，这里只是预留接口

        cache_data = {}  # 模拟缓存

        async def cached_query(key, query_func):
            if key in cache_data:
                return cache_data[key]

            result = await query_func()
            cache_data[key] = result
            return result

        async for db in get_db():
            # 第一次查询（无缓存）
            start_time = time.time()
            result1 = await cached_query("org_stats", lambda: db.execute(text("""
                SELECT COUNT(*) as count FROM organizations
            """)))
            first_time = time.time() - start_time

            # 第二次查询（有缓存）
            start_time = time.time()
            result2 = await cached_query("org_stats", lambda: db.execute(text("""
                SELECT COUNT(*) as count FROM organizations
            """)))
            second_time = time.time() - start_time

            # 缓存查询应该更快
            assert second_time < first_time / 2


if __name__ == "__main__":
    # 运行性能测试
    asyncio.run(pytest.main([__file__, "-v", "-s"]))