(function(){
const deepFreeze=o=>{Object.values(o).forEach(v=>{if(v&&typeof v==="object")deepFreeze(v)});return Object.freeze(o)};
const seed=window.__SEED;const store={};for(const c in seed){store[c]={};for(const id in seed[c])store[c][id]=JSON.parse(JSON.stringify(seed[c][id]))}
const subs=[];
function snapOf(col){const docs=Object.keys(store[col]||{}).sort().map(id=>({id,exists:true,data:()=>deepFreeze(JSON.parse(JSON.stringify(store[col][id])))}));return {docs,empty:!docs.length,docChanges:()=>[],metadata:{}}}
function fire(col){subs.filter(s=>s.col===col).forEach(s=>setTimeout(()=>s.fn(snapOf(col)),5));setTimeout(()=>subs.filter(s=>s.col===col).forEach(s=>s.fn(snapOf(col))),150)}
const db={collection(col){return {onSnapshot(fn){subs.push({col,fn});setTimeout(()=>fn(snapOf(col)),20);return()=>{}}}},
 doc(path){const [col,id]=path.split("/");return {set:async d=>{window.__writes=(window.__writes||0)+1;store[col]=store[col]||{};store[col][id]=JSON.parse(JSON.stringify(d));fire(col)},delete:async()=>{delete store[col][id];fire(col)}}}};
window.__store=store;
const smp=null;window.claude={use:async n=>n==="db"?db:null};})();
