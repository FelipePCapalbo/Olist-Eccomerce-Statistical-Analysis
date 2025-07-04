import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import chi2_contingency, normaltest, jarque_bera
import os
import warnings
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches
from collections import Counter
warnings.filterwarnings('ignore')

# Configuração do matplotlib para melhor visualização
plt.rcParams['figure.figsize'] = (16, 12)
plt.rcParams['font.size'] = 9
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8

def load_and_prepare_comprehensive_data():
    """
    Carrega e prepara dados com análise de qualidade e tratamento de vulnerabilidades.
    
    Returns:
        tuple: (DataFrame principal, dict com estatísticas de qualidade)
    """
    print("=== CARREGAMENTO E ANÁLISE DE QUALIDADE DOS DADOS ===")
    
    # Carregar todos os datasets necessários
    print("Carregando datasets...")
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    orders_df = pd.read_csv('olist-csv/olist_orders_dataset.csv')
    customers_df = pd.read_csv('olist-csv/olist_customers_dataset.csv')
    
    quality_stats = {}
    
    # 1. ANÁLISE DE QUALIDADE INICIAL
    print("\n1. ANÁLISE DE QUALIDADE DOS DADOS")
    quality_stats['items_total'] = len(items_df)
    quality_stats['orders_total'] = len(orders_df)
    quality_stats['customers_total'] = len(customers_df)
    quality_stats['products_total'] = len(products_df)
    
    # Verificar dados faltantes críticos
    quality_stats['items_missing_product'] = items_df['product_id'].isna().sum()
    quality_stats['items_missing_price'] = items_df['price'].isna().sum()
    quality_stats['products_missing_category'] = products_df['product_category_name'].isna().sum()
    
    print(f"   • Itens sem produto ID: {quality_stats['items_missing_product']}")
    print(f"   • Itens sem preço: {quality_stats['items_missing_price']}")
    print(f"   • Produtos sem categoria: {quality_stats['products_missing_category']}")
    
    # 2. MERGE PROGRESSIVO COM CONTROLE DE QUALIDADE
    print("\n2. CONSTRUÇÃO DO DATASET INTEGRADO")
    
    # Merge items com products
    items_products = items_df.merge(
        products_df[['product_id', 'product_category_name']], 
        on='product_id', 
        how='left'
    )
    quality_stats['items_after_product_merge'] = len(items_products)
    quality_stats['items_lost_in_product_merge'] = quality_stats['items_total'] - quality_stats['items_after_product_merge']
    
    # Merge com tradução de categorias
    items_products_trans = items_products.merge(
        translation_df, 
        on='product_category_name', 
        how='left'
    )
    
    # Merge orders com customers para obter UF
    orders_customers = orders_df.merge(
        customers_df[['customer_id', 'customer_state', 'customer_city']], 
        on='customer_id', 
        how='left'
    )
    
    # Merge final: items com orders+customers
    final_df = items_products_trans.merge(
        orders_customers[['order_id', 'customer_state', 'customer_city', 'order_status']], 
        on='order_id', 
        how='left'
    )
    
    quality_stats['final_records'] = len(final_df)
    print(f"   • Registros após merge completo: {quality_stats['final_records']}")
    
    # 3. LIMPEZA E FILTROS DE QUALIDADE
    print("\n3. APLICAÇÃO DE FILTROS DE QUALIDADE")
    
    # Filtrar apenas pedidos entregues
    final_df = final_df[final_df['order_status'] == 'delivered']
    quality_stats['delivered_orders'] = len(final_df)
    print(f"   • Registros após filtro de pedidos entregues: {quality_stats['delivered_orders']}")
    
    # Remover registros com dados críticos faltantes
    initial_count = len(final_df)
    final_df = final_df.dropna(subset=['price', 'freight_value', 'product_category_name_english', 'customer_state'])
    quality_stats['after_critical_na_removal'] = len(final_df)
    print(f"   • Registros após remoção de NAs críticos: {quality_stats['after_critical_na_removal']}")
    
    # Filtrar valores de preço válidos
    final_df = final_df[
        (final_df['price'] > 0) & 
        (final_df['freight_value'] >= 0) &
        (final_df['price'] <= 10000)  # Filtro de outliers extremos
    ]
    quality_stats['after_price_filters'] = len(final_df)
    print(f"   • Registros após filtros de preço: {quality_stats['after_price_filters']}")
    
    # 4. AGREGAÇÃO POR PEDIDO
    print("\n4. AGREGAÇÃO POR PEDIDO")
    
    # Calcular métricas por pedido
    orders_summary = final_df.groupby(['order_id', 'customer_state']).agg({
        'price': 'sum',  # Ticket total
        'freight_value': 'sum',  # Frete total
        'order_item_id': 'count',  # Quantidade de itens
        'product_category_name_english': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'mixed'  # Categoria principal
    }).reset_index()
    
    # Renomear colunas
    orders_summary.columns = ['order_id', 'customer_state', 'order_ticket', 'freight_value', 'n_items', 'product_category']
    
    # Calcular freight_ratio
    orders_summary['freight_ratio'] = orders_summary['freight_value'] / orders_summary['order_ticket']
    orders_summary['freight_ratio'] = orders_summary['freight_ratio'].clip(0, 1)  # Limitar a [0,1]
    
    quality_stats['final_orders'] = len(orders_summary)
    print(f"   • Pedidos únicos finais: {quality_stats['final_orders']}")
    
    # 5. ANÁLISE DE DISTRIBUIÇÃO FINAL
    print("\n5. ANÁLISE DE DISTRIBUIÇÃO FINAL")
    print(f"   • Estados únicos: {orders_summary['customer_state'].nunique()}")
    print(f"   • Categorias únicas: {orders_summary['product_category'].nunique()}")
    
    top_states = orders_summary['customer_state'].value_counts().head(5)
    top_categories = orders_summary['product_category'].value_counts().head(5)
    
    print("   • Top 5 estados:")
    for state, count in top_states.items():
        print(f"     {state}: {count} pedidos ({count/len(orders_summary)*100:.1f}%)")
    
    print("   • Top 5 categorias:")
    for cat, count in top_categories.items():
        print(f"     {cat}: {count} pedidos ({count/len(orders_summary)*100:.1f}%)")
    
    return orders_summary, quality_stats

def identify_analysis_strategy(df):
    """
    Identifica estratégia de análise baseada na distribuição dos dados.
    
    Args:
        df: DataFrame com os dados
        
    Returns:
        dict: Estratégia de análise recomendada
    """
    print("\n=== DEFINIÇÃO DE ESTRATÉGIA DE ANÁLISE ===")
    
    strategy = {}
    
    # Análise de estados
    state_counts = df['customer_state'].value_counts()
    strategy['total_states'] = len(state_counts)
    strategy['states_with_min_sample'] = (state_counts >= 100).sum()
    strategy['top_states'] = state_counts.head(8).index.tolist()  # Top 8 estados
    
    print(f"Estados com amostra mínima (≥100): {strategy['states_with_min_sample']}/{strategy['total_states']}")
    
    # Análise de categorias
    category_counts = df['product_category'].value_counts()
    strategy['total_categories'] = len(category_counts)
    strategy['categories_with_min_sample'] = (category_counts >= 100).sum()
    strategy['top_categories'] = category_counts.head(6).index.tolist()  # Top 6 categorias
    
    print(f"Categorias com amostra mínima (≥100): {strategy['categories_with_min_sample']}/{strategy['total_categories']}")
    
    # Análise de combinações estado-categoria
    state_category_counts = df.groupby(['customer_state', 'product_category']).size()
    strategy['viable_combinations'] = (state_category_counts >= 30).sum()
    strategy['total_combinations'] = len(state_category_counts)
    
    print(f"Combinações viáveis estado-categoria (≥30): {strategy['viable_combinations']}/{strategy['total_combinations']}")
    
    # Recomendação de análise
    if strategy['viable_combinations'] >= 20:
        strategy['analysis_type'] = 'full_crossover'
        print("RECOMENDAÇÃO: Análise cruzada completa estado × categoria")
    elif strategy['states_with_min_sample'] >= 5:
        strategy['analysis_type'] = 'state_focused'
        print("RECOMENDAÇÃO: Análise focada em estados principais")
    else:
        strategy['analysis_type'] = 'category_focused'
        print("RECOMENDAÇÃO: Análise focada em categorias principais")
    
    return strategy

def analyze_discrete_variable(data, variable_name, max_categories=15):
    """
    Análise específica para variáveis discretas com distribuições apropriadas.
    
    Args:
        data: array com os dados
        variable_name: nome da variável
        max_categories: máximo de categorias para exibir
        
    Returns:
        dict: Resultados da análise
    """
    results = {}
    
    # Contar frequências
    value_counts = pd.Series(data).value_counts().sort_index()
    
    if len(value_counts) > max_categories:
        # Se há muitas categorias, agrupar as menos frequentes
        top_categories = value_counts.head(max_categories - 1)
        others_count = value_counts.tail(len(value_counts) - max_categories + 1).sum()
        value_counts = pd.concat([top_categories, pd.Series([others_count], index=['Others'])])
    
    results['value_counts'] = value_counts
    results['total_observations'] = len(data)
    results['unique_values'] = len(pd.Series(data).unique())
    results['mode'] = pd.Series(data).mode().iloc[0] if len(pd.Series(data).mode()) > 0 else None
    results['median'] = pd.Series(data).median()
    results['mean'] = pd.Series(data).mean()
    results['std'] = pd.Series(data).std()
    
    # Teste de uniformidade (qui-quadrado)
    if len(value_counts) > 1:
        expected_freq = results['total_observations'] / len(value_counts)
        chi2_stat = ((value_counts - expected_freq) ** 2 / expected_freq).sum()
        chi2_pvalue = 1 - stats.chi2.cdf(chi2_stat, len(value_counts) - 1)
        results['uniformity_test'] = {
            'chi2_statistic': chi2_stat,
            'p_value': chi2_pvalue,
            'is_uniform': chi2_pvalue > 0.05
        }
    
    return results

def create_discrete_distribution_plot(data, variable_name, title=""):
    """
    Cria gráfico apropriado para variável discreta.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Análise da variável
    analysis = analyze_discrete_variable(data, variable_name)
    value_counts = analysis['value_counts']
    
    # Gráfico de barras das frequências
    ax1.bar(range(len(value_counts)), value_counts.values, 
            color='steelblue', alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(value_counts)))
    ax1.set_xticklabels(value_counts.index, rotation=45)
    ax1.set_ylabel('Frequência Absoluta')
    ax1.set_title(f'Distribuição de Frequências - {variable_name}')
    ax1.grid(True, alpha=0.3)
    
    # Adicionar valores nas barras
    for i, v in enumerate(value_counts.values):
        ax1.text(i, v + max(value_counts.values) * 0.01, str(v), 
                ha='center', va='bottom', fontsize=8)
    
    # Gráfico de frequências relativas (probabilidades empíricas)
    rel_freq = value_counts / value_counts.sum()
    ax2.bar(range(len(rel_freq)), rel_freq.values, 
            color='orange', alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(rel_freq)))
    ax2.set_xticklabels(rel_freq.index, rotation=45)
    ax2.set_ylabel('Probabilidade Empírica')
    ax2.set_title(f'Distribuição de Probabilidades - {variable_name}')
    ax2.grid(True, alpha=0.3)
    
    # Adicionar valores nas barras
    for i, v in enumerate(rel_freq.values):
        ax2.text(i, v + max(rel_freq.values) * 0.01, f'{v:.3f}', 
                ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig, analysis

def comprehensive_variable_analysis(df, variable, category_col, state_col, variable_type='continuous'):
    """
    Análise abrangente de uma variável por categoria e estado.
    
    Args:
        df: DataFrame
        variable: nome da variável a analisar
        category_col: coluna de categoria
        state_col: coluna de estado
        variable_type: 'continuous' ou 'discrete'
    """
    print(f"\n=== ANÁLISE ABRANGENTE: {variable.upper()} ===")
    
    # Selecionar top categorias e estados para análise detalhada
    top_categories = df[category_col].value_counts().head(6).index
    top_states = df[state_col].value_counts().head(8).index
    
    # Filtrar dados para análise focada
    analysis_df = df[
        (df[category_col].isin(top_categories)) & 
        (df[state_col].isin(top_states))
    ]
    
    print(f"Dados para análise: {len(analysis_df)} registros")
    print(f"Categorias analisadas: {list(top_categories)}")
    print(f"Estados analisados: {list(top_states)}")
    
    # Criar visualização composta por estado
    for state in top_states:
        state_data = analysis_df[analysis_df[state_col] == state]
        
        if len(state_data) < 50:  # Pular estados com poucos dados
            continue
            
        create_state_composite_analysis(state_data, variable, category_col, state, variable_type)

def create_state_composite_analysis(state_data, variable, category_col, state_name, variable_type):
    """
    Cria análise composta para um estado específico com subimagens por categoria.
    """
    categories = state_data[category_col].value_counts().head(6).index
    
    # Configurar figura grande
    fig = plt.figure(figsize=(20, 16))
    fig.suptitle(f'ANÁLISE DETALHADA - {variable.upper()} - ESTADO: {state_name}', 
                 fontsize=16, fontweight='bold', y=0.95)
    
    # Criar grid para subplots
    gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)
    
    # Análise geral do estado (subplot principal)
    ax_main = fig.add_subplot(gs[0, :])
    
    if variable_type == 'discrete':
        analysis = analyze_discrete_variable(state_data[variable], variable)
        value_counts = analysis['value_counts']
        
        bars = ax_main.bar(range(len(value_counts)), value_counts.values, 
                          color='darkblue', alpha=0.7, edgecolor='black')
        ax_main.set_xticks(range(len(value_counts)))
        ax_main.set_xticklabels(value_counts.index)
        ax_main.set_ylabel('Frequência')
        ax_main.set_title(f'{state_name} - Distribuição Geral de {variable} (N={len(state_data)})')
        
        # Adicionar valores nas barras
        for bar, value in zip(bars, value_counts.values):
            height = bar.get_height()
            ax_main.text(bar.get_x() + bar.get_width()/2., height + max(value_counts.values)*0.01,
                        f'{value}', ha='center', va='bottom', fontweight='bold')
    else:
        # Análise contínua
        ax_main.hist(state_data[variable], bins=30, color='darkblue', alpha=0.7, edgecolor='black')
        ax_main.set_ylabel('Frequência')
        ax_main.set_xlabel(variable)
        ax_main.set_title(f'{state_name} - Distribuição Geral de {variable} (N={len(state_data)})')
        ax_main.axvline(state_data[variable].mean(), color='red', linestyle='--', 
                       label=f'Média: {state_data[variable].mean():.2f}')
        ax_main.legend()
    
    ax_main.grid(True, alpha=0.3)
    
    # Análises por categoria (subplots menores)
    subplot_positions = [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
    
    for i, category in enumerate(categories[:6]):
        if i >= len(subplot_positions):
            break
            
        row, col = subplot_positions[i]
        ax = fig.add_subplot(gs[row, col])
        
        cat_data = state_data[state_data[category_col] == category][variable]
        
        if len(cat_data) < 10:  # Pular categorias com poucos dados
            ax.text(0.5, 0.5, f'Dados insuficientes\n(N={len(cat_data)})', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{category}')
            continue
        
        if variable_type == 'discrete':
            cat_analysis = analyze_discrete_variable(cat_data, variable)
            cat_counts = cat_analysis['value_counts']
            
            bars = ax.bar(range(len(cat_counts)), cat_counts.values, 
                         color='orange', alpha=0.7, edgecolor='black')
            ax.set_xticks(range(len(cat_counts)))
            ax.set_xticklabels(cat_counts.index, fontsize=8)
            
            # Adicionar valores nas barras se não há muitas
            if len(cat_counts) <= 8:
                for bar, value in zip(bars, cat_counts.values):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + max(cat_counts.values)*0.05,
                           f'{value}', ha='center', va='bottom', fontsize=7)
        else:
            ax.hist(cat_data, bins=15, color='orange', alpha=0.7, edgecolor='black')
            ax.axvline(cat_data.mean(), color='red', linestyle='--', linewidth=2)
        
        ax.set_title(f'{category}\n(N={len(cat_data)})', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # Estatísticas básicas no subplot
        if variable_type == 'discrete':
            stats_text = f'Moda: {cat_analysis["mode"]}\nMédia: {cat_analysis["mean"]:.2f}'
        else:
            stats_text = f'Média: {cat_data.mean():.2f}\nDP: {cat_data.std():.2f}'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               verticalalignment='top', fontsize=7, 
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Salvar figura
    filename = f'charts/composite_{variable}_{state_name.lower()}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   → Análise composta salva: {filename}")

def generate_comprehensive_report(df, quality_stats, strategy):
    """
    Gera relatório abrangente da análise.
    """
    print("\n=== GERANDO RELATÓRIO ABRANGENTE ===")
    
    report_lines = []
    
    # Cabeçalho
    report_lines.extend([
        "# ANÁLISE ESTATÍSTICA ABRANGENTE - E-COMMERCE BRASILEIRO",
        "## Análise Exploratória Expandida por UF e Categoria de Produto",
        "",
        "### METODOLOGIA E QUALIDADE DOS DADOS",
        "",
    ])
    
    # Seção de qualidade dos dados
    report_lines.extend([
        "#### 1. Avaliação da Qualidade dos Dados",
        "",
        "Esta análise implementa controles rigorosos de qualidade para identificar e tratar vulnerabilidades que podem comprometer o entendimento estatístico:",
        "",
        f"**Volume de Dados Processados:**",
        f"- Registros iniciais de itens: {quality_stats['items_total']:,}",
        f"- Pedidos únicos finais: {quality_stats['final_orders']:,}",
        f"- Taxa de aproveitamento: {quality_stats['final_orders']/quality_stats['items_total']*100:.1f}%",
        "",
        f"**Vulnerabilidades Identificadas e Tratadas:**",
        f"- Produtos sem categoria: {quality_stats['products_missing_category']:,}",
        f"- Itens sem correspondência de produto: {quality_stats.get('items_missing_product', 0):,}",
        f"- Pedidos não entregues removidos: {quality_stats['orders_total'] - quality_stats['delivered_orders']:,}",
        "",
    ])
    
    # Seção de estratégia
    report_lines.extend([
        "#### 2. Estratégia de Análise Adotada",
        "",
        f"**Distribuição Geográfica:**",
        f"- Estados com amostra significativa (≥100): {strategy['states_with_min_sample']}/{strategy['total_states']}",
        f"- Estados selecionados para análise detalhada: {', '.join(strategy['top_states'])}",
        "",
        f"**Distribuição por Categoria:**",
        f"- Categorias com amostra significativa (≥100): {strategy['categories_with_min_sample']}/{strategy['total_categories']}",
        f"- Categorias selecionadas: {', '.join(strategy['top_categories'])}",
        "",
        f"**Combinações Viáveis Estado×Categoria:**",
        f"- Combinações com amostra mínima (≥30): {strategy['viable_combinations']}/{strategy['total_combinations']}",
        f"- Tipo de análise recomendada: {strategy['analysis_type']}",
        "",
    ])
    
    # Análise descritiva por variável
    variables_analysis = {
        'order_ticket': ('Ticket Médio (R$)', 'continuous'),
        'freight_ratio': ('Razão do Frete', 'continuous'),
        'n_items': ('Quantidade de Itens', 'discrete')
    }
    
    for var_name, (var_display, var_type) in variables_analysis.items():
        if var_name in df.columns:
            report_lines.extend([
                f"### ANÁLISE DA VARIÁVEL: {var_display}",
                "",
                f"**Tipo de Variável:** {var_type.title()}",
                f"**Metodologia:** {'Distribuições discretas com análise de frequências' if var_type == 'discrete' else 'Análise de distribuições contínuas com testes de normalidade'}",
                "",
            ])
            
            # Estatísticas gerais
            if var_type == 'discrete':
                analysis = analyze_discrete_variable(df[var_name], var_name)
                report_lines.extend([
                    f"**Estatísticas Descritivas Gerais:**",
                    f"- Total de observações: {analysis['total_observations']:,}",
                    f"- Valores únicos: {analysis['unique_values']}",
                    f"- Moda: {analysis['mode']}",
                    f"- Mediana: {analysis['median']:.2f}",
                    f"- Média: {analysis['mean']:.2f}",
                    f"- Desvio padrão: {analysis['std']:.2f}",
                    "",
                ])
                
                if 'uniformity_test' in analysis:
                    uniformity = analysis['uniformity_test']
                    report_lines.extend([
                        f"**Teste de Uniformidade (Qui-quadrado):**",
                        f"- Estatística χ²: {uniformity['chi2_statistic']:.4f}",
                        f"- P-valor: {uniformity['p_value']:.4f}",
                        f"- Distribuição uniforme: {'Sim' if uniformity['is_uniform'] else 'Não'} (α = 0.05)",
                        "",
                    ])
            else:
                report_lines.extend([
                    f"**Estatísticas Descritivas Gerais:**",
                    f"- Média: {df[var_name].mean():.2f}",
                    f"- Mediana: {df[var_name].median():.2f}",
                    f"- Desvio padrão: {df[var_name].std():.2f}",
                    f"- Mínimo: {df[var_name].min():.2f}",
                    f"- Máximo: {df[var_name].max():.2f}",
                    "",
                ])
            
            # Análise por estado
            report_lines.extend([
                f"**Análise por Estado (Top 5):**",
                "",
            ])
            
            for state in strategy['top_states'][:5]:
                state_data = df[df['customer_state'] == state][var_name]
                if len(state_data) > 0:
                    if var_type == 'discrete':
                        state_analysis = analyze_discrete_variable(state_data, var_name)
                        report_lines.append(f"- **{state}** (N={len(state_data)}): Moda={state_analysis['mode']}, Média={state_analysis['mean']:.2f}")
                    else:
                        report_lines.append(f"- **{state}** (N={len(state_data)}): Média={state_data.mean():.2f}, DP={state_data.std():.2f}")
            
            report_lines.extend(["", "---", ""])
    
    # Salvar relatório
    with open('comprehensive_analysis_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print("   → Relatório salvo: comprehensive_analysis_report.md")

def main():
    """
    Função principal que executa a análise abrangente.
    """
    print("INICIANDO ANÁLISE ESTATÍSTICA ABRANGENTE")
    print("=" * 60)
    
    # Criar diretório para gráficos se não existir
    os.makedirs('charts', exist_ok=True)
    
    # 1. Carregar e preparar dados
    df, quality_stats = load_and_prepare_comprehensive_data()
    
    # 2. Definir estratégia de análise
    strategy = identify_analysis_strategy(df)
    
    # 3. Análises por variável
    variables_to_analyze = [
        ('order_ticket', 'continuous'),
        ('freight_ratio', 'continuous'),
        ('n_items', 'discrete')
    ]
    
    for variable, var_type in variables_to_analyze:
        if variable in df.columns:
            comprehensive_variable_analysis(
                df, variable, 'product_category', 'customer_state', var_type
            )
    
    # 4. Gerar relatório
    generate_comprehensive_report(df, quality_stats, strategy)
    
    print("\n" + "=" * 60)
    print("ANÁLISE ABRANGENTE CONCLUÍDA")
    print(f"Total de gráficos gerados: {len([f for f in os.listdir('charts') if f.startswith('composite_')])}")
    print("Verifique o arquivo 'comprehensive_analysis_report.md' para o relatório detalhado")

if __name__ == "__main__":
    main()