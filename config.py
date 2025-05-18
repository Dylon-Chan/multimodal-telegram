import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_API_KEY = os.environ.get('TELEGRAM_API_KEY')
