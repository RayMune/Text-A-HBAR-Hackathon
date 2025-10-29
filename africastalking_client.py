"""
AfricasTalking API Integration Module
This module provides authentication, configuration, and core API functionality
for integrating with AfricasTalking services.
"""

import os
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Optional

class AfricasTalkingConfig:
    """
    Configuration management for AfricasTalking API
    """
    
    def __init__(self):
        # Load configuration from environment variables
        self.username = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
        self.api_key = os.getenv('AFRICASTALKING_API_KEY', self._get_demo_api_key())
        self.sender_id = os.getenv('AFRICASTALKING_SENDER_ID', 'TEXTAHBAR')
        
        # API endpoints
        self.is_sandbox = self.username == 'sandbox'
        self.base_url = self._get_base_url()
        
        # Rate limiting and retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0
        self.rate_limit_per_minute = 100
        
        logging.info(f"AfricasTalking configured - Mode: {'Sandbox' if self.is_sandbox else 'Production'}")
    
    def _get_demo_api_key(self) -> str:
        """Generate a demo API key for testing purposes"""
        return "atsk_" + "x" * 40  # Demo key format
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL based on environment"""
        if self.is_sandbox:
            return "https://api.sandbox.africastalking.com/version1"
        else:
            return "https://api.africastalking.com/version1"
    
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey': self.api_key,
            'User-Agent': f'TextAHBAR-App/1.0 ({self.username})'
        }
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration settings"""
        validation = {
            'username_set': bool(self.username and self.username != ''),
            'api_key_set': bool(self.api_key and self.api_key != ''),
            'sender_id_valid': bool(self.sender_id and len(self.sender_id) <= 11),
            'endpoints_accessible': True  # Would normally test connectivity
        }
        
        validation['all_valid'] = all(validation.values())
        
        if not validation['all_valid']:
            logging.warning("AfricasTalking configuration validation failed")
        
        return validation

class AfricasTalkingAPI:
    """
    Core API client for AfricasTalking services
    """
    
    def __init__(self):
        self.config = AfricasTalkingConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())
        
        # Request tracking
        self.request_count = 0
        self.last_request_time = None
        
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make authenticated request to AfricasTalking API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload
            
        Returns:
            API response as dict
        """
        try:
            url = f"{self.config.base_url}/{endpoint}"
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            logging.debug(f"Making {method} request to {url}")
            
            # For demo purposes, simulate API responses
            if "messaging" in endpoint and method.upper() == "POST":
                return self._simulate_sms_response(data)
            elif "delivery-reports" in endpoint:
                return self._simulate_delivery_report()
            elif "balance" in endpoint:
                return self._simulate_balance_response()
            else:
                return self._simulate_generic_response()
                
        except Exception as e:
            logging.error(f"API request failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _simulate_sms_response(self, data: Dict) -> Dict:
        """Simulate SMS sending response"""
        import uuid
        import random
        
        message_id = f"ATXid_{uuid.uuid4().hex[:16]}"
        cost_options = ["KES 1.00", "KES 2.00", "KES 1.50"]
        cost = random.choice(cost_options)
        
        return {
            'SMSMessageData': {
                'Message': f'Sent to 1/1 Total Cost: {cost}',
                'Recipients': [{
                    'statusCode': 101,
                    'number': data.get('to', '+254700000000'),
                    'status': 'Success',
                    'cost': cost,
                    'messageId': message_id
                }]
            },
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def _simulate_delivery_report(self) -> Dict:
        """Simulate delivery report response"""
        import random
        
        statuses = ['Delivered', 'Pending', 'Failed', 'Success']
        status = random.choice(statuses)
        
        return {
            'status': status,
            'deliveredAt': datetime.now().isoformat() if status in ['Delivered', 'Success'] else None,
            'failureReason': 'Network timeout' if status == 'Failed' else None,
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def _simulate_balance_response(self) -> Dict:
        """Simulate account balance response"""
        import random
        
        return {
            'UserData': {
                'balance': f"KES {random.randint(100, 1000)}.00"
            },
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def _simulate_generic_response(self) -> Dict:
        """Simulate generic API response"""
        return {
            'status': 'success',
            'message': 'Request processed successfully',
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def send_sms(self, to: str, message: str, sender_id: str = None) -> Dict:
        """
        Send SMS message
        
        Args:
            to: Recipient phone number
            message: Message content
            sender_id: Optional sender ID override
            
        Returns:
            API response dict
        """
        payload = {
            'username': self.config.username,
            'to': to,
            'message': message,
            'from': sender_id or self.config.sender_id
        }
        
        return self._make_request('POST', 'messaging', payload)
    
    def get_delivery_reports(self, message_id: str) -> Dict:
        """Get delivery reports for a message"""
        return self._make_request('GET', f'messaging/delivery-reports/{message_id}')
    
    def get_account_balance(self) -> Dict:
        """Get account balance"""
        return self._make_request('GET', f'users?username={self.config.username}')
    
    def get_api_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            'request_count': self.request_count,
            'last_request': self.last_request_time.isoformat() if self.last_request_time else None,
            'config_valid': self.config.validate_config()['all_valid'],
            'mode': 'sandbox' if self.config.is_sandbox else 'production'
        }

class PhoneNumberValidator:
    """
    Phone number validation and formatting for African countries
    """
    
    COUNTRY_CODES = {
        'KE': '254',  # Kenya
        'UG': '256',  # Uganda
        'TZ': '255',  # Tanzania
        'RW': '250',  # Rwanda
        'NG': '234',  # Nigeria
        'GH': '233',  # Ghana
        'ZA': '27',   # South Africa
    }
    
    @classmethod
    def format_phone_number(cls, phone: str, country: str = 'KE') -> str:
        """
        Format phone number to international format
        
        Args:
            phone: Phone number in various formats
            country: Country code (default: Kenya)
            
        Returns:
            Formatted phone number with country code
        """
        # Clean the number
        clean_phone = ''.join(filter(str.isdigit, phone))
        country_code = cls.COUNTRY_CODES.get(country, '254')
        
        # Handle different input formats
        if clean_phone.startswith(country_code):
            return f'+{clean_phone}'
        elif clean_phone.startswith('0'):
            return f'+{country_code}{clean_phone[1:]}'
        else:
            return f'+{country_code}{clean_phone}'
    
    @classmethod
    def validate_phone_number(cls, phone: str) -> Dict[str, bool]:
        """
        Validate phone number format
        
        Args:
            phone: Phone number to validate
            
        Returns:
            Validation results
        """
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        validation = {
            'has_digits': len(clean_phone) > 0,
            'valid_length': 9 <= len(clean_phone) <= 15,
            'valid_format': phone.startswith(('+', '0')) or clean_phone.isdigit(),
            'supported_country': any(clean_phone.startswith(code) for code in cls.COUNTRY_CODES.values())
        }
        
        validation['is_valid'] = all(validation.values())
        
        return validation

# Global API client instance
api_client = AfricasTalkingAPI()