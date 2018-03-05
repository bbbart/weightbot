# Weightbot
Telegram bot to keep track of a user's weight and provide them with useful statistics to evaluate their weight evolution over time agains a set goal.

Usage:
* Edit the config section in weighbot.py to suit your preferences
* Run the bot somewhere on a server with HTTP access to the Internet
* Find it on Telegram and say /start to it
* Add your weight as simple floats from time to time

Warning:
* This bot only knows about a single database (CSV file) which is not user dependent. Basically, this bot is for one user only.

Commands:
* /start: greets you
* /stats: presents you with some statistics on the logged weights
