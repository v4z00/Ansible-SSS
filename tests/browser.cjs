'use strict';
// Run the shipped inline browser script against a small, isolated DOM fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.value = ''; this.children = []; this.dataset = {};
    this.listeners = {}; this.textContent = '';
  }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  append(element) { this.children.push(element); element.parentElement = this; }
  replaceChildren() { this.children = []; }
  remove() {
    const parent = this.parentElement;
    parent.children = parent.children.filter(child => child !== this);
  }
  querySelectorAll(tagName) {
    return this.children.flatMap(child => [...(child.tagName === tagName ? [child] : []), ...child.querySelectorAll(tagName)]);
  }
}
async function exercise(initialLanguage, local) {
  const nodes = new Map(), labels = [];
  for (const tag of source.matchAll(/<(\w+)[^>]*>/g)) {
    const node = new Element(tag[1]), id = tag[0].match(/ id="([^"]+)"/);
    const label = tag[0].match(/ data-label="([^"]+)"/);
    if (id) nodes.set(id[1],node);
    if (label) { node.dataset.label = label[1]; labels.push(node); }
  }
  const get = id => nodes.get(id);
  get('category').value = 'master';
  const document = {documentElement:{lang:initialLanguage},getElementById:get,createElement:tag=>new Element(tag),
    createTextNode:text=>Object.assign(new Element('text'),{textContent:text}),querySelectorAll:()=>labels};
  const calls = [], window = new Element('window');
  let expiry;
  const context = vm.createContext({document,window,location:local?{protocol:'http:',hostname:'127.0.0.1'}:{protocol:'file:',hostname:''},
    clearTimeout:()=>{},setTimeout:(fn,ms)=>{assert.equal(ms,60000);expiry=fn;},
    fetch:async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>({secret:'mock',second_factor:'mock-factor',second_factor_type:'totp'})};}});
  vm.runInContext(source.match(/<script>([\s\S]+?)<\/script>/)[1], context);
  const keys = vm.runInContext('Object.keys(words.en).sort().join() === Object.keys(words.de).sort().join()', context);
  assert.equal(keys,true); assert.equal(get('startup').hidden,local);
  const fields = () => get('inputs').querySelectorAll('textarea');
  const enter = (i,text) => { const field=fields()[i]; field.value=text; field.listeners.input(); };
  const envelope = (category,t,n,index) => ['SSS1','a'.repeat(32),category,t,n,index+'-'+'b'.repeat(16),'0'.repeat(16)].join('|');
  enter(0,envelope('master',2,3,1)); assert.equal(fields().length,2);
  assert.match(get('hint').textContent,initialLanguage==='en'?/2 different.*3/:/2 verschiedene.*3/);
  enter(1,envelope('master',2,3,2)); assert.equal(get('restore').disabled,!local);
  if (!local) { await get('restore').onclick(); assert.equal(calls.length,0); return; }
  await get('restore').onclick(); assert.equal(calls[0][0],'combine');
  assert.equal(JSON.parse(calls[0][1].body).shares.length,2);
  assert.equal(fields().length,1); assert.equal(fields()[0].value,'');
  assert.equal(get('result').hidden,false); assert.equal(get('output').hidden,true);
  get('reveal').onclick(); assert.equal(get('password').textContent,'mock');
  assert.equal(get('second-factor').textContent,'mock-factor');
  expiry(); assert.equal(get('password').textContent,''); assert.equal(get('second-factor').textContent,'');
  get('category').value='infra'; get('category').onchange(); enter(0,envelope('infra',4,5,1)); assert.equal(fields().length,4);
  get('language').value=initialLanguage==='en'?'de':'en'; get('language').onchange();
  assert.equal(document.documentElement.lang,get('language').value); assert.equal(fields().length,1); assert.equal(fields()[0].value,'');
  enter(0,envelope('infra',21,21,1)); assert.equal(fields().length,1);
  enter(0,envelope('infra',20,20,1)); assert.equal(fields().length,20);
  enter(0,envelope('master',2,3,1)); assert.equal(fields().length,1); assert.equal(get('restore').disabled,true);
  window.listeners.pagehide(); assert.equal(fields()[0].value,'');
}
(async()=>{await exercise('en',true);await exercise('de',true);await exercise('de',false);})().catch(error=>{console.error(error);process.exitCode=1;});
