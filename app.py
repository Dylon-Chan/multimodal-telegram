from flask import Flask, request, jsonify
from config import Config
import requests
import time
import json
import os
from apps.gemini import get_gemini_response
from io import StringIO
import pandas as pd
import pypdf
import tempfile

app = Flask(__name__)
app.config.from_object(Config)

telegram_api_key = Config.TELEGRAM_API_KEY
base_url = f'https://api.telegram.org/bot{telegram_api_key}/'

users_dict = {}

def send_message(id, text, reply_markup=None):
    MAX_MESSAGE_LENGTH = 4096
    data = {'chat_id': id}
    
    if len(text) <= MAX_MESSAGE_LENGTH:
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        data['text'] = text
        response = requests.post(base_url + 'sendMessage', json=data)
    else:
        paragraphs = text.split('\n\n')
        current_chunk = ''

        for p in paragraphs:
            if len(current_chunk + p + '\n\n') > MAX_MESSAGE_LENGTH and current_chunk:
                data['text'] = current_chunk.strip()
                response = requests.post(base_url + 'sendMessage', json=data)

                current_chunk = p + '\n\n'
                time.sleep(1)
            else:
                current_chunk += p + '\n\n'
            
        if current_chunk.strip():
            data['text'] = current_chunk.strip()
            response = requests.post(base_url + 'sendMessage', json=data)
    return response.json()

@app.route('/')
def index():
    return "Telegram Bot Webhook Server is running!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'message': 'Webhook is active'})
        
    if request.method == 'POST':
        update = request.get_json()
        isMessage = update.get('message', {})
        isCallback = update.get('callback_query', {})

        if isCallback:
            chat_id = isCallback['message']['chat']['id']
            callback_data = isCallback['data']
            users_dict[chat_id]['callback_data'] = callback_data
            if callback_data == 'SD':
                text = f'Welcome to the Stable Diffusion Image Generator!\n\nI can help you create amazing images from your text descriptions. Just tell me what you\'d like to see, and I\'ll generate it for you.\n\n[Enter /end to end]'
            elif callback_data == 'DeepSeek':
                text = f'Welcome to DeepSeek Chat!\n\nI\'m your advanced AI assistant powered by DeepSeek. I can help you with various tasks, answer questions, and engage in meaningful conversations.\n\nHow can I assist you today?\n\n[Enter /end to end]'
            elif callback_data == 'Sea-Lion':
                text = f'Welcome to Sea-Lion Chat!\n\nI\'m your friendly AI companion powered by Sea-Lion. I\'m here to help you with your questions and tasks.\n\nWhat would you like to discuss?\n\n[Enter /end to end]'
            elif callback_data == 'Gemini':
                text = f'Welcome to Gemini Chat!\n\nI\'m powered by Google\'s Gemini model, ready to help you with a wide range of tasks. I can assist with information, analysis, and creative tasks.\n\nHow can I help you today?\n\n[Enter /end to end]'
            send_message(chat_id, text)
            return jsonify({'action': 'select_tool', 'status': 'success'})
        
        if isMessage:
            chat_id = isMessage['chat']['id']
            file_upload = isMessage.get('document','')
            q = isMessage.get('text','')

            if file_upload:
                caption = isMessage.get('caption','')
                file_type = file_upload['mime_type']
                if not caption:
                    send_message(chat_id, 'Please enter your prompt in the caption when uploading a file!')
                    return jsonify({'error': 'no caption', 'status': 'error'})
                if file_type not in ['text/csv', 'application/vnd.ms-excel', 'application/pdf']:
                    send_message(chat_id, 'I am sorry that I can only accept CSV, Excel, or PDF file. Please re-upload a correct file.')
                    return jsonify({'error': 'not correct file type', 'status': 'error'})
                file_id = file_upload['file_id']
                get_file = requests.get(base_url + f'getFile?file_id={file_id}')
                file_path = get_file.json()['result']['file_path']
                download_file = requests.get(f'https://api.telegram.org/file/bot{telegram_api_key}/{file_path}')
                if file_upload['mime_type'] == 'text/csv':
                    df = pd.read_csv(StringIO(download_file.text))
                    file_text = df.to_string(index=False)
                elif file_upload['mime_type'] == 'application/vnd.ms-excel':
                    df = pd.read_excel(StringIO(download_file.text))
                    file_text = df.to_string(index=False)
                elif file_upload['mime_type'] == 'application/pdf':
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                        temp_pdf.write(download_file.content)
                        temp_pdf_path = temp_pdf.name
                    reader = pypdf.PdfReader(temp_pdf_path)
                    file_text = ''
                    for p in reader.pages:
                        txt = p.extract_text()
                        if txt:
                            file_text += txt + '\n'
                    os.remove(temp_pdf_path)
                q = f'{file_text}\n\n{caption}'
                
            if q == '/start' or not users_dict.get(chat_id, {}).get('callback_data', {}):
                users_dict[chat_id] = {'callback_data': None, 'status': 'start'}
                welcome_reply_markup = {
                    'inline_keyboard': [
                        [{'text': 'Chat with DeepSeek (dev in progress)', 'callback_data': 'DeepSeek'},
                        {'text': 'Chat with Sea-Lion (dev in progress)', 'callback_data': 'Sea-Lion'}],
                        [{'text': 'Chat with Gemini', 'callback_data': 'Gemini'},
                        {'text': 'Image Generator (dev in progress)', 'callback_data': 'SD'}]
                    ]
                }
                welcome_text = 'Welcome to the Multimodal Chatbot! Please choose a chatbot/tool:'
                send_message(chat_id, welcome_text, welcome_reply_markup)
                return jsonify({'action': 'welcome', 'status': 'success'})
            
            if users_dict.get(chat_id, {}).get('status', '') != 'start':
                send_message(chat_id, 'Please enter /start to start a session')
                return jsonify({'action': 'ask_start', 'status': 'success'})
            
            if q == '/end':
                users_dict[chat_id]['callback_data'] = None
                users_dict[chat_id]['status'] = 'end'
                send_message(chat_id, 'Bye and see you again! [Enter /start to start a session]')
                return jsonify({'action': 'exit', 'status': 'success'})
            
            tool = users_dict[chat_id]['callback_data']
            print(f'User {chat_id} is using tool: {tool}')

            if tool == 'DeepSeek':
                r = 'This is a test response from DeepSeek.'
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

# route to setup webhook by visiting the url (e.g. https://your-domain.com/setup_webhook?url=https://your-domain.com/webhook)
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