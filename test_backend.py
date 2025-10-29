#!/usr/bin/env python3
"""
Backend API Test Script
Quick test to verify all backend functionality works without frontend
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

def test_api_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an API endpoint and return result"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code == expected_status,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "response_time": response.elapsed.total_seconds()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def run_backend_tests():
    """Run comprehensive backend API tests"""
    
    print("🚀 TextAHBAR Backend API Test Suite")
    print("=" * 50)
    
    # Test results storage
    results = []
    
    # Test 1: Service Info
    print("1. Testing service information...")
    result = test_api_endpoint("GET", "/")
    results.append(("Service Info", result))
    if result.get("success"):
        print("   ✅ Service info endpoint working")
        service_data = result.get("data", {})
        print(f"   📝 Service: {service_data.get('service', 'Unknown')}")
        print(f"   📊 Version: {service_data.get('version', 'Unknown')}")
        print(f"   🔧 Features: {len(service_data.get('features', []))}")
    else:
        print(f"   ❌ Service info failed: {result.get('error', 'Unknown error')}")
    
    # Test 2: API Documentation
    print("\n2. Testing API documentation...")
    result = test_api_endpoint("GET", "/api/docs")
    results.append(("API Docs", result))
    if result.get("success"):
        print("   ✅ API documentation available")
        docs = result.get("data", {})
        endpoints = docs.get("endpoints", {})
        print(f"   📚 Documented endpoints: {len(endpoints)}")
    else:
        print(f"   ❌ API docs failed: {result.get('error', 'Unknown error')}")
    
    # Test 3: Dashboard
    print("\n3. Testing service dashboard...")
    result = test_api_endpoint("GET", "/api/dashboard")
    results.append(("Dashboard", result))
    if result.get("success"):
        print("   ✅ Dashboard accessible")
        dashboard = result.get("data", {})
        services = dashboard.get("services", {})
        print(f"   🎛️ Services monitored: {len(services)}")
        for service, status in services.items():
            print(f"      • {service}: {status}")
    else:
        print(f"   ❌ Dashboard failed: {result.get('error', 'Unknown error')}")
    
    # Test 4: Stock List
    print("\n4. Testing stock listings...")
    result = test_api_endpoint("GET", "/api/stocks/list")
    results.append(("Stock List", result))
    if result.get("success"):
        print("   ✅ Stock listings available")
        stock_data = result.get("data", {})
        stocks = stock_data.get("stocks", [])
        print(f"   📈 Available stocks: {len(stocks)}")
        if stocks:
            print(f"      Example: {stocks[0].get('name')} ({stocks[0].get('ticker')}) - KES {stocks[0].get('price')}")
    else:
        print(f"   ❌ Stock list failed: {result.get('error', 'Unknown error')}")
    
    # Test 5: Specific Stock Price
    print("\n5. Testing stock price query...")
    result = test_api_endpoint("GET", "/api/stocks/price/SAF")
    results.append(("Stock Price", result))
    if result.get("success"):
        print("   ✅ Stock price query working")
        stock_info = result.get("data", {}).get("stock", {})
        print(f"   💰 {stock_info.get('name', 'N/A')}: KES {stock_info.get('price', 0):.2f}")
    else:
        print(f"   ❌ Stock price failed: {result.get('error', 'Unknown error')}")
    
    # Test 6: Phone Validation
    print("\n6. Testing phone validation...")
    phone_data = {"phone_number": "+254700000000"}
    result = test_api_endpoint("POST", "/api/phone/validate", phone_data)
    results.append(("Phone Validation", result))
    if result.get("success"):
        print("   ✅ Phone validation working")
        validation_result = result.get("data", {})
        print(f"   📞 Formatted: {validation_result.get('formatted', 'N/A')}")
        print(f"   🌐 Network: {validation_result.get('network', 'N/A')}")
        print(f"   ✓ Valid: {validation_result.get('validation', {}).get('is_valid', False)}")
    else:
        print(f"   ❌ Phone validation failed: {result.get('error', 'Unknown error')}")
    
    # Test 7: SMS Status
    print("\n7. Testing SMS service status...")
    result = test_api_endpoint("GET", "/sms_status")
    results.append(("SMS Status", result))
    if result.get("success"):
        print("   ✅ SMS service status available")
        sms_status = result.get("data", {})
        print(f"   📱 Service: {sms_status.get('service_status', 'unknown')}")
        print(f"   📊 Recent messages: {sms_status.get('recent_messages', 0)}")
    else:
        print(f"   ❌ SMS status failed: {result.get('error', 'Unknown error')}")
    
    # Test 8: Hedera Status
    print("\n8. Testing Hedera service status...")
    result = test_api_endpoint("GET", "/hedera_status")
    results.append(("Hedera Status", result))
    if result.get("success"):
        print("   ✅ Hedera service status available")
        hedera_status = result.get("data", {})
        print(f"   ⚡ Network: {hedera_status.get('network', 'unknown')}")
        print(f"   🏦 Account: {hedera_status.get('account_id', 'N/A')}")
        print(f"   🪙 Token ID: {hedera_status.get('token_id', 'N/A')}")
    else:
        print(f"   ❌ Hedera status failed: {result.get('error', 'Unknown error')}")
    
    # Test 9: Chat Endpoint (AI Integration)
    print("\n9. Testing chat endpoint...")
    chat_data = {
        "message": "What is the price of Safaricom stock?",
        "recipient_name": "stock trader",
        "convo_id": 1
    }
    result = test_api_endpoint("POST", "/api/chat", chat_data)
    results.append(("Chat", result))
    if result.get("success"):
        print("   ✅ Chat endpoint working")
        chat_response = result.get("data", {})
        reply = chat_response.get("reply", "No reply")
        print(f"   🤖 AI Response: {reply[:100]}{'...' if len(reply) > 100 else ''}")
    else:
        print(f"   ❌ Chat failed: {result.get('error', 'Unknown error')}")
    
    # Test 10: Transaction History
    print("\n10. Testing transaction history...")
    result = test_api_endpoint("GET", "/api/transactions?limit=5")
    results.append(("Transactions", result))
    if result.get("success"):
        print("   ✅ Transaction history available")
        tx_data = result.get("data", {})
        stats = tx_data.get("statistics", {})
        print(f"   📊 Total transactions: {stats.get('total_transactions', 0)}")
        print(f"   ✅ Successful: {stats.get('successful_transactions', 0)}")
        print(f"   ❌ Failed: {stats.get('failed_transactions', 0)}")
    else:
        print(f"   ❌ Transaction history failed: {result.get('error', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    successful_tests = sum(1 for _, result in results if result.get("success", False))
    total_tests = len(results)
    
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    print(f"📊 Success rate: {(successful_tests/total_tests*100):.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 All tests passed! Your TextAHBAR backend is fully operational.")
    else:
        print(f"\n⚠️  {total_tests - successful_tests} test(s) failed. Check the details above.")
        print("\nFailed tests:")
        for test_name, result in results:
            if not result.get("success", False):
                print(f"   ❌ {test_name}: {result.get('error', 'Unknown error')}")
    
    # Performance Summary
    print(f"\n⏱️  Average response time: {sum(r.get('response_time', 0) for _, r in results) / len(results):.3f}s")
    
    # Next Steps
    print("\n🚀 NEXT STEPS:")
    print("1. Run: python cli_manager.py utils config  # Check configuration")
    print("2. Run: python api_client.py              # Test Python client")
    print("3. Visit: http://localhost:8080/api/docs  # View API documentation")
    print("4. Test SMS: python cli_manager.py sms send --to '+254700000000' --message 'Test'")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    try:
        print("🔄 Starting backend tests...")
        print("⏳ Make sure your TextAHBAR app is running on localhost:8080")
        print()
        
        # Give user a moment to start the app if needed
        time.sleep(2)
        
        success = run_backend_tests()
        exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)