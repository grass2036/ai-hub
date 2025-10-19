'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface BatchJob {
  job_id: string;
  name: string;
  task_type: string;
  status: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface BatchStatistics {
  status_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  total_jobs: number;
  recent_jobs: Array<{
    job_id: string;
    name: string;
    task_type: string;
    status: string;
    created_at: string;
  }>;
}

interface TaskDetail {
  task_id: string;
  task_type: string;
  status: string;
  progress: number;
  total_items: number;
  processed_items: number;
  failed_items: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export default function DeveloperBatch() {
  const router = useRouter();
  const [batchJobs, setBatchJobs] = useState<BatchJob[]>([]);
  const [statistics, setStatistics] = useState<BatchStatistics | null>(null);
  const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null);
  const [jobTasks, setJobTasks] = useState<TaskDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'jobs' | 'create' | 'statistics'>('jobs');
  const [currentPage, setCurrentPage] = useState(1);

  // 表单状态
  const [createFormData, setCreateFormData] = useState({
    name: '',
    taskType: 'batch_generation',
    model: 'gpt-4o-mini',
    prompts: [''],
    analysisType: 'sentiment',
    texts: [''],
    maxConcurrentTasks: 5,
    priority: 5
  });

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('developer_access_token');

      if (!token) {
        router.push('/developer/login');
        return;
      }

      try {
        // 并行获取数据
        const [jobsRes, statsRes] = await Promise.all([
          fetch(`/api/v1/developer/batch/jobs?page=${currentPage}&limit=20`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/batch/statistics', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (jobsRes.ok) {
          const jobsResult = await jobsRes.json();
          setBatchJobs(jobsResult.data.batch_jobs);
        }

        if (statsRes.ok) {
          const statsResult = await statsRes.json();
          setStatistics(statsResult.data);
        }

      } catch (err) {
        setError('加载数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router, currentPage]);

  const handleCreateBatchJob = async (type: string) => {
    const token = localStorage.getItem('developer_access_token');
    if (!token) return;

    try {
      let endpoint, requestData;

      if (type === 'generation') {
        endpoint = '/api/v1/developer/batch/generation';
        requestData = {
          name: createFormData.name || `批量生成任务 - ${new Date().toLocaleString()}`,
          model: createFormData.model,
          prompts: createFormData.prompts.filter(p => p.trim()),
          parameters: {},
          max_concurrent_tasks: createFormData.maxConcurrentTasks,
          priority: createFormData.priority
        };
      } else if (type === 'analysis') {
        endpoint = '/api/v1/developer/batch/analysis';
        requestData = {
          name: createFormData.name || `批量分析任务 - ${new Date().toLocaleString()}`,
          analysis_type: createFormData.analysisType,
          texts: createFormData.texts.filter(t => t.trim()),
          max_concurrent_tasks: createFormData.maxConcurrentTasks
        };
      } else {
        return;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      if (response.ok) {
        const result = await response.json();
        alert(`批量任务创建成功！任务ID: ${result.data.job_id}`);
        setActiveTab('jobs');
        // 刷新任务列表
        window.location.reload();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '创建批量任务失败');
      }

    } catch (err) {
      setError('创建批量任务失败');
    }
  };

  const handleCancelJob = async (jobId: string) => {
    const token = localStorage.getItem('developer_access_token');
    if (!token) return;

    try {
      const response = await fetch(`/api/v1/developer/batch/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        alert('任务已取消');
        window.location.reload();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '取消任务失败');
      }

    } catch (err) {
      setError('取消任务失败');
    }
  };

  const handleViewJobDetail = async (job: BatchJob) => {
    setSelectedJob(job);
    const token = localStorage.getItem('developer_access_token');
    if (!token) return;

    try {
      const response = await fetch(`/api/v1/developer/batch/jobs/${job.job_id}/tasks`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const result = await response.json();
        setJobTasks(result.data.tasks);
      }

    } catch (err) {
      setError('获取任务详情失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'running':
        return '运行中';
      case 'pending':
        return '等待中';
      case 'failed':
        return '失败';
      case 'cancelled':
        return '已取消';
      default:
        return status;
    }
  };

  const addPrompt = () => {
    setCreateFormData(prev => ({
      ...prev,
      prompts: [...prev.prompts, '']
    }));
  };

  const removePrompt = (index: number) => {
    setCreateFormData(prev => ({
      ...prev,
      prompts: prev.prompts.filter((_, i) => i !== index)
    }));
  };

  const updatePrompt = (index: number, value: string) => {
    setCreateFormData(prev => ({
      ...prev,
      prompts: prev.prompts.map((p, i) => i === index ? value : p)
    }));
  };

  const addText = () => {
    setCreateFormData(prev => ({
      ...prev,
      texts: [...prev.texts, '']
    }));
  };

  const removeText = (index: number) => {
    setCreateFormData(prev => ({
      ...prev,
      texts: prev.texts.filter((_, i) => i !== index)
    }));
  };

  const updateText = (index: number, value: string) => {
    setCreateFormData(prev => ({
      ...prev,
      texts: prev.texts.map((t, i) => i === index ? value : t)
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/developer" className="text-blue-600 hover:text-blue-800">
                ← 返回控制台
              </Link>
              <h1 className="ml-4 text-xl font-bold text-gray-900">
                批量处理
              </h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* 统计概览 */}
        {statistics && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">总任务数</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {statistics.total_jobs}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">已完成</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {statistics.status_distribution.completed || 0}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">运行中</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {statistics.status_distribution.running || 0}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">失败</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {statistics.status_distribution.failed || 0}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 标签页导航 */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'jobs', label: '批量任务', icon: '📋' },
                { id: 'create', label: '创建任务', icon: '➕' },
                { id: 'statistics', label: '统计分析', icon: '📊' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 批量任务列表 */}
        {activeTab === 'jobs' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                批量任务列表
              </h3>
              {batchJobs.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          任务名称
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          类型
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          状态
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          进度
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
                      {batchJobs.map((job) => (
                        <tr key={job.job_id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {job.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {job.task_type === 'batch_generation' ? '批量生成' :
                             job.task_type === 'batch_analysis' ? '批量分析' :
                             job.task_type === 'data_export' ? '数据导出' : job.task_type}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}>
                              {getStatusText(job.status)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            <div className="flex items-center">
                              <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                                <div
                                  className="bg-blue-500 h-2 rounded-full"
                                  style={{ width: `${job.total_tasks > 0 ? (job.completed_tasks / job.total_tasks) * 100 : 0}%` }}
                                ></div>
                              </div>
                              <span className="text-xs">
                                {job.completed_tasks}/{job.total_tasks}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(job.created_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button
                              onClick={() => handleViewJobDetail(job)}
                              className="text-blue-600 hover:text-blue-900 mr-3"
                            >
                              详情
                            </button>
                            {job.status === 'running' && (
                              <button
                                onClick={() => handleCancelJob(job.job_id)}
                                className="text-red-600 hover:text-red-900"
                              >
                                取消
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">暂无批量任务</p>
              )}

              {/* 分页 */}
              <div className="mt-4 flex justify-center">
                <div className="flex space-x-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
                  >
                    上一页
                  </button>
                  <span className="px-3 py-1 text-gray-700">
                    第 {currentPage} 页
                  </span>
                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    下一页
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 创建任务 */}
        {activeTab === 'create' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                创建批量任务
              </h3>

              {/* 任务类型选择 */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  任务类型
                </label>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <button
                    onClick={() => setCreateFormData(prev => ({ ...prev, taskType: 'batch_generation' }))}
                    className={`p-4 border rounded-lg text-left ${
                      createFormData.taskType === 'batch_generation'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="text-lg font-medium">📝 批量文本生成</div>
                    <div className="text-sm text-gray-600">批量生成多个提示词的回复</div>
                  </button>
                  <button
                    onClick={() => setCreateFormData(prev => ({ ...prev, taskType: 'batch_analysis' }))}
                    className={`p-4 border rounded-lg text-left ${
                      createFormData.taskType === 'batch_analysis'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="text-lg font-medium">🔍 批量分析</div>
                    <div className="text-sm text-gray-600">批量分析文本的情感、关键词等</div>
                  </button>
                </div>
              </div>

              {/* 任务名称 */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  任务名称
                </label>
                <input
                  type="text"
                  value={createFormData.name}
                  onChange={(e) => setCreateFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="输入任务名称"
                />
              </div>

              {/* 批量生成配置 */}
              {createFormData.taskType === 'batch_generation' && (
                <>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      AI模型
                    </label>
                    <select
                      value={createFormData.model}
                      onChange={(e) => setCreateFormData(prev => ({ ...prev, model: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4o-mini">GPT-4o Mini</option>
                      <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                      <option value="grok-4-fast:free">Grok 4 Fast (Free)</option>
                      <option value="deepseek-chat-v3.1:free">DeepSeek Chat (Free)</option>
                    </select>
                  </div>

                  <div className="mb-6">
                    <div className="flex justify-between items-center mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        提示词列表
                      </label>
                      <button
                        onClick={addPrompt}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        + 添加提示词
                      </button>
                    </div>
                    {createFormData.prompts.map((prompt, index) => (
                      <div key={index} className="mb-2">
                        <div className="flex">
                          <textarea
                            value={prompt}
                            onChange={(e) => updatePrompt(index, e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={2}
                            placeholder={`输入提示词 ${index + 1}`}
                          />
                          {createFormData.prompts.length > 1 && (
                            <button
                              onClick={() => removePrompt(index)}
                              className="ml-2 text-red-600 hover:text-red-800"
                            >
                              删除
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* 批量分析配置 */}
              {createFormData.taskType === 'batch_analysis' && (
                <>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      分析类型
                    </label>
                    <select
                      value={createFormData.analysisType}
                      onChange={(e) => setCreateFormData(prev => ({ ...prev, analysisType: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="sentiment">情感分析</option>
                      <option value="keywords">关键词提取</option>
                      <option value="classification">文本分类</option>
                    </select>
                  </div>

                  <div className="mb-6">
                    <div className="flex justify-between items-center mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        文本列表
                      </label>
                      <button
                        onClick={addText}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        + 添加文本
                      </button>
                    </div>
                    {createFormData.texts.map((text, index) => (
                      <div key={index} className="mb-2">
                        <div className="flex">
                          <textarea
                            value={text}
                            onChange={(e) => updateText(index, e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={2}
                            placeholder={`输入文本 ${index + 1}`}
                          />
                          {createFormData.texts.length > 1 && (
                            <button
                              onClick={() => removeText(index)}
                              className="ml-2 text-red-600 hover:text-red-800"
                            >
                              删除
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* 高级配置 */}
              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-700 mb-4">高级配置</h4>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      最大并发任务数
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={createFormData.maxConcurrentTasks}
                      onChange={(e) => setCreateFormData(prev => ({ ...prev, maxConcurrentTasks: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      任务优先级 (1-10)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={createFormData.priority}
                      onChange={(e) => setCreateFormData(prev => ({ ...prev, priority: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              {/* 提交按钮 */}
              <div className="flex justify-end">
                <button
                  onClick={() => handleCreateBatchJob(createFormData.taskType)}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                >
                  创建批量任务
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 统计分析 */}
        {activeTab === 'statistics' && statistics && (
          <div className="space-y-6">
            {/* 任务类型分布 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  任务类型分布
                </h3>
                <div className="space-y-4">
                  {Object.entries(statistics.type_distribution).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">
                        {type === 'batch_generation' ? '批量生成' :
                         type === 'batch_analysis' ? '批量分析' :
                         type === 'data_export' ? '数据导出' : type}
                      </span>
                      <div className="flex items-center">
                        <div className="w-32 bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${(count / statistics.total_jobs) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-600">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 最近任务 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  最近任务
                </h3>
                {statistics.recent_jobs.length > 0 ? (
                  <div className="space-y-4">
                    {statistics.recent_jobs.map((job) => (
                      <div key={job.job_id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                          <div className="font-medium text-gray-900">{job.name}</div>
                          <div className="text-sm text-gray-600">
                            {job.created_at} • {job.task_type}
                          </div>
                        </div>
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}>
                          {getStatusText(job.status)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无最近任务</p>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 任务详情模态框 */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <h3 className="text-xl font-bold text-gray-900">
                  任务详情 - {selectedJob.name}
                </h3>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-6">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">任务ID</p>
                    <p className="font-medium">{selectedJob.job_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">状态</p>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedJob.status)}`}>
                      {getStatusText(selectedJob.status)}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">总任务数</p>
                    <p className="font-medium">{selectedJob.total_tasks}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">已完成</p>
                    <p className="font-medium">{selectedJob.completed_tasks}</p>
                  </div>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="text-lg font-medium text-gray-900 mb-4">子任务列表</h4>
                {jobTasks.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            任务ID
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            状态
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            进度
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            创建时间
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {jobTasks.map((task) => (
                          <tr key={task.task_id}>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {task.task_id.substring(0, 8)}...
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(task.status)}`}>
                                {getStatusText(task.status)}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {task.progress.toFixed(1)}%
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {new Date(task.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无子任务</p>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}