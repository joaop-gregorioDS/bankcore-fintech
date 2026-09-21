# BankCore 2.0 — Baseline pós-P5

**Data:** 2026-09-21  
**Branch de trabalho:** `p6/cicd-iac`  
**Tag local:** `bankcore-p5-observability`  
**Commit consolidado:** `cc962503ba222c472f600127967fa137c4dcb0df`  
**PR remoto:** #6 — P5 Observability  

## Marco

O P5 foi integrado à `main` com merge commit. A `main` local e `origin/main`
estão sincronizadas no commit acima, com working tree limpa.

O run final do GitHub Actions para a `main` foi o **run #17**, com **15/15 jobs
verdes**. O run incluiu os gates anteriores e o E2E consolidado de
observabilidade, concluído em 8m48s. Os avisos de depreciação do Node.js 20,
cache sem `go.sum` e migração futura do `ubuntu-latest` foram não bloqueantes.

## Capacidades congeladas

- logs estruturados e `request_id`/`correlation_id`;
- tracing distribuído HTTP e Kafka via OpenTelemetry;
- métricas Prometheus com cardinalidade controlada;
- quatro dashboards Grafana provisionados;
- regras Prometheus para falhas operacionais;
- E2E de fluxo financeiro e cenários de falha/recuperação;
- observabilidade fail-open: Collector, Prometheus e Grafana não são fonte da
  verdade nem dependência da integridade financeira;
- CI remoto cobrindo P0–P5.

## Limites da baseline

Esta baseline comprova o estado do repositório e dos ambientes descartáveis de
CI. Ela não comprova disponibilidade, TLS, firewall, volumes, secrets,
registry, topologia Kafka/Redis ou qualquer configuração da VPS. Nenhuma VPS,
produção remota ou secret real foi acessado.

O próximo passo é o P6-A — auditoria de deployment e infraestrutura. Nenhum
deploy ou alteração de infraestrutura remota está autorizado por esta
baseline.

