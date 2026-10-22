# Publicação — API na Oracle Cloud, front na Vercel

Decisão e alternativas: [ADR-015](../docs/backend/ADR-015-publicacao-oracle-vercel.md).

```
navegador ──► Vercel (front estático)
         └──► https://<API_DOMINIO> ──► Caddy (HTTPS) ──► API (Docker) ──► Neon (São Paulo)
                  máquina Oracle Always Free, região São Paulo
```

| Arquivo | Para quê |
| --- | --- |
| `../ia-predictor/Dockerfile` | imagem da API (Python 3.14, ARM ou x86) |
| `docker-compose.yml` | API + Caddy |
| `Caddyfile` | HTTPS automático e proxy para a API |
| `.env.example` | modelo do `deploy/.env` do servidor (segredos — nunca versionar) |
| `atualizar.sh` | puxa a `main` e reconstrói a API |
| `../app-react/vercel.json` | rotas do React no build da Vercel |

---

## 1. Criar a máquina na Oracle Cloud

1. Crie a conta em <https://signup.cloud.oracle.com> e escolha a região
   **Brazil East (São Paulo)**. A região escolhida no cadastro é definitiva: os recursos
   Always Free só existem nela.
2. *Compute → Instances → Create instance*:
   - **Image**: Canonical Ubuntu 24.04 (a versão comum, não a "Minimal").
   - **Shape**: *Ampere* → `VM.Standard.A1.Flex`, **4 OCPUs e 24 GB** (o limite do
     Always Free).
   - **Networking**: deixe criar a VCN nova com sub-rede pública e marque
     *Assign a public IPv4 address*.
   - **SSH keys**: *Generate a key pair for me* e baixe a chave privada (`.key`).
   - Se aparecer *Out of capacity*, tente outro *Availability domain* ou mais tarde.
3. Anote o **IP público** da máquina.
4. *Networking → Virtual cloud networks →* (a VCN criada) *→ Security Lists → Default* →
   *Add Ingress Rules*: origem `0.0.0.0/0`, TCP, portas de destino **80** e depois **443**.

## 2. Endereço com HTTPS (DuckDNS, grátis)

1. Entre em <https://www.duckdns.org> (login com GitHub ou Google).
2. Crie um subdomínio, ex.: `verdeperto-api` → `verdeperto-api.duckdns.org`.
3. Em *current ip*, coloque o IP público da máquina e clique em *update ip*.

## 3. Preparar a máquina

No seu computador (PowerShell ou Git Bash), com a chave baixada:

```bash
ssh -i caminho/da/chave.key ubuntu@<IP_PUBLICO>
```

Já dentro da máquina:

```bash
# Docker (pacotes do próprio Ubuntu)
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu && newgrp docker

# A imagem Ubuntu da Oracle bloqueia as portas no firewall da própria máquina,
# além da Security List do passo 1.4
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 4. Baixar o código (repositório privado)

O repositório é privado. Crie uma chave de leitura só para o servidor:

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub
```

Cole a chave pública no GitHub em *Settings → Deploy keys → Add deploy key* do
repositório (só leitura; quem tem acesso de admin do repositório faz isso). Depois:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/github_deploy
EOF
git clone git@github.com:FelipeGA02/TCC---Inventory-Forecasting.git ~/app
```

## 5. Configurar e subir a API

```bash
cd ~/app/deploy
cp .env.example .env
nano .env
```

Preencha com os mesmos valores do `ia-predictor/.env` local (`DATABASE_URL`,
`JWT_SECRET_KEY`, senhas), mais `API_DOMINIO` (passo 2) e `CORS_ORIGINS` (passo 6; dá
para subir agora com `[]` e completar depois). Então:

```bash
chmod 600 .env
docker compose up -d --build      # o primeiro build leva alguns minutos
docker compose logs -f api        # espere "Application startup complete", Ctrl+C para sair
curl https://<API_DOMINIO>/health # {"status":"ok",...}
```

O Caddy pede o certificado na primeira requisição; se o `curl` falhar no primeiro
segundo, tente de novo.

## 6. Publicar o front na Vercel

1. Em <https://vercel.com>, *Add New → Project* e importe o repositório do GitHub.
2. **Root Directory**: `app-react`. O resto (Vite, `npm run build`, `dist`) é detectado
   sozinho.
3. *Environment Variables*: `VITE_API_URL` = `https://<API_DOMINIO>`.
4. *Deploy*. Anote o endereço (ex.: `https://verde-perto.vercel.app`).
5. No servidor, coloque esse endereço no `deploy/.env` e reinicie a API:

   ```bash
   # deploy/.env
   CORS_ORIGINS=["https://verde-perto.vercel.app"]
   ```

   ```bash
   docker compose up -d
   ```

## 7. Atualizar depois de um merge na `main`

- **Front**: a Vercel publica sozinha a cada push na `main` (e cria uma prévia para cada
  PR).
- **API**: no servidor, `~/app/deploy/atualizar.sh`. Um treino em andamento é
  interrompido pelo restart. Se havia planilha nova, o treino de segunda (ou o botão
  "Atualizar os modelos") refaz.

## Problemas comuns

| Sintoma | Causa provável |
| --- | --- |
| `curl` não conecta | portas 80/443 fechadas: confira a Security List (1.4) **e** o `iptables` (3) |
| Erro de certificado | o DuckDNS não aponta para o IP da máquina, ou a porta 80 está fechada |
| Front abre, mas o login falha com erro de rede | `CORS_ORIGINS` sem o endereço exato da Vercel (com `https://`, sem `/` no fim) |
| API não sobe, erro de validação nos logs | valor em formato errado no `deploy/.env` (ex.: `CORS_ORIGINS` precisa ser uma lista JSON). Variável com nome errado é ignorada: confira a grafia |
| Treino morre no meio | memória: baixe `TRAINING_WORKERS` no `deploy/.env` |
