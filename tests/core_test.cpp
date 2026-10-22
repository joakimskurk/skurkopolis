#include "sequencer.h"
#include <cstdio>
#include <cstdlib>
#define CHECK(x) do { if(!(x)){std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);std::exit(1);} } while(0)
using namespace metro;
int main(){
 Engine e; Pulse x; Phrase p=canonical();
 const int order[]={1,2,3,1,2,3,4,5,4,5,6,7,8,6,7,8};
 for(int cycle=0;cycle<3;++cycle)for(int n:order){CHECK(e.next(x));CHECK(x.position.stage+1==n);CHECK(x.position.cycle==static_cast<unsigned>(cycle));}
 e.reset();CHECK(e.next(x)&&x.position.stage==0&&x.position.cycle==0);
 p.stages[0].pulses=3;p.stages[0].ratchet.count=4;CHECK(e.configure(p));
 for(int i=0;i<3;++i){CHECK(e.next(x));CHECK(x.position.stage==0&&x.position.pulse==i&&x.gateCount==4);CHECK(x.gates[3].offset==90&&x.gates[3].duration==15);}
 CHECK(e.next(x)&&x.position.stage==1);
 // Rejected configuration must not rewind or overwrite running state.
 Phrase bad=p;bad.segments[0].repeats=0;CHECK(!e.configure(bad));CHECK(e.next(x)&&x.position.stage==2);
 p=canonical();for(auto& s:p.stages)s.skip=true;CHECK(e.configure(p));CHECK(!e.next(x)&&x.gateCount==0);
 p.stages[7].skip=false;CHECK(e.configure(p));CHECK(e.next(x)&&x.position.stage==7);CHECK(e.next(x)&&x.position.repeat==1);CHECK(e.next(x)&&x.position.cycle==1);
 p=canonical();p.stages[0].rest=true;CHECK(e.configure(p));CHECK(e.next(x)&&x.gateCount==0);CHECK(e.next(x)&&x.position.stage==1);
 bad=canonical();bad.count=0;CHECK(!valid(bad));bad.count=9;CHECK(!valid(bad));
 bad=canonical();bad.segments[1].first=2;CHECK(!valid(bad));bad=canonical();bad.segments[2].last=6;CHECK(!valid(bad));
 bad=canonical();bad.stages[0].pulses=0;CHECK(!valid(bad));bad=canonical();bad.stages[0].ratchet.count=5;CHECK(!valid(bad));
 // Independent oracle across every pulse/ratchet/repeat combination, nonuniform stages.
 unsigned checks=0;
 for(int pc=1;pc<=8;++pc)for(int rc=1;rc<=4;++rc)for(int repeat=1;repeat<=8;++repeat){
  p=canonical();for(auto& s:p.stages){s.pulses=pc;s.ratchet.count=rc;}p.stages[3].skip=true;p.stages[6].rest=true;
  for(int s=0;s<3;++s)p.segments[s].repeats=repeat;
  CHECK(e.configure(p));
  for(int cy=0;cy<2;++cy)for(int s=0;s<3;++s)for(int r=0;r<repeat;++r)for(int st=p.segments[s].first;st<=p.segments[s].last;++st){
   if(st==3)continue;
   for(int pulse=0;pulse<pc;++pulse){CHECK(e.next(x));CHECK(x.position.cycle==static_cast<unsigned>(cy)&&x.position.segment==s&&x.position.repeat==r&&x.position.stage==st&&x.position.pulse==pulse);
    CHECK(x.gateCount==(st==6?0:rc));for(int g=0;g<x.gateCount;++g){CHECK(x.gates[g].offset==g*120/rc);CHECK(x.gates[g].offset+x.gates[g].duration<=120);}++checks;}
  }
 }
 std::printf("PASS canonical/reset/validation/skip/rest; %u oracle pulses; Phrase=%zu Engine=%zu Pulse=%zu bytes (host)\n",checks,sizeof(Phrase),sizeof(Engine),sizeof(Pulse));
}
