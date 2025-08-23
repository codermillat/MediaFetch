#!/usr/bin/env python3
"""
Test script to verify metrics fixes work correctly
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_metrics_import():
    """Test that metrics can be imported without conflicts"""
    try:
        from telegram_media_bot.metrics import MetricsCollector
        print("✅ MetricsCollector imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import MetricsCollector: {e}")
        return False

def test_metrics_initialization():
    """Test that metrics can be initialized without conflicts"""
    try:
        from telegram_media_bot.metrics import MetricsCollector

        # Create metrics instance
        metrics = MetricsCollector()
        print("✅ MetricsCollector initialized successfully")

        # Test basic metrics operations
        metrics.increment_command_usage('test')
        print("✅ Command usage incremented successfully")

        # Test prometheus metrics generation
        prometheus_metrics = metrics.get_prometheus_metrics()
        print("✅ Prometheus metrics generated successfully")
        print(f"Metrics length: {len(prometheus_metrics)} bytes")

        return True
    except Exception as e:
        print(f"❌ Failed to initialize metrics: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_metrics_endpoint():
    """Test that the app metrics endpoint works"""
    try:
        from app import global_metrics

        # Test metrics generation
        metrics_data = global_metrics.get_prometheus_metrics()
        print("✅ App metrics generated successfully")
        print(f"App metrics length: {len(metrics_data)} bytes")

        return True
    except Exception as e:
        print(f"❌ Failed to test app metrics: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing metrics fixes...")
    print("=" * 50)

    tests = [
        test_metrics_import,
        test_metrics_initialization,
        test_app_metrics_endpoint
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Metrics fixes should resolve the Heroku issues.")
        return 0
    else:
        print("❌ Some tests failed. Issues may persist.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
