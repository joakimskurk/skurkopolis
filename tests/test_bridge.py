import importlib.util
import unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('server',Path(__file__).resolve().parents[1]/'host/server.py');server=importlib.util.module_from_spec(s);s.loader.exec_module(server)
def config():return {'segments':[[1,3,2],[4,5,2],[6,8,2]],'stages':[dict(note=48+i,pulses=1,ratchet=1,skip=0,rest=0) for i in range(8)]}
class Bridge(unittest.TestCase):
 def test_canonical(self):self.assertEqual([e['stage'] for e in server.trace(config())['events']],[1,2,3,1,2,3,4,5,4,5,6,7,8,6,7,8])
 def test_max_cycle(self):
  c=config();c['segments']=[[1,8,8]]
  for s in c['stages']:s.update(pulses=8,ratchet=4)
  events=server.trace(c)['events'];self.assertEqual(len(events),512);self.assertTrue(all(len(e['gates'])==4 for e in events))
 def test_empty(self):
  c=config()
  for s in c['stages']:s['skip']=1
  self.assertEqual(server.trace(c)['events'],[])
 def test_invalid(self):
  for key,value in [('pulses',0),('ratchet',5),('note',128),('skip',True),('pulses',1.5)]:
   c=config();c['stages'][0][key]=value
   with self.assertRaises(ValueError):server.trace(c)
 def test_gap_overlap_and_shape(self):
  for seg in ([[1,3,2],[3,8,2]],[[1,3,2],[5,8,2]],[],[[1,8,0]],'bad'):
   c=config();c['segments']=seg
   with self.assertRaises(ValueError):server.trace(c)
if __name__=='__main__':unittest.main()
