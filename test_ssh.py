import os
import paramiko
from dotenv import load_dotenv

load_dotenv()

def test_ssh_connection():
    host = os.environ.get("SSH_HOST")
    user = os.environ.get("SSH_USER")
    key_path = os.environ.get("SSH_KEY_PATH")
    
    print(f"Intentando conectar a {host} como {user}...")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        expanded_key_path = os.path.expanduser(key_path) if key_path else None
        
        client.connect(
            hostname=host,
            username=user,
            key_filename=expanded_key_path,
            timeout=10 # Margen de tiempo útil si te conectas a través del túnel de Tailscale
        )
        
        print("✅ Conexión SSH establecida con éxito.")
        
        # Ejecutar un comando básico para verificar
        stdin, stdout, stderr = client.exec_command('uname -a && uptime')
        salida = stdout.read().decode('utf-8').strip()
        
        print("\nRespuesta del servidor:")
        print(f"--- \n{salida}\n---")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error al conectar: {str(e)}")

if __name__ == "__main__":
    test_ssh_connection()