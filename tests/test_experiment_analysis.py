import sys
import unittest
import test_bus_trace as bt
ROOT=bt.ROOT
sys.path.insert(0,str(ROOT/'host'))
from experiment_analysis import summarize_window,word_reads


class ExperimentAnalysisTests(unittest.TestCase):
    def key_frame(self,value):
        source=bt.DecoderTests().waveform([0x49,0,0],released_from=1)
        events=[]
        for i,e in enumerate(source):
            events.append(e)
            if i>=27 and (i-27)%3==0 and (i-27)//3<16:
                bit=(i-27)//3
                events.append(dict(e,cycle=e['cycle']+1,kind='read',address=0x23,
                                   pc=0x7ac if bit<8 else 0x7e6,value=((value>>bit)&1)<<3))
        return events

    def test_complete_key_frame_requires_all_sixteen_samples(self):
        e=self.key_frame(0x8123)
        self.assertEqual(summarize_window(e)['completeKeyWords'],{0x8123:1})
        del e[next(i for i,x in enumerate(e) if x['kind']=='read')]
        with self.assertRaises(ValueError):summarize_window(e)

    def test_partial_gpio_frames_are_excluded_from_key_counts(self):
        e=self.key_frame(1)
        s=summarize_window(e[5:-1])
        self.assertEqual(s['completeKeyWords'],{})
        self.assertEqual(s['partialGpioFrames'],1)

    def test_display_values_are_distinct_from_write_sequence_count(self):
        e=bt.DecoderTests().waveform([0,1,2,3,4,5,6])
        one=summarize_window(e)
        two=summarize_window(e+[dict(x,cycle=x['cycle']+1000) for x in e])
        self.assertEqual(one['displayPayloads'][0]['bytes'],[1,2,3,4,5,6])
        self.assertEqual(two['displayPayloads'][0]['count'],2)
        self.assertNotEqual(one['writeSequenceSha256'],two['writeSequenceSha256'])

    def test_spi_boundaries_allow_only_initial_low_and_final_high(self):
        def e(pc,v):return dict(kind='read',address=0x4e,pc=pc,value=v)
        s=word_reads([e(2,9),e(1,0x12),e(2,0x34),e(1,0x56)],1,2)
        self.assertEqual(s,{'wordCounts':{0x1234:1},'partialAtStart':True,'partialAtStop':True})
        for items in ([e(2,1),e(2,2)],[e(1,1),e(1,2)]):
            with self.assertRaises(ValueError):word_reads(items,1,2)


if __name__=='__main__':unittest.main()
