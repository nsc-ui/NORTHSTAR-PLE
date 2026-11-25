import asyncio, json, os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import websockets

class ModelHandler(BaseHTTPRequestHandler):
    calls=0
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n))
        ModelHandler.calls+=1
        if ModelHandler.calls==1:
            message={'role':'assistant','content':'Recon command requested.','tool_calls':[{'id':'call_1','type':'function','function':{'name':'shell','arguments':json.dumps({'command':'echo NORTHSTAR_SMOKE_OK','timeout_sec':30})}}]}
        else:
            message={'role':'assistant','content':'Smoke test finished after tool execution.','tool_calls':None}
        out={'choices':[{'message':message}], 'usage':{'prompt_tokens':9,'completion_tokens':3}}
        b=json.dumps(out).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

async def run_test():
    from harness import solve
    http=HTTPServer(('127.0.0.1',0),ModelHandler); threading.Thread(target=http.serve_forever,daemon=True).start()
    os.environ['MODEL_BASE_URL']=f'http://127.0.0.1:{http.server_port}/v1'; os.environ['MODEL_API_KEY']='test'; os.environ['MODEL_NAME']='fake'
    async def agent_server(ws):
        task=json.loads(await ws.recv())
        await solve(ws,task)
    async with websockets.serve(agent_server,'127.0.0.1',0,max_size=16*2**20,ping_interval=None) as srv:
        port=srv.sockets[0].getsockname()[1]
        async with websockets.connect(f'ws://127.0.0.1:{port}',ping_interval=None) as client:
            await client.send(json.dumps({'type':'task','protocol':1,'instruction':'Smoke test task','workdir':'/app','limits':{'agent_timeout_sec':60},'mcp_servers':[]}))
            while True:
                m=json.loads(await client.recv())
                if m['type']=='exec':
                    ModelHandler.execs=getattr(ModelHandler,'execs',[])+[m.get('command','')]
                    await client.send(json.dumps({'type':'result','id':m['id'],'exit_code':0,'output':'NORTHSTAR_SMOKE_OK\n/app\nempty directory','truncated':False,'timed_out':False}))
                elif m['type']=='usage': continue
                elif m['type']=='log': print('HARNESS LOG:',m.get('text')); continue
                elif m['type']=='done':
                    assert 'Final file inventory' in m.get('final_message','')
                    break
                elif m['type']=='error': raise AssertionError(m)
    http.shutdown()
    assert ModelHandler.calls >= 3, f'Expected tool call + final verification, got {ModelHandler.calls} calls'
    assert any('NORTHSTAR_SMOKE_OK' in c for c in getattr(ModelHandler,'execs',[])), 'shell tool not executed'
    print('Protocol smoke test: PASS (tool call, final check); model calls:', ModelHandler.calls)

asyncio.run(run_test())
