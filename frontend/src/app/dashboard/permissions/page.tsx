'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 类型定义
interface Permission {
  id: string;
  name: string;
  display_name: string;
  description: string;
  scope: string;
  action: string;
  resource_type?: string;
  conditions: Record<string, any>;
  metadata: Record<string, any>;
  created_at: string;
}

interface Role {
  id: string;
  name: string;
  display_name: string;
  description: string;
  scope: string;
  level: number;
  parent_role_id?: string;
  is_system_role: boolean;
  is_default: boolean;
  permission_count: number;
  created_at: string;
}

interface UserRole {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  role_id: string;
  role_name: string;
  assigned_at: string;
  expires_at?: string;
  is_active: boolean;
}

interface User {
  id: string;
  email: string;
  full_name?: string;
}

export default function PermissionsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'permissions' | 'roles' | 'assignments' | 'logs'>('permissions');
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [userRoles, setUserRoles] = useState<UserRole[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);

  // 表单状态
  const [showCreatePermission, setShowCreatePermission] = useState(false);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [showAssignRole, setShowAssignRole] = useState(false);

  // 模拟数据
  const mockPermissions: Permission[] = [
    {
      id: '1',
      name: 'user.read',
      display_name: '读取用户信息',
      description: '查看用户基本信息和资料',
      scope: 'organization',
      action: 'read',
      resource_type: 'user',
      conditions: {},
      metadata: {},
      created_at: new Date().toISOString()
    },
    {
      id: '2',
      name: 'api_key.create',
      display_name: '创建API密钥',
      description: '为用户或团队创建新的API访问密钥',
      scope: 'organization',
      action: 'create',
      resource_type: 'api_key',
      conditions: {},
      metadata: {},
      created_at: new Date().toISOString()
    },
    {
      id: '3',
      name: 'billing.read',
      display_name: '查看账单信息',
      description: '查看组织账单和订阅信息',
      scope: 'organization',
      action: 'read',
      resource_type: 'billing',
      conditions: {},
      metadata: {},
      created_at: new Date().toISOString()
    }
  ];

  const mockRoles: Role[] = [
    {
      id: '1',
      name: 'org_admin',
      display_name: '组织管理员',
      description: '拥有组织内所有权限',
      scope: 'organization',
      level: 100,
      is_system_role: false,
      is_default: false,
      permission_count: 15,
      created_at: new Date().toISOString()
    },
    {
      id: '2',
      name: 'developer',
      display_name: '开发者',
      description: '可以创建和管理API密钥，查看使用统计',
      scope: 'organization',
      level: 50,
      is_system_role: false,
      is_default: true,
      permission_count: 8,
      created_at: new Date().toISOString()
    },
    {
      id: '3',
      name: 'viewer',
      display_name: '查看者',
      description: '只能查看信息，无法进行修改操作',
      scope: 'organization',
      level: 10,
      is_system_role: false,
      is_default: false,
      permission_count: 3,
      created_at: new Date().toISOString()
    }
  ];

  const mockUserRoles: UserRole[] = [
    {
      id: '1',
      user_id: 'user1',
      user_email: 'zhang@example.com',
      user_name: '张三',
      role_id: '1',
      role_name: '组织管理员',
      assigned_at: new Date(Date.now() - 86400000).toISOString(),
      is_active: true
    },
    {
      id: '2',
      user_id: 'user2',
      user_email: 'li@example.com',
      user_name: '李四',
      role_id: '2',
      role_name: '开发者',
      assigned_at: new Date(Date.now() - 172800000).toISOString(),
      expires_at: new Date(Date.now() + 30 * 86400000).toISOString(),
      is_active: true
    },
    {
      id: '3',
      user_id: 'user3',
      user_email: 'wang@example.com',
      user_name: '王五',
      role_id: '3',
      role_name: '查看者',
      assigned_at: new Date(Date.now() - 259200000).toISOString(),
      is_active: true
    }
  ];

  const mockUsers: User[] = [
    { id: 'user1', email: 'zhang@example.com', full_name: '张三' },
    { id: 'user2', email: 'li@example.com', full_name: '李四' },
    { id: 'user3', email: 'wang@example.com', full_name: '王五' },
    { id: 'user4', email: 'zhao@example.com', full_name: '赵六' }
  ];

  useEffect(() => {
    if (activeTab === 'permissions') {
      fetchPermissions();
    } else if (activeTab === 'roles') {
      fetchRoles();
    } else if (activeTab === 'assignments') {
      fetchUserRoles();
    }
  }, [activeTab]);

  const fetchPermissions = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setPermissions(mockPermissions);
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setRoles(mockRoles);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserRoles = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setUserRoles(mockUserRoles);
      setUsers(mockUsers);
    } catch (error) {
      console.error('Failed to fetch user roles:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getScopeColor = (scope: string) => {
    switch (scope) {
      case 'system': return 'text-red-600 bg-red-100';
      case 'organization': return 'text-blue-600 bg-blue-100';
      case 'team': return 'text-green-600 bg-green-100';
      case 'user': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create': return 'text-green-600 bg-green-100';
      case 'read': return 'text-blue-600 bg-blue-100';
      case 'update': return 'text-yellow-600 bg-yellow-100';
      case 'delete': return 'text-red-600 bg-red-100';
      case 'admin': return 'text-purple-600 bg-purple-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">权限管理</h1>
        <p className="text-gray-600">管理用户权限、角色和访问控制</p>
      </div>

      {/* 标签页 */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('permissions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'permissions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔐 权限管理
          </button>
          <button
            onClick={() => setActiveTab('roles')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'roles'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            👥 角色管理
          </button>
          <button
            onClick={() => setActiveTab('assignments')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'assignments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📋 角色分配
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'logs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📝 访问日志
          </button>
        </nav>
      </div>

      {/* 操作按钮 */}
      <div className="mb-6 flex justify-end space-x-3">
        {activeTab === 'permissions' && (
          <button
            onClick={() => setShowCreatePermission(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + 创建权限
          </button>
        )}
        {activeTab === 'roles' && (
          <button
            onClick={() => setShowCreateRole(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + 创建角色
          </button>
        )}
        {activeTab === 'assignments' && (
          <button
            onClick={() => setShowAssignRole(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + 分配角色
          </button>
        )}
      </div>

      {/* 内容区域 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {activeTab === 'permissions' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        权限名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        作用域
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        资源类型
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        创建时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {permissions.map((permission) => (
                      <tr key={permission.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {permission.display_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {permission.name}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getScopeColor(permission.scope)}`}>
                            {permission.scope}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionColor(permission.action)}`}>
                            {permission.action}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {permission.resource_type || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(permission.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button className="text-blue-600 hover:text-blue-900 mr-3">
                            编辑
                          </button>
                          <button className="text-red-600 hover:text-red-900">
                            删除
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'roles' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        角色名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        作用域
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        等级
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        权限数量
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        类型
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        创建时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {roles.map((role) => (
                      <tr key={role.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {role.display_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {role.name}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getScopeColor(role.scope)}`}>
                            {role.scope}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className="text-sm text-gray-900">{role.level}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {role.permission_count}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex space-x-2">
                            {role.is_system_role && (
                              <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">
                                系统
                              </span>
                            )}
                            {role.is_default && (
                              <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                默认
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(role.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button className="text-blue-600 hover:text-blue-900 mr-3">
                            编辑
                          </button>
                          <button className="text-red-600 hover:text-red-900">
                            删除
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'assignments' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        用户
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        角色
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        分配时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        过期时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状态
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {userRoles.map((userRole) => (
                      <tr key={userRole.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {userRole.user_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {userRole.user_email}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                            {userRole.role_name}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(userRole.assigned_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {userRole.expires_at ? formatDate(userRole.expires_at) : '永不过期'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            userRole.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {userRole.is_active ? '活跃' : '已停用'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button className="text-blue-600 hover:text-blue-900 mr-3">
                            编辑
                          </button>
                          <button className="text-red-600 hover:text-red-900">
                            移除
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">访问日志</h3>
                <p className="text-gray-600">
                  访问日志功能正在开发中，将显示详细的权限检查记录和访问历史。
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* 创建权限模态框 */}
      {showCreatePermission && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">创建权限</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">权限名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: user.read"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: 读取用户信息"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  rows={3}
                  placeholder="权限描述..."
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowCreatePermission(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={() => setShowCreatePermission(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 创建角色模态框 */}
      {showCreateRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">创建角色</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">角色名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: developer"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: 开发者"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  rows={3}
                  placeholder="角色描述..."
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowCreateRole(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={() => setShowCreateRole(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 分配角色模态框 */}
      {showAssignRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">分配角色</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">选择用户</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="">请选择用户</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name || user.email}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">选择角色</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="">请选择角色</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.display_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowAssignRole(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={() => setShowAssignRole(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                分配
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}