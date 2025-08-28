# 🌐 Guia de Hospedagem - Catraca Virtual

Este guia mostra diferentes formas de hospedar o sistema de cadastro web para acesso contínuo.

## 🚀 Opções de Hospedagem

### 1. 🌍 ngrok - Túnel Público Temporário (Mais Rápido)

**Ideal para:** Testes rápidos e demonstrações

```bash
# Instalar ngrok
python3 deploy_cloud.py

# Ou manualmente:
# 1. Baixe ngrok: https://ngrok.com/download
# 2. Crie conta gratuita em: https://ngrok.com
# 3. Configure token: ngrok authtoken SEU_TOKEN
# 4. Execute: ngrok http 5000
```

**Vantagens:**

- ✅ Configuração em minutos
- ✅ URL pública imediata
- ✅ HTTPS automático

**Desvantagens:**

- ❌ URL muda a cada reinicialização
- ❌ Limitado a algumas horas (plano gratuito)

### 2. ☁️ Heroku - Hospedagem Gratuita Permanente

**Ideal para:** Uso contínuo e profissional

```bash
# 1. Instalar Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# 2. Criar arquivos de deploy
python3 deploy_cloud.py
# Escolha opção 4

# 3. Deploy
heroku login
heroku create seu-app-catraca
git init
git add .
git commit -m "Deploy inicial"
git push heroku main

# Sua URL será: https://seu-app-catraca.herokuapp.com
```

**Vantagens:**

- ✅ URL permanente e personalizada
- ✅ HTTPS automático
- ✅ Backups automáticos
- ✅ Escalabilidade automática

### 3. 🐳 Docker + Cloud Provider

**Ideal para:** Controle total e escalabilidade

```bash
# Build da imagem
docker build -t catraca-virtual .

# Executar localmente
docker-compose up -d

# Deploy em cloud providers:
# - Google Cloud Run
# - AWS ECS
# - Azure Container Instances
```

### 4. 🏠 Rede Local Permanente

**Ideal para:** Ambiente corporativo interno

```bash
# Configurar servidor sempre ativo
python3 deploy_cloud.py
# Escolha opção 2

# Acessível via: http://SEU_IP:5000
```

## 🔧 Configuração Detalhada

### Heroku (Recomendado)

1. **Preparar arquivos:**

   ```bash
   python3 deploy_cloud.py  # Opção 4
   ```

2. **Instalar Heroku CLI:**

   - macOS: `brew install heroku/brew/heroku`
   - Windows: Baixar de https://devcenter.heroku.com/articles/heroku-cli

3. **Deploy:**

   ```bash
   heroku login
   heroku create minha-catraca-virtual
   git init
   git add .
   git commit -m "Deploy inicial"
   git push heroku main
   ```

4. **Configurar variáveis (opcional):**
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=sua_chave_secreta
   ```

### Railway (Alternativa Moderna)

1. **Conectar GitHub:**

   - Acesse https://railway.app
   - Conecte seu repositório GitHub
   - Deploy automático a cada commit

2. **Configurar:**
   - Start Command: `python web_server.py`
   - Port: `5000`

### Google Cloud Run

1. **Build e Push:**

   ```bash
   gcloud builds submit --tag gcr.io/SEU_PROJECT/catraca-virtual
   ```

2. **Deploy:**
   ```bash
   gcloud run deploy --image gcr.io/SEU_PROJECT/catraca-virtual --platform managed
   ```

## 📱 URLs de Acesso

Após hospedagem, sua equipe poderá acessar:

- **Cadastro:** `https://sua-url.com/`
- **Status:** `https://sua-url.com/status`

## 🔒 Segurança

### Para Ambiente Corporativo:

1. **Adicionar autenticação:**

   ```python
   # No web_server.py, adicionar:
   @app.before_request
   def require_auth():
       # Implementar autenticação
   ```

2. **HTTPS obrigatório:**

   ```python
   @app.before_request
   def force_https():
       if not request.is_secure:
           return redirect(request.url.replace('http://', 'https://'))
   ```

3. **Limitar IPs:**
   ```python
   ALLOWED_IPS = ['192.168.1.0/24']  # Apenas rede interna
   ```

## 📊 Monitoramento

### Logs de Acesso:

```bash
# Heroku
heroku logs --tail

# Docker
docker-compose logs -f

# Local
tail -f logs/access.log
```

### Status da Aplicação:

- Acesse `/status` para ver estatísticas
- Monitor de usuários cadastrados
- Registros de acesso do dia

## 🆘 Troubleshooting

### Erro de Memória:

```bash
# Heroku - Aumentar dyno
heroku ps:scale web=1:standard-1x
```

### Erro de Dependências:

```bash
# Verificar requirements.txt
pip freeze > requirements.txt
```

### Banco de Dados:

```bash
# Backup
cp catraca_virtual.db backup_$(date +%Y%m%d).db

# Restaurar
cp backup_YYYYMMDD.db catraca_virtual.db
```

## 💡 Dicas Importantes

1. **Backup regular** do banco de dados
2. **Monitorar uso** para não exceder limites gratuitos
3. **Testar recuperação** em caso de falhas
4. **Documentar URLs** para a equipe
5. **Configurar notificações** de sistema offline

## 📞 Suporte

Para dúvidas sobre hospedagem:

1. Verifique logs de erro
2. Teste localmente primeiro
3. Consulte documentação do provedor
4. Use fóruns da comunidade

---

**Escolha a opção que melhor se adequa ao seu uso:**

- 🏃‍♂️ **Rápido:** ngrok
- 🏢 **Profissional:** Heroku
- 🔧 **Avançado:** Docker + Cloud
- 🏠 **Interno:** Rede local
