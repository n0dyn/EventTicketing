/**
 * Performance Dashboard Component
 * Real-time performance monitoring and metrics display
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  performanceOptimization, 
  PerformanceMetric, 
  WebVitalsMetric 
} from '@/lib/performance';
import { 
  Activity, 
  Zap, 
  Database, 
  Image, 
  Wifi, 
  RefreshCw,
  TrendingUp,
  AlertCircle
} from 'lucide-react';

interface PerformanceStats {
  metrics: PerformanceMetric[];
  webVitals: { [key: string]: WebVitalsMetric };
  resourceTimings: any[];
  bundleAnalysis: any;
  memoryUsage: any;
}

export default function PerformanceDashboard() {
  const [stats, setStats] = useState<PerformanceStats>({
    metrics: [],
    webVitals: {},
    resourceTimings: [],
    bundleAnalysis: null,
    memoryUsage: null
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshStats = async () => {
    setIsRefreshing(true);
    
    try {
      const metrics = performanceOptimization.monitor.getMetrics();
      const resourceTimings = performanceOptimization.monitor.getResourceTimings();
      const bundleAnalysis = await performanceOptimization.bundle.analyzeBundlePerformance();
      const memoryUsage = performanceOptimization.memory.getMemoryUsage();

      setStats({
        metrics,
        webVitals: stats.webVitals, // Keep existing web vitals
        resourceTimings,
        bundleAnalysis,
        memoryUsage
      });
    } catch (error) {
      console.error('Failed to refresh performance stats:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    // Set up web vitals callback
    const handleWebVitals = (metric: WebVitalsMetric) => {
      setStats(prev => ({
        ...prev,
        webVitals: {
          ...prev.webVitals,
          [metric.name]: metric
        }
      }));
    };

    performanceOptimization.monitor.setWebVitalsCallback(handleWebVitals);
    
    // Initial load
    refreshStats();

    // Auto-refresh every 30 seconds
    const interval = setInterval(refreshStats, 30000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  const getWebVitalsBadge = (metric: WebVitalsMetric) => {
    const variants = {
      good: 'default',
      'needs-improvement': 'secondary',
      poor: 'destructive'
    } as const;

    return (
      <Badge variant={variants[metric.rating]}>
        {metric.value.toFixed(0)}ms ({metric.rating})
      </Badge>
    );
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getMetricAverage = (name: string) => {
    const filteredMetrics = stats.metrics.filter(m => m.name === name);
    if (filteredMetrics.length === 0) return 0;
    return filteredMetrics.reduce((sum, m) => sum + m.value, 0) / filteredMetrics.length;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Performance Dashboard</h1>
          <p className="text-gray-600">Real-time application performance monitoring</p>
        </div>
        <Button onClick={refreshStats} disabled={isRefreshing} variant="outline">
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Tabs defaultValue="vitals" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="vitals">Web Vitals</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="bundles">Bundles</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="network">Network</TabsTrigger>
        </TabsList>

        <TabsContent value="vitals" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(stats.webVitals).map(([name, metric]) => (
              <Card key={name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <Activity className="w-4 h-4 mr-2" />
                    {name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {getWebVitalsBadge(metric)}
                  <p className="text-xs text-gray-500 mt-2">
                    Delta: {metric.delta.toFixed(0)}ms
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          {Object.keys(stats.webVitals).length === 0 && (
            <Card>
              <CardContent className="text-center py-8">
                <AlertCircle className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-gray-500">No Web Vitals data available yet</p>
                <p className="text-xs text-gray-400">Navigate through the app to collect metrics</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <Zap className="w-4 h-4 mr-2" />
                  Page Load Time
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {getMetricAverage('navigation').toFixed(0)}ms
                </div>
                <p className="text-xs text-gray-500">Average navigation timing</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  First Contentful Paint
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {getMetricAverage('first-contentful-paint').toFixed(0)}ms
                </div>
                <p className="text-xs text-gray-500">Time to first content</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <Activity className="w-4 h-4 mr-2" />
                  Total Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.metrics.length}</div>
                <p className="text-xs text-gray-500">Performance data points</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="bundles" className="space-y-4">
          {stats.bundleAnalysis ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <Database className="w-4 h-4 mr-2" />
                    Total Bundle Size
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatBytes(stats.bundleAnalysis.totalSize)}
                  </div>
                  <p className="text-xs text-gray-500">Combined size of all bundles</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Recommendations</CardTitle>
                </CardHeader>
                <CardContent>
                  {stats.bundleAnalysis.recommendations.length > 0 ? (
                    <ul className="space-y-1">
                      {stats.bundleAnalysis.recommendations.map((rec: string, idx: number) => (
                        <li key={idx} className="text-xs text-gray-600 flex items-start">
                          <AlertCircle className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-green-600 flex items-center">
                      <Activity className="w-3 h-3 mr-1" />
                      Bundle size looks good!
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <AlertCircle className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-gray-500">Bundle analysis not available</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="memory" className="space-y-4">
          {stats.memoryUsage ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Used Memory</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Math.round(stats.memoryUsage.usedJSHeapSize / 1024 / 1024)}MB
                  </div>
                  <Progress 
                    value={(stats.memoryUsage.usedJSHeapSize / stats.memoryUsage.jsHeapSizeLimit) * 100}
                    className="mt-2"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Memory</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Math.round(stats.memoryUsage.totalJSHeapSize / 1024 / 1024)}MB
                  </div>
                  <p className="text-xs text-gray-500">Total allocated</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Memory Limit</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Math.round(stats.memoryUsage.jsHeapSizeLimit / 1024 / 1024)}MB
                  </div>
                  <p className="text-xs text-gray-500">Maximum available</p>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <AlertCircle className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-gray-500">Memory information not available</p>
                <p className="text-xs text-gray-400">Feature not supported in this browser</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="network" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center">
                <Wifi className="w-4 h-4 mr-2" />
                Resource Loading Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              {stats.resourceTimings.length > 0 ? (
                <div className="space-y-2">
                  {stats.resourceTimings.slice(0, 10).map((resource, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="truncate flex-1 mr-2">
                        {resource.name.split('/').pop() || 'Unknown'}
                      </span>
                      <div className="flex items-center space-x-2">
                        <span>{resource.duration.toFixed(0)}ms</span>
                        <span className="text-gray-500">
                          {formatBytes(resource.transferSize)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">
                  No resource timing data available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}