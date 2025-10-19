"""
租户管理API
提供企业级多租户用户管理功能
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.core.database import get_db
from backend.core.tenant_isolation import (
    get_current_tenant,
    get_current_tenant_user,
    get_current_user_id,
    get_current_user_role,
    require_tenant_role,
    TenantService,
    tenant_context
)
from backend.models.tenant import (
    Tenant, TenantUser, Team, TeamMember,
    TenantCreate, TenantUpdate, TenantResponse,
    TenantUserCreate, TenantUserUpdate, TenantUserResponse,
    TeamCreate, TeamUpdate, TeamResponse,
    TeamMemberCreate, TeamMemberUpdate, TeamMemberResponse,
    TenantStatus, TenantPlan, UserRole,
    get_default_quotas, generate_tenant_slug
)
from backend.core.security import get_password_hash, generate_password_reset_token
from backend.core.email import send_email

router = APIRouter()

# 租户管理端点

@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db)
):
    """创建新租户"""
    # 检查slug是否已存在
    existing_tenant = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="租户标识符已存在"
        )

    # 检查域名是否已存在
    if tenant_data.domain:
        existing_domain = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="域名已被使用"
            )

    # 创建租户
    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        domain=tenant_data.domain,
        email=tenant_data.email,
        phone=tenant_data.phone,
        address=tenant_data.address,
        plan=tenant_data.plan,
        quotas=get_default_quotas(tenant_data.plan).dict() if tenant_data.quotas is None else tenant_data.quotas.dict(),
        settings=tenant_data.settings.dict() if tenant_data.settings else {},
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14) if tenant_data.plan == TenantPlan.STARTER else None
    )

    db.add(tenant)
    db.flush()  # 获取tenant.id

    # 如果提供了用户ID，将用户添加为租户所有者
    current_user_id = get_current_user_id()
    if current_user_id:
        tenant_user = TenantUser(
            tenant_id=tenant.id,
            user_id=current_user_id,
            role=UserRole.OWNER,
            is_active=True,
            joined_at=datetime.now(timezone.utc)
        )
        db.add(tenant_user)

    db.commit()
    db.refresh(tenant)

    # 构建响应
    response = TenantResponse.from_orm(tenant)
    response.user_count = 1 if current_user_id else 0
    response.team_count = 0
    response.api_key_count = 0

    return response

@router.get("/tenants", response_model=List[TenantResponse])
async def get_user_tenants(
    include_inactive: bool = Query(False, description="包含非活跃租户"),
    db: Session = Depends(get_db)
):
    """获取用户可访问的租户列表"""
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未认证"
        )

    tenant_service = TenantService(db)
    tenants = tenant_service.get_user_tenants(user_id)

    # 构建响应
    responses = []
    for tenant in tenants:
        stats = tenant_service.get_tenant_stats(tenant.id)
        response = TenantResponse.from_orm(tenant)
        response.user_count = stats.get("user_count", 0)
        response.team_count = stats.get("team_count", 0)
        response.api_key_count = stats.get("api_key_count", 0)
        responses.append(response)

    return responses

@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """获取租户详情"""
    tenant_service = TenantService(db)
    stats = tenant_service.get_tenant_stats(tenant.id)

    response = TenantResponse.from_orm(tenant)
    response.user_count = stats.get("user_count", 0)
    response.team_count = stats.get("team_count", 0)
    response.api_key_count = stats.get("api_key_count", 0)

    return response

@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_update: TenantUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """更新租户信息"""
    # 检查权限：只有所有者和管理员可以更新租户信息
    user_role = get_current_user_role()
    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以更新租户信息"
        )

    # 更新字段
    update_data = tenant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)

    tenant.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tenant)

    # 构建响应
    tenant_service = TenantService(db)
    stats = tenant_service.get_tenant_stats(tenant.id)
    response = TenantResponse.from_orm(tenant)
    response.user_count = stats.get("user_count", 0)
    response.team_count = stats.get("team_count", 0)
    response.api_key_count = stats.get("api_key_count", 0)

    return response

@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """删除租户（软删除）"""
    # 检查权限：只有所有者可以删除租户
    user_role = get_current_user_role()
    if user_role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者可以删除租户"
        )

    # 软删除：设置为非活跃状态
    tenant.status = TenantStatus.INACTIVE
    tenant.updated_at = datetime.now(timezone.utc)
    db.commit()

# 租户用户管理端点

@router.get("/tenants/{tenant_id}/users", response_model=List[TenantUserResponse])
async def get_tenant_users(
    include_inactive: bool = Query(False, description="包含非活跃用户"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """获取租户用户列表"""
    tenant_service = TenantService(db)
    users = tenant_service.get_tenant_users(tenant.id, include_inactive)

    return [TenantUserResponse.from_orm(user) for user in users]

@router.post("/tenants/{tenant_id}/users", response_model=TenantUserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user_to_tenant(
    user_data: TenantUserCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """邀请用户加入租户"""
    # 检查权限
    user_role = get_current_user_role()
    current_user_id = get_current_user_id()

    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以邀请用户"
        )

    # 检查用户是否已在租户中
    existing_user = db.query(TenantUser).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == user_data.user_id
        )
    ).first()

    if existing_user:
        if existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户已在租户中"
            )
        else:
            # 重新激活用户
            existing_user.is_active = True
            existing_user.role = user_data.role
            existing_user.permissions = user_data.permissions
            existing_user.invited_by = current_user_id
            existing_user.invited_at = datetime.now(timezone.utc)
            existing_user.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(existing_user)

            # 发送邀请邮件
            await send_user_invitation_email(existing_user, tenant, user_data.invite_message)

            return TenantUserResponse.from_orm(existing_user)

    # 检查配额
    tenant_service = TenantService(db)
    can_add, quota_info = tenant_service.quota_manager.check_quota(tenant.id, "max_users", 1)
    if not can_add:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户配额已满 ({quota_info['current']}/{quota_info['limit']})"
        )

    # 创建租户用户
    tenant_user = TenantUser(
        tenant_id=tenant.id,
        user_id=user_data.user_id,
        role=user_data.role,
        permissions=user_data.permissions,
        is_active=True,
        invited_by=current_user_id,
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc)
    )

    db.add(tenant_user)
    db.commit()
    db.refresh(tenant_user)

    # 发送邀请邮件
    await send_user_invitation_email(tenant_user, tenant, user_data.invite_message)

    return TenantUserResponse.from_orm(tenant_user)

@router.put("/tenants/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def update_tenant_user(
    user_id: str,
    user_update: TenantUserUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """更新租户用户信息"""
    # 检查权限
    current_user_role = get_current_user_role()
    current_user_id = get_current_user_id()

    if current_user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        # 普通用户只能更新自己的信息
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能更新自己的信息"
            )

    # 获取要更新的用户
    tenant_user = db.query(TenantUser).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == user_id
        )
    ).first()

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不在租户中"
        )

    # 更新字段
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(tenant_user, field):
            setattr(tenant_user, field, value)

    tenant_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tenant_user)

    return TenantUserResponse.from_orm(tenant_user)

@router.delete("/tenants/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_tenant(
    user_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """从租户中移除用户"""
    # 检查权限
    current_user_role = get_current_user_role()
    current_user_id = get_current_user_id()

    if current_user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        # 普通用户只能移除自己
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能移除自己"
            )

    # 不能移除最后一个所有者
    if current_user_role == UserRole.OWNER:
        owner_count = db.query(TenantUser).filter(
            and_(
                TenantUser.tenant_id == tenant.id,
                TenantUser.role == UserRole.OWNER,
                TenantUser.is_active == True
            )
        ).count()

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能移除最后一个所有者"
            )

    # 获取要移除的用户
    tenant_user = db.query(TenantUser).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == user_id
        )
    ).first()

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不在租户中"
        )

    # 软删除：设置为非活跃状态
    tenant_user.is_active = False
    tenant_user.updated_at = datetime.now(timezone.utc)
    db.commit()

# 团队管理端点

@router.get("/tenants/{tenant_id}/teams", response_model=List[TeamResponse])
async def get_tenant_teams(
    include_inactive: bool = Query(False, description="包含非活跃团队"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """获取租户团队列表"""
    tenant_service = TenantService(db)
    teams = tenant_service.get_tenant_teams(tenant.id, include_inactive)

    # 添加成员数量
    responses = []
    for team in teams:
        member_count = db.query(TeamMember).filter(
            and_(
                TeamMember.team_id == team.id,
                TeamMember.is_active == True
            )
        ).count()

        response = TeamResponse.from_orm(team)
        response.member_count = member_count
        responses.append(response)

    return responses

@router.post("/tenants/{tenant_id}/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """创建团队"""
    # 检查权限
    user_role = get_current_user_role()
    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以创建团队"
        )

    # 检查团队名称是否已存在
    existing_team = db.query(Team).filter(
        and_(
            Team.tenant_id == tenant.id,
            Team.slug == team_data.slug
        )
    ).first()

    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="团队标识符已存在"
        )

    # 检查父团队
    if team_data.parent_team_id:
        parent_team = db.query(Team).filter(
            and_(
                Team.id == team_data.parent_team_id,
                Team.tenant_id == tenant.id,
                Team.is_active == True
            )
        ).first()

        if not parent_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父团队不存在"
            )

    # 检查配额
    tenant_service = TenantService(db)
    can_add, quota_info = tenant_service.quota_manager.check_quota(tenant.id, "max_teams", 1)
    if not can_add:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"团队配额已满 ({quota_info['current']}/{quota_info['limit']})"
        )

    # 创建团队
    team = Team(
        tenant_id=tenant.id,
        name=team_data.name,
        description=team_data.description,
        slug=team_data.slug,
        parent_team_id=team_data.parent_team_id,
        quotas=team_data.quotas,
        permissions=team_data.permissions
    )

    db.add(team)
    db.commit()
    db.refresh(team)

    response = TeamResponse.from_orm(team)
    response.member_count = 0

    return response

@router.put("/tenants/{tenant_id}/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    team_update: TeamUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """更新团队信息"""
    # 检查权限
    user_role = get_current_user_role()
    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以更新团队信息"
        )

    # 获取团队
    team = db.query(Team).filter(
        and_(
            Team.id == team_id,
            Team.tenant_id == tenant.id
        )
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队不存在"
        )

    # 检查父团队
    if team_update.parent_team_id:
        if team_update.parent_team_id == team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="团队不能设置自己为父团队"
            )

        parent_team = db.query(Team).filter(
            and_(
                Team.id == team_update.parent_team_id,
                Team.tenant_id == tenant.id,
                Team.is_active == True
            )
        ).first()

        if not parent_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父团队不存在"
            )

    # 更新字段
    update_data = team_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(team, field):
            setattr(team, field, value)

    team.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(team)

    # 添加成员数量
    member_count = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team.id,
            TeamMember.is_active == True
        )
    ).count()

    response = TeamResponse.from_orm(team)
    response.member_count = member_count

    return response

@router.delete("/tenants/{tenant_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """删除团队（软删除）"""
    # 检查权限
    user_role = get_current_user_role()
    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以删除团队"
        )

    # 获取团队
    team = db.query(Team).filter(
        and_(
            Team.id == team_id,
            Team.tenant_id == tenant.id
        )
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队不存在"
        )

    # 检查是否有子团队
    child_teams = db.query(Team).filter(
        and_(
            Team.parent_team_id == team_id,
            Team.is_active == True
        )
    ).count()

    if child_teams > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除包含子团队的团队"
        )

    # 软删除：设置为非活跃状态
    team.is_active = False
    team.updated_at = datetime.now(timezone.utc)

    # 同时移除所有成员
    db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True
        )
    ).update({
        TeamMember.is_active: False,
        TeamMember.updated_at: datetime.now(timezone.utc)
    })

    db.commit()

# 团队成员管理端点

@router.get("/tenants/{tenant_id}/teams/{team_id}/members", response_model=List[TeamMemberResponse])
async def get_team_members(
    team_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """获取团队成员列表"""
    # 验证团队存在
    team = db.query(Team).filter(
        and_(
            Team.id == team_id,
            Team.tenant_id == tenant.id
        )
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队不存在"
        )

    # 获取团队成员
    members = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True
        )
    ).all()

    return [TeamMemberResponse.from_orm(member) for member in members]

@router.post("/tenants/{tenant_id}/teams/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: str,
    member_data: TeamMemberCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """添加团队成员"""
    # 检查权限
    user_role = get_current_user_role()
    current_user_id = get_current_user_id()

    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以添加团队成员"
        )

    # 验证团队存在
    team = db.query(Team).filter(
        and_(
            Team.id == team_id,
            Team.tenant_id == tenant.id,
            Team.is_active == True
        )
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队不存在"
        )

    # 检查用户是否已在团队中
    existing_member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == member_data.user_id
        )
    ).first()

    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户已在团队中"
            )
        else:
            # 重新激活成员
            existing_member.is_active = True
            existing_member.role = member_data.role
            existing_member.added_by = current_user_id
            existing_member.added_at = datetime.now(timezone.utc)
            existing_member.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(existing_member)

            return TeamMemberResponse.from_orm(existing_member)

    # 检查用户是否在租户中
    tenant_user = db.query(TenantUser).filter(
        and_(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == member_data.user_id,
            TenantUser.is_active == True
        )
    ).first()

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不在租户中，请先邀请用户加入租户"
        )

    # 创建团队成员
    team_member = TeamMember(
        team_id=team_id,
        user_id=member_data.user_id,
        role=member_data.role,
        added_by=current_user_id,
        added_at=datetime.now(timezone.utc)
    )

    db.add(team_member)
    db.commit()
    db.refresh(team_member)

    return TeamMemberResponse.from_orm(team_member)

@router.put("/tenants/{tenant_id}/teams/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member(
    team_id: str,
    user_id: str,
    member_update: TeamMemberUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """更新团队成员信息"""
    # 检查权限
    user_role = get_current_user_role()

    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者和管理员可以更新团队成员信息"
        )

    # 获取团队成员
    team_member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    ).first()

    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队成员不存在"
        )

    # 更新字段
    update_data = member_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(team_member, field):
            setattr(team_member, field, value)

    team_member.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(team_member)

    return TeamMemberResponse.from_orm(team_member)

@router.delete("/tenants/{tenant_id}/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: str,
    user_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """从团队中移除成员"""
    # 检查权限
    user_role = get_current_user_role()
    current_user_id = get_current_user_id()

    if user_role not in [UserRole.OWNER, UserRole.ADMIN]:
        # 普通用户只能移除自己
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能移除自己"
            )

    # 获取团队成员
    team_member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    ).first()

    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="团队成员不存在"
        )

    # 软删除：设置为非活跃状态
    team_member.is_active = False
    team_member.updated_at = datetime.now(timezone.utc)
    db.commit()

# 统计端点

@router.get("/tenants/{tenant_id}/stats", response_model=Dict[str, Any])
async def get_tenant_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """获取租户统计信息"""
    tenant_service = TenantService(db)
    return tenant_service.get_tenant_stats(tenant.id)

# 辅助函数

async def send_user_invitation_email(tenant_user: TenantUser, tenant: Tenant, message: str = None):
    """发送用户邀请邮件"""
    try:
        # 这里需要根据实际的邮件服务实现
        subject = f"邀请您加入 {tenant.name}"

        body = f"""
        您好！

        {tenant.name} 邀请您加入他们的AI Hub平台团队。

        请点击以下链接接受邀请：
        [邀请链接]

        {message or ''}

        如果您有任何问题，请联系租户管理员。

        谢谢！
        AI Hub Team
        """

        # await send_email(to=tenant_user.email, subject=subject, body=body)
        print(f"发送邀请邮件给用户 {tenant_user.user_id}: {subject}")

    except Exception as e:
        print(f"发送邀请邮件失败: {e}")