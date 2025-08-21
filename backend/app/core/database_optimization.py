"""
Database optimization utilities for EventTicketing platform.
Implements query optimization, connection pooling, and performance monitoring.
"""
import time
import logging
from typing import Any, Dict, List, Optional, Type, Union, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text, Index, inspect
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.sql import Select
from sqlalchemy.engine import Row
from sqlalchemy import event, pool
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.core.caching import cache_manager, cached

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """Query performance tracking data."""
    query_hash: str
    execution_time: float
    rows_returned: int
    cache_hit: bool
    timestamp: datetime
    query_type: str  # SELECT, INSERT, UPDATE, DELETE
    table_names: List[str]


class QueryOptimizer:
    """Database query optimization and monitoring."""
    
    def __init__(self):
        self.query_metrics: List[QueryPerformanceMetrics] = []
        self.slow_query_threshold = 1.0  # seconds
        self.query_cache = {}
        
    def add_metric(self, metric: QueryPerformanceMetrics):
        """Add query performance metric."""
        self.query_metrics.append(metric)
        
        # Keep only last 1000 metrics to prevent memory issues
        if len(self.query_metrics) > 1000:
            self.query_metrics = self.query_metrics[-1000:]
        
        # Log slow queries
        if metric.execution_time > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected: {metric.execution_time:.3f}s, "
                f"Hash: {metric.query_hash}, Tables: {metric.table_names}"
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get query performance summary."""
        if not self.query_metrics:
            return {"message": "No metrics available"}
        
        total_queries = len(self.query_metrics)
        slow_queries = [m for m in self.query_metrics if m.execution_time > self.slow_query_threshold]
        cache_hits = [m for m in self.query_metrics if m.cache_hit]
        
        avg_execution_time = sum(m.execution_time for m in self.query_metrics) / total_queries
        
        return {
            "total_queries": total_queries,
            "slow_queries": len(slow_queries),
            "cache_hit_rate": len(cache_hits) / total_queries * 100,
            "average_execution_time": avg_execution_time,
            "slow_query_threshold": self.slow_query_threshold,
            "slowest_queries": sorted(
                [(m.query_hash, m.execution_time, m.table_names) for m in slow_queries],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }


# Global query optimizer instance
query_optimizer = QueryOptimizer()


class DatabaseConnection:
    """Optimized database connection management."""
    
    @staticmethod
    def configure_engine(engine: AsyncEngine):
        """Configure database engine for optimal performance."""
        
        # Connection pool configuration
        if isinstance(engine.pool, QueuePool):
            engine.pool._pool_timeout = 30
            engine.pool._max_overflow = 20
            engine.pool._pool_size = 10
        
        # Add event listeners for monitoring
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            execution_time = time.time() - context._query_start_time
            
            # Extract query information
            query_hash = str(hash(statement))[:8]
            query_type = statement.strip().split()[0].upper()
            
            # Simple table name extraction (could be improved)
            table_names = []
            for word in statement.split():
                if word.upper() in ['FROM', 'JOIN', 'UPDATE', 'INTO']:
                    continue
                if '.' in word or word.isidentifier():
                    table_names.append(word.replace(',', ''))
            
            metric = QueryPerformanceMetrics(
                query_hash=query_hash,
                execution_time=execution_time,
                rows_returned=cursor.rowcount if cursor.rowcount > 0 else 0,
                cache_hit=False,  # Database level, not cache
                timestamp=datetime.utcnow(),
                query_type=query_type,
                table_names=table_names[:3]  # Limit to first 3 tables
            )
            
            query_optimizer.add_metric(metric)


class OptimizedQueries:
    """Collection of optimized database queries."""
    
    @staticmethod
    @cached(ttl=300, key_prefix="events_with_stats")
    async def get_events_with_stats(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        category_id: Optional[int] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get events with aggregated statistics using optimized query."""
        
        base_query = """
        SELECT 
            e.id,
            e.title,
            e.description,
            e.start_date,
            e.end_date,
            e.location,
            e.image_url,
            e.status,
            e.organization_id,
            o.name as organization_name,
            COUNT(DISTINCT t.id) as ticket_types_count,
            COALESCE(SUM(t.quantity), 0) as total_capacity,
            COALESCE(SUM(t.quantity - t.available_quantity), 0) as tickets_sold,
            COALESCE(MIN(t.price), 0) as min_price,
            COALESCE(MAX(t.price), 0) as max_price,
            COUNT(DISTINCT ord.id) as total_orders,
            COALESCE(SUM(CASE WHEN ord.status = 'completed' THEN ord.total_amount ELSE 0 END), 0) as total_revenue
        FROM events e
        LEFT JOIN organizations o ON e.organization_id = o.id
        LEFT JOIN tickets t ON e.id = t.event_id
        LEFT JOIN orders ord ON e.id = ord.event_id
        WHERE e.status = 'published'
        """
        
        params = {}
        
        if category_id:
            base_query += " AND e.category_id = :category_id"
            params["category_id"] = category_id
        
        if location:
            base_query += " AND e.location ILIKE :location"
            params["location"] = f"%{location}%"
        
        base_query += """
        GROUP BY e.id, o.name
        ORDER BY e.start_date ASC
        LIMIT :limit OFFSET :offset
        """
        
        params.update({"limit": limit, "offset": offset})
        
        result = await db.execute(text(base_query), params)
        return [dict(row._mapping) for row in result]
    
    @staticmethod
    @cached(ttl=600, key_prefix="user_dashboard_data")
    async def get_user_dashboard_data(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user dashboard data in a single optimized query."""
        
        query = """
        WITH user_stats AS (
            SELECT 
                COUNT(DISTINCT o.id) as total_orders,
                COUNT(DISTINCT CASE WHEN o.status = 'completed' THEN o.id END) as completed_orders,
                COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END), 0) as total_spent,
                COUNT(DISTINCT e.id) as events_attended
            FROM orders o
            LEFT JOIN events e ON o.event_id = e.id
            WHERE o.user_id = :user_id
        ),
        recent_orders AS (
            SELECT 
                o.id,
                o.status,
                o.total_amount,
                o.created_at,
                e.title as event_title,
                e.start_date as event_start_date
            FROM orders o
            JOIN events e ON o.event_id = e.id
            WHERE o.user_id = :user_id
            ORDER BY o.created_at DESC
            LIMIT 5
        ),
        upcoming_events AS (
            SELECT 
                e.id,
                e.title,
                e.start_date,
                e.location,
                COUNT(a.id) as ticket_count
            FROM events e
            JOIN orders o ON e.id = o.event_id
            LEFT JOIN attendees a ON o.id = a.order_id
            WHERE o.user_id = :user_id 
                AND o.status = 'completed'
                AND e.start_date > NOW()
            GROUP BY e.id, e.title, e.start_date, e.location
            ORDER BY e.start_date ASC
            LIMIT 5
        )
        SELECT 
            (SELECT row_to_json(user_stats) FROM user_stats) as stats,
            (SELECT json_agg(recent_orders) FROM recent_orders) as recent_orders,
            (SELECT json_agg(upcoming_events) FROM upcoming_events) as upcoming_events
        """
        
        result = await db.execute(text(query), {"user_id": user_id})
        row = result.first()
        
        return {
            "stats": row.stats if row and row.stats else {},
            "recent_orders": row.recent_orders if row and row.recent_orders else [],
            "upcoming_events": row.upcoming_events if row and row.upcoming_events else []
        }
    
    @staticmethod
    @cached(ttl=900, key_prefix="analytics_summary")
    async def get_analytics_summary(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get analytics summary with optimized aggregation query."""
        
        base_query = """
        WITH date_series AS (
            SELECT generate_series(
                :start_date::date,
                :end_date::date,
                '1 day'::interval
            )::date as date
        ),
        daily_stats AS (
            SELECT 
                DATE(o.created_at) as order_date,
                COUNT(DISTINCT o.id) as orders_count,
                COUNT(DISTINCT o.user_id) as unique_customers,
                COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END), 0) as revenue,
                COUNT(DISTINCT e.id) as events_with_orders
            FROM orders o
            JOIN events e ON o.event_id = e.id
            WHERE o.created_at BETWEEN :start_date AND :end_date
        """
        
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        if organization_id:
            base_query += " AND e.organization_id = :organization_id"
            params["organization_id"] = organization_id
        
        base_query += """
            GROUP BY DATE(o.created_at)
        ),
        summary_stats AS (
            SELECT 
                COUNT(DISTINCT o.id) as total_orders,
                COUNT(DISTINCT o.user_id) as total_customers,
                COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END), 0) as total_revenue,
                COUNT(DISTINCT e.id) as total_events,
                AVG(CASE WHEN o.status = 'completed' THEN o.total_amount END) as avg_order_value
            FROM orders o
            JOIN events e ON o.event_id = e.id
            WHERE o.created_at BETWEEN :start_date AND :end_date
        """
        
        if organization_id:
            base_query += " AND e.organization_id = :organization_id"
        
        base_query += """
        )
        SELECT 
            (SELECT row_to_json(summary_stats) FROM summary_stats) as summary,
            (SELECT json_agg(
                json_build_object(
                    'date', ds.date,
                    'orders', COALESCE(daily_stats.orders_count, 0),
                    'revenue', COALESCE(daily_stats.revenue, 0),
                    'customers', COALESCE(daily_stats.unique_customers, 0)
                ) ORDER BY ds.date
            ) FROM date_series ds 
            LEFT JOIN daily_stats ON ds.date = daily_stats.order_date) as daily_data
        """
        
        result = await db.execute(text(base_query), params)
        row = result.first()
        
        return {
            "summary": row.summary if row and row.summary else {},
            "daily_data": row.daily_data if row and row.daily_data else []
        }


class QueryBuilder:
    """Advanced query builder with optimization hints."""
    
    @staticmethod
    def build_optimized_select(
        model_class: Type,
        filters: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Select:
        """Build an optimized SELECT query with proper joins and filtering."""
        
        query = Select(model_class)
        
        # Add relationship loading
        if relationships:
            for rel in relationships:
                if hasattr(model_class, rel):
                    # Use selectinload for to-many relationships, joinedload for to-one
                    rel_attr = getattr(model_class, rel)
                    if hasattr(rel_attr.property, 'direction'):
                        if rel_attr.property.direction.name in ['ONETOMANY', 'MANYTOMANY']:
                            query = query.options(selectinload(rel_attr))
                        else:
                            query = query.options(joinedload(rel_attr))
        
        # Add filters
        if filters:
            for field, value in filters.items():
                if hasattr(model_class, field):
                    attr = getattr(model_class, field)
                    if isinstance(value, list):
                        query = query.where(attr.in_(value))
                    elif isinstance(value, dict):
                        # Handle range queries
                        if 'gte' in value:
                            query = query.where(attr >= value['gte'])
                        if 'lte' in value:
                            query = query.where(attr <= value['lte'])
                        if 'like' in value:
                            query = query.where(attr.ilike(f"%{value['like']}%"))
                    else:
                        query = query.where(attr == value)
        
        # Add ordering
        if order_by:
            if order_by.startswith('-'):
                field = order_by[1:]
                if hasattr(model_class, field):
                    query = query.order_by(getattr(model_class, field).desc())
            else:
                if hasattr(model_class, order_by):
                    query = query.order_by(getattr(model_class, order_by))
        
        # Add pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        return query


class ConnectionPoolMonitor:
    """Monitor database connection pool health."""
    
    @staticmethod
    def get_pool_status(engine: AsyncEngine) -> Dict[str, Any]:
        """Get connection pool status and metrics."""
        pool = engine.pool
        
        if isinstance(pool, QueuePool):
            return {
                "pool_type": "QueuePool",
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "pool_timeout": pool._timeout,
                "max_overflow": pool._max_overflow,
                "total_connections": pool.size() + pool.overflow()
            }
        else:
            return {
                "pool_type": type(pool).__name__,
                "status": "monitoring_not_available"
            }


class IndexManager:
    """Database index management and optimization."""
    
    @staticmethod
    async def analyze_table_indexes(db: AsyncSession, table_name: str) -> Dict[str, Any]:
        """Analyze indexes for a specific table."""
        
        # Get existing indexes
        indexes_query = """
        SELECT 
            indexname,
            indexdef,
            schemaname,
            tablename
        FROM pg_indexes 
        WHERE tablename = :table_name
        """
        
        result = await db.execute(text(indexes_query), {"table_name": table_name})
        indexes = [dict(row._mapping) for row in result]
        
        # Get table statistics
        stats_query = """
        SELECT 
            schemaname,
            tablename,
            attname,
            n_distinct,
            correlation
        FROM pg_stats 
        WHERE tablename = :table_name
        """
        
        stats_result = await db.execute(text(stats_query), {"table_name": table_name})
        stats = [dict(row._mapping) for row in stats_result]
        
        return {
            "table_name": table_name,
            "indexes": indexes,
            "column_statistics": stats,
            "recommendations": IndexManager._generate_index_recommendations(indexes, stats)
        }
    
    @staticmethod
    def _generate_index_recommendations(indexes: List[Dict], stats: List[Dict]) -> List[str]:
        """Generate index recommendations based on analysis."""
        recommendations = []
        
        # Check for missing primary key index
        has_primary_key = any("_pkey" in idx["indexname"] for idx in indexes)
        if not has_primary_key:
            recommendations.append("Consider adding a primary key index")
        
        # Check for foreign key indexes
        foreign_key_columns = [col["attname"] for col in stats if col["attname"].endswith("_id")]
        indexed_columns = []
        for idx in indexes:
            # Simple extraction of indexed columns (could be improved)
            if "(" in idx["indexdef"]:
                cols = idx["indexdef"].split("(")[1].split(")")[0]
                indexed_columns.extend([col.strip() for col in cols.split(",")])
        
        for fk_col in foreign_key_columns:
            if fk_col not in indexed_columns:
                recommendations.append(f"Consider adding index on foreign key column: {fk_col}")
        
        # Check for highly correlated columns
        for stat in stats:
            if stat["correlation"] and abs(float(stat["correlation"])) > 0.8:
                recommendations.append(f"Column {stat['attname']} has high correlation, consider for ordering optimization")
        
        return recommendations


# Performance monitoring context manager
@asynccontextmanager
async def monitor_query_performance(query_name: str):
    """Context manager to monitor individual query performance."""
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        logger.info(f"Query '{query_name}' executed in {execution_time:.3f}s")
        
        if execution_time > query_optimizer.slow_query_threshold:
            logger.warning(f"Slow query detected: '{query_name}' took {execution_time:.3f}s")