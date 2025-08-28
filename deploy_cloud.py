#!/usr/bin/env python3
"""
Script para hospedagem do sistema de cadastro na nuvem
Suporte para múltiplas opções de deploy
"""

import os
import subprocess
import sys
import socket
import time
import json
from datetime import datetime

def check_internet():
    """Verifica conexão com internet."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def get_local_ip():
    """Obtém IP local."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def install_ngrok():
    """Instala ngrok se não estiver disponível."""
    print("🔽 Verificando se ngrok está instalado...")
    
    try:
        # Verificar se ngrok já está instalado
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ngrok já está instalado!")
            return True
    except FileNotFoundError:
        pass
    
    print("📦 ngrok não encontrado. Instalando...")
    
    # Tentar instalar via homebrew (macOS)
    try:
        subprocess.run(['brew', '--version'], capture_output=True, check=True)
        print("🍺 Instalando ngrok via Homebrew...")
        subprocess.run(['brew', 'install', 'ngrok/ngrok/ngrok'], check=True)
        print("✅ ngrok instalado com sucesso!")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Instruções para instalação manual
    print("❌ Não foi possível instalar ngrok automaticamente.")
    print("📋 Por favor, instale manualmente:")
    print("1. Acesse: https://ngrok.com/download")
    print("2. Baixe o ngrok para seu sistema")
    print("3. Siga as instruções de instalação")
    print("4. Execute novamente este script")
    return False

def setup_ngrok():
    """Configura ngrok para hospedar o servidor."""
    if not install_ngrok():
        return False
    
    print("\n🔧 === CONFIGURAÇÃO NGROK ===")
    print("Para usar o ngrok, você precisa:")
    print("1. Criar conta gratuita em: https://ngrok.com")
    print("2. Obter seu token de autenticação")
    print("3. Configurar o token com: ngrok authtoken SEU_TOKEN")
    
    token = input("\n🔑 Cole seu token do ngrok (ou ENTER para pular): ").strip()
    
    if token:
        try:
            subprocess.run(['ngrok', 'authtoken', token], check=True)
            print("✅ Token configurado com sucesso!")
        except subprocess.CalledProcessError:
            print("❌ Erro ao configurar token. Verifique se o token está correto.")
            return False
    
    return True

def deploy_ngrok(port=5000):
    """Executa deploy usando ngrok."""
    print(f"\n🚀 === DEPLOY COM NGROK ===")
    print("Iniciando servidor web e túnel ngrok...")
    
    # Iniciar servidor web em background
    try:
        # Iniciar servidor Flask
        import threading
        from web_server import run_web_server
        
        server_thread = threading.Thread(target=run_web_server, args=(port,), daemon=True)
        server_thread.start()
        
        # Aguardar servidor iniciar
        time.sleep(3)
        
        # Iniciar ngrok
        print(f"🌐 Criando túnel público para localhost:{port}...")
        ngrok_process = subprocess.Popen(['ngrok', 'http', str(port)])
        
        # Aguardar ngrok inicializar
        time.sleep(5)
        
        # Obter URL público do ngrok
        try:
            import requests
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()['tunnels']
            if tunnels:
                public_url = tunnels[0]['public_url']
                print(f"\n✅ === SISTEMA ONLINE ===")
                print(f"🌍 URL Pública: {public_url}")
                print(f"📱 Acesse de qualquer lugar: {public_url}")
                print(f"📊 Status: {public_url}/status")
                print(f"🔧 Painel ngrok: http://localhost:4040")
                print("=" * 60)
                print("💡 Compartilhe a URL com sua equipe para cadastros!")
                print("🛑 Pressione Ctrl+C para parar")
                
                # Manter ativo
                try:
                    ngrok_process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Parando servidor...")
                    ngrok_process.terminate()
                    
            else:
                print("❌ Erro: Não foi possível obter URL do ngrok")
                
        except Exception as e:
            print(f"❌ Erro ao obter URL do ngrok: {e}")
            print("💡 Verifique http://localhost:4040 para ver a URL")
            
            try:
                ngrok_process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Parando servidor...")
                ngrok_process.terminate()
        
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        return False

def deploy_local_network(port=5000):
    """Deploy apenas na rede local."""
    print(f"\n🏠 === DEPLOY REDE LOCAL ===")
    
    local_ip = get_local_ip()
    print(f"🌐 Servidor será acessível em:")
    print(f"📱 Rede local: http://{local_ip}:{port}")
    print(f"💻 Localhost: http://localhost:{port}")
    print(f"📊 Status: http://{local_ip}:{port}/status")
    print("=" * 50)
    print("💡 Dispositivos na mesma rede WiFi podem acessar!")
    print("🛑 Pressione Ctrl+C para parar")
    
    try:
        from web_server import run_web_server
        run_web_server(port)
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado.")

def show_cloud_options():
    """Mostra opções de hospedagem em nuvem."""
    print("\n☁️ === OPÇÕES DE HOSPEDAGEM EM NUVEM ===")
    print()
    print("🔷 1. HEROKU (Recomendado para iniciantes)")
    print("   • Gratuito até certo limite")
    print("   • Deploy fácil via Git")
    print("   • URL permanente")
    print("   • Tutorial: https://devcenter.heroku.com/articles/getting-started-with-python")
    print()
    print("🔷 2. RAILWAY")
    print("   • Moderno e simples")
    print("   • Deploy via GitHub")
    print("   • Plano gratuito disponível")
    print("   • Site: https://railway.app")
    print()
    print("🔷 3. RENDER")
    print("   • Alternativa ao Heroku")
    print("   • Deploy automático")
    print("   • SSL gratuito")
    print("   • Site: https://render.com")
    print()
    print("🔷 4. VERCEL (Para apps estáticos)")
    print("   • Ideal para frontend")
    print("   • Deploy ultra-rápido")
    print("   • Site: https://vercel.com")
    print()
    print("🔷 5. AWS, Google Cloud, Azure")
    print("   • Para uso avançado/empresarial")
    print("   • Maior controle e escalabilidade")
    print("   • Requer mais conhecimento técnico")

def create_heroku_files():
    """Cria arquivos necessários para deploy no Heroku."""
    print("\n📁 Criando arquivos para deploy no Heroku...")
    
    # Procfile
    with open('Procfile', 'w') as f:
        f.write('web: python web_server.py\n')
    
    # runtime.txt
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    with open('runtime.txt', 'w') as f:
        f.write(f'python-{python_version}\n')
    
    # requirements.txt (atualizado)
    requirements = """
flask==3.0.0
opencv-python-headless==4.12.0.88
face-recognition==1.3.0
numpy==2.2.6
pillow==11.3.0
dlib==20.0.0
""".strip()
    
    with open('requirements_heroku.txt', 'w') as f:
        f.write(requirements)
    
    # .gitignore
    gitignore = """
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.DS_Store
*.db
uploads/
usuarios/
""".strip()
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore)
    
    print("✅ Arquivos criados:")
    print("   • Procfile")
    print("   • runtime.txt")
    print("   • requirements_heroku.txt")
    print("   • .gitignore")
    print()
    print("📋 Próximos passos para Heroku:")
    print("1. Instale Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli")
    print("2. heroku login")
    print("3. heroku create seu-app-catraca")
    print("4. git init")
    print("5. git add .")
    print("6. git commit -m 'Deploy inicial'")
    print("7. git push heroku main")

def main():
    """Menu principal."""
    print("🚀 === SISTEMA DE DEPLOY - CATRACA VIRTUAL ===")
    print()
    
    if not check_internet():
        print("❌ Sem conexão com internet. Usando apenas rede local.")
        deploy_local_network()
        return
    
    print("Escolha uma opção de deploy:")
    print()
    print("1. 🌍 ngrok - Túnel público temporário (rápido)")
    print("2. 🏠 Rede local - Apenas WiFi local")
    print("3. ☁️ Ver opções de nuvem permanente")
    print("4. 📁 Criar arquivos para Heroku")
    print("5. 🚪 Sair")
    print()
    
    escolha = input("Digite sua escolha (1-5): ").strip()
    
    if escolha == '1':
        if setup_ngrok():
            deploy_ngrok()
    elif escolha == '2':
        deploy_local_network()
    elif escolha == '3':
        show_cloud_options()
    elif escolha == '4':
        create_heroku_files()
    elif escolha == '5':
        print("👋 Até logo!")
    else:
        print("❌ Opção inválida!")

if __name__ == '__main__':
    main()
