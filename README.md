# bgan-broadcast
One-way information broadcast via Inmarsat text service for DX spots, headlines, miscellaneous

Python-based utilities for the following:

spotserver.py - Connects to a Hughes HNS9201 terminal, extracts text messages. Pushes some information to an IRC Channel, serves up DX Spots via it's own telnet server, and writes information to a log file. Requires https://github.com/bmo/python-gsmmodem which has been tweaked for the HNS9201 terminal.

SpotSender.py - Run this one in the cloud or on a reliable server somewhere. It connects to a DX cluster (in this case VE7CC) and obtains spots, filters to ones that should be sent, and submits them via the BGAN network. BGAN has an email gateway and a web page; the email gateway is less reliable than the web page. Delayed or out of order messages are the norm. Sometimes either service goes down for hours days with no notice.

NewsSender.py - Collects stories from various sites RSS feeds, splits them into satellite-friendly sizes, labels and numbers, sends them along. Keeps a small Sqlite DB of articles it's seen before so only new ones are sent. Nothing special here. Were this more complicated, the first message would contain the number of pieces, and the client side would do the re-assembly.  

VE7CC_Upstream.py - support for spotsender.py, opens and hangs out on a VE7CC packet cluster connection, heaving up lines of information when available

