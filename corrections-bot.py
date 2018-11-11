#!/usr/bin/env python3
import os
import sys
import time
import socket
import pickle
import requests
from bs4 import BeautifulSoup
from slackclient import SlackClient
from twilio.rest import Client as TwilioClient

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# XXX private info
user_login_value = 'YOUR_INTRA_NAME_HERE'                       # XXX
user_password_value = 'YOUR_INTRA_PASSWORD_HERE'                # XXX
twilio_account_sid = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'       # XXX
twilio_auth_token = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'          # XXX
twilio_from_number = '+1xxxxxxxxxx'                             # XXX
twilio_to_number = '+1xxxxxxxxxx'                               # XXX
slack_token = 'xoxs-xxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# settings
sign_out = False            # if set to True, bot will log out of intra, generates unwanted email notifications
save_session = True
save_html = False
debug = True
send_sms = True
send_group_msg = True
send_direct_msg = True
send_direct_msg_if = False   # send direct message only if group message fails

# values the bot searches for (on the login page)
user_login_key = 'user[login]'
user_password_key = 'user[password]'

# urls the bot uses
intra_signin_page = 'https://signin.intra.42.fr/users/sign_in'
intra_signout_page = 'https://signin.intra.42.fr/users/sign_out'
intra_profile_page = 'https://profile.intra.42.fr/'

# once the bot posts login, it compares the html title to this to make sure its on the correct page
intra_profile_page_title = 'Intra Profile Home'

# filename to use for storing requests session,
# this way we can re-use it next time (to prevent multiple logins and email notifications)
intra_session_file = 'intra_session.pickled'

# http user agent, you'll be able to see this on your intra page,
# check your connection logs at    https://profile.intra.42.fr/users/YOUR_INTRA_NAME_HERE/user_logins
user_agent = 'Mozilla/5.0 (Nintendo Banana; U; Windows Like Godzilla; en) Version/0.42.US'

# http headers dict to send
headers = {'User-Agent': user_agent}

# a place to store our correction string, this way we can avoid sending duplicates
log_file = 'corrections.log'
slack_user_list_file = 'slack.user.list'

def twilio_sms(message):
    tc = TwilioClient(twilio_account_sid, twilio_auth_token)
    a = tc.messages.create(to=twilio_to_number, from_=twilio_from_number, body=message)

def slack_update_user_list():
    sc = SlackClient(slack_token)
    user_list = sc.api_call('users.list')
    with open(slack_user_list_file, 'wb') as fp:
        pickle.dump(user_list, fp)
        fp.close()

def slack_get_user_list():
    user_list = {};
    if os.path.isfile(slack_user_list_file) == False:
        slack_update_user_list()
    if os.stat(slack_user_list_file).st_mtime < time.time() - 86400:    # if older than 24 hours, then update
        slack_update_user_list()
    try:
        with open(slack_user_list_file, 'rb') as fp:
            user_list = pickle.load(fp)
            fp.close()
    except:
        pass
    return user_list
        
def slack_get_user_id(display_name):
    user_list = slack_get_user_list()
    for user in user_list['members']:
        if user['profile']['display_name'].lower() == display_name:
            return user['id']
    return None

def slack_send_direct_message(user1, message):
    userid1 = slack_get_user_id(user1)
    if userid1 == None:
        return False
    sc = SlackClient(slack_token)
    sc.api_call('chat.postMessage', channel=userid1, text=message);
    return True

def slack_send_group_message(user1, user2, message):
    userid1 = slack_get_user_id(user1)
    if userid1 == None:
        return False
    userid2 = slack_get_user_id(user2)
    if userid2 == None:
        return False
    message = message.replace('You ', '<@' + userid1 + '> ', 1);
    message = message.replace(' ' + user2 + ' ',' <@' + userid2 + '> ', 1)
    sc = SlackClient(slack_token)
    group_chat = sc.api_call('conversations.open', users=[userid1, userid2])
    if group_chat['ok'] != True:
        return False
    sc.api_call('chat.postMessage', channel=group_chat['channel']['id'], text=message)
    return True

def is_text_in_file(filename, text):    #returns true if text matches a line in file, false otherwise
    try:
        with open(filename, 'r') as fp:
            for line in fp.read().splitlines():
                if line == text:
                    fp.close()
                    return True
            fp.close()
            return False
    except:
            return False

def put_text_in_file(filename, text):
    try:
        with open(filename, 'a') as fp:
            print(text, file=fp)
            fp.close()
    except:
        pass

###############################################################################

def is_online(host="8.8.8.8", port=53, timeout=3):      # returns true if we can ping google
	try:
		socket.setdefaulttimeout(timeout)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
		return True
	except:
		return False


def load_session():     # get previously saved session from file
    try:
        with open(intra_session_file, 'rb') as fp:
            result = pickle.load(fp)
            fp.close()
            return result
    except:
        return False

def store_session(session): #save session into a file
    try:
        with open(intra_session_file, 'wb') as fp:
            pickle.dump(session, fp)
            fp.close()
            return True  #great success
    except:
        return False

def init_session():     # tries to load a saved session from file, or create a new one
    session = load_session()
    if session == False:
        if debug: print('load_session() failed, trying to create new')
        session = create_session()
        if session == False:
            if debug:
                print('failed to create session, bad credentials?')
            sys.exit(1)
        session = load_session()
        if not session:
            print('load_session() failed, something is wrong')
            sys.exit(1)
    return session

###############################################################################
def create_session():   # creates a session, logs in, saves session to a file
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})

    req1 = session.get(intra_signin_page)   #request1, get sign-in page
    if req1.status_code == 200:
        page_signin = req1.content.decode('utf-8')
    else:
        if debug:
            print('failed to get sign-in page, requests.get returned: ', req1.status_code)
        return False
        
    soup1 = BeautifulSoup(page_signin, features="html.parser")  ## prints a warning if not specified

    post_data = {} 
    for form_input in soup1.find_all('input'):
        key = form_input.get('name')
        value = form_input.get('value')
        post_data[key] = value

    post_data[user_login_key] = user_login_value
    post_data[user_password_key] = user_password_value

    req2 = session.post(intra_signin_page, data=post_data, allow_redirects=False)    #request2, post login data
    if req2.status_code == 200 or req2.status_code == 302:
        if save_session == True:
            store_session(session)
        return True
    else:
        if debug:
            print('failed to post login data, requests.post returned: ', req2.status_code)
        return False

###############################################################################
#--main logic here-------------------------------------------------------------

if is_online() != True:
	print("offline")
	sys.exit()

session = init_session()
req3 = session.get(intra_profile_page)
if req3.status_code == 200:
    page_profile = req3.content.decode('utf-8')
else:
    if debug:
        print('failed to get profile page, response code: ', req3.status_code)
    sys.exit(1)


soup2 = BeautifulSoup(page_profile, features="html.parser")

#are we at the right place?
if soup2.title.string != intra_profile_page_title:
    #maybe we're logged out? try to login again?
    if debug:
        print('wrong profile title page; logged out or bad credentials? deleting stored session file')
    try:
        os.remove(intra_session_file)
    except:
        pass
    sys.exit(1)

if debug:
    print('got profile page .. ok')
if save_html:
    output = 'profile_' + str(time.time()) + '.html'
    with open(output, 'w') as fp:
        fp.write(page_profile)
        fp.close()

message=None
for reminder in soup2.find_all('div', class_='project-item reminder'):
    for project in reminder.find_all('div', class_='project-item-text'):
        message = ' '.join(project.text.split()) + ' at '
        for span in project.parent.find_all('span'):
            if span.has_attr('data-long-date'):
                message += span.get('title')
                break

        partner = None
        for user in project.parent.find_all('a'):
            if user.has_attr('data-user-link'):
                partner = user.get('data-user-link')

        if is_text_in_file(log_file, message) == False:
            put_text_in_file(log_file, message)                         #save in log file
            if send_sms == True: twilio_sms(message)                                         #send sms

            user_login_value = user_login_value.lower()
            if partner != None:
                partner = partner.lower()         
           
            group_msg_result = False
            if send_group_msg == True:
                if partner != None:
                    group_msg_result = slack_send_group_message(user_login_value, partner, message)
            if send_direct_msg == True:
                if send_direct_msg_if == False:
                    slack_send_direct_message(user_login_value, message)
                elif (send_direct_msg_if == True) and (group_msg_result == False):
                    slack_send_direct_message(user_login_value, message)
            if debug:                                                   #print message
                print(message)

if debug and not message:
    print('debug: no corrections on your intra page')

if save_session:
    if debug: print('debug: saving session')
    store_session(session)

if sign_out:
    if debug: print('debug: signing out')
    signout_data = {'_method': 'delete', 'authenticity_token': ''}
    for meta in soup2.find_all('meta'):
        if meta.get('name') == 'csrf-token':
            signout_data['authenticity_token'] = meta.get('content')
            break
    req3 = session.post(intra_signout_page, data=signout_data, allow_redirects=True)    #request3, log out

