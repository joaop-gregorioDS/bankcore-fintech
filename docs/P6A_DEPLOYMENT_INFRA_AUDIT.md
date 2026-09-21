# P6-A — Deployment & Infrastructure Audit

**Data:** 2026-09-21  
**Branch:** `p6/cicd-iac`  
**Fonte local:** `cc962503ba222c472f600127967fa137c4dcb0df`  
**Tag de referência:** `bankcore-p5-observability`  
**Escopo:** somente leitura local; sem push, merge, deploy, secrets reais ou VPS.

## 1. Resultado executivo

O repositório possui uma base local/testável madura, mas ainda não possui uma
unidade de release pronta para produção. O `docker-compose.yml` é um runtime
production-like mínimo com PostgreSQL, Redis, Auth, Transactions, Risk, Nginx
e jobs de migration; Kafka, Audit Consumer, Outbox Publisher e a stack de
observabilidade entram somente por Compose overlays descartáveis.

O CI prova qualidade e builds, mas não publica imagens, não cria um release
manifest, não executa migrations em um ambiente de entrega, não faz rollout,
smoke pós-deploy ou rollback. Não há Terraform/OpenTofu, Ansible, workflow de
deploy ou configuração versionada da VPS no repositório.

Conclusão: o próximo trabalho deve separar explicitamente **artefato de
release**, **configuração/secrets**, **topologia de produção** e **mecanismo de
rollout** antes de qualquer acesso à VPS.

## 2. Inventário atual

### Runtime base

Arquivo principal: `docker-compose.yml`.

| Componente | Estado local observado | Persistência/exposição |
|---|---|---|
| PostgreSQL | Imagem `postgres:16.4-alpine3.20`, healthcheck `pg_isready` | volume `postgres_data`; sem porta publicada |
| Redis | `redis:7.4.1-alpine3.20`, AOF e `noeviction` | volume `redis_data`; sem porta publicada; usado pelo Auth |
| Auth | imagem construída localmente, non-root, readiness de banco | chave privada somente em mount read-only; sem porta publicada |
| Transactions | imagem construída localmente, non-root, readiness de banco | somente chave pública; sem porta publicada |
| Risk | ASP.NET Core, imagem runtime com digest, non-root, readiness de banco | somente chave pública; `expose: 8080` |
| Nginx | `nginxinc/nginx-unprivileged:1.27.1-alpine` | único serviço publicado; `${GATEWAY_PORT:-80}:8080` |
| Migrations | Auth/Transactions via Alembic e Risk via migrator EF em profile `migration` | execução manual; não é uma etapa automática de startup |

O network `bankcore_net` é bridge sem publicação dos serviços internos. O
Compose aplica `no-new-privileges`, remove todas as capabilities nos serviços
de aplicação e usa healthchecks básicos.

### Overlays e ambientes descartáveis

- `docker-compose.e2e.yml`: imagens locais para Auth, Transactions e Risk e
  runner E2E;
- `docker-compose.p3-e2e.yml`: Kafka KRaft single-node, Audit, Publisher,
  crash/recovery e E2E de eventos;
- `docker-compose.kafka-test.yml`: somente broker Kafka descartável;
- `docker-compose.p5-*.yml`: Collector, Prometheus, Grafana e alertas;
- `docker-compose.*-test.yml`: bancos, Kafka, Redis e runners isolados para
  testes.

Esses arquivos são adequados para laboratório/CI, mas não constituem ainda um
bundle production-like completo. Em particular, Kafka, Audit, Publisher,
Collector, Prometheus e Grafana não estão no Compose base.

### Dockerfiles e imagens

- Auth, Transactions, Audit e testes usam `python:3.12.8-slim-bookworm` por tag,
  sem digest;
- Risk fixa os stages SDK/runtime por digest SHA-256;
- PostgreSQL, Redis, Nginx, Kafka, Collector, Prometheus e Grafana usam tags
  versionadas, mas não digest no Compose;
- Auth/Transactions/Audit não definem nomes de imagem de release no Compose
  base; os jobs de migration referenciam nomes locais derivados do projeto;
- Risk possui `image: bankcore-fintech-audit-risk-service`, também sem registry
  ou tag de release;
- não existe convenção de tag por commit, digest de release, SBOM, assinatura ou
  política de retenção de imagens no repositório.

### Nginx e entrada

`infra/nginx/bankcore.conf` encaminha somente Auth e Transactions, bloqueia
docs/OpenAPI e endpoints internos/Risk, propaga request/correlation IDs e
mantém logs JSON. A configuração versionada escuta HTTP na porta 8080 do
container; TLS externo, DNS, firewall, certificados, rate limiting de borda e
proxy para Risk não estão definidos nem verificados.

### Bancos, migrations e dados

- Auth e Transactions mantêm históricos Alembic separados;
- Audit possui histórico Alembic próprio;
- Risk possui migration EF Core própria e um migrator separado;
- as aplicações abortam se o schema esperado não estiver migrado;
- `depends_on` aguarda saúde do PostgreSQL, mas não aguarda a conclusão das
  migrations;
- o fluxo documentado exige executar jobs de migration manualmente antes de
  `docker compose up`;
- o P1-D valida backup/restore descartável separado para **Auth e
  Transactions**;
- Risk e Audit não aparecem no fluxo de backup/restore validado pelo P1-D;
- Redis é reconstruível e corretamente não é fonte da verdade financeira;
- Kafka possui persistência em volume nos cenários de teste, mas a topologia
  de produção, retenção, replicação e restauração não existem no bundle base.

### Secrets e configuração

`.env.example` documenta nomes de configuração e `.env` é ignorado pelo Git.
O Compose exige, entre outros, senha PostgreSQL, `JWT_ACTIVE_KID`, token
interno e segredo HMAC do rate limit. A chave privada JWT é montada do host
somente no Auth; os demais serviços recebem chaves públicas.

Limitações atuais:

- não há secret manager, KMS/Vault, rotação automatizada ou distribuição
  versionada de secrets;
- `AUTH_SERVICE_TOKEN` continua sendo um segredo compartilhado por configuração;
- não há política de secret injection específica para produção;
- Redis local não configura ACL, senha ou TLS; o ADR registra isso como uma
  decisão dependente do ambiente externo;
- os mounts de chaves dependem de caminhos no host e não de um artefato de
  release autocontido.

### GitHub Actions

`.github/workflows/ci.yml` dispara em PR, push para `main` e manualmente, com
cancelamento de execuções antigas. O CI atual cobre:

- quality gates, secret scan e dependency audits;
- build/test/EF e integração PostgreSQL do Risk;
- E2E Auth → Risk;
- Kafka smoke, outbox, Audit, retry/DLQ e recovery;
- Redis resilience;
- tracing, metrics, Grafana, alertas e E2E de observabilidade.

Não há no workflow atual:

- login/push para registry;
- criação de tags ou release manifest;
- SBOM, assinatura/proveniência ou scan de vulnerabilidade de imagens;
- migration pre-deploy com backup e aprovação;
- deploy SSH/API, rollout, smoke pós-deploy ou rollback;
- environment protegido ou secrets de produção.

## 3. Validações executadas

Foram usados somente placeholders efêmeros em processo, sem registrar valores
sensíveis. Sem o `.env`, `docker compose config` aborta corretamente porque
variáveis obrigatórias não estão definidas. Com placeholders sintéticos, os
quatro bundles abaixo passaram na validação de configuração:

1. `docker-compose.yml`;
2. base + `docker-compose.e2e.yml`;
3. base + E2E + `docker-compose.p3-e2e.yml`;
4. base + P3 E2E + overlays P5 de tracing, metrics, Grafana e alertas.

Nenhum container, volume, rede ou serviço remoto foi iniciado durante a
auditoria.

## 4. Classificação de gaps

| Área | Classificação | Evidência |
|---|---|---|
| CI/testes P0–P5 | **Comprovado local/remoto** | run #17 com 15/15 jobs verdes |
| Compose base e overlays | **Comprovado localmente** | `docker compose config` com placeholders sintéticos |
| Non-root, healthchecks e rede interna | **Mitigado localmente** | Dockerfiles e Compose base |
| Migrations | **Parcial** | presentes, mas execução é manual e sem gate de release |
| Imagens versionadas | **Pendente** | tags locais/default; sem registry/digest uniforme |
| Backup de Risk/Audit | **Pendente** | P1-D cobre Auth/Transactions |
| Secrets de produção | **Pendente** | `.env`/mounts; sem secret manager ou rotação |
| Kafka/Audit/Publisher em produção | **Não verificado** | somente overlays/ambientes descartáveis |
| TLS, DNS, firewall e VPS | **Não verificado por escopo** | nenhum acesso remoto realizado |
| Rollout/rollback | **Ausente** | nenhum workflow ou runbook encontrado |
| IaC | **Ausente** | nenhum Terraform/OpenTofu/Ansible/Kubernetes encontrado |
| Registry, SBOM e assinatura | **Ausente** | nenhum estágio correspondente no CI |

## 5. Arquitetura-alvo proposta

Sem escolher ainda o provedor ou ferramenta definitiva, o desenho recomendado
é separar responsabilidades em quatro camadas:

```text
PR / main
  ↓
CI: testes + migrations em banco vazio + security gates
  ↓
Build reproduzível: imagens por commit + SBOM + scan + assinatura
  ↓
Registry privado/público controlado
  ↓
Release manifest imutável
  ↓
Deploy em VPS: backup → migrations compatíveis → rollout → smoke/readiness
  ↓                         ↘ falha → rollback da aplicação + diagnóstico
Nginx → Auth → Transactions → Risk → Ledger/Outbox → Kafka → Audit
                         ↘ Redis (rate limit) e observabilidade best-effort
```

Para uma única VPS, a opção mínima a avaliar é um Compose de produção separado
do Compose de desenvolvimento/teste, com:

- nomes de imagem completos e tags por commit, nunca `latest`;
- arquivo de release que fixa imagens por digest;
- migrations como jobs explícitos e idempotentes antes do rollout;
- backup validado antes de migrations destrutivas ou incompatíveis;
- health/readiness para todos os processos long-running, incluindo Publisher e
  Audit Consumer;
- política de rollback documentada e smoke test após cada release;
- secrets injetados pelo ambiente de execução, nunca pela imagem ou Git;
- somente Nginx publicado externamente, com TLS e firewall definidos fora do
  repositório de aplicação;
- volumes PostgreSQL/Kafka/Redis explicitamente classificados por criticidade;
- observabilidade desacoplada do caminho financeiro.

IaC deve provisionar host, firewall, DNS, volumes e pré-requisitos. A
configuração da aplicação e o rollout devem permanecer separados da
provisioning layer. A escolha entre OpenTofu/Terraform e Ansible só deve ser
feita depois de confirmar o que o provedor da VPS expõe e qual parte pode ser
reproduzida sem acesso privilegiado.

## 6. Backlog P6 sugerido

1. **P6-A — esta auditoria:** congelar escopo e riscos, sem runtime novo.
2. **P6-B — Release packaging:** nomes de imagem, tags por SHA, digests e
   manifest de release.
3. **P6-C — Production configuration:** Compose de produção separado, contrato
   de environment/secrets e limites operacionais.
4. **P6-D — Migration and data safety:** jobs de migration, backup/restore para
   Risk/Audit e política de compatibilidade/rollback.
5. **P6-E — Deployment mechanism:** rollout em ambiente controlado, smoke,
   recovery e rollback sem VPS real inicialmente.
6. **P6-F — IaC:** provisionamento mínimo reproduzível, após escolha da ferramenta
   e do escopo do provedor.
7. **P6-G — CI/CD completion:** registry, SBOM, image scan, assinatura,
   environment protegido e deploy somente após CI verde.

## 7. Primeira mudança recomendada — ainda não aplicada

Antes de qualquer push ou acesso remoto, a primeira mudança deveria ser um
artefato local de release: um `docker-compose.production.yml` (ou bundle
equivalente) sem secrets, acompanhado de um release manifest e validações
estáticas. Ele deve tornar explícitos os serviços que pertencem à produção,
suas imagens imutáveis, ordem de migration/readiness e limites de exposição.

Essa mudança ainda não foi aplicada. O próximo passo depende da revisão desta
baseline e de uma decisão explícita sobre registry, cobertura de backup e
topologia de produção.

