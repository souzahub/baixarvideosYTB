# BaixaYoutube (Web)

App Flask para baixar vídeos do YouTube em MP4 com barra de progresso.
Downloads são temporários (apagados após o envio ao cliente).

## Recursos
- Formulário web (Flask) com barra de progresso em tempo real
- Conversão/merge com `ffmpeg`
- Downloads efêmeros (sem ocupar disco do servidor)
- Configurável por variáveis de ambiente

## Variáveis de ambiente
- `HOST` (default `0.0.0.0`)
- `PORT` (default `5000`)
- `BASE_URL` (opcional). Ex.: `https://uadezap-baixarvideoytb.xv2gsb.easypanel.host` ou `http://SEU_IP:5000`.
- `PUBLIC_PORT` (opcional). Se definido, monta automaticamente BASE_URL com `http://69.30.204.84:PORT`. Ex.: `8080`
- `DISABLE_CERT_VERIFY` = `1` para desativar verificação SSL (último recurso)
- `PROXY_URL` = `http://user:pass@proxy:3128` (ou `https://...`) se sua rede exigir proxy

## Deploy no EasyPanel (via Git)
1. Crie um repositório e envie estes arquivos:
   - `downloader.py`, `requirements.txt`, `Dockerfile`
   - A pasta `intalacao/ffmpeg/bin` é opcional no Docker (imagem instala ffmpeg)
2. No EasyPanel, crie app → Fonte: GitHub → Branch: `main` → Caminho de build: `/`
3. Tipo de build: Dockerfile
4. Variáveis de ambiente: defina `HOST=0.0.0.0` e `PORT=5000` (e as opcionais acima)
5. Porta do container: interna `5000`; exponha via HTTP/HTTPS do painel (80/443)
6. Opcional: adicione domínio e ative SSL (Let’s Encrypt)
7. Build & Deploy. Acesse `https://seu-dominio` (ou IP:porta do painel)

Exemplo:
HOST=0.0.0.0
PORT=5000
(Opcional) DISABLE_CERT_VERIFY = 1

## Rodar com Docker (local/servidor)
```bash
# Build
docker build -t baixa-youtube .

# Run (porta 5000)
docker run --rm -p 5000:5000 \
  -e HOST=0.0.0.0 -e PORT=5000 \
  -e DISABLE_CERT_VERIFY=0 \
  -e PROXY_URL= \
  baixa-youtube
```

## Windows (EXE, sem instalar Python)
1. No PowerShell, na pasta do projeto:
   ```powershell
   .\build_exe.bat
   ```
   O executável será criado em `dist\BaixaYoutube.exe`.
2. Para abrir firewall e servir na rede:
   ```powershell
   .\run_server.bat
   ```
3. Início automático no login (opcional):
   ```powershell
   .\install_service.bat
   ```
4. Acesse `http://SEU_IP:5000/`.

## Windows (Python)
```powershell
pip install -r requirements.txt
set HOST=0.0.0.0
set PORT=5000
python downloader.py
```

## Observações
- SSL: usamos `certifi`. Em redes com interceptação TLS, defina a CA corporativa ou, em último caso, `DISABLE_CERT_VERIFY=1`.
- Proxy: use `PROXY_URL` se necessário.
- Segurança: se publicar na internet, considere autenticação básica e limites de tamanho. Podemos adicionar isso facilmente.

## Licença
Uso interno/educacional. Verifique os termos de uso da plataforma de origem.
