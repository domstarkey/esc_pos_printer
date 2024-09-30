import feedparser
from escpos.printer import Network
import textwrap
import requests
from datetime import datetime
import os
from dotenv import load_dotenv, dotenv_values 
from pprint import pprint
from flask import Flask, redirect, request, session, url_for, jsonify
load_dotenv()
import json
from datetime import date
import random
from ticktick.oauth2 import OAuth2        # OAuth2 Manager
from ticktick.api import TickTickClient   # Main Interface
import datetime

# Step 2: Connect to the ESC/POS printer
printer_ip = '192.168.2.134'

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def print_rss_feed(printer, caption = 'Heidelberg News', rss_feed_url='https://www.rnz.de/feed/139-RL_Heidelberg_free.xml', _count = 5):
    printer.text(f"{ caption }\n")
    #printer.set(align='left', bold=False, double_height=False)
    printer.set(bold= False,normal_textsize=True)

    feed = feedparser.parse(rss_feed_url)
    # Print each entry from the RSS feed
    for entry in feed.entries[:_count]:  # Limit to the first 5 headlines
        # Wrap text for the small paper width
        #headline = textwrap.fill(entry.title, width=52)
        #description = textwrap.fill(entry.description, width=52)

        headline = entry.title
        description = entry.description

        # Print the headline and description
        printer.set(bold= True,normal_textsize=True)
        printer.text(f"{headline}\n")
        printer.set(bold= False,normal_textsize=True)
        printer.text(f"{description}\n")
        printer.text("\n---\n\n")

# Step 3: Format and print the news
@app.route('/print_news')
def print_news():
    try:
        printer= Network(printer_ip)
        # Print the feed title
        print_daily_basics(printer= printer)

        print_basecamp_tasks(printer= printer)

        #printer.set(align='center', bold=True, double_height=True)
        print_rss_feed(printer = printer, caption = 'Heidelberg News', rss_feed_url='https://www.rnz.de/feed/139-RL_Heidelberg_free.xml', _count = 3)

        print_rss_feed(printer = printer, caption= 'Tagesschau', rss_feed_url='https://www.tagesschau.de/inland/index~rss2.xml', _count = 3)

        

        # Step 4: Cut the paper
        printer.cut()
        return jsonify({"status": "success", "message": "Printed successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to print."}), 500

def print_daily_basics(printer):

    try:
        if printer == None:
            printer = Network(printer_ip)

        today = date.today()

        printer.set(double_width=True, double_height=True, align='center',bold=True)
        printer.text(f"{ today.strftime('%A %x')}\n\n")
        printer.set(double_width=False, double_height=False, align='center',bold=False, normal_textsize= True)

        sunset = requests.get("https://api.sunrise-sunset.org/json?lat=49.3988&lng=8.6724&date=today&tzid=Europe/Berlin").json()

        printer.text(f"{ sunset['results']['sunrise'] } - { sunset['results']['sunset']}\n")

        printer.set(double_width=True, double_height=True, align='center')
        printer.text(f'# { random.randint(1,53) }\n')
        printer.set(double_width=False, double_height=False, align='center', normal_textsize=True)

        printer.set(align='left')

    except Exception as e:
        pprint(e)

def get_basecamp_access_token_accountid():

    access_token = None

    try:

        with open('.bc_token','r') as f:
            access_token = f.read().replace('\n','')

        if not access_token:
            print('Access token not there.')
            exit(1)

        # get account id
        headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'ESCPrinter (daniel@dakoller.net)',
        }
        r = requests.get('https://launchpad.37signals.com/authorization.json',headers= headers)
        resp = r.json()
        pprint(resp)
        # look for bc3 product
        account_id = None
        for item in resp['accounts']:
            if item['product'] == 'bc3':
                account_id = item['id']

        return access_token, account_id
    except Exception as e:
        pprint(e)
        return None,None

def get_ticktick_accesstoken():
    access_token = None

    with open('.tt_token','r') as f:
        access_token = f.read().replace('\n','')

    if not access_token:
        print('Access token not there.')
        exit(1)

    ## get account id
    #headers = {
    #    'Authorization': f'Bearer {access_token}',
    #}

    #r = requests.get('https://ticktick.com/open/v1/project',headers= headers)
    #resp = r.json()

    #pprint(resp)

    return access_token

def print_basecamp_tasks(printer):
    try:
        access_token, account_id = get_basecamp_access_token_accountid()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'ESCPrinter (daniel@dakoller.net)',
        }

        if printer == None:
            printer = Network(printer_ip)

        #pprint(account_id)
        _tasks = []

        # get projects
        projects = requests.get(f'https://3.basecampapi.com/{account_id}/projects.json', headers=headers).json()

        for project in projects:
            #pprint(project)
            project_id = project['id']

            # get todo set id
            todoset_id = None
            for item in project['dock']:
                if item['name'] == 'todoset':
                    todoset_id = item['id']

            todolists = requests.get(f'https://3.basecampapi.com/{account_id}/buckets/{project_id}/todosets/{todoset_id}/todolists.json', headers=headers).json()
            for todolist in todolists:
                #pprint(todolist)
                todolist_id = todolist['id']

                # get tasks finally
                tasks = requests.get(f'https://3.basecampapi.com/{account_id}/buckets/{project_id}/todolists/{todolist_id}/todos.json',headers=headers).json()
                #pprint(tasks)

                for task in tasks:
                    if task['assignees'] != []:
                        for assignee in task['assignees']:
                            if assignee['id'] == int(os.getenv('BASECAMP_OWN_ACCOUNT_ID')):
                                _tasks.append({
                                    'project': task['bucket']['name'],
                                    'content': task['content'],
                                    'due_date': task['due_on'],
                                    'status': task['status'],
                                    'url': task['app_url'],
                                })
        #exit(0)
        if len(_tasks) > 0:

            printer.set(bold= True,normal_textsize=True)
            printer.text(f"Basecamp-Tasks:\n")
            printer.set(bold= False,normal_textsize=True)
            #printer.text(f"{description}\n")
            #printer.text("\n---\n\n")

            for task in _tasks:
                printer.set(bold= True,normal_textsize=True)
                printer.text(f"{task['content']} ")
                printer.set(bold= False,normal_textsize=True)
                printer.text(f"from {task['project']}\n")
                printer.set(bold= True,normal_textsize=True)
                printer.text(f"{task['due_date']}\n")
                printer.set(bold= False,normal_textsize=True)
                printer.qr(task['url'],size=5)
                printer.text("\n---\n\n")

    except Exception as e:
        print(e)

def get_ticktick_tasks():
    access_token = get_ticktick_accesstoken()

    try:

        auth_client = OAuth2(client_id=os.getenv("TICKTICK_CLIENT_ID"),
                        client_secret=os.getenv("TICKTICK_CLIENT_SECRET"),
                        redirect_uri=os.getenv("TICKTICK_REDIRECT_URI"))

        client = TickTickClient(os.getenv("TICKTICK_USERNAME"), os.getenv("TICKTICK_PASSWORD"), auth_client)

        pprint(client.state['tasks'])


    except Exception as e:
        pprint(e)


def get_ticktick_api():
    access_token = get_ticktick_accesstoken()

    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    r = requests.get('https://api.ticktick.com/open/v1/project/inbox122326785/task/66b776cfc1b6d19b4d30a79d/',headers=headers)

    pprint(r.text)

@app.route('/basecamp_callback')
def basecamp_callback():
    request_data = request.args
    code = request_data['code']

    data = {
        'client_id':    os.getenv('BASECAMP_CLIENT_ID'),
        'type':         'web_server',
        'redirect_uri': os.getenv('BASECAMP_CALLBACK_URL'),
        'client_secret':os.getenv('BASECAMP_CLIENT_SECRET'),
        'code':         code,
    }
    #pprint(data)

    r = requests.post('https://launchpad.37signals.com/authorization/token', data=data)
    response = r.json()
    if 'access_token' in response.keys():
        with open('.bc_token','w') as f:
            f.write(response['access_token'])

    return jsonify({"status": "success", "message": "Callback received!"}), 200

@app.route('/ticktick_callback')
def ticktick_callback():
    request_data = request.args
    code = request_data['code']

    #pprint(code)

    data = {
        'client_id':    os.getenv('TICKTICK_CLIENT_ID'),
        'grant_type':         'authorization_code',
        'redirect_uri': os.getenv('TICKTICK_REDIRECT_URI'),
        'client_secret':os.getenv('TICKTICK_CLIENT_SECRET'),
        'code':         code,
        'scope':        'tasks:read',
    }
    #pprint(data)

    r = requests.post('https://ticktick.com/oauth/token', data=data)
    response = r.json()
    pprint(response)
    if 'access_token' in response.keys():
        with open('.tt_token','w') as f:
            f.write(response['access_token'])

    return jsonify({"status": "success", "message": "Callback received!"}), 200

# Execute the print job
if __name__ == '__main__':
    #pprint(f"Basecamp oAuth Link:  https://launchpad.37signals.com/authorization/new?type=web_server&client_id={ os.getenv('BASECAMP_CLIENT_ID') }&redirect_uri={ os.getenv( 'BASECAMP_CALLBACK_URL' )}")
    #pprint(f"Ticktick: https://ticktick.com/oauth/authorize?client_id={ os.getenv('TICKTICK_CLIENT_ID')}&scope=tasks:read&redirect_uri={os.getenv('TICKTICK_REDIRECT_URI')}&response_type=code")
    app.run(debug=False, host='0.0.0.0', port=5000)
    #print_news()
    #pprint(print_basecamp_tasks(None))
    #get_ticktick_tasks()
    #get_ticktick_api()
    #print_daily_basics(None)

