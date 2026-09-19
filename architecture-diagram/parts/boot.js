/* ------------------------------------------------ source fan, unused in this deck */
function drawSourceFan(){
  if(!V.sourceFan||!EL.bronze)return;
  var b=R("bronze"), cx=b.l-64, cy=b.cy;
  (V.tiles||[]).forEach(function(t,i){
    var e=EL[t.k]; if(!e)return;
    var x1=e.offsetLeft+e.offsetWidth, y1=e.offsetTop+e.offsetHeight/2;
    var far=(e.offsetLeft<140), gut=EL[V.tiles[1].k].offsetLeft+EL[V.tiles[1].k].offsetWidth+12;
    var lead=far?(" H"+gut):"", sx=far?gut:x1;
    var p=P("M"+x1+","+y1+lead+" C"+(sx+70)+","+y1+" "+(cx-80)+","+cy+" "+cx+","+cy,
            {stroke:cssv("--wire"),"stroke-width":"1.4"});
    paths.push({p:p,n:1,c:cssv("--green"),r:3.2,sp:4+(i%4)*.4,ph:(i*.37)%1});
    link(t.k,p);
  });
  P("M"+(cx-2)+","+(cy-14)+" h22 v-12 l24,26 l-24,26 v-12 h-22 z",{fill:cssv("--green"),stroke:"none"});
}

/* ------------------------------------------------ modal */
var modal=document.getElementById("modal"), card=document.getElementById("card"), lastFocus=null;
function open(k){
  var d=DATA[k]; if(!d)return; lastFocus=document.activeElement;
  var plate=(d.ic||d.g)?'<div class="plate"><span style="color:'+(d.tint||"inherit")+'">'+(d.g?glyph(d.g):ico(d.ic))+'</span></div>':"";
  card.innerHTML='<button class="x" id="mx" aria-label="Close">&times;</button><div class="mhd">'+plate+
   '<div><h3 id="mtitle">'+d.title+'</h3><div class="where">'+d.where+'</div></div></div><p class="blurb">'+d.blurb+'</p>'+
   '<table><tbody>'+(d.kv||[]).map(function(r){return '<tr><td>'+r[0]+'</td><td class="num">'+fmt(r[1])+'</td></tr>';}).join("")+'</tbody></table>'+
   '<h4>How it works</h4><ul class="tick">'+(d.pts||[]).map(function(p){return "<li>"+p+"</li>";}).join("")+'</ul>';
  modal.hidden=false; document.getElementById("mx").addEventListener("click",closeModal); document.getElementById("mx").focus();
}
function closeModal(){modal.hidden=true; if(lastFocus&&lastFocus.focus)lastFocus.focus();}
modal.addEventListener("click",function(e){if(e.target===modal)closeModal();});
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&!modal.hidden)closeModal();});

/* ---------- countdown ring: only the platform view carries one ---------- */
function tick(){
  var fg=document.getElementById("ringfg"), cd=document.getElementById("cd");
  if(!fg&&!cd)return;
  var d=new Date(), s=(15-(d.getMinutes()%15))*60-d.getSeconds(), frac=1-s/900;
  if(fg){var C=2*Math.PI*47; fg.setAttribute("stroke-dasharray",C); fg.setAttribute("stroke-dashoffset",C*(1-frac));}
  if(cd){cd.textContent="next run "+String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
    cd.setAttribute("title","time to the next 15-minute cycle");}
}
setInterval(tick,1000);

/* ---------- view switching ---------- */
function setView(k){ if(!VIEWS[k])return; renderView(k); tick();
  try{localStorage.setItem("arch-view",k);}catch(e){} }
window.__setView=setView;   // the verification harness drives the views through this
document.querySelectorAll(".seg button").forEach(function(b){
  b.addEventListener("click",function(){setView(b.dataset.v);});});

/* ---------- night mode + card flip ---------- */
var root=document.documentElement;
function applyTheme(t){ root.setAttribute("data-theme",t); try{localStorage.setItem("arch-theme",t);}catch(e){}
  ["bTheme","bThemeB"].forEach(function(id){var b=document.getElementById(id); if(b)b.textContent=(t==="dark"?"Day mode":"Night mode");});
  if(V)draw(); }
var savedTheme=null; try{savedTheme=localStorage.getItem("arch-theme");}catch(e){}
["bTheme","bThemeB"].forEach(function(id){var b=document.getElementById(id);
  if(b)b.addEventListener("click",function(){applyTheme(root.getAttribute("data-theme")==="dark"?"light":"dark");});});

var flipper=document.getElementById("flipper"), faceBack=document.getElementById("faceBack"), faceFront=document.getElementById("faceFront");
function flip(to){ var on=(to===undefined)?!flipper.classList.contains("flipped"):to; flipper.classList.toggle("flipped",on);
  faceBack.setAttribute("aria-hidden",on?"false":"true"); faceFront.setAttribute("aria-hidden",on?"true":"false");
  setTimeout(function(){ var f=document.getElementById(on?"bBack":"bFlip"); if(f)f.focus();
    if(on){var bw=faceBack.querySelector(".bwrap"); if(bw)bw.scrollTop=0;} },450); }
document.getElementById("bFlip").addEventListener("click",function(){flip(true);});
document.getElementById("bBack").addEventListener("click",function(){flip(false);});
document.addEventListener("keydown",function(e){ if(e.key==="Escape"&&modal.hidden&&flipper.classList.contains("flipped")) flip(false); });

/* ---------- scale to fit ---------- */
var stage=document.getElementById("stage");
function fit(){var vw=window.innerWidth,vh=window.innerHeight,pad=vw<700?6:24,s=Math.min((vw-pad*2)/W,(vh-pad*2)/H),vp=stage.parentNode;
  var small=s<0.6; if(small)s=0.6;   // phones: keep text legible and let the stage pan instead of shrinking to a thumbnail
  vp.style.overflow=small?"auto":"hidden";
  stage.style.transform="scale("+s+")"; stage.style.left=Math.max(pad,(vw-W*s)/2)+"px"; stage.style.top=Math.max(pad,(vh-H*s)/2)+"px";
  var pan=document.getElementById("pan");
  pan.style.width=small?(W*s+pad*2)+"px":"0"; pan.style.height=small?(H*s+pad*2)+"px":"0";
  if(!small)vp.scrollTo(0,0); }
window.addEventListener("resize",function(){clearTimeout(window.__t);window.__t=setTimeout(fit,80);});

/* draw() reads offsetLeft/offsetWidth from the live DOM, so it must run after layout. */
var savedView=null; try{savedView=localStorage.getItem("arch-view");}catch(e){}
applyTheme(savedTheme==="dark"?"dark":"light");
fit();
requestAnimationFrame(function(){ setView(VIEWS[savedView]?savedView:"pipeline"); requestAnimationFrame(frame); });
