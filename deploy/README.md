# Vercel + an always-on Linux VM

Your laptop does not need to remain on. Vercel serves the interface; an Oracle Cloud VM (or another Linux VM) runs Docker and the Python backend. Oracle free-tier capacity and account eligibility are not guaranteed. Provisioning the VM and entering account secrets must happen in your accounts.

## VM

Use an Ubuntu VM with enough RAM for the OS, API and one 512 MB sandbox; 2 GB or more is a practical starting point. Arm hosts build the sandbox image locally for their architecture.

1. Install Git, Python 3 and `python3-venv`. Install Docker Engine using its [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
2. Create a dedicated `agentarena` user and add it to the `docker` group. Membership grants powerful host access; reserve it for this backend account.
3. Copy this project to `/opt/agentarena`, owned by that user. Create its virtual environment, install requirements, copy `.env.example` to `.env`, and enter real keys and a generated API token. Set `ALLOWED_ORIGINS` to your Vercel URL. Keep one worker.
4. Build `agentarena-sandbox` from `backend/sandbox`. Ensure the service user can run `docker info`.
5. Set `DATA_DIR=/opt/agentarena/data` in `.env`, create that writable directory, and set `.env` permissions to 600.
6. Copy `deploy/agentarena.service` to `/etc/systemd/system/agentarena.service`, then run `sudo systemctl daemon-reload` and `sudo systemctl enable --now agentarena`. Check `sudo systemctl status agentarena` and `journalctl -u agentarena`.
7. Check `curl http://127.0.0.1:8000/api/health`. Readiness requires model configuration, the private token and a reachable Docker daemon. This is a dependency check, not a paid inference test.

Do not enable systemd `PrivateTmp=true`: the host Docker daemon must see the same temporary paths used for bind mounts. Do not expose Docker’s socket or port publicly.

## HTTPS address

With a domain, run an HTTPS reverse proxy such as Caddy on the VM, forwarding to `127.0.0.1:8000`. Allow HTTPS in both Oracle’s network rules and the host firewall.

Without a domain, an HTTPS tunnel running **on the VM** can expose port 8000 while your laptop is off. For example, install ngrok from its official instructions, authenticate on the VM, run `ngrok http 8000`, and configure it as a persistent service. Use your assigned HTTPS domain as `BACKEND_URL`. Check your tunnel plan’s current limits; a process launched only in an SSH shell will stop when that session ends. Port 8000 can remain closed to public ingress.

## Vercel

Set the project root directory to `frontend`, use the Next.js preset, and add these server-side environment variables for Production:

- `BACKEND_URL`: your backend’s public HTTPS origin, without `/api`.
- `AGENTARENA_API_TOKEN`: the exact token from the VM’s `.env`.

Remove obsolete `NEXT_PUBLIC_API_URL` configuration. Redeploy after changing variables. No Nebius or Tavily key belongs in Vercel client variables: those keys stay on the VM. The frontend’s proxy attaches the private API token to run requests.

Visit the site, confirm live readiness, run one investigation, inspect the corrected control and generated test evidence, then reload history. Verify `/benchmarks` and recorded playback while the backend is stopped. Hosting plans impose request-duration limits; check your Vercel plan for live SSE support and duration. A disconnected request does not automatically stop a running backend job.

The supplied code is ready to configure, but no VM, DNS, tunnel, Vercel settings, provider balance or credentials have been created or changed by this update.
