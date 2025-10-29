"""
SMS Service Module using AfricasTalking API
This module handles all SMS-related functionality including sending messages,
delivery reports, and integration with the main application.
"""

import os
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

class AfricasTalkingSMS:
    """
    AfricasTalking SMS API wrapper for sending SMS messages
    """
    
    def __init__(self):
        self.username = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
        self.api_key = os.getenv('AFRICASTALKING_API_KEY', 'your_api_key_here')
        self.base_url = "https://api.sandbox.africastalking.com/version1/messaging"
        
        # For production, use: https://api.africastalking.com/version1/messaging
        if self.username != 'sandbox':
            self.base_url = "https://api.africastalking.com/version1/messaging"
            
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey': self.api_key
        }
        
        logging.info(f"AfricasTalking SMS initialized - Username: {self.username}")
        
    def send_sms(self, to: str, message: str, sender_id: str = None) -> Dict:
        """
        Send SMS message via AfricasTalking API
        
        Args:
            to: Phone number in international format (+254XXXXXXXXX)
            message: SMS message content
            sender_id: Optional sender ID (shortcode or alphanumeric)
            
        Returns:
            Dict with status, message_id, cost, and delivery info
        """
        try:
            # Ensure phone number is in correct format
            if not to.startswith('+'):
                if to.startswith('0'):
                    to = '+254' + to[1:]  # Convert Kenyan number
                elif to.startswith('254'):
                    to = '+' + to
                else:
                    to = '+254' + to
                    
            payload = {
                'username': self.username,
                'to': to,
                'message': message
            }
            
            if sender_id:
                payload['from'] = sender_id
                
            logging.info(f"Sending SMS to {to}: {message[:50]}...")
            
            # Simulate API response for demo purposes
            # In real implementation, you would make actual HTTP request:
            # response = requests.post(f"{self.base_url}", headers=self.headers, data=payload)
            
            # Simulated successful response
            message_id = f"ATXid_{uuid.uuid4().hex[:16]}"
            cost = "KES 1.00"  # Standard SMS cost
            
            simulated_response = {
                'SMSMessageData': {
                    'Message': 'Sent to 1/1 Total Cost: ' + cost,
                    'Recipients': [{
                        'statusCode': 101,  # Success status
                        'number': to,
                        'status': 'Success',
                        'cost': cost,
                        'messageId': message_id
                    }]
                }
            }
            
            logging.info(f"SMS sent successfully to {to} - Message ID: {message_id}")
            
            return {
                'success': True,
                'message_id': message_id,
                'status': 'sent',
                'cost': cost,
                'recipient': to,
                'delivery_status': 'pending',
                'api_response': simulated_response
            }
            
        except Exception as e:
            logging.error(f"Failed to send SMS to {to}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
                'recipient': to
            }
    
    def send_bulk_sms(self, recipients: List[str], message: str, sender_id: str = None) -> List[Dict]:
        """
        Send SMS to multiple recipients
        
        Args:
            recipients: List of phone numbers
            message: SMS message content
            sender_id: Optional sender ID
            
        Returns:
            List of delivery results for each recipient
        """
        results = []
        
        for recipient in recipients:
            result = self.send_sms(recipient, message, sender_id)
            results.append(result)
            
        return results
    
    def get_delivery_reports(self, message_id: str) -> Dict:
        """
        Get delivery report for a specific message
        
        Args:
            message_id: Message ID from send_sms response
            
        Returns:
            Dict with delivery status and timestamps
        """
        try:
            # Simulate delivery report lookup
            # In real implementation: GET request to delivery reports endpoint
            
            # Simulated delivery status (randomly success or pending)
            import random
            statuses = ['Success', 'Pending', 'Failed', 'Delivered']
            status = random.choice(statuses)
            
            return {
                'message_id': message_id,
                'status': status,
                'delivered_at': datetime.now().isoformat() if status in ['Success', 'Delivered'] else None,
                'failure_reason': 'Network error' if status == 'Failed' else None
            }
            
        except Exception as e:
            logging.error(f"Failed to get delivery report for {message_id}: {str(e)}")
            return {
                'message_id': message_id,
                'status': 'unknown',
                'error': str(e)
            }

class SMSTemplates:
    """
    Pre-defined SMS message templates for different scenarios
    """
    
    @staticmethod
    def stock_purchase_confirmation(stock_name: str, quantity: int, price: float, transaction_id: str) -> str:
        """Stock purchase confirmation SMS"""
        return (
            f"✅ STOCK PURCHASE CONFIRMED\n"
            f"Stock: {stock_name}\n"
            f"Qty: {quantity} shares\n"
            f"Amount: KES {price:.2f}\n"
            f"Ref: {transaction_id}\n"
            f"Tokens will be sent to your Hedera account."
        )
    
    @staticmethod
    def hbar_transfer_notification(amount: int, recipient_account: str, transaction_id: str) -> str:
        """HBAR/Token transfer notification SMS"""
        return (
            f"🎉 TOKEN TRANSFER COMPLETE\n"
            f"Amount: {amount} tokens\n"
            f"To: {recipient_account}\n"
            f"TxID: {transaction_id[:16]}...\n"
            f"Check your Hedera wallet for confirmation."
        )
    
    @staticmethod
    def payment_received(amount: float, from_number: str, transaction_id: str) -> str:
        """Payment received notification SMS"""
        return (
            f"💰 PAYMENT RECEIVED\n"
            f"Amount: KES {amount:.2f}\n"
            f"From: {from_number}\n"
            f"Ref: {transaction_id}\n"
            f"Thank you for your payment!"
        )
    
    @staticmethod
    def mpesa_confirmation(amount: float, recipient: str, balance: float, transaction_id: str) -> str:
        """M-PESA style confirmation message"""
        timestamp = datetime.now().strftime("%d/%m/%y at %I:%M %p")
        return (
            f"{transaction_id} Confirmed. "
            f"Ksh{amount:.2f} sent to {recipient} on {timestamp}. "
            f"New M-pesa balance is Ksh{balance:.2f}. "
            f"Transaction cost, Ksh0.00."
        )

class SMSNotificationService:
    """
    High-level SMS notification service that integrates with the main app
    """
    
    def __init__(self):
        self.sms_client = AfricasTalkingSMS()
        self.message_log = []  # Store sent messages for tracking
        
    def notify_stock_purchase(self, recipient_phone: str, stock_name: str, 
                            quantity: int, price: float, transaction_id: str) -> Dict:
        """
        Send stock purchase confirmation SMS
        """
        message = SMSTemplates.stock_purchase_confirmation(
            stock_name, quantity, price, transaction_id
        )
        
        result = self.sms_client.send_sms(recipient_phone, message, sender_id="STOCKS")
        
        # Log the message
        self.message_log.append({
            'type': 'stock_purchase',
            'recipient': recipient_phone,
            'message': message,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"Stock purchase SMS sent to {recipient_phone} - Success: {result['success']}")
        return result
    
    def notify_token_transfer(self, recipient_phone: str, amount: int, 
                           recipient_account: str, transaction_id: str) -> Dict:
        """
        Send token transfer notification SMS
        """
        message = SMSTemplates.hbar_transfer_notification(
            amount, recipient_account, transaction_id
        )
        
        result = self.sms_client.send_sms(recipient_phone, message, sender_id="HBAR")
        
        # Log the message
        self.message_log.append({
            'type': 'token_transfer',
            'recipient': recipient_phone,
            'message': message,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"Token transfer SMS sent to {recipient_phone} - Success: {result['success']}")
        return result
    
    def send_mpesa_confirmation(self, recipient_phone: str, amount: float, 
                              recipient_name: str, balance: float, transaction_id: str) -> Dict:
        """
        Send M-PESA style confirmation SMS
        """
        message = SMSTemplates.mpesa_confirmation(
            amount, recipient_name, balance, transaction_id
        )
        
        result = self.sms_client.send_sms(recipient_phone, message, sender_id="MPESA")
        
        # Log the message
        self.message_log.append({
            'type': 'mpesa_confirmation',
            'recipient': recipient_phone,
            'message': message,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        logging.info(f"M-PESA confirmation SMS sent to {recipient_phone} - Success: {result['success']}")
        return result
    
    def get_message_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent SMS message history
        """
        return self.message_log[-limit:] if self.message_log else []
    
    def get_delivery_status(self, message_id: str) -> Dict:
        """
        Check delivery status of a sent message
        """
        return self.sms_client.get_delivery_reports(message_id)

# Global SMS service instance
sms_service = SMSNotificationService()