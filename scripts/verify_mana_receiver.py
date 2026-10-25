"""Mana-generated adapter -> isolated Python profile API -> catalog rule -> OLED frame. No mic."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audio.server import create_server
from audio.custom_rules import CustomRules
from hardware.display import Presentation,render

with tempfile.TemporaryDirectory() as temporary:
    profile_path=Path(temporary)/'profile.json'
    server=create_server(port=0,profile_path=profile_path)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        script="""
import {createAwareReceiverAdapter} from './frontend/mana/awareReceiverAdapter.js';
const base=process.argv[1];
const request=async(path,body,signal,method='GET')=>{
 const response=await fetch(base+path,{method,signal,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
 if(!response.ok)throw new Error(`HTTP ${response.status}`);
 return response.json();
};
const adapter=createAwareReceiverAdapter(request);
await adapter.saveEdits({name_detection:{enabled:true,primary_name:'Demo',aliases:[]}});
const saved=await adapter.saveEdits({notification_preferences:{event_tiers:{dog_bark:0}},custom_sound_requests:[{id:'rain-test',label:'Rain',tier:3,status:'recognized',model_labels:['Rain']}]});
if(saved.notification_preferences.event_tiers.dog_bark!==0||saved.name_detection.primary_name!=='Demo')throw new Error('Settings lost');
console.log(JSON.stringify({revision:saved.revision,ignore_preserved:true,name_preserved:true}));
"""
        checked=subprocess.run(['node','--input-type=module','-e',script,f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,capture_output=True,text=True,check=True)
        rules=CustomRules(profile_path)
        event=rules.detect({'Rain':.9},'simulation',now=0)[0]
        server.alert_state.add(event)
        display=server.alert_state.presentation()
        assert display['icon_id']=='cue_rain' and display['effective_tier']==3
        result=dict(status='passed',mana_adapter=json.loads(checked.stdout),catalog_event=event['label'],icon=display['icon_id'],tier=display['effective_tier'],frame_bytes=len(render(Presentation.parse(display)).buffer),microphone_used=False,physical_hardware_used=False)
        print(json.dumps(result,indent=2))
    finally:
        server.shutdown();server.server_close()
