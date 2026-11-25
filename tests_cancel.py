"""Mock cancellation regression: harness must send a best-effort done summary."""
import asyncio, json, os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import websockets

class ModelHandler(BaseHTTPRequestHandler):
    calls=0
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); json.loads(self.rfile.read(n))
        ModelHandler.calls+=1
        message={'role':'assistant','content':None,'tool_calls':[{'id':'cancel-tool-1','type':'function','function':{'name':'shell','arguments':json.dumps({'command':'sleep 100','timeout_sec':100})}}]}
        out={'choices':[{'message':message}], 'usage':{'prompt_tokens':2,'completion_tokens':1}}
        b=json.dumps(out).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*args): pass

async def run_test():
    from harness import solve
    http=HTTPServer(('127.0.0.1',0),ModelHandler); threading.Thread(target=http.serve_forever,daemon=True).start()
    os.environ['MODEL_BASE_URL']=f'http://127.0.0.1:{http.server_port}/v1'; os.environ['MODEL_API_KEY']='test'; os.environ['MODEL_NAME']='mock'
    async def server(ws): await solve(ws,json.loads(await ws.recv()))
    async with websockets.serve(server,'127.0.0.1',0,ping_interval=None) as srv:
        port=srv.sockets[0].getsockname()[1]
        async with websockets.connect(f'ws://127.0.0.1:{port}',ping_interval=None) as client:
            await client.send(json.dumps({'type':'task','protocol':1,'instruction':'mock cancellation test','workdir':'/tmp','limits':{'agent_timeout_sec':90},'mcp_servers':[]}))
            sent_cancel=False; got_done=False
            while not got_done:
                msg=json.loads(await client.recv())
                if msg.get('type')=='exec' and not sent_cancel:
                    if 'sleep 100' in msg.get('command',''):
                        sent_cancel=True
                        await client.send(json.dumps({'type':'cancel','reason':'test cancel'}))
                    else:
                        await client.send(json.dumps({'type':'result','id':msg['id'],'exit_code':0,'output':'workspace inventory','truncated':False,'timed_out':False}))
                elif msg.get('type')=='done':
                    got_done=True
                    assert 'cancelled' in msg.get('final_message','').lower()
                elif msg.get('type') in ('log','usage'):
                    pass
    http.shutdown()
    assert sent_cancel and got_done and ModelHandler.calls==1
    print('Cancellation test: PASS (cancel received; best-effort done sent)')

if __name__=='__main__': asyncio.run(run_test())
