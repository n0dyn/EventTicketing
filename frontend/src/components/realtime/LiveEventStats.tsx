/**
 * Live Event Statistics Component
 * Displays real-time event statistics using WebSocket connection
 */

import React from 'react';
import { useLiveEventStats } from '../../hooks/useWebSocket';

interface LiveEventStatsProps {
  eventId: number;
  className?: string;
}

export function LiveEventStats({ eventId, className = '' }: LiveEventStatsProps) {
  const { stats, isConnected, connectionError } = useLiveEventStats(eventId);

  if (connectionError) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse mr-3"></div>
          <span className="text-red-700 text-sm">Connection Error: {connectionError}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white border rounded-lg shadow-sm ${className}`}>
      {/* Connection Status */}
      <div className="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Live Event Statistics</h3>
        <div className="flex items-center">
          <div 
            className={`w-2 h-2 rounded-full mr-2 ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            }`}
          ></div>
          <span className="text-xs text-gray-500">
            {isConnected ? 'Live' : 'Connecting...'}
          </span>
        </div>
      </div>

      {/* Statistics */}
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {stats.totalCheckedIn || 0}
            </div>
            <div className="text-xs text-gray-500">Checked In</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {stats.liveViewers || 0}
            </div>
            <div className="text-xs text-gray-500">Live Viewers</div>
          </div>
        </div>

        {/* Recent Activity */}
        {stats.recentActivity && stats.recentActivity.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Recent Check-ins</h4>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {stats.recentActivity.slice(0, 5).map((activity: any, index: number) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <span className="text-gray-700 truncate">
                    {activity.attendee_name}
                  </span>
                  <span className="text-gray-500">
                    {new Date(activity.checked_in_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LiveEventStats;