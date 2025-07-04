import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

# Configuração do matplotlib para melhor visualização
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

def load_and_prepare_data():
    """
    Carrega e prepara os dados agregando por order_id e incluindo categoria de produto.
    
    Returns:
        pd.DataFrame: DataFrame com order_id, order_ticket, freight_ratio, n_items, product_category
    """
    print("Carregando dados...")
    
    # Carregar dados dos itens
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    
    # Carregar dados dos produtos para obter categoria
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    
    # Carregar tradução das categorias
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    
    # Merge para obter categorias dos produtos
    items_with_category = items_df.merge(
        products_df[['product_id', 'product_category_name']], 
        on='product_id', 
        how='left'
    )
    
    # Adicionar tradução das categorias
    items_with_category = items_with_category.merge(
        translation_df, 
        on='product_category_name', 
        how='left'
    )
    
    # Para cada pedido, calcular métricas agregadas
    orders_summary = items_with_category.groupby('order_id').agg({
        'price': 'sum',  # Ticket total
        'freight_value': 'sum',  # Frete total
        'order_item_id': 'count',  # Quantidade de itens
        'product_category_name_english': lambda x: x.mode().iloc[0] if not x.mode().empty else 'unknown'  # Categoria mais frequente
    }).reset_index()
    
    # Renomear colunas
    orders_summary.columns = ['order_id', 'order_ticket', 'freight_value', 'n_items', 'product_category']
    
    # Calcular freight_ratio
    orders_summary['freight_ratio'] = orders_summary['freight_value'] / orders_summary['order_ticket']
    
    # Filtrar dados válidos
    orders_summary = orders_summary[
        (orders_summary['order_ticket'] > 0) & 
        (orders_summary['freight_value'] >= 0) &
        (orders_summary['n_items'] > 0) &
        (orders_summary['product_category'].notna()) &
        (orders_summary['product_category'] != 'unknown')
    ]
    
    # Limitar freight_ratio a [0, 1] para valores realistas
    orders_summary['freight_ratio'] = orders_summary['freight_ratio'].clip(0, 1)
    
    print(f"Dados carregados: {len(orders_summary)} pedidos")
    print(f"Categorias encontradas: {orders_summary['product_category'].nunique()}")
    
    return orders_summary

def anderson_darling_interpretation(statistic, critical_values, significance_levels):
    """
    Interpreta os resultados do teste Anderson-Darling com explicação das hipóteses.
    
    Returns:
        str: Interpretação formatada do teste
    """
    interpretation = []
    interpretation.append("**Hipóteses do Teste Anderson-Darling:**")
    interpretation.append("- **H₀ (Hipótese Nula)**: Os dados seguem uma distribuição normal")
    interpretation.append("- **H₁ (Hipótese Alternativa)**: Os dados NÃO seguem uma distribuição normal")
    interpretation.append("")
    interpretation.append("**Critério de Decisão:**")
    interpretation.append("- Se A² < valor crítico: NÃO rejeitamos H₀ (dados podem ser normais)")
    interpretation.append("- Se A² ≥ valor crítico: REJEITAMOS H₀ (dados não são normais)")
    interpretation.append("")
    interpretation.append(f"**Estatística do Teste A²**: {statistic:.4f}")
    interpretation.append("")
    interpretation.append("**Resultados por nível de significância:**")
    
    for i, (sl, cv) in enumerate(zip(significance_levels, critical_values)):
        if statistic < cv:
            decision = f"NÃO REJEITAR H₀"
            conclusion = "dados podem ser considerados normais"
        else:
            decision = f"REJEITAR H₀"
            conclusion = "dados não são normais"
        
        interpretation.append(f"  - α = {sl}%: A² = {statistic:.3f} {'<' if statistic < cv else '≥'} {cv:.3f} → {decision} ({conclusion})")
    
    return "\n".join(interpretation)

def graphical_summary_by_category(data, variable_name, category, output_dir='charts'):
    """
    Gera análise descritiva completa para uma variável em uma categoria específica.
    
    Args:
        data (pd.Series): Dados da variável
        variable_name (str): Nome da variável
        category (str): Nome da categoria
        output_dir (str): Diretório de saída
    
    Returns:
        str: Markdown com a análise
    """
    if len(data) < 50:  # Muito poucos dados para análise confiável
        return f"**Categoria {category}**: Dados insuficientes (N={len(data)}) para análise."
    
    # Criar diretório se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Estatísticas descritivas
    desc_stats = data.describe()
    
    # Teste de normalidade Anderson-Darling
    try:
        anderson_result = stats.anderson(data.dropna())
        anderson_interpretation = anderson_darling_interpretation(
            anderson_result.statistic, 
            anderson_result.critical_values, 
            anderson_result.significance_level
        )
    except:
        anderson_interpretation = "Erro no cálculo do teste Anderson-Darling"
    
    # Fit de distribuições
    distributions_to_test = [
        ('Normal', stats.norm),
        ('Log-Normal', stats.lognorm),
        ('Exponencial', stats.expon),
        ('Gamma', stats.gamma),
        ('Weibull', stats.weibull_min)
    ]
    
    best_fit_name = ''
    best_fit_sse = np.inf
    best_fit_params = None
    
    data_clean = data.dropna()
    sorted_data = np.sort(data_clean)
    y_ecdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
    
    for dist_name, distribution in distributions_to_test:
        try:
            if dist_name == 'Log-Normal' and (data_clean <= 0).any():
                continue  # Log-normal não funciona com valores <= 0
            
            params = distribution.fit(data_clean)
            cdf_fitted = distribution.cdf(sorted_data, *params)
            sse = np.sum((y_ecdf - cdf_fitted) ** 2)
            
            if sse < best_fit_sse:
                best_fit_name = dist_name
                best_fit_sse = sse
                best_fit_params = params
        except:
            continue
    
    # Gerar gráficos
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'Análise: {variable_name} - {category}', fontsize=16, weight='bold')
    
    # Histograma com densidades
    ax1 = axes[0, 0]
    data_clean.hist(bins=30, density=True, alpha=0.7, ax=ax1, color='lightblue')
    
    # KDE
    try:
        data_clean.plot(kind='kde', ax=ax1, color='blue', linewidth=2, label='KDE')
    except:
        pass
    
    # Curva normal
    x_range = np.linspace(data_clean.min(), data_clean.max(), 100)
    normal_curve = stats.norm.pdf(x_range, data_clean.mean(), data_clean.std())
    ax1.plot(x_range, normal_curve, 'r--', linewidth=2, label='Normal')
    
    # Melhor fit
    if best_fit_name and best_fit_params:
        try:
            best_dist = distributions_to_test[[d[0] for d in distributions_to_test].index(best_fit_name)][1]
            best_curve = best_dist.pdf(x_range, *best_fit_params)
            ax1.plot(x_range, best_curve, 'g-.', linewidth=2, label=f'Melhor Fit: {best_fit_name}')
        except:
            pass
    
    ax1.set_title('Histograma e Curvas de Densidade')
    ax1.set_xlabel(variable_name)
    ax1.set_ylabel('Densidade')
    ax1.legend()
    
    # Boxplot
    ax2 = axes[0, 1]
    data_clean.plot(kind='box', ax=ax2, vert=True)
    ax2.set_title('Boxplot')
    ax2.set_ylabel(variable_name)
    
    # Q-Q Plot
    ax3 = axes[1, 0]
    stats.probplot(data_clean, dist="norm", plot=ax3)
    ax3.set_title('Q-Q Plot (Normal)')
    ax3.grid(True)
    
    # Estatísticas textuais
    ax4 = axes[1, 1]
    ax4.axis('off')
    stats_text = f"""
Estatísticas Descritivas:
N: {len(data_clean):,}
Média: {desc_stats['mean']:.2f}
Mediana: {desc_stats['50%']:.2f}
Desvio Padrão: {desc_stats['std']:.2f}
Mín: {desc_stats['min']:.2f}
Máx: {desc_stats['max']:.2f}
Q1: {desc_stats['25%']:.2f}
Q3: {desc_stats['75%']:.2f}
IQR: {desc_stats['75%'] - desc_stats['25%']:.2f}

Melhor Distribuição: {best_fit_name}
SSE: {best_fit_sse:.4f}
    """
    ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=10, 
             verticalalignment='top', fontfamily='monospace')
    
    plt.tight_layout()
    
    # Salvar gráfico
    filename = f"{variable_name.lower().replace(' ', '_')}_{category.lower().replace(' ', '_').replace('/', '_')}.png"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Gerar markdown
    markdown_output = f"""
#### Categoria: **{category}**

##### Estatísticas Descritivas
| Métrica | Valor |
|---------|-------|
| Contagem (N) | {len(data_clean):,} |
| Média | {desc_stats['mean']:.2f} |
| Desvio Padrão | {desc_stats['std']:.2f} |
| Mínimo | {desc_stats['min']:.2f} |
| 1º Quartil (Q1) | {desc_stats['25%']:.2f} |
| Mediana (Q2) | {desc_stats['50%']:.2f} |
| 3º Quartil (Q3) | {desc_stats['75%']:.2f} |
| Máximo | {desc_stats['max']:.2f} |
| Amplitude Interquartil | {desc_stats['75%'] - desc_stats['25%']:.2f} |

##### Teste de Normalidade (Anderson-Darling)
{anderson_interpretation}

##### Melhor Ajuste de Distribuição
- **Distribuição**: {best_fit_name}
- **SSE**: {best_fit_sse:.4f}

##### Gráfico
![{variable_name} - {category}]({filepath})

---
"""
    
    return markdown_output

def analyze_variable_by_category(data, variable_column, variable_display_name, top_n_categories=10):
    """
    Analisa uma variável para as top N categorias de produto.
    
    Args:
        data (pd.DataFrame): DataFrame com os dados
        variable_column (str): Nome da coluna no DataFrame
        variable_display_name (str): Nome para exibição nos gráficos e relatórios
        top_n_categories (int): Número de categorias a analisar (mais frequentes)
    
    Returns:
        str: Markdown com todas as análises
    """
    # Selecionar as top N categorias por volume de pedidos
    top_categories = data['product_category'].value_counts().head(top_n_categories).index.tolist()
    
    markdown_results = []
    markdown_results.append(f"## Análise da Variável: **{variable_display_name}**")
    markdown_results.append(f"*Análise desagregada pelas {top_n_categories} categorias de produto com maior volume de pedidos*")
    markdown_results.append("")
    
    for category in top_categories:
        category_data = data[data['product_category'] == category][variable_column]
        analysis = graphical_summary_by_category(category_data, variable_display_name, category)
        markdown_results.append(analysis)
    
    return "\n".join(markdown_results)

def main():
    """Função principal que executa toda a análise."""
    
    print("=== ANÁLISE DESCRITIVA POR CATEGORIA DE PRODUTO ===")
    
    # Carregar e preparar dados
    data = load_and_prepare_data()
    
    # Mostrar overview das categorias
    print("\nTop 15 categorias por volume:")
    print(data['product_category'].value_counts().head(15))
    
    # Criar diretório de gráficos
    os.makedirs('charts', exist_ok=True)
    
    # Analisar as 3 variáveis principais para as top 8 categorias
    variables_to_analyze = [
        ('order_ticket', 'Ticket Médio (R$)'),
        ('freight_ratio', 'Razão do Frete'),
        ('n_items', 'Quantidade de Itens')
    ]
    
    all_results = []
    all_results.append("# Análise Descritiva por Categoria de Produto")
    all_results.append("")
    all_results.append("Esta análise examina as distribuições das principais variáveis contínuas desagregadas por categoria de produto, focando nas categorias com maior volume de pedidos.")
    all_results.append("")
    
    for var_col, var_name in variables_to_analyze:
        print(f"\nAnalisando: {var_name}")
        analysis = analyze_variable_by_category(data, var_col, var_name, top_n_categories=8)
        all_results.append(analysis)
        all_results.append("\n" + "="*80 + "\n")
    
    # Salvar resultados completos
    with open('analise_por_categoria.md', 'w', encoding='utf-8') as f:
        f.write("\n".join(all_results))
    
    print(f"\n=== ANÁLISE CONCLUÍDA ===")
    print(f"- Gráficos salvos em: charts/")
    print(f"- Relatório completo salvo em: analise_por_categoria.md")
    print(f"- Total de pedidos analisados: {len(data):,}")
    print(f"- Categorias analisadas: 8 (das {data['product_category'].nunique()} disponíveis)")

if __name__ == '__main__':
    main() 