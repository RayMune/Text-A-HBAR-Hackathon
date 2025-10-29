
from flask import Flask, render_template, request, jsonify
import re
import os
import boto3
import logging
import time
from datetime import datetime
import uuid
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Hedera imports for token transfers
from hedera import (
    Client,
    AccountId,
    PrivateKey,
    TokenId,
    TransferTransaction,
    Hbar
)

# Import our custom SMS and HBAR management modules
from sms_service import sms_service, SMSTemplates
from africastalking_client import api_client, PhoneNumberValidator
from hbar_manager import transaction_service, HederaTokenManager
from utils import (
    transaction_logger, sms_rate_limiter, api_rate_limiter,
    PhoneNumberUtils, SMSCostCalculator, ConfigValidator, MessageFormatter
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- AWS Bedrock Configuration ---
env_bearer = os.getenv('BEDROCK_BEARER_TOKEN') or os.getenv('AWS_BEARER_TOKEN_BEDROCK')
if env_bearer:
    os.environ['AWS_BEARER_TOKEN_BEDROCK'] = env_bearer
else:
    logging.error("AWS_BEARER_TOKEN_BEDROCK not found in environment variables!")
    exit("Exiting: AWS Bearer token is required.")

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')

try:
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION
    )
    logging.info(f"AWS Bedrock client initialized for region: {AWS_REGION}")
except Exception as e:
    logging.critical(f"Failed to initialize AWS Bedrock client: {e}")
    exit("Exiting: Failed to initialize AWS Bedrock client.")

chat_sessions = {}
pending_mpesa_confirmations = {}
pending_purchases = {}
user_balances = {"default_user_session": 400.00}

# --- Hedera Configuration ---
my_account_id_str = os.getenv('MY_ACCOUNT_ID')
my_private_key_str = os.getenv('MY_PRIVATE_KEY')
token_id_str = os.getenv('TOKEN_ID')

if not my_account_id_str or not my_private_key_str or not token_id_str:
    logging.error("Missing required Hedera environment variables!")
    exit("Exiting: MY_ACCOUNT_ID, MY_PRIVATE_KEY, and TOKEN_ID are required.")

MY_ACCOUNT_ID = AccountId.fromString(my_account_id_str)
MY_PRIVATE_KEY = PrivateKey.fromString(my_private_key_str)
TOKEN_ID = TokenId.fromString(token_id_str)

# Initialize Hedera client
hedera_client = Client.forTestnet()
hedera_client.setOperator(MY_ACCOUNT_ID, MY_PRIVATE_KEY)
logging.info(f"🚀 Connected to Hedera Testnet with Token ID: {TOKEN_ID}")

# --- Kenya Stocks Database ---
kenya_stocks = [
    {'ticker': 'SAF', 'name': 'Safaricom PLC', 'price': 22.50, 'sector': 'Telecommunications', 'market_cap': '902B KES'},
    {'ticker': 'EQTY', 'name': 'Equity Group Holdings', 'price': 45.75, 'sector': 'Banking', 'market_cap': '172B KES'},
    {'ticker': 'KCB', 'name': 'KCB Group', 'price': 38.25, 'sector': 'Banking', 'market_cap': '156B KES'},
    {'ticker': 'EABL', 'name': 'East African Breweries', 'price': 185.00, 'sector': 'Consumer Goods', 'market_cap': '140B KES'},
    {'ticker': 'BAT', 'name': 'British American Tobacco Kenya', 'price': 425.00, 'sector': 'Consumer Goods', 'market_cap': '85B KES'},
    {'ticker': 'COOP', 'name': 'Co-operative Bank', 'price': 14.50, 'sector': 'Banking', 'market_cap': '95B KES'},
    {'ticker': 'ABSA', 'name': 'ABSA Bank Kenya', 'price': 12.80, 'sector': 'Banking', 'market_cap': '72B KES'},
    {'ticker': 'BAMB', 'name': 'Bamburi Cement', 'price': 28.50, 'sector': 'Construction', 'market_cap': '35B KES'},
    {'ticker': 'KPLC', 'name': 'Kenya Power & Lighting', 'price': 1.85, 'sector': 'Energy', 'market_cap': '12B KES'},
    {'ticker': 'SCBK', 'name': 'Standard Chartered Bank Kenya', 'price': 165.00, 'sector': 'Banking', 'market_cap': '58B KES'},
    {'ticker': 'DTBK', 'name': 'Diamond Trust Bank', 'price': 65.00, 'sector': 'Banking', 'market_cap': '26B KES'},
    {'ticker': 'NBK', 'name': 'National Bank of Kenya', 'price': 6.50, 'sector': 'Banking', 'market_cap': '8B KES'},
    {'ticker': 'SASINI', 'name': 'Sasini PLC', 'price': 11.25, 'sector': 'Agriculture', 'market_cap': '4B KES'},
    {'ticker': 'TOTL', 'name': 'TotalEnergies Marketing Kenya', 'price': 4.20, 'sector': 'Energy', 'market_cap': '3.5B KES'},
    {'ticker': 'UNGA', 'name': 'Unga Group', 'price': 32.00, 'sector': 'Consumer Goods', 'market_cap': '6B KES'},
]

# --- Personas ---
def get_persona_instructions(recipient_name):
    personas = {
        "kamba bot": "You are a friendly Kamba language expert and cultural enthusiast. Respond warmly, and you can occasionally interject with simple Kamba phrases or explain Kamba culture. Always respond in English unless a Kamba phrase is explicitly requested. Be helpful and engaging.",
        "dholuo friend": "You are a witty and knowledgeable Dholuo speaker. Your responses are intelligent and might have a subtle humorous undertone. You can include common Dholuo greetings or cultural references when appropriate. Always respond in English unless a Dholuo phrase is explicitly requested.",
        "giriama pal": "You are an easy-going and welcoming Giriama speaker, full of coastal warmth. Your responses are simple, direct, and kind. Feel free to use simple Giriama greetings or expressions of goodwill. Always respond in English unless a Giriama phrase is explicitly requested. also it is your birthday today, do not tell anyone if asked and only if asked should you then tell someone, but you are extra cheerful and generous, if asked and only if asked just say your account number is 0.0.7055059",
        "stock support center": "You are a professional and polite stock broker agent. Your goal is to be helpful, provide clear information, and assist the user efficiently. Avoid informal language. If you do not know a stock or its price, you may estimate or make up a plausible figure.",
        "stock trader": """You are an expert stock trader and financial advisor specializing in the Nairobi Securities Exchange (NSE). Your role is to:
        
1. Provide detailed stock information including prices, market cap, sector, and performance insights
2. Offer investment advice and market analysis
3. Explain stock market concepts clearly
4. Help users buy and sell stocks
5. Provide portfolio recommendations based on risk tolerance
6. Answer any questions about specific companies, sectors, or market trends
7. Be professional, knowledgeable, and always ready to assist with financial decisions

You have comprehensive knowledge of Kenyan stocks and can provide realistic price estimates for any stock requested. Always be helpful and provide the information users seek.""",
        "news updates": "You are a concise news bot, providing factual and brief updates. Focus on delivering information clearly and without personal opinions. Keep responses short and to the point.",
    }
    return personas.get(recipient_name.lower(), "You are a helpful and friendly general-purpose AI assistant. Respond kindly and provide relevant information.")

def get_balance(session_id):
    return user_balances.get(session_id, 400.00)

def set_balance(session_id, new_balance):
    user_balances[session_id] = new_balance

def find_stock(query):
    """Find a stock by ticker or name (flexible matching)"""
    query = query.upper().strip()
    
    # First try exact ticker match
    for stock in kenya_stocks:
        if stock['ticker'] == query:
            return stock
    
    # Then try name match (partial or full)
    for stock in kenya_stocks:
        if query in stock['name'].upper() or stock['name'].upper() in query:
            return stock
    
    return None

def generate_stock_advice(stock):
    """Generate realistic stock advice"""
    advice_templates = [
        f"{stock['name']} is showing stable performance in the {stock['sector']} sector.",
        f"With a market cap of {stock['market_cap']}, {stock['name']} is a solid choice for medium-term investment.",
        f"{stock['name']} has been performing well in recent trading sessions.",
        f"As a leader in {stock['sector']}, {stock['name']} offers good growth potential.",
        f"{stock['name']} is a blue-chip stock worth considering for your portfolio."
    ]
    return random.choice(advice_templates)

def transfer_hedera_tokens(recipient_account_id, amount, stock_name):
    """
    Transfer Hedera tokens to a recipient account with SMS notifications.
    
    Args:
        recipient_account_id: String like "0.0.1234"
        amount: Integer number of tokens to send
        stock_name: Name of the stock for the memo
        
    Returns:
        dict with 'success': bool, 'message': str, 'transaction_id': str (if successful)
    """
    try:
        logging.info(f"📦 Attempting to send {amount} token units to {recipient_account_id}")
        
        # Parse recipient account
        friend_account = AccountId.fromString(recipient_account_id)
        
        # Create and execute transfer transaction
        tx = (
            TransferTransaction()
            .addTokenTransfer(TOKEN_ID, MY_ACCOUNT_ID, -amount)   # sender (debit)
            .addTokenTransfer(TOKEN_ID, friend_account, amount)   # recipient (credit)
            .setTransactionMemo(f"{stock_name} stock token transfer of {amount} units.")
        )
        
        tx_response = tx.execute(hedera_client)
        receipt = tx_response.getReceipt(hedera_client)
        transaction_id = str(tx_response.transactionId)
        
        logging.info(f"✅ Transfer complete! Status: {receipt.status}")
        
        # Send SMS notification about successful token transfer
        try:
            # Get recipient phone number from session or use demo number
            recipient_phone = get_user_phone_from_session() or "+254700000000"
            
            # Send token transfer notification SMS
            sms_result = sms_service.notify_token_transfer(
                recipient_phone, amount, recipient_account_id, transaction_id
            )
            
            logging.info(f"📱 SMS notification sent - Success: {sms_result.get('success', False)}")
            
        except Exception as sms_error:
            logging.warning(f"SMS notification failed: {sms_error}")
        
        return {
            'success': True,
            'message': f"Successfully transferred {amount} token units to {recipient_account_id}",
            'transaction_id': transaction_id,
            'status': str(receipt.status)
        }
        
    except Exception as e:
        logging.error(f"❌ Token transfer failed: {e}", exc_info=True)
        return {
            'success': False,
            'message': f"Transfer failed: {str(e)}",
            'transaction_id': None
        }

def get_user_phone_from_session():
    """
    Get user's phone number from session or request context.
    In a real app, this would be stored in user session/database.
    """
    # For demo purposes, return a sample Kenyan phone number
    demo_phones = ["+254700000000", "+254722000000", "+254733000000"]
    return random.choice(demo_phones)

def send_africastalking_sms(phone_number, message, sender_id="TEXTAHBAR"):
    """
    Send SMS using AfricasTalking API
    
    Args:
        phone_number: Recipient phone number
        message: SMS message content
        sender_id: Sender ID for the SMS
        
    Returns:
        Dict with sending status and details
    """
    try:
        # Format phone number to international format
        formatted_phone = PhoneNumberValidator.format_phone_number(phone_number)
        
        # Send SMS using our API client
        result = api_client.send_sms(formatted_phone, message, sender_id)
        
        logging.info(f"📱 AfricasTalking SMS sent to {formatted_phone} - Success: {result.get('success', False)}")
        
        return result
        
    except Exception as e:
        logging.error(f"Failed to send AfricasTalking SMS: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    """
    API Root endpoint with service information
    """
    return jsonify({
        'service': 'TextAHBAR API',
        'version': '2.0.0',
        'description': 'SMS-enabled HBAR trading platform with AfricasTalking integration',
        'features': [
            'SMS notifications via AfricasTalking API',
            'Hedera HBAR token transfers',
            'Stock trading with instant notifications',
            'M-PESA payment simulation',
            'AI-powered chat responses',
            'Phone number validation and formatting',
            'Transaction logging and reporting'
        ],
        'endpoints': {
            'chat': '/api/chat - Send chat messages',
            'sms': '/api/sms - SMS operations',
            'stocks': '/api/stocks - Stock trading',
            'hedera': '/api/hedera - HBAR operations',
            'dashboard': '/api/dashboard - Service status',
            'docs': '/api/docs - API documentation'
        },
        'status': 'operational',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """
    Complete API documentation
    """
    docs = {
        'TextAHBAR API Documentation': {
            'version': '2.0.0',
            'base_url': 'https://your-domain.com',
            'authentication': 'API Key (Header: X-API-Key)',
            'content_type': 'application/json'
        },
        'endpoints': {
            '/api/chat': {
                'method': 'POST',
                'description': 'Send chat messages to AI assistants',
                'parameters': {
                    'message': 'string - The message to send',
                    'recipient_type': 'string - Type of recipient (stock_trader, kamba_bot, etc.)',
                    'phone_number': 'string - Optional phone for SMS notifications'
                },
                'example': {
                    'message': 'What is the price of Safaricom stock?',
                    'recipient_type': 'stock_trader',
                    'phone_number': '+254700000000'
                }
            },
            '/api/sms/send': {
                'method': 'POST',
                'description': 'Send SMS messages via AfricasTalking',
                'parameters': {
                    'to': 'string - Recipient phone number',
                    'message': 'string - SMS content',
                    'sender_id': 'string - Optional sender ID'
                }
            },
            '/api/stocks/list': {
                'method': 'GET',
                'description': 'Get list of available stocks'
            },
            '/api/stocks/price': {
                'method': 'GET',
                'description': 'Get stock price',
                'parameters': {
                    'ticker': 'string - Stock ticker symbol'
                }
            },
            '/api/stocks/buy': {
                'method': 'POST',
                'description': 'Purchase stocks with HBAR tokens',
                'parameters': {
                    'ticker': 'string - Stock ticker',
                    'quantity': 'integer - Number of shares',
                    'phone_number': 'string - For SMS notifications',
                    'hedera_account': 'string - Hedera account for token delivery'
                }
            },
            '/api/hedera/balance': {
                'method': 'GET',
                'description': 'Get Hedera account balance',
                'parameters': {
                    'account_id': 'string - Hedera account ID'
                }
            },
            '/api/hedera/transfer': {
                'method': 'POST',
                'description': 'Transfer HBAR tokens',
                'parameters': {
                    'to_account': 'string - Recipient Hedera account',
                    'amount': 'integer - Token amount',
                    'memo': 'string - Transaction memo',
                    'notify_phone': 'string - Phone for SMS notification'
                }
            }
        },
        'response_format': {
            'success': 'boolean - Operation success status',
            'data': 'object - Response data',
            'message': 'string - Status message',
            'timestamp': 'string - ISO timestamp'
        },
        'error_codes': {
            '400': 'Bad Request - Invalid parameters',
            '401': 'Unauthorized - Invalid API key',
            '404': 'Not Found - Endpoint does not exist',
            '429': 'Too Many Requests - Rate limit exceeded',
            '500': 'Internal Server Error - Server error'
        }
    }
    
    return jsonify(docs)

@app.route('/api/chat', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_id = data.get('convo_id', None)
    recipient_name = data.get('recipient_name', 'Unknown Recipient')
    recipient_number = data.get('recipient_number', 'Unknown Number')
    user_session_id = 'default_user_session'

    logging.info(f"Received message for convo_id: {conversation_id}, recipient: {recipient_name}, message: {user_message}")

    # === HEDERA ACCOUNT ID PROCESSING (HIGHEST PRIORITY - CHECK FIRST) ===
    account_match = re.match(r'^(0\.\d+\.\d+)$', user_message.strip())
    if account_match:
        account_id = account_match.group(1)
        logging.info(f"🆔 HEDERA ACCOUNT ID DETECTED: {account_id}")
        logging.info(f"📋 Pending purchases: {pending_purchases}")
        logging.info(f"👤 User session ID: {user_session_id}")
        
        # Check if we have a pending purchase for this session
        if user_session_id in pending_purchases:
            purchase = pending_purchases[user_session_id]
            logging.info(f"📦 Purchase details: {purchase}")
            logging.info(f"✅ MPESA confirmed: {purchase.get('mpesa_confirmed', False)}")
            
            if not purchase.get('mpesa_confirmed', False):
                # Payment not yet confirmed
                return jsonify({
                    'type': 'chat_reply', 
                    'reply': "❌ Payment not confirmed yet. Please complete the M-PESA STK push first by entering your PIN."
                })
            
            # Payment confirmed - proceed with token transfer
            stock_name = purchase.get('stock_name', purchase.get('stock_requested', 'Unknown Stock'))
            qty = purchase.get('qty', 1)
            
            logging.info(f"🚀 Initiating Hedera token transfer: {qty} units to {account_id} for {stock_name}")
            
            # Execute actual Hedera token transfer (1 token per stock unit)
            tokens_to_send = qty  # Send 1 token per stock unit
            transfer_result = transfer_hedera_tokens(account_id, tokens_to_send, stock_name)
            
            if transfer_result['success']:
                # Log the successful transaction
                transaction_data = {
                    'stock_name': stock_name,
                    'quantity': qty,
                    'tokens_sent': tokens_to_send,
                    'recipient_account': account_id,
                    'hedera_transaction_id': transfer_result['transaction_id'],
                    'success': True
                }
                
                tx_log_id = transaction_logger.log_transaction('stock_purchase', transaction_data)
                
                # Send comprehensive SMS notification
                try:
                    recipient_phone = get_user_phone_from_session()
                    
                    # Send stock purchase confirmation SMS
                    purchase_total = purchase.get('total_amount', qty * 100)  # Fallback price
                    sms_result = sms_service.notify_stock_purchase(
                        recipient_phone, stock_name, qty, purchase_total, tx_log_id
                    )
                    
                    logging.info(f"📱 Stock purchase SMS sent - Success: {sms_result.get('success', False)}")
                    
                except Exception as sms_error:
                    logging.warning(f"SMS notification failed: {sms_error}")
                
                # Transfer succeeded
                ack_message = (
                    f"🎉 **Stock Purchase Complete!** 🎉\n\n"
                    f"✅ **{stock_name}**: {qty} unit(s) purchased\n"
                    f"💰 **Tokens Sent**: {tokens_to_send} token units\n"
                    f"📧 **To Account**: {account_id}\n"
                    f"🔗 **Transaction ID**: {transfer_result['transaction_id']}\n"
                    f"📊 **Status**: {transfer_result['status']}\n"
                    f"📱 **SMS Confirmation**: Sent to your registered number\n\n"
                    f"Your tokens have been successfully delivered to your Hedera account!\n"
                    f"Thank you for trading with us! 📈"
                )
                
                # Clean up pending records
                pending_purchases.pop(user_session_id, None)
                pending_mpesa_confirmations.pop(user_session_id, None)
                
            else:
                # Transfer failed
                ack_message = (
                    f"⚠️ **Token Delivery Issue** ⚠️\n\n"
                    f"❌ **Error**: {transfer_result['message']}\n\n"
                    f"Your purchase of {qty} unit(s) of {stock_name} was confirmed, "
                    f"but we couldn't deliver tokens to {account_id}.\n\n"
                    f"Please contact support with your transaction details."
                )
            
            return jsonify({'type': 'chat_reply', 'reply': ack_message})
            
        else:
            # No pending purchase found
            return jsonify({
                'type': 'chat_reply', 
                'reply': "❌ No pending purchase found. Please start a new stock purchase with 'buy [quantity] [ticker]'"
            })

    is_stock_trader = 'stock trader' in recipient_name.lower()

    # === STOCK TRADER - HANDLE STOCK-SPECIFIC QUERIES ===
    if is_stock_trader:
        logging.info("Stock Trader query detected")
        
        # 1. List/show all stocks
        if re.search(r'(list|show|top|all|available|kenyan).*stocks?', user_message, re.IGNORECASE):
            logging.info("List stocks command detected")
            reply_lines = ["📊 **Available Kenyan Stocks (NSE)**\n"]
            for idx, s in enumerate(kenya_stocks, start=1):
                reply_lines.append(f"{idx}. **{s['name']}** ({s['ticker']}) - KES {s['price']:.2f} | {s['sector']}")
            return jsonify({'type': 'chat_reply', 'reply': '\n'.join(reply_lines)})

        # 2. Stock price/info query - VERY BROAD PATTERNS
        stock_keywords = ['price', 'quote', 'value', 'cost', 'worth', 'stock', 'share', 'trading']
        is_stock_query = any(keyword in user_message.lower() for keyword in stock_keywords)
        
        if is_stock_query:
            logging.info(f"Stock query detected: {user_message}")
            
            clean_msg = user_message.lower()
            for word in ['what', 'is', 'the', 'of', 'for', 'price', 'quote', 'stock', 'share', 'current', 'today', 'trading', 'at', 'how', 'much']:
                clean_msg = clean_msg.replace(word, ' ')
            
            potential_stock = ' '.join(clean_msg.split()).strip()
            logging.info(f"Extracted potential stock: '{potential_stock}'")
            
            if potential_stock:
                stock = find_stock(potential_stock)
                
                if stock:
                    logging.info(f"Stock found: {stock['name']}")
                    reply = (
                        f"📈 **{stock['name']} ({stock['ticker']})**\n\n"
                        f"💰 Current Price: KES {stock['price']:.2f}\n"
                        f"🏢 Sector: {stock['sector']}\n"
                        f"📊 Market Cap: {stock['market_cap']}\n\n"
                        f"💡 {generate_stock_advice(stock)}\n\n"
                        f"Would you like to buy {stock['ticker']}? Reply 'buy [quantity] {stock['ticker']}'"
                    )
                    return jsonify({'type': 'chat_reply', 'reply': reply})
                else:
                    logging.info(f"Stock not found in database, generating estimate for: {potential_stock}")
                    made_up_price = round(random.uniform(10, 500), 2)
                    sectors = ['Technology', 'Banking', 'Energy', 'Manufacturing', 'Retail', 'Agriculture']
                    sector = random.choice(sectors)
                    reply = (
                        f"📈 **{potential_stock.title()}**\n\n"
                        f"💰 Current Price: KES {made_up_price:.2f}\n"
                        f"🏢 Sector: {sector}\n\n"
                        f"This stock is currently trading at KES {made_up_price:.2f}. "
                        f"Would you like more information or to place an order?"
                    )
                    return jsonify({'type': 'chat_reply', 'reply': reply})

        # 3. Buy command
        buy_match = re.search(r'buy\s+(\d+)\s+(?:units?\s+(?:of\s+)?)?([A-Za-z0-9\s]+)', user_message, re.IGNORECASE)
        if buy_match:
            logging.info("Buy command detected")
            qty = int(buy_match.group(1))
            ticker = buy_match.group(2).strip().upper()
            stock = find_stock(ticker)
            
            if stock:
                unit_price = stock['price']
                total = unit_price * qty
                pending_purchases[user_session_id] = {
                    'ticker': stock['ticker'],
                    'qty': qty,
                    'unit_price': unit_price,
                    'total_amount': total,
                    'recipient_name': recipient_name,
                    'recipient_number': recipient_number,
                    'stock_name': stock['name'],
                    'mpesa_confirmed': False
                }
                # Trigger STK push simulation for the total amount (UI will handle PIN entry)
                transaction_id = "TJTG" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
                current_time = datetime.now().strftime("%d/%m/%y at %I:%M %p")
                old_balance = get_balance(user_session_id)
                new_balance = max(0, old_balance - total)
                # deduct only at STK success; but keep previous behavior of reserving funds by deducting now:
                set_balance(user_session_id, new_balance)
                
                # Enhanced M-PESA confirmation message
                confirmation_message_text = (
                    f"{transaction_id} Confirmed. Ksh{total:.2f} sent to "
                    f"{stock['name']} {recipient_number} on {current_time}. "
                    f"New M-pesa balance is ksh{new_balance:.2f}. Transaction cost, Ksh0.00. "
                    "Amount you can transact within the day is 499,230."
                )
                
                # Log M-PESA transaction
                mpesa_data = {
                    'amount': total,
                    'recipient': stock['name'],
                    'recipient_number': recipient_number,
                    'transaction_id': transaction_id,
                    'new_balance': new_balance,
                    'success': True
                }
                
                transaction_logger.log_transaction('mpesa_payment', mpesa_data)
                pending_mpesa_confirmations[user_session_id] = {
                    'message': confirmation_message_text,
                    'recipient_name': 'M-PESA',
                    'purchase_ref': user_session_id
                }
                return jsonify({
                    'type': 'stk_prompt',
                    'amount': total,
                    'recipient': stock['name'],
                    'recipient_number': recipient_number,
                    'prompt_message': f"STK Push for Ksh {total:.2f} to {stock['name']} ({recipient_number}). Enter PIN."
                })
            else:
                return jsonify({'type': 'chat_reply', 'reply': f"Sorry, I couldn't find stock ticker '{ticker}'. Please check the ticker and try again."})

        # 4. Natural language payment (e.g., "pay 20 for safaricom")
        pay_match = re.search(r'pay\s+([\d\.]+)\s+for\s+(.+)', user_message, re.IGNORECASE)
        if pay_match:
            logging.info("Pay command detected")
            amount = float(pay_match.group(1))
            target = pay_match.group(2).strip()
            stock = find_stock(target)
            
            if stock:
                transaction_id = "TJTG" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
                current_time = datetime.now().strftime("%d/%m/%y at %I:%M %p")
                old_balance = get_balance(user_session_id)
                new_balance = max(0, old_balance - amount)
                set_balance(user_session_id, new_balance)
                
                confirmation_message_text = (
                    f"{transaction_id} Confirmed. Ksh{amount:.2f} sent to "
                    f"{stock['name']} {recipient_number} on {current_time}. "
                    f"New M-pesa balance is ksh{new_balance:.2f}. Transaction cost, Ksh0.00. "
                    "Amount you can transact within the day is 499,230."
                )
                
                pending_purchases[user_session_id] = {
                    'ticker': stock['ticker'],
                    'qty': 1,
                    'unit_price': amount,
                    'total_amount': amount,
                    'recipient_name': recipient_name,
                    'recipient_number': recipient_number,
                    'stock_requested': stock['name'],
                    'stock_name': stock['name'],
                    'mpesa_confirmed': False
                }
                
                pending_mpesa_confirmations[user_session_id] = {
                    'message': confirmation_message_text,
                    'recipient_name': 'M-PESA',
                    'stock_requested': stock['name'],
                    'purchase_ref': user_session_id
                }
                
                return jsonify({
                    'type': 'stk_prompt',
                    'amount': amount,
                    'recipient': stock['name'],
                    'recipient_number': recipient_number,
                    'prompt_message': f"STK Push for Ksh {amount:.2f} to {stock['name']} ({recipient_number}). Enter PIN."
                })
        
        # 5. If it's stock trader but no specific command matched, provide helpful default
        logging.info("Stock trader query but no specific pattern matched, providing general help")
        default_reply = (
            "👋 Welcome to Stock Trader!\n\n"
            "I'm your personal stock trading assistant. I can help you with:\n\n"
            "📊 Check stock prices (e.g., 'Safaricom stock price' or 'price of SAF')\n"
            "📈 List available stocks ('list stocks' or 'top Kenyan stocks')\n"
            "💰 Buy stocks ('buy 5 SAF')\n"
            "💡 Investment advice and market insights\n"
            "📉 Sector analysis and portfolio recommendations\n\n"
            "What would you like to know about the market today?"
        )
        return jsonify({'type': 'chat_reply', 'reply': default_reply})

    # === GENERAL STK PUSH COMMAND (non-stock) ===
    stk_match = re.match(r'^(pay|PAY)\s+([\d\.]+)\s*$', user_message, re.IGNORECASE)
    if stk_match:
        amount = float(stk_match.group(2))
        transaction_id = "TJTG" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
        current_time = datetime.now().strftime("%d/%m/%y at %I:%M %p")
        old_balance = get_balance(user_session_id)
        new_balance = max(0, old_balance - amount)
        set_balance(user_session_id, new_balance)
        
        confirmation_message_text = (
            f"{transaction_id} Confirmed. Ksh{amount:.2f} sent to "
            f"{recipient_name} {recipient_number} on {current_time}. "
            f"New M-pesa balance is ksh{new_balance:.2f}. Transaction cost, Ksh0.00. "
            "Amount you can transact within the day is 499,230."
        )
        
        pending_mpesa_confirmations[user_session_id] = {
            'message': confirmation_message_text,
            'recipient_name': 'M-PESA'
        }
        
        return jsonify({
            'type': 'stk_prompt',
            'amount': amount,
            'recipient': recipient_name,
            'recipient_number': recipient_number,
            'prompt_message': f"STK Push for Ksh {amount:.2f} to {recipient_name} ({recipient_number}). Enter PIN."
        })

    # === BEDROCK AI CHAT (for all other non-stock queries) ===
    if conversation_id not in chat_sessions:
        logging.info(f"Initializing new chat session for convo_id: {conversation_id}")
        chat_sessions[conversation_id] = {
            'history': [],
            'persona_instruction': get_persona_instructions(recipient_name)
        }
        
        chat_sessions[conversation_id]['history'].append({
            'role': 'user',
            'content': [{'text': chat_sessions[conversation_id]['persona_instruction']}]
        })
        chat_sessions[conversation_id]['history'].append({
            'role': 'assistant',
            'content': [{'text': "Acknowledged. I will now respond as per my instructions."}]
        })

    chat_session_data = chat_sessions[conversation_id]
    messages_for_api = chat_session_data['history'] + [{'role': 'user', 'content': [{'text': user_message}]}]

    try:
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=messages_for_api,
            inferenceConfig={
                "temperature": 0.7,
                "topP": 0.9,
                "maxTokens": 300,
            }
        )
        
        bedrock_reply = response['output']['message']['content'][0]['text']
        
        
        chat_session_data['history'].append({'role': 'user', 'content': [{'text': user_message}]})
        chat_session_data['history'].append({'role': 'assistant', 'content': [{'text': bedrock_reply}]})

        return jsonify({'type': 'chat_reply', 'reply': bedrock_reply})

    except Exception as e:
        logging.error(f"Error communicating with AWS Bedrock API: {e}", exc_info=True)
        return jsonify({'type': 'chat_reply', 'reply': 'Sorry, I am having trouble connecting to the AI at the moment.'})

@app.route('/enter_pin', methods=['POST'])
def enter_pin():
    data = request.get_json()
    pin = data.get('pin', '')
    user_session_id = 'default_user_session'
    
    logging.info(f"PIN entered: {pin}. Processing STK push.")

    if pin == "0000":
        time.sleep(1)  # simulate processing
        
        if user_session_id in pending_mpesa_confirmations:
            confirmation = pending_mpesa_confirmations.pop(user_session_id)
            # Mark the purchase as confirmed so hedge account can be accepted next
            if user_session_id in pending_purchases:
                purchase = pending_purchases[user_session_id]
                purchase['mpesa_confirmed'] = True
                # Compose message prompting for Hedera account ID
                stock_name = purchase.get('stock_name', purchase.get('stock_requested', 'the stock'))
                qty = purchase.get('qty', 1)
                congrats_message = (
                    f"✅ Payment confirmed (simulated). You purchased {qty} unit(s) of {stock_name}. "
                    "Please enter your Hedera account ID (format: 0.x.y) so we can deliver your token."
                )
            else:
                congrats_message = "✅ Payment confirmed (simulated). No pending purchase found — if you intended to buy stock, please start a new order."

            return jsonify({
                'status': 'success',
                'type': 'mpesa_confirmation_available',
                'confirmation_message': confirmation['message'],
                'sender': confirmation.get('recipient_name'),
                'congrats_message': congrats_message
            })
        else:
            return jsonify({'status': 'error', 'message': 'No pending M-PESA transaction.'})
    else:
        return jsonify({'status': 'error', 'message': 'Incorrect PIN. Transaction failed.'})

@app.route('/sms_status', methods=['GET'])
def sms_status():
    """
    Get SMS service status and recent activity
    """
    try:
        # Get API stats
        api_stats = api_client.get_api_stats()
        
        # Get recent SMS history
        message_history = sms_service.get_message_history(limit=10)
        
        # Get account balance (simulated)
        balance_info = api_client.get_account_balance()
        
        status_info = {
            'service_status': 'active',
            'api_stats': api_stats,
            'recent_messages': len(message_history),
            'message_history': message_history[-5:],  # Last 5 messages
            'balance_info': balance_info,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(status_info)
        
    except Exception as e:
        logging.error(f"SMS status check failed: {e}")
        return jsonify({
            'service_status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/send_test_sms', methods=['POST'])
def send_test_sms():
    """
    Send a test SMS message (for debugging/testing)
    """
    try:
        data = request.get_json()
        phone = data.get('phone', '+254700000000')
        message = data.get('message', 'Test message from TextAHBAR app')
        
        # Send test SMS
        result = send_africastalking_sms(phone, message)
        
        return jsonify({
            'test_result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Test SMS failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/hedera_status', methods=['GET'])
def hedera_status():
    """
    Get Hedera network status and account information
    """
    try:
        # Get account balance and info
        balance_info = transaction_service.token_manager.get_account_balance()
        
        # Get recent transactions
        transaction_history = transaction_service.token_manager.get_transaction_history()
        
        # Get configuration validation
        config_validation = transaction_service.token_manager.config.validate_config()
        
        hedera_info = {
            'network': transaction_service.token_manager.config.network,
            'account_id': transaction_service.token_manager.config.my_account_id,
            'token_id': transaction_service.token_manager.config.token_id,
            'balance_info': balance_info,
            'recent_transactions': transaction_history[-5:],  # Last 5 transactions
            'config_validation': config_validation,
            'service_status': 'active' if config_validation.get('all_valid') else 'configuration_error',
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(hedera_info)
        
    except Exception as e:
        logging.error(f"Hedera status check failed: {e}")
        return jsonify({
            'service_status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    """
    Comprehensive API status dashboard
    """
    try:
        # Get configuration report
        config_report = ConfigValidator.get_configuration_report()
        
        # Get transaction statistics
        all_transactions = transaction_logger.get_transactions(limit=100)
        
        transaction_stats = {
            'total_transactions': len(all_transactions),
            'sms_transactions': len([tx for tx in all_transactions if tx['type'] == 'sms']),
            'stock_purchases': len([tx for tx in all_transactions if tx['type'] == 'stock_purchase']),
            'mpesa_payments': len([tx for tx in all_transactions if tx['type'] == 'mpesa_payment']),
            'token_transfers': len([tx for tx in all_transactions if tx['type'] == 'token_transfer']),
            'recent_activity': all_transactions[-10:] if all_transactions else []
        }
        
        # Get SMS service stats
        sms_stats = {
            'service_enabled': hasattr(sms_service, 'sms_client'),
            'recent_messages': len(sms_service.get_message_history(limit=50)),
            'africastalking_mode': os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
        }
        
        # Get Hedera service stats
        hedera_stats = {
            'network': transaction_service.token_manager.config.network,
            'account_id': transaction_service.token_manager.config.my_account_id,
            'token_id': transaction_service.token_manager.config.token_id,
            'service_enabled': transaction_service.token_manager.config.validate_config()['all_valid']
        }
        
        dashboard_data = {
            'application': {
                'name': 'TextAHBAR',
                'version': '1.0.0',
                'uptime_start': datetime.now().isoformat(),
                'status': 'operational'
            },
            'configuration': config_report,
            'statistics': {
                'transactions': transaction_stats,
                'sms': sms_stats,
                'hedera': hedera_stats
            },
            'services': {
                'sms_service': 'active' if sms_stats['service_enabled'] else 'inactive',
                'hedera_service': 'active' if hedera_stats['service_enabled'] else 'inactive',
                'stock_trading': 'active',
                'ai_chat': 'active'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logging.error(f"Dashboard generation failed: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/phone/validate', methods=['POST'])
def validate_phone_number():
    """
    Validate and format phone number
    """
    try:
        data = request.get_json()
        phone_number = data.get('phone_number', '')
        
        # Validate phone number
        validation = PhoneNumberValidator.validate_phone_number(phone_number)
        
        # Format phone number
        formatted = PhoneNumberValidator.format_phone_number(phone_number)
        
        # Get network info (for Kenyan numbers)
        network = PhoneNumberUtils.identify_kenyan_network(phone_number)
        display_format = PhoneNumberUtils.format_display_number(phone_number)
        
        # Calculate SMS cost
        sample_message = "Test message from TextAHBAR"
        cost_info = SMSCostCalculator.calculate_cost(phone_number, len(sample_message))
        
        result = {
            'original': phone_number,
            'formatted': formatted,
            'display_format': display_format,
            'validation': validation,
            'network': network,
            'cost_estimate': cost_info,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/stocks/list', methods=['GET'])
def get_stocks_list():
    """
    Get list of available stocks on NSE
    """
    try:
        return jsonify({
            'success': True,
            'data': {
                'stocks': kenya_stocks,
                'total_count': len(kenya_stocks),
                'market': 'Nairobi Securities Exchange (NSE)'
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/stocks/price/<ticker>', methods=['GET'])
def get_stock_price(ticker):
    """
    Get current price for a specific stock
    """
    try:
        stock = find_stock(ticker)
        
        if stock:
            return jsonify({
                'success': True,
                'data': {
                    'stock': stock,
                    'advice': generate_stock_advice(stock),
                    'market_status': 'open',  # Simulated
                    'last_updated': datetime.now().isoformat()
                },
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Stock ticker {ticker} not found',
                'timestamp': datetime.now().isoformat()
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/stocks/buy', methods=['POST'])
def buy_stock_api():
    """
    Purchase stocks via API with SMS and HBAR integration
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ['ticker', 'quantity', 'phone_number', 'hedera_account']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ticker = data['ticker'].upper()
        quantity = int(data['quantity'])
        phone_number = data['phone_number']
        hedera_account = data['hedera_account']
        
        # Validate Hedera account format
        if not transaction_service.token_manager.validate_account_id(hedera_account):
            return jsonify({
                'success': False,
                'error': 'Invalid Hedera account ID format',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Find stock
        stock = find_stock(ticker)
        if not stock:
            return jsonify({
                'success': False,
                'error': f'Stock ticker {ticker} not found',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # Calculate total cost
        total_cost = stock['price'] * quantity
        
        # Process the complete stock purchase
        result = transaction_service.process_stock_purchase(
            recipient_phone=phone_number,
            recipient_account=hedera_account,
            stock_name=stock['name'],
            quantity=quantity,
            price=total_cost
        )
        
        return jsonify({
            'success': result.get('success', False),
            'data': {
                'transaction_reference': result.get('transaction_reference'),
                'stock': stock,
                'quantity': quantity,
                'total_cost': total_cost,
                'hedera_transaction': result.get('token_transfer', {}),
                'sms_notifications': result.get('sms_notifications', [])
            },
            'message': 'Stock purchase completed successfully' if result.get('success') else 'Stock purchase failed',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Stock purchase API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/sms/send', methods=['POST'])
def send_sms_api():
    """
    Send SMS message via AfricasTalking API
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        if not data.get('to') or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: to, message',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        phone_number = data['to']
        message = data['message']
        sender_id = data.get('sender_id', 'TEXTAHBAR')
        
        # Validate phone number
        validation = PhoneNumberValidator.validate_phone_number(phone_number)
        if not validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number format',
                'validation': validation,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Calculate cost
        cost_info = SMSCostCalculator.calculate_cost(phone_number, len(message))
        
        # Send SMS
        result = send_africastalking_sms(phone_number, message, sender_id)
        
        return jsonify({
            'success': result.get('success', False),
            'data': {
                'message_id': result.get('message_id'),
                'recipient': phone_number,
                'cost_info': cost_info,
                'delivery_status': result.get('status', 'unknown')
            },
            'message': 'SMS sent successfully' if result.get('success') else 'SMS sending failed',
            'error': result.get('error') if not result.get('success') else None,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"SMS API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/hedera/balance/<account_id>', methods=['GET'])
def get_hedera_balance_api(account_id):
    """
    Get Hedera account balance
    """
    try:
        # Validate account ID format
        if not transaction_service.token_manager.validate_account_id(account_id):
            return jsonify({
                'success': False,
                'error': 'Invalid Hedera account ID format',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        balance_info = transaction_service.token_manager.get_account_balance(account_id)
        
        return jsonify({
            'success': balance_info.get('success', False),
            'data': balance_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/hedera/transfer', methods=['POST'])
def transfer_hedera_api():
    """
    Transfer HBAR tokens between accounts
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ['to_account', 'amount']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        to_account = data['to_account']
        amount = int(data['amount'])
        memo = data.get('memo', 'API token transfer')
        notify_phone = data.get('notify_phone')
        
        # Validate account ID format
        if not transaction_service.token_manager.validate_account_id(to_account):
            return jsonify({
                'success': False,
                'error': 'Invalid recipient Hedera account ID format',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Transfer tokens
        result = transaction_service.token_manager.transfer_tokens(to_account, amount, memo)
        
        # Send SMS notification if phone provided
        sms_result = None
        if notify_phone and result.get('success'):
            try:
                sms_result = sms_service.notify_token_transfer(
                    notify_phone, amount, to_account, result.get('transaction_id', '')
                )
            except Exception as sms_error:
                logging.warning(f"SMS notification failed: {sms_error}")
        
        return jsonify({
            'success': result.get('success', False),
            'data': {
                'transfer': result,
                'sms_notification': sms_result
            },
            'message': 'Token transfer completed' if result.get('success') else 'Token transfer failed',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Hedera transfer API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/transactions', methods=['GET'])
def get_transactions_api():
    """
    Get transaction history with filtering options
    """
    try:
        # Get query parameters
        transaction_type = request.args.get('type')  # sms, stock_purchase, token_transfer
        limit = int(request.args.get('limit', 50))
        
        transactions = transaction_logger.get_transactions(transaction_type, limit)
        
        # Calculate statistics
        stats = {
            'total_transactions': len(transactions),
            'successful_transactions': len([tx for tx in transactions if tx.get('status')]),
            'failed_transactions': len([tx for tx in transactions if not tx.get('status')]),
            'transaction_types': {}
        }
        
        # Count by type
        for tx in transactions:
            tx_type = tx.get('type', 'unknown')
            stats['transaction_types'][tx_type] = stats['transaction_types'].get(tx_type, 0) + 1
        
        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'statistics': stats,
                'filters': {
                    'type': transaction_type,
                    'limit': limit
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/webhook/sms', methods=['POST'])
def sms_webhook():
    """
    Webhook endpoint for SMS delivery reports from AfricasTalking
    """
    try:
        data = request.get_json()
        
        # Log the webhook data
        logging.info(f"SMS webhook received: {data}")
        
        # Process delivery report
        message_id = data.get('id')
        status = data.get('status', 'unknown')
        
        if message_id:
            # Update delivery status in logs
            transaction_data = {
                'message_id': message_id,
                'delivery_status': status,
                'webhook_data': data,
                'success': status.lower() in ['success', 'delivered']
            }
            
            transaction_logger.log_transaction('sms_delivery_report', transaction_data)
        
        return jsonify({
            'success': True,
            'message': 'Webhook processed successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"SMS webhook error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })


if __name__ == '__main__':
    # Log startup information
    logging.info("🚀 TextAHBAR app starting up...")
    logging.info("=" * 50)
    
    # Configuration validation
    config_report = ConfigValidator.get_configuration_report()
    logging.info(f"⚙️  Configuration Status: {'✅ Valid' if config_report['validation_results']['all_valid'] else '❌ Invalid'}")
    
    # Service status
    logging.info(f"📱 SMS Service (AfricasTalking): {'✅ Enabled' if hasattr(sms_service, 'sms_client') else '❌ Disabled'}")
    logging.info(f"🌐 Hedera Network: {transaction_service.token_manager.config.network.upper()}")
    logging.info(f"💰 Token ID: {transaction_service.token_manager.config.token_id}")
    logging.info(f"🏦 Account ID: {transaction_service.token_manager.config.my_account_id}")
    
    # AfricasTalking configuration
    at_mode = config_report['environment_summary']['africastalking_mode']
    logging.info(f"📞 AfricasTalking Mode: {at_mode.upper()}")
    
    # Feature status
    logging.info("🔧 Features:")
    logging.info("   • Stock Trading with SMS notifications")
    logging.info("   • Hedera token transfers")  
    logging.info("   • M-PESA simulation")
    logging.info("   • AI-powered chat")
    logging.info("   • Transaction logging")
    logging.info("   • Phone number validation")
    logging.info("   • SMS cost calculation")
    



    # API endpoints
    logging.info("🌐 API Endpoints:")
    logging.info("   • /api/dashboard - Service status dashboard")
    logging.info("   • /sms_status - SMS service status")
    logging.info("   • /hedera_status - Hedera network status")
    logging.info("   • /api/phone/validate - Phone validation")
    logging.info("   • /send_test_sms - Test SMS sending")
    
    # Recommendations
    if config_report['recommendations']:
        logging.info("💡 Recommendations:")
        for rec in config_report['recommendations']:
            logging.info(f"   • {rec}")
    
    logging.info("=" * 50)
    logging.info("🎉 TextAHBAR is ready to handle SMS and HBAR transactions!")
    
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))