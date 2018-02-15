import logging
import telnetlib


class VE7CC_Upstream(object):
    VE7CC_HOST = 'dxc.ve7cc.net'
    VE7CC_PORT = 23

    def __init__(self, **kwargs):
        logging.debug(kwargs)
        self.login = kwargs.get('login')
        self.connection = telnetlib.Telnet()

    # do everything necessary to open a connx. Probably throw an exception if there's a problem
    def connect(self):
        logging.debug("connect")
        self.connection.open(self.VE7CC_HOST, self.VE7CC_PORT)
        #self.connection.set_debuglevel(3)
        txt = self.connection.read_until('login: ')
        logging.debug(txt)
        self.connection.write(self.login + '\n')
        self.connection.write('SET/WIDTH 90' + '\n')
        return True

    # shutdown
    def close(self):
        logging.debug("close")
        self.connection.close()

    # return lines read from upstream
    def read(self):
        # logging.debug("read")
        lines = self.connection.read_until('\r\n',1)
        lines = lines.rstrip()
        if lines != "":
            logging.debug("read {}".format(lines))
        else:
            lines = None
        return lines

