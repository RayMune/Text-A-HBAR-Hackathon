"""
HBAR and Token Management Module
This module handles Hedera HBAR transactions, token transfers, and wallet management
integrated with SMS notifications.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid
import random

# Hedera SDK imports
try:
    from hedera import (
        Client, AccountId, PrivateKey, TokenId, 
        TransferTransaction, Hbar, AccountBalanceQuery,
        TokenAssociateTransaction, TokenCreateTransaction
    )
    HEDERA_AVAILABLE = True
except ImportError:
    logging.warning("Hedera SDK not available - using simulation mode")
    HEDERA_AVAILABLE = False

class HederaConfig:
    """
    Configuration management for Hedera network integration
    """
    
    def __init__(self):
        # Load Hedera configuration from environment
        self.my_account_id = os.getenv('MY_ACCOUNT_ID', '0.0.1001')
        self.my_private_key = os.getenv('MY_PRIVATE_KEY', 'your_private_key_here')
        self.token_id = os.getenv('TOKEN_ID', '0.0.2001')
        
        # Network configuration
        self.network = os.getenv('HEDERA_NETWORK', 'testnet')  # testnet or mainnet
        self.memo_prefix = "TextAHBAR-"
        
        # Transaction settings
        self.max_transaction_fee = Hbar(2) if HEDERA_AVAILABLE else "2 HBAR"
        self.transaction_timeout = 30  # seconds
        
        logging.info(f"Hedera configured - Network: {self.network}, Account: {self.my_account_id}")
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate Hedera configuration"""
        validation = {
            'account_id_set': bool(self.my_account_id and self.my_account_id != 'your_account_here'),
            'private_key_set': bool(self.my_private_key and self.my_private_key != 'your_private_key_here'),
            'token_id_set': bool(self.token_id and self.token_id != 'your_token_here'),
            'sdk_available': HEDERA_AVAILABLE,
            'network_valid': self.network in ['testnet', 'mainnet']
        }
        
        validation['all_valid'] = all(validation.values())
        return validation

class HederaTokenManager:
    """
    Manages Hedera token operations including transfers and balance queries
    """
    
    def __init__(self):
        self.config = HederaConfig()
        self.client = None
        self.transaction_history = []
        
        if HEDERA_AVAILABLE and self.config.validate_config()['all_valid']:
            self._initialize_client()
        else:
            logging.warning("Using Hedera simulation mode - check configuration")
    
    def _initialize_client(self):
        """Initialize Hedera client with proper network and credentials"""
        try:
            if self.config.network == 'testnet':
                self.client = Client.forTestnet()
            else:
                self.client = Client.forMainnet()
            
            # Set operator account
            account_id = AccountId.fromString(self.config.my_account_id)
            private_key = PrivateKey.fromString(self.config.my_private_key)
            
            self.client.setOperator(account_id, private_key)
            
            logging.info(f"✅ Hedera client initialized for {self.config.network}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Hedera client: {e}")
            self.client = None
    
    def transfer_tokens(self, recipient_account: str, amount: int, memo: str = None) -> Dict:
        """
        Transfer tokens to a recipient account
        
        Args:
            recipient_account: Hedera account ID (e.g., "0.0.1234")
            amount: Number of tokens to transfer
            memo: Optional transaction memo
            
        Returns:
            Transaction result dictionary
        """
        try:
            if not self.client:
                return self._simulate_token_transfer(recipient_account, amount, memo)
            
            # Real Hedera transaction
            recipient_id = AccountId.fromString(recipient_account)
            sender_id = AccountId.fromString(self.config.my_account_id)
            token_id = TokenId.fromString(self.config.token_id)
            
            transaction_memo = f"{self.config.memo_prefix}{memo or 'Token transfer'}"
            
            logging.info(f"🚀 Initiating token transfer: {amount} tokens to {recipient_account}")
            
            # Create transfer transaction
            transfer_tx = (
                TransferTransaction()
                .addTokenTransfer(token_id, sender_id, -amount)
                .addTokenTransfer(token_id, recipient_id, amount)
                .setTransactionMemo(transaction_memo)
                .setMaxTransactionFee(self.config.max_transaction_fee)
            )
            
            # Execute transaction
            tx_response = transfer_tx.execute(self.client)
            receipt = tx_response.getReceipt(self.client)
            
            transaction_id = str(tx_response.transactionId)
            status = str(receipt.status)
            
            # Log transaction
            tx_record = {
                'type': 'token_transfer',
                'transaction_id': transaction_id,
                'recipient': recipient_account,
                'amount': amount,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'memo': transaction_memo,
                'network_fee': None  # Would get from transaction record
            }
            
            self.transaction_history.append(tx_record)
            
            logging.info(f"✅ Token transfer completed - TX ID: {transaction_id[:20]}...")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': status,
                'recipient': recipient_account,
                'amount': amount,
                'memo': transaction_memo,
                'timestamp': datetime.now().isoformat(),
                'explorer_url': self._get_explorer_url(transaction_id)
            }
            
        except Exception as e:
            logging.error(f"❌ Token transfer failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient_account,
                'amount': amount,
                'timestamp': datetime.now().isoformat()
            }
    
    def _simulate_token_transfer(self, recipient_account: str, amount: int, memo: str = None) -> Dict:
        """Simulate token transfer for demo purposes"""
        import time
        import random
        
        # Simulate processing delay
        time.sleep(random.uniform(1.0, 3.0))
        
        # Generate mock transaction ID
        transaction_id = f"0.0.{random.randint(1000, 9999)}@{int(datetime.now().timestamp())}.{random.randint(100000000, 999999999)}"
        
        # Simulate success (90% success rate)
        success = random.random() > 0.1
        
        if success:
            tx_record = {
                'type': 'token_transfer_simulation',
                'transaction_id': transaction_id,
                'recipient': recipient_account,
                'amount': amount,
                'status': 'SUCCESS',
                'timestamp': datetime.now().isoformat(),
                'memo': memo or 'Simulated transfer',
                'network': self.config.network
            }
            
            self.transaction_history.append(tx_record)
            
            logging.info(f"✅ Simulated token transfer: {amount} tokens to {recipient_account}")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': 'SUCCESS',
                'recipient': recipient_account,
                'amount': amount,
                'memo': memo or 'Simulated transfer',
                'timestamp': datetime.now().isoformat(),
                'explorer_url': self._get_explorer_url(transaction_id),
                'simulation': True
            }
        else:
            error_messages = [
                "Insufficient token balance",
                "Account not associated with token",
                "Network congestion",
                "Invalid recipient account"
            ]
            error = random.choice(error_messages)
            
            logging.error(f"❌ Simulated token transfer failed: {error}")
            
            return {
                'success': False,
                'error': error,
                'recipient': recipient_account,
                'amount': amount,
                'timestamp': datetime.now().isoformat(),
                'simulation': True
            }
    
    def get_account_balance(self, account_id: str = None) -> Dict:
        """
        Get HBAR and token balance for an account
        
        Args:
            account_id: Account to query (defaults to operator account)
            
        Returns:
            Balance information dictionary
        """
        try:
            target_account = account_id or self.config.my_account_id
            
            if not self.client:
                return self._simulate_balance_query(target_account)
            
            # Real balance query
            account = AccountId.fromString(target_account)
            balance_query = AccountBalanceQuery().setAccountId(account)
            balance = balance_query.execute(self.client)
            
            # Get token balance if token is associated
            token_balance = 0
            if hasattr(balance, 'tokens') and self.config.token_id:
                token_id = TokenId.fromString(self.config.token_id)
                token_balance = balance.tokens.get(token_id, 0)
            
            return {
                'success': True,
                'account_id': target_account,
                'hbar_balance': str(balance.hbars),
                'token_balance': token_balance,
                'token_id': self.config.token_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Balance query failed for {target_account}: {e}")
            return {
                'success': False,
                'error': str(e),
                'account_id': target_account,
                'timestamp': datetime.now().isoformat()
            }
    
    def _simulate_balance_query(self, account_id: str) -> Dict:
        """Simulate balance query for demo purposes"""
        import random
        
        hbar_balance = round(random.uniform(10.0, 1000.0), 2)
        token_balance = random.randint(0, 10000)
        
        return {
            'success': True,
            'account_id': account_id,
            'hbar_balance': f"{hbar_balance} ℏ",
            'token_balance': token_balance,
            'token_id': self.config.token_id,
            'timestamp': datetime.now().isoformat(),
            'simulation': True
        }
    
    def _get_explorer_url(self, transaction_id: str) -> str:
        """Get blockchain explorer URL for transaction"""
        if self.config.network == 'mainnet':
            return f"https://hashscan.io/mainnet/transaction/{transaction_id}"
        else:
            return f"https://hashscan.io/testnet/transaction/{transaction_id}"
    
    def get_transaction_history(self, limit: int = 10) -> List[Dict]:
        """Get recent transaction history"""
        return self.transaction_history[-limit:] if self.transaction_history else []
    
    def validate_account_id(self, account_id: str) -> bool:
        """
        Validate Hedera account ID format
        
        Args:
            account_id: Account ID to validate (e.g., "0.0.1234")
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        
        # Hedera account ID pattern: 0.0.XXXXX
        pattern = r'^0\.\d+\.\d+$'
        return bool(re.match(pattern, account_id))

class IntegratedTransactionService:
    """
    Integrated service that combines HBAR transactions with SMS notifications
    """
    
    def __init__(self):
        self.token_manager = HederaTokenManager()
        
        # Import SMS service (will be created)
        try:
            from sms_service import sms_service
            self.sms_service = sms_service
            self.sms_enabled = True
        except ImportError:
            logging.warning("SMS service not available")
            self.sms_enabled = False
    
    def process_stock_purchase(self, recipient_phone: str, recipient_account: str, 
                             stock_name: str, quantity: int, price: float) -> Dict:
        """
        Process complete stock purchase: transfer tokens and send SMS notifications
        
        Args:
            recipient_phone: Phone number for SMS notifications
            recipient_account: Hedera account ID for token delivery
            stock_name: Name of purchased stock
            quantity: Number of shares/tokens
            price: Total purchase price
            
        Returns:
            Combined transaction result
        """
        try:
            logging.info(f"Processing stock purchase: {quantity} {stock_name} for {recipient_phone}")
            
            # Generate transaction reference
            transaction_ref = f"STOCK_{uuid.uuid4().hex[:8].upper()}"
            
            # Step 1: Transfer tokens to recipient account
            memo = f"Stock purchase: {quantity} {stock_name}"
            token_result = self.token_manager.transfer_tokens(
                recipient_account, quantity, memo
            )
            
            result = {
                'transaction_reference': transaction_ref,
                'stock_name': stock_name,
                'quantity': quantity,
                'price': price,
                'recipient_phone': recipient_phone,
                'recipient_account': recipient_account,
                'token_transfer': token_result,
                'sms_notifications': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Step 2: Send SMS notifications if enabled
            if self.sms_enabled and token_result['success']:
                # Stock purchase confirmation SMS
                sms_result1 = self.sms_service.notify_stock_purchase(
                    recipient_phone, stock_name, quantity, price, transaction_ref
                )
                result['sms_notifications'].append({
                    'type': 'purchase_confirmation',
                    'result': sms_result1
                })
                
                # Token delivery confirmation SMS
                sms_result2 = self.sms_service.notify_token_transfer(
                    recipient_phone, quantity, recipient_account, token_result['transaction_id']
                )
                result['sms_notifications'].append({
                    'type': 'token_delivery',
                    'result': sms_result2
                })
                
                logging.info(f"SMS notifications sent for stock purchase {transaction_ref}")
            
            result['success'] = token_result['success']
            result['overall_status'] = 'completed' if token_result['success'] else 'failed'
            
            return result
            
        except Exception as e:
            logging.error(f"Stock purchase processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_account_summary(self, account_id: str, phone_number: str = None) -> Dict:
        """
        Get comprehensive account summary including balances and recent activity
        
        Args:
            account_id: Hedera account ID
            phone_number: Associated phone number
            
        Returns:
            Account summary dictionary
        """
        balance_info = self.token_manager.get_account_balance(account_id)
        transaction_history = self.token_manager.get_transaction_history()
        
        summary = {
            'account_id': account_id,
            'phone_number': phone_number,
            'balance_info': balance_info,
            'recent_transactions': transaction_history,
            'account_status': 'active' if balance_info['success'] else 'inactive',
            'last_activity': transaction_history[-1]['timestamp'] if transaction_history else None,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary

# Global integrated service instance
transaction_service = IntegratedTransactionService()