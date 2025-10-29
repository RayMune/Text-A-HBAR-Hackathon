#!/usr/bin/env python3
"""
TextAHBAR CLI Management Tool
Command-line interface for managing SMS, HBAR, and stock operations
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sms_service import sms_service
from africastalking_client import api_client, PhoneNumberValidator
from hbar_manager import transaction_service
from utils import (
    transaction_logger, PhoneNumberUtils, SMSCostCalculator,
    ConfigValidator, MessageFormatter
)

def setup_cli():
    """Setup command-line argument parser"""
    parser = argparse.ArgumentParser(description='TextAHBAR CLI Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # SMS Commands
    sms_parser = subparsers.add_parser('sms', help='SMS operations')
    sms_subparsers = sms_parser.add_subparsers(dest='sms_action')
    
    # Send SMS
    send_sms_parser = sms_subparsers.add_parser('send', help='Send SMS message')
    send_sms_parser.add_argument('--to', required=True, help='Recipient phone number')
    send_sms_parser.add_argument('--message', required=True, help='SMS message content')
    send_sms_parser.add_argument('--sender-id', default='TEXTAHBAR', help='Sender ID')
    
    # SMS Status
    sms_subparsers.add_parser('status', help='Check SMS service status')
    
    # SMS History
    history_parser = sms_subparsers.add_parser('history', help='View SMS history')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of messages to show')
    
    # HBAR Commands
    hbar_parser = subparsers.add_parser('hbar', help='Hedera HBAR operations')
    hbar_subparsers = hbar_parser.add_subparsers(dest='hbar_action')
    
    # Balance Query
    balance_parser = hbar_subparsers.add_parser('balance', help='Check account balance')
    balance_parser.add_argument('--account', help='Hedera account ID (optional)')
    
    # Transfer Tokens
    transfer_parser = hbar_subparsers.add_parser('transfer', help='Transfer tokens')
    transfer_parser.add_argument('--to', required=True, help='Recipient account ID')
    transfer_parser.add_argument('--amount', type=int, required=True, help='Token amount')
    transfer_parser.add_argument('--memo', help='Transaction memo')
    transfer_parser.add_argument('--notify', help='Phone number for SMS notification')
    
    # Stock Commands
    stock_parser = subparsers.add_parser('stocks', help='Stock operations')
    stock_subparsers = stock_parser.add_subparsers(dest='stock_action')
    
    # List Stocks
    stock_subparsers.add_parser('list', help='List available stocks')
    
    # Stock Price
    price_parser = stock_subparsers.add_parser('price', help='Get stock price')
    price_parser.add_argument('ticker', help='Stock ticker symbol')
    
    # Buy Stock
    buy_parser = stock_subparsers.add_parser('buy', help='Buy stock')
    buy_parser.add_argument('--ticker', required=True, help='Stock ticker')
    buy_parser.add_argument('--quantity', type=int, required=True, help='Number of shares')
    buy_parser.add_argument('--phone', required=True, help='Phone for notifications')
    buy_parser.add_argument('--account', required=True, help='Hedera account for tokens')
    
    # Utility Commands
    util_parser = subparsers.add_parser('utils', help='Utility operations')
    util_subparsers = util_parser.add_subparsers(dest='util_action')
    
    # Config Check
    util_subparsers.add_parser('config', help='Check configuration')
    
    # Phone Validation
    phone_parser = util_subparsers.add_parser('phone', help='Validate phone number')
    phone_parser.add_argument('number', help='Phone number to validate')
    
    # Transaction History
    tx_parser = util_subparsers.add_parser('transactions', help='View transaction history')
    tx_parser.add_argument('--type', help='Filter by transaction type')
    tx_parser.add_argument('--limit', type=int, default=20, help='Number of transactions')
    
    # Cost Calculator
    cost_parser = util_subparsers.add_parser('cost', help='Calculate SMS cost')
    cost_parser.add_argument('--phone', required=True, help='Phone number')
    cost_parser.add_argument('--message', required=True, help='Message content')
    
    return parser

def handle_sms_commands(args):
    """Handle SMS-related commands"""
    if args.sms_action == 'send':
        print(f"📱 Sending SMS to {args.to}...")
        
        # Validate phone number
        validation = PhoneNumberValidator.validate_phone_number(args.to)
        if not validation['is_valid']:
            print(f"❌ Invalid phone number: {args.to}")
            return
        
        # Calculate cost
        cost_info = SMSCostCalculator.calculate_cost(args.to, len(args.message))
        print(f"💰 Estimated cost: {cost_info['currency']} {cost_info['total_cost']:.2f}")
        
        # Send SMS
        result = sms_service.sms_client.send_sms(args.to, args.message, args.sender_id)
        
        if result.get('success'):
            print(f"✅ SMS sent successfully!")
            print(f"   Message ID: {result.get('message_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Cost: {result.get('cost', 'N/A')}")
        else:
            print(f"❌ SMS sending failed: {result.get('error', 'Unknown error')}")
    
    elif args.sms_action == 'status':
        print("📊 SMS Service Status:")
        api_stats = api_client.get_api_stats()
        print(f"   Mode: {api_stats.get('mode', 'unknown')}")
        print(f"   Requests made: {api_stats.get('request_count', 0)}")
        print(f"   Last request: {api_stats.get('last_request', 'Never')}")
        print(f"   Config valid: {api_stats.get('config_valid', False)}")
    
    elif args.sms_action == 'history':
        print(f"📜 Recent SMS History (last {args.limit}):")
        history = sms_service.get_message_history(args.limit)
        
        if not history:
            print("   No SMS messages found")
            return
        
        for i, msg in enumerate(history, 1):
            print(f"   {i}. {msg['type']} to {msg['recipient']}")
            print(f"      Status: {msg['result'].get('success', False)}")
            print(f"      Time: {msg['timestamp']}")

def handle_hbar_commands(args):
    """Handle HBAR-related commands"""
    if args.hbar_action == 'balance':
        account_id = args.account or transaction_service.token_manager.config.my_account_id
        print(f"💰 Checking balance for account: {account_id}")
        
        balance_info = transaction_service.token_manager.get_account_balance(account_id)
        
        if balance_info.get('success'):
            print(f"✅ Account Balance:")
            print(f"   Account: {balance_info['account_id']}")
            print(f"   HBAR: {balance_info.get('hbar_balance', 'N/A')}")
            print(f"   Tokens: {balance_info.get('token_balance', 'N/A')}")
            print(f"   Token ID: {balance_info.get('token_id', 'N/A')}")
        else:
            print(f"❌ Balance query failed: {balance_info.get('error', 'Unknown error')}")
    
    elif args.hbar_action == 'transfer':
        print(f"⚡ Transferring {args.amount} tokens to {args.to}...")
        
        # Validate account ID
        if not transaction_service.token_manager.validate_account_id(args.to):
            print(f"❌ Invalid Hedera account ID format: {args.to}")
            return
        
        # Transfer tokens
        result = transaction_service.token_manager.transfer_tokens(
            args.to, args.amount, args.memo or f"CLI transfer - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if result.get('success'):
            print(f"✅ Transfer completed!")
            print(f"   Transaction ID: {result.get('transaction_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Explorer: {result.get('explorer_url')}")
            
            # Send SMS notification if requested
            if args.notify:
                print(f"📱 Sending SMS notification to {args.notify}...")
                sms_result = sms_service.notify_token_transfer(
                    args.notify, args.amount, args.to, result.get('transaction_id', '')
                )
                print(f"   SMS sent: {sms_result.get('success', False)}")
        else:
            print(f"❌ Transfer failed: {result.get('error', 'Unknown error')}")

def handle_stock_commands(args):
    """Handle stock-related commands"""
    if args.stock_action == 'list':
        print("📈 Available Kenyan Stocks (NSE):")
        
        # Import kenya_stocks from app
        from app import kenya_stocks
        
        for i, stock in enumerate(kenya_stocks, 1):
            print(f"   {i:2}. {stock['name']} ({stock['ticker']})")
            print(f"       Price: KES {stock['price']:.2f} | Sector: {stock['sector']}")
            print(f"       Market Cap: {stock['market_cap']}")
            print()
    
    elif args.stock_action == 'price':
        print(f"💹 Getting price for {args.ticker.upper()}...")
        
        from app import find_stock, generate_stock_advice
        stock = find_stock(args.ticker.upper())
        
        if stock:
            print(f"✅ {stock['name']} ({stock['ticker']})")
            print(f"   Current Price: KES {stock['price']:.2f}")
            print(f"   Sector: {stock['sector']}")
            print(f"   Market Cap: {stock['market_cap']}")
            print(f"   Advice: {generate_stock_advice(stock)}")
        else:
            print(f"❌ Stock not found: {args.ticker.upper()}")
    
    elif args.stock_action == 'buy':
        print(f"🛒 Purchasing {args.quantity} shares of {args.ticker.upper()}...")
        
        from app import find_stock
        stock = find_stock(args.ticker.upper())
        
        if not stock:
            print(f"❌ Stock not found: {args.ticker.upper()}")
            return
        
        total_cost = stock['price'] * args.quantity
        print(f"   Stock: {stock['name']}")
        print(f"   Quantity: {args.quantity}")
        print(f"   Unit Price: KES {stock['price']:.2f}")
        print(f"   Total Cost: KES {total_cost:.2f}")
        
        # Process purchase
        result = transaction_service.process_stock_purchase(
            recipient_phone=args.phone,
            recipient_account=args.account,
            stock_name=stock['name'],
            quantity=args.quantity,
            price=total_cost
        )
        
        if result.get('success'):
            print(f"✅ Stock purchase completed!")
            print(f"   Reference: {result.get('transaction_reference')}")
            print(f"   HBAR Transfer: {result.get('token_transfer', {}).get('success', False)}")
            print(f"   SMS Notifications: {len(result.get('sms_notifications', []))}")
        else:
            print(f"❌ Stock purchase failed: {result.get('error', 'Unknown error')}")

def handle_util_commands(args):
    """Handle utility commands"""
    if args.util_action == 'config':
        print("⚙️ Configuration Status:")
        config_report = ConfigValidator.get_configuration_report()
        
        validation = config_report['validation_results']
        print(f"   Overall Status: {'✅ Valid' if validation['all_valid'] else '❌ Invalid'}")
        print("\n   Individual Checks:")
        
        for key, value in validation.items():
            if key != 'all_valid':
                status = '✅' if value else '❌'
                print(f"   {status} {key.replace('_', ' ').title()}")
        
        if config_report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in config_report['recommendations']:
                print(f"   • {rec}")
    
    elif args.util_action == 'phone':
        print(f"📞 Validating phone number: {args.number}")
        
        # Validate
        validation = PhoneNumberValidator.validate_phone_number(args.number)
        formatted = PhoneNumberValidator.format_phone_number(args.number)
        network = PhoneNumberUtils.identify_kenyan_network(args.number)
        display = PhoneNumberUtils.format_display_number(args.number)
        
        print(f"   Original: {args.number}")
        print(f"   Formatted: {formatted}")
        print(f"   Display Format: {display}")
        print(f"   Network: {network}")
        print(f"   Valid: {'✅' if validation['is_valid'] else '❌'}")
        
        if not validation['is_valid']:
            print("   Issues:")
            for check, passed in validation.items():
                if check != 'is_valid' and not passed:
                    print(f"   • {check.replace('_', ' ').title()}")
    
    elif args.util_action == 'transactions':
        print(f"📊 Transaction History (last {args.limit}):")
        transactions = transaction_logger.get_transactions(args.type, args.limit)
        
        if not transactions:
            print("   No transactions found")
            return
        
        for tx in transactions:
            status = '✅' if tx.get('status') else '❌'
            timestamp = datetime.fromisoformat(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   {status} {tx['transaction_id']} ({tx['type']})")
            print(f"      Time: {timestamp}")
            if tx.get('data'):
                key_data = {k: v for k, v in tx['data'].items() if k in ['amount', 'recipient', 'phone_number', 'stock_name']}
                for key, value in key_data.items():
                    print(f"      {key.title()}: {value}")
            print()
    
    elif args.util_action == 'cost':
        print(f"💰 Calculating SMS cost...")
        cost_info = SMSCostCalculator.calculate_cost(args.phone, len(args.message))
        
        print(f"   Phone: {args.phone}")
        print(f"   Message Length: {len(args.message)} characters")
        print(f"   SMS Count: {cost_info['sms_count']} SMS")
        print(f"   Cost per SMS: {cost_info['currency']} {cost_info['cost_per_sms']:.2f}")
        print(f"   Total Cost: {cost_info['currency']} {cost_info['total_cost']:.2f}")
        print(f"   Network: {cost_info['network']}")
        print(f"   Local: {'Yes' if cost_info['is_local'] else 'No'}")

def main():
    """Main CLI entry point"""
    parser = setup_cli()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🚀 TextAHBAR CLI Tool")
    print("=" * 40)
    
    try:
        if args.command == 'sms':
            handle_sms_commands(args)
        elif args.command == 'hbar':
            handle_hbar_commands(args)
        elif args.command == 'stocks':
            handle_stock_commands(args)
        elif args.command == 'utils':
            handle_util_commands(args)
        else:
            print(f"❌ Unknown command: {args.command}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 40)

if __name__ == "__main__":
    main()