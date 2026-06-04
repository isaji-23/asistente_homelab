import os
import asyncio
import logging
from dotenv import load_dotenv

# Componentes principales del Microsoft Agent Framework Base
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

# Componentes de Rich para construir una interfaz visual avanzada en terminal
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

# ==========================================
# CONFIGURACIÓN DE LOGS Y ENTORNO
# ==========================================

# Silenciamos los logs informativos internos de los frameworks para evitar ruido en la terminal
logging.getLogger("agent_framework.foundry").setLevel(logging.ERROR)
logging.getLogger("paramiko").setLevel(logging.WARNING)

# Cargamos las variables de entorno declaradas en el archivo .env
load_dotenv()

# Inicializamos el objeto central de control de Rich para el renderizado de estilos
console = Console()

# Códigos ANSI limpios para estilizar el prompt clásico de input() que Rich no controla directamente
C_ADMIN = "\033[92m"  # Verde para el prompt del Administrador
C_TEXT = "\033[97m"  # Blanco para el texto introducido
C_RESET = "\033[0m"  # Reseteo de color para evitar contaminación visual

# ==========================================
# CAPA DE CONEXIÓN DE INFRAESTRUCTURA (SSH)
# ==========================================


def run_ssh_command(command: str) -> str:
    """
    Función auxiliar genérica que abre un túnel SSH, ejecuta un comando en
    el servidor remoto Ubuntu y devuelve la respuesta limpia de la terminal.
    """
    import paramiko

    try:
        # Inicializamos el cliente SSH v2 nativo de Paramiko
        client = paramiko.SSHClient()

        # Saltamos la verificación estricta de hosts conocidos (ideal para IPs dinámicas o Tailscale)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Recuperamos la ruta de la clave privada SSH y expandimos el carácter '~' si existe
        key_path = os.environ.get("SSH_KEY_PATH")
        expanded_key_path = os.path.expanduser(key_path) if key_path else None

        # Establecemos la conexión autenticada mediante clave pública hacia el minipc
        client.connect(
            hostname=os.environ.get("SSH_HOST"),
            username=os.environ.get("SSH_USER"),
            key_filename=expanded_key_path,
            timeout=10,  # Margen de espera prudencial para la conexión remota
        )

        # Ejecutamos el comando en caliente en la shell del servidor remoto
        stdin, stdout, stderr = client.exec_command(command)

        # Leemos los flujos de respuesta estándar y de error, decodificando los bytes a texto UTF-8
        salida = stdout.read().decode("utf-8").strip()
        error = stderr.read().decode("utf-8").strip()

        # Cerramos el canal SSH de forma limpia
        client.close()

        # Si el comando generó una salida ordinaria, la devolvemos; si no, devolvemos el log de error
        return salida if salida else error

    except Exception as e:
        return f"Error en conexión SSH: {str(e)}"


# ==========================================
# DEFINICIÓN DE HERRAMIENTAS (SKILLS / TOOLS)
# ==========================================


@tool(approval_mode="never_require")
def ver_discos() -> str:
    """Llama a esta herramienta para consultar el espacio en disco disponible en el servidor remoto."""
    return run_ssh_command("df -h")


@tool(approval_mode="never_require")
def estado_docker() -> str:
    """Úsala para saber qué contenedores están corriendo actualmente y su estado en el servidor remoto."""
    return run_ssh_command("docker ps -a")


@tool(approval_mode="never_require")
def metricas_sistema() -> str:
    """Úsala para consultar el uso y carga de la CPU, la memoria RAM libre y el tiempo de actividad (uptime) del servidor remoto."""
    # Encadenamos tres comandos de diagnóstico clásicos de Linux para extraer toda la telemetría en un solo viaje
    comando = (
        'echo "--- RAM ---" && free -m && '
        'echo "--- UPTIME/CPU LOAD ---" && uptime && '
        'echo "--- CPU USAGE ---" && top -bn1 | grep "Cpu(s)"'
    )
    return run_ssh_command(comando)


# ==========================================
# FLUJO PRINCIPAL CON ORQUESTACIÓN DE AGENTE
# ==========================================


async def main():
    # 1. Instanciamos el cliente de Foundry.
    # Extrae automáticamente del entorno: FOUNDRY_PROJECT_ENDPOINT y FOUNDRY_MODEL
    client = FoundryChatClient(credential=AzureCliCredential())

    # 2. Definimos las directrices y limitaciones de comportamiento (System Prompt)
    system_message = """
    Eres un Asistente de Operaciones (AIOps) especializado en monitorización de infraestructura Linux y Docker. 
    Tu objetivo es interactuar con herramientas de sistema y traducir las salidas en bruto de la terminal (stdout) a respuestas humanas, directas y estructuradas.

    REGLAS ESTRICTAS DE COMPORTAMIENTO Y FORMATO:
    1. EXTRACCIÓN QUIRÚRGICA: Nunca devuelvas la tabla de la terminal tal cual. Analiza el resultado de la herramienta y extrae únicamente la información que el usuario ha solicitado.
    2. SÍNTESIS DE DATOS: Si el usuario pregunta "qué contenedores están caídos", filtra la lista y nombra solo los que tienen el estado "Exited".
    3. LEGIBILIDAD PARA TERMINAL: Usa listas cortas y Markdown estándar (**negritas** para resaltar datos clave, `código` para contenedores).
    4. IGNORAR RUIDO: Omite particiones irrelevantes o RAM cacheada, céntrate en datos reales.
    5. SOLO LECTURA: Eres un ente de monitorización. No tienes capacidad para modificar el servidor. Deniega educadamente cualquier acción destructiva.
    """

    # 3. Construimos el Agente inyectándole el motor de inferencia, sus directrices y su inventario de herramientas
    agent = Agent(
        client=client,
        name="AIOps_Assistant",
        instructions=system_message,
        tools=[ver_discos, estado_docker, metricas_sistema],
    )

    # 4. Dibujamos el Banner de bienvenida de la interfaz de usuario con Rich
    console.print(
        f"\n[bold cyan]=================================================================[/bold cyan]"
    )
    console.print(
        f"  🤖 [white]Asistente AIOps Inicializado[/white] [cyan](Microsoft Foundry + Rich UI)[/cyan]"
    )
    console.print(
        f"  🔒 Canal SSH activo hacia: [green]{os.environ.get('SSH_HOST')}[/green]"
    )
    console.print(f"  ⌨️  Escribe '[yellow]exit[/yellow]' para cerrar la sesión.")
    console.print(
        f"[bold cyan]=================================================================[/bold cyan]\n"
    )

    # Bucle REPL (Read-Eval-Print Loop) infinito para la conversación interactiva
    while True:
        try:
            # Capturamos la entrada del administrador
            user_input = input(f"{C_ADMIN}❯ Administrador:{C_TEXT} ")

            # Gestión de cláusula de escape para romper el bucle y cerrar el script
            if user_input.lower() in ["exit", "quit", "salir"]:
                console.print(
                    f"\n[yellow]Desconectando del ecosistema de monitorización. ¡Adiós![/yellow]"
                )
                break
            if not user_input.strip():
                continue

            full_response = ""

            # 5. Creamos un contexto de visualización en vivo (Live) controlado por Rich.
            # Inicialmente pinta un objeto animado Spinner con puntos Braille mientras la IA procesa o llama a SSH.
            with Live(
                Spinner(
                    "dots", text="AIOps está consultando tu entorno...", style="yellow"
                ),
                console=console,
                refresh_per_second=12,
            ) as live:

                # Consumimos de forma asíncrona los fragmentos (chunks) de texto devueltos en streaming por el LLM
                async for chunk in agent.run(user_input, stream=True):
                    # Evaluamos si el chunk viene en formato de objeto con propiedad de texto o como string plano
                    text = chunk.text if hasattr(chunk, "text") else str(chunk)
                    full_response += text

                    # Al mutar el contenido de live.update con un objeto Markdown, Rich limpia el Spinner
                    # de forma atómica y empieza a renderizar el texto formateado en tiempo real.
                    live.update(Markdown(f"### ❯ AIOps:\n{full_response}"))

        except KeyboardInterrupt:
            # Captura un Ctrl+C en la terminal para evitar un vuelco de traza feo del sistema operativo
            console.print(f"\n\n[yellow]Interrupción detectada. Saliendo...[/yellow]")
            break
        except Exception as e:
            # Captura y aislamiento de cualquier excepción en tiempo de ejecución o fallos de red con Azure
            console.print(f"\n[bold red][Error de ejecución]: {str(e)}[/bold red]")


# ==========================================
# COMPATIBILIDAD Y ARRANQUE DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    # Si detectamos que corremos en Windows (nt), configuramos la salida estándar (stdout) para
    # forzar la codificación UTF-8. Esto previene que se rompa el renderizado de caracteres Unicode/Braille.
    if os.name == "nt":
        import sys

        sys.stdout.reconfigure(encoding="utf-8")

    # Lanzamos el bucle de eventos asíncrono para ejecutar el flujo principal
    asyncio.run(main())
