import requests
import logging
import VE7CCUpstream
import re
import os
import sys

from time import sleep

#
# get spots. Filter them the way we want them. Send them via email or web form post through the satellite
#

SATELLITE_PHONE = '+870772533943'
SATELLITE_EMAIL = "870772533943@message.inmarsat.com"

USE_EMAIL = False
USE_WEBPOST = True

VE7CC_LOGIN = "n9adg-9"

MAILGUN_API_KEY = None
MAILGUN_API_URL = None
SPOT_SENDER = 'spot@contestcq.com'

if USE_EMAIL:
  # get mailgun credentials from environment

  for x in ['MAILGUN_API_KEY', 'MAILGUN_API_URL']:
    if os.environ.get(x) is None:
      print("{} must be specified in environment if using email delivery".format(x))
      sys.exit(-1) 
    else:
      globals()[x] = os.environ.get(x)
      
# TODO move the delivery classes out of here to own files

class MailGun(object):

    def __init__(self, **kwargs):
        self._sender = kwargs.get('sender')
        self._api_key = kwargs.get('api_key')
        self._send_url = kwargs.get('send_url', 'https://api.mailgun.net/v3/samples.mailgun.org/messages')
        self._default_from = kwargs.get('sender')

    def send(self, **kwargs):
        subject = kwargs.get('subject','')
        sender = kwargs.get('from',self._sender)
        to = kwargs.get('to','')
        text = kwargs.get('text', '')
        logging.debug("sending mail {} to {}".format(self._send_url,to))
        r = requests.post(self._send_url, auth=('api', self._api_key),
                          data = {
                              'to': to,
                              'from' : sender,
                              'subject' : subject,
                              'text' : text
                          })
        return r

class WebInmarsatSend(object):

    INMARSAT_SEND_URL = 'http://connect.inmarsat.com/Services/Land/IsatPhone/SMS/sms.html'
    INMARSAT_SEND_POST = 'http://connect.inmarsat.com/gsps.ashx'

    def __init__(self, **kwargs):
        self._sender = kwargs.get('sender')
        pass

    def send(self, **kwargs):
        text = kwargs.get('text', '')
        sender = kwargs.get('from', self._sender)
        to = kwargs.get('to', '')
        s = requests.session()
        req = s.get(self.INMARSAT_SEND_URL)
        #logging.debug(req)
        logging.debug("posting {} to {}".format(text, to))
        r = s.post(self.INMARSAT_SEND_POST, data={'to': to,
                                                  'reply_email': sender,
                                                  'message': text
                                                                  })
        print(r)

class SpotSender(object):
    def __init__(self):
        self._ve7cc_upstream = None
        self._mg = MailGun(send_url=MAILGUN_API_URL,
                 api_key=MAILGUN_API_KEY,
                 sender=SPOT_SENDER)

        self._webpost = WebInmarsatSend(sender=SPOT_SENDER)

    def mail(self, text):
        if USE_EMAIL:
            r = self._mg.send(subject='sp', to=SATELLITE_EMAIL, text=text)
            logging.debug('Mailgun status:{}, text:{}'.format(r.status_code, r.text))
        elif USE_WEBPOST:
            r = self._webpost.send(subject='sp', to=SATELLITE_PHONE, text=text)


    def init_ve7cc(self):
        self._ve7cc_upstream = VE7CCUpstream.VE7CC_Upstream(login=VE7CC_LOGIN)
        self._ve7cc_upstream.connect()

    #
    #
    # --------- Change these filters to suit.
    #
    #
    #
    #
    def filter(self, line):
        # return a filtered version of the line if we want it, otherwise, None
        #
        if line is None:
            return None

        # Only report skimmer spots on the half hours

        m = re.match(r".*\sdB\s+.*(\d{4})Z$", line)

        if m is not None:
            mins = int(m.group(1)) % 100
            if mins <= 5 or ((mins >= 30) and (mins <=35)):
                pass
            else:
                logging.debug("Skipping skimmer spot outside time window {}".format(line))
                return None
        #

        if re.match(r".*VK9MA.*", line):
            return line

        if re.match(r".*\s+N9ADG.*", line):
            return line

        if re.match(r".*N7QT.*", line):
            return line

        if re.match(r".*3G9A.*", line):
            return line

        return None

    def run(self):
        if self._ve7cc_upstream is None:
            self.init_ve7cc()

        while True:
            line = self._ve7cc_upstream.read()
            if self.filter(line) is not None:
                logging.debug("VE7CC: [{}]".format(line))
                self.mail(line+"\n")
                sleep(0.25)
            sleep(0.1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    s = SpotSender()
    s.run()
