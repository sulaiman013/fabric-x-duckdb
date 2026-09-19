/* ------------------------------------------------ render one view */
var layer=document.getElementById("layer"), plats=document.getElementById("plats"),
    head=document.getElementById("head"), kp=document.getElementById("kpis"),
    EL={}, DATA={}, LINK={}, paths=[], dashes=[], dots=[], V=null, viewKey=null;

function btn(cls,k,html,d,parent){var b=document.createElement("button");b.className=cls;b.dataset.k=k;b.innerHTML=html;
  b.addEventListener("click",function(){open(k);});
  b.addEventListener("mouseenter",function(){hover(k,true);});b.addEventListener("mouseleave",function(){hover(k,false);});
  (parent||layer).appendChild(b);EL[k]=b;DATA[k]=d;return b;}

function renderView(key){
  viewKey=key; V=VIEWS[key]; EL={}; DATA={}; LINK={};
  layer.innerHTML=""; plats.innerHTML=""; kp.innerHTML="";
  head.innerHTML='<div class="eyebrow">'+V.eyebrow+'</div><h1>'+V.h1+'</h1><div class="context">'+V.context+'</div>';

  V.plats.forEach(function(p,i){
    var d=document.createElement("div"); d.className="plat rv"; d.id=p.id;
    d.style.cssText="left:"+p.x+"px;top:"+p.y+"px;width:"+p.w+"px;height:"+p.h+"px";
    d.style.animationDelay=(.15+i*.05)+"s";
    d.innerHTML='<div class="lab">'+(p.ic?ico(p.ic):"")+p.lab+'</div>'+
      (p.foot?'<div class="foot"'+(p.footX?' style="left:'+p.footX+'px"':'')+'>'+p.foot+'</div>':'');
    plats.appendChild(d);
  });

  (V.tiles||[]).forEach(function(t,i){
    var b=btn("src rv",t.k,(t.g?glyph(t.g):ico(t.ic||"postgres"))+'<span class="nm">'+t.nm+'</span>'+(t.ct!==undefined?'<span class="ct">'+t.ct+'</span>':''),t);
    b.style.left=t.x+"px"; b.style.top=t.y+"px"; b.style.animationDelay=(.25+i*.03)+"s";
    b.setAttribute("aria-label",t.title);
  });

  Object.keys(V.nodes).forEach(function(k,i){
    var d=V.nodes[k];
    var b=btn("node rv"+(d.ring?" hasring":"")+(d.w?" fixed":"")+(d.cls?" "+d.cls:""),k,
      '<div class="plate">'+(d.n2?'<span class="num">'+d.n2+'</span>':'')+
      '<span style="color:'+(d.tint||"inherit")+'">'+(d.g?glyph(d.g):ico(d.ic))+'</span>'+
      (d.lay?'<span class="lay" style="background:'+d.lay+'"></span>':'')+
      (d.ring?'<div class="ringwrap"><svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="47"/><circle class="fg" id="ringfg" cx="50" cy="50" r="47"/></svg></div><div class="cd" id="cd">--:--</div>':'')+
      '</div><div class="tx"><div class="t">'+d.t+'</div><div class="s">'+d.s+'</div></div>',d);
    b.style.left=d.x+"px"; b.style.top=d.y+"px";
    if(d.w){b.style.width=d.w+"px"; b.style.height=d.h+"px";}
    b.style.animationDelay=(.35+i*.04)+"s";
  });

  (V.caps||[]).forEach(function(c){
    var e=document.createElement("div"); e.className="srccap rv";
    e.style.cssText="left:"+c.x+"px;top:"+c.y+"px;width:"+c.w+"px"; e.style.animationDelay=".5s";
    e.innerHTML="<b>"+c.b+"</b>"+c.s; layer.appendChild(e);
  });

  (V.bands||[]).forEach(function(bd){
    var e=document.createElement("div"); e.className="band rv";
    e.style.cssText="left:"+bd.x+"px;top:"+bd.y+"px;width:"+bd.w+"px;height:"+bd.h+"px";
    e.style.animationDelay=".5s"; e.innerHTML='<span class="bt">'+bd.t+'</span>';
    layer.appendChild(e);
  });

  (V.brackets||[]).forEach(function(br){
    var e=document.createElement("div"); e.className="bracket rv";
    e.style.cssText="left:"+br.x+"px;top:"+br.y+"px;width:"+br.w+"px"; e.style.animationDelay=".55s";
    e.innerHTML='<div class="t"'+(br.tw?' style="width:'+br.tw+'px"':'')+'><b>'+br.b+'</b><span>'+br.s+'</span></div>';
    layer.appendChild(e);
  });

  Object.keys(V.chips||{}).forEach(function(k){var d=V.chips[k];
    btn("chip rv"+(d.amber?" amber":""),k,(d.ic?ico(d.ic):"")+'<span class="t">'+d.t+'</span>'+(d.s?'<span class="s">'+d.s+'</span>':''),d).style.animationDelay=".6s";});

  if(V.flow){
    var f=document.createElement("div"); f.className="flow rv";
    f.style.cssText="left:"+V.flow.x+"px;top:"+V.flow.y+"px;width:"+V.flow.w+"px"; f.style.animationDelay=".65s";
    f.innerHTML='<span class="fhd">'+V.flow.hd+'</span>';
    V.flow.steps.forEach(function(s,i){
      if(i){var a=document.createElement("span");a.className="arrow";a.innerHTML="&#9654;";f.appendChild(a);}
      var b=document.createElement("button"); b.className="fn"; b.dataset.k=s.k;
      b.innerHTML='<svg viewBox="0 0 22 22">'+s.svg+'</svg><span class="t">'+s.t+'</span><span class="s">'+s.s+'</span>';
      b.addEventListener("click",function(){open(s.k);});
      b.addEventListener("mouseenter",function(){hover(s.k,true);});
      b.addEventListener("mouseleave",function(){hover(s.k,false);});
      f.appendChild(b); EL[s.k]=b; DATA[s.k]=s;});
    layer.appendChild(f);
  }

  V.kpis.forEach(function(k){var b=document.createElement("button"); b.className="card kbtn"; b.dataset.k=k.k;
    b.innerHTML='<div class="kpi-label">'+k.l+'</div><div class="kpi-value'+(k.g?" good":"")+'">'+k.v+'</div><div class="kpi-sub">'+k.s+'</div>';
    b.addEventListener("click",function(){open(k.k);}); kp.appendChild(b); DATA[k.k]=k;});
  kp.style.gridTemplateColumns="repeat("+V.kpis.length+",1fr)";

  document.querySelectorAll(".seg button").forEach(function(b){
    b.setAttribute("aria-pressed",String(b.dataset.v===key));});
  document.getElementById("footL").innerHTML=V.foot;
  draw();
}
