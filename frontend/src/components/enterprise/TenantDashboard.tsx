/**
 * 企业租户仪表板组件
 * 提供企业级用户管理界面
 */

"use client";

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Building2,
  Users,
  Shield,
  Settings,
  Plus,
  MoreHorizontal,
  Edit,
  Trash2,
  UserPlus,
  Mail,
  Phone,
  Calendar,
  Activity,
  Key,
  Globe,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  Search,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';

// 类型定义
interface Tenant {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  status: 'active' | 'inactive' | 'suspended' | 'trial' | 'pending';
  plan: 'starter' | 'professional' | 'enterprise' | 'custom';
  email: string;
  phone?: string;
  address?: string;
  quotas: Record<string, any>;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
  trial_ends_at?: string;
  suspended_at?: string;
  user_count: number;
  team_count: number;
  api_key_count: number;
}

interface TenantUser {
  id: string;
  tenant_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'developer' | 'analyst' | 'member';
  permissions: string[];
  is_active: boolean;
  invited_by?: string;
  invited_at?: string;
  joined_at: string;
  last_login_at?: string;
  preferences: Record<string, any>;
  notifications: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Team {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  slug: string;
  parent_team_id?: string;
  is_active: boolean;
  quotas: Record<string, any>;
  permissions: string[];
  created_at: string;
  updated_at: string;
  member_count: number;
}

interface TenantStats {
  user_count: number;
  team_count: number;
  api_key_count: number;
  created_at: string;
  plan: string;
  status: string;
  quotas: Record<string, any>;
}

export default function TenantDashboard() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [tenantUsers, setTenantUsers] = useState<TenantUser[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [stats, setStats] = useState<TenantStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showCreateTenant, setShowCreateTenant] = useState(false);
  const [showInviteUser, setShowInviteUser] = useState(false);
  const [showCreateTeam, setShowCreateTeam] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // 表单状态
  const [newTenant, setNewTenant] = useState({
    name: '',
    slug: '',
    domain: '',
    email: '',
    phone: '',
    address: '',
    plan: 'starter' as const,
  });

  const [newUser, setNewUser] = useState({
    user_id: '',
    role: 'member' as const,
    permissions: [] as string[],
    invite_message: '',
  });

  const [newTeam, setNewTeam] = useState({
    name: '',
    description: '',
    slug: '',
    parent_team_id: '',
  });

  // 获取租户列表
  const fetchTenants = async () => {
    try {
      const response = await fetch('/api/v1/tenant/tenants');
      if (response.ok) {
        const data = await response.json();
        setTenants(data);
        if (data.length > 0 && !currentTenant) {
          setCurrentTenant(data[0]);
        }
      }
    } catch (error) {
      console.error('获取租户列表失败:', error);
      toast.error('获取租户列表失败');
    }
  };

  // 获取租户用户
  const fetchTenantUsers = async () => {
    if (!currentTenant) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/users`);
      if (response.ok) {
        const data = await response.json();
        setTenantUsers(data);
      }
    } catch (error) {
      console.error('获取租户用户失败:', error);
      toast.error('获取租户用户失败');
    }
  };

  // 获取团队列表
  const fetchTeams = async () => {
    if (!currentTenant) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/teams`);
      if (response.ok) {
        const data = await response.json();
        setTeams(data);
      }
    } catch (error) {
      console.error('获取团队列表失败:', error);
      toast.error('获取团队列表失败');
    }
  };

  // 获取租户统计
  const fetchStats = async () => {
    if (!currentTenant) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('获取租户统计失败:', error);
    }
  };

  // 创建租户
  const handleCreateTenant = async () => {
    try {
      const response = await fetch('/api/v1/tenant/tenants', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTenant),
      });

      if (response.ok) {
        const tenant = await response.json();
        setTenants([...tenants, tenant]);
        setCurrentTenant(tenant);
        setShowCreateTenant(false);
        setNewTenant({
          name: '',
          slug: '',
          domain: '',
          email: '',
          phone: '',
          address: '',
          plan: 'starter',
        });
        toast.success('租户创建成功');
      } else {
        const error = await response.json();
        toast.error(error.detail || '创建租户失败');
      }
    } catch (error) {
      console.error('创建租户失败:', error);
      toast.error('创建租户失败');
    }
  };

  // 邀请用户
  const handleInviteUser = async () => {
    if (!currentTenant) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newUser),
      });

      if (response.ok) {
        const user = await response.json();
        setTenantUsers([...tenantUsers, user]);
        setShowInviteUser(false);
        setNewUser({
          user_id: '',
          role: 'member',
          permissions: [],
          invite_message: '',
        });
        toast.success('用户邀请成功');
      } else {
        const error = await response.json();
        toast.error(error.detail || '邀请用户失败');
      }
    } catch (error) {
      console.error('邀请用户失败:', error);
      toast.error('邀请用户失败');
    }
  };

  // 创建团队
  const handleCreateTeam = async () => {
    if (!currentTenant) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/teams`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTeam),
      });

      if (response.ok) {
        const team = await response.json();
        setTeams([...teams, team]);
        setShowCreateTeam(false);
        setNewTeam({
          name: '',
          description: '',
          slug: '',
          parent_team_id: '',
        });
        toast.success('团队创建成功');
      } else {
        const error = await response.json();
        toast.error(error.detail || '创建团队失败');
      }
    } catch (error) {
      console.error('创建团队失败:', error);
      toast.error('创建团队失败');
    }
  };

  // 移除用户
  const handleRemoveUser = async (userId: string) => {
    if (!currentTenant) return;

    if (!confirm('确定要移除这个用户吗？')) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant.id}/users/${userId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setTenantUsers(tenantUsers.filter(user => user.user_id !== userId));
        toast.success('用户移除成功');
      } else {
        const error = await response.json();
        toast.error(error.detail || '移除用户失败');
      }
    } catch (error) {
      console.error('移除用户失败:', error);
      toast.error('移除用户失败');
    }
  };

  // 删除团队
  const handleDeleteTeam = async (teamId: string) => {
    if (!confirm('确定要删除这个团队吗？')) return;

    try {
      const response = await fetch(`/api/v1/tenant/tenants/${currentTenant?.id}/teams/${teamId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setTeams(teams.filter(team => team.id !== teamId));
        toast.success('团队删除成功');
      } else {
        const error = await response.json();
        toast.error(error.detail || '删除团队失败');
      }
    } catch (error) {
      console.error('删除团队失败:', error);
      toast.error('删除团队失败');
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'trial':
        return 'bg-blue-500';
      case 'suspended':
        return 'bg-red-500';
      case 'pending':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '活跃';
      case 'trial':
        return '试用';
      case 'suspended':
        return '暂停';
      case 'pending':
        return '待审核';
      default:
        return '未知';
    }
  };

  // 获取计划文本
  const getPlanText = (plan: string) => {
    switch (plan) {
      case 'starter':
        return '初创版';
      case 'professional':
        return '专业版';
      case 'enterprise':
        return '企业版';
      case 'custom':
        return '定制版';
      default:
        return '未知';
    }
  };

  // 获取角色文本
  const getRoleText = (role: string) => {
    switch (role) {
      case 'owner':
        return '所有者';
      case 'admin':
        return '管理员';
      case 'developer':
        return '开发者';
      case 'analyst':
        return '分析师';
      case 'member':
        return '成员';
      default:
        return '未知';
    }
  };

  // 计算配额使用率
  const getQuotaUsage = (quotaType: string) => {
    if (!stats || !stats.quotas) return 0;

    const quota = stats.quotas[quotaType];
    const current = stats[`${quotaType.split('_')[1]}_count`] || 0;

    if (!quota) return 100; // 无限制

    return Math.min(100, Math.round((current / quota) * 100));
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      await fetchTenants();
      setLoading(false);
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (currentTenant) {
      fetchTenantUsers();
      fetchTeams();
      fetchStats();
    }
  }, [currentTenant]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载企业数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">企业管理中心</h1>
          <p className="text-gray-600 mt-1">管理您的企业租户、用户和团队</p>
        </div>
        <div className="flex items-center space-x-4">
          <Select value={currentTenant?.id || ''} onValueChange={(value) => {
            const tenant = tenants.find(t => t.id === value);
            setCurrentTenant(tenant || null);
          }}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="选择租户" />
            </SelectTrigger>
            <SelectContent>
              {tenants.map((tenant) => (
                <SelectItem key={tenant.id} value={tenant.id}>
                  <div className="flex items-center space-x-2">
                    <Building2 className="h-4 w-4" />
                    <span>{tenant.name}</span>
                    <Badge variant="outline" className="text-xs">
                      {getPlanText(tenant.plan)}
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Dialog open={showCreateTenant} onOpenChange={setShowCreateTenant}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                新建租户
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建新租户</DialogTitle>
                <DialogDescription>
                  创建一个新的企业租户来管理您的团队和资源
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">租户名称</Label>
                  <Input
                    id="name"
                    value={newTenant.name}
                    onChange={(e) => setNewTenant({...newTenant, name: e.target.value})}
                    placeholder="输入租户名称"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">联系邮箱</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newTenant.email}
                    onChange={(e) => setNewTenant({...newTenant, email: e.target.value})}
                    placeholder="输入联系邮箱"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="plan">订阅计划</Label>
                  <Select value={newTenant.plan} onValueChange={(value: any) => setNewTenant({...newTenant, plan: value})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="starter">初创版</SelectItem>
                      <SelectItem value="professional">专业版</SelectItem>
                      <SelectItem value="enterprise">企业版</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowCreateTenant(false)}>
                  取消
                </Button>
                <Button onClick={handleCreateTenant}>
                  创建租户
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {currentTenant && (
        <>
          {/* 租户概览 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">用户总数</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.user_count || 0}</div>
                <p className="text-xs text-muted-foreground">
                  配额: {stats?.quotas.max_users || '无限制'}
                </p>
                {stats?.quotas.max_users && (
                  <Progress value={getQuotaUsage('max_users')} className="mt-2" />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">团队总数</CardTitle>
                <Shield className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.team_count || 0}</div>
                <p className="text-xs text-muted-foreground">
                  配额: {stats?.quotas.max_teams || '无限制'}
                </p>
                {stats?.quotas.max_teams && (
                  <Progress value={getQuotaUsage('max_teams')} className="mt-2" />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">API密钥</CardTitle>
                <Key className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.api_key_count || 0}</div>
                <p className="text-xs text-muted-foreground">
                  配额: {stats?.quotas.max_api_keys || '无限制'}
                </p>
                {stats?.quotas.max_api_keys && (
                  <Progress value={getQuotaUsage('max_api_keys')} className="mt-2" />
                )}
              </CardContent>
            </Card>
          </div>

          {/* 租户信息 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Building2 className="h-5 w-5" />
                <span>{currentTenant.name}</span>
                <Badge variant="outline">{getPlanText(currentTenant.plan)}</Badge>
                <Badge className={getStatusColor(currentTenant.status)}>
                  {getStatusText(currentTenant.status)}
                </Badge>
              </CardTitle>
              <CardDescription>
                租户ID: {currentTenant.id}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="flex items-center space-x-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{currentTenant.email}</span>
                </div>
                {currentTenant.phone && (
                  <div className="flex items-center space-x-2">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{currentTenant.phone}</span>
                  </div>
                )}
                {currentTenant.domain && (
                  <div className="flex items-center space-x-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{currentTenant.domain}</span>
                  </div>
                )}
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    创建于 {new Date(currentTenant.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 标签页 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">概览</TabsTrigger>
              <TabsTrigger value="users">用户管理</TabsTrigger>
              <TabsTrigger value="teams">团队管理</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 活动统计 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Activity className="h-5 w-5" />
                      <span>活动统计</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">日活跃用户</span>
                        <span className="font-medium">--</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">周活跃用户</span>
                        <span className="font-medium">--</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">API调用次数</span>
                        <span className="font-medium">--</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">存储使用量</span>
                        <span className="font-medium">--</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 系统状态 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <TrendingUp className="h-5 w-5" />
                      <span>系统状态</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">数据库连接</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">缓存服务</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">API服务</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <AlertCircle className="h-4 w-4 text-yellow-500" />
                        <span className="text-sm">备份服务</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="users" className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Input
                    placeholder="搜索用户..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Button variant="outline" size="icon">
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
                <Dialog open={showInviteUser} onOpenChange={setShowInviteUser}>
                  <DialogTrigger asChild>
                    <Button>
                      <UserPlus className="h-4 w-4 mr-2" />
                      邀请用户
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>邀请新用户</DialogTitle>
                      <DialogDescription>
                        邀请新用户加入租户 {currentTenant.name}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid gap-2">
                        <Label htmlFor="user_id">用户ID</Label>
                        <Input
                          id="user_id"
                          value={newUser.user_id}
                          onChange={(e) => setNewUser({...newUser, user_id: e.target.value})}
                          placeholder="输入用户ID"
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="role">角色</Label>
                        <Select value={newUser.role} onValueChange={(value: any) => setNewUser({...newUser, role: value})}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="member">成员</SelectItem>
                            <SelectItem value="developer">开发者</SelectItem>
                            <SelectItem value="analyst">分析师</SelectItem>
                            <SelectItem value="admin">管理员</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="invite_message">邀请消息 (可选)</Label>
                        <Textarea
                          id="invite_message"
                          value={newUser.invite_message}
                          onChange={(e) => setNewUser({...newUser, invite_message: e.target.value})}
                          placeholder="添加个性化邀请消息..."
                          rows={3}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowInviteUser(false)}>
                        取消
                      </Button>
                      <Button onClick={handleInviteUser}>
                        发送邀请
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>

              <Card>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>用户</TableHead>
                      <TableHead>角色</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>加入时间</TableHead>
                      <TableHead>最后登录</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tenantUsers
                      .filter(user =>
                        searchTerm === '' ||
                        user.user_id.toLowerCase().includes(searchTerm.toLowerCase())
                      )
                      .map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center space-x-3">
                            <Avatar>
                              <AvatarImage src={`/avatars/${user.user_id}.jpg`} />
                              <AvatarFallback>
                                {user.user_id.slice(0, 2).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-medium">{user.user_id}</div>
                              <div className="text-sm text-muted-foreground">
                                {user.permissions.length} 个权限
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {getRoleText(user.role)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={user.is_active ? 'bg-green-500' : 'bg-red-500'}>
                            {user.is_active ? '活跃' : '非活跃'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {new Date(user.joined_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {user.last_login_at
                            ? new Date(user.last_login_at).toLocaleDateString()
                            : '从未登录'
                          }
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>操作</DropdownMenuLabel>
                              <DropdownMenuItem>
                                <Edit className="h-4 w-4 mr-2" />
                                编辑
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-red-600"
                                onClick={() => handleRemoveUser(user.user_id)}
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                移除
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </TabsContent>

            <TabsContent value="teams" className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Input
                    placeholder="搜索团队..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Button variant="outline" size="icon">
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
                <Dialog open={showCreateTeam} onOpenChange={setShowCreateTeam}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="h-4 w-4 mr-2" />
                      创建团队
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>创建新团队</DialogTitle>
                      <DialogDescription>
                        在租户 {currentTenant.name} 中创建新团队
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid gap-2">
                        <Label htmlFor="team_name">团队名称</Label>
                        <Input
                          id="team_name"
                          value={newTeam.name}
                          onChange={(e) => setNewTeam({...newTeam, name: e.target.value})}
                          placeholder="输入团队名称"
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="team_description">团队描述 (可选)</Label>
                        <Textarea
                          id="team_description"
                          value={newTeam.description}
                          onChange={(e) => setNewTeam({...newTeam, description: e.target.value})}
                          placeholder="描述团队的职责和目标..."
                          rows={3}
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="parent_team">父团队 (可选)</Label>
                        <Select value={newTeam.parent_team_id} onValueChange={(value) => setNewTeam({...newTeam, parent_team_id: value})}>
                          <SelectTrigger>
                            <SelectValue placeholder="选择父团队" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="">无父团队</SelectItem>
                            {teams.map((team) => (
                              <SelectItem key={team.id} value={team.id}>
                                {team.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowCreateTeam(false)}>
                        取消
                      </Button>
                      <Button onClick={handleCreateTeam}>
                        创建团队
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {teams
                  .filter(team =>
                    searchTerm === '' ||
                    team.name.toLowerCase().includes(searchTerm.toLowerCase())
                  )
                  .map((team) => (
                  <Card key={team.id}>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        <span>{team.name}</span>
                        <Badge className={team.is_active ? 'bg-green-500' : 'bg-red-500'}>
                          {team.is_active ? '活跃' : '非活跃'}
                        </Badge>
                      </CardTitle>
                      {team.description && (
                        <CardDescription>{team.description}</CardDescription>
                      )}
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">成员数量</span>
                          <span className="font-medium">{team.member_count}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">创建时间</span>
                          <span className="font-medium">
                            {new Date(team.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 mt-4">
                        <Button variant="outline" size="sm" className="flex-1">
                          <Users className="h-4 w-4 mr-2" />
                          管理成员
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="h-4 w-4 mr-2" />
                              编辑
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => handleDeleteTeam(team.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}