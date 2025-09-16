"""
Performance monitoring and health check endpoints.
Provides database performance metrics, query optimization insights, and system health status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, get_database_info, monitor_connection_pool
from app.utils.query_optimizer import query_optimizer
from app.utils.dependencies import get_current_user
from app.models.user import User, UserRole
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Health status information
    """
    try:
        # Test database connectivity
        from app.database import test_database_connection
        db_healthy = await test_database_connection()
        
        # Get basic system info
        db_info = await get_database_info()
        
        status_code = "healthy" if db_healthy else "unhealthy"
        
        return {
            "status": status_code,
            "database": {
                "connected": db_healthy,
                "version": db_info.get("database_version", "unknown")
            },
            "api": {
                "status": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


@router.get("/database", response_model=Dict[str, Any])
async def get_database_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive database performance metrics.
    Requires admin access.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Database performance metrics
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get database info and connection pool status
        db_info = await get_database_info()
        pool_status = await monitor_connection_pool()
        
        # Get index usage statistics
        index_stats = await query_optimizer.verify_index_usage(db)
        unused_indexes = await query_optimizer.get_unused_indexes(db)
        
        # Get table statistics
        table_stats = await query_optimizer.analyze_table_statistics(db)
        
        return {
            "database_info": db_info,
            "connection_pool": pool_status,
            "index_usage": {
                "total_indexes": len(index_stats),
                "unused_indexes": unused_indexes,
                "top_used_indexes": sorted(
                    [
                        {
                            "table": stat.table_name,
                            "index": stat.index_name,
                            "scans": stat.scans,
                            "tuples_read": stat.tuples_read
                        }
                        for stat in index_stats
                    ],
                    key=lambda x: x["scans"],
                    reverse=True
                )[:10]
            },
            "table_statistics": table_stats
        }
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database metrics"
        )


@router.get("/query-performance", response_model=Dict[str, Any])
async def get_query_performance_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get query performance metrics and analysis.
    Requires admin access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Query performance metrics
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get performance summary
        performance_summary = query_optimizer.get_query_performance_summary()
        
        # Get slow queries
        slow_queries = query_optimizer.get_slow_queries(limit=10)
        
        # Format slow queries for response
        formatted_slow_queries = [
            {
                "query_hash": query.query_hash,
                "query_text": query.query_text,
                "execution_time": query.execution_time,
                "rows_examined": query.rows_examined,
                "rows_returned": query.rows_returned,
                "timestamp": query.timestamp.isoformat(),
                "endpoint": query.endpoint
            }
            for query in slow_queries
        ]
        
        return {
            "performance_summary": performance_summary,
            "slow_queries": formatted_slow_queries,
            "optimization_recommendations": _get_optimization_recommendations(
                performance_summary, slow_queries
            )
        }
    except Exception as e:
        logger.error(f"Failed to get query performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query performance metrics"
        )


@router.get("/performance-summary", response_model=Dict[str, Any])
async def get_performance_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get overall system performance summary.
    Requires admin access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System performance summary
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get middleware performance metrics
        from app.main import app
        performance_middleware = None
        
        # Find performance middleware
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and 'PerformanceMonitoringMiddleware' in str(middleware.cls):
                performance_middleware = middleware.cls
                break
        
        middleware_summary = {}
        if performance_middleware and hasattr(performance_middleware, 'get_performance_summary'):
            middleware_summary = performance_middleware.get_performance_summary()
        
        # Get query performance
        query_summary = query_optimizer.get_query_performance_summary()
        
        # Get database metrics
        db_info = await get_database_info()
        pool_status = await monitor_connection_pool()
        
        return {
            "system_health": {
                "database_status": "healthy" if "error" not in db_info else "unhealthy",
                "connection_pool_status": pool_status.get("status", "unknown"),
                "query_performance_status": _get_query_performance_status(query_summary)
            },
            "performance_metrics": {
                "middleware": middleware_summary,
                "queries": query_summary,
                "database": {
                    "pool_utilization": db_info.get("pool_utilization", 0),
                    "cache_hit_ratio": db_info.get("performance_stats", {}).get("cache_hit_ratio", 0)
                }
            },
            "recommendations": _get_system_recommendations(
                query_summary, pool_status, db_info
            )
        }
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance summary"
        )


def _get_optimization_recommendations(
    performance_summary: Dict[str, Any],
    slow_queries: List[Any]
) -> List[str]:
    """
    Generate query optimization recommendations.
    
    Args:
        performance_summary: Query performance summary
        slow_queries: List of slow queries
        
    Returns:
        List of optimization recommendations
    """
    recommendations = []
    
    # Check slow query percentage
    slow_query_percentage = performance_summary.get("slow_query_percentage", 0)
    if slow_query_percentage > 10:
        recommendations.append("High percentage of slow queries detected - review query optimization")
    
    # Check average execution time
    avg_time = performance_summary.get("average_execution_time", 0)
    if avg_time > 0.5:
        recommendations.append("Average query execution time is high - consider index optimization")
    
    # Check for common slow query patterns
    if slow_queries:
        query_texts = [q.query_text for q in slow_queries]
        
        # Check for missing WHERE clauses
        if any("WHERE" not in query.upper() for query in query_texts):
            recommendations.append("Some queries lack WHERE clauses - ensure proper filtering")
        
        # Check for SELECT * patterns
        if any("SELECT *" in query.upper() for query in query_texts):
            recommendations.append("Avoid SELECT * queries - specify required columns")
        
        # Check for ORDER BY without LIMIT
        order_by_queries = [q for q in query_texts if "ORDER BY" in q.upper()]
        if any("LIMIT" not in query.upper() for query in order_by_queries):
            recommendations.append("ORDER BY queries without LIMIT can be expensive")
    
    if not recommendations:
        recommendations.append("Query performance looks good - no immediate optimizations needed")
    
    return recommendations


def _get_query_performance_status(query_summary: Dict[str, Any]) -> str:
    """
    Determine query performance status.
    
    Args:
        query_summary: Query performance summary
        
    Returns:
        Performance status string
    """
    avg_time = query_summary.get("average_execution_time", 0)
    slow_query_percentage = query_summary.get("slow_query_percentage", 0)
    
    if avg_time > 1.0 or slow_query_percentage > 20:
        return "critical"
    elif avg_time > 0.5 or slow_query_percentage > 10:
        return "warning"
    else:
        return "healthy"


def _get_system_recommendations(
    query_summary: Dict[str, Any],
    pool_status: Dict[str, Any],
    db_info: Dict[str, Any]
) -> List[str]:
    """
    Generate system-wide performance recommendations.
    
    Args:
        query_summary: Query performance summary
        pool_status: Connection pool status
        db_info: Database information
        
    Returns:
        List of system recommendations
    """
    recommendations = []
    
    # Connection pool recommendations
    pool_utilization = pool_status.get("utilization_percent", 0)
    if pool_utilization > 80:
        recommendations.append("Connection pool utilization is high - consider increasing pool size")
    elif pool_utilization < 20:
        recommendations.append("Connection pool may be over-provisioned")
    
    # Cache hit ratio recommendations
    cache_hit_ratio = db_info.get("performance_stats", {}).get("cache_hit_ratio", 0)
    if cache_hit_ratio < 90:
        recommendations.append("Database cache hit ratio is low - consider increasing shared_buffers")
    
    # Query performance recommendations
    avg_query_time = query_summary.get("average_execution_time", 0)
    if avg_query_time > 0.5:
        recommendations.append("Average query time is high - review indexing strategy")
    
    # Add pool-specific recommendations
    pool_recommendations = pool_status.get("recommendations", [])
    recommendations.extend(pool_recommendations)
    
    if not recommendations:
        recommendations.append("System performance is optimal")
    
    return recommendations