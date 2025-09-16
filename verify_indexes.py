#!/usr/bin/env python3
"""
Database index verification script.
Verifies that all required indexes are created and provides optimization recommendations.
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, inspect
from app.config import settings
from app.utils.query_optimizer import query_optimizer
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_database_indexes():
    """
    Verify that all required database indexes exist and are being used.
    
    Returns:
        Dictionary with verification results
    """
    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Get all indexes in the database
            indexes_query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
            """
            
            result = await conn.execute(text(indexes_query))
            existing_indexes = result.fetchall()
            
            # Expected indexes for optimal performance
            expected_indexes = {
                'properties': [
                    'properties_pkey',  # Primary key
                    'ix_properties_id',  # ID index
                    'ix_properties_created_at',  # Created at index
                    'ix_properties_updated_at',  # Updated at index
                    'ix_properties_title',  # Title index
                    'ix_properties_property_type',  # Property type index
                    'ix_properties_price',  # Price index
                    'ix_properties_bedrooms',  # Bedrooms index
                    'ix_properties_location',  # Location index
                    'ix_properties_is_active',  # Active status index
                    'ix_properties_agent_id',  # Agent ID index
                    'idx_properties_location_price',  # Composite location-price index
                    'idx_properties_bedrooms_price',  # Composite bedrooms-price index
                    'idx_properties_type_active',  # Composite type-active index
                    'idx_properties_agent_active',  # Composite agent-active index
                    'idx_properties_search_optimization',  # Comprehensive search index
                    'idx_properties_coordinates'  # Coordinates index
                ],
                'users': [
                    'users_pkey',  # Primary key
                    'ix_users_id',  # ID index
                    'ix_users_created_at',  # Created at index
                    'ix_users_updated_at',  # Updated at index
                    'ix_users_email'  # Email index (unique)
                ],
                'property_images': [
                    'property_images_pkey',  # Primary key
                    'ix_property_images_id',  # ID index
                    'ix_property_images_created_at',  # Created at index
                    'ix_property_images_updated_at',  # Updated at index
                    'ix_property_images_property_id'  # Property ID foreign key index
                ]
            }
            
            # Organize existing indexes by table
            existing_by_table = {}
            for row in existing_indexes:
                table = row.tablename
                if table not in existing_by_table:
                    existing_by_table[table] = []
                existing_by_table[table].append({
                    'name': row.indexname,
                    'definition': row.indexdef
                })
            
            # Check for missing indexes
            missing_indexes = {}
            for table, expected in expected_indexes.items():
                if table not in existing_by_table:
                    missing_indexes[table] = expected
                    continue
                
                existing_names = [idx['name'] for idx in existing_by_table[table]]
                missing = [idx for idx in expected if idx not in existing_names]
                if missing:
                    missing_indexes[table] = missing
            
            # Get index usage statistics
            async with AsyncSession(engine) as session:
                index_stats = await query_optimizer.verify_index_usage(session)
                unused_indexes = await query_optimizer.get_unused_indexes(session)
                table_stats = await query_optimizer.analyze_table_statistics(session)
            
            return {
                'existing_indexes': existing_by_table,
                'missing_indexes': missing_indexes,
                'index_usage_stats': index_stats,
                'unused_indexes': unused_indexes,
                'table_statistics': table_stats,
                'total_indexes': len(existing_indexes),
                'verification_passed': len(missing_indexes) == 0
            }
    
    finally:
        await engine.dispose()


async def generate_index_recommendations(verification_results: Dict[str, Any]) -> List[str]:
    """
    Generate index optimization recommendations.
    
    Args:
        verification_results: Results from index verification
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Check for missing indexes
    missing_indexes = verification_results.get('missing_indexes', {})
    if missing_indexes:
        recommendations.append("CRITICAL: Missing required indexes detected!")
        for table, indexes in missing_indexes.items():
            recommendations.append(f"  - Table '{table}' missing indexes: {', '.join(indexes)}")
        recommendations.append("  Run database migrations to create missing indexes.")
    
    # Check for unused indexes
    unused_indexes = verification_results.get('unused_indexes', [])
    if unused_indexes:
        recommendations.append("INFO: Unused indexes detected (consider removing if confirmed unused):")
        for index in unused_indexes:
            recommendations.append(f"  - {index}")
    
    # Check table statistics for optimization opportunities
    table_stats = verification_results.get('table_statistics', {})
    for table, stats in table_stats.items():
        dead_tuple_ratio = stats.get('dead_tuple_ratio', 0)
        if dead_tuple_ratio > 0.1:  # More than 10% dead tuples
            recommendations.append(f"WARNING: Table '{table}' has high dead tuple ratio ({dead_tuple_ratio:.1%})")
            recommendations.append(f"  Consider running VACUUM ANALYZE on '{table}' table")
    
    # Check index usage patterns
    index_stats = verification_results.get('index_usage_stats', [])
    if index_stats:
        # Find heavily used indexes
        heavy_usage_threshold = 10000
        heavy_indexes = [stat for stat in index_stats if stat.scans > heavy_usage_threshold]
        if heavy_indexes:
            recommendations.append("INFO: Heavily used indexes (monitor for performance):")
            for stat in heavy_indexes[:5]:  # Top 5
                recommendations.append(f"  - {stat.table_name}.{stat.index_name}: {stat.scans} scans")
    
    # General recommendations
    if not recommendations:
        recommendations.append("✅ Index configuration looks optimal!")
        recommendations.append("Continue monitoring index usage patterns.")
    
    recommendations.extend([
        "",
        "General Performance Tips:",
        "- Monitor slow query logs for optimization opportunities",
        "- Consider partial indexes for frequently filtered subsets",
        "- Use EXPLAIN ANALYZE to verify query plans use indexes",
        "- Regular VACUUM and ANALYZE maintenance is important"
    ])
    
    return recommendations


async def create_missing_indexes_sql(missing_indexes: Dict[str, List[str]]) -> List[str]:
    """
    Generate SQL statements to create missing indexes.
    
    Args:
        missing_indexes: Dictionary of missing indexes by table
        
    Returns:
        List of SQL CREATE INDEX statements
    """
    sql_statements = []
    
    # Index definitions (these should match the model definitions)
    index_definitions = {
        'idx_properties_location_price': 
            "CREATE INDEX idx_properties_location_price ON properties (location, price, is_active);",
        'idx_properties_bedrooms_price': 
            "CREATE INDEX idx_properties_bedrooms_price ON properties (bedrooms, price, is_active);",
        'idx_properties_type_active': 
            "CREATE INDEX idx_properties_type_active ON properties (property_type, is_active, created_at DESC);",
        'idx_properties_agent_active': 
            "CREATE INDEX idx_properties_agent_active ON properties (agent_id, is_active, updated_at DESC);",
        'idx_properties_search_optimization': 
            "CREATE INDEX idx_properties_search_optimization ON properties (location, price, bedrooms, property_type, is_active);",
        'idx_properties_coordinates': 
            "CREATE INDEX idx_properties_coordinates ON properties (latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;"
    }
    
    for table, indexes in missing_indexes.items():
        for index in indexes:
            if index in index_definitions:
                sql_statements.append(index_definitions[index])
            elif not index.endswith('_pkey') and not index.startswith('ix_'):
                # Skip primary keys and basic column indexes (handled by SQLAlchemy)
                sql_statements.append(f"-- Missing index: {index} (definition needed)")
    
    return sql_statements


async def main():
    """Main function to verify database indexes."""
    print("🔍 Verifying database indexes...")
    print("=" * 50)
    
    try:
        # Verify indexes
        results = await verify_database_indexes()
        
        # Print results
        print(f"Total indexes found: {results['total_indexes']}")
        print(f"Verification passed: {'✅' if results['verification_passed'] else '❌'}")
        print()
        
        # Print existing indexes by table
        print("📊 Existing Indexes by Table:")
        for table, indexes in results['existing_indexes'].items():
            print(f"  {table}: {len(indexes)} indexes")
            for idx in indexes:
                print(f"    - {idx['name']}")
        print()
        
        # Print missing indexes
        if results['missing_indexes']:
            print("⚠️  Missing Indexes:")
            for table, indexes in results['missing_indexes'].items():
                print(f"  {table}: {', '.join(indexes)}")
            print()
            
            # Generate SQL for missing indexes
            sql_statements = await create_missing_indexes_sql(results['missing_indexes'])
            if sql_statements:
                print("📝 SQL to create missing indexes:")
                for sql in sql_statements:
                    print(f"  {sql}")
                print()
        
        # Print unused indexes
        if results['unused_indexes']:
            print("🗑️  Potentially Unused Indexes:")
            for index in results['unused_indexes']:
                print(f"  - {index}")
            print()
        
        # Generate and print recommendations
        recommendations = await generate_index_recommendations(results)
        print("💡 Recommendations:")
        for rec in recommendations:
            print(f"  {rec}")
        
        # Print index usage statistics
        if results['index_usage_stats']:
            print("\n📈 Top 10 Most Used Indexes:")
            sorted_stats = sorted(results['index_usage_stats'], key=lambda x: x.scans, reverse=True)
            for stat in sorted_stats[:10]:
                print(f"  {stat.table_name}.{stat.index_name}: {stat.scans:,} scans, {stat.tuples_read:,} tuples read")
        
        # Exit with error code if verification failed
        if not results['verification_passed']:
            print("\n❌ Index verification failed!")
            sys.exit(1)
        else:
            print("\n✅ Index verification passed!")
    
    except Exception as e:
        logger.error(f"Index verification failed: {e}")
        print(f"❌ Error during verification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())