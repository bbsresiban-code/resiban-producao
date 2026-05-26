# Sistema de Gestão de Produção — Resiban (Grupo CRB)

## Contexto
A Resiban é uma recicladora de PEBD (filme flexível PCR) em BH. Toda a operação — OPs, controle de produção, estoque, romaneios — é feita em papel e depois digitada manualmente no Excel. Isso gera erros de lançamento (ex: códigos sem zero, grades errados), retrabalho e falta de visibilidade. O objetivo é criar um app web acessível pelo celular para 2-5 operadores, com dashboard operacional em tempo real.

**Contexto ERP:** Migração do SAGI para Sankhya em andamento (fiscal/financeiro em ~30 dias, produção em meses). A balança será integrada ao Sankhya. Nosso sistema será o braço mobile do chão de fábrica, complementar ao ERP — não concorrente. Construído de forma modular para evoluir junto com o Sankhya.

## Tecnologia
- **Streamlit** (Python) — deploy gratuito no Streamlit Cloud
- **Google Sheets** como banco de dados (gratuito, sem expiração por inatividade, dados visíveis direto na planilha)
- **Plotly** para gráficos no dashboard
- **openpyxl** para exportar relatórios em Excel (.xlsx)
- Interface 100% em Português (BR), mobile-friendly

---

## Fluxo Real da Operação (que o sistema deve refletir)

```
COMPRA MP → RECEBIMENTO (pesagem, NF, qualidade A/B/C)
    │
    ▼
OP LAVAÇÃO (gerente Fábio cria)
    │── Turnos A/B/C registram fardo a fardo (fardinhos + fardões)
    │── Registram perdas (lixo, papelão, plástico colorido)
    │── Registram paradas (quebra, corretiva, preventiva)
    │
    ▼
MATERIAL LAVADO (estoque intermediário no chão)
    │
    ▼
OP EXTRUSÃO (gerente Fábio cria — independente da OP Lavação)
    │── Turnos A/B/C registram lote a lote (hora, peso, lote, OP)
    │── Registram manutenção (troca telas, limpeza gaveta, troca facas)
    │── Bigbag recebe LOTE (serial) + PESO na produção
    │
    ▼
ÁREA QUALIDADE (todos os bags vão pra cá)
    │── Lab analisa: MFI, teor cinzas, densidade, umidade, filme
    │── Lote recebe GRADE + COR
    │
    ▼
ESTOQUE (com posicionamento físico: A2, A3, A12, EXPED., etc.)
    │
    ▼
VENDA (João Paulo negocia → WhatsApp) → SEPARAÇÃO → ROMANEIO → NF → EXPEDIÇÃO (maioria CIF)
```

---

## Estrutura de Arquivos

```
resiban-producao/
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml          # Credenciais Google (NÃO vai pro git)
├── app.py                    # Navegação e conexão Google Sheets
├── pages/
│   ├── 1_dashboard.py        # Painel com KPIs e gráficos
│   ├── 2_op_lavacao.py       # Criar/consultar OP de lavação
│   ├── 3_producao_lavacao.py # Lançamento diário por turno
│   ├── 4_op_extrusao.py      # Criar/consultar OP de extrusão
│   ├── 5_producao_extrusao.py# Lançamento diário por turno
│   ├── 6_qualidade.py        # Lab: atribuir grade e cor ao lote
│   ├── 7_estoque.py          # Visualizar estoque + posicionamento
│   ├── 8_romaneio.py         # Montar romaneio de carregamento
│   └── 9_exportar.py         # Download de relatórios em Excel
├── utils/
│   ├── __init__.py
│   ├── database.py           # CRUD Google Sheets
│   ├── serial_code.py        # Geração automática do código serial
│   ├── validators.py         # Validações
│   └── formatters.py         # Formatação BR
├── requirements.txt
└── .gitignore
```

---

## Modelo de Dados (Google Sheets — 1 planilha, múltiplas abas)

### Aba `op_lavacao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID único |
| numero_op | string | Nº da OP |
| data | date | Data de criação |
| responsavel | string | Quem criou (gerente) |
| cliente | string | Cliente destino |
| volume_ton | float | Volume a produzir (ton) |
| produto | string | Produto alvo |
| indice_fluidez | string | MFI alvo |
| status | string | aberta / fechada |
| observacao | string | Obs |
| created_at | datetime | Timestamp |

### Aba `op_lavacao_nfs`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| op_lavacao_id | string | FK para op_lavacao |
| nf_apara | string | Nº NF da apara |
| quant_fardos | int | Quantidade de fardos |
| peso_kg | float | Peso |
| obs | string | Observação |

### Aba `producao_lavacao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| data | date | Data do registro |
| turno | string | A, B ou C |
| numero_op | string | Nº da OP em produção |
| tipo_fardo | string | fardinho ou fardão |
| nf | string | NF de origem |
| quantidade | int | Qtd de fardos |
| peso_kg | float | Peso |
| perda_lixo_kg | float | Perda: lixo |
| perda_papelao_kg | float | Perda: papelão |
| perda_plastico_colorido_kg | float | Perda: plástico colorido |
| perda_total_kg | float | Soma perdas |
| registrado_por | string | Operador |
| created_at | datetime | Timestamp |

### Aba `paradas_lavacao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| data | date | Data |
| turno | string | A, B ou C |
| tipo_parada | string | quebra / corretiva / preventiva |
| hora_inicio | time | Início da parada |
| hora_fim | time | Fim da parada |
| duracao_min | float | Calculado |
| observacao | string | Obs |
| created_at | datetime | Timestamp |

### Aba `op_extrusao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| numero_op | string | Nº OP (prefixo A=canela, B=serviço, C=reticulado) |
| data | date | Data criação |
| responsavel | string | Gerente |
| cliente | string | Cliente |
| volume_ton | float | Volume a produzir |
| produto | string | Produto |
| maquina | string | Extrusora A ou B |
| data_inicio | date | Início produção |
| data_final | date | Fim produção |
| coordenador | string | Coordenador |
| producao_final_kg | float | Fechamento: total produzido |
| perda_percentual | float | Fechamento: % perda |
| status | string | aberta / fechada |
| observacao | string | Obs |
| created_at | datetime | Timestamp |

### Aba `producao_extrusao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| data | date | Data |
| turno | string | A, B ou C |
| hora | time | Hora do registro |
| numero_op | string | Nº OP |
| codigo_lote | string | Serial: TT-MM-AA-SSS-X (auto) |
| tipo | string | 01, 02 ou 04 |
| tipo_descricao | string | Próprio / Serviço / Revenda |
| extrusora | string | A ou B |
| peso_kg | float | Peso do bigbag |
| mes | int | Mês |
| ano | int | Ano (2 dígitos) |
| sequencial | int | Nº sequencial |
| status | string | em_analise / disponivel / carregado |
| observacao_lote | string | Obs |
| registrado_por | string | Operador |
| created_at | datetime | Timestamp |

### Aba `manutencao_extrusao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| data | date | Data |
| turno | string | A, B ou C |
| troca_telas | string | Registro da troca |
| limpeza_gaveta | string | Registro da limpeza |
| troca_facas | string | Registro da troca |
| observacao | string | Obs |
| created_at | datetime | Timestamp |

### Aba `qualidade`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| codigo_lote | string | FK para producao_extrusao |
| mfi | float | Índice de fluidez |
| teor_cinzas | float | % cinzas |
| densidade | float | g/cm³ |
| umidade | float | % umidade |
| teste_filme | string | ok / anomalia |
| grade | string | RESI01C, RESI02CI, RESI03CR, RESI04CS, RESI05CO, RESI06S |
| cor | string | C1-C3, M1-M3, EM1-EM3, E1-E3 |
| local_estoque | string | Posição física (A2, A3, A12, EXPED.) |
| analista | string | Quem analisou |
| data_analise | date | Data da análise |
| observacao | string | Obs |
| created_at | datetime | Timestamp |

### Aba `romaneio`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| data | date | Data carregamento |
| numero_pedido | string | Nº do pedido |
| cliente | string | Cliente |
| transportadora | string | Transportadora |
| placa_veiculo | string | Placa |
| motorista | string | Nome do motorista |
| responsavel_carregamento | string | Quem carregou |
| nf_saida | string | Nº NF emitida |
| codigo_produto_nf | string | Código produto na NF |
| peso_total_kg | float | Peso total |
| qtd_lotes | int | Quantidade de lotes |
| serial | string | Serial do romaneio |
| registrado_por | string | Quem registrou |
| created_at | datetime | Timestamp |

### Aba `romaneio_itens`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | UUID | ID |
| romaneio_id | string | FK para romaneio |
| codigo_lote | string | FK para producao_extrusao |
| produto | string | Grade + Cor (ex: RESI01C - EM3) |
| peso_kg | float | Peso do lote |

---

## Telas do Sistema

### 1. Dashboard
**KPIs (cards):**
- Fardos processados no mês (kg) — lavação
- Bigbags produzidos (qtd + kg) — extrusão
- Lotes em análise (qtd) — qualidade
- Lotes disponíveis em estoque (qtd + kg)
- Lotes expedidos no mês (qtd + kg)
- % perda média na lavação
- Tempo de parada no mês (horas)

**Gráficos (Plotly):**
- Produção mensal: lavação entrada vs extrusão saída (6 meses)
- Composição de perdas (pizza): lixo vs papelão vs colorido
- Extrusora A vs B: produção comparada
- Estoque por grade e cor
- Paradas por tipo (quebra/corretiva/preventiva)

**Filtros:** período, extrusora, turno

### 2. OP Lavação
- **Criar OP:** Nº OP, data, responsável, cliente, volume (ton), produto, índice fluidez
- **Adicionar NFs:** tabela com Nº NF apara, quant. fardos, peso, obs
- **Consultar OPs:** lista com status (aberta/fechada), filtro por período

### 3. Produção Lavação (lançamento diário)
- **Selecionar:** data, turno (A/B/C), Nº OP ativa
- **Lançar fardinhos:** NF, quantidade, peso
- **Lançar fardões:** NF, quantidade, peso
- **Lançar perdas:** lixo (kg), papelão (kg), plástico colorido (kg)
- **Registrar parada:** tipo (quebra/corretiva/preventiva), hora início, hora fim, observação
- **Histórico:** filtro por data, turno, OP

### 4. OP Extrusão
- **Criar OP:** Nº OP (com prefixo A/B/C), data, responsável, cliente, volume, produto, máquina, coordenador
- **Fechamento de OP:** produção final (kg), perda (%), lista de lotes produzidos
- **Consultar OPs:** lista com status, filtro por período

### 5. Produção Extrusão (lançamento diário)
- **Selecionar:** data, turno (A/B/C), Nº OP ativa, extrusora (A/B)
- **Registrar bigbag:** tipo (01/02/04), peso → **código de lote gerado automaticamente**
- **Preview do lote** antes de confirmar (ex: "01-05-26-???-B")
- **Registrar manutenção (verso):** troca telas, limpeza gaveta, troca facas, obs
- **Histórico:** duas colunas (ext A e ext B), filtro por data/turno/OP
- Lote criado com status `em_analise`

### 6. Qualidade (Lab)
- **Lista de lotes em análise** (status `em_analise`)
- **Formulário por lote:** MFI, teor cinzas, densidade, umidade, teste filme
- **Atribuir:** grade (selectbox com 6 opções) + cor (selectbox C1-E3)
- **Definir posição:** local no estoque (A2, A3, A12, EXPED., etc.)
- **Ao salvar:** status do lote muda para `disponivel`
- **Histórico de análises**

### 7. Estoque
- **Tabela de lotes disponíveis** com: lote, data produção, grade, cor, peso, local, dias em estoque
- **Filtros:** grade, cor, extrusora, período
- **Totalizadores:** qtd lotes, peso total, por grade
- **Mapa de posições:** visualização dos locais físicos

### 8. Romaneio
- **Criar romaneio:** data, nº pedido, cliente, transportadora, placa, motorista, responsável
- **Selecionar lotes:** tabela com checkbox dos lotes `disponivel`, filtro por grade/cor
- **Totalizador:** qtd lotes + peso total
- **Ao confirmar:** grava romaneio + itens, atualiza status dos lotes para `carregado`
- **Campos de fechamento:** Nº NF, código produto NF, serial
- **Histórico:** lista de romaneios, expandível com detalhes

### 9. Exportar
- Seletor de módulo
- Seletor de período
- Gera .xlsx formatado igual ao modelo atual (familiaridade)
- Download direto

---

## Lógica do Código Serial (Extrusão)

Formato: `TT-MM-AA-SSS-X`
- **TT:** tipo com zero (01=próprio, 02=serviço/terceiros, 04=revenda)
- **MM:** mês (01-12)
- **AA:** ano (25, 26...)
- **SSS:** sequencial no mês, auto-incremento por tipo+mês+ano+extrusora
- **X:** extrusora (A ou B)

Geração: ao submeter, lê aba `producao_extrusao` sem cache → filtra tipo+mês+ano+extrusora → próximo sequencial = max + 1 → gera código → verifica unicidade.

---

## Controle de Status do Lote

```
em_analise → disponivel → carregado
   (extrusão)    (após lab)    (após romaneio)
```

Estoque = lotes com status `disponivel`. Não existe tabela separada de estoque.

---

## Ordem de Implementação

### Fase 1 — Fundação
1. Criar repo GitHub, estrutura de pastas, `.gitignore`, `requirements.txt`
2. Configurar Google Cloud (service account + Sheets API)
3. Criar planilha Google Sheets com todas as abas e cabeçalhos
4. Implementar `utils/database.py` (read, append, update)
5. Implementar `utils/serial_code.py`
6. Implementar `app.py` com navegação
7. Testar conexão local

### Fase 2 — Lavação
8. `pages/2_op_lavacao.py` (criar + consultar OPs)
9. `pages/3_producao_lavacao.py` (lançamento por turno + paradas)

### Fase 3 — Extrusão
10. `pages/4_op_extrusao.py` (criar + consultar + fechar OPs)
11. `pages/5_producao_extrusao.py` (lançamento + serial automático + manutenção)

### Fase 4 — Qualidade e Estoque
12. `pages/6_qualidade.py` (análise lab + atribuir grade/cor/local)
13. `pages/7_estoque.py` (visualização + filtros)

### Fase 5 — Expedição
14. `pages/8_romaneio.py` (montar + selecionar lotes + fechar)

### Fase 6 — Dashboard e Exportação
15. `pages/1_dashboard.py` (KPIs + gráficos)
16. `pages/9_exportar.py` (download Excel)

### Fase 7 — Deploy
17. Deploy Streamlit Cloud + configurar secrets
18. Testar no celular
19. Compartilhar URL com equipe

---

## Verificação / Como Testar
1. `streamlit run app.py` local
2. Criar OP de lavação → verificar no Google Sheets
3. Lançar produção lavação (fardinhos + fardões + perdas + parada) → verificar
4. Criar OP extrusão → lançar bigbags → verificar código serial automático
5. No módulo qualidade, atribuir grade + cor a um lote → verificar status mudou para `disponivel`
6. No estoque, confirmar que lote aparece com posição
7. Criar romaneio selecionando lotes → verificar status mudou para `carregado`
8. Dashboard: conferir KPIs e gráficos com dados registrados
9. Exportar Excel e conferir formatação
10. Testar tudo no celular (Chrome DevTools + dispositivo real)

---

## Melhorias Futuras (V2+)
- Autenticação simples (senha por perfil: gerente, coordenador, operador)
- Módulo de recebimento de MP (pesagem, NF, qualidade A/B/C)
- QR code nos lotes para etiquetas nos bigbags
- Cadastro master de clientes/transportadoras (evitar digitação repetida)
- Módulo de aprovação de NFs (substituir WhatsApp do Fábio com centro de custos)
- Integração com Sankhya via API
- Notificações WhatsApp ao criar romaneio
