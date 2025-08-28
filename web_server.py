#!/usr/bin/env python3
# web_server.py
# Servidor web para cadastro remoto via celular

from flask import Flask, request, render_template_string, redirect, url_for, flash, jsonify
import os
import sqlite3
import face_recognition
import cv2
import numpy as np
from PIL import Image
import io
import re
from datetime import datetime
import threading
import socket

# Importar funções do sistema principal
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurações
DB_FILE = "catraca_virtual.db"
USUARIOS_DIR = "usuarios"
UPLOAD_FOLDER = "uploads"

# Criar diretório de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(USUARIOS_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'catraca_virtual_secret_key_2024'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def sanitizar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos de um CPF."""
    return re.sub(r'\D', '', cpf)

def salvar_usuario_db(nome: str, equipe: str, cpf: str, foto_path: str) -> bool:
    """Salva usuário no banco de dados."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usuarios (nome, equipe, cpf, foto_path)
            VALUES (?, ?, ?, ?)
        ''', (nome, equipe, cpf, foto_path))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Erro ao salvar usuário: {e}")
        return False

def processar_foto_upload(file, cpf_sanitizado: str, nome: str) -> tuple:
    """Processa foto enviada via upload."""
    try:
        # Ler imagem do upload
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Converter para RGB se necessário
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Criar diretório do usuário
        caminho_usuario = os.path.join(USUARIOS_DIR, cpf_sanitizado)
        os.makedirs(caminho_usuario, exist_ok=True)
        
        # Salvar imagem otimizada
        caminho_foto = os.path.join(caminho_usuario, "foto.jpg")
        
        # Redimensionar se muito grande (manter proporção)
        max_size = 1024
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Salvar com qualidade otimizada
        image.save(caminho_foto, 'JPEG', quality=90, optimize=True)
        
        return True, caminho_foto
        
    except Exception as e:
        return False, f"Erro ao processar imagem: {str(e)}"

# Template HTML responsivo
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 Catraca Virtual - Cadastro Remoto</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 16px;
        }
        
        .form-container {
            padding: 30px 20px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
            font-size: 16px;
        }
        
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e1e1;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus, input[type="file"]:focus {
            outline: none;
            border-color: #4CAF50;
        }
        
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
        }
        
        .file-input-button {
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            padding: 15px 20px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
            font-size: 16px;
            font-weight: 600;
            text-align: center;
            transition: transform 0.3s;
        }
        
        .file-input-button:hover {
            transform: translateY(-2px);
        }
        
        input[type="file"] {
            position: absolute;
            left: -9999px;
        }
        
        .submit-btn {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            padding: 18px 30px;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            width: 100%;
            cursor: pointer;
            transition: transform 0.3s;
            margin-top: 20px;
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
        }
        
        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .preview-container {
            margin-top: 15px;
            text-align: center;
        }
        
        .preview-image {
            max-width: 100%;
            max-height: 200px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .alert {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .info-box {
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            color: #0056b3;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .info-box h3 {
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .info-box ul {
            margin-left: 20px;
        }
        
        .info-box li {
            margin-bottom: 5px;
        }
        
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            
            .container {
                border-radius: 15px;
            }
            
            .header {
                padding: 20px 15px;
            }
            
            .form-container {
                padding: 20px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Cadastro Remoto</h1>
            <p>Sistema de Identificação - Catraca</p>
        </div>
        
        <div class="form-container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <div class="info-box">
                <h3>📋 Instruções para o cadastro:</h3>
                <ul>
                    <li>✅ Preencha todos os campos obrigatórios</li>
                    <li>✅ Envie uma foto da pessoa</li>
                    <li>✅ Qualquer formato de imagem é aceito</li>
                    <li>✅ CPF pode ter qualquer formato</li>
                </ul>
            </div>
            
            <form method="POST" enctype="multipart/form-data" onsubmit="return validateForm()">
                <div class="form-group">
                    <label for="nome">👤 Nome Completo</label>
                    <input type="text" id="nome" name="nome" required placeholder="Digite seu nome completo">
                </div>
                
                <div class="form-group">
                    <label for="equipe">🏢 Equipe/Setor</label>
                    <input type="text" id="equipe" name="equipe" required placeholder="Digite sua equipe ou setor">
                </div>
                
                <div class="form-group">
                    <label for="cpf">🆔 CPF</label>
                    <input type="text" id="cpf" name="cpf" required placeholder="Digite o CPF">
                </div>
                
                <div class="form-group">
                    <label for="foto">📸 Sua Foto</label>
                    <div class="file-input-wrapper">
                        <button type="button" class="file-input-button" onclick="document.getElementById('foto').click()">
                            📷 Selecionar Foto
                        </button>
                        <input type="file" id="foto" name="foto" accept="image/*" capture="environment" required onchange="previewImage()">
                    </div>
                    <div id="preview-container" class="preview-container" style="display: none;">
                        <img id="preview-image" class="preview-image" alt="Preview">
                    </div>
                </div>
                
                <button type="submit" class="submit-btn" id="submit-btn">
                    ✅ Cadastrar Pessoa
                </button>
            </form>
        </div>
    </div>
    
    <script>
        function previewImage() {
            const file = document.getElementById('foto').files[0];
            const previewContainer = document.getElementById('preview-container');
            const previewImage = document.getElementById('preview-image');
            const button = document.querySelector('.file-input-button');
            
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    previewContainer.style.display = 'block';
                    button.textContent = '✅ Foto Selecionada';
                    button.style.background = 'linear-gradient(135deg, #4CAF50, #45a049)';
                };
                reader.readAsDataURL(file);
            }
        }
        
        function validateForm() {
            const nome = document.getElementById('nome').value.trim();
            const equipe = document.getElementById('equipe').value.trim();
            const cpf = document.getElementById('cpf').value.trim();
            const foto = document.getElementById('foto').files[0];
            
            if (!nome || !equipe || !cpf || !foto) {
                alert('Por favor, preencha todos os campos e selecione uma foto.');
                return false;
            }
            
            // Desabilitar botão durante o envio
            const submitBtn = document.getElementById('submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = '📤 Enviando...';
            
            return true;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/', methods=['POST'])
def cadastrar():
    try:
        # Coletar dados do formulário
        nome = request.form.get('nome', '').strip()
        equipe = request.form.get('equipe', '').strip()
        cpf = request.form.get('cpf', '').strip()
        foto = request.files.get('foto')
        
        # Validações
        if not nome or not equipe or not cpf or not foto:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('index'))
        
        cpf_sanitizado = sanitizar_cpf(cpf)
        if len(cpf_sanitizado) == 0:
            flash('CPF não pode estar vazio.', 'error')
            return redirect(url_for('index'))
        
        # Verificar se usuário já existe
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nome FROM usuarios WHERE cpf = ?', (cpf_sanitizado,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            flash(f'Pessoa "{existing[0]}" já cadastrada com este CPF.', 'error')
            return redirect(url_for('index'))
        
        # Processar foto
        sucesso, resultado = processar_foto_upload(foto, cpf_sanitizado, nome)
        
        if not sucesso:
            flash(resultado, 'error')
            return redirect(url_for('index'))
        
        # Salvar no banco de dados
        if salvar_usuario_db(nome, equipe, cpf_sanitizado, resultado):
            flash(f'✅ {nome} cadastrado com sucesso! A pessoa já pode ser identificada pelo sistema.', 'success')
        else:
            flash('Erro ao salvar no banco de dados. CPF pode já estar em uso.', 'error')
        
    except Exception as e:
        flash(f'Erro interno: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/status')
def status():
    """Endpoint para verificar status do sistema."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        total_usuarios = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM acessos WHERE DATE(data_hora) = DATE("now")')
        acessos_hoje = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'online',
            'total_usuarios': total_usuarios,
            'acessos_hoje': acessos_hoje,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_local_ip():
    """Obtém o IP local da máquina."""
    try:
        # Conectar a um endereço remoto para descobrir o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_web_server(port=5000):
    """Executa o servidor web."""
    local_ip = get_local_ip()
    print(f"\n🌐 === SERVIDOR WEB INICIADO ===")
    print(f"📱 Acesse pelo celular: http://{local_ip}:{port}")
    print(f"💻 Acesse pelo computador: http://localhost:{port}")
    print(f"📊 Status do sistema: http://{local_ip}:{port}/status")
    print(f"🛑 Para parar: Ctrl+C")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_web_server()

