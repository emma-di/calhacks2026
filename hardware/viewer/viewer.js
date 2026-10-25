/* Depth-tested CAD rendering. Bundled meshes work from file:// and HTTP. */
const DATA=window.DETECT_DATA;
const canvas=document.querySelector('#stlCanvas');
const gl=canvas.getContext('webgl',{antialias:true,alpha:false,preserveDrawingBuffer:true});
if(!gl)throw new Error('WebGL is required to view the solid CAD.');
const vs=`attribute vec3 aPosition;attribute vec3 aNormal;uniform mat4 uMVP;uniform mat4 uModel;varying vec3 vNormal;void main(){gl_Position=uMVP*vec4(aPosition,1.);vNormal=mat3(uModel)*aNormal;}`;
const fs=`precision mediump float;varying vec3 vNormal;uniform vec4 uColor;void main(){vec3 n=normalize(vNormal);float l=.54+.37*abs(dot(n,normalize(vec3(-.5,-.7,1.))))+.12*abs(dot(n,normalize(vec3(.8,.3,.4))));gl_FragColor=vec4(uColor.rgb*l,uColor.a);}`;
function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
const uniforms=Object.fromEntries(['uMVP','uModel','uColor'].map(k=>[k,gl.getUniformLocation(program,k)]));
const pos=gl.getAttribLocation(program,'aPosition'),normal=gl.getAttribLocation(program,'aNormal');
function I(){return[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}
function mul(a,b){let o=new Array(16).fill(0);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o}
function translation(v){let m=I();m[12]=v[0];m[13]=v[1];m[14]=v[2];return m}
function rotation(axis,d){const a=d*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return axis==='x'?[1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1]:axis==='y'?[c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1]:[c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1]}
function model(n){return mul(translation(n.translate),mul(rotation('z',n.rotate[2]),mul(rotation('y',n.rotate[1]),rotation('x',n.rotate[0]))))}
function unit(v){let l=Math.hypot(...v)||1;return v.map(x=>x/l)}
function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function dot(a,b){return a.reduce((s,x,i)=>s+x*b[i],0)}
function lookAt(eye,center,up=[0,0,1]){const z=unit(eye.map((v,i)=>v-center[i])),x=unit(cross(up,z)),y=cross(z,x);return[x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]}
function perspective(aspect){const f=1/Math.tan(Math.PI/8),n=.5,far=2000;return[f/aspect,0,0,0,0,f,0,0,0,0,(far+n)/(n-far),-1,0,0,2*far*n/(n-far),0]}
function ortho(aspect){const h=distance*.36,w=h*aspect,n=.5,f=2000;return[1/w,0,0,0,0,1/h,0,0,0,0,-2/(f-n),0,0,0,-(f+n)/(f-n),1]}
const meshes={};
for(const [id,m] of Object.entries(DATA.meshes)){
  const raw=atob(m.data),bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
  const values=new Float32Array(bytes.buffer),buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,values,gl.STATIC_DRAW);
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(let i=0;i<values.length;i+=6)for(let j=0;j<3;j++){lo[j]=Math.min(lo[j],values[i+j]);hi[j]=Math.max(hi[j],values[i+j])}
  meshes[id]={buffer,count:m.triangles*3,lo,hi};
}
let selected=null,opened=true,frame=true,path=false,wiring=true,dimensions=true,mechanisms=false,hookMode=false,viewMode='top',yaw=0,pitch=Math.PI/2,distance=300,center=[38,-47,8];
const list=document.querySelector('#partList');
DATA.prints.forEach((id,i)=>{const b=document.createElement('button');b.className='part-button';b.dataset.id=id;b.innerHTML=`<span>${String(i+1).padStart(2,'0')}</span>${DATA.labels[id]}`;b.onclick=()=>selectPart(id);list.appendChild(b)});
function selectPart(id){
  selected=id;if(id!=='body')hookMode=false;document.querySelector('#showHook').classList.toggle('on',hookMode);document.querySelectorAll('.part-button').forEach(b=>b.classList.toggle('active',b.dataset.id===id||(!id&&b.id==='assemblyButton')));
  if(['mic_left','mic_right'].includes(id)){viewMode='3d';document.querySelectorAll('#topView,#sideView,#threeView').forEach(b=>b.classList.toggle('on',b.id==='threeView'))}
  document.querySelector('#partName').textContent=id?DATA.labels[id].toUpperCase():'ASSEMBLY';
  const dl=document.querySelector('#downloadStl');dl.href=id?`assets/stl-v14/${id}.stl`:'downloads/DETECT_4_PRINT_PARTS_v0.14.zip';dl.download=id?`${id}.stl`:'DETECT_4_PRINT_PARTS_v0.14.zip';dl.textContent=id?'DOWNLOAD STL':'DOWNLOAD 4 PRINTS';
  document.querySelector('#triangleCount').textContent=id?DATA.meshes[id].triangles.toLocaleString():'—';document.querySelector('#fileSize').textContent=id?`${Math.round(DATA.meshes[id].bytes/1024)} KB`:'—';
  document.querySelector('.path-key').style.display=!id&&path?'flex':'none';resetCamera();draw();
}
function selectedNodes(){const black=[.22,.23,.24,1];if(hookMode)return [{mesh:'ref_hook_detail',translate:[0,0,0],rotate:[0,0,0],color:black},{mesh:'ref_hook_frame',translate:[0,0,0],rotate:[0,0,0],color:[.27,.3,.32,1]},{mesh:'ref_hook_screws',translate:[0,0,0],rotate:[0,0,0],color:[.7,.72,.74,1]}];return [{mesh:selected,translate:[0,0,0],rotate:[0,0,0],color:black},...(mechanisms?(DATA.detail_nodes?.[selected]||[]):[])]}
function resetCamera(){yaw=viewMode==='side'?Math.PI/2:-2.1;pitch=viewMode==='top'?Math.PI/2:viewMode==='side'?0:.7;if(selected){if(viewMode==='3d'&&['mic_left','mic_right'].includes(selected)){yaw=1.25;pitch=.5}const ms=selectedNodes().map(n=>meshes[n.mesh]);const lo=[0,1,2].map(i=>Math.min(...ms.map(m=>m.lo[i]))),hi=[0,1,2].map(i=>Math.max(...ms.map(m=>m.hi[i])));center=lo.map((v,i)=>(v+hi[i])/2);distance=Math.max(...hi.map((v,i)=>v-lo[i]))*2.2}else{const r=canvas.getBoundingClientRect(),aspect=r.width/r.height;center=frame?[48,-52,10]:[22,0,11];distance=frame?(viewMode==='3d'?Math.max(410,400/aspect):Math.max(330,320/aspect)):245}draw()}
function drawNode(n,viewProjection){const mesh=meshes[n.mesh],matrix=model(n);gl.bindBuffer(gl.ARRAY_BUFFER,mesh.buffer);gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(normal);gl.vertexAttribPointer(normal,3,gl.FLOAT,false,24,12);gl.uniformMatrix4fv(uniforms.uModel,false,new Float32Array(matrix));gl.uniformMatrix4fv(uniforms.uMVP,false,new Float32Array(mul(viewProjection,matrix)));gl.uniform4fv(uniforms.uColor,new Float32Array(n.color));gl.drawArrays(gl.TRIANGLES,0,mesh.count)}
function annotate(vp,w,h){
  const overlay=document.querySelector('#opticalLabels'),note=document.querySelector('#dimensionNote');
  overlay.setAttribute('viewBox',`0 0 ${w} ${h}`);overlay.innerHTML='';note.replaceChildren();
  const p=DATA.parameters,om=Math.hypot(...p.O.map((v,i)=>v-p.M[i])),ml=Math.hypot(...p.M.map((v,i)=>v-p.L[i]));
  const o=DATA.measurements?.optics||{oled_to_mirror_chief_ray_mm:om,mirror_to_focusing_lens_chief_ray_mm:ml,folded_object_distance_mm:om+ml};
  const wr=DATA.measurements.wiring;
  const mm=n=>Number(n.toFixed(1)),size=a=>a.map(mm).join(' × ')+' mm';
  const isMic=['mic_left','mic_right'].includes(selected),labels=[];
  function noteLines(lines){for(const line of lines){const d=document.createElement('div');d.textContent=line;note.appendChild(d)}}
  if(dimensions){
    if(isMic)noteLines([`Ø${p.mic_d} mm PCB · ${p.mic_total_depth} mm depth including soldered pins`, `${p.mic_wire_count} leads leave the open rear/top; remove M2 guard to drop the board in.`, 'Fixes shows the reserved pin-depth envelope; actual solder-pad positions need dry fitting.']);
    else if(hookMode)noteLines([`INTEGRAL HOOK · arm ${size([p.temple_h,p.temple_t])} · clear height ${mm(p.temple_h+2*p.temple_fit)} mm`, 'Approach from below/outside and slide sideways into the open mouth; no PLA snap fit.', 'Optional padded M3 screws tighten downward from the top; the wearer-facing underside stays smooth.']);
    else if(selected==='body')noteLines(['FLAT PI + INTEGRAL HANGING HOOK · no separate jaw', `OLED pocket ${size([p.oled_pocket_w,p.oled_pocket_h,p.oled_pocket_t])} · 1 mm extra in every dimension.`, 'Hook view shows the arm and two optional top-entry M3 pressure screws.']);
    else if(selected==='cover')noteLines([`Raised hood · ${mm(wr.plug_headroom_mm)} mm above assumed GPIO plug tops`, `Both mics use the ${size(wr.mic_rear_exit_mm)} rear opening. Six M2 lid screws.`]);
    else if(!selected&&mechanisms)noteLines(['FOUR PRINTED PIECES TOTAL · hook and optic guides integrated into body', 'Pi screws down flat; microphone PCBs drop into one-piece carriers.']);
    else if(!selected&&path)noteLines([`${mm(o.oled_to_mirror_chief_ray_mm)} + ${mm(o.mirror_to_focusing_lens_chief_ray_mm)} = ${mm(o.folded_object_distance_mm)} mm folded object path`, `OLED calibration travel ±${p.oled_focus_travel} mm · 33–39 mm range`, 'Virtual image → eye; not a projection screen. Bench calibration required.']);
    else if(!selected&&wiring)noteLines([`${p.mic_wire_count} leads / mic · both mic bundles enter the rear`, `Rear ${size(wr.mic_rear_exit_mm)} · OLED front ${size(wr.oled_front_exit_mm)}`, `${mm(wr.plug_headroom_mm)} mm above assumed GPIO plugs · dry-fit actual connectors and wire bends.`]);
  }
  if(selected&&!isMic&&!hookMode)return;
  if(hookMode){
    if(!dimensions)return;
    labels.push([['INTEGRAL UPPER SHELF','Bears hanging weight'],[56,0,23],60,-45], [['OPEN SIDE ENTRY','Slide around the arm'],[56,-5.2,15],-65,-45], [['TOP-ENTRY M3 SCREWS','Soft tips · underside stays smooth'],[40,0,30],60,45]);
  }else if(isMic){
    if(!dimensions)return;
    const rear=p.temple_t/2+p.temple_fit+p.mic_wall+p.mic_pin_gap;
    labels.push([['OPEN WIRE ROUTE',`${p.mic_wire_count} leads · rear/top exit`],[0,rear+2,27],-95,-55]);
    labels.push([['ACOUSTIC FACE','Outward · keep centre clear'],[0,rear+p.mic_total_depth,15],85,65]);
  }else if(mechanisms){
    labels.push([['FLAT PI TRAY','Four M2 screws from above'],[52,26,22],-50,-50],
      [['INTEGRATED OPTIC GUIDES','All glass loads from above'],[-23,0,9],-70,55],
      [['GPIO WIRE HOOD',`${mm(wr.plug_headroom_mm)} mm above plug tops`],[52,18,48],70,-45],
      [['DROP-IN MIC CARRIER','M2 edge guard + M3 saddle bolt'],[p.mic_x,9,16],75,35]);
  }else if(path){
    labels.push([['OLED',...(dimensions?[`slides ±${p.oled_focus_travel} mm`]:[])],p.O,85,50],[['MIRROR'],p.M,80,-45],[['LENS',...(dimensions?[`Ø${p.lens_d}`]:[])],p.L,-45,-80],[['COMBINER',...(dimensions?[`Ø${p.combiner_d} × ${p.combiner_t} mm`]:[])],p.C,-55,-30]);
    if(frame)labels.push([['EYE'],p.E,-65,45]);
  }else if(wiring){
    labels.push([['GPIO HOOD',...(dimensions?[`${mm(wr.plug_headroom_mm)} mm above assumed plug tops`]:[])],[52,18,48],80,-35],
      [['OLED FRONT EXIT',...(dimensions?[`${size(wr.oled_front_exit_mm)} clear`,`${p.oled_wire_count} leads`]:[])],[22,18,39],-65,-60],
      [['BOTH MICS · REAR ENTRY',...(dimensions?[`${size(wr.mic_rear_exit_mm)} clear`,`${2*p.mic_wire_count} leads · two Ø${p.mic_bundle_d} mm bundles`]:[])],[92,18,43],65,35],
      [['USB POWER OPENING',`Plug ${size([p.usb_plug_w,p.usb_plug_h])} · 1 mm vertical allowance`],[75,44,24],95,60]);
  }
  const project=p=>{const q=[0,0,0,0];for(let i=0;i<4;i++)for(let j=0;j<4;j++)q[i]+=vp[j*4+i]*[...p,1][j];return[(q[0]/q[3]+1)*w/2,(1-q[1]/q[3])*h/2]};
  const ns='http://www.w3.org/2000/svg';
  function el(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text)n.textContent=text;overlay.appendChild(n);return n}
  const toolbarHeight=document.querySelector('.viewer-bar').offsetHeight;
  document.querySelector('.path-key').style.top=(toolbarHeight+16)+'px';
  const top=toolbarHeight+40,bottom=h-Math.max(60,note.offsetHeight+58),occupied=[];
  function callout(lines,point,dx,dy){
    const [x,y]=project(point);if(x<0||x>w||y<0||y>h)return;
    const tw=Math.max(...lines.map(s=>s.length))*5.8,bh=lines.length*14+5;
    const left=dx<0,tx=Math.max(left?tw+14:14,Math.min(left?w-14:w-tw-14,x+dx));
    const bx=left?tx-tw:tx,initial=Math.max(top,Math.min(bottom-bh,y+dy));
    let ty=initial;
    const collides=t=>occupied.some(r=>bx<r.x+r.w+10&&bx+tw+10>r.x&&t<r.y+r.h+10&&t+bh+10>r.y);
    for(let step=0;step<30&&collides(ty);step++)ty=Math.max(top,Math.min(bottom-bh,initial+(step%2?1:-1)*Math.ceil((step+1)/2)*18));
    occupied.push({x:bx,y:ty,w:tw,h:bh});
    el('path',{d:`M${x},${y} L${tx},${ty+4}`});el('circle',{cx:x,cy:y,r:2});
    lines.forEach((line,i)=>el('text',{x:tx,y:ty+i*14,'text-anchor':left?'end':'start',class:i?'detail':''},line));
  }
  if(!selected&&path&&dimensions){
    // Extension lines measure centre-ray segments, not the nearest surface gap.
    for(const [a,b,offset,value] of [[p.O,p.M,[0,29,0],o.oled_to_mirror_chief_ray_mm],[p.M,p.L,[-24,0,0],o.mirror_to_focusing_lens_chief_ray_mm]]){
      const aa=a.map((v,i)=>v+offset[i]),bb=b.map((v,i)=>v+offset[i]);
      const A=project(aa),B=project(bb),a0=project(a),b0=project(b),d=unit([B[0]-A[0],B[1]-A[1],0]),t=[-d[1]*4,d[0]*4];
      el('path',{class:'dimension-line',d:`M${a0} L${A} M${b0} L${B} M${A} L${B} M${A[0]-t[0]},${A[1]-t[1]} L${A[0]+t[0]},${A[1]+t[1]} M${B[0]-t[0]},${B[1]-t[1]} L${B[0]+t[0]},${B[1]+t[1]}`});
      callout([`${mm(value)} mm`],aa.map((v,i)=>(v+bb[i])/2),offset[0]?-25:25,-10);
    }
  }
  labels.forEach(args=>callout(...args));
}
function draw(){
  const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),w=Math.round(rect.width*dpr),h=Math.round(rect.height*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}gl.viewport(0,0,w,h);gl.clearColor(.118,.133,.141,1);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);gl.depthMask(true);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  const eye=[center[0]+distance*Math.cos(yaw)*Math.cos(pitch),center[1]+distance*Math.sin(yaw)*Math.cos(pitch),center[2]+distance*Math.sin(pitch)],top=viewMode==='top',vp=mul(top||viewMode==='side'?ortho(w/h):perspective(w/h),lookAt(eye,center,top?[-1,0,0]:[0,0,1]));
  let nodes=selected?selectedNodes():DATA.nodes.filter(n=>!(opened&&n.lid)&&!(!frame&&['frame','spectacle_lenses','eye'].includes(n.id))&&!(!wiring&&['wires','gpio_plugs','oled_plug'].includes(n.id))&&!(!path&&n.id==='rays')).map(n=>opened&&n.id==='body'?{...n,color:[...n.color.slice(0,3),.23]}:n);
  gl.disable(gl.BLEND);nodes.filter(n=>n.color[3]===1).forEach(n=>drawNode(n,vp));
  gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);nodes.filter(n=>n.color[3]<1).sort((a,b)=>Math.hypot(...a.translate.map((x,i)=>x-eye[i]))-Math.hypot(...b.translate.map((x,i)=>x-eye[i]))).forEach(n=>drawNode(n,vp));gl.depthMask(true);annotate(vp,rect.width,rect.height);
}
document.querySelector('#assemblyButton').onclick=()=>selectPart(null);
document.querySelector('#resetCamera').onclick=resetCamera;
document.querySelector('#showHook').onclick=()=>{hookMode=!hookMode;if(hookMode){viewMode='3d';document.querySelectorAll('#topView,#sideView,#threeView').forEach(b=>b.classList.toggle('on',b.id==='threeView'));selectPart('body');yaw=0;pitch=.15;draw()}else{selectPart(null)}};
for(const [id,mode] of [['topView','top'],['sideView','side'],['threeView','3d']])document.querySelector('#'+id).onclick=()=>{viewMode=mode;document.querySelectorAll('#topView,#sideView,#threeView').forEach(b=>b.classList.toggle('on',b.id===id));resetCamera()};
document.querySelector('#openBody').onclick=e=>{opened=!opened;e.currentTarget.classList.toggle('on',opened);draw()};
document.querySelector('#showFrame').onclick=e=>{frame=!frame;e.currentTarget.classList.toggle('on',frame);resetCamera()};
document.querySelector('#showWiring').onclick=e=>{wiring=!wiring;e.currentTarget.classList.toggle('on',wiring);draw()};
document.querySelector('#showDimensions').onclick=e=>{dimensions=!dimensions;e.currentTarget.classList.toggle('on',dimensions);e.currentTarget.setAttribute('aria-pressed',dimensions);draw()};
document.querySelector('#showMechanisms').onclick=e=>{mechanisms=!mechanisms;e.currentTarget.classList.toggle('on',mechanisms);if(selected){viewMode='3d';document.querySelectorAll('#topView,#sideView,#threeView').forEach(b=>b.classList.toggle('on',b.id==='threeView'));resetCamera()}else draw()};
document.querySelector('#showPath').onclick=e=>{path=!path;e.currentTarget.classList.toggle('on',path);document.querySelector('.path-key').style.display=!selected&&path?'flex':'none';draw()};
let drag=null;canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};canvas.onpointermove=e=>{if(!drag)return;viewMode='3d';document.querySelectorAll('#topView,#sideView').forEach(b=>b.classList.remove('on'));document.querySelector('#threeView').classList.add('on');yaw-=(e.clientX-drag[0])*.009;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-drag[1])*.009));drag=[e.clientX,e.clientY];draw()};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
canvas.addEventListener('wheel',e=>{e.preventDefault();distance=Math.max(20,Math.min(900,distance*(e.deltaY>0?1.09:.92)));draw()},{passive:false});new ResizeObserver(draw).observe(canvas);
document.querySelector('#loading').classList.add('hidden');selectPart(null);
