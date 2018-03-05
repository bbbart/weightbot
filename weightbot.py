#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

"""Telegram Bot to collect weight measurements and their timestamp into a
CSV file for some very simple statistical analysis and goal follow-up."""

import configparser
import csv
import logging
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pendulum
import telegram
from telegram.ext import BaseFilter, CommandHandler, MessageHandler, Updater

BASEDIR = Path(__file__).parent

CONFIG = configparser.ConfigParser(inline_comment_prefixes='#')
CONFIG.read((BASEDIR / 'config', BASEDIR / 'config.local'))
CONFIG = CONFIG[configparser.DEFAULTSECT]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

LOGGER = logging.getLogger(__name__)


class WeightFilter(BaseFilter):
    """Check if the given weight is acceptable or not."""

    @staticmethod
    def filter(message):
        """Check if the given weight is acceptable or not."""
        try:
            weight = float(message.text)
            return 50 < weight < 150
        except ValueError:
            return False


def bot_start(bot, update):
    """Send a welcome message."""
    update.message.reply_text(
        'Hi! Just type in your current weight and I\'ll store it for you!')


def bot_error(bot, update, error):
    """Log errors caused by updates."""
    LOGGER.warning(f'Update {update} caused error {error}')
    if update:
        update.message.reply_text('[some error occurred; check the log]')


def bot_weight(bot, update):
    """Store the given weight (if found acceptable)."""
    bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=telegram.ChatAction.TYPING)
    weight = update.message.text
    store_weight(weight)
    update.message.reply_text(f'{weight}kg successfully stored!')
    bot_stats(bot, update)


def bot_stats(bot, update):
    """Generate more elaborate progress statistics."""
    bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=telegram.ChatAction.TYPING)

    data = pd.read_csv(
        CONFIG['csvfile'],
        parse_dates=['timestamp'],
        index_col='timestamp')
    data.index = data.index.tz_localize('UTC').tz_convert('Europe/Brussels')

    weekweight_mean_weight = data.last('7d').weight.mean()

    weight_min_weight = data.loc[data.weight.idxmin()].weight
    weight_min_timestamp = pendulum.instance(
        data.weight.idxmin()).diff_for_humans()

    weight_max_weight = data.loc[data.weight.idxmax()].weight
    weight_max_timestamp = pendulum.instance(
        data.weight.idxmax()).diff_for_humans()

    x = matplotlib.dates.date2num(data.index.to_pydatetime())
    y = data.weight
    fit_a, fit_b = np.polyfit(x, y, deg=1)
    weight_loss = fit_a * (x[0] - x[-1])
    weight_loss_period = (data.index.max() - data.index.min()
                          ) / np.timedelta64(1, 'D')

    weight_goal = fit_a * x[0] + fit_b + \
        (12 * float(CONFIG['goal']) / 365 * weight_loss_period)
    weight_orig = fit_a * x[0] + fit_b
    weight_now = fit_a * x[-1] + fit_b

    fig, ax = plt.subplots()
    ax.plot(data, 'k.')
    ax.plot(x, fit_a * x + fit_b, 'g' if weight_now <= weight_goal else 'r')
    ax.plot([x[0], x[-1]], [weight_orig, weight_goal], '--', color='orange')
    ax.set_ylim([min(weight_goal, weight_min_weight) - 1,
                 weight_max_weight + 1])
    ax.yaxis.set_ticks_position('both')
    fig.autofmt_xdate()

    update.message.reply_text(
        f'Your weight mean the past week is {weekweight_mean_weight:.1f}kg. '
        f'The minimum over the complete period was {weight_min_weight:.1f}kg '
        f'({weight_min_timestamp}) and maximum was {weight_max_weight:.1f}kg '
        f'({weight_max_timestamp}).')
    bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=telegram.ChatAction.TYPING)

    with tempfile.NamedTemporaryFile(suffix='.png') as figfile:
        fig.savefig(figfile.name, bbox_inches='tight')
        update.message.reply_photo(figfile)
    gainedlost = 'lost' if weight_loss >= 0 else 'gained'
    update.message.reply_text(
        f'You have {gainedlost} {weight_loss:.1f}kg '
        f'in {weight_loss_period:.0f} days')


def store_weight(weight):
    """Write the given weight to the CSV file with the current timestamp."""
    with open(CONFIG['csvfile'], mode='a', newline='') as csvfile:
        weightwriter = csv.writer(csvfile)
        weightwriter.writerow([pendulum.now(), weight])


def main():
    """Run bot."""
    csvfile_path = Path(CONFIG['csvfile'])
    if not csvfile_path.is_file() or csvfile_path.stat().st_size == 0:
        with csvfile_path.open(mode='w', newline='') as csvfile:
            weightwriter = csv.writer(csvfile)
            weightwriter.writerow(['timestamp', 'weight'])

    updater = Updater(CONFIG['token'])

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', bot_start))
    dispatcher.add_handler(CommandHandler('stats', bot_stats))
    dispatcher.add_handler(MessageHandler(WeightFilter(), bot_weight))
    dispatcher.add_error_handler(bot_error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
