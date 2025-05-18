from flask import Flask, request, jsonify
from config import Config
import requests
import time
import json
import os
from apps.gemini import get_gemini_response

app = Flask(__name__)
app.config.from_object(Config)

telegram_api_key = Config.TELEGRAM_API_KEY
base_url = f'https://api.telegram.org/bot{telegram_api_key}/'

users_dict = {}

def send_message(id, text, reply_markup=None):
    data = {'chat_id': id, 'text': text}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    response = requests.post(base_url + 'sendMessage', json=data)
    return response.json()

@app.route('/')
def index():
    return "Telegram Bot Webhook Server is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        isMessage = update.get('message', {})
        isCallback = update.get('callback_query', {})

        if isCallback:
            chat_id = isCallback['message']['chat']['id']
            callback_data = isCallback['data']
            users_dict[chat_id]['callback_data'] = callback_data
            if callback_data == 'SD':
                text = f'What image would you like to generate? [Enter /end to end]'
            else:
                text = f'Hi, I am your {callback_data} chatbot. How can I help you today? [Enter /end to end]'
            send_message(chat_id, text)
            return jsonify({'action': 'select_tool', 'status': 'success'})
        
        if isMessage:
            chat_id = isMessage['chat']['id']
            q = isMessage['text']

            if users_dict.get(chat_id, {}).get('status', '') != 'start':
                send_message(chat_id, 'Please enter /start to start a session')
                return jsonify({'action': 'ask_start', 'status': 'success'})

            if q == '/start' or not users_dict.get(chat_id, {}).get('callback_data', {}):
                users_dict[chat_id] = {'callback_data': None, 'status': 'start'}
                welcome_reply_markup = {
                    'inline_keyboard': [
                        [{'text': 'Chat with DeepSeek', 'callback_data': 'DeepSeek'},
                        {'text': 'Chat with Sea-Lion', 'callback_data': 'Sea-Lion'}],
                        [{'text': 'Chat with Gemini', 'callback_data': 'Gemini'},
                        {'text': 'Image generator with Stable Diffusion', 'callback_data': 'SD'}]
                    ]
                }
                welcome_text = 'Welcome to the Multimodal Chatbot! Please choose a chatbot/tool:'
                send_message(chat_id, welcome_text, welcome_reply_markup)
                return jsonify({'action': 'welcome', 'status': 'success'})
            
            if q == '/end':
                users_dict[chat_id]['callback_data'] = None
                users_dict[chat_id]['status'] = 'end'
                send_message(chat_id, 'Bye and see you again! [Enter /start to start a session]')
                return jsonify({'action': 'exit', 'status': 'success'})
            
            tool = users_dict[chat_id]['callback_data']

            if tool == 'DeepSeek':
                r = 'This is a test response from DeepSeek'
                send_message(chat_id, r)

            elif tool == 'Sea-Lion':
                r = 'This is a test response from Sea-Lion'
                send_message(chat_id, r)

            elif tool == 'Gemini':
                r = get_gemini_response(q)
                send_message(chat_id, r)

            elif tool == 'SD':
                r = 'This is a test response from Stable Diffusion'
                send_message(chat_id, r)

            return jsonify({'action': 'reply_message', 'status': 'success'})
        
    return jsonify({'status': 'error', 'message': 'Invalid request'})

@app.route('/setup_webhook', methods=['GET'])
def setup_webhook():
    webhook_url = request.args.get('url')
    if not webhook_url:
        return jsonify({'status': 'error', 'message': 'No webhook URL provided'})
    data = {'url': webhook_url}
    response = requests.post(base_url + 'setWebhook', json=data)
    return jsonify(response.json())

@app.route('/get_webhook_info', methods=['GET'])
def get_webhook_info():
    response = requests.get(base_url + 'getWebhookInfo')
    return jsonify(response.json())

@app.route('/delete_webhook', methods=['GET'])
def delete_webhook():
    response = requests.get(base_url + 'deleteWebhook')
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)