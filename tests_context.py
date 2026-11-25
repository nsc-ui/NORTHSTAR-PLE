"""Context compaction regression test with mocked summarizer response."""
import asyncio
import harness

class UsageSink:
    def __init__(self): self.usage_records=[]
    async def usage(self,*args): self.usage_records.append(args)

async def main():
    task_msg={"role":"user","content":"Original engineering task: design and verify deliverables."}
    messages=[{"role":"system","content":"system instructions"},task_msg]
    for i in range(24):
        messages.extend([
            {"role":"assistant","content":f"Decision {i}; assumption and source ref; output path."},
            {"role":"tool","tool_call_id":f"t{i}","content":f"Tool result {i}: validation details."}
        ])
    original_count=len(messages)
    async def fake_model_call(client,base,key,model,prompt,tools,retries=4):
        assert tools == []
        return {"choices":[{"message":{"content":"Preserved task progress, calculations, sources, deliverables, and pending checks."}}],"usage":{"prompt_tokens":7,"completion_tokens":5}}
    harness.model_call=fake_model_call
    sink=UsageSink()
    compacted=await harness.compact_history(sink,None,None,None,"mock",messages)
    assert len(compacted)<original_count
    assert compacted[0]["content"]=="system instructions"
    assert compacted[1]["content"]==task_msg["content"]
    assert "DURABLE PROGRESS SUMMARY" in compacted[2]["content"]
    assert "Decision 23" in str(compacted[-2:]) or "Tool result 23" in str(compacted[-2:])
    assert sink.usage_records, "summary usage should be reported"
    print("Context compaction test: PASS (task, summary, recent messages, usage)")

if __name__=="__main__": asyncio.run(main())
