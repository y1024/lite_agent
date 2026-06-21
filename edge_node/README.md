# Edge Node Deployment

This directory contains the necessary payload to deploy an Edge Sentinel node.

## Deployment Strategy: Flattening

The contents of this directory are designed to be deployed **flat** on the edge node.
Do **not** copy the `edge_node` directory itself. Instead, copy all files *inside* this directory into the target directory on the edge node (default: `/opt/edge_sentinel/`).

### Steps for a new VPS:
1. `mkdir -p /opt/edge_sentinel/` on the edge node.
2. Copy `edge_sentinel.py`, `edge_crypto.py`, `edge_whitelist.py`, and `whitelist.json` into `/opt/edge_sentinel/`.
3. Create a `.env` file in `/opt/edge_sentinel/` with your keys.
4. Setup a systemd service or cron job to run `python3 /opt/edge_sentinel/edge_sentinel.py`.

*Note: The `__init__.py` file is only used by the central Lite Agent to import these modules as a package. It is ignored by the edge node.*

### A Note on the `sys.path.insert` Hack
Inside `edge_sentinel.py`, there is a line `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`. This might seem redundant since flattening puts the files in the same directory, and `import edge_crypto` works automatically when running `python edge_sentinel.py`. However, **do not remove this hack**. It acts as an insurance policy for alternative startup methods (e.g., `python -m`, certain systemd setups, or external imports) where the script's directory might not be natively added to `sys.path`.
