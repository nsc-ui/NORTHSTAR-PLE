"""NORTHSTAR PLE: iterative engineering agent with native PLE protocol + MCP tools."""
from __future__ import annotations
import asyncio, base64, json, os, re, time, uuid
from typing import Any
import httpx

MAX_FRAME = 16 * 1024 * 1024
MAX_TOOL_TURNS = int(os.getenv("MAX_TOOL_TURNS", "110"))
MAX_MODEL_ERRORS = 5
MAX_SUMMARY_CHARS = 8000
MAX_TOOL_OUTPUT_CHARS = 24000
MAX_HISTORY_CHARS = 90000
RECENT_HISTORY_MESSAGES = 14
FINAL_RESERVE_SEC = 120
SYSTEM = open(os.path.join(os.path.dirname(__file__), "prompts", "system.md"), encoding="utf-8").read()

class PLESession:
    def __init__(self, ws, task):
        self.ws, self.task = ws, task
        self.workdir = task.get("workdir") or "/"
        self.servers = task.get("mcp_servers") or []
        limits = task.get("limits") or {}
        self.timeout_total = float(limits.get("agent_timeout_sec") or 21600)
        self.deadline = time.monotonic() + self.timeout_total
        self.final_reserve = min(FINAL_RESERVE_SEC, max(10.0, self.timeout_total * 0.05))
        self.req_id = 0
        self.cancelled = False
        self.cancel_event = asyncio.Event()
        self.inflight = {}
        self.reader = None
        self.cancel_reason = "task cancelled"

    async def read_loop(self):
        async for frame in self.ws:
            try: msg = json.loads(frame)
            except Exception: continue
            if msg.get("type") == "cancel":
                self.cancelled = True
                self.cancel_reason = str(msg.get("reason") or "task cancelled")
                self.cancel_event.set()
                for fut in self.inflight.values():
                    if not fut.done(): fut.set_exception(TimeoutError(self.cancel_reason))
                return
            if msg.get("type") == "result":
                f = self.inflight.pop(str(msg.get("id")), None)
                if f and not f.done(): f.set_result(msg)

    async def request(self, kind, **kwargs):
        if self.cancelled: raise TimeoutError("task cancelled")
        self.req_id += 1
        rid = str(self.req_id)
        frame = {"type":kind,"id":rid,**kwargs}
        encoded = json.dumps(frame)
        if len(encoded) > MAX_FRAME: raise ValueError("protocol frame exceeds 16MiB")
        fut = asyncio.get_running_loop().create_future()
        self.inflight[rid] = fut
        await self.ws.send(encoded)
        return await fut

    async def exec(self, command, timeout=120):
        result = await self.request("exec", command=command, timeout_sec=max(1,min(int(timeout),600)))
        return result

    async def read(self, path):
        r = await self.request("read_file", path=path)
        if not r.get("ok"): return {"error":r.get("error")}
        if r.get("truncated"): return {"error":"read exceeds 10MB; use shell to inspect in chunks", "size":r.get("size")}
        return base64.b64decode(r.get("content_b64","")).decode("utf-8","replace")

    async def write(self, path, content):
        data = content.encode("utf-8") if isinstance(content,str) else content
        if len(data) <= 9_500_000:
            r = await self.request("write_file",path=path,content_b64=base64.b64encode(data).decode(),append=False)
            return r
        # Write large payload in safe sequential chunks.
        r0 = None
        for offset in range(0,len(data),4*1024*1024):
            chunk=data[offset:offset+4*1024*1024]
            r0=await self.request("write_file",path=path,content_b64=base64.b64encode(chunk).decode(),append=offset>0)
        return r0

    async def log(self, msg):
        try: await self.ws.send(json.dumps({"type":"log","text":str(msg)[:20000]}))
        except Exception: pass

    async def usage(self, model, inp=0, out=0, cached=0):
        try:
            await self.ws.send(json.dumps({"type":"usage","model":model,"input_tokens":int(inp or 0),"output_tokens":int(out or 0),"cache_read_tokens":int(cached or 0)}))
        except Exception: pass

    def left(self): return max(0, self.deadline-time.monotonic())

class MCP:
    """Streamable-HTTP MCP client for task-local MCP servers."""
    def __init__(self, session, server):
        self.s, self.server = session, server
        self.url = server["url"]
        self.headers = {"Content-Type":"application/json","Accept":"application/json, text/event-stream"}
        self.session_id = None
        self.version = None
        self.rpc_id = 0
        self.initialized = False

    async def post(self, payload):
        headers = dict(self.headers)
        if self.session_id: headers["Mcp-Session-Id"] = self.session_id
        if self.version: headers["MCP-Protocol-Version"] = self.version
        # Request through task evaluator, which restricts URLs to registered MCP hosts.
        r = await self.s.request("http", url=self.url, method="POST", headers=headers, body_b64=base64.b64encode(json.dumps(payload).encode()).decode(), timeout_sec=240)
        if not r.get("ok",True): raise RuntimeError(r.get("error"))
        response_headers = {str(k).lower(): str(v) for k,v in (r.get("headers") or {}).items()}
        self.session_id = response_headers.get("mcp-session-id", self.session_id)
        self.version = response_headers.get("mcp-protocol-version", self.version)
        body = base64.b64decode(r.get("body_b64") or "").decode("utf-8","replace")
        if r.get("truncated"): raise RuntimeError("MCP response truncated")
        if "text/event-stream" in response_headers.get("content-type",""):
            # Streamable HTTP can split JSON across multiple SSE data lines.
            events=[]; current=[]
            for line in body.splitlines():
                if line.startswith("data:"):
                    current.append(line[5:].lstrip())
                elif not line.strip() and current:
                    events.append("\n".join(current)); current=[]
            if current: events.append("\n".join(current))
            for event in reversed(events):
                if event.strip()=="[DONE]": continue
                try: return json.loads(event)
                except Exception: continue
            return {}
        try: return json.loads(body)
        except Exception: return {}

    async def initialize(self):
        if self.initialized: return {"result":{"protocolVersion":self.version}}
        self.rpc_id+=1
        res=await self.post({"jsonrpc":"2.0","id":self.rpc_id,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"northstar-ple","version":"0.3.0"}}})
        if res.get("error"): raise RuntimeError(res["error"])
        self.version=(res.get("result") or {}).get("protocolVersion", self.version)
        await self.post({"jsonrpc":"2.0","method":"notifications/initialized"})
        self.initialized=True
        return res

    async def list_tools(self):
        all_tools=[]; cursor=None
        # Paginate; task apps can publish large catalogs.
        for _ in range(20):
            self.rpc_id+=1
            params={"cursor":cursor} if cursor else {}
            r=await self.post({"jsonrpc":"2.0","id":self.rpc_id,"method":"tools/list","params":params})
            result=r.get("result") or {}
            all_tools.extend(result.get("tools") or [])
            cursor=result.get("nextCursor")
            if not cursor: break
        return all_tools

    async def call_tool(self, name, args):
        self.rpc_id+=1
        return await self.post({"jsonrpc":"2.0","id":self.rpc_id,"method":"tools/call","params":{"name":name,"arguments":args}})

def tool_schemas(mcp_catalog):
    # Keep context small even for app servers exposing hundreds of tools.
    return [
      {"type":"function","function":{"name":"shell","description":"Run bash in the task workspace. Use for file discovery, scripts, calculations, conversions, validation, and software tools. Always inspect output and handle errors.","parameters":{"type":"object","properties":{"command":{"type":"string"},"timeout_sec":{"type":"integer"}},"required":["command"]}}},
      {"type":"function","function":{"name":"read_file","description":"Read a text file in the task workspace. Use shell for binary, large, or partial inspection.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
      {"type":"function","function":{"name":"write_file","description":"Write text content to a requested task workspace file. Avoid overwriting source files.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
      {"type":"function","function":{"name":"search_mcp_tools","description":"Search the available task MCP tools by keyword and optionally server. Use this before calling an unfamiliar app/document/spreadsheet/CAD tool.","parameters":{"type":"object","properties":{"query":{"type":"string"},"server":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
      {"type":"function","function":{"name":"call_mcp_tool","description":"Call a discovered task MCP tool. First use search_mcp_tools to inspect its description and input schema, then pass the exact tool name, server, and arguments.","parameters":{"type":"object","properties":{"server":{"type":"string"},"tool":{"type":"string"},"arguments":{"type":"object"}},"required":["server","tool","arguments"]}}},
      {"type":"function","function":{"name":"verify_workspace","description":"Run a non-destructive final audit of workspace deliverables: recursive inventory, git status if relevant, Python compile checks, PDF metadata/text extraction availability, CSV/JSON/YAML parsing, and checks for empty files. Use before finalizing; output is diagnostic and does not replace inspecting task-specific deliverables.","parameters":{"type":"object","properties":{"command":{"type":"string","description":"Optional task-specific verification command to run, such as a documented validator or test. Avoid destructive commands."}},"required":[]}}},
    ]

async def discover_mcp(s):
    catalogs={}; clients={}
    async def one(server):
        name=server.get("name","mcp")
        try:
            client=MCP(s,server)
            await asyncio.wait_for(client.initialize(),timeout=60)
            catalog=await asyncio.wait_for(client.list_tools(),timeout=90)
            catalogs[name]=catalog; clients[name]=client
            await s.log(f"MCP discovery {name}: {len(catalog)} tools")
        except Exception as e:
            catalogs[name]=[]
            await s.log(f"MCP discovery failed for server {name}: {type(e).__name__}")
    await asyncio.gather(*(one(server) for server in s.servers))
    return catalogs, clients

def search_mcp(catalogs, query, server=None, limit=25):
    terms=set(re.findall(r"[a-z0-9]+", (query or "").lower()))
    rows=[]
    for sn, toolslist in catalogs.items():
        if server and sn.lower()!=server.lower(): continue
        for tool in toolslist:
            name=tool.get("name","")
            desc=tool.get("description","")
            hay=(name+" "+desc).lower()
            score=sum(2 for term in terms if term in name.lower())+sum(1 for term in terms if term in hay)
            if score or not terms:
                rows.append((score,sn,tool))
    rows.sort(key=lambda r:(-r[0],r[1],r[2].get("name","")))
    return [{"server":sn,"name":t.get("name"),"description":(t.get("description") or "")[:1200],"inputSchema":t.get("inputSchema") or {}} for _,sn,t in rows[:max(1,min(int(limit or 25),60))]]

async def model_call(client, base, key, model, messages, tools, retries=4):
    endpoint=base.rstrip("/")
    if endpoint.endswith("/chat/completions"): url=endpoint
    else: url=endpoint+"/chat/completions"
    body={"model":model,"messages":messages}
    if tools:
        body.update({"tools":tools,"tool_choice":"auto"})
    # Keep temperature omitted for reasoning and Claude-compatible endpoints.
    for attempt in range(retries):
        try:
            r=await client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=body)
            if r.status_code==400: raise RuntimeError("HTTP 400 invalid model request: "+r.text[:1200])
            if r.status_code in (429,500,502,503,504) and attempt<retries-1:
                await asyncio.sleep(min(2**attempt*2,20)); continue
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException,httpx.TransportError) as e:
            if attempt==retries-1: raise
            await asyncio.sleep(min(2**attempt*2,20))
    raise RuntimeError("model request exhausted retries")

def history_size(messages):
    try: return sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
    except Exception: return 0

async def compact_history(s, client, base, key, model, messages):
    """Summarize old turns while preserving the original task and recent tool cycles."""
    if len(messages) <= 36 and history_size(messages) < MAX_HISTORY_CHARS:
        return messages
    system = messages[0]
    original_task = messages[1] if len(messages) > 1 and messages[1].get("role") == "user" else None
    recent = messages[-RECENT_HISTORY_MESSAGES:]
    # Avoid starting the retained slice on an orphaned tool response. Move back
    # to a user/assistant content turn, then retain complete tool-call cycles.
    start = max(2, len(messages)-RECENT_HISTORY_MESSAGES)
    while start < len(messages)-1 and (messages[start].get("role") == "tool" or messages[start].get("tool_call_id")):
        start += 1
    recent = messages[start:]
    old = messages[2:start]
    if not old:
        old = messages[2:-RECENT_HISTORY_MESSAGES]
    old_text = []
    for m in old:
        role=m.get("role", "unknown")
        if role == "tool":
            content=m.get("content", "")
            old_text.append(f"TOOL RESULT: {str(content)[:6000]}")
        else:
            content=m.get("content", "")
            if content is None: content=""
            old_text.append(f"{role.upper()}: {str(content)[:4000]}")
        calls=m.get("tool_calls") or []
        if calls:
            old_text.append("TOOL CALLS: "+json.dumps(calls, ensure_ascii=False)[:3000])
    compact_prompt=[
      {"role":"system","content":"You are a faithful context compressor for a long engineering task. Do not solve, invent, or omit important details. Preserve acceptance criteria, source references, exact values and units, assumptions, unresolved questions, decisions and their rationale, output paths, commands and validation results, failed attempts, current status, and next steps. Clearly distinguish verified facts from assumptions. Produce a concise but detailed structured progress ledger."},
      {"role":"user","content":"Compress the following conversation history into a durable progress ledger.\n\n"+"\n\n".join(old_text)[:60000]}
    ]
    try:
        response=await model_call(client,base,key,model,compact_prompt,tools=[] ,retries=2)
        summary=(response.get("choices") or [{}])[0].get("message",{}).get("content") or ""
        u=response.get("usage") or {}
        await s.usage(model,u.get("prompt_tokens",0),u.get("completion_tokens",0),u.get("prompt_tokens_details",{}).get("cached_tokens",0))
        if not summary.strip(): raise RuntimeError("empty context summary")
    except Exception:
        # Fallback is lossy but bounded and explicitly labeled.
        summary="Context compaction fallback; earlier conversation may be incomplete.\n"+"\n".join(old_text[-30:])[:12000]
    out=[system]
    if original_task: out.append(original_task)
    out.append({"role":"assistant","content":"DURABLE PROGRESS SUMMARY (compacted prior context):\n"+summary[:20000]})
    out.extend(recent)
    return out

async def model_or_cancel(s, client, base, key, model, messages, tools):
    call_task=asyncio.create_task(model_call(client,base,key,model,messages,tools))
    cancel_task=asyncio.create_task(s.cancel_event.wait())
    done,pending=await asyncio.wait({call_task,cancel_task},return_when=asyncio.FIRST_COMPLETED)
    for p in pending: p.cancel()
    if cancel_task in done and s.cancelled:
        if not call_task.done(): call_task.cancel()
        raise asyncio.CancelledError(s.cancel_reason)
    cancel_task.cancel()
    return await call_task

async def solve(ws, task):
    s=PLESession(ws,task)
    reader=asyncio.create_task(s.read_loop())
    model=os.getenv("MODEL_NAME","unknown-model")
    base=os.getenv("MODEL_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    key=os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not base or not key:
        raise RuntimeError("Evaluator model endpoint environment variables missing.")
    mcp_catalog, mcp_clients=await discover_mcp(s)
    tools=tool_schemas(mcp_catalog)
    messages=[
        {"role":"system","content":SYSTEM+"\n\nWorkspace root: "+s.workdir+"\nMCP servers expose task-local tools. Search their names/descriptions/schemas with search_mcp_tools before calling an unfamiliar tool; use call_mcp_tool for execution. Available MCP servers and counts: "+json.dumps({k:len(v) for k,v in mcp_catalog.items()})},
        {"role":"user","content":s.task["instruction"]}
    ]
    # Start with broad project reconnaissance. Model receives output and must plan.
    try:
        inventory=await s.exec("pwd; ls -la; find . -maxdepth 4 -type f -printf '%p\\t%k KB\\n' | head -350",timeout=90)
        messages.append({"role":"assistant","content":"I will inspect the task workspace and plan deliverables before working."})
        messages.append({"role":"user","content":"Initial workspace inventory (inspect carefully):\n"+str(inventory.get("output",""))[:16000]})
    except Exception as e:
        await s.log(f"Initial inventory failed: {e}")
    final_text=""
    errors=0
    final_check_pending=False
    async with httpx.AsyncClient(timeout=httpx.Timeout(900.0,connect=30.0)) as client:
        for turn in range(MAX_TOOL_TURNS):
            if s.cancelled:
                final_text=f"Task cancelled ({s.cancel_reason}). Best-effort outputs were preserved; final verification was interrupted."
                break
            if s.left()<s.final_reserve:
                await s.log("Time budget reached; entering final verification/summary window.")
                break
            try:
                messages=await compact_history(s,client,base,key,model,messages)
                resp=await model_or_cancel(s,client,base,key,model,messages,tools)
                choice=(resp.get("choices") or [{}])[0]
                msg=choice.get("message") or {}
                usage=resp.get("usage") or {}
                await s.usage(model,usage.get("prompt_tokens",0),usage.get("completion_tokens",0),usage.get("prompt_tokens_details",{}).get("cached_tokens",0))
                messages.append(msg)
                calls=msg.get("tool_calls") or []
                if not calls:
                    final_text=msg.get("content") or ""
                    if final_check_pending:
                        break
                    inventory2=await s.exec("find . -maxdepth 4 -type f -printf '%p\\t%k KB\\n' | head -350; git status --short 2>/dev/null || true",timeout=90)
                    messages.append({"role":"user","content":"FINAL CHECK REQUIRED. Reconcile the requested deliverables with this inventory. Reopen and validate each final file, verify calculations/units and run relevant tests. If anything is incomplete, continue using tools. Do not claim a check passed unless its output confirms it.\n"+str(inventory2.get("output",""))[:12000]})
                    final_check_pending=True
                    if turn < MAX_TOOL_TURNS-2:
                        continue
                    break
                for tc in calls:
                    fn=tc.get("function") or {}
                    name=fn.get("name","")
                    try: args=json.loads(fn.get("arguments") or "{}")
                    except Exception: args={}
                    await s.log(f"tool invoked: {name}")
                    result=None
                    try:
                        if name=="shell":
                            command=args.get("command","")
                            if not isinstance(command,str) or not command.strip(): result={"error":"command must be a non-empty string"}
                            else: result=await s.exec(command,args.get("timeout_sec",120))
                        elif name=="read_file":
                            path=args.get("path","")
                            if not isinstance(path,str) or not path: result={"error":"path must be a non-empty string"}
                            else: result=await s.read(path)
                        elif name=="write_file":
                            path=args.get("path",""); content=args.get("content","")
                            if not isinstance(path,str) or not path or not isinstance(content,str): result={"error":"path/content must be strings"}
                            else: result=await s.write(path,content)
                        elif name=="search_mcp_tools":
                            result=search_mcp(mcp_catalog,args.get("query",""),args.get("server"),args.get("limit",25))
                        elif name=="call_mcp_tool":
                            server_name=args.get("server",""); tool_name=args.get("tool","")
                            available=next((t for t in mcp_catalog.get(server_name,[]) if t.get("name")==tool_name),None)
                            mcp_client=mcp_clients.get(server_name)
                            if not available or not mcp_client:
                                result={"error":"Unknown MCP server/tool. Search tools and use exact names."}
                            else:
                                result=await mcp_client.call_tool(tool_name,args.get("arguments") or {})
                        elif name=="verify_workspace":
                            cmd=args.get("command","")
                            audit="set -eu; echo '--- recursive inventory ---'; find . -maxdepth 5 -type f -printf '%p\t%k KB\n' | sort | head -500; echo '--- empty files ---'; find . -maxdepth 5 -type f -empty -print; echo '--- git status ---'; git status --short 2>/dev/null || true; echo '--- Python compile check ---'; python -m compileall -q . 2>&1 || true; echo '--- file validation availability ---'; command -v pdftotext || true; command -v pdfinfo || true; command -v libreoffice || true; command -v python || true"
                            if cmd and isinstance(cmd,str): audit += "\n--- task-specific validation ---\n"+cmd
                            result=await s.exec(audit,timeout=180)
                        else:
                            result={"error":"Unknown tool name"}
                    except Exception as tool_exc:
                        # Return errors as tool results so the model can repair/retry,
                        # instead of aborting the entire task loop.
                        result={"tool_error":type(tool_exc).__name__,"message":str(tool_exc)[:2500]}
                    try: tool_content=json.dumps(result,ensure_ascii=False)
                    except Exception: tool_content=str(result)
                    messages.append({"role":"tool","tool_call_id":tc.get("id"),"content":tool_content[:MAX_TOOL_OUTPUT_CHARS]})
                errors=0
                if calls:
                    final_check_pending=False
            except asyncio.CancelledError as e:
                final_text=f"Task cancelled ({s.cancel_reason}). Best-effort outputs were preserved; final verification was interrupted."
                break
            except Exception as e:
                errors+=1
                await s.log(f"Model/tool loop exception ({errors}/{MAX_MODEL_ERRORS}): {type(e).__name__}")
                messages.append({"role":"user","content":f"Recover from this error and proceed carefully: {type(e).__name__}: {e}"})
                if errors>=MAX_MODEL_ERRORS: break
    # Last-minute inventory and clear final status, no fabricated pass claims.
    try:
        check=await s.exec("find . -maxdepth 4 -type f -printf '%p\\t%k KB\\n' | head -350",timeout=45)
        inventory_text=check.get("output","")
    except Exception: inventory_text="Final inventory could not be collected."
    final=(final_text.strip() or "NORTHSTAR ended without a final model response.")+"\n\nFinal file inventory:\n"+inventory_text[:10000]
    try:
        await ws.send(json.dumps({"type":"done","final_message":final[:MAX_SUMMARY_CHARS]}))
    except Exception: pass
    reader.cancel()
    try: await reader
    except asyncio.CancelledError: pass
