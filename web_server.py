#!/usr/bin/env python3
# web_server.py
# Servidor web local para cadastro por etapas via celular

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
import socket

# Configurações
DB_FILE = "catraca_virtual.db"
USUARIOS_DIR = "usuarios"
UPLOAD_FOLDER = "uploads"

# Criar diretórios se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(USUARIOS_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'catraca_virtual_local_2024'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def sanitizar_matricula(matricula: str) -> str:
    """Remove espaços em branco e normaliza matrícula."""
    return matricula.strip().upper()

def salvar_usuario_db(nome: str, equipe: str, matricula: str, foto_path: str) -> bool:
    """Salva usuário no banco de dados."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usuarios (nome, equipe, cpf, foto_path)
            VALUES (?, ?, ?, ?)
        ''', (nome, equipe, matricula, foto_path))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Erro ao salvar usuário: {e}")
        return False

def processar_foto_upload(file, matricula_sanitizada: str, nome: str) -> tuple:
    """Processa foto enviada via upload com otimização para reconhecimento facial."""
    try:
        # Ler imagem do upload
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Converter para RGB se necessário
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Converter para numpy array para processamento
        image_array = np.array(image)
        
        # Otimizar para reconhecimento facial
        # Redimensionar mantendo qualidade para face_recognition
        height, width = image_array.shape[:2]
        
        # Garantir tamanho mínimo para boa detecção
        min_size = 300
        if width < min_size or height < min_size:
            # Aumentar imagem pequena mantendo proporção
            scale_factor = max(min_size/width, min_size/height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            image_array = np.array(image)
        
        # Redimensionar se muito grande (máximo 1200px)
        max_size = 1200
        if width > max_size or height > max_size:
            scale_factor = min(max_size/width, max_size/height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            image_array = np.array(image)
        
        # Melhorar contraste e nitidez para reconhecimento
        from PIL import ImageEnhance
        
        # Aumentar contraste levemente
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # Aumentar nitidez levemente
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Criar diretório do usuário
        caminho_usuario = os.path.join(USUARIOS_DIR, matricula_sanitizada)
        os.makedirs(caminho_usuario, exist_ok=True)
        
        # Salvar imagem com alta qualidade para reconhecimento
        caminho_foto = os.path.join(caminho_usuario, "foto.jpg")
        
        # Salvar com qualidade alta para melhor reconhecimento
        image.save(caminho_foto, 'JPEG', quality=95, optimize=False, subsampling=0)
        
        # Testar se consegue fazer encoding (validação)
        try:
            test_image = face_recognition.load_image_file(caminho_foto)
            encodings = face_recognition.face_encodings(test_image)
            print(f"✅ Foto processada - {len(encodings)} encoding(s) gerado(s)")
        except Exception as e:
            print(f"⚠️ Aviso: {e}")
        
        return True, caminho_foto
        
    except Exception as e:
        return False, f"Erro ao processar imagem: {str(e)}"

# Template HTML para interface por etapas
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 Catraca Virtual - Cadastro</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 0;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 400px;
            margin: 0 auto;
            background: linear-gradient(145deg, #2c2c54 0%, #40407a 100%);
            min-height: 100vh;
            position: relative;
            box-shadow: 0 0 30px rgba(0,0,0,0.5);
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 50%, #2c3e50 100%);
            color: white;
            padding: 40px 20px 30px;
            text-align: center;
            position: relative;
            border-bottom: 3px solid #e74c3c;
        }
        
        .step-indicator {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
            gap: 15px;
        }
        
        .step-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
            transition: all 0.3s ease;
        }
        
        .step-dot.active {
            background: #e74c3c;
            transform: scale(1.2);
            box-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
        }
        
        .step-dot.completed {
            background: #27ae60;
            box-shadow: 0 0 10px rgba(39, 174, 96, 0.3);
        }
        
        .step-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        
        .step-subtitle {
            font-size: 16px;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px 30px;
            text-align: center;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: rgba(255, 255, 255, 0.02);
        }
        
        .step-icon {
            width: 120px;
            height: 120px;
            margin: 0 auto 30px;
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            color: white;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(231, 76, 60, 0.3);
            border: 3px solid rgba(255, 255, 255, 0.1);
        }
        
        .form-group {
            margin-bottom: 25px;
            text-align: left;
        }
        
        .form-label {
            display: block;
            font-size: 16px;
            font-weight: 600;
            color: #ecf0f1;
            margin-bottom: 8px;
        }
        
        .form-input {
            width: 100%;
            padding: 18px 20px;
            border: 2px solid #34495e;
            border-radius: 12px;
            font-size: 16px;
            background: rgba(52, 73, 94, 0.8);
            color: #ecf0f1;
            transition: all 0.3s ease;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #e74c3c;
            background: rgba(52, 73, 94, 1);
            box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.2);
        }
        
        .form-input::placeholder {
            color: #95a5a6;
        }
        
        .file-input-container {
            position: relative;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .file-input-button {
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            box-shadow: 0 5px 15px rgba(231, 76, 60, 0.3);
        }
        
        .file-input-button:hover {
            transform: translateY(-2px);
        }
        
        .file-input-button:active {
            transform: translateY(0);
        }
        
        input[type="file"] {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        
        .preview-container {
            margin-top: 20px;
            border-radius: 12px;
            overflow: hidden;
            display: none;
        }
        
        .preview-image {
            width: 100%;
            max-height: 200px;
            object-fit: cover;
        }
        
        .action-button {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: auto;
            box-shadow: 0 5px 15px rgba(231, 76, 60, 0.3);
        }
        
        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(231, 76, 60, 0.4);
        }
        
        .action-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .countdown {
            font-size: 48px;
            font-weight: 700;
            color: #e74c3c;
            margin: 20px 0;
            text-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #c3e6cb;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }
        
        .step {
            display: none;
        }
        
        .step.active {
            display: block;
        }
        
        .back-button {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 10px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .progress-bar {
            position: absolute;
            bottom: 0;
            left: 0;
            height: 4px;
            background: linear-gradient(90deg, #e74c3c, #c0392b);
            transition: width 0.5s ease;
            box-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <button class="back-button" onclick="previousStep()" id="backBtn" style="display: none;">←</button>
            
            <div class="step-indicator">
                <div class="step-dot active" id="dot1"></div>
                <div class="step-dot" id="dot2"></div>
                <div class="step-dot" id="dot3"></div>
                <div class="step-dot" id="dot4"></div>
            </div>
            
            <div class="step-title" id="stepTitle">Bem-vindo!</div>
            <div class="step-subtitle" id="stepSubtitle">Vamos começar seu cadastro</div>
            
            <div class="progress-bar" id="progressBar" style="width: 25%"></div>
        </div>
        
        <div class="content">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="{{ 'success-message' if category == 'success' else 'error-message' }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form id="cadastroForm" method="POST" enctype="multipart/form-data">
                <!-- Etapa 1: Nome -->
                <div class="step active" id="step1">
                    <div class="step-icon">👤</div>
                    <div class="form-group">
                        <label class="form-label" for="nome">Nome Completo</label>
                        <input type="text" class="form-input" id="nome" name="nome" 
                               placeholder="Digite seu nome completo" required>
                    </div>
                    <button type="button" class="action-button" onclick="nextStep(1)">
                        Continuar
                    </button>
                </div>
                
                <!-- Etapa 2: Equipe -->
                <div class="step" id="step2">
                    <div class="step-icon">🏢</div>
                    <div class="form-group">
                        <label class="form-label" for="equipe">Equipe/Setor</label>
                        <input type="text" class="form-input" id="equipe" name="equipe" 
                               placeholder="Digite sua equipe ou setor" required>
                    </div>
                    <button type="button" class="action-button" onclick="nextStep(2)">
                        Continuar
                    </button>
                </div>
                
                <!-- Etapa 3: Matrícula -->
                <div class="step" id="step3">
                    <div class="step-icon">🎫</div>
                    <div class="form-group">
                        <label class="form-label" for="matricula">Matrícula</label>
                        <input type="text" class="form-input" id="matricula" name="matricula" 
                               placeholder="Digite sua matrícula" required>
                    </div>
                    <button type="button" class="action-button" onclick="nextStep(3)">
                        Continuar
                    </button>
                </div>
                
                <!-- Etapa 4: Foto -->
                <div class="step" id="step4">
                    <div class="step-icon">📸</div>
                    <div class="file-input-container">
                        <button type="button" class="file-input-button" id="fileButton">
                            📷 Selecionar Foto
                        </button>
                        <input type="file" id="foto" name="foto" accept="image/*" 
                               capture="environment" required onchange="previewImage()">
                    </div>
                    <div class="preview-container" id="previewContainer">
                        <img id="previewImage" class="preview-image" alt="Preview">
                    </div>
                    <button type="submit" class="action-button" id="submitBtn">
                        ✅ Finalizar Cadastro
                    </button>
                </div>
                
                <!-- Etapa 5: Sucesso com Countdown -->
                <div class="step" id="step5">
                    <div class="step-icon">✅</div>
                    <h2>Cadastro Realizado!</h2>
                    <p>Redirecionando em:</p>
                    <div class="countdown" id="countdown">5</div>
                    <p>Você já pode ser identificado pelo sistema</p>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        let currentStep = 1;
        const totalSteps = 4;
        
        const stepTitles = [
            "Bem-vindo!",
            "Seu Nome",
            "Sua Equipe", 
            "Sua Matrícula",
            "Sua Foto"
        ];
        
        const stepSubtitles = [
            "Vamos começar seu cadastro",
            "Como você gostaria de ser chamado?",
            "Qual é o seu setor de trabalho?",
            "Digite sua matrícula de identificação",
            "Tire uma foto para identificação"
        ];
        
        function updateUI() {
            // Atualizar título e subtítulo
            document.getElementById('stepTitle').textContent = stepTitles[currentStep];
            document.getElementById('stepSubtitle').textContent = stepSubtitles[currentStep];
            
            // Atualizar indicadores
            for (let i = 1; i <= totalSteps; i++) {
                const dot = document.getElementById(`dot${i}`);
                const step = document.getElementById(`step${i}`);
                
                if (i < currentStep) {
                    dot.className = 'step-dot completed';
                } else if (i === currentStep) {
                    dot.className = 'step-dot active';
                } else {
                    dot.className = 'step-dot';
                }
                
                step.className = i === currentStep ? 'step active' : 'step';
            }
            
            // Atualizar barra de progresso
            const progress = (currentStep / totalSteps) * 100;
            document.getElementById('progressBar').style.width = progress + '%';
            
            // Mostrar/ocultar botão voltar
            document.getElementById('backBtn').style.display = currentStep > 1 ? 'block' : 'none';
        }
        
        function nextStep(step) {
            // Validar campo atual
            let isValid = true;
            let fieldValue = '';
            
            switch(step) {
                case 1:
                    fieldValue = document.getElementById('nome').value.trim();
                    if (!fieldValue) {
                        alert('Por favor, digite seu nome completo');
                        isValid = false;
                    }
                    break;
                case 2:
                    fieldValue = document.getElementById('equipe').value.trim();
                    if (!fieldValue) {
                        alert('Por favor, digite sua equipe/setor');
                        isValid = false;
                    }
                    break;
                case 3:
                    fieldValue = document.getElementById('matricula').value.trim();
                    if (!fieldValue) {
                        alert('Por favor, digite sua matrícula');
                        isValid = false;
                    }
                    break;
            }
            
            if (isValid && currentStep < totalSteps) {
                currentStep++;
                updateUI();
            }
        }
        
        function previousStep() {
            if (currentStep > 1) {
                currentStep--;
                updateUI();
            }
        }
        
        function previewImage() {
            const file = document.getElementById('foto').files[0];
            const previewContainer = document.getElementById('previewContainer');
            const previewImage = document.getElementById('previewImage');
            const button = document.getElementById('fileButton');
            
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
        
        document.getElementById('cadastroForm').onsubmit = function(e) {
            // Validar se todos os campos estão preenchidos
            const nome = document.getElementById('nome').value.trim();
            const equipe = document.getElementById('equipe').value.trim();
            const matricula = document.getElementById('matricula').value.trim();
            const foto = document.getElementById('foto').files[0];
            
            if (!nome || !equipe || !matricula || !foto) {
                e.preventDefault();
                alert('Por favor, preencha todos os campos e selecione uma foto.');
                return false;
            }
            
            // Desabilitar botão
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = '📤 Enviando...';
        };
        
        function startCountdown() {
            let count = 5;
            const countdownEl = document.getElementById('countdown');
            
            const timer = setInterval(() => {
                count--;
                countdownEl.textContent = count;
                
                if (count <= 0) {
                    clearInterval(timer);
                    window.location.href = '/';
                }
            }, 1000);
        }
        
        // Verificar se deve mostrar tela de sucesso
        if (window.location.search.includes('success=1')) {
            currentStep = 5;
            document.getElementById('step5').className = 'step active';
            document.getElementById('stepTitle').textContent = 'Sucesso!';
            document.getElementById('stepSubtitle').textContent = 'Cadastro realizado com sucesso';
            document.getElementById('progressBar').style.width = '100%';
            
            // Marcar todos os dots como completos
            for (let i = 1; i <= 4; i++) {
                document.getElementById(`dot${i}`).className = 'step-dot completed';
            }
            
            startCountdown();
        }
        
        // Prevenir envio com Enter nas etapas
        document.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && currentStep < 4) {
                e.preventDefault();
                nextStep(currentStep);
            }
        });
        
        // Configurar evento do botão de arquivo
        document.getElementById('fileButton').onclick = function() {
            document.getElementById('foto').click();
        };
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
        matricula = request.form.get('matricula', '').strip()
        foto = request.files.get('foto')
        
        # Validações
        if not nome or not equipe or not matricula or not foto:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('index'))
        
        matricula_sanitizada = sanitizar_matricula(matricula)
        if len(matricula_sanitizada) == 0:
            flash('Matrícula não pode estar vazia.', 'error')
            return redirect(url_for('index'))
        
        # Verificar se usuário já existe
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nome FROM usuarios WHERE cpf = ?', (matricula_sanitizada,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            flash(f'Pessoa "{existing[0]}" já cadastrada com esta matrícula.', 'error')
            return redirect(url_for('index'))
        
        # Processar foto
        sucesso, resultado = processar_foto_upload(foto, matricula_sanitizada, nome)
        
        if not sucesso:
            flash(resultado, 'error')
            return redirect(url_for('index'))
        
        # Salvar no banco de dados
        if salvar_usuario_db(nome, equipe, matricula_sanitizada, resultado):
            flash(f'✅ {nome} cadastrado com sucesso!', 'success')
            return redirect(url_for('index') + '?success=1')
        else:
            flash('Erro ao salvar no banco de dados. Matrícula pode já estar em uso.', 'error')
        
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_local_server(port=5000):
    """Executa o servidor web local."""
    local_ip = get_local_ip()
    print(f"\n📱 === SERVIDOR LOCAL INICIADO ===")
    print(f"📱 Acesso via CELULAR: http://{local_ip}:{port}")
    print(f"💻 Acesso via COMPUTADOR: http://localhost:{port}")
    print(f"📊 Status do sistema: http://{local_ip}:{port}/status")
    print(f"🛑 Para parar: Ctrl+C")
    print("=" * 50)
    print("💡 Cadastro por etapas com interface moderna!")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_local_server()