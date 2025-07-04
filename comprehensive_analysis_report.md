# ANÁLISE ESTATÍSTICA ABRANGENTE - E-COMMERCE BRASILEIRO
## Análise Exploratória Expandida por UF e Categoria de Produto

### METODOLOGIA E QUALIDADE DOS DADOS

#### 1. Avaliação da Qualidade dos Dados

Esta análise implementa controles rigorosos de qualidade para identificar e tratar vulnerabilidades que podem comprometer o entendimento estatístico:

**Volume de Dados Processados:**
- Registros iniciais de itens: 112,650
- Pedidos únicos finais: 95,127
- Taxa de aproveitamento: 84.4%

**Vulnerabilidades Identificadas e Tratadas:**
- Produtos sem categoria: 610
- Itens sem correspondência de produto: 0
- Pedidos não entregues removidos: -10,756

#### 2. Estratégia de Análise Adotada

**Distribuição Geográfica:**
- Estados com amostra significativa (≥100): 24/27
- Estados selecionados para análise detalhada: SP, RJ, MG, RS, PR, SC, BA, DF

**Distribuição por Categoria:**
- Categorias com amostra significativa (≥100): 51/71
- Categorias selecionadas: bed_bath_table, health_beauty, sports_leisure, computers_accessories, furniture_decor, housewares

**Combinações Viáveis Estado×Categoria:**
- Combinações com amostra mínima (≥30): 363/1349
- Tipo de análise recomendada: full_crossover

### ANÁLISE DA VARIÁVEL: Ticket Médio (R$)

**Tipo de Variável:** Continuous
**Metodologia:** Análise de distribuições contínuas com testes de normalidade

**Estatísticas Descritivas Gerais:**
- Média: 137.14
- Mediana: 86.00
- Desvio padrão: 208.93
- Mínimo: 0.85
- Máximo: 13440.00

**Análise por Estado (Top 5):**

- **SP** (N=39954): Média=125.23, DP=183.26
- **RJ** (N=12166): Média=142.74, DP=238.81
- **MG** (N=11187): Média=137.05, DP=202.82
- **RS** (N=5268): Média=136.64, DP=184.58
- **PR** (N=4855): Média=135.48, DP=198.60

---

### ANÁLISE DA VARIÁVEL: Razão do Frete

**Tipo de Variável:** Continuous
**Metodologia:** Análise de distribuições contínuas com testes de normalidade

**Estatísticas Descritivas Gerais:**
- Média: 0.29
- Mediana: 0.22
- Desvio padrão: 0.23
- Mínimo: 0.00
- Máximo: 1.00

**Análise por Estado (Top 5):**

- **SP** (N=39954): Média=0.25, DP=0.19
- **RJ** (N=12166): Média=0.30, DP=0.23
- **MG** (N=11187): Média=0.31, DP=0.23
- **RS** (N=5268): Média=0.32, DP=0.24
- **PR** (N=4855): Média=0.32, DP=0.24

---

### ANÁLISE DA VARIÁVEL: Quantidade de Itens

**Tipo de Variável:** Discrete
**Metodologia:** Distribuições discretas com análise de frequências

**Estatísticas Descritivas Gerais:**
- Total de observações: 95,127
- Valores únicos: 17
- Moda: 1
- Mediana: 1.00
- Média: 1.14
- Desvio padrão: 0.54

**Teste de Uniformidade (Qui-quadrado):**
- Estatística χ²: 1069977.9095
- P-valor: 0.0000
- Distribuição uniforme: Não (α = 0.05)

**Análise por Estado (Top 5):**

- **SP** (N=39954): Moda=1, Média=1.15
- **RJ** (N=12166): Moda=1, Média=1.14
- **MG** (N=11187): Moda=1, Média=1.14
- **RS** (N=5268): Moda=1, Média=1.15
- **PR** (N=4855): Moda=1, Média=1.15

---
