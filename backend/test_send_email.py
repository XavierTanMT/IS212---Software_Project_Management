from dotenv import load_dotenv
import os

# Ensure .env is loaded
# This is purely for testing purposes
load_dotenv()

from email_utils import send_email

def main():
    to = os.getenv('TEST_EMAIL_TO') or os.getenv('EMAIL_FROM')
    if not to:
        print('No TEST_EMAIL_TO or EMAIL_FROM configured in env; set TEST_EMAIL_TO to test recipient')
        return
    ok = send_email(to, 'Test email from task-manager', 'This is a test email sent by test_send_email.py')
    print('send_email returned:', ok)

if __name__ == '__main__':
    main()
