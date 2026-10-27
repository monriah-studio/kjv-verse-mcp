"""Optional interop check with the official MCP Python SDK (pip install mcp): python tests/sdk_interop.py"""
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pathlib; ROOT=str(pathlib.Path(__file__).resolve().parents[1])
async def main():
    p=StdioServerParameters(command=sys.executable,args=["-m","kjv_verse_mcp"],cwd=ROOT)
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            init=await s.initialize(); print("server:",init.server_info.name,init.protocol_version)
            tools=await s.list_tools(); print("tools:",[t.name for t in tools.tools])
            res=await s.call_tool("get_passage",{"reference":"Philippians 4:13"}); print(res.content[0].text)
            res=await s.call_tool("search_kjv",{"query":"fear not","limit":3}); print(res.content[0].text)
            res=await s.call_tool("verse_of_the_day",{"date":"2026-10-26"}); print(res.content[0].text)
asyncio.run(main())
