#!/usr/bin/env python3
"""
Performance test runner for the Property Listing API.
Runs comprehensive performance tests and generates reports.
"""

import asyncio
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List
import argparse


def run_command(command: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    """
    Run a command and return the result.
    
    Args:
        command: Command to run as list of strings
        cwd: Working directory
        
    Returns:
        CompletedProcess result
    """
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    
    return result


def setup_test_environment():
    """Set up the test environment."""
    print("Setting up test environment...")
    
    # Start Docker containers
    result = run_command(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"])
    if result.returncode != 0:
        print("Failed to start test containers")
        return False
    
    # Wait for services to be ready
    print("Waiting for services to be ready...")
    time.sleep(10)
    
    # Run database migrations
    result = run_command(["docker-compose", "-f", "docker-compose.test.yml", "exec", "-T", "api", "python", "migrate.py"])
    if result.returncode != 0:
        print("Failed to run database migrations")
        return False
    
    return True


def cleanup_test_environment():
    """Clean up the test environment."""
    print("Cleaning up test environment...")
    run_command(["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"])


def run_performance_tests(test_pattern: str = None) -> Dict[str, Any]:
    """
    Run performance tests and collect results.
    
    Args:
        test_pattern: Optional test pattern to filter tests
        
    Returns:
        Test results dictionary
    """
    print("Running performance tests...")
    
    # Build pytest command
    command = [
        "docker-compose", "-f", "docker-compose.test.yml", "exec", "-T", "api",
        "python", "-m", "pytest", "tests/test_performance.py", "-v", "--tb=short"
    ]
    
    if test_pattern:
        command.extend(["-k", test_pattern])
    
    # Add performance-specific options
    command.extend([
        "--durations=10",  # Show 10 slowest tests
        "--disable-warnings",
        "--json-report",
        "--json-report-file=/tmp/performance_report.json"
    ])
    
    result = run_command(command)
    
    # Extract test results
    test_results = {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.returncode
    }
    
    # Try to get JSON report
    try:
        json_result = run_command([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", "-T", "api",
            "cat", "/tmp/performance_report.json"
        ])
        if json_result.returncode == 0:
            test_results["json_report"] = json.loads(json_result.stdout)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Failed to parse JSON report: {e}")
    
    return test_results


def run_load_tests() -> Dict[str, Any]:
    """
    Run load tests using locust or similar tool.
    
    Returns:
        Load test results
    """
    print("Running load tests...")
    
    # For now, we'll simulate load tests with concurrent pytest runs
    # In a real scenario, you'd use tools like locust, artillery, or k6
    
    load_test_results = {
        "message": "Load tests would be implemented with tools like locust or k6",
        "concurrent_test_simulation": True
    }
    
    # Run concurrent performance tests to simulate load
    concurrent_command = [
        "docker-compose", "-f", "docker-compose.test.yml", "exec", "-T", "api",
        "python", "-m", "pytest", "tests/test_performance.py::TestPerformanceOptimization::test_concurrent_search_requests",
        "-v", "--tb=short"
    ]
    
    result = run_command(concurrent_command)
    load_test_results.update({
        "concurrent_test_success": result.returncode == 0,
        "concurrent_test_output": result.stdout
    })
    
    return load_test_results


def generate_performance_report(test_results: Dict[str, Any], load_results: Dict[str, Any]) -> str:
    """
    Generate a comprehensive performance report.
    
    Args:
        test_results: Performance test results
        load_results: Load test results
        
    Returns:
        Report content as string
    """
    report_lines = [
        "# Property Listing API Performance Report",
        f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Test Environment",
        "- Docker containers with PostgreSQL database",
        "- Test data with large datasets (1000+ properties)",
        "- Concurrent request simulation",
        "",
        "## Performance Test Results",
        f"- Overall Success: {'✅' if test_results['success'] else '❌'}",
        f"- Return Code: {test_results['return_code']}",
        ""
    ]
    
    # Add JSON report summary if available
    if "json_report" in test_results:
        json_report = test_results["json_report"]
        summary = json_report.get("summary", {})
        
        report_lines.extend([
            "### Test Summary",
            f"- Total Tests: {summary.get('total', 'N/A')}",
            f"- Passed: {summary.get('passed', 'N/A')}",
            f"- Failed: {summary.get('failed', 'N/A')}",
            f"- Duration: {summary.get('duration', 'N/A')}s",
            ""
        ])
        
        # Add test details
        if "tests" in json_report:
            report_lines.extend([
                "### Individual Test Results",
                ""
            ])
            
            for test in json_report["tests"]:
                status = "✅" if test.get("outcome") == "passed" else "❌"
                duration = test.get("duration", 0)
                report_lines.append(f"- {test.get('nodeid', 'Unknown')}: {status} ({duration:.3f}s)")
            
            report_lines.append("")
    
    # Add load test results
    report_lines.extend([
        "## Load Test Results",
        f"- Concurrent Test Success: {'✅' if load_results.get('concurrent_test_success', False) else '❌'}",
        ""
    ])
    
    # Add test output excerpts
    if test_results.get("stdout"):
        report_lines.extend([
            "## Test Output (Last 20 lines)",
            "```",
            *test_results["stdout"].split('\n')[-20:],
            "```",
            ""
        ])
    
    # Add recommendations
    report_lines.extend([
        "## Performance Recommendations",
        "",
        "### Database Optimization",
        "- Ensure all search indexes are properly created",
        "- Monitor query execution plans for slow queries",
        "- Consider connection pool tuning for high concurrency",
        "",
        "### Application Optimization", 
        "- Implement caching for frequently accessed data",
        "- Use pagination for large result sets",
        "- Monitor memory usage during peak loads",
        "",
        "### Infrastructure Optimization",
        "- Scale horizontally with multiple API instances",
        "- Use read replicas for search-heavy workloads",
        "- Implement CDN for static assets",
        ""
    ])
    
    return "\n".join(report_lines)


def main():
    """Main function to run performance tests."""
    parser = argparse.ArgumentParser(description="Run Property Listing API performance tests")
    parser.add_argument("--test-pattern", help="Test pattern to filter tests")
    parser.add_argument("--skip-setup", action="store_true", help="Skip test environment setup")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip test environment cleanup")
    parser.add_argument("--output", default="performance_report.md", help="Output report file")
    
    args = parser.parse_args()
    
    try:
        # Setup test environment
        if not args.skip_setup:
            if not setup_test_environment():
                print("Failed to setup test environment")
                sys.exit(1)
        
        # Run performance tests
        test_results = run_performance_tests(args.test_pattern)
        
        # Run load tests
        load_results = run_load_tests()
        
        # Generate report
        report_content = generate_performance_report(test_results, load_results)
        
        # Write report to file
        with open(args.output, 'w') as f:
            f.write(report_content)
        
        print(f"Performance report generated: {args.output}")
        
        # Print summary
        print("\n" + "="*50)
        print("PERFORMANCE TEST SUMMARY")
        print("="*50)
        print(f"Performance Tests: {'PASSED' if test_results['success'] else 'FAILED'}")
        print(f"Load Tests: {'PASSED' if load_results.get('concurrent_test_success', False) else 'FAILED'}")
        print(f"Report: {args.output}")
        
        # Exit with appropriate code
        if not test_results['success']:
            sys.exit(1)
    
    finally:
        # Cleanup test environment
        if not args.skip_cleanup:
            cleanup_test_environment()


if __name__ == "__main__":
    main()