#include "sequencer.h"
#include <iostream>
// Bounded whitespace protocol from trusted local bridge; no files or shell commands.
int main(){
 metro::Phrase p={}; int count;
 if(!(std::cin>>count) || count<1 || count>8) return 2;
 p.count=static_cast<uint8_t>(count);
 for(int i=0;i<count;++i){int a,b,r;if(!(std::cin>>a>>b>>r)||a<0||a>7||b<0||b>7||r<1||r>8)return 2;
  p.segments[i]={static_cast<uint8_t>(a),static_cast<uint8_t>(b),static_cast<uint8_t>(r)};}
 for(auto& s:p.stages){int n,pc,rc,sk,re;if(!(std::cin>>n>>pc>>rc>>sk>>re)||n<0||n>127||pc<1||pc>8||rc<1||rc>4||sk<0||sk>1||re<0||re>1)return 2;
  s={static_cast<uint8_t>(n),static_cast<uint8_t>(pc),{static_cast<uint8_t>(rc)},sk!=0,re!=0};}
 std::cin>>std::ws;if(!std::cin.eof())return 2;
 metro::Engine e;if(!e.configure(p))return 2;
 std::cout<<"{\"ticksPerPulse\":120,\"events\":[";
 metro::Pulse x;bool first=true;
 for(int i=0;i<513 && e.next(x);++i){
  if(x.position.cycle>0)break;
  if(!first)std::cout<<",";
  first=false;
  std::cout<<"{\"stage\":"<<int(x.position.stage)+1<<",\"segment\":"<<int(x.position.segment)+1
   <<",\"repeat\":"<<int(x.position.repeat)+1<<",\"pulse\":"<<int(x.position.pulse)+1
   <<",\"note\":"<<int(x.note)<<",\"gates\":[";
  for(int j=0;j<x.gateCount;++j){if(j)std::cout<<",";std::cout<<"["<<x.gates[j].offset<<","<<x.gates[j].duration<<"]";}
  std::cout<<"]}";
 }
 std::cout<<"]}\n";
}
