# AgenticOS Production Deployment Playbook

This deployment playbook describes the standard configurations and procedures for deploying AgenticOS in production environments.

## 1. Docker Compose Deployment

To deploy AgenticOS in a containerized environment, use the following `docker-compose.yml` configuration. This maps the workspace to a host directory to ensure dual-persistent checkpoints, session SQLite databases, and logs are persisted.

```yaml
version: '3.8'

services:
  agenticos:
    image: agenticos:latest
    container_name: agenticos-runtime
    restart: unless-stopped
    volumes:
      # Mount the host workspace directory to persist data
      - ./workspace:/app/workspace
      # Mount cfg.yaml and environment variables
      - ./cfg.yaml:/app/cfg.yaml
      - ./.env:/app/.env
    environment:
      - PYTHONUNBUFFERED=1
      - WORKSPACE_ROOT=/app/workspace
    # If using local Ollama model running on the host:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## 2. Windows Service Deployment via NSSM

For Windows production deployments where AgenticOS needs to run continuously as a background service, use **NSSM (Non-Sucking Service Manager)**.

### Installation Steps

1. Download NSSM from [nssm.cc](https://nssm.cc) and extract it.
2. Open an Administrator Command Prompt.
3. Run the following command to open the NSSM GUI:
   ```cmd
   nssm install AgenticOS
   ```
4. Configure the service in the GUI:
   - **Path**: `C:\Users\<User>\AgenticOS\venv\Scripts\python.exe`
   - **Startup directory**: `C:\Users\<User>\AgenticOS`
   - **Arguments**: `main.py`
5. On the **Environment** tab, set required environment variables (e.g., API keys, system paths):
   ```text
   GEMINI_API_KEY=your_key_here
   PYTHONUNBUFFERED=1
   ```
6. Click **Install service**.
7. Start the service:
   ```cmd
   nssm start AgenticOS
   ```

## 3. Kubernetes Deployment

For high-availability orchestration, use the following Kubernetes manifests. This deployment sets up a single-replica pod with a PersistentVolumeClaim to ensure persistent checkpoints.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agenticos-workspace-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenticos-deployment
  labels:
    app: agenticos
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agenticos
  template:
    metadata:
      labels:
        app: agenticos
    spec:
      containers:
        - name: agenticos
          image: agenticos:latest
          imagePullPolicy: IfNotPresent
          env:
            - name: PYTHONUNBUFFERED
              value: "1"
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: agenticos-secrets
                  key: gemini-api-key
          volumeMounts:
            - name: workspace-volume
              mountPath: /app/workspace
      volumes:
        - name: workspace-volume
          persistentVolumeClaim:
            claimName: agenticos-workspace-pvc
```
