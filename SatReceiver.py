#
# act like a local DX cluster spot server, getting spots from
# satellite SMS messages, and distributing them to clients
# uses the https://github.com/shmup/miniboa telnet server library

#

import logging
import telnetlib

import irc.client
import sys

import datetime

import time

from gsmmodem.modem import GsmModem, Sms
from gsmmodem.exceptions import TimeoutException, PinRequiredError, IncorrectPinError

from miniboa import TelnetServer
import VE7CCUpstream

IDLE_TIMEOUT = 300
CLIENT_LIST = []
UPSTREAMS = []
SERVER_RUN = True
CLUSTER_SERVER_PORT=7777

SATELLITE_IP = "192.168.128.100:1829"
#SATELLITE_IP = "192.168.128.100:1829"


SATELLITE = True
VE7CC = False
IRC = True

class SatelliteSMS(object):

    def __init__(self, port="socket://{}".format(SATELLITE_IP)):
        self.modem = GsmModem(port, 115200, AT_CNMI=None)

    def connect(self):
        self.modem.connect(None, waitingForModemToStartInSeconds=10)
        return True

    def split_sender(self, sms):
        line = sms.text
        sender, msg = line.split(" ",1)

        # could be from text msg, so leave message alone
        if not ("@" in sender):
            msg = sender + " " + msg
            if sms.number is not None:
                sender = sms.number
        # if the sender is 'Web text' then the sender's email or phone is the last word of the message
        if sender == 'Web text':
            sender = msg.rsplit(None, 1)[-1]
            msg = msg.rpartition(' ')[0]
        msg = msg.replace('\n', ' ').replace('\r', '')
        return {
            'sender':sender,
            'msg':msg
        }

    # returns an array of dict of sender and msg
    def read(self):
        messages = self.modem.listStoredSms(status = Sms.STATUS_RECEIVED_UNREAD, delete=True)

        if len(messages) == 0:
            return None
        logging.debug("Messages received {}".format(len(messages)))
        logging.debug("Messages {}".format(messages))

        messages = [ self.split_sender(x) for x in messages]
        #messages = [ x.text.split(" ",1)[-1] for x in messages ]
        # turns out that sometimes a space gets converted to a break... so fix that
        #messages = [ x.replace('\n', ' ').replace('\r', '') for x in messages ]

        logging.debug("Messages = {}".format(messages))
        return messages

    def close(self):
        self.modem.close()

class IRCCat(irc.client.SimpleIRCClient):

    def __init__(self, targets):
        irc.client.SimpleIRCClient.__init__(self)
        self._targets = targets
        self._started = {}
        for t in self._targets:
            self._started[t] = False

    def on_welcome(self, connection, event):
        logging.debug("on_welcome")

        for t in self._targets:
            if irc.client.is_channel(t):
                connection.join(t)

    def on_join(self, connection, event):
        logging.debug("on_join for ".format(event.target))
        self._started[event.target] = True

    def on_disconnect(self, connection, event):
        logging.debug("on_disconnect: {}".format(event))
        #sys.exit(0)

    def send_line(self, target, line):
        if self._started.get(target) is not None and self._started[target]:
            self.connection.privmsg(target, line)
        else:
            logging.debug("Ignoring line since IRC note ready: {}".format(line))

    def process(self):
        self.reactor.process_once()

    def close(self):
        self.connection.quit("")

class IRCWriter(object):
    def __init__(self, targets, **kwargs):
        # target is the channel name
        self._c = IRCCat(targets)
        self._server = kwargs.get('server','192.168.128.99')
        self._port = kwargs.get('port', int('6667'))
        self._nickname = kwargs.get('nickname', 'IRCWriter')

    def connect(self):
        try:
            self._c.connect(self._server, self._port, self._nickname)
        except irc.client.ServerConnectionError as x:
            print(x)

    def write(self,target, msg):
        if type(msg) is list:
            for m in msg:
                self._c.send_line(target, m.rstrip())
        else:
            self._c.send_line(target, msg.rstrip())

    def process(self):
        self._c.process()

    def close(self):
        self._c.close()

def on_connect(client):
    """
    Sample on_connect function.
    Handles new connections.
    """
    logging.info("Opened connection to {}".format(client.addrport()))
    broadcast("{} connected.\n".format(client.addrport()))
    CLIENT_LIST.append(client)
    client.send("DXpedition Spot Server {}.\n".format(client.addrport()))


def on_disconnect(client):
    """
    Sample on_disconnect function.
    Handles lost connections.
    """
    logging.info("Lost connection to {}".format(client.addrport()))
    CLIENT_LIST.remove(client)
    broadcast("{} leaves the conversation.\n".format(client.addrport()))


def kick_idle():
    """
    Looks for idle clients and disconnects them by setting active to False.
    """
    # Who hasn't been typing?
    for client in CLIENT_LIST:
        if client.idle() > IDLE_TIMEOUT:
            logging.info("Kicking idle lobby client from {}".format(client.addrport()))
            client.active = False

def process_clients():
    """
    Check each client, if client.cmd_ready == True then there is a line of
    input available via client.get_command().
    """
    for client in CLIENT_LIST:
        if client.active and client.cmd_ready:
            # If the client sends input, just show it in log
            logging.debug("process_clients: {}".format(client.get_command()))


def broadcast(msg):
    """
    Send msg to every client.
    """
    for client in CLIENT_LIST:
        if type(msg) is list:
            for m in msg:
                client.send(m + '\n')
        else:
            client.send(msg + '\n')


def chat(client):
    """
    Echo whatever client types to everyone.
    """
    global SERVER_RUN
    msg = client.get_command()
    logging.info("{} says '{}'".format(client.addrport(), msg))

    for guest in CLIENT_LIST:
        if guest != client:
            guest.send("{} says '{}'\n".format(client.addrport(), msg))
        else:
            guest.send("You say '{}'\n".format(msg))

    cmd = msg.lower()
    # bye = disconnect
    if cmd == 'bye':
        client.active = False
    # shutdown == stop the server
    elif cmd == 'shutdown':
        SERVER_RUN = False


if __name__ == '__main__':

    # Simple chat server to demonstrate connection handling via the
    # async and telnet modules.

    logging.basicConfig(level=logging.DEBUG)

    # Create a telnet server with a port, address,
    # a function to call with new connections
    # and one to call with lost connections.

    telnet_server = TelnetServer(
        port=CLUSTER_SERVER_PORT,
        address='',
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        timeout = 0.05
        )

    if IRC:
        irc_writer = IRCWriter(['#spots', '#misc', '#news', '#n9adg'], nickname='SatSpotter')
        irc_writer.connect()

    # Enable to have a source of test spots
    if VE7CC:
        ve7cc_upstream = VE7CCUpstream.VE7CC_Upstream(login="n9adg-9")
        ve7cc_upstream.connect()

    # Enable to get spots from the Satellite
    if SATELLITE:
        sat_upstream = SatelliteSMS()
        sat_upstream.connect()

    logging.info("Listening for connections on port {}. CTRL-C to break.".format(telnet_server.port))

    start_time = datetime.datetime.now()

    logging.debug("Initial 5 second startup for IRC connections")

    # Server Loop
    while SERVER_RUN:
        telnet_server.poll()        # Send, Recv, and look for new connections
        # kick_idle()                 # Check for idle clients

        line = None

        time_now = datetime.datetime.now()

        if IRC:
            irc_writer.process()

            # initialize for 5 seconds
            td = time_now - start_time
            if td.total_seconds() < 15.0:
                continue

        if VE7CC:
            line = ve7cc_upstream.read()
            if line != None:
                broadcast(line)

        if SATELLITE:
            msgs = sat_upstream.read()
            if msgs is not None:
                # process the messages based on the sender
                #
                for m in msgs:
                    logging.debug("Message {}".format(m))

                    if m['sender'] == 'spot@contestcq.com':

                        # send to connected spot clients
                        broadcast(m['msg'])

                        if IRC:
                            irc_writer.write('#spots', m['msg'])

                    elif m['sender'] == 'news@contestcq.com':
                        if IRC:
                            irc_writer.write('#news', m['msg'])
                    else:
                        irc_writer.write('#misc',m['msg'])



        process_clients()           # Check for client input

        if line is None:
            if SATELLITE:
                time.sleep(1.0)
            else:
                time.sleep(0.02)

    logging.info("Server shutdown.")

