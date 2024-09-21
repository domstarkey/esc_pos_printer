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

# Step 1: Parse the RSS feed
RSS_FEED_URL = 'https://www.rnz.de/feed/139-RL_Heidelberg_free.xml'
feed = feedparser.parse(RSS_FEED_URL)

# Step 2: Connect to the ESC/POS printer
printer_ip = '192.168.2.134'

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Step 3: Format and print the news
@app.route('/print_news')
def print_news():
    try:

        printer= Network(printer_ip)
        # Print the feed title
        #printer.set(align='center', bold=True, double_height=True)
        printer.text("Heidelberg News\n")
        #printer.set(align='left', bold=False, double_height=False)
        printer.set(bold= False,normal_textsize=True)

        # Print each entry from the RSS feed
        for entry in feed.entries[:8]:  # Limit to the first 5 headlines
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

        # Step 4: Cut the paper
        printer.cut()
        return jsonify({"status": "success", "message": "Printed successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to print."}), 500

# Execute the print job
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
    #print_news()

