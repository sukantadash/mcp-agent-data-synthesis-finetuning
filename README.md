# Agent & MCP Server Data Synthesis — Sample

Synthesize **tool-calling training trajectories** from a live MCP server using SDG Hub.

## How it works

```text
[MCP Server tools]          [Teacher LLM via LiteLLM]
        │                              │
        └──────────┬───────────────────┘
                   ▼
            MCPAgentBlock
         (agentic tool loop)
                   │
                   ▼
     Full traces: user → tool_calls → tool results → answer
                   │
                   ▼
          SFT JSONL (messages schema)
```

| Approach | When to use |
| --- | --- |
| **Offline plans** | No API key; scripted tool sequences with live MCP results |
| **`MCPAgentBlock`** | Teacher LLM generates grounded tool traces from seed questions |

## Quick start

### 1. Create a virtualenv (Python 3.10–3.13; 3.12 recommended)

`sdg_hub` / `litellm` do not support Python 3.14 yet.

```bash
cd docs/samples/mcp-agent-synthesis
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ../../../repos/sdg_hub fastmcp nest_asyncio ipykernel nbclient
```

### 2. Configure teacher (optional)

Create `.env` in this folder (gitignored):

```bash
TEACHER_MODEL_URL=https://your-openai-compatible-endpoint/v1
TEACHER_MODEL_NAME=openai/your-model-id
TEACHER_API_KEY=sk-...
```

### 3. Run the test notebook

```bash
# Select the .venv kernel in Jupyter/VS Code, then open:
test_mcp_flows.ipynb
```

The notebook:

1. Starts `mcp_server.py` if port 8008 is free  
2. Smoke-tests MCP tools  
3. Runs offline trajectory synthesis → `tool_calling_dataset_offline.jsonl`  
4. Runs teacher `MCPAgentBlock` synthesis → `tool_calling_dataset.jsonl` (if `.env` is set)  
5. Inspects and peeks at saved trajectories  

### Files

| File | Role |
| --- | --- |
| `mcp_server.py` | Sample Order Ops FastMCP server (`list_orders`, `get_order`, `check_inventory`, `create_shipment`) |
| `test_mcp_flows.ipynb` | End-to-end test notebook for offline + teacher flows |
| `.env` | Teacher model URL / name / API key (gitignored) |

## OpenAPI note

MCP tools are the preferred contract. If you only have an OpenAPI/Swagger spec, wrap the API as an MCP server, then run the same synthesis path so trajectories stay schema-validated against real tool execution.
