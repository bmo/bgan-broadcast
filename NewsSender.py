
import logging
import re
import random
import sqlite3

import feedparser

import sys
import os

import textwrap

import DeliveryMethods

from time import sleep


USE_EMAIL = False
USE_WEBPOST = True

REALLY_SEND = True

SATELLITE_PHONE = '+870772533943'
SATELLITE_EMAIL = "870772533943@message.inmarsat.com"
NEWS_SENDER = 'news@contestcq.com'

MAILGUN_API_KEY = None
MAILGUN_API_URL = None


if USE_EMAIL:
    # get mailgun credentials from environment

    for x in ['MAILGUN_API_KEY', 'MAILGUN_API_URL']:
        if os.environ.get(x) is None:
            print("{} must be specified in environment if using email delivery".format(x))
            sys.exit(-1)
        else:
            globals()[x] = os.environ.get(x)


class NewsSender(object):

    ARTICLE_DB_NAME = "articles.sqlite3"

    def __init__(self, **kwargs):
        self._send = kwargs.get("send",False)

        if USE_EMAIL:
            self._mg = DeliveryMethods.MailGun(send_url=MAILGUN_API_URL,
                           api_key=MAILGUN_API_KEY,
                           sender=NEWS_SENDER)
        if USE_WEBPOST:
            self._webpost = DeliveryMethods.WebInmarsatSend(sender=NEWS_SENDER)
        self._db = sqlite3.connect(self.ARTICLE_DB_NAME)
        self.open_or_create_db()

    def open_or_create_db(self):
        c = self._db.cursor()
        # Creating a new SQLite table with 1 column
        c.execute('CREATE TABLE IF NOT EXISTS {tn} ({nf} {ft})'\
            .format(tn='articles_seen', nf='article_id', ft='VARCHAR'))
        self._db.commit()

    def mail(self, text):
        if USE_EMAIL:
            r = self._mg.send(subject='news', to=SATELLITE_EMAIL, text=text)
            logging.debug('Mailgun status:{}, text:{}'.format(r.status_code, r.text))
        if USE_WEBPOST:
            r = self._webpost.send(subject='news', to=SATELLITE_PHONE, text=text)

    def get_articles(self,url):
        feed = None
        try:
            feed = feedparser.parse(url)
        except:
            logging.debug("Exception")

        return feed

    def seen_it(self, entry):
        c = self._db.cursor()
        c.execute('SELECT * from articles_seen where article_id=?',(entry.id,))
        r = c.fetchone()

        if r is not None:
            logging.debug("see  n article {}".format(entry,id))
            return True
        else:
            return False

    def remove_seen(self, feed, url):
        new_feed = []
        # reconcile the feed against articles we've seen. Remove entries we've seen
        for entry in feed:
            if not self.seen_it(entry):
                new_feed.append(entry)

        return new_feed

    def send_feed(self,name, entries):
        MAX_LEN = 120
        calculated_max = MAX_LEN - len(name) - 8
        for entry in entries:
            text = entry['title']
            lines = textwrap.wrap(text, calculated_max)

            text = entry['summary']
            text = re.sub("<.*?>", "", text)

            lines = lines + textwrap.wrap(text, calculated_max)

            # generate a story number and append on a count
            story = '%04x' % random.randrange(16 ** 4)
            linecount = 1
            for line in lines:
                logging.debug("{}-{}-{:1}:{}".format(name, story, linecount, line.encode('ascii','replace')))
                if self._send:
                    self.mail("{}-{}-{:1}:{}".format(name, story, linecount, line.encode('ascii','replace')))
                    # TODO need some sort of delay??? Where do some of the messages go?
                linecount = linecount + 1

    def save_seen(self,name, entries):
        # add these to our db as seen
        c = self._db.cursor()
        list = [ (x.id,) for x in entries ]
        c.executemany("INSERT INTO articles_seen ('article_id') VALUES (?)", list)
        self._db.commit()

    def run(self, name, the_url):
        feed = self.get_articles(the_url)
        cleaned_feed = self.remove_seen(feed.entries, the_url)
        self.save_seen(name, cleaned_feed)
        self.send_feed(name, cleaned_feed)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    n = NewsSender(send=REALLY_SEND)
    n.run('reuters','http://feeds.reuters.com/reuters/topNews')
    #n.run('reuters','http://feeds.reuters.com/Reuters/domesticNews')
    #n.run('bbc','http://feeds.bbci.co.uk/news/rss.xml#')
    #n.run('wired','https://www.wired.com/feed/rss')