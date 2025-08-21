"""
Comprehensive caching system for EventTicketing platform.
Implements multi-layer caching with Redis and in-memory strategies.
"""
import json
import pickle
import hashlib
from typing import Any, Optional, Union, Dict, List, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import logging

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Advanced cache manager with multiple cache layers and strategies."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "sets": 0,
            "deletes": 0
        }
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key."""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    async def get(self, key: str, use_memory: bool = True) -> Optional[Any]:
        """Get value from cache with fallback strategy."""
        try:
            # Try memory cache first (fastest)
            if use_memory and key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                if cache_entry["expires_at"] > datetime.utcnow():
                    self.cache_stats["hits"] += 1
                    self.cache_stats["memory_hits"] += 1
                    return cache_entry["value"]
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
            
            # Try Redis cache
            if self.redis_client:
                redis_value = await self.redis_client.get(key)
                if redis_value is not None:
                    self.cache_stats["hits"] += 1
                    self.cache_stats["redis_hits"] += 1
                    
                    try:
                        # Try JSON first (faster)
                        value = json.loads(redis_value)
                    except (json.JSONDecodeError, TypeError):
                        # Fallback to pickle
                        value = pickle.loads(redis_value.encode('latin1'))
                    
                    # Store in memory cache for faster future access
                    if use_memory:
                        self.memory_cache[key] = {
                            "value": value,
                            "expires_at": datetime.utcnow() + timedelta(minutes=5)
                        }
                    
                    return value
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats["misses"] += 1
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600,
        use_memory: bool = True,
        serialize_json: bool = True
    ) -> bool:
        """Set value in cache with configurable TTL."""
        try:
            # Store in Redis
            if self.redis_client:
                if serialize_json:
                    try:
                        serialized_value = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        # Fallback to pickle for complex objects
                        serialized_value = pickle.dumps(value).decode('latin1')
                        serialize_json = False
                else:
                    serialized_value = pickle.dumps(value).decode('latin1')
                
                await self.redis_client.setex(key, ttl, serialized_value)
            
            # Store in memory cache with shorter TTL
            if use_memory:
                memory_ttl = min(ttl, 300)  # Max 5 minutes in memory
                self.memory_cache[key] = {
                    "value": value,
                    "expires_at": datetime.utcnow() + timedelta(seconds=memory_ttl)
                }
            
            self.cache_stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache layers."""
        try:
            # Remove from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(key)
            
            self.cache_stats["deletes"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            deleted_count = 0
            
            # Delete from memory cache
            keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.memory_cache[key]
                deleted_count += 1
            
            # Delete from Redis
            if self.redis_client:
                keys = await self.redis_client.keys(f"*{pattern}*")
                if keys:
                    redis_deleted = await self.redis_client.delete(*keys)
                    deleted_count += redis_deleted
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def clear_memory_cache(self):
        """Clear the in-memory cache."""
        self.memory_cache.clear()
        logger.info("Memory cache cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache_stats.copy()
        stats["memory_cache_size"] = len(self.memory_cache)
        
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats["redis_used_memory"] = redis_info.get("used_memory_human", "unknown")
                stats["redis_connected"] = True
            except Exception:
                stats["redis_connected"] = False
        else:
            stats["redis_connected"] = False
        
        # Calculate hit rate
        total_requests = stats["hits"] + stats["misses"]
        stats["hit_rate"] = (stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return stats


# Global cache manager instance
cache_manager = CacheManager()


def cache_key(*args, **kwargs):
    """Decorator to generate cache keys for functions."""
    def decorator(func):
        func._cache_key_generator = lambda *a, **kw: cache_manager._generate_cache_key(
            func.__name__, *args, *a, **kwargs, **kw
        )
        return func
    return decorator


def cached(
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    use_memory: bool = True,
    serialize_json: bool = True,
    skip_if: Optional[Callable] = None
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip caching if condition is met
            if skip_if and skip_if(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache_manager._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, use_memory)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(
                cache_key, 
                result, 
                ttl=ttl, 
                use_memory=use_memory,
                serialize_json=serialize_json
            )
            
            return result
        
        # Add cache management methods to the function
        wrapper.cache_clear = lambda *args, **kwargs: cache_manager.delete(
            cache_manager._generate_cache_key(key_prefix or func.__name__, *args, **kwargs)
        )
        wrapper.cache_clear_pattern = lambda pattern: cache_manager.delete_pattern(pattern)
        
        return wrapper
    return decorator


class DatabaseQueryCache:
    """Specialized caching for database queries."""
    
    @staticmethod
    @cached(ttl=300, key_prefix="db_query")  # 5 minutes default
    async def execute_cached_query(
        db: AsyncSession,
        query: str,
        params: Optional[Dict] = None
    ) -> List[Dict]:
        """Execute and cache database query results."""
        try:
            result = await db.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Database query cache error: {e}")
            raise
    
    @staticmethod
    @cached(ttl=900, key_prefix="db_count")  # 15 minutes for counts
    async def get_cached_count(
        db: AsyncSession,
        table_name: str,
        where_clause: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> int:
        """Get cached count for a table."""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        result = await DatabaseQueryCache.execute_cached_query(db, query, params)
        return result[0]["count"] if result else 0


class RequestCache:
    """Request-level caching for API responses."""
    
    @staticmethod
    def get_request_cache_key(request: Request, additional_params: Optional[Dict] = None) -> str:
        """Generate cache key from request parameters."""
        key_parts = [
            request.method,
            str(request.url.path),
            str(sorted(request.query_params.items()))
        ]
        
        if additional_params:
            key_parts.append(str(sorted(additional_params.items())))
        
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    @staticmethod
    async def get_cached_response(request: Request, additional_params: Optional[Dict] = None):
        """Get cached API response."""
        cache_key = f"api_response:{RequestCache.get_request_cache_key(request, additional_params)}"
        return await cache_manager.get(cache_key)
    
    @staticmethod
    async def set_cached_response(
        request: Request, 
        response_data: Any, 
        ttl: int = 300,
        additional_params: Optional[Dict] = None
    ):
        """Cache API response."""
        cache_key = f"api_response:{RequestCache.get_request_cache_key(request, additional_params)}"
        await cache_manager.set(cache_key, response_data, ttl=ttl)


# Cache invalidation helpers
class CacheInvalidator:
    """Manages cache invalidation patterns."""
    
    @staticmethod
    async def invalidate_event_cache(event_id: int):
        """Invalidate all event-related cache entries."""
        patterns = [
            f"event:{event_id}",
            f"event_tickets:{event_id}",
            f"event_analytics:{event_id}",
            "events_list",
            "public_events"
        ]
        
        for pattern in patterns:
            await cache_manager.delete_pattern(pattern)
    
    @staticmethod
    async def invalidate_user_cache(user_id: int):
        """Invalidate all user-related cache entries."""
        patterns = [
            f"user:{user_id}",
            f"user_orders:{user_id}",
            f"user_tickets:{user_id}",
            f"user_analytics:{user_id}"
        ]
        
        for pattern in patterns:
            await cache_manager.delete_pattern(pattern)
    
    @staticmethod
    async def invalidate_order_cache(order_id: int):
        """Invalidate all order-related cache entries."""
        patterns = [
            f"order:{order_id}",
            f"order_items:{order_id}",
            "revenue_analytics",
            "sales_stats"
        ]
        
        for pattern in patterns:
            await cache_manager.delete_pattern(pattern)


# Performance monitoring
class CachePerformanceMonitor:
    """Monitors cache performance and provides insights."""
    
    @staticmethod
    async def get_performance_report() -> Dict[str, Any]:
        """Generate comprehensive cache performance report."""
        stats = await cache_manager.get_stats()
        
        # Calculate performance metrics
        performance_report = {
            "cache_efficiency": {
                "hit_rate": stats["hit_rate"],
                "memory_hit_percentage": (stats["memory_hits"] / max(stats["hits"], 1)) * 100,
                "redis_hit_percentage": (stats["redis_hits"] / max(stats["hits"], 1)) * 100,
            },
            "cache_usage": {
                "total_requests": stats["hits"] + stats["misses"],
                "cache_hits": stats["hits"],
                "cache_misses": stats["misses"],
                "cache_sets": stats["sets"],
                "cache_deletes": stats["deletes"],
            },
            "memory_cache": {
                "size": stats["memory_cache_size"],
                "estimated_memory_kb": len(cache_manager.memory_cache) * 1024,  # Rough estimate
            },
            "redis_status": {
                "connected": stats["redis_connected"],
                "used_memory": stats.get("redis_used_memory", "unknown"),
            },
            "recommendations": CachePerformanceMonitor._generate_recommendations(stats)
        }
        
        return performance_report
    
    @staticmethod
    def _generate_recommendations(stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on stats."""
        recommendations = []
        
        hit_rate = stats.get("hit_rate", 0)
        if hit_rate < 50:
            recommendations.append("Low cache hit rate. Consider increasing TTL values or caching more data.")
        elif hit_rate > 90:
            recommendations.append("Excellent cache hit rate. Monitor for potential over-caching.")
        
        memory_cache_size = stats.get("memory_cache_size", 0)
        if memory_cache_size > 10000:
            recommendations.append("Large memory cache. Consider reducing memory cache TTL.")
        elif memory_cache_size < 100:
            recommendations.append("Small memory cache. Consider increasing memory cache usage.")
        
        if not stats.get("redis_connected", False):
            recommendations.append("Redis not connected. Cache performance is degraded.")
        
        return recommendations