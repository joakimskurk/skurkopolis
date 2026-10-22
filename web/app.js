'use strict';
const $=id=>document.getElementById(id);
const notes=[48,50,55,53,57,55,59,60];
const stages=notes.map(note=>({note,pulses:1,ratchet:1,skip:0,rest:0}));
const noteName=n=>['C','C♯','D','D♯','E','F','F♯','G','G♯','A','B♭','B'][n%12]+(Math.floor(n/12)-1);
let startToken=0;
let events=[],revision=0,ctx,master,playing=false,timer,frame,nextTime=0,eventIndex=0,visual=[],voices=new Set();
function stop(){++startToken;playing=false;clearInterval(timer);cancelAnimationFrame(frame);visual=[];for(const o of voices){try{o.stop()}catch{}}voices.clear();document.querySelectorAll('.stage').forEach(e=>e.classList.remove('active'));$('position').textContent='KLAR';$('play').textContent='Spill';}
for(let i=0;i<8;i++){
 const el=document.createElement('div');el.className='stage';el.id='stage'+i;
 el.innerHTML=`<h3>${String(i+1).padStart(2,'0')}<span class="led"></span></h3><div class="pitch"><input aria-label="Tone trinn ${i+1}" type="range" min="36" max="84" value="${stages[i].note}" data-key="note"></div><output class="note">${noteName(stages[i].note)}</output><label class="field">PULSER<select data-key="pulses">${Array.from({length:8},(_,j)=>`<option>${j+1}</option>`).join('')}</select></label><label class="field">RATCHET<select data-key="ratchet">${[1,2,3,4].map(n=>`<option>${n}</option>`).join('')}</select></label><label class="toggle"><input type="checkbox" data-key="skip"> Skip</label><label class="toggle"><input type="checkbox" data-key="rest"> Rest</label>`;
 el.addEventListener('input',ev=>{const k=ev.target.dataset.key;if(!k)return;stages[i][k]=ev.target.type==='checkbox'?Number(ev.target.checked):Number(ev.target.value);el.querySelector('.note').textContent=noteName(stages[i].note);stop();refresh();});$('stages').append(el);
}
function configuration(){let start=1;const segments=$('segments').value.split(',').map(raw=>{const m=/^\s*([1-8])\s*x\s*([1-8])\s*$/i.exec(raw);if(!m)throw Error('Bruk formatet 3x2, 5x2, 8x2.');const row=[start,Number(m[1]),Number(m[2])];start=row[1]+1;return row;});return {segments,stages};}
async function refresh(){
 const ticket=++revision;events=[];$('engineBadge').textContent=$('engine').value==='avr'?'SIMAVR / AVR CODE':'NATIVE C++ CORE';
 try{const response=await fetch($('engine').value==='avr'?'/api/trace/avr':'/api/trace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(configuration())});const data=await response.json();if(ticket!==revision)return;if(!response.ok)throw Error(data.error);events=data.events;const sim=data.simulation;$('simulation').textContent=sim?`AVR-maskinkode · ${sim.flashImageBytes} B flash · ${sim.staticSramBytes} B statisk RAM · ${sim.observedStackBytes} B observert stack · ${sim.maxRequestCycles} sykler maks. per instrumentert forespørsel. simavr-signatur ${sim.modelSignature}; 16 MHz testklokke, rev010 ikke emulert.`:'Native C++ på vertsmaskinen. Ingen AVR-minne- eller syklusemulering.';$('order').replaceChildren();let last='';
 for(const e of events){const c=document.createElement('span');const group=e.segment+':'+e.repeat;c.className='chip'+(group!==last?' boundary':'');c.textContent=e.stage+(e.pulse>1?'.'+e.pulse:'');c.title=`Segment ${e.segment}, repetisjon ${e.repeat}, puls ${e.pulse}`;$('order').append(c);last=group;}
 $('count').textContent=`${events.length} pulser / frase`;$('debug').textContent=JSON.stringify(data,null,2);$('status').textContent=events.length?'Frasen er beregnet av C++-kjernen. Klar for avspilling.':'Alle trinn er hoppet over. Ingen klokker eller toner spilles.';
 }catch(error){if(ticket!==revision)return;$('simulation').textContent='Ingen gyldig kjøring fra valgt motor.';$('order').replaceChildren();$('count').textContent='';$('debug').textContent='';$('status').textContent=error.message;}
}
function schedule(){
 if(!playing)return;
 const beat=60/Number($('bpm').value);
 // Never burst-play missed pulses after background suspension.
 if(nextTime<ctx.currentTime-.05){stop();$('status').textContent='Avspilling stoppet etter forsinkelse. Trykk Spill igjen.';return;}
 while(nextTime<ctx.currentTime+.12){
  const e=events[eventIndex];visual.push({time:nextTime,event:e});
  for(const [offset,length] of e.gates){const t=nextTime+offset/120*beat,d=length/120*beat;const o=ctx.createOscillator(),g=ctx.createGain();o.type='triangle';o.frequency.value=440*2**((e.note-69)/12);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.7,t+.003);g.gain.setValueAtTime(.7,t+Math.max(.003,d-.008));g.gain.linearRampToValueAtTime(0,t+d);o.connect(g).connect(master);voices.add(o);o.onended=()=>{voices.delete(o);o.disconnect();g.disconnect();};o.start(t);o.stop(t+d+.005);}
  nextTime+=beat;eventIndex=(eventIndex+1)%events.length;
 }
}
function draw(){if(!playing)return;while(visual.length&&visual[0].time<=ctx.currentTime){const e=visual.shift().event;document.querySelectorAll('.stage').forEach((s,i)=>s.classList.toggle('active',i===e.stage-1));$('position').textContent=`SEG ${e.segment} · REP ${e.repeat} · TRINN ${e.stage} · PULS ${e.pulse}`;}frame=requestAnimationFrame(draw);}
$('play').onclick=async()=>{if(playing){stop();return;}const bpm=Number($('bpm').value);if(!Number.isFinite(bpm)||bpm<30||bpm>240){$('status').textContent='Tempo må være 30–240 BPM.';return;}if(!events.length){$('status').textContent='Ingen spillbar frase. Kontroller segmentene og Skip.';return;}
 const token=++startToken;const rev=revision;
 try{ctx??=new AudioContext();master??=ctx.createGain();master.disconnect();master.connect(ctx.destination);master.gain.value=Number($('volume').value);await ctx.resume();if(token!==startToken||rev!==revision)return;playing=true;eventIndex=0;nextTime=ctx.currentTime+.06;$('play').textContent='Pause';schedule();timer=setInterval(schedule,25);draw();}catch(e){stop();$('status').textContent='Lyd kunne ikke startes: '+e.message;}};
$('stop').onclick=stop;$('volume').oninput=()=>{if(master)master.gain.setTargetAtTime(Number($('volume').value),ctx.currentTime,.015);};$('bpm').oninput=stop;
$('engine').onchange=()=>{stop();refresh();};
$('segments').oninput=()=>{stop();refresh();};$('canonical').onclick=()=>{stop();$('segments').value='3x2, 5x2, 8x2';refresh();};$('straight').onclick=()=>{stop();$('segments').value='8x1';refresh();};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});refresh();
