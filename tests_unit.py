import asyncio, base64, json
from harness import MCP, search_mcp

class FakeSession:
    def __init__(self, response): self.response=response; self.last=None
    async def request(self, *args, **kwargs): self.last=(args,kwargs); return self.response

class FakeResponse(dict): pass

async def test_sse_parser():
    body='event: message\ndata: {"jsonrpc":"2.0",\ndata: "id":"7","result":{"ok":true}}\n\n'
    r=FakeResponse(ok=True,headers={'content-type':'text/event-stream','mcp-session-id':'abc'},body_b64=base64.b64encode(body.encode()).decode(),truncated=False)
    s=FakeSession(r); m=MCP(s,{'name':'test','url':'http://127.0.0.1:9000/mcp'})
    got=await m.post({'jsonrpc':'2.0','id':7,'method':'test'})
    assert got['result']['ok'] is True
    assert m.session_id=='abc'

async def test_search():
    catalog={'docs':[{'name':'read_pdf','description':'extract PDF text','inputSchema':{'type':'object'}},{'name':'send_email','description':'send mail'}]}
    result=search_mcp(catalog,'pdf extract')
    assert result and result[0]['name']=='read_pdf'

async def main():
    await test_sse_parser(); await test_search()
    print('Unit tests: PASS (SSE multiline/session header; MCP search ranking)')

if __name__=='__main__': asyncio.run(main())
