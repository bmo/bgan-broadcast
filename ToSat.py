import requests
import logging

logging.basicConfig(level=logging.DEBUG)
#
# to	+870772533943
#reply_email	spots@contestcq.com
# message	Spot+goes+here
s = requests.session()
req = s.get('http://connect.inmarsat.com/Services/Land/IsatPhone/SMS/sms.html')
logging.debug(req)
r = s.post('http://connect.inmarsat.com/gsps.ashx', data = {'to':'+870772533943',
                                                                   'reply_email' :'spots@contestcq.com',
                                                                   'message': 'Spot+goes+here'
                                                                   })
print(r)
print(r.text)