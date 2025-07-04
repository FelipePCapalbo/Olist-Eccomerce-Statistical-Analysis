# README – BRAZILIAN ECCOMERCE STATISTICAL ANALYSIS  
### Seminário 1 – Definição do Tema e Estrutura Inicial  
*(foco exclusivo na variável-resposta **ticket médio**)*  

---

## 1 · Tema de Pesquisa  
> **“Como variáveis temporais, socioeconômicas e de produto influenciam o ticket médio no e-commerce brasileiro?”**  

---

## 2 · Variáveis Envolvidas  

| Índice | Variável (`col_name` ou derivação)                       | Tipo/Natureza        | Observações / Como obter                                |
|-------:|---------------------------------------------------------|----------------------|---------------------------------------------------------|
| **y1** | **Ticket médio** (`order_ticket`)                       | Contínua (R$)        | Σ `price` por `order_id` (`olist_order_items_dataset`)  |
| x1     | Faixa horária 3 h (`time_slot`)                         | Categórica nominal   | 0 (00-02h) … 7 (21-23h)                                 |
| x2     | UF (`state`)                                            | Categórica nominal   | 27 estados (Tabela `customers`)                         |
| x3     | Capital × Interior (`urban_class`)                      | Binária              | Derivada de CEP × lista de capitais IBGE                |
| x4     | Renda per capita – quintis 1-5 (`income_level`)         | Ordinal              | Mapear UF → 5 níveis (IBGE/IPEA)                        |
| x5     | Categoria do produto (`product_cat`)                    | Categórica nominal   | Item de maior valor em cada pedido                      |
| x6     | Quantidade de itens (`n_items`)                         | Discreta             | `count(order_item_id)`                                  |
| x7     | Tipo de pagamento (`payment_type`)                      | Categórica nominal   | Cartão, boleto, voucher… (`order_payments`)             |
| x8     | **Índice de dia útil** (`busday_idx`)                   | Discreta             | 1º, 2º, … dia útil do mês                               |
| x9     | **Janela pós-salário** (`after_salary`)                 | Binária              | 1 ⇒ pedido entre 5º e 9º dia útil                       |
| x10    | Evento/promomoção (`calendar_event`)                    | Categórica nominal   | Black Friday, Dia Mães…                                 |
| x11    | **Dias até evento** (`days_to_event`)                   | Contínua/Discreta    | ∈ [−30 … +30]; 0 = dia do evento                        |
| x12    | **Share frete** (`freight_ratio`)                       | Contínua [0-1]       | `freight_value` / `order_ticket`                        |

---

## 3 · Problemas / Questões a Investigar  

1. **Elasticidade renda × categoria**  
   - *Como a distribuição relativa do ticket médio por categoria varia entre as cinco faixas de renda?*  
   - Ex.: “beleza_saude” mantém ticket alto mesmo em faixas de baixa renda?  

2. **Elasticidade estadual**  
   - A relação renda × ticket médio se mantém uniforme quando analisada por estado?  

3. **Efeito pós-salário**  
   - O ticket médio cresce nos quatro dias úteis após o 5º dia útil do mês?  

4. **Faixa horária**  
   - Qual faixa de 3 h exibe maior ticket médio e como isso difere entre capitais e interior?  

5. **Frete como barreira**  
   - A razão frete / ticket médio é maior no interior?  
   - Existe ponto de inflexão onde o aumento do frete reduz o ticket total?  

6. **Bundle vs. Unit Purchase**  
   - Há economia de escala: pedidos com >3 itens apresentam ticket médio **por item** menor?  

7. **Calendário & eventos**  
   - Quais categorias explodem perto de cada data comemorativa?  
   - *Dias-distância* ao evento com maior frequência de compra/ticket médio (pico: −3, 0 ou +1 dia?).  

---

## “Pré-DOE” – Fatorial Completo & Tamanho da Base  

### 1 · Inventário de Variáveis

| Sigla | Variável                              | Tipo | # Níveis (se ≠ contínua) |
|:----:|----------------------------------------|------|--------------------------|
| **y1** | Ticket médio (order_ticket)         | Contínua | — |
| x1 | Faixa horária 3 h (time_slot)          | Categórica | **8** |
| x2 | UF (state)                             | Categórica | **27** |
| x3 | Capital × Interior (urban_class)       | Categórica | **2** |
| x4 | Renda per capita (income_level)        | Ordinal | **5** |
| x5 | Categoria do produto (product_cat)     | Categórica | **73** |
| x6 | Tipo de pagamento (payment_type)       | Categórica | **4** |
| x7 | Janela pós-salário (after_salary)      | Categórica | **2** |
| x8 | Quantidade de itens (n_items)          | Contínua | — |
| x9 | Dia útil do mês (busday_idx)           | Contínua | — |
| x10| Dias até evento (days_to_event)        | Contínua | — |
| x11| Razão frete/ticket (freight_ratio)     | Contínua | — |

> **Somente variáveis categóricas/ordinais entram no cálculo do fatorial completo.**  
> Contínuas servirão como covariáveis na análise posterior.

---


### 2 · Estratégia de Redução para Permitir 5 Réplicas  

Para viabilizar uma réplica mínima de **5 por célula**, é necessário limitar a complexidade combinatória do fatorial completo. Mantendo as **27 UFs**, propomos um **filtro nas variáveis categóricas** com muitos níveis. A principal candidata é `product_cat` (com 73 níveis), pois domina o espaço amostral.

#### Etapas do Filtro:

1. **Agrupamento por popularidade**:  
   Selecionar as **k categorias de produto mais representativas**, cobrindo uma fração relevante dos pedidos (ex.: 90% do volume total).

2. **Redução do fator `product_cat`**:  
   - Reduzir de 73 para, por exemplo, **10 categorias mais frequentes**, ou aplicar uma **consolidação temática** (agrupar categorias similares).
   - Avaliar distribuição pós-redução para manter heterogeneidade e garantir robustez estatística.

3. **Reavaliação da combinatória** com `product_cat reduzido`:

\[
8 × 2 × 5 × \textbf{10} × 4 × 2 × 27 = 172\,800 \text{ células}
\]

\[
\bar r = \frac{100\,000}{172\,800} \approx 0{,}58
\]

4. **Aplicação de mais um filtro (ex: `payment_type`) (REDUZIR)**:  
   - Reduzir de 4 para **2 tipos principais** (ex.: à vista e à prazo), mantendo os mais frequentes.

\[
8 × 2 × 5 × \textbf{10} × \textbf{2} × 2 × 27 = 86\,400 \text{ células}
\]

\[
\bar r = \frac{100\,000}{86\,400} \approx 1{,}16
\]

5. **Iterar redução até alcançar \(\bar r \geq 5\)**:  
   - Por exemplo, aplicar filtros adicionais em `time_slot` (reduzir de 8 para 4 slots) e `income_level` (agrupar níveis extremos).
   - Resultado esperado:

\[
4 × 2 × 3 × 8 × 2 × 2 × 27 = 20\,736 \text{ células}
\]

\[
\bar r = \frac{100\,000}{20\,736} \approx 4{,}82 \approx 5
\]

---