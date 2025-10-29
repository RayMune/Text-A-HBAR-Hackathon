"""
TextAHBAR API Client Library
Python client for interacting with the TextAHBAR backend API
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Union

class TextAHBARClient:
    """
    Python client for TextAHBAR API
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = None):
        """
        Initialize the API client
        
        Args:
            base_url: Base URL of the TextAHBAR API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TextAHBAR-Client/1.0'
        })
        
        if api_key:
            self.session.headers['X-API-Key'] = api_key
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload for POST requests
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # === Service Information ===
    
    def get_service_info(self) -> Dict:
        """Get service information and available endpoints"""
        return self._make_request('GET', '/')
    
    def get_api_docs(self) -> Dict:
        """Get comprehensive API documentation"""
        return self._make_request('GET', '/api/docs')
    
    def get_dashboard(self) -> Dict:
        """Get service status dashboard"""
        return self._make_request('GET', '/api/dashboard')
    
    # === SMS Operations ===
    
    def send_sms(self, to: str, message: str, sender_id: str = 'TEXTAHBAR') -> Dict:
        """
        Send SMS message
        
        Args:
            to: Recipient phone number
            message: SMS content
            sender_id: Sender ID for the SMS
            
        Returns:
            SMS sending result
        """
        data = {
            'to': to,
            'message': message,
            'sender_id': sender_id
        }
        
        return self._make_request('POST', '/api/sms/send', data)
    
    def get_sms_status(self) -> Dict:
        """Get SMS service status and statistics"""
        return self._make_request('GET', '/sms_status')
    
    def send_test_sms(self, phone: str, message: str = None) -> Dict:
        """
        Send test SMS message
        
        Args:
            phone: Test phone number
            message: Optional custom message
            
        Returns:
            Test result
        """
        data = {
            'phone': phone,
            'message': message or f'Test message from TextAHBAR at {datetime.now().strftime("%H:%M:%S")}'
        }
        
        return self._make_request('POST', '/send_test_sms', data)
    
    # === Stock Operations ===
    
    def get_stocks(self) -> Dict:
        """Get list of available stocks"""
        return self._make_request('GET', '/api/stocks/list')
    
    def get_stock_price(self, ticker: str) -> Dict:
        """
        Get current stock price
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Stock price information
        """
        return self._make_request('GET', f'/api/stocks/price/{ticker.upper()}')
    
    def buy_stock(self, ticker: str, quantity: int, phone_number: str, hedera_account: str) -> Dict:
        """
        Purchase stock with HBAR tokens
        
        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares to buy
            phone_number: Phone for SMS notifications
            hedera_account: Hedera account for token delivery
            
        Returns:
            Purchase result
        """
        data = {
            'ticker': ticker,
            'quantity': quantity,
            'phone_number': phone_number,
            'hedera_account': hedera_account
        }
        
        return self._make_request('POST', '/api/stocks/buy', data)
    
    # === Hedera Operations ===
    
    def get_hedera_balance(self, account_id: str) -> Dict:
        """
        Get Hedera account balance
        
        Args:
            account_id: Hedera account ID (e.g., "0.0.1234")
            
        Returns:
            Account balance information
        """
        return self._make_request('GET', f'/api/hedera/balance/{account_id}')
    
    def transfer_hbar(self, to_account: str, amount: int, memo: str = None, notify_phone: str = None) -> Dict:
        """
        Transfer HBAR tokens
        
        Args:
            to_account: Recipient Hedera account ID
            amount: Number of tokens to transfer
            memo: Optional transaction memo
            notify_phone: Optional phone for SMS notification
            
        Returns:
            Transfer result
        """
        data = {
            'to_account': to_account,
            'amount': amount
        }
        
        if memo:
            data['memo'] = memo
        if notify_phone:
            data['notify_phone'] = notify_phone
        
        return self._make_request('POST', '/api/hedera/transfer', data)
    
    def get_hedera_status(self) -> Dict:
        """Get Hedera service status"""
        return self._make_request('GET', '/hedera_status')
    
    # === Chat Operations ===
    
    def send_chat_message(self, message: str, recipient_type: str = 'stock_trader', phone_number: str = None) -> Dict:
        """
        Send message to AI chat assistant
        
        Args:
            message: Message to send
            recipient_type: Type of recipient (stock_trader, kamba_bot, etc.)
            phone_number: Optional phone for notifications
            
        Returns:
            Chat response
        """
        data = {
            'message': message,
            'recipient_name': recipient_type,
            'convo_id': 1
        }
        
        if phone_number:
            data['phone_number'] = phone_number
        
        return self._make_request('POST', '/api/chat', data)
    
    # === Transaction Operations ===
    
    def get_transactions(self, transaction_type: str = None, limit: int = 50) -> Dict:
        """
        Get transaction history
        
        Args:
            transaction_type: Filter by transaction type
            limit: Maximum number of transactions
            
        Returns:
            Transaction history
        """
        params = f'?limit={limit}'
        if transaction_type:
            params += f'&type={transaction_type}'
        
        return self._make_request('GET', f'/api/transactions{params}')
    
    # === Utility Operations ===
    
    def validate_phone(self, phone_number: str) -> Dict:
        """
        Validate and format phone number
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Validation results
        """
        data = {'phone_number': phone_number}
        return self._make_request('POST', '/api/phone/validate', data)
    
    # === Convenience Methods ===
    
    def quick_stock_purchase(self, ticker: str, quantity: int, phone: str, account: str) -> Dict:
        """
        Simplified stock purchase with automatic notifications
        
        Args:
            ticker: Stock ticker (e.g., "SAF")
            quantity: Number of shares
            phone: Phone number for notifications
            account: Hedera account for token delivery
            
        Returns:
            Complete purchase result
        """
        # First get stock price
        price_result = self.get_stock_price(ticker)
        if not price_result.get('success'):
            return price_result
        
        stock = price_result['data']['stock']
        total_cost = stock['price'] * quantity
        
        print(f"📈 Purchasing {quantity} shares of {stock['name']}")
        print(f"💰 Total cost: KES {total_cost:.2f}")
        print(f"📱 Notifications will be sent to: {phone}")
        print(f"⚡ Tokens will be delivered to: {account}")
        
        # Execute purchase
        return self.buy_stock(ticker, quantity, phone, account)
    
    def send_notification_sms(self, phone: str, message_type: str, **kwargs) -> Dict:
        """
        Send formatted notification SMS
        
        Args:
            phone: Recipient phone number
            message_type: Type of notification (stock_purchase, token_transfer, etc.)
            **kwargs: Additional parameters for message formatting
            
        Returns:
            SMS sending result
        """
        # Format message based on type
        if message_type == 'stock_purchase':
            message = f"✅ STOCK PURCHASE CONFIRMED\nStock: {kwargs.get('stock_name')}\nQty: {kwargs.get('quantity')} shares\nAmount: KES {kwargs.get('amount', 0):.2f}\nRef: {kwargs.get('ref_id')}"
        elif message_type == 'token_transfer':
            message = f"🎉 TOKEN TRANSFER COMPLETE\nAmount: {kwargs.get('amount')} tokens\nTo: {kwargs.get('to_account')}\nTxID: {kwargs.get('tx_id', 'N/A')[:16]}..."
        else:
            message = kwargs.get('message', 'Notification from TextAHBAR')
        
        return self.send_sms(phone, message)
    
    def get_service_health(self) -> Dict:
        """
        Get overall service health status
        
        Returns:
            Health check results
        """
        results = {}
        
        # Check main service
        results['api'] = self.get_service_info()
        
        # Check SMS service
        results['sms'] = self.get_sms_status()
        
        # Check Hedera service
        results['hedera'] = self.get_hedera_status()
        
        # Check dashboard
        results['dashboard'] = self.get_dashboard()
        
        # Calculate overall health
        health_score = sum(1 for service in results.values() if service.get('success', True))
        total_services = len(results)
        
        return {
            'overall_health': 'healthy' if health_score == total_services else 'degraded',
            'health_score': f"{health_score}/{total_services}",
            'services': results,
            'timestamp': datetime.now().isoformat()
        }

# === Usage Examples ===

def example_usage():
    """
    Example usage of the TextAHBAR API client
    """
    # Initialize client
    client = TextAHBARClient("http://localhost:8080")
    
    # Check service status
    print("🚀 Checking service status...")
    health = client.get_service_health()
    print(f"Health: {health['overall_health']} ({health['health_score']})")
    
    # Get available stocks
    print("\n📈 Getting available stocks...")
    stocks = client.get_stocks()
    if stocks.get('success'):
        print(f"Found {stocks['data']['total_count']} stocks")
    
    # Get specific stock price
    print("\n💰 Getting Safaricom price...")
    saf_price = client.get_stock_price("SAF")
    if saf_price.get('success'):
        stock = saf_price['data']['stock']
        print(f"{stock['name']}: KES {stock['price']:.2f}")
    
    # Validate phone number
    print("\n📞 Validating phone number...")
    phone_validation = client.validate_phone("+254700000000")
    if phone_validation.get('success'):
        print(f"Phone valid: {phone_validation.get('validation', {}).get('is_valid', False)}")
    
    # Send test SMS
    print("\n📱 Sending test SMS...")
    sms_result = client.send_test_sms("+254700000000")
    print(f"SMS sent: {sms_result.get('success', False)}")
    
    print("\n✅ Example completed!")

if __name__ == "__main__":
    example_usage()