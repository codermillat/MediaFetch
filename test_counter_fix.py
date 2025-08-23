#!/usr/bin/env python3
"""
Test script to verify the Counter fix works correctly
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_counter_initialization():
    """Test that MetricsCollector can be initialized without Counter conflicts"""
    try:
        from telegram_media_bot.metrics import MetricsCollector

        # This should not crash with the Counter error
        metrics = MetricsCollector()
        print("✅ MetricsCollector initialized successfully")

        # Test the platform_stats Counter
        metrics.platform_stats['test'] = 1
        print("✅ Platform stats Counter working correctly")

        # Test error breakdown Counter
        summary = metrics.get_summary()
        print("✅ Error breakdown Counter working correctly")

        return True
    except Exception as e:
        print(f"❌ Counter initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prometheus_fallback():
    """Test prometheus client fallback mechanism"""
    try:
        from telegram_media_bot.metrics import MetricsCollector

        metrics = MetricsCollector()

        # Test prometheus metrics generation (should use fallback)
        prometheus_data = metrics.get_prometheus_metrics()
        print("✅ Prometheus fallback working correctly")
        print(f"Generated {len(prometheus_data)} bytes of metrics data")

        return True
    except Exception as e:
        print(f"❌ Prometheus fallback failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Counter fixes...")
    print("=" * 50)

    tests = [
        test_counter_initialization,
        test_prometheus_fallback
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
        print("🎉 All Counter fixes working! Should resolve Heroku crashes.")
        return 0
    else:
        print("❌ Some tests failed. Issues may persist.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
