import requests
import logging


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
