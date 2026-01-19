# Load Monitor Webhook

A Python application that monitors system load and posts to an API based on configurable thresholds. The application
listens for webhook triggers rather than running on a schedule.

## Features

- **Webhook-based triggering**: Listen for POST requests to trigger load checks
- **Dynamic node discovery**: Automatically fetches node ID from API on startup
- **Configurable thresholds**: Adjust CPU load thresholds for increase/decrease actions
- **Docker deployment**: Pre-configured for containerized deployment (Python 3.14 on Alpine)
- **Production-ready logging**: Comprehensive logging for monitoring

## Configuration

The application can be configured using environment variables. All variables have sensible defaults:

| Variable           | Default                     | Description                               |
|--------------------|-----------------------------|-------------------------------------------|
| `API_URL`          | `http://192.168.1.131:8265` | The API endpoint to post the payload      |
| `TARGET_NODE_NAME` | `r10-ubuntu`                | The node name to monitor                  |
| `WORKER_TYPE`      | `transcodecpu`              | The worker type to adjust                 |
| `LOW_THRESHOLD`    | `12`                        | CPU load threshold for increasing workers |
| `HIGH_THRESHOLD`   | `24`                        | CPU load threshold for decreasing workers |
| `WEBHOOK_PORT`     | `5000`                      | Port for the webhook server               |

### Setting Environment Variables

#### For local development:

```bash
export API_URL="http://192.168.1.131:8265"
export TARGET_NODE_NAME="r10-ubuntu"
export WORKER_TYPE="transcodecpu"
export LOW_THRESHOLD="12"
export HIGH_THRESHOLD="24"
export WEBHOOK_PORT="5000"
```

#### For Docker:

```bash
docker run -d \
  --name load-monitor \
  -p 5000:5000 \
  -e API_URL="http://192.168.1.131:8265" \
  -e TARGET_NODE_NAME="r10-ubuntu" \
  -e WORKER_TYPE="transcodecpu" \
  -e LOW_THRESHOLD="12" \
  -e HIGH_THRESHOLD="24" \
  -e WEBHOOK_PORT="5000" \
  --restart unless-stopped \
  load-monitor:latest
```

#### For Docker Compose:

Create or update your `.env` file:

```env
API_URL=http://192.168.1.131:8265
TARGET_NODE_NAME=r10-ubuntu
WORKER_TYPE=transcodecpu
LOW_THRESHOLD=12
HIGH_THRESHOLD=24
WEBHOOK_PORT=5000
```

Then use `docker compose up -d`

## Local Development

### Requirements

- Python 3.14+
- [UV](https://docs.astral.sh/uv/) (Python package manager)
- Update `uv.lock` after dependency changes:
  ```bash
  uv lock --upgrade           # refresh lockfile
  uv sync --locked            # install exactly what is pinned
  ```

### Running without Docker

```bash
uv sync
uv run load_monitor.py
```

### Testing the Webhook

```bash
curl -X POST http://localhost:5000/webhook -H 'Content-Type: application/json' -d '{}'
```

Expected response (example):

```json
{
  "success": true,
  "load": 2.45,
  "action": "increase"
}
```

## Docker Deployment

### Build the Image

```bash
docker build -t load-monitor:latest .
```

### Run with Docker

```bash
docker run -d \
  --name load-monitor \
  -p 5000:5000 \
  --restart unless-stopped \
  load-monitor:latest
```

### Run with Docker Compose

```bash
docker compose up -d
```

The compose file maps container port 5000 to host port 5000. From your host, use `http://localhost:5000`. From other
containers on the same compose network, use `http://load-monitor:5000`.

### Stop the Container

```bash
docker compose down
```

or

```bash
docker stop load-monitor
docker rm load-monitor
```

### Compose example

```yaml
services:
  tdarr-node:
    container_name: tdarr-node
    image: ghcr.io/haveagitgat/tdarr_node:latest
    restart: unless-stopped
    environment: [ 'set your env vars here' ]
    volumes: [ 'set your volumes here' ]
  load-monitor:
    image: ghcr.io/chrisjohnson00/tdarr-load-monitor:latest
    container_name: load-monitor
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

### Adding to a Flow

You can add the load monitor webhook to your existing automation flows by sending a POST request to the webhook endpoint
whenever you want to check the system load and potentially adjust worker limits.

I do this by adding a `webRequest` node in my TDarr server flows that points to the load monitor webhook URL. For my
flows, I place this node directly after executing ffmpeg.

- `method`: post
- `Request URL`: `http://load-monitor:5000/webhook`
- `Request Headers`: `{"Content-Type": "application/json"}`
- `Request Body`: `{}`

## Webhook Usage

The webhook endpoint accepts POST requests and triggers a system load check:

```bash
curl -X POST http://localhost:5000/webhook -H 'Content-Type: application/json' -d '{}'
```

On trigger, the application will:

1. Fetch `NODE_ID` from `GET_NODES_URL` by finding `nodeName == TARGET_NODE_NAME`
2. Check the current 1-minute load average
3. Compare against configured thresholds
    - `<= 12` → post `{ process: "increase" }`
    - `>= 24` → post `{ process: "decrease" }`
    - otherwise → no action
4. Post to `API_URL` with payload:

```json
{
  "data": {
    "nodeID": "<resolved NODE_ID>",
    "process": "increase|decrease",
    "workerType": "transcodecpu"
  }
}
```

5. Return JSON response with the result

## Logs

View container logs:

```bash
docker compose logs -f load-monitor
```

or

```bash
docker logs -f load-monitor
```

## Architecture

The application consists of:

1. **Node Discovery**: Fetches the node ID from `GET_NODES_URL` on startup
2. **Load Monitor**: Checks system load when webhook is triggered
3. **API Integration**: Posts worker limit changes to `API_URL`
4. **Flask Server**: Listens for webhook triggers on port 5000

## Error Handling

- Failed API connections are logged and don't stop the service
- Missing target node triggers critical error and graceful shutdown
- All errors are logged for debugging and monitoring
