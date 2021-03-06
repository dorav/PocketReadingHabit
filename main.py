from pocket import Pocket
import random
import os
from time import sleep
from http.server import *
import webbrowser
import mail
import config

access_token_file = os.path.expanduser('~/pocket_reminder_access_token')

html_page_after_authenticated_with_pocket = u'''
<html>
<body>
Succesfully authenticated against pocket <br>
You should soon receive a mail with a suggested article to read
</body>
</html>
'''.encode()

class PocketAuthenticationWaiter(BaseHTTPRequestHandler):
    def do_GET(self):
        global html_page_after_authenticated_with_pocket
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_page_after_authenticated_with_pocket)
        
def get_user_permission_for_pocket():
    print ("Preparing to get authenticated with pocket, may take a few seconds")
    server_address = ('0.0.0.0', config.localhost_port)
    httpd = HTTPServer(server_address, PocketAuthenticationWaiter)
    redirect_uri = 'http://localhost:' + str(config.localhost_port)
    request_token = Pocket.get_request_token(consumer_key=config.pocket_consumer_key, redirect_uri=redirect_uri)
    auth_url = Pocket.get_auth_url(code=request_token, redirect_uri=redirect_uri)

    print ("Opening the browser to handle user input ", redirect_uri)
    webbrowser.open_new_tab(auth_url) 

    print ("Waiting for authentication")
    httpd.handle_request()

    user_credentials = Pocket.get_credentials(consumer_key=config.pocket_consumer_key, code=request_token)

    print ("Pocket authenticated! credentials = ", user_credentials)
    return user_credentials['access_token']

def existing_token():
    global access_token_file

    if os.path.isfile(access_token_file) == False:
        return ''

    with open(access_token_file, 'r') as f:
        return f.read()

def save_token(token):
    global access_token_file
    with open(access_token_file, 'w+') as f:
        f.write(token)

def login_to_pocket():
    access_token = existing_token()
    if access_token == '':
        print ("User access token does not exist, need to get user permission")
        access_token = get_user_permission_for_pocket()
        save_token(access_token)

    try:
        pocket_instance = Pocket(config.pocket_consumer_key, access_token)
        pocket_instance.get(count=1)
    except:
        print ("User revoked his permissions from pocket, asking again")
        access_token = get_user_permission_for_pocket()
        save_token(access_token)
    
    return Pocket(config.pocket_consumer_key, access_token)

config = config.load_config()

pocket_instance = login_to_pocket()

art_list = pocket_instance.get(state='unread')[0]['list']

list_length = len(art_list)
print('Number of items in Pocket list is: ' + str(list_length))
rand_key = random.choice(list(art_list.keys()))
rand_article = art_list[rand_key]
title = rand_article['resolved_title']
word_count = rand_article['word_count']
id = rand_article['item_id']
url = "https://getpocket.com/a/read/" + id
print (title)
print(word_count)
print(url)
minutes = int(word_count)//178
print("Read time (min): " + str(minutes))


subject = "Here is what you need to read today"
msg = "With only " + str(list_length) + \
      " items left in your pocket read list, here is what I offer you to read today\n" + title +\
      "\nwhich will take you " + str(minutes) + " minutes to read.\n" + url

response = mail.send_mailgun_msg(config, subject, msg)
print (response)
