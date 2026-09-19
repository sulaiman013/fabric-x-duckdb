/* ------------------------------------------------ wires
   Same construction as v1: a flow line is a solid brand-green base with a marching
   overlay on top, and packets ride the base. Every view declares its edges as
   {from, to, kind, curve} and the geometry is measured from the live DOM, so a node
   can be moved by changing one x/y without touching a path string. */
var svg=document.getElementById("wires"), NS="http://www.w3.org/2000/svg", flowOn=true;
function el(t,a){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);return e;}
function cssv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()||"#C2CCB9";}
function R(k){var e=EL[k]; if(!e)return null; return {l:e.offsetLeft,r:e.offsetLeft+e.offsetWidth,t:e.offsetTop,
  b:e.offsetTop+e.offsetHeight,cx:e.offsetLeft+e.offsetWidth/2,cy:e.offsetTop+e.offsetHeight/2};}
function P(d,o){var p=el("path",Object.assign({d:d,fill:"none","stroke-linecap":"round"},o)); svg.appendChild(p); return p;}
function F(d,w,marker){var base=P(d,{stroke:cssv("--green"),"stroke-width":w,"marker-end":marker||"url(#mG)",opacity:".95"});
  var ov=P(d,{stroke:cssv("--green-hi"),"stroke-width":(w+1.2),"stroke-dasharray":"10 12","stroke-linecap":"butt",opacity:"1","marker-end":marker||"url(#mG)"});
  ov._period=22; ov._speed=30; dashes.push(ov); base._ov=ov; return base;}
function A(d,w){var base=P(d,{stroke:cssv("--amber"),"stroke-width":w,"marker-end":"url(#mA)",opacity:".95","stroke-dasharray":"7 9"});
  base._period=16; base._speed=14; dashes.push(base); return base;}
function chipAt(k,p,t){if(!EL[k])return; var pt=p.getPointAtLength(t*p.getTotalLength());
  EL[k].style.left=pt.x+"px"; EL[k].style.top=(pt.y-18)+"px";}

/* side: which edge of a node a wire leaves from / arrives at */
function anchor(box,side){
  if(side==="r")return {x:box.r+4,y:box.cy}; if(side==="l")return {x:box.l-4,y:box.cy};
  if(side==="t")return {x:box.cx,y:box.t-4}; if(side==="b")return {x:box.cx,y:box.b+4};
  return {x:box.cx,y:box.cy};
}
function pathFor(a,b,c){
  if(c&&c.straight)return "M"+a.x+","+a.y+" L"+b.x+","+b.y;
  var dx=(b.x-a.x), bow=(c&&c.bow)||0, arc=(c&&c.arc)||0;
  var k=(c&&c.k!==undefined)?c.k:Math.max(60,Math.abs(dx)*.45);
  if(arc)return "M"+a.x+","+a.y+" C"+(a.x+k)+","+(a.y+arc)+" "+(b.x-k)+","+(b.y+arc)+" "+b.x+","+b.y;
  return "M"+a.x+","+a.y+" C"+(a.x+k)+","+(a.y+bow)+" "+(b.x-k)+","+(b.y-bow)+" "+b.x+","+b.y;
}
function link(k,p){ (LINK[k]=LINK[k]||[]).push(p); }

function draw(){
  while(svg.firstChild)svg.removeChild(svg.firstChild);
  paths=[]; dashes=[]; for(var k in LINK)delete LINK[k];
  var defs=el("defs",{}); defs.innerHTML=
   '<marker id="mG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1.5 L9,5 L0,8.5 z" fill="'+cssv("--green")+'"/></marker>'+
   '<marker id="mA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,1.5 L9,5 L0,8.5 z" fill="'+cssv("--amber")+'"/></marker>'+
   '<marker id="mF" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,1.5 L9,5 L0,8.5 z" fill="'+cssv("--wire")+'"/></marker>'+
   '<marker id="mGB" viewBox="0 0 10 10" refX="8.6" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,1.2 L9,5 L0,8.8 z" fill="'+cssv("--green")+'"/></marker>';
  svg.appendChild(defs);

  (V.edges||[]).forEach(function(e){
    var A1=e.from?R(e.from):null, B1=e.to?R(e.to):null;
    if((e.from&&!A1)||(e.to&&!B1))return;
    if(!e.fromPt&&!A1)return; if(!e.toPt&&!B1)return;
    var a=e.fromPt?{x:e.fromPt[0],y:e.fromPt[1]}:anchor(A1,e.fs||"r");
    var b=e.toPt?{x:e.toPt[0],y:e.toPt[1]}:anchor(B1,e.ts||"l");
    if(e.dy)a.y+=e.dy; if(e.dy2)b.y+=e.dy2;
    var d=e.dRaw||pathFor(a,b,e);
    var p, col=cssv("--green");
    if(e.style==="amber"){p=A(d,e.w||1.8); col=cssv("--amber");}
    else if(e.style==="thin"){p=P(d,{stroke:cssv("--wire"),"stroke-width":e.w||1.4}); col=cssv("--green");}
    else {p=F(d,e.w||2,e.big?"url(#mGB)":null);}
    paths.push({p:p,n:e.n||1,c:col,r:e.r||3.6,sp:e.sp||2.4,ph:e.ph||0});
    if(e.from)link(e.from,p); if(e.to)link(e.to,p); if(e.chip){link(e.chip,p); chipAt(e.chip,p,e.at||.45);}
  });

  (V.marks||[]).forEach(function(m){
    if(m.arrow){var x=m.arrow[0],y=m.arrow[1];
      P("M"+x+","+(y-14)+" h22 v-12 l24,26 l-24,26 v-12 h-22 z",{fill:cssv("--green"),stroke:"none"});}
  });

  if(typeof drawSourceFan==="function")drawSourceFan();
  paths.forEach(function(Q){Q.len=Q.p.getTotalLength(); Q.base=Q.p.getAttribute("stroke-width");});
  seed();
}
function seed(){
  dots.forEach(function(d){d.el.remove();}); dots=[]; if(!flowOn)return;
  paths.forEach(function(Q){
    for(var k=0;k<Q.n;k++){var d=el("circle",{r:Q.r,fill:Q.c,stroke:cssv("--halo"),"stroke-width":"1.6"});
      svg.appendChild(d); dots.push({el:d,Q:Q,ph:(k/Q.n+Q.ph)%1});}
  });
}
/* One frame loop for everything. It deliberately ignores prefers-reduced-motion:
   this machine reports it, which made an earlier build look completely static. */
var t0=performance.now();
function frame(now){
  var t=(now-t0)/1000;
  dashes.forEach(function(o){o.setAttribute("stroke-dashoffset", -((t*o._speed)%o._period));});
  if(flowOn){dots.forEach(function(d){var u=(t/d.Q.sp+d.ph)%1, pt=d.Q.p.getPointAtLength(u*d.Q.len);
    d.el.setAttribute("cx",pt.x); d.el.setAttribute("cy",pt.y);
    var f=u<.08?u/.08:(u>.92?(1-u)/.08:1); d.el.setAttribute("opacity",f);});}
  requestAnimationFrame(frame);
}
function hover(k,on){
  var ps=LINK[k]||[]; if(!ps.length){if(EL[k])EL[k].classList.toggle("lit",on); return;}
  paths.forEach(function(Q){var mine=ps.indexOf(Q.p)>=0;
    Q.p.setAttribute("stroke-width", on?(mine?(+Q.base+1.4):Q.base):Q.base);
    Q.p.setAttribute("opacity", on&&!mine?".35":".9");
    if(Q.p._ov){Q.p._ov.setAttribute("opacity", on&&!mine?".25":".95");
      Q.p._ov.setAttribute("stroke-width", on?(mine?(+Q.base+2.6):(+Q.base+1.2)):(+Q.base+1.2));}});
  dots.forEach(function(d){d.el.style.opacity=(on&&ps.indexOf(d.Q.p)<0)?".25":"";});
  if(EL[k])EL[k].classList.toggle("lit",on);
}
