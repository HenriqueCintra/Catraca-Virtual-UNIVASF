# Sistema de Catraca Virtual

Sistema de controle de acesso com reconhecimento facial desenvolvido em Python, utilizando webcam para captura e validação de usuários.

## Funcionalidades

### ✅ Cadastro de Usuários

- Coleta de dados: Nome completo, Equipe, CPF
- Captura de foto via webcam no momento do cadastro
- Armazenamento organizado por CPF em `usuarios/CPF/`
- Validação de dados e detecção de duplicatas

### ✅ Reconhecimento Facial

- Detecção e reconhecimento de rostos via webcam
- Threshold ajustável (padrão: 0.6) para controle de precisão
- Feedback visual em tempo real durante o reconhecimento
- Libera acesso automaticamente para usuários reconhecidos

### ✅ Controle de Acesso

- Registro automático de ENTRADA/SAÍDA baseado no último acesso
- Log completo em arquivo CSV com timestamp
- Registro de tentativas negadas para segurança

### ✅ Interface de Terminal

Menu interativo com as opções:

1. Cadastrar novo usuário
2. Validar acesso
3. Visualizar registros de acesso
4. Sair

## Estrutura do Projeto

```
catraca-virtual/
├── catraca_virtual.py          # Arquivo principal do sistema
├── requirements.txt            # Dependências do projeto
├── usuarios/                   # Diretório de usuários cadastrados
│   └── [CPF]/
│       ├── foto.jpg           # Foto do usuário
│       └── dados.json         # Dados cadastrais
├── acessos.csv                # Log de acessos
└── venv/                      # Ambiente virtual Python
```

## Instalação e Configuração

### 1. Pré-requisitos

- Python 3.8 ou superior
- Webcam funcional
- Sistema operacional: Windows, macOS ou Linux

### 2. Configuração do Ambiente

```bash
# Clone ou baixe o projeto
cd catraca-virtual

# Ative o ambiente virtual
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 3. Executar o Sistema

```bash
# Com o ambiente virtual ativado
python catraca_virtual.py
```

## Como Usar

### Primeiro Uso

1. Execute o programa
2. Escolha a opção "1 - Cadastrar novo usuário"
3. Preencha os dados solicitados (Nome, Equipe, CPF)
4. Posicione seu rosto na webcam e pressione 's' para salvar a foto
5. O sistema confirmará o cadastro

### Validação de Acesso

1. Escolha a opção "2 - Validar acesso"
2. Posicione o rosto na frente da webcam
3. O sistema reconhecerá automaticamente e liberará o acesso
4. Pressione 'q' para cancelar

### Visualizar Registros

1. Escolha a opção "3 - Visualizar registros de acesso"
2. Veja o histórico completo de acessos

## Especificações Técnicas

### Dependências Principais

- **OpenCV**: Captura de vídeo e processamento de imagens
- **face_recognition**: Biblioteca para reconhecimento facial
- **numpy**: Operações numéricas
- **json**: Armazenamento de dados dos usuários
- **csv**: Log de acessos

### Configurações

- **FACE_MATCH_THRESHOLD**: 0.6 (ajustável no código)
- **Resolução de processamento**: 1/4 da resolução original para otimização
- **Formato de armazenamento**: JSON para dados, JPG para fotos, CSV para logs

### Arquivos de Dados

- **dados.json**: `{"nome": "string", "equipe": "string", "cpf": "string"}`
- **acessos.csv**: Nome, Equipe, CPF, DataHora, Tipo, Status

## Funcionalidades de Segurança

- ✅ Validação de CPF (11 dígitos)
- ✅ Detecção de usuários duplicados
- ✅ Registro de tentativas negadas
- ✅ Verificação de face única no cadastro
- ✅ Log timestampado de todos os acessos

## Solução de Problemas

### Webcam não funciona

- Verifique se a webcam está conectada e funcionando
- Teste em outros aplicativos
- Reinicie o sistema se necessário

### Erro de importação face_recognition

```bash
# Instale setuptools se necessário
pip install setuptools
```

### Performance lenta

- O sistema processa em 1/4 da resolução para otimização
- Certifique-se de ter boa iluminação para melhor detecção

## Melhorias Futuras

- [ ] Interface gráfica (GUI)
- [ ] Banco de dados SQLite
- [ ] Controle de horários de acesso
- [ ] Relatórios mais detalhados
- [ ] Integração com sistemas externos
- [ ] Suporte a múltiplas câmeras

## Desenvolvido por

Sistema desenvolvido em Python para controle de acesso com reconhecimento facial.

---

**Nota**: Este sistema foi projetado para uso local e educacional. Para uso em produção, considere implementar medidas adicionais de segurança.

