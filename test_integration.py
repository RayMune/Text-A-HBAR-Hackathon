#!/usr/bin/env python3
"""
Test script for TextAHBAR SMS and HBAR functionality
Run this script to test the integration of AfricasTalking SMS and Hedera token transfers
"""

import os
import sys
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sms_service import sms_service, SMSTemplates
from africastalking_client import api_client, PhoneNumberValidator
from hbar_manager import transaction_service
from utils import (
    transaction_logger, PhoneNumberUtils, SMSCostCalculator, 
    ConfigValidator, MessageFormatter
)

def test_configuration():
    """Test application configuration"""
    print("🔧 Testing Configuration...")
    config_report = ConfigValidator.get_configuration_report()
    
    print(f"Configuration Valid: {config_report['validation_results']['all_valid']}")
    print(f"Environment Summary: {json.dumps(config_report['environment_summary'], indent=2)}")
    
    if config_report['recommendations']:
        print("Recommendations:")
        for rec in config_report['recommendations']:
            print(f"  • {rec}")
    
    return config_report['validation_results']['all_valid']

def test_phone_validation():
    """Test phone number validation and formatting"""
    print("\n📞 Testing Phone Number Validation...")
    
    test_numbers = [
        "+254700000000",
        "0700000000",
        "254722000000",
        "0733123456"
    ]
    
    for phone in test_numbers:
        formatted = PhoneNumberValidator.format_phone_number(phone)
        validation = PhoneNumberValidator.validate_phone_number(phone)
        network = PhoneNumberUtils.identify_kenyan_network(phone)
        display = PhoneNumberUtils.format_display_number(phone)
        
        print(f"Original: {phone}")
        print(f"  Formatted: {formatted}")
        print(f"  Display: {display}")
        print(f"  Network: {network}")
        print(f"  Valid: {validation['is_valid']}")
        print()

def test_sms_cost_calculation():
    """Test SMS cost calculation"""
    print("💰 Testing SMS Cost Calculation...")
    
    test_cases = [
        ("+254700000000", "Short message"),
        ("+254722000000", "This is a longer message that might span multiple SMS segments depending on the length and character count which could affect pricing"),
        ("+1234567890", "International message")
    ]
    
    for phone, message in test_cases:
        cost_info = SMSCostCalculator.calculate_cost(phone, len(message))
        print(f"Phone: {phone}")
        print(f"Message Length: {len(message)} chars")
        print(f"SMS Count: {cost_info['sms_count']}")
        print(f"Total Cost: {cost_info['currency']} {cost_info['total_cost']:.2f}")
        print(f"Network: {cost_info['network']}")
        print()

def test_sms_templates():
    """Test SMS message templates"""
    print("📱 Testing SMS Templates...")
    
    # Test stock purchase confirmation
    stock_sms = SMSTemplates.stock_purchase_confirmation(
        "Safaricom PLC", 5, 112.50, "STOCK_ABC123"
    )
    print("Stock Purchase SMS:")
    print(stock_sms)
    print()
    
    # Test HBAR transfer notification
    hbar_sms = SMSTemplates.hbar_transfer_notification(
        50, "0.0.1234", "TX123ABC456"
    )
    print("HBAR Transfer SMS:")
    print(hbar_sms)
    print()
    
    # Test M-PESA confirmation
    mpesa_sms = SMSTemplates.mpesa_confirmation(
        112.50, "Safaricom PLC", 287.50, "MP123456"
    )
    print("M-PESA Confirmation SMS:")
    print(mpesa_sms)
    print()

def test_sms_sending():
    """Test SMS sending functionality"""
    print("📤 Testing SMS Sending...")
    
    # Test with demo phone number
    test_phone = "+254700000000"
    test_message = "Hello from TextAHBAR! This is a test message to verify SMS functionality."
    
    # Send via SMS service
    result = sms_service.sms_client.send_sms(test_phone, test_message)
    
    print(f"SMS Send Result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Message ID: {result.get('message_id', 'N/A')}")
    print(f"  Status: {result.get('status', 'unknown')}")
    print(f"  Cost: {result.get('cost', 'N/A')}")
    
    if result.get('success'):
        # Test delivery report
        delivery = sms_service.sms_client.get_delivery_reports(result['message_id'])
        print(f"  Delivery Status: {delivery.get('status', 'unknown')}")

def test_hedera_functionality():
    """Test Hedera token management"""
    print("\n⚡ Testing Hedera Functionality...")
    
    # Test account balance query
    balance_info = transaction_service.token_manager.get_account_balance()
    print(f"Account Balance Query:")
    print(f"  Success: {balance_info.get('success', False)}")
    print(f"  Account: {balance_info.get('account_id', 'N/A')}")
    print(f"  HBAR Balance: {balance_info.get('hbar_balance', 'N/A')}")
    print(f"  Token Balance: {balance_info.get('token_balance', 'N/A')}")
    
    # Test token transfer (simulation)
    print("\nTesting Token Transfer (simulation)...")
    transfer_result = transaction_service.token_manager.transfer_tokens(
        "0.0.9999", 10, "Test stock purchase"
    )
    
    print(f"Token Transfer Result:")
    print(f"  Success: {transfer_result.get('success', False)}")
    print(f"  Transaction ID: {transfer_result.get('transaction_id', 'N/A')}")
    print(f"  Status: {transfer_result.get('status', 'N/A')}")
    
    if transfer_result.get('explorer_url'):
        print(f"  Explorer URL: {transfer_result['explorer_url']}")

def test_integrated_stock_purchase():
    """Test complete stock purchase flow"""
    print("\n🏪 Testing Integrated Stock Purchase Flow...")
    
    # Simulate complete stock purchase with SMS notifications
    result = transaction_service.process_stock_purchase(
        recipient_phone="+254700000000",
        recipient_account="0.0.9999",
        stock_name="Safaricom PLC",
        quantity=5,
        price=112.50
    )
    
    print(f"Stock Purchase Result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Transaction Reference: {result.get('transaction_reference', 'N/A')}")
    print(f"  Stock: {result.get('stock_name', 'N/A')}")
    print(f"  Quantity: {result.get('quantity', 'N/A')}")
    print(f"  Total Price: KES {result.get('price', 0):.2f}")
    
    # Show token transfer details
    token_result = result.get('token_transfer', {})
    print(f"  Token Transfer Success: {token_result.get('success', False)}")
    
    # Show SMS notification results
    sms_notifications = result.get('sms_notifications', [])
    print(f"  SMS Notifications Sent: {len(sms_notifications)}")
    
    for i, notification in enumerate(sms_notifications, 1):
        print(f"    {i}. {notification['type']}: {notification['result'].get('success', False)}")

def test_transaction_logging():
    """Test transaction logging functionality"""
    print("\n📝 Testing Transaction Logging...")
    
    # Log a test transaction
    test_data = {
        'amount': 100.0,
        'recipient': '+254700000000',
        'success': True
    }
    
    tx_id = transaction_logger.log_transaction('test_transaction', test_data)
    print(f"Transaction Logged: {tx_id}")
    
    # Retrieve recent transactions
    recent = transaction_logger.get_transactions(limit=5)
    print(f"Recent Transactions: {len(recent)}")
    
    for tx in recent[-3:]:  # Show last 3
        print(f"  {tx['transaction_id']}: {tx['type']} - {tx['status']}")

def main():
    """Run all tests"""
    print("🚀 TextAHBAR Integration Test Suite")
    print("=" * 50)
    
    try:
        # Run all test functions
        test_configuration()
        test_phone_validation()
        test_sms_cost_calculation()
        test_sms_templates()
        test_sms_sending()
        test_hedera_functionality()
        test_integrated_stock_purchase()
        test_transaction_logging()
        
        print("\n✅ All tests completed successfully!")
        print("Your TextAHBAR app is ready for SMS and HBAR functionality.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()