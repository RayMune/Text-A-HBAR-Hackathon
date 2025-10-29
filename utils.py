"""
Utility functions and helpers for TextAHBAR application
This module provides various utility functions for phone number validation,
transaction logging, error handling, and integration helpers.
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import uuid

class TransactionLogger:
    """
    Enhanced transaction logging with structured data
    """
    
    def __init__(self, log_file: str = "transactions.json"):
        self.log_file = log_file
        self.transactions = []
        self.load_existing_logs()
    
    def load_existing_logs(self):
        """Load existing transaction logs from file"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    self.transactions = json.load(f)
        except Exception as e:
            logging.warning(f"Could not load existing transaction logs: {e}")
            self.transactions = []
    
    def log_transaction(self, transaction_type: str, data: Dict) -> str:
        """
        Log a new transaction with structured data
        
        Args:
            transaction_type: Type of transaction (sms, token_transfer, stock_purchase)
            data: Transaction data dictionary
            
        Returns:
            Transaction ID
        """
        transaction_id = f"{transaction_type.upper()}_{uuid.uuid4().hex[:8]}"
        
        log_entry = {
            'transaction_id': transaction_id,
            'type': transaction_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'status': data.get('success', False)
        }
        
        self.transactions.append(log_entry)
        self.save_logs()
        
        logging.info(f"Transaction logged: {transaction_id} ({transaction_type})")
        return transaction_id
    
    def save_logs(self):
        """Save transaction logs to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.transactions, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save transaction logs: {e}")
    
    def get_transactions(self, transaction_type: str = None, limit: int = 50) -> List[Dict]:
        """Get transaction history with optional filtering"""
        filtered = self.transactions
        
        if transaction_type:
            filtered = [tx for tx in filtered if tx['type'] == transaction_type]
        
        return filtered[-limit:] if filtered else []
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Get specific transaction by ID"""
        for tx in self.transactions:
            if tx['transaction_id'] == transaction_id:
                return tx
        return None

class PhoneNumberUtils:
    """
    Enhanced phone number utilities for African markets
    """
    
    KENYAN_PREFIXES = {
        '70': 'Safaricom',
        '71': 'Safaricom', 
        '72': 'Safaricom',
        '74': 'Safaricom',
        '75': 'Safaricom',
        '76': 'Safaricom',
        '77': 'Safaricom',
        '78': 'Safaricom',
        '79': 'Safaricom',
        '73': 'Airtel',
        '78': 'Airtel',  # Some overlap
        '10': 'Airtel',
        '73': 'Telkom',
        '77': 'Telkom',  # Some overlap
    }
    
    @classmethod
    def identify_kenyan_network(cls, phone_number: str) -> str:
        """Identify the mobile network for a Kenyan phone number"""
        # Extract first two digits after country code
        clean_number = re.sub(r'[^\d]', '', phone_number)
        
        if clean_number.startswith('254'):
            prefix = clean_number[3:5]
        elif clean_number.startswith('0'):
            prefix = clean_number[1:3]
        else:
            prefix = clean_number[:2]
        
        return cls.KENYAN_PREFIXES.get(prefix, 'Unknown')
    
    @classmethod
    def format_display_number(cls, phone_number: str) -> str:
        """Format phone number for display purposes"""
        clean = re.sub(r'[^\d]', '', phone_number)
        
        if clean.startswith('254'):
            return f"+254 {clean[3:6]} {clean[6:9]} {clean[9:]}"
        elif len(clean) == 10 and clean.startswith('0'):
            return f"0{clean[1:4]} {clean[4:7]} {clean[7:]}"
        else:
            return phone_number  # Return as-is if format unclear

class SMSCostCalculator:
    """
    Calculate SMS costs and delivery estimates
    """
    
    COSTS = {
        'local': 1.00,      # KES per SMS within Kenya
        'international': 5.00,  # KES per international SMS
        'premium': 2.00     # KES per premium SMS
    }
    
    @classmethod
    def calculate_cost(cls, phone_number: str, message_length: int) -> Dict:
        """
        Calculate SMS cost based on destination and length
        
        Args:
            phone_number: Recipient phone number
            message_length: Length of SMS message
            
        Returns:
            Cost breakdown dictionary
        """
        # Determine if local or international
        is_local = cls._is_kenyan_number(phone_number)
        
        # Calculate number of SMS units needed (160 chars per SMS)
        sms_count = max(1, (message_length + 159) // 160)
        
        base_cost = cls.COSTS['local'] if is_local else cls.COSTS['international']
        total_cost = base_cost * sms_count
        
        return {
            'phone_number': phone_number,
            'is_local': is_local,
            'message_length': message_length,
            'sms_count': sms_count,
            'cost_per_sms': base_cost,
            'total_cost': total_cost,
            'currency': 'KES',
            'network': PhoneNumberUtils.identify_kenyan_network(phone_number) if is_local else 'International'
        }
    
    @classmethod
    def _is_kenyan_number(cls, phone_number: str) -> bool:
        """Check if phone number is Kenyan"""
        clean = re.sub(r'[^\d]', '', phone_number)
        return clean.startswith('254') or (clean.startswith('0') and len(clean) == 10)

class ConfigValidator:
    """
    Validate application configuration and API credentials
    """
    
    REQUIRED_ENV_VARS = [
        'AWS_BEARER_TOKEN_BEDROCK',
        'MY_ACCOUNT_ID',
        'MY_PRIVATE_KEY', 
        'TOKEN_ID',
        'AFRICASTALKING_USERNAME',
        'AFRICASTALKING_API_KEY'
    ]
    
    @classmethod
    def validate_environment(cls) -> Dict[str, bool]:
        """Validate all required environment variables are set"""
        validation = {}
        
        for var in cls.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            validation[var] = bool(value and value != '' and 'your_' not in value.lower())
        
        # Additional validations
        validation['hedera_account_format'] = cls._validate_hedera_account(os.getenv('MY_ACCOUNT_ID'))
        validation['token_id_format'] = cls._validate_hedera_account(os.getenv('TOKEN_ID'))
        
        validation['all_valid'] = all(validation.values())
        
        return validation
    
    @classmethod
    def _validate_hedera_account(cls, account_id: str) -> bool:
        """Validate Hedera account ID format"""
        if not account_id:
            return False
        return bool(re.match(r'^0\.\d+\.\d+$', account_id))
    
    @classmethod
    def get_configuration_report(cls) -> Dict:
        """Get comprehensive configuration report"""
        validation = cls.validate_environment()
        
        report = {
            'validation_results': validation,
            'environment_summary': {
                'hedera_network': os.getenv('HEDERA_NETWORK', 'testnet'),
                'africastalking_mode': 'sandbox' if os.getenv('AFRICASTALKING_USERNAME') == 'sandbox' else 'production',
                'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
            },
            'recommendations': []
        }
        
        # Add recommendations based on validation
        if not validation['all_valid']:
            report['recommendations'].append("Some environment variables are missing or invalid")
        
        if os.getenv('AFRICASTALKING_USERNAME') == 'sandbox':
            report['recommendations'].append("Using AfricasTalking sandbox mode - switch to production for live SMS")
        
        if os.getenv('HEDERA_NETWORK') == 'testnet':
            report['recommendations'].append("Using Hedera testnet - switch to mainnet for production")
        
        return report

class MessageFormatter:
    """
    Format messages for different channels and contexts
    """
    
    @staticmethod
    def format_stock_summary(stock_data: Dict) -> str:
        """Format stock information for display"""
        return (
            f"📈 {stock_data['name']} ({stock_data['ticker']})\n"
            f"💰 Price: KES {stock_data['price']:.2f}\n"
            f"🏢 Sector: {stock_data['sector']}\n"
            f"📊 Market Cap: {stock_data['market_cap']}"
        )
    
    @staticmethod
    def format_transaction_summary(transaction: Dict) -> str:
        """Format transaction for SMS or display"""
        tx_type = transaction.get('type', 'Transaction')
        amount = transaction.get('amount', 0)
        timestamp = datetime.fromisoformat(transaction.get('timestamp', datetime.now().isoformat()))
        
        return (
            f"✅ {tx_type.title()} Complete\n"
            f"💰 Amount: {amount}\n"
            f"🕒 Time: {timestamp.strftime('%d/%m/%y %H:%M')}\n"
            f"📧 Ref: {transaction.get('transaction_id', 'N/A')[:12]}..."
        )
    
    @staticmethod
    def format_error_message(error: str, context: str = None) -> str:
        """Format error message for user display"""
        base_message = "❌ Something went wrong"
        
        if context:
            base_message = f"❌ {context} failed"
        
        return f"{base_message}\n🔍 Error: {error}\n📞 Please contact support if this persists."

class RateLimiter:
    """
    Simple rate limiting for API calls and SMS sending
    """
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests = []
    
    def can_make_request(self, identifier: str = "default") -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests = [req for req in self.requests if req['timestamp'] > window_start]
        
        # Count requests for this identifier
        identifier_requests = [req for req in self.requests if req['identifier'] == identifier]
        
        return len(identifier_requests) < self.max_requests
    
    def record_request(self, identifier: str = "default"):
        """Record a new request"""
        self.requests.append({
            'identifier': identifier,
            'timestamp': datetime.now()
        })

# Global utility instances
transaction_logger = TransactionLogger()
sms_rate_limiter = RateLimiter(max_requests=30, window_minutes=1)  # 30 SMS per minute
api_rate_limiter = RateLimiter(max_requests=100, window_minutes=1)  # 100 API calls per minute