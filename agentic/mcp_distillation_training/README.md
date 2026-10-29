# MCP Server Distillation — E-commerce Example

Automatically generate tool-use training data to teach a small language model how to use your MCP server's tools.

## What this example does

A small model (e.g., Qwen3-8B) connected to your MCP server struggles with tool selection, parameter extraction, and multi-step chaining. This pipeline uses a **frontier model** to generate expert-quality training data that you can use to fine-tune the small model.

```
  ┌───────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │  Expert   │   │ Question │   │ Quality  │   │ Expert   │   │ Format   │
  │Exploration│──▶│Synthesis │──▶│ Filter   │──▶│Trajectory│──▶│ Training │
  │           │   │          │   │          │   │          │   │   Data   │
  └───────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
   Frontier model  Teacher LLM   Teacher LLM    Frontier model  Structured
   calls MCP tools generates Qs  scores quality  solves via MCP  messages
```

**Key idea:** The frontier model *actively explores* your MCP server — calling every tool, discovering real data, mapping tool relationships — then generates training examples grounded in what it found. This is fundamentally different from approaches that only read tool schemas.

## Files

| File | Description |
|---|---|
| `server.py` | **ShopInsights Analytics Platform** — a 15-tool FastMCP e-commerce server with deliberate ambiguity clusters |
| `data.py` | Deterministic seed data: 51 products, 30 customers, 200 orders, inventory, carts, promotions |
| `demo.ipynb` | Step-by-step tutorial notebook walking through the full pipeline |

## The MCP Server

The ShopInsights server provides 15 tools organized into **ambiguity clusters** — groups of tools that look similar but serve different purposes. This makes it challenging for small models and is representative of real-world MCP servers.

| Cluster | Tools | Challenge |
|---|---|---|
| Product Discovery | `search_products`, `browse_catalog`, `get_trending_products`, `get_product_details` | Which search/browse tool for a given query? |
| Sales & Revenue | `get_sales_data`, `get_revenue_report`, `get_store_overview` | Per-product units vs. aggregate revenue vs. snapshot |
| Customer Analytics | `get_customer_segments`, `get_customer_profile`, `get_abandoned_carts` | Individual vs. aggregate vs. behavioral |
| Multi-step | `analyze_product_performance`, `compare_products`, `forecast_demand`, `get_inventory_status`, `create_promotion` | Require chaining 2-4 tools |

## Prerequisites

1. **Python 3.10–3.13** (3.12 recommended; create a local venv)
2. **Langflow** running with a frontier model agent connected to the MCP server
3. **Teacher LLM** credentials (OpenAI-compatible / LiteLLM) in `.env`

## Quick start

### 1. Create a venv and install dependencies

From the `sdg_hub` repo root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,integration]" fastmcp pyarrow ipykernel python-dotenv
```

Create `examples/agentic/mcp_distillation_training/.env`:

```bash
TEACHER_MODEL_URL=https://your-openai-compatible-endpoint/v1
TEACHER_MODEL_NAME=openai/your-model-id
TEACHER_API_KEY=sk-...
LANGFLOW_URL=http://localhost:7860/api/v1/run/<your-flow-id>
LANGFLOW_API_KEY=
```

### 2. Start the MCP server

```bash
source .venv/bin/activate
python examples/agentic/mcp_distillation_training/server.py
```

The server starts on port 8008 (configurable via `PORT`) at `http://127.0.0.1:8008/mcp`.

### 3. Install and start Langflow (separate venv)

```bash
python3.12 -m venv .langflow-venv
source .langflow-venv/bin/activate
pip install langflow
LANGFLOW_AUTO_LOGIN=true langflow run --host 127.0.0.1 --port 7860
```

In Langflow (`http://127.0.0.1:7860`), build an agent flow that can call the ShopInsights MCP server.

#### Wire the canvas

Chat Input and MCP Tools do **not** connect to each other. You need an **Agent** in the middle:

```text
Chat Input ──▶ Agent ──▶ Chat Output
                  ▲
MCP Tools ────────┘  (Toolset → Tools)
```

1. Open **Models & Agents** and drag **Agent** onto the canvas.
2. From **Input / Output**, drag **Chat Input** and **Chat Output** (if not already present).
3. From **Models & Agents**, drag **MCP Tools**.
4. Register the MCP server (Settings → MCP Servers, or MCP sidebar → Add MCP Server):
   - Mode: **HTTP/SSE**
   - URL: `http://127.0.0.1:8008/mcp`
   - Select that server on the MCP Tools component (actions like `SEARCH_PRODUCTS`, `GET_STORE_OVERVIEW`, etc. should appear).
5. On **MCP Tools**, open the component menu and enable **Tool Mode**.
6. Connect the edges:
   - **Chat Input** → **Agent** input
   - **Agent** output → **Chat Output** input
   - **MCP Tools → Toolset** → **Agent → Tools**
7. On **Agent**, set the language model to an OpenAI-compatible provider using the same LiteLLM URL / model / key as `.env` (e.g. `llama-scout-17b`).

#### Test in Playground (not Langflow Assistant)

Use the flow **Playground** (top right). Do **not** use the bottom **Langflow Assistant** chat — that helper does not run your canvas tools.

Ask something like:

```text
Call get_store_overview and summarize total revenue.
```

You should see the agent call `get_store_overview` and return store metrics.

#### Point the notebook at the flow

Copy the flow **UUID** run URL into `.env` (the flow display name alone returns 404):

```bash
# Example: http://localhost:7860/api/v1/run/b8aeba99-fdc3-42fa-b9b0-275f7f44c2ba
LANGFLOW_URL=http://localhost:7860/api/v1/run/<your-flow-uuid>
LANGFLOW_API_KEY=   # set if Langflow auth requires it
```

In Langflow, open the flow → Share / API examples to copy the UUID URL.

### 4. Run the notebook

Select the `Python (sdg_hub mcp)` kernel (or the `.venv` kernel), open [demo.ipynb](demo.ipynb), and run cells in order. The notebook loads `.env` and passes `api_base` into `set_model_config`.

Or run the pipeline from Python:

```python
from sdg_hub import Flow

flow = Flow.from_yaml("src/sdg_hub/flows/agentic/mcp_distillation/flow.yaml")

flow.set_model_config(
    model="openai/your-model-id",
    api_key="...",
    api_base="https://your-openai-compatible-endpoint/v1",
)

flow.set_agent_config(
    agent_framework="langflow",
    agent_url="http://localhost:7860/api/v1/run/<your-flow-id>",
    agent_api_key="...",
)

result = flow.generate(dataset)
```

## Pipeline stages

The flow (`src/sdg_hub/flows/agentic/mcp_distillation/flow.yaml`) runs 6 stages:

### Stage 1: Expert Exploration

The frontier model connects to your MCP server and **actively calls every tool**. It discovers:
- Real data entities (product IDs, customer names, category hierarchies)
- Tool relationships (which outputs feed into which inputs)
- Ambiguity clusters (which tools overlap and when to use each)
- Edge cases (error conditions, empty results, parameter constraints)

The output is a structured "server understanding" document used to ground all subsequent question generation.

### Stage 2: Diversity

Multiplies each input row (×10 by default) and samples different tool subsets to ensure the training data covers diverse tool combinations.

### Stage 3: Question Synthesis

A teacher LLM generates realistic user questions using:
- The sampled tool subset
- The exploration findings (real entities, known tool relationships)

Questions reference real data discovered during exploration, not hypothetical scenarios.

### Stage 4: Question Quality Filter

Each question is scored on difficulty, realism, and uniqueness. Only "good" or "excellent" questions survive.

### Stage 5: Expert Trajectory Generation

The frontier model **solves each question** by actually calling MCP tools. The full tool call trace is captured: tool names, arguments, structured outputs, and the final synthesized answer.

### Stage 6: Response Quality Filter

Trajectories are scored on completeness. Incomplete responses are filtered out.

## Output format

Each training example is a structured function-calling conversation:

```json
[
  {"role": "system", "content": "<tool declarations for all 15 tools>"},
  {"role": "user", "content": "Find the top trending laptop and check inventory"},
  {"role": "assistant", "content": "", "function_call": {"name": "get_trending_products", "arguments": "{...}"}},
  {"role": "function", "content": "{\"trending\": [...]}", "name": "get_trending_products"},
  {"role": "assistant", "content": "", "function_call": {"name": "get_inventory_status", "arguments": "{...}"}},
  {"role": "function", "content": "{\"inventory\": [...]}", "name": "get_inventory_status"},
  {"role": "assistant", "content": "The AeroBook Gaming X17 is the top trending laptop..."}
]
```

Compatible with standard SFT frameworks (TRL, Axolotl, LLaMA-Factory).

## Scaling up

Increase volume and complexity via runtime parameter overrides:

```python
result = flow.generate(
    dataset,
    runtime_params={
        "multiply_tool_rows": {"num_samples": 50},  # 50 candidates instead of 10
        "sample_tools": {"num_samples": 3},          # 3-tool combos (harder questions)
    },
)
```

For multiple MCP servers, create a multi-row input DataFrame — one row per server. The pipeline explores each independently.

## Adapting for your own MCP server

1. Replace `server.py` and `data.py` with your own MCP server
2. Extract tool schemas into the input DataFrame format (`tool_list`, `mcp_server_name`, `mcp_server_description`)
3. Set up a Langflow agent with your frontier model + your MCP server
4. Run the pipeline — the exploration phase will automatically discover your server's data and tool relationships
