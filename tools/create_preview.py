"""Create an offline audition page for every exported sample."""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
items=json.loads((p/'assets/sounds/library.json').read_text(encoding='utf-8'))['samples']
# JSON embedded for offline use; backslash/u2028 handled by default json dump.
data=json.dumps(items,ensure_ascii=True).replace('</','<\\/')
html='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kaoru Ink — Biblioteca de sonidos</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#151322;color:#f9f0ff;font:15px Segoe UI,Arial,sans-serif;margin:0}
main{max-width:1080px;margin:auto;padding:36px 20px}header{display:flex;align-items:center;gap:16px;margin-bottom:28px}
header img{height:75px;width:75px;border-radius:18px}h1{font-size:30px;margin:0 0 4px}header p{margin:0;color:#bbafc7}
.tools{background:#261f35;border:1px solid #44365b;border-radius:18px;padding:20px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:20px}
button,select,input{font:inherit}button,select{background:#342847;color:#f7eeff;border:1px solid #665178;border-radius:9px;padding:10px}
button{cursor:pointer}button:hover{background:#604581}button.active{background:#8f59b5}input[type=range]{accent-color:#d9a4e5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.card{background:#221e30;border:1px solid #3d324e;padding:15px;border-radius:13px;display:flex;flex-direction:column;justify-content:space-between;gap:14px}
.card strong{font-size:14px}.card small{color:#baafc9;display:block;margin-top:6px}.card button{align-self:flex-start}
.kbd{font-size:12px;padding:3px 7px;border:1px solid #745388;border-radius:7px;color:#dbb4f3}.hint{color:#b7a6c8;font-size:13px}
footer{color:#aba0bc;padding:30px 0;line-height:1.5}
</style></head><body><main><header><img src="assets/icon.png"><div><h1>Kaoru Ink · Sound Library</h1><p>Escucha tus recortes remasterizados, sin abrir el .exe.</p></div></header>
<div class="tools"><select id="category"><option value="all">Todas las categorías</option><option value="short">Trazo corto</option><option value="medium">Trazo medio</option><option value="long">Trazo largo</option><option value="brush">Pintura en loop</option><option value="favorite">★ Favoritos 7–9 segundos</option></select>
<label>Velocidad <output id="speedv">1.00×</output> <input id="speed" type="range" min="70" max="160" value="100" step="5"></label>
<label>Volumen <input id="vol" type="range" min="0" max="100" value="75"></label><button id="stop">Detener ◼</button>
<span class="hint" id="count"></span></div><div class="grid" id="grid"></div>
<footer>Estos archivos provienen de audios suministrados para uso local. Ver ASSETS_NOTICE.md para información sobre derechos. El audio se detiene al elegir otro recorte.</footer></main>
<script>const samples = DATAGOESHERE; let audio=new Audio(), active=null;
const grid=document.getElementById('grid'), cat=document.getElementById('category'), speed=document.getElementById('speed'),vol=document.getElementById('vol');
function stop(){audio.pause();audio.currentTime=0;if(active){active.classList.remove('active');active.textContent='▶ Escuchar';active=null}}
function render(){stop();const want=cat.value;const visible=samples.filter(s=>want==='all'||(want==='favorite'&&s.favorite)||s.category===want);grid.replaceChildren();document.getElementById('count').textContent=visible.length+' recortes';
for(const s of visible){let card=document.createElement('div');card.className='card';let head=document.createElement('div');let name=document.createElement('strong');name.textContent=s.label;let info=document.createElement('small');info.textContent=s.category.toUpperCase()+' · '+s.duration_sec.toFixed(2)+' s · Fuente '+s.source+' ('+s.start_sec.toFixed(2)+'–'+s.end_sec.toFixed(2)+' s)';head.append(name,info);let btn=document.createElement('button');btn.textContent='▶ Escuchar';btn.onclick=()=>{if(active===btn){stop();return;}stop();active=btn;btn.classList.add('active');btn.textContent='◼ Detener';audio=new Audio('assets/sounds/'+s.file);audio.volume=vol.value/100;audio.playbackRate=speed.value/100;audio.loop=s.loop;audio.onended=()=>stop();audio.play().catch(()=>{stop();alert('No se pudo reproducir el audio. Abre esta página desde la carpeta del proyecto completo.')})};card.append(head,btn);grid.append(card)}}
cat.addEventListener('change',render);speed.oninput=()=>{document.getElementById('speedv').textContent=(speed.value/100).toFixed(2)+'×';audio.playbackRate=speed.value/100};vol.oninput=()=>audio.volume=vol.value/100;document.getElementById('stop').onclick=stop;render();</script></body></html>'''
(p/'escuchar-sonidos.html').write_text(html.replace('DATAGOESHERE',data),encoding='utf-8')
