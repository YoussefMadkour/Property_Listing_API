"""
Database query optimization utilities for performance monitoring and optimization.
Provides query analysis, index verification, and performance monitoring capabilities.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect, MetaData, Table
from sqlalchemy.engine import Engine
from typing import Dict, List, Any, Optional, Tuple
import logging
import time
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetric:
    """Data class for storing query performance metrics."""
    query_hash: str
    query_text: str
    execution_time: float
    rows_examined: Optional[int]
    rows_returned: Optional[int]
    timestamp: datetime
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class IndexUsageStats:
    """Data class for index usage statistics."""
    table_name: str
    index_name: str
    scans: int
    tuples_read: int
    tuples_fetched: int
    last_used: Optional[datetime]


class QueryOptimizer:
    """
    Query optimization and monitoring utility.
    Provides database query analysis, index verification, and performance monitoring.
    """
    
    def __init__(self):
        self.query_metrics: Dict[str, List[QueryPerformanceMetric]] = defaultdict(list)
        self.slow_query_threshold = 1.0  # seconds
        self.metrics_retention_hours = 24
        self._cleanup_task = None
    
    async def analyze_query_performance(
        self,
        db: AsyncSession,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None
    ) -> QueryPerformanceMetric:
        """
        Analyze query performance using EXPLAIN ANALYZE.
        
        Args:
            db: Database session
            query: SQL query to analyze
            parameters: Query parameters
            endpoint: API endpoint that triggered the query
            
        Returns:
            QueryPerformanceMetric with performance data
        """
        try:
            # Generate query hash for tracking
            query_hash = str(hash(query))
            
            # Execute EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            start_time = time.time()
            
            if parameters:
                result = await db.execute(text(explain_query), parameters)
            else:
                result = await db.execute(text(explain_query))
            
            execution_time = time.time() - start_time
            explain_result = result.fetchone()[0]
            
            # Extract performance metrics from explain result
            plan = explain_result[0]["Plan"]
            rows_examined = self._extract_rows_examined(plan)
            rows_returned = plan.get("Actual Rows", 0)
            
            # Create performance metric
            metric = QueryPerformanceMetric(
                query_hash=query_hash,
                query_text=query[:500],  # Truncate for storage
                execution_time=execution_time,
                rows_examined=rows_examined,
                rows_returned=rows_returned,
                timestamp=datetime.utcnow(),
                endpoint=endpoint,
                parameters=parameters
            )
            
            # Store metric
            self.query_metrics[query_hash].append(metric)
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected: {execution_time:.3f}s - {query[:100]}...",
                    extra={
                        "query_hash": query_hash,
                        "execution_time": execution_time,
                        "rows_examined": rows_examined,
                        "rows_returned": rows_returned,
                        "endpoint": endpoint
                    }
                )
            
            return metric
        except Exception as e:
            logger.error(f"Failed to analyze query performance: {e}")
            # Return basic metric without detailed analysis
            return QueryPerformanceMetric(
                query_hash=str(hash(query)),
                query_text=query[:500],
                execution_time=0.0,
                rows_examined=None,
                rows_returned=None,
                timestamp=datetime.utcnow(),
                endpoint=endpoint,
                parameters=parameters
            )
    
    def _extract_rows_examined(self, plan: Dict[str, Any]) -> int:
        """
        Extract total rows examined from query plan.
        
        Args:
            plan: Query execution plan
            
        Returns:
            Total number of rows examined
        """
        rows_examined = plan.get("Actual Rows", 0)
        
        # Add rows from child plans
        if "Plans" in plan:
            for child_plan in plan["Plans"]:
                rows_examined += self._extract_rows_examined(child_plan)
        
        return rows_examined
    
    async def verify_index_usage(self, db: AsyncSession) -> List[IndexUsageStats]:
        """
        Verify database index usage statistics.
        
        Args:
            db: Database session
            
        Returns:
            List of index usage statistics
        """
        try:
            # Query PostgreSQL statistics for index usage
            index_stats_query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC;
            """
            
            result = await db.execute(text(index_stats_query))
            rows = result.fetchall()
            
            index_stats = []
            for row in rows:
                stats = IndexUsageStats(
                    table_name=row.tablename,
                    index_name=row.indexname,
                    scans=row.scans,
                    tuples_read=row.tuples_read,
                    tuples_fetched=row.tuples_fetched,
                    last_used=None  # PostgreSQL doesn't track last used time
                )
                index_stats.append(stats)
            
            logger.info(f"Retrieved index usage statistics for {len(index_stats)} indexes")
            return index_stats
        except Exception as e:
            logger.error(f"Failed to verify index usage: {e}")
            return []
    
    async def get_unused_indexes(self, db: AsyncSession) -> List[str]:
        """
        Identify potentially unused indexes.
        
        Args:
            db: Database session
            
        Returns:
            List of unused index names
        """
        try:
            unused_indexes_query = """
            SELECT 
                schemaname,
                tablename,
                indexname
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            AND idx_scan = 0
            AND indexname NOT LIKE '%_pkey'  -- Exclude primary keys
            ORDER BY tablename, indexname;
            """
            
            result = await db.execute(text(unused_indexes_query))
            rows = result.fetchall()
            
            unused_indexes = [f"{row.tablename}.{row.indexname}" for row in rows]
            
            if unused_indexes:
                logger.warning(f"Found {len(unused_indexes)} potentially unused indexes")
            
            return unused_indexes
        except Exception as e:
            logger.error(f"Failed to get unused indexes: {e}")
            return []
    
    async def analyze_table_statistics(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """
        Analyze table statistics for optimization insights.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with table statistics
        """
        try:
            table_stats_query = """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC;
            """
            
            result = await db.execute(text(table_stats_query))
            rows = result.fetchall()
            
            table_stats = {}
            for row in rows:
                table_stats[row.tablename] = {
                    "inserts": row.inserts,
                    "updates": row.updates,
                    "deletes": row.deletes,
                    "live_tuples": row.live_tuples,
                    "dead_tuples": row.dead_tuples,
                    "dead_tuple_ratio": (
                        row.dead_tuples / max(row.live_tuples, 1) 
                        if row.dead_tuples else 0
                    ),
                    "last_vacuum": row.last_vacuum,
                    "last_autovacuum": row.last_autovacuum,
                    "last_analyze": row.last_analyze,
                    "last_autoanalyze": row.last_autoanalyze
                }
            
            logger.info(f"Retrieved statistics for {len(table_stats)} tables")
            return table_stats
        except Exception as e:
            logger.error(f"Failed to analyze table statistics: {e}")
            return {}
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryPerformanceMetric]:
        """
        Get slowest queries from recent metrics.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of slowest query metrics
        """
        all_metrics = []
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        
        for query_hash, metrics in self.query_metrics.items():
            # Filter recent metrics
            recent_metrics = [
                m for m in metrics 
                if m.timestamp > cutoff_time
            ]
            all_metrics.extend(recent_metrics)
        
        # Sort by execution time (slowest first)
        all_metrics.sort(key=lambda x: x.execution_time, reverse=True)
        
        return all_metrics[:limit]
    
    def get_query_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive query performance summary.
        
        Returns:
            Dictionary with performance summary
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        
        total_queries = 0
        slow_queries = 0
        total_execution_time = 0.0
        execution_times = []
        
        for query_hash, metrics in self.query_metrics.items():
            recent_metrics = [
                m for m in metrics 
                if m.timestamp > cutoff_time
            ]
            
            for metric in recent_metrics:
                total_queries += 1
                total_execution_time += metric.execution_time
                execution_times.append(metric.execution_time)
                
                if metric.execution_time > self.slow_query_threshold:
                    slow_queries += 1
        
        if not execution_times:
            return {
                "total_queries": 0,
                "slow_queries": 0,
                "average_execution_time": 0.0,
                "median_execution_time": 0.0,
                "p95_execution_time": 0.0,
                "p99_execution_time": 0.0
            }
        
        execution_times.sort()
        
        return {
            "total_queries": total_queries,
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / total_queries * 100) if total_queries > 0 else 0,
            "average_execution_time": total_execution_time / total_queries,
            "median_execution_time": execution_times[len(execution_times) // 2],
            "p95_execution_time": execution_times[int(len(execution_times) * 0.95)],
            "p99_execution_time": execution_times[int(len(execution_times) * 0.99)],
            "total_execution_time": total_execution_time
        }
    
    async def start_cleanup_task(self):
        """Start background task to clean up old metrics."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_old_metrics(self):
        """Background task to clean up old metrics."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
                
                for query_hash in list(self.query_metrics.keys()):
                    # Filter out old metrics
                    self.query_metrics[query_hash] = [
                        m for m in self.query_metrics[query_hash]
                        if m.timestamp > cutoff_time
                    ]
                    
                    # Remove empty entries
                    if not self.query_metrics[query_hash]:
                        del self.query_metrics[query_hash]
                
                logger.debug("Cleaned up old query metrics")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup task: {e}")


# Global query optimizer instance
query_optimizer = QueryOptimizer()