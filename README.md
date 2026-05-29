# CXAS-CLAW

CX Agent Studio CLI Agent & Workspace - an agentic CLI tool for CX Agent Studio (CXAS / Dialogflow CX).

Inspired by OpenClaw and Hermes Agent.
Built on top of cxas-scrapi (dfcx_scrapi) and the CXAS Playbook Server APIs.

```
 ██████╗ ██╗  ██╗ █████╗ ███████╗      ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝ ╚██╗██╔╝██╔══██╗██╔════╝     ██╔════╝██║     ██╔══██╗██║    ██║
██║       ╚███╔╝ ███████║███████╗     ██║     ██║     ███████║██║ █╗ ██║
██║       ██╔██╗ ██╔══██║╚════██║     ██║     ██║     ██╔══██║██║███╗██║
╚██████╗ ██╔╝ ██╗██║  ██║███████║     ╚██████╗███████╗██║  ██║╚███╔███╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝      ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

## What is CXAS-CLAW?

CXAS-CLAW is an interactive CLI agent that lets you talk to, manage, and inspect your
CX Agent Studio agents from your terminal. Think of it as a shell for your CXAS workspace.

## Features

- Interactive REPL loop (talk to any agent by name or ID)
- Agent lifecycle management: list, create, delete, update AgentEngines
- Session management: create/resume/delete sessions, inspect turns and events
- Scratchpad: run test utterances against an agent and inspect the response
- Playbooks and Tools inspection (via dfcx_scrapi)
- MCP Server integration: connect to a running Playbook Server MCP endpoint
- Rich table output for agents, sessions, intents, playbooks
- Profile system for multiple GCP projects/credentials
- Pipe-friendly: output JSON or CSV with --json / --csv flags
- Skills system: save reusable conversation test sequences

## Architecture

    User (CLI)
        |
     cxas-claw (this tool)
        |-- cxas_claw.repl         -- Interactive REPL
        |-- cxas_claw.commands     -- Command dispatch
        |-- cxas_claw.client       -- CXAS API wrapper (cxas-scrapi + v3beta1 client lib)
        |-- cxas_claw.session      -- Session lifecycle
        |-- cxas_claw.scratchpad   -- Test conversation runner
        |-- cxas_claw.mcp          -- MCP server integration
        |-- cxas_claw.profile      -- Multi-project profile management
        |-- cxas_claw.renderer     -- Rich table / JSON / CSV output

## Installation

    pip install cxas-scrapi google-cloud-dialogflow-cx==3.14.1.dev1
    git clone https://github.com/yourname/cxas-claw
    cd cxas-claw
    pip install -e .

## Quick Start

    # Set credentials
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa_key.json
    export CXAS_PROJECT=my-gcp-project
    export CXAS_LOCATION=us-central1

    # Launch interactive REPL
    claw

    # Or single commands
    claw agents list
    claw agents get <agent_id>
    claw session create <agent_id>
    claw chat <agent_id> "Hello, what can you do?"
    claw scratchpad <agent_id>

## Commands Overview

    agents          Manage AgentEngine resources
    sessions        Manage sessions
    chat            Chat with an agent interactively
    scratchpad      Run test utterances
    playbooks       List/inspect playbooks
    tools           List/inspect tools
    intents         List/inspect intents
    flows           List/inspect flows
    pages           List/inspect pages
    webhooks        List/inspect webhooks
    mcp             Connect to MCP server
    profile         Manage credential profiles

## License

Apache 2.0
