# Asistente AIOps Homelab

Agente de monitorización de infraestructura Linux/Docker controlado por voz de terminal. Usa Microsoft Azure AI Foundry como motor de inferencia y se conecta al servidor homelab vía SSH con Paramiko.

## Qué hace

- Consulta espacio en disco, estado de contenedores Docker y métricas de CPU/RAM del servidor remoto.
- Traduce la salida cruda de terminal a respuestas estructuradas en lenguaje natural.
- Modo solo lectura: no puede modificar ni ejecutar acciones destructivas en el servidor.
- Interfaz visual en terminal con Rich (spinner de espera + Markdown en streaming).

## Stack

| Componente | Tecnología |
|---|---|
| LLM / Agente | Microsoft Azure AI Foundry (`agent-framework-foundry`) |
| Autenticación Azure | `AzureCliCredential` (azure-identity) |
| Conexión SSH | Paramiko |
| UI terminal | Rich |
| Carga de entorno | python-dotenv |

## Requisitos previos

- Python 3.11+
- Azure CLI instalado y autenticado (`az login`)
- Acceso SSH al servidor homelab mediante clave pública
- Un proyecto activo en Azure AI Foundry con un modelo desplegado (probado con `gpt-4o-mini`)

## Instalación

```bash
# Clonar el repositorio
git clone <repo-url>
cd asistente_homelab

# Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

## Configuración

Copia `.env.example` como `.env` y rellena los valores:

```env
FOUNDRY_PROJECT_ENDPOINT=https://<tu-recurso>.services.ai.azure.com/api/projects/<proyecto>
FOUNDRY_MODEL=gpt-4o-mini
SSH_HOST=<ip-o-hostname-del-servidor>
SSH_USER=<usuario-ssh>
SSH_KEY_PATH=~/.ssh/id_ed25519
```

## Uso

```bash
python agent.py
```

El agente abre un REPL interactivo. Escribe `exit` para salir.

Ejemplos de consultas:

```
❯ Administrador: ¿Qué contenedores están caídos?
❯ Administrador: ¿Cuánta RAM libre queda?
❯ Administrador: ¿Cuánto espacio hay en el disco principal?
```

## Herramientas disponibles

| Tool | Comando SSH | Descripción |
|---|---|---|
| `ver_discos` | `df -h` | Espacio en disco por partición |
| `estado_docker` | `docker ps -a` | Estado de todos los contenedores |
| `metricas_sistema` | `free -m` + `uptime` + `top` | RAM, carga CPU y uptime |

## Añadir nuevas herramientas

```python
@tool(approval_mode="never_require")
def nueva_herramienta() -> str:
    """Descripción que el LLM usará para decidir cuándo llamar a esta tool."""
    return run_ssh_command("tu-comando-linux")
```

Registra la función en la lista `tools=[...]` al construir el agente.

## Seguridad

- El archivo `.env` está excluido del repositorio. **Nunca lo subas.**
- La clave SSH nunca sale del sistema local; Paramiko la usa directamente desde disco.
- El agente opera en modo solo lectura por diseño de system prompt.
