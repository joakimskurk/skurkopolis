import json
import os
import threading
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from test_bridge import server,config
class HTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=HTTPServer(('127.0.0.1',0),server.Handler)
  cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
  cls.base='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join()
 def test_health(self):
  with urllib.request.urlopen(self.base+'/api/health') as r:self.assertEqual(json.load(r)['engine'],'native-cpp')
 def test_trace(self):
  req=urllib.request.Request(self.base+'/api/trace',data=json.dumps(config()).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req) as r:self.assertEqual(len(json.load(r)['events']),16)
 def test_static_allowlist(self):
  for path in ['/', '/style.css','/app.js']:
   with urllib.request.urlopen(self.base+path) as r:self.assertEqual(r.status,200)
  with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(self.base+'/../core/sequencer.h')
  self.assertEqual(cm.exception.code,404)
 def test_bad_requests(self):
  for data,mime,code in [(b'{}','application/json',400),(b'not json','application/json',400),(b'{}','text/plain',415),(b' '*8193,'application/json',400)]:
   req=urllib.request.Request(self.base+'/api/trace',data=data,headers={'Content-Type':mime})
   with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req)
   self.assertEqual(cm.exception.code,code)

 @unittest.skipUnless(os.environ.get('RUN_AVR_TESTS')=='1','AVR build required')
 def test_avr_trace(self):
  req=urllib.request.Request(self.base+'/api/trace/avr',data=json.dumps(config()).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req) as r:
   result=json.load(r)
   self.assertEqual(len(result['events']),16)
   self.assertEqual(result['simulation']['engine'],'simavr')
   self.assertFalse(result['simulation']['boardEmulated'])
