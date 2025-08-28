# catraca_virtual.py
# Sistema de Controle de Acesso com Reconhecimento Facial via Webcam

import cv2
import face_recognition
import os
import json
import numpy as np
import re
import sqlite3
import threading
import time
import csv
from datetime import datetime
from typing import List, Tuple, Optional, Dict

# --- CONFIGURAÇÕES GLOBAIS ---
USUARIOS_DIR = "usuarios"
DB_FILE = "catraca_virtual.db"
LOG_FILE = "acessos.csv"
FACE_MATCH_THRESHOLD = 0.6  # Nível de tolerância para reconhecimento (0.6 é o padrão)

# Variáveis globais para controle da câmera
camera_active = False
camera_thread = None
current_frame = None
frame_lock = threading.Lock()
known_face_encodings = []
known_user_data = []
last_recognition_time = 0
RECOGNITION_COOLDOWN = 3  # segundos entre reconhecimentos

# --- FUNÇÕES AUXILIARES E DE SETUP ---

def setup():
    """Cria os diretórios e arquivos necessários se não existirem."""
    if not os.path.exists(USUARIOS_DIR):
        os.makedirs(USUARIOS_DIR)
        print(f"📁 Diretório '{USUARIOS_DIR}' criado.")

    # Configurar banco de dados SQLite
    setup_database()
    print("✅ Sistema inicializado com sucesso!")

def setup_database():
    """Configura o banco de dados SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            equipe TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            foto_path TEXT NOT NULL,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de acessos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT,
            equipe TEXT,
            cpf TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT,
            status TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🗃️ Banco de dados configurado.")

def sanitizar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos de um CPF."""
    return re.sub(r'\D', '', cpf)

def draw_face_landmarks(frame, face_location, color=(0, 255, 0), thickness=2):
    """Desenha marcos faciais estilizados similar à imagem de referência."""
    top, right, bottom, left = face_location
    
    # Calcular dimensões do rosto
    width = right - left
    height = bottom - top
    corner_length = min(width, height) // 4
    
    # Desenhar cantos do retângulo (estilo futurístico)
    # Canto superior esquerdo
    cv2.line(frame, (left, top), (left + corner_length, top), color, thickness)
    cv2.line(frame, (left, top), (left, top + corner_length), color, thickness)
    
    # Canto superior direito
    cv2.line(frame, (right, top), (right - corner_length, top), color, thickness)
    cv2.line(frame, (right, top), (right, top + corner_length), color, thickness)
    
    # Canto inferior esquerdo
    cv2.line(frame, (left, bottom), (left + corner_length, bottom), color, thickness)
    cv2.line(frame, (left, bottom), (left, bottom - corner_length), color, thickness)
    
    # Canto inferior direito
    cv2.line(frame, (right, bottom), (right - corner_length, bottom), color, thickness)
    cv2.line(frame, (right, bottom), (right, bottom - corner_length), color, thickness)
    
    # Linhas diagonais internas (efeito de análise)
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    
    # Linhas cruzadas no centro
    cross_size = min(width, height) // 8
    cv2.line(frame, (center_x - cross_size, center_y), (center_x + cross_size, center_y), color, 1)
    cv2.line(frame, (center_x, center_y - cross_size), (center_x, center_y + cross_size), color, 1)
    
    # Pontos de análise facial
    points = [
        (center_x, top + height // 4),  # Testa
        (left + width // 4, center_y),  # Olho esquerdo área
        (right - width // 4, center_y),  # Olho direito área
        (center_x, center_y + height // 6),  # Nariz
        (center_x, bottom - height // 4)  # Boca
    ]
    
    for point in points:
        cv2.circle(frame, point, 3, color, -1)
        cv2.circle(frame, point, 8, color, 1)

def draw_recognition_interface(frame, face_locations, face_names, distances, passage_times=None):
    """Desenha a interface de identificação facial."""
    for i, ((top, right, bottom, left), name, distance) in enumerate(zip(face_locations, face_names, distances)):
        # Escalar coordenadas de volta para o frame original (se necessário)
        if hasattr(draw_recognition_interface, 'scale_factor'):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
        
        if name != "Desconhecido":
            # Usuário identificado - verde
            color = (0, 255, 0)
            status = "IDENTIFICADO"
            draw_face_landmarks(frame, (top, right, bottom, left), color, 3)
            
            # Obter horário atual formatado
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # Texto do usuário identificado com horário
            cv2.putText(frame, f"PASSAGEM: {current_time}", (left + 6, top - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(frame, name, (left + 6, top - 15), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)
            cv2.putText(frame, status, (left + 6, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            # Usuário não identificado - amarelo (não é erro, apenas não cadastrado)
            color = (0, 255, 255)
            status = "NAO CADASTRADO"
            draw_face_landmarks(frame, (top, right, bottom, left), color, 2)
            
            # Texto pessoa não cadastrada
            cv2.putText(frame, status, (left + 6, bottom + 25), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
    
    # Interface de status no topo apenas
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
    
    # Texto de status no topo
    cv2.putText(frame, "SISTEMA DE IDENTIFICACAO - CATRACA", (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Pessoas cadastradas: {len(known_face_encodings)} | Rostos detectados: {len(face_locations)}", 
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def capturar_rosto_otimizado(cpf_sanitizado: str) -> bool:
    """
    Captura rosto de forma otimizada para melhor reconhecimento.
    """
    print("🎥 Iniciando captura de rosto...")
    
    # Tentar diferentes índices de câmera
    cap = None
    for camera_idx in range(3):
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                print(f"✅ Câmera {camera_idx} funcionando!")
                break
            else:
                cap.release()
        cap = None
    
    if cap is None:
        print("❌ Erro: Não foi possível abrir a câmera.")
        return False

    # Configurar câmera para melhor qualidade
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("📸 Posicione seu rosto no centro. Pressione ESPAÇO para capturar ou ESC para cancelar.")
    
    best_frame = None
    best_quality = 0
    frames_captured = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detectar rostos
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        # Interface simples de captura
        display_frame = frame.copy()
        
        if len(face_locations) == 1:
            top, right, bottom, left = face_locations[0]
            
            # Desenhar interface de reconhecimento
            draw_face_landmarks(display_frame, face_locations[0], (0, 255, 0), 3)
            
            # Calcular qualidade da detecção (baseado no tamanho do rosto)
            face_size = (right - left) * (bottom - top)
            quality_score = min(100, face_size / 10000 * 100)
            
            if quality_score > best_quality:
                best_quality = quality_score
                best_frame = frame.copy()
            
            # Mostrar status
            cv2.putText(display_frame, "ROSTO DETECTADO", (left, top - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Qualidade: {quality_score:.0f}%", (left, bottom + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display_frame, "ESPACO: Capturar | ESC: Cancelar", (10, display_frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
        elif len(face_locations) == 0:
            cv2.putText(display_frame, "POSICIONE SEU ROSTO NO CENTRO", 
                       (display_frame.shape[1]//2 - 200, display_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            cv2.putText(display_frame, "APENAS UM ROSTO POR VEZ", 
                       (display_frame.shape[1]//2 - 150, display_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow('Cadastro - Captura de Rosto', display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("❌ Cadastro cancelado.")
            break
        elif key == 32:  # ESPAÇO
            if len(face_locations) == 1 and best_frame is not None:
                print("💾 Salvando melhor foto capturada...")
                
                # Criar diretório
                caminho_usuario = os.path.join(USUARIOS_DIR, cpf_sanitizado)
                os.makedirs(caminho_usuario, exist_ok=True)
                
                # Salvar foto
                caminho_foto = os.path.join(caminho_usuario, "foto.jpg")
                success = cv2.imwrite(caminho_foto, best_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                if success:
                    # Testar encoding imediatamente
                    try:
                        test_image = face_recognition.load_image_file(caminho_foto)
                        encodings = face_recognition.face_encodings(test_image)
                        if len(encodings) > 0:
                            print(f"✅ Foto salva com sucesso! Qualidade: {best_quality:.0f}%")
                            cap.release()
                            cv2.destroyAllWindows()
                            return True
                        else:
                            print("❌ Erro: Não foi possível gerar encoding da foto. Tente novamente.")
                    except Exception as e:
                        print(f"❌ Erro ao processar foto: {e}")
                else:
                    print("❌ Erro ao salvar foto.")
            else:
                print("❌ Posicione apenas um rosto no centro e tente novamente.")

    cap.release()
    cv2.destroyAllWindows()
    return False

def capturar_rosto(cpf_sanitizado: str) -> bool:
    """Função de compatibilidade."""
    return capturar_rosto_otimizado(cpf_sanitizado)

def iniciar_camera_continua():
    """Inicia a câmera em modo contínuo para reconhecimento."""
    global camera_active, current_frame, frame_lock, known_face_encodings, known_user_data, last_recognition_time
    
    print("🎥 Iniciando câmera contínua...")
    
    # Tentar diferentes índices de câmera
    cap = None
    for camera_idx in range(3):
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                print(f"✅ Câmera {camera_idx} funcionando!")
                break
            else:
                cap.release()
        else:
            cap.release() if cap else None
        cap = None
    
    if cap is None:
        print("❌ Erro: Não foi possível abrir a câmera.")
        return False
    
    # Configurar resolução da câmera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    camera_active = True
    print("✅ Câmera ativa! Sistema de reconhecimento iniciado.")
    
    while camera_active:
        ret, frame = cap.read()
        if not ret:
            print("❌ Erro ao capturar frame")
            continue
        
        # Atualizar frame global
        with frame_lock:
            current_frame = frame.copy()
        
        # Processamento de reconhecimento facial
        current_time = time.time()
        if current_time - last_recognition_time > 0.5:  # Processar a cada 0.5 segundos
            # Redimensionar para processamento mais rápido
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detectar rostos
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            face_names = []
            face_distances = []
            
            for face_encoding in face_encodings:
                if len(known_face_encodings) > 0:
                    # Comparar com rostos conhecidos
                    distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(distances)
                    
                    if distances[best_match_index] <= FACE_MATCH_THRESHOLD:
                        # Usuário reconhecido
                        user_data = known_user_data[best_match_index]
                        face_names.append(user_data['nome'])
                        face_distances.append(distances[best_match_index])
                        
                        # Registrar passagem (com cooldown)
                        if current_time - last_recognition_time > RECOGNITION_COOLDOWN:
                            tipo = determinar_tipo_acesso_db(user_data['cpf'])
                            registrar_acesso_db(user_data, "Identificado", tipo)
                            print(f"👤 Pessoa identificada: {user_data['nome']} ({user_data['equipe']}) - {tipo}")
                            last_recognition_time = current_time
                    else:
                        face_names.append("Desconhecido")
                        face_distances.append(distances[best_match_index])
                else:
                    face_names.append("Desconhecido")
                    face_distances.append(1.0)
            
            # Escalar coordenadas de volta para frame original
            face_locations = [(top * 4, right * 4, bottom * 4, left * 4) 
                            for (top, right, bottom, left) in face_locations]
            
            # Desenhar interface de reconhecimento
            if face_locations:
                draw_recognition_interface(frame, face_locations, face_names, face_distances)
            else:
                # Interface quando nenhum rosto detectado - apenas cabeçalho
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
                
                cv2.putText(frame, "SISTEMA DE IDENTIFICACAO - CATRACA", (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, f"Pessoas cadastradas: {len(known_face_encodings)} | Aguardando passagem...", 
                            (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Mostrar frame
        cv2.imshow('Catraca Virtual - Sistema Ativo', frame)
        
        # Verificar teclas
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c') or key == ord('C'):
            # Parar câmera completamente para cadastro
            camera_active = False
            cap.release()
            cv2.destroyAllWindows()
            print("\n📷 Câmera fechada para cadastro...")
            
            if cadastrar_usuario_db():
                print("🔄 Recarregando pessoas cadastradas...")
                carregar_usuarios_db()
            
            print("🎥 Reiniciando sistema de identificação...")
            return "restart"
        elif key == 27:  # ESC
            # Pausar para menu
            parar_camera()
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return True

def parar_camera():
    """Para a câmera contínua."""
    global camera_active
    camera_active = False
    cv2.destroyAllWindows()
    print("📷 Câmera pausada.")

# --- FUNÇÕES DO BANCO DE DADOS ---

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
        print("❌ Usuário com este CPF já está cadastrado no banco.")
        return False
    except Exception as e:
        print(f"❌ Erro ao salvar usuário no banco: {e}")
        return False

def carregar_usuarios_db():
    """Carrega usuários do banco de dados."""
    global known_face_encodings, known_user_data
    
    known_face_encodings = []
    known_user_data = []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT nome, equipe, cpf, foto_path FROM usuarios')
        usuarios = cursor.fetchall()
        conn.close()
        
        print(f"📊 Carregando {len(usuarios)} usuário(s) do banco...")
        
        for nome, equipe, cpf, foto_path in usuarios:
            try:
                if os.path.exists(foto_path):
                    imagem = face_recognition.load_image_file(foto_path)
                    encodings = face_recognition.face_encodings(imagem)
                    
                    if len(encodings) > 0:
                        known_face_encodings.append(encodings[0])
                        known_user_data.append({
                            'nome': nome,
                            'equipe': equipe, 
                            'cpf': cpf,
                            'foto_path': foto_path
                        })
                        print(f"✅ {nome} carregado")
                    else:
                        print(f"⚠️ Nenhum rosto encontrado na foto de {nome}")
                else:
                    print(f"❌ Foto não encontrada: {foto_path}")
            except Exception as e:
                print(f"❌ Erro ao carregar {nome}: {e}")
        
        print(f"✅ {len(known_face_encodings)} usuário(s) prontos para reconhecimento")
        
    except Exception as e:
        print(f"❌ Erro ao carregar usuários do banco: {e}")

def registrar_acesso_db(dados_usuario: dict, status: str, tipo: str = "N/A"):
    """Registra acesso no banco de dados."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Buscar ID do usuário se for autorizado
        usuario_id = None
        if status == "Identificado" and dados_usuario:
            cursor.execute('SELECT id FROM usuarios WHERE cpf = ?', (dados_usuario['cpf'],))
            result = cursor.fetchone()
            if result:
                usuario_id = result[0]
        
        cursor.execute('''
            INSERT INTO acessos (usuario_id, nome, equipe, cpf, tipo, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id,
            dados_usuario.get('nome', 'Desconhecido'),
            dados_usuario.get('equipe', 'N/A'),
            dados_usuario.get('cpf', 'N/A'),
            tipo,
            status
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao registrar acesso: {e}")

def determinar_tipo_acesso_db(cpf: str) -> str:
    """Determina tipo de acesso baseado no último registro do banco."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tipo FROM acessos 
            WHERE cpf = ? AND status = "Identificado"
            ORDER BY data_hora DESC LIMIT 1
        ''', (cpf,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == "ENTRADA":
            return "SAÍDA"
        else:
            return "ENTRADA"
            
    except Exception as e:
        print(f"❌ Erro ao determinar tipo de acesso: {e}")
        return "ENTRADA"

# --- FUNÇÕES PRINCIPAIS DO SISTEMA ---

def cadastrar_usuario_db():
    """Coleta dados do usuário, captura o rosto e salva no banco de dados."""
    print("\n🆕 === CADASTRO DE NOVA PESSOA ===")
    
    # Coleta de dados essenciais
    nome = input("👤 Nome completo: ").strip()
    if not nome:
        print("❌ Nome é obrigatório.")
        return False
    
    equipe = input("🏢 Equipe/Setor: ").strip()
    if not equipe:
        print("❌ Equipe é obrigatória.")
        return False
    
    # Simplificar CPF - aceitar qualquer sequência de números
    while True:
        cpf = input("🆔 CPF (11 dígitos): ").strip()
        cpf_sanitizado = sanitizar_cpf(cpf)
        
        if len(cpf_sanitizado) == 11:
            break
        elif len(cpf_sanitizado) == 0:
            print("❌ Digite o CPF.")
            continue
        else:
            print(f"❌ CPF deve ter 11 dígitos. Você digitou {len(cpf_sanitizado)} dígitos.")
            print(f"💡 Exemplo: 12345678901")
            continue

    # Verificar se usuário já existe
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT nome FROM usuarios WHERE cpf = ?', (cpf_sanitizado,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            print(f"❌ Pessoa '{existing[0]}' já cadastrada com este CPF.")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar CPF: {e}")
        return False

    print(f"\n📸 Agora vamos capturar sua foto, {nome}!")
    print("💡 Posicione-se bem na frente da câmera")
    input("📷 Pressione ENTER quando estiver pronto...")
    
    # Capturar foto de forma mais simples
    if capturar_foto_simples(cpf_sanitizado, nome):
        foto_path = os.path.join(USUARIOS_DIR, cpf_sanitizado, "foto.jpg")
        
        # Salvar no banco de dados
        if salvar_usuario_db(nome, equipe, cpf_sanitizado, foto_path):
            print(f"\n✅ {nome} cadastrado com sucesso!")
            print(f"📁 CPF: {cpf_sanitizado}")
            print(f"🏢 Equipe: {equipe}")
            print(f"📸 Foto salva")
            return True
        else:
            print("❌ Falha ao salvar no banco de dados.")
    else:
        print("❌ Falha na captura da foto.")
    
    return False

def capturar_foto_simples(cpf_sanitizado: str, nome: str) -> bool:
    """Captura foto de forma mais simples e direta."""
    print("🎥 Abrindo câmera...")
    
    # Abrir câmera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Erro: Não foi possível abrir a câmera.")
        return False

    # Configurar câmera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("📸 Câmera aberta! Posicione seu rosto e pressione ESPAÇO para capturar")
    print("🚫 Pressione ESC para cancelar")
    
    melhor_foto = None
    melhor_score = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detectar rostos
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        # Preparar frame para exibição
        display_frame = frame.copy()
        
        if len(face_locations) == 1:
            top, right, bottom, left = face_locations[0]
            
            # Desenhar retângulo ao redor do rosto
            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
            
            # Calcular score baseado no tamanho do rosto
            face_size = (right - left) * (bottom - top)
            score = min(100, face_size / 15000 * 100)
            
            if score > melhor_score:
                melhor_score = score
                melhor_foto = frame.copy()
            
            # Mostrar informações
            cv2.putText(display_frame, f"{nome}", (left, top - 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display_frame, "ROSTO DETECTADO", (left, top - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Qualidade: {score:.0f}%", (left, bottom + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Instruções
            cv2.putText(display_frame, "ESPACO: Capturar Foto | ESC: Cancelar", 
                       (10, display_frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
        elif len(face_locations) == 0:
            cv2.putText(display_frame, "POSICIONE SEU ROSTO NA CAMERA", 
                       (display_frame.shape[1]//2 - 250, display_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        else:
            cv2.putText(display_frame, "APENAS UM ROSTO POR VEZ", 
                       (display_frame.shape[1]//2 - 180, display_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow(f'Cadastro: {nome}', display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("❌ Captura cancelada.")
            break
        elif key == 32:  # ESPAÇO
            if len(face_locations) == 1 and melhor_foto is not None:
                print(f"📸 Foto capturada! Qualidade: {melhor_score:.0f}%")
                
                # Criar diretório e salvar
                caminho_usuario = os.path.join(USUARIOS_DIR, cpf_sanitizado)
                os.makedirs(caminho_usuario, exist_ok=True)
                
                caminho_foto = os.path.join(caminho_usuario, "foto.jpg")
                success = cv2.imwrite(caminho_foto, melhor_foto, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                if success:
                    # Testar se o reconhecimento funciona
                    try:
                        test_image = face_recognition.load_image_file(caminho_foto)
                        encodings = face_recognition.face_encodings(test_image)
                        if len(encodings) > 0:
                            print("✅ Foto processada com sucesso!")
                            cap.release()
                            cv2.destroyAllWindows()
                            return True
                        else:
                            print("❌ Erro no processamento da foto. Tente novamente.")
                    except Exception as e:
                        print(f"❌ Erro ao processar foto: {e}")
                else:
                    print("❌ Erro ao salvar foto.")
            else:
                print("❌ Posicione apenas um rosto e tente novamente.")

    cap.release()
    cv2.destroyAllWindows()
    return False

def cadastrar_usuario():
    """Função de compatibilidade - redireciona para versão com banco."""
    cadastrar_usuario_db()


def carregar_dados_usuarios():
    """Carrega os encodings faciais e dados de todos os usuários cadastrados."""
    known_face_encodings = []
    known_user_data = []

    if not os.path.exists(USUARIOS_DIR):
        print(f"⚠️ Diretório {USUARIOS_DIR} não existe")
        return known_face_encodings, known_user_data

    usuarios_encontrados = os.listdir(USUARIOS_DIR)
    print(f"📁 Verificando diretórios em {USUARIOS_DIR}: {usuarios_encontrados}")

    for cpf_dir in usuarios_encontrados:
        caminho_usuario = os.path.join(USUARIOS_DIR, cpf_dir)
        if os.path.isdir(caminho_usuario):
            print(f"👤 Processando usuário: {cpf_dir}")
            try:
                caminho_foto = os.path.join(caminho_usuario, "foto.jpg")
                caminho_json = os.path.join(caminho_usuario, "dados.json")

                # Verificar se os arquivos existem
                if not os.path.exists(caminho_foto):
                    print(f"❌ Foto não encontrada: {caminho_foto}")
                    continue
                    
                if not os.path.exists(caminho_json):
                    print(f"❌ Dados não encontrados: {caminho_json}")
                    continue

                # Carregar dados JSON
                with open(caminho_json, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                print(f"✅ Dados carregados: {dados}")
                
                # Carregar e processar imagem
                print(f"📸 Carregando foto: {caminho_foto}")
                imagem = face_recognition.load_image_file(caminho_foto)
                encodings = face_recognition.face_encodings(imagem)
                
                if len(encodings) == 0:
                    print(f"❌ Nenhum rosto encontrado na foto de {dados.get('nome', cpf_dir)}")
                    continue
                elif len(encodings) > 1:
                    print(f"⚠️ Múltiplos rostos encontrados na foto de {dados.get('nome', cpf_dir)}, usando o primeiro")
                
                encoding = encodings[0]
                
                known_face_encodings.append(encoding)
                known_user_data.append(dados)
                print(f"✅ Usuário {dados.get('nome', cpf_dir)} carregado com sucesso")
                
            except Exception as e:
                print(f"❌ Erro ao carregar dados do usuário {cpf_dir}: {e}")
                import traceback
                traceback.print_exc()

    print(f"📊 Total de usuários carregados: {len(known_face_encodings)}")
    return known_face_encodings, known_user_data

def registrar_acesso(dados_usuario, status, tipo="N/A"):
    """Registra uma tentativa de acesso (autorizada ou negada) no arquivo CSV."""
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    nome = dados_usuario.get('nome', 'Desconhecido')
    equipe = dados_usuario.get('equipe', 'N/A')
    cpf = dados_usuario.get('cpf', 'N/A')

    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([nome, equipe, cpf, agora, tipo, status])
    
    print(f"Registro de acesso: {status} para {nome} às {agora}")

def determinar_tipo_acesso(cpf: str) -> str:
    """Verifica o último acesso do usuário para determinar se é ENTRADA ou SAÍDA."""
    ultimo_tipo = "SAÍDA" # Default para primeiro acesso
    try:
        with open(LOG_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logs_usuario = [
                row for row in reader 
                if row["CPF"] == cpf and row["Status"] == "Identificado"
            ]
            if logs_usuario:
                ultimo_log = logs_usuario[-1]
                if ultimo_log["Tipo"] == "ENTRADA":
                    ultimo_tipo = "ENTRADA"

    except FileNotFoundError:
        return "ENTRADA"

    return "SAÍDA" if ultimo_tipo == "ENTRADA" else "ENTRADA"


def validar_acesso():
    """Ativa a webcam para reconhecer um usuário e registrar o acesso."""
    print("\n--- Validando Acesso ---")
    print("Carregando dados dos usuários...")
    
    known_face_encodings, known_user_data = carregar_dados_usuarios()

    if not known_face_encodings:
        print("❌ Nenhum usuário cadastrado. Cadastre alguém primeiro.")
        return
    
    print(f"✅ {len(known_face_encodings)} usuário(s) carregado(s)")

    print("Tentando abrir a webcam...")
    
    # Tentar diferentes índices de câmera
    cap = None
    for camera_idx in range(3):
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                print(f"✅ Câmera {camera_idx} funcionando!")
                break
            else:
                cap.release()
        else:
            cap.release() if cap else None
        cap = None
    
    if cap is None or not cap.isOpened():
        print("❌ Erro: Não foi possível abrir a webcam.")
        print("Verifique se a câmera não está sendo usada por outro aplicativo.")
        return

    print("✅ Webcam ativada. Posicione o rosto para validação.")
    print("Pressione 'q' para sair.")
    
    rosto_detectado_sem_match = False
    frames_sem_rosto = 0
    max_frames_sem_rosto = 30  # ~1 segundo a 30fps

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Erro ao capturar frame da câmera")
            break

        # Processamento mais rápido - reduzir tamanho
        rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        # Mostrar status na tela
        status_text = f"Rostos detectados: {len(face_locations)}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Usuarios cadastrados: {len(known_face_encodings)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if len(face_locations) == 0:
            frames_sem_rosto += 1
            cv2.putText(frame, "Nenhum rosto detectado", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            frames_sem_rosto = 0

        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Calcular distâncias para todos os usuários conhecidos
            distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            melhor_match_idx = np.argmin(distances)
            melhor_distancia = distances[melhor_match_idx]
            
            # Escalar coordenadas de volta para o frame original
            top, right, bottom, left = [i * 4 for i in face_location]
            
            print(f"Distância do melhor match: {melhor_distancia:.3f} (threshold: {FACE_MATCH_THRESHOLD})")
            
            if melhor_distancia <= FACE_MATCH_THRESHOLD:
                dados_usuario = known_user_data[melhor_match_idx]
                
                # Desenha um retângulo verde e exibe o nome
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
                cv2.putText(frame, dados_usuario['nome'], (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, f"Match: {melhor_distancia:.3f}", (left + 6, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                print(f"✅ Usuário reconhecido: {dados_usuario['nome']} (distância: {melhor_distancia:.3f})")
                tipo = determinar_tipo_acesso(dados_usuario['cpf'])
                registrar_acesso(dados_usuario, "Identificado", tipo)
                print(f"🚪 Acesso Liberado! Tipo: {tipo}")
                
                # Mostrar por 2 segundos antes de fechar
                cv2.imshow('Catraca Virtual - ACESSO LIBERADO', frame)
                cv2.waitKey(2000)

                cap.release()
                cv2.destroyAllWindows()
                return # Sai da função após sucesso

            else:
                # Rosto detectado mas não reconhecido
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, "NAO RECONHECIDO", (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(frame, f"Dist: {melhor_distancia:.3f}", (left + 6, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                rosto_detectado_sem_match = True

        cv2.imshow('Catraca Virtual', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if rosto_detectado_sem_match:
        print("❌ Acesso Negado. Rosto detectado mas não corresponde a nenhum usuário cadastrado.")
        registrar_acesso({}, "Negado")
        
    cap.release()
    cv2.destroyAllWindows()


def visualizar_registros_db():
    """Exibe os registros de passagens do banco de dados."""
    print("\n--- Histórico de Passagens ---")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT nome, equipe, cpf, data_hora, tipo, status 
            FROM acessos 
            ORDER BY data_hora DESC 
            LIMIT 50
        ''')
        
        registros = cursor.fetchall()
        conn.close()
        
        if not registros:
            print("Nenhum registro de passagem encontrado.")
            return
        
        print(f"{'Nome':<25} | {'Equipe':<15} | {'CPF':<12} | {'Data/Hora':<20} | {'Movimento':<8} | {'Status'}")
        print("-" * 100)
        
        for nome, equipe, cpf, data_hora, tipo, status in registros:
            print(f"{nome:<25} | {equipe:<15} | {cpf:<12} | {data_hora:<20} | {tipo:<8} | {status}")
            
    except Exception as e:
        print(f"❌ Erro ao ler registros do banco: {e}")

def listar_usuarios_db():
    """Lista todos os usuários cadastrados no banco."""
    print("\n--- Usuários Cadastrados ---")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT nome, equipe, cpf, data_cadastro FROM usuarios ORDER BY nome')
        usuarios = cursor.fetchall()
        conn.close()
        
        if not usuarios:
            print("Nenhum usuário cadastrado.")
            return
        
        print(f"{'Nome':<25} | {'Equipe':<15} | {'CPF':<12} | {'Data Cadastro':<20}")
        print("-" * 80)
        
        for nome, equipe, cpf, data_cadastro in usuarios:
            print(f"{nome:<25} | {equipe:<15} | {cpf:<12} | {data_cadastro:<20}")
            
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")

def iniciar_servidor_web():
    """Inicia o servidor web para cadastro remoto."""
    try:
        import subprocess
        import socket
        
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return "127.0.0.1"
        
        local_ip = get_local_ip()
        port = 5000
        
        print(f"\n🌐 === INICIANDO SERVIDOR WEB ===")
        print(f"📱 Acesse pelo celular: http://{local_ip}:{port}")
        print(f"💻 Acesse pelo computador: http://localhost:{port}")
        print(f"📊 Status: http://{local_ip}:{port}/status")
        print(f"🛑 Para parar: Ctrl+C")
        print("=" * 50)
        print("💡 Deixe este servidor rodando e use o celular para cadastrar!")
        print("💡 Pressione Ctrl+C quando terminar de cadastrar")
        
        # Executar servidor web
        subprocess.run([
            "python", "web_server.py"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
    except KeyboardInterrupt:
        print("\n🛑 Servidor web parado.")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor web: {e}")
        print("💡 Certifique-se de que o arquivo web_server.py existe")

def menu_sistema():
    """Menu do sistema quando a câmera está pausada."""
    while True:
        print("\n=== SISTEMA DE IDENTIFICAÇÃO - CATRACA ===")
        print("1. 🎥 Iniciar sistema de identificação")
        print("2. 👤 Cadastrar nova pessoa (terminal)")
        print("3. 📱 Cadastrar via celular (servidor web)")
        print("4. 📊 Visualizar registro de passagens")
        print("5. 👥 Listar pessoas cadastradas")
        print("6. 🚪 Sair")
        
        escolha = input("\nEscolha uma opção: ").strip()

        if escolha == '1':
            carregar_usuarios_db()
            return  # Retorna para reiniciar a câmera
        elif escolha == '2':
            cadastrar_usuario_db()
            carregar_usuarios_db()
        elif escolha == '3':
            iniciar_servidor_web()
            carregar_usuarios_db()  # Recarregar após cadastros remotos
        elif escolha == '4':
            visualizar_registros_db()
        elif escolha == '5':
            listar_usuarios_db()
        elif escolha == '6':
            print("👋 Saindo do sistema...")
            break
        else:
            print("❌ Opção inválida. Tente novamente.")

# --- INTERFACE PRINCIPAL ---

def main():
    """Função principal do sistema."""
    print("🚀 Iniciando Sistema de Identificação - Catraca...")
    setup()
    carregar_usuarios_db()
    
    print("\n✅ Sistema pronto!")
    print("💡 A câmera ficará ativa para identificação automática de pessoas.")
    print("💡 Pressione 'C' durante a identificação para cadastrar nova pessoa.")
    
    # Loop principal com reinicio automático
    try:
        while True:
            result = iniciar_camera_continua()
            if result == "restart":
                # Reiniciar câmera após cadastro
                continue
            else:
                # Saiu da câmera normalmente - mostrar menu
                menu_sistema()
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro no sistema: {e}")
        print("Tentando continuar no modo menu...")
        menu_sistema()
    finally:
        parar_camera()
        print("👋 Sistema finalizado.")

# Funções de compatibilidade para manter compatibilidade com versão anterior
def visualizar_registros():
    """Função de compatibilidade - redireciona para versão com banco."""
    visualizar_registros_db()

def validar_acesso_compat():
    """Função de compatibilidade - agora integrada ao sistema contínuo."""
    print("💡 Use o sistema contínuo (opção 1) para validação automática de acesso.")
    print("Ou pressione 'C' durante o reconhecimento para cadastrar novo usuário.")

if __name__ == "__main__":
    main()
