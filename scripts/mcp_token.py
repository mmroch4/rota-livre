"""Mints a Coreflux MCP bearer token so Claude Code can drive the local broker.

MCP token commands are not exposed as MCP tools (an agent cannot mint its own
credentials), so we send them over the MQTT command topic instead.

    python scripts/mcp_token.py            # mint and save to .claude/settings.local.json
    python scripts/mcp_token.py --print    # mint and only print the token
    python scripts/mcp_token.py --revoke   # revoke this machine's token

The token is saved as env COREFLUX_MCP_TOKEN in .claude/settings.local.json (gitignored),
which .mcp.json expands into the Authorization header. Restart Claude Code afterwards.
"""

import argparse
import getpass
import json
import os
import pathlib
import sys
import threading
import uuid

import paho.mqtt.client as mqtt

COMMAND_TOPIC = "$SYS/Coreflux/Command"
OUTPUT_TOPIC = "$SYS/Coreflux/Command/Output"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SETTINGS_LOCAL = REPO_ROOT / ".claude" / "settings.local.json"


def run_command(args, command):
    """Publishes a broker command and returns its JSON reply (matched by requestId)."""
    request_id = uuid.uuid4().hex[:8]
    reply = {}
    done = threading.Event()

    def on_connect(client, _userdata, _flags, reason_code, _properties):
        if reason_code.is_failure:
            sys.exit(f"MQTT connection refused: {reason_code}")
        client.subscribe(OUTPUT_TOPIC)

    def on_subscribe(client, *_):
        client.publish(COMMAND_TOPIC, f"{command} -requestId {request_id}")

    def on_message(_client, _userdata, msg):
        try:
            data = json.loads(msg.payload)
        except ValueError:
            return
        if data.get("requestId") == request_id:
            reply.update(data)
            done.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(args.user, args.password)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(args.host, args.port)
    client.loop_start()
    if not done.wait(timeout=10):
        sys.exit(f"No reply to '{command.split()[0]}'. Is the broker running (docker compose up -d)?")
    client.loop_stop()
    client.disconnect()
    return reply


def save_token(token):
    settings = json.loads(SETTINGS_LOCAL.read_text()) if SETTINGS_LOCAL.exists() else {}
    settings.setdefault("env", {})["COREFLUX_MCP_TOKEN"] = token
    SETTINGS_LOCAL.parent.mkdir(exist_ok=True)
    # Owner-only: the file holds a bearer token for the broker
    fd = os.open(SETTINGS_LOCAL, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(settings, indent=2) + "\n")
    os.chmod(SETTINGS_LOCAL, 0o600)  # also tightens a pre-existing file


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--user", default="root", help="MQTT user that sends the command")
    parser.add_argument("--password", default="coreflux")
    parser.add_argument("--token-user", default="root", help="broker user the token acts as (its RBAC applies)")
    parser.add_argument("--name", default=f"claude-{getpass.getuser()}", help="token name (no spaces)")
    parser.add_argument("--print", action="store_true", help="print the token instead of saving it")
    parser.add_argument("--revoke", action="store_true", help="revoke the token called --name")
    args = parser.parse_args()

    if args.revoke:
        reply = run_command(args, f"-revokeMcpToken {args.name}")
        print(reply.get("message", reply))
        return

    reply = run_command(args, f"-createMcpToken {args.token_user} {args.name}")
    token = reply.get("data", {}).get("token")
    if not reply.get("success") or not token:
        errors = "; ".join(e.get("message", "") for e in reply.get("errors", []))
        sys.exit(f"{reply.get('message', 'createMcpToken failed')} {errors}\n"
                 f"If the name is taken, run with --revoke first or pick another --name.")

    if args.print:
        print(token)
    else:
        save_token(token)
        print(f"Token '{args.name}' (user {args.token_user}) saved to {SETTINGS_LOCAL.relative_to(REPO_ROOT)}.")
        print("Restart Claude Code, then check with: claude mcp list")


if __name__ == "__main__":
    main()
