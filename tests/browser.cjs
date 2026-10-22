// Optional UI check: install Playwright + Chromium, run server, then node tests/browser.cjs.
const assert=require('node:assert/strict');
let chromium;try{({chromium}=require('playwright'));}catch{({chromium}=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright'));}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8080');await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('16 pulser'));
 assert.equal(await page.locator('.stage').count(),8);assert.equal(await page.locator('.chip').count(),16);
 await page.screenshot({path:'/tmp/metropolis-desktop.png',fullPage:true});
 await page.locator('#play').click();await page.waitForFunction(()=>document.querySelector('.stage.active'));await page.locator('#stop').click();assert.equal(await page.locator('.stage.active').count(),0);
 await page.locator('#stage0 select[data-key=pulses]').selectOption('3');await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('20 pulser'));
 await page.locator('#stage0 select[data-key=ratchet]').selectOption('4');await page.waitForFunction(()=>JSON.parse(document.querySelector('#debug').textContent).events[0].gates.length===4);
 await page.locator('#segments').fill('4x2, 3x2');await page.waitForFunction(()=>document.querySelector('#count').textContent==='');await page.locator('#play').click();assert.equal(await page.locator('.stage.active').count(),0);
 await page.locator('#canonical').click();await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('20 pulser'));
 for(let i=0;i<8;i++)await page.locator(`#stage${i} input[data-key=skip]`).check();await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('0 pulser'));
 for(let i=0;i<8;i++)await page.locator(`#stage${i} input[data-key=skip]`).uncheck();await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('20 pulser'));
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'/tmp/metropolis-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);console.log('PASS browser: canonical, play/stop, pulses, ratchet, invalid config, all-skip, mobile width, no JS errors');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
