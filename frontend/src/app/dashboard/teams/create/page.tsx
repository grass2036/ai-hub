'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface Organization {
  id: string;
  name: string;
  slug: string;
}

interface TeamFormData {
  name: string;
  description: string;
  organization_id: string;
  parent_team_id?: string;
}

export default function CreateTeamPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedOrgId = searchParams.get('organization');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [formData, setFormData] = useState<TeamFormData>({
    name: '',
    description: '',
    organization_id: preselectedOrgId || '',
    parent_team_id: ''
  });

  useEffect(() => {
    fetchOrganizations();
    if (preselectedOrgId) {
      fetchTeams(preselectedOrgId);
    }
  }, []);

  useEffect(() => {
    if (formData.organization_id) {
      fetchTeams(formData.organization_id);
    }
  }, [formData.organization_id]);

  const fetchOrganizations = async () => {
    try {
      const response = await fetch('/api/v1/organizations/');
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error('Error fetching organizations:', error);
    }
  };

  const fetchTeams = async (orgId: string) => {
    try {
      const response = await fetch(`/api/v1/organizations/${orgId}/teams`);
      if (response.ok) {
        const data = await response.json();
        setTeams(data);
      }
    } catch (error) {
      console.error('Error fetching teams:', error);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Team name is required');
      return false;
    }
    if (!formData.organization_id) {
      setError('Organization is required');
      return false;
    }
    if (formData.name.length < 2) {
      setError('Team name must be at least 2 characters');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Prepare request data - only include parent_team_id if it's not empty
      const requestData: any = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        organization_id: formData.organization_id
      };

      if (formData.parent_team_id && formData.parent_team_id !== '') {
        requestData.parent_team_id = formData.parent_team_id;
      }

      const response = await fetch(`/api/v1/organizations/${formData.organization_id}/teams`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create team');
      }

      const newTeam = await response.json();

      // Redirect to the team details page
      router.push(`/dashboard/teams/${newTeam.id}`);
    } catch (error) {
      console.error('Error creating team:', error);
      setError(error instanceof Error ? error.message : 'Failed to create team');
    } finally {
      setLoading(false);
    }
  };

  if (organizations.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No organizations available</h3>
          <p className="mt-1 text-sm text-gray-500">
            You need to create an organization first before you can create teams.
          </p>
          <div className="mt-6">
            <Link
              href="/dashboard/organizations/create"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Create Organization
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center space-x-3">
          <Link
            href="/dashboard/teams"
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Create Team</h1>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          Set up a new team to organize members and manage access
        </p>
      </div>

      <div className="max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">
                    {error}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
            <div className="space-y-6">
              <div>
                <label htmlFor="organization_id" className="block text-sm font-medium text-gray-700">
                  Organization *
                </label>
                <div className="mt-1">
                  <select
                    name="organization_id"
                    id="organization_id"
                    required
                    value={formData.organization_id}
                    onChange={handleInputChange}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  >
                    <option value="">Select an organization</option>
                    {organizations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  The organization this team will belong to
                </p>
              </div>

              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  Team Name *
                </label>
                <div className="mt-1">
                  <input
                    type="text"
                    name="name"
                    id="name"
                    required
                    value={formData.name}
                    onChange={handleInputChange}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Engineering Team"
                  />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  The display name for your team
                </p>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <div className="mt-1">
                  <textarea
                    name="description"
                    id="description"
                    rows={3}
                    value={formData.description}
                    onChange={handleInputChange}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="A brief description of the team's purpose and responsibilities..."
                  />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  Optional description to help identify this team's role
                </p>
              </div>

              {teams.length > 0 && (
                <div>
                  <label htmlFor="parent_team_id" className="block text-sm font-medium text-gray-700">
                    Parent Team (Optional)
                  </label>
                  <div className="mt-1">
                    <select
                      name="parent_team_id"
                      id="parent_team_id"
                      value={formData.parent_team_id}
                      onChange={handleInputChange}
                      className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                      <option value="">No parent team (root team)</option>
                      {teams.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    Select a parent team to create a hierarchical structure
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">Team Structure</h3>
                <div className="mt-2 text-sm text-blue-700">
                  <p>Teams can be organized hierarchically with parent and child relationships.</p>
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    <li>Root teams have no parent and operate at the organization level</li>
                    <li>Child teams inherit permissions from their parent teams</li>
                    <li>You can create multiple levels of team hierarchy</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Team'
              )}
            </button>
            <Link
              href="/dashboard/teams"
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}