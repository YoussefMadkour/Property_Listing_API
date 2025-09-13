"""
Performance monitoring middleware for request timing and metrics collection.
Provides detailed performance monitoring and logging capabilities.
"""

from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import time
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

# Optional psutil import for system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive performance monitoring and metrics collection.
    Tracks request timing, system resources, and endpoint performance.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enable_detailed_logging: bool = True,
        enable_metrics_collection: bool = True,
        slow_request_threshold: float = 1.0,  # seconds
        metrics_window_size: int = 1000,  # number of requests to keep in memory
        enable_system_monitoring: bool = True
    ):
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
        self.enable_metrics_collection = enable_metrics_collection
        self.slow_request_threshold = slow_request_threshold
        self.metrics_window_size = metrics_window_size
        self.enable_system_monitoring = enable_system_monitoring
        
        # Metrics storage
        self.request_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=metrics_window_size))
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "error_count": 0,
            "last_request": None
        })
        
        # System monitoring
        self.system_stats = {
            "start_time": datetime.utcnow(),
            "total_requests": 0,
            "total_errors": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through performance monitoring middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response object with performance headers
        """
        start_time = time.time()
        start_cpu_time = time.process_time()
        
        # Get system metrics before request
        system_metrics_before = await self._get_system_metrics() if self.enable_system_monitoring else {}
        
        # Generate or get request ID
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate timing metrics
            end_time = time.time()
            end_cpu_time = time.process_time()
            
            processing_time = end_time - start_time
            cpu_time = end_cpu_time - start_cpu_time
            
            # Get system metrics after request
            system_metrics_after = await self._get_system_metrics() if self.enable_system_monitoring else {}
            
            # Log performance metrics
            await self._log_performance_metrics(
                request, response, request_id, processing_time, cpu_time,
                system_metrics_before, system_metrics_after
            )
            
            # Collect metrics
            if self.enable_metrics_collection:
                await self._collect_metrics(request, response, processing_time, cpu_time)
            
            # Add performance headers to response
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            response.headers["X-CPU-Time"] = f"{cpu_time:.3f}"
            
            # Update system stats
            self.system_stats["total_requests"] += 1
            if response.status_code >= 400:
                self.system_stats["total_errors"] += 1
            
            return response
            
        except Exception as exc:
            # Handle errors and still log performance
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.error(
                f"Request error [{request_id}]: {type(exc).__name__} - {str(exc)} "
                f"(processing_time: {processing_time:.3f}s)",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "processing_time": processing_time,
                    "error_type": type(exc).__name__
                },
                exc_info=True
            )
            
            # Update error stats
            self.system_stats["total_requests"] += 1
            self.system_stats["total_errors"] += 1
            
            # Re-raise the exception
            raise exc
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system performance metrics.
        
        Returns:
            Dictionary containing system metrics
        """
        if not PSUTIL_AVAILABLE:
            return {}
            
        try:
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            # Get process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "process_memory_rss": process_memory.rss,
                "process_memory_vms": process_memory.vms,
                "process_cpu_percent": process.cpu_percent(),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            return {}
    
    async def _log_performance_metrics(
        self,
        request: Request,
        response: Response,
        request_id: str,
        processing_time: float,
        cpu_time: float,
        system_before: Dict[str, Any],
        system_after: Dict[str, Any]
    ) -> None:
        """
        Log detailed performance metrics.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            request_id: Unique request identifier
            processing_time: Total processing time in seconds
            cpu_time: CPU processing time in seconds
            system_before: System metrics before request
            system_after: System metrics after request
        """
        if not self.enable_detailed_logging:
            return
        
        endpoint = f"{request.method} {request.url.path}"
        
        # Determine log level based on performance
        if processing_time > self.slow_request_threshold:
            log_level = logging.WARNING
            log_message = f"SLOW REQUEST [{request_id}]: {endpoint} - {processing_time:.3f}s"
        else:
            log_level = logging.INFO
            log_message = f"Request [{request_id}]: {endpoint} - {processing_time:.3f}s"
        
        # Prepare extra logging data
        extra_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time": processing_time,
            "cpu_time": cpu_time,
            "endpoint": endpoint
        }
        
        # Add system metrics if available
        if system_before and system_after:
            extra_data.update({
                "cpu_usage_before": system_before.get("cpu_percent", 0),
                "cpu_usage_after": system_after.get("cpu_percent", 0),
                "memory_usage_before": system_before.get("memory_percent", 0),
                "memory_usage_after": system_after.get("memory_percent", 0),
                "process_memory_delta": (
                    system_after.get("process_memory_rss", 0) - 
                    system_before.get("process_memory_rss", 0)
                )
            })
        
        # Add query parameters for GET requests
        if request.method == "GET" and request.query_params:
            extra_data["query_params"] = dict(request.query_params)
        
        logger.log(log_level, log_message, extra=extra_data)
    
    async def _collect_metrics(
        self,
        request: Request,
        response: Response,
        processing_time: float,
        cpu_time: float
    ) -> None:
        """
        Collect and store performance metrics.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            processing_time: Total processing time in seconds
            cpu_time: CPU processing time in seconds
        """
        endpoint = f"{request.method} {request.url.path}"
        
        # Store individual request metrics
        metric_data = {
            "timestamp": time.time(),
            "processing_time": processing_time,
            "cpu_time": cpu_time,
            "status_code": response.status_code,
            "method": request.method,
            "path": request.url.path
        }
        
        self.request_metrics[endpoint].append(metric_data)
        
        # Update endpoint statistics
        stats = self.endpoint_stats[endpoint]
        stats["total_requests"] += 1
        stats["total_time"] += processing_time
        stats["min_time"] = min(stats["min_time"], processing_time)
        stats["max_time"] = max(stats["max_time"], processing_time)
        stats["last_request"] = datetime.utcnow()
        
        if response.status_code >= 400:
            stats["error_count"] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Returns:
            Dictionary containing performance statistics
        """
        summary = {
            "system_stats": self.system_stats.copy(),
            "uptime_seconds": (datetime.utcnow() - self.system_stats["start_time"]).total_seconds(),
            "endpoints": {}
        }
        
        # Calculate endpoint statistics
        for endpoint, stats in self.endpoint_stats.items():
            if stats["total_requests"] > 0:
                avg_time = stats["total_time"] / stats["total_requests"]
                error_rate = stats["error_count"] / stats["total_requests"]
                
                summary["endpoints"][endpoint] = {
                    "total_requests": stats["total_requests"],
                    "average_time": round(avg_time, 3),
                    "min_time": round(stats["min_time"], 3),
                    "max_time": round(stats["max_time"], 3),
                    "error_count": stats["error_count"],
                    "error_rate": round(error_rate, 3),
                    "last_request": stats["last_request"].isoformat() if stats["last_request"] else None
                }
        
        return summary
    
    def get_recent_slow_requests(self, limit: int = 10) -> list:
        """
        Get recent slow requests across all endpoints.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of slow request metrics
        """
        slow_requests = []
        
        for endpoint, metrics in self.request_metrics.items():
            for metric in metrics:
                if metric["processing_time"] > self.slow_request_threshold:
                    slow_requests.append({
                        "endpoint": endpoint,
                        "timestamp": datetime.fromtimestamp(metric["timestamp"]).isoformat(),
                        "processing_time": metric["processing_time"],
                        "cpu_time": metric["cpu_time"],
                        "status_code": metric["status_code"]
                    })
        
        # Sort by processing time (slowest first) and limit results
        slow_requests.sort(key=lambda x: x["processing_time"], reverse=True)
        return slow_requests[:limit]