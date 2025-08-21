/**
 * Admin Dashboard Main Page
 * Main landing page for system administrators
 */

'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Users, Calendar, CreditCard, Building2, TrendingUp, Activity } from 'lucide-react';

interface DashboardStats {
  overview: {
    total_users: number;
    total_events: number;
    total_orders: number;
    total_organizations: number;
    total_revenue: number;
    active_events: number;
  };
  recent_activity: {
    new_users_30d: number;
    new_events_30d: number;
    new_orders_30d: number;
    revenue_30d: number;
  };
  top_events: Array<{
    title: string;
    orders: number;
  }>;
}

export default function AdminDashboardPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    if (isLoading) return;
    if (!user || !user.is_superuser) {
      router.replace('/dashboard');
    }
  }, [isLoading, user]);

  useEffect(() => {
    const fetchStats = async () => {
      if (!user?.is_superuser) return;
      
      try {
        const token = document.cookie
          .split('; ')
          .find(row => row.startsWith('auth_token='))
          ?.split('=')[1];

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/dashboard/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        setStatsLoading(false);
      }
    };

    fetchStats();
  }, [user]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (!user || !user.is_superuser) {
    return null;
  }

  return (
    <div className="py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-bold text-gray-900">
              Admin Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Welcome back, {user.first_name} {user.last_name}
            </p>
          </div>
          <div className="mt-4 flex md:ml-4 md:mt-0">
            <button
                type="button"
                className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                onClick={() => router.push('/admin/performance')}
              >
                <Activity className="mr-2 h-4 w-4" />
                Performance
              </button>
            </div>
        </div>

        {/* Stats Grid */}
        {statsLoading ? (
            <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                      <div className="h-8 bg-gray-200 rounded w-1/3"></div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : stats ? (
            <>
              <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {/* Total Users */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Users className="h-8 w-8 text-blue-600" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            Total Users
                          </dt>
                          <dd className="text-lg font-medium text-gray-900">
                            {stats.overview.total_users.toLocaleString()}
                          </dd>
                        </dl>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="text-sm text-gray-500">
                        +{stats.recent_activity.new_users_30d} new this month
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Total Events */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Calendar className="h-8 w-8 text-green-600" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            Total Events
                          </dt>
                          <dd className="text-lg font-medium text-gray-900">
                            {stats.overview.total_events.toLocaleString()}
                          </dd>
                        </dl>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="text-sm text-gray-500">
                        {stats.overview.active_events} active events
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Total Revenue */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <CreditCard className="h-8 w-8 text-purple-600" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            Total Revenue
                          </dt>
                          <dd className="text-lg font-medium text-gray-900">
                            {'$' + stats.overview.total_revenue.toLocaleString()}
                          </dd>
                        </dl>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="text-sm text-gray-500">
                        {`$${stats.recent_activity.revenue_30d.toLocaleString()} this month`}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Total Orders */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <TrendingUp className="h-8 w-8 text-orange-600" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            Total Orders
                          </dt>
                          <dd className="text-lg font-medium text-gray-900">
                            {stats.overview.total_orders.toLocaleString()}
                          </dd>
                        </dl>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="text-sm text-gray-500">
                        +{stats.recent_activity.new_orders_30d} new this month
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Organizations */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Building2 className="h-8 w-8 text-indigo-600" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            Organizations
                          </dt>
                          <dd className="text-lg font-medium text-gray-900">
                            {stats.overview.total_organizations.toLocaleString()}
                          </dd>
                        </dl>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* System Health */}
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Activity className="h-8 w-8 text-green-500" />
                      </div>
                      <div className="ml-5 w-0 flex-1">
                        <dl>
                          <dt className="text-sm font-medium text-gray-500 truncate">
                            System Status
                          </dt>
                          <dd className="text-lg font-medium text-green-600">
                            Healthy
                          </dd>
                        </dl>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Top Events */}
              {stats.top_events.length > 0 && (
                <div className="mt-8">
                  <Card>
                    <CardContent className="p-6">
                      <h3 className="text-lg font-medium text-gray-900 mb-4">
                        Top Events by Orders
                      </h3>
                      <div className="space-y-3">
                        {stats.top_events.map((event, index) => (
                          <div key={index} className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-900">
                              {event.title}
                            </span>
                            <span className="text-sm text-gray-500">
                              {event.orders} orders
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </>
          ) : (
            <div className="mt-6">
              <Card>
                <CardContent className="p-6 text-center">
                  <p className="text-gray-500">Failed to load dashboard statistics</p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
);
}
