import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu, kruskal
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

# Configuração de visualização
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

def load_data():
    """Carrega e prepara os dados para análise sazonal"""
    print("Carregando dados...")
    
    # Carregar datasets
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    orders_df = pd.read_csv('olist-csv/olist_orders_dataset.csv')
    customers_df = pd.read_csv('olist-csv/olist_customers_dataset.csv')
    
    # Merge dos dados
    items_products = items_df.merge(products_df[['product_id', 'product_category_name']], on='product_id', how='left')
    items_products_trans = items_products.merge(translation_df, on='product_category_name', how='left')
    orders_customers = orders_df.merge(customers_df[['customer_id', 'customer_state']], on='customer_id', how='left')
    
    final_df = items_products_trans.merge(
        orders_customers[['order_id', 'customer_state', 'order_status', 'order_purchase_timestamp']], 
        on='order_id', how='left'
    )
    
    # Filtros de qualidade
    final_df = final_df[
        (final_df['order_status'] == 'delivered') &
        (final_df['price'] > 0) &
        (final_df['price'] <= 10000) &
        (final_df['freight_value'] >= 0) &
        (final_df['product_category_name_english'].notna()) &
        (final_df['customer_state'].notna())
    ]
    
    # Agregação por pedido
    orders_summary = final_df.groupby(['order_id', 'customer_state']).agg({
        'price': 'sum',
        'freight_value': 'sum',
        'order_item_id': 'count',
        'product_category_name_english': lambda x: x.mode().iloc[0],
        'order_purchase_timestamp': 'first'
    }).reset_index()
    
    orders_summary.columns = ['order_id', 'customer_state', 'order_ticket', 'freight_value', 'n_items', 'product_category', 'order_date']
    orders_summary['freight_ratio'] = orders_summary['freight_value'] / orders_summary['order_ticket']
    orders_summary['freight_ratio'] = orders_summary['freight_ratio'].clip(0, 1)
    
    # Converter data
    orders_summary['order_date'] = pd.to_datetime(orders_summary['order_date'])
    orders_summary['month'] = orders_summary['order_date'].dt.month
    orders_summary['day'] = orders_summary['order_date'].dt.day
    orders_summary['year'] = orders_summary['order_date'].dt.year
    
    # Classificar por região
    norte = ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO']
    nordeste = ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE']
    centro_oeste = ['DF', 'GO', 'MT', 'MS']
    sudeste = ['ES', 'MG', 'RJ', 'SP']
    sul = ['PR', 'RS', 'SC']
    
    def classify_region(state):
        if state in norte:
            return 'Norte'
        elif state in nordeste:
            return 'Nordeste'
        elif state in centro_oeste:
            return 'Centro-Oeste'
        elif state in sudeste:
            return 'Sudeste'
        elif state in sul:
            return 'Sul'
        else:
            return 'Outros'
    
    orders_summary['region'] = orders_summary['customer_state'].apply(classify_region)
    
    print(f"Dados carregados: {len(orders_summary)} pedidos")
    return orders_summary

def define_seasonal_periods(df):
    """Define períodos sazonais para datas comemorativas"""
    df = df.copy()
    
    # Criar coluna de período sazonal
    df['seasonal_period'] = 'normal'
    
    # Definir janelas sazonais (10 dias antes até a data)
    seasonal_windows = {
        'dia_das_maes': {
            'months': [4, 5],
            'days_april': list(range(28, 31)),  # 28-30 de abril
            'days_may': list(range(1, 9))       # 1-8 de maio
        },
        'dia_dos_pais': {
            'months': [8],
            'days': list(range(2, 13))           # 2-12 de agosto
        },
        'dia_das_criancas': {
            'months': [10],
            'days': list(range(2, 13))           # 2-12 de outubro
        },
        'natal': {
            'months': [12],
            'days': list(range(15, 26))          # 15-25 de dezembro
        }
    }
    
    # Aplicar janelas sazonais
    # Dia das Mães
    maes_mask = ((df['month'] == 4) & (df['day'].isin(seasonal_windows['dia_das_maes']['days_april']))) | \
                ((df['month'] == 5) & (df['day'].isin(seasonal_windows['dia_das_maes']['days_may'])))
    df.loc[maes_mask, 'seasonal_period'] = 'dia_das_maes'
    
    # Dia dos Pais
    pais_mask = (df['month'] == 8) & (df['day'].isin(seasonal_windows['dia_dos_pais']['days']))
    df.loc[pais_mask, 'seasonal_period'] = 'dia_dos_pais'
    
    # Dia das Crianças
    criancas_mask = (df['month'] == 10) & (df['day'].isin(seasonal_windows['dia_das_criancas']['days']))
    df.loc[criancas_mask, 'seasonal_period'] = 'dia_das_criancas'
    
    # Natal
    natal_mask = (df['month'] == 12) & (df['day'].isin(seasonal_windows['natal']['days']))
    df.loc[natal_mask, 'seasonal_period'] = 'natal'
    
    # Estatísticas dos períodos
    print("\nDistribuição de pedidos por período sazonal:")
    period_counts = df['seasonal_period'].value_counts()
    for period, count in period_counts.items():
        pct = (count / len(df)) * 100
        print(f"{period}: {count:,} pedidos ({pct:.1f}%)")
    
    return df

def analyze_ticket_by_category_and_season(df):
    """Analisa ticket médio por categoria em cada data comemorativa"""
    print("\n" + "="*80)
    print("ANÁLISE: TICKET MÉDIO POR CATEGORIA EM DATAS COMEMORATIVAS")
    print("="*80)
    
    # Filtrar categorias principais
    top_categories = df['product_category'].value_counts().head(8).index.tolist()
    df_categories = df[df['product_category'].isin(top_categories)]
    
    seasonal_periods = ['dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal']
    
    results = {}
    
    for category in top_categories:
        print(f"\n--- CATEGORIA: {category.upper()} ---")
        category_data = df_categories[df_categories['product_category'] == category]
        
        # Estatísticas por período
        category_stats = category_data.groupby('seasonal_period')['order_ticket'].agg(['count', 'mean', 'std']).round(2)
        print("\nEstatísticas por período:")
        print(category_stats)
        
        # Comparar cada data comemorativa vs período normal
        category_results = {}
        
        normal_data = category_data[category_data['seasonal_period'] == 'normal']['order_ticket']
        
        for period in seasonal_periods:
            period_data = category_data[category_data['seasonal_period'] == period]['order_ticket']
            
            if len(period_data) < 30:  # Amostra muito pequena
                print(f"\n{period}: Amostra insuficiente (n={len(period_data)})")
                continue
            
            # Teste Mann-Whitney U
            u_stat, p_val = mannwhitneyu(period_data, normal_data, alternative='two-sided')
            
            mean_period = period_data.mean()
            mean_normal = normal_data.mean()
            
            category_results[period] = {
                'mean_period': mean_period,
                'mean_normal': mean_normal,
                'p_value': p_val,
                'significant': p_val < 0.05,
                'higher': mean_period > mean_normal,
                'n_period': len(period_data),
                'n_normal': len(normal_data)
            }
            
            sig_mark = "***" if p_val < 0.05 else "ns"
            direction = "MAIOR" if mean_period > mean_normal else "menor"
            print(f"\n{period} vs normal:")
            print(f"  Médias: {mean_period:.2f} vs {mean_normal:.2f}")
            print(f"  P-value: {p_val:.6f} {sig_mark}")
            print(f"  Ticket {direction} na data comemorativa")
        
        results[category] = category_results
    
    return results

def compare_seasonal_periods_by_category(df):
    """Compara datas comemorativas entre si por categoria usando análise combinatória"""
    print("\n" + "="*80)
    print("ANÁLISE COMBINATÓRIA: RANKING DE DATAS COMEMORATIVAS POR CATEGORIA")
    print("="*80)
    
    # Filtrar categorias principais
    top_categories = df['product_category'].value_counts().head(6).index.tolist()
    df_categories = df[df['product_category'].isin(top_categories)]
    
    seasonal_periods = ['dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal']
    
    for category in top_categories:
        print(f"\n--- RANKING PARA {category.upper()} ---")
        category_data = df_categories[df_categories['product_category'] == category]
        
        # Filtrar apenas períodos sazonais (excluir normal)
        seasonal_data = category_data[category_data['seasonal_period'].isin(seasonal_periods)]
        
        # Verificar se há dados suficientes para cada período
        period_counts = seasonal_data['seasonal_period'].value_counts()
        valid_periods = [p for p in seasonal_periods if period_counts.get(p, 0) >= 20]
        
        if len(valid_periods) < 2:
            print("Dados insuficientes para comparação")
            continue
        
        # Estatísticas por período
        stats = seasonal_data.groupby('seasonal_period')['order_ticket'].agg(['count', 'mean']).round(2)
        print("\nEstatísticas por período:")
        for period in valid_periods:
            if period in stats.index:
                mean_val = stats.loc[period, 'mean']
                count_val = stats.loc[period, 'count']
                print(f"{period}: {mean_val:.2f} (n={count_val})")
        
        # Comparações par a par
        print(f"\nComparações par a par ({len(list(combinations(valid_periods, 2)))} testes):")
        
        results = {}
        for period1, period2 in combinations(valid_periods, 2):
            group1 = seasonal_data[seasonal_data['seasonal_period'] == period1]['order_ticket']
            group2 = seasonal_data[seasonal_data['seasonal_period'] == period2]['order_ticket']
            
            u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
            
            mean1, mean2 = group1.mean(), group2.mean()
            winner = period1 if mean1 > mean2 else period2
            significant = p_val < 0.05
            
            results[(period1, period2)] = {
                'winner': winner,
                'significant': significant,
                'p_value': p_val
            }
            
            sig_mark = "***" if significant else "ns"
            print(f"{period1} vs {period2}: {mean1:.2f} vs {mean2:.2f}, p={p_val:.5f} {sig_mark} → {winner}")
        
        # Calcular ranking
        scores = {period: 0 for period in valid_periods}
        for (p1, p2), result in results.items():
            if result['significant']:
                scores[result['winner']] += 1
            else:
                scores[p1] += 0.5
                scores[p2] += 0.5
        
        # Ranking final
        period_means = seasonal_data.groupby('seasonal_period')['order_ticket'].mean()
        ranking = sorted(valid_periods, key=lambda x: (scores[x], period_means[x]), reverse=True)
        
        print(f"\nRANKING FINAL:")
        for i, period in enumerate(ranking, 1):
            print(f"{i}. {period} (pontos: {scores[period]:.1f}, média: {period_means[period]:.2f})")

def analyze_freight_willingness_by_season(df):
    """Analisa disposição para pagar frete por região em datas comemorativas"""
    print("\n" + "="*80)
    print("ANÁLISE: DISPOSIÇÃO PARA PAGAR FRETE EM DATAS COMEMORATIVAS")
    print("="*80)
    
    seasonal_periods = ['dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal']
    regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
    
    for region in regions:
        print(f"\n--- REGIÃO: {region.upper()} ---")
        region_data = df[df['region'] == region]
        
        # Estatísticas por período
        region_stats = region_data.groupby('seasonal_period')['freight_ratio'].agg(['count', 'mean', 'std']).round(4)
        print("\nEstatísticas de razão do frete por período:")
        print(region_stats)
        
        # Comparar cada data comemorativa vs período normal
        normal_data = region_data[region_data['seasonal_period'] == 'normal']['freight_ratio']
        
        for period in seasonal_periods:
            period_data = region_data[region_data['seasonal_period'] == period]['freight_ratio']
            
            if len(period_data) < 30:
                print(f"\n{period}: Amostra insuficiente (n={len(period_data)})")
                continue
            
            # Teste Mann-Whitney U
            u_stat, p_val = mannwhitneyu(period_data, normal_data, alternative='two-sided')
            
            mean_period = period_data.mean()
            mean_normal = normal_data.mean()
            
            sig_mark = "***" if p_val < 0.05 else "ns"
            direction = "MAIOR" if mean_period > mean_normal else "menor"
            print(f"\n{period} vs normal:")
            print(f"  Razão frete: {mean_period:.4f} vs {mean_normal:.4f}")
            print(f"  P-value: {p_val:.6f} {sig_mark}")
            print(f"  Disposição {direction} para pagar frete na data comemorativa")

def compare_seasonal_freight_willingness(df):
    """Compara disposição para pagar frete entre datas comemorativas"""
    print("\n" + "="*80)
    print("RANKING GERAL: QUAL DATA COMEMORATIVA TEM MAIOR DISPOSIÇÃO PARA PAGAR FRETE")
    print("="*80)
    
    seasonal_periods = ['dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal']
    
    # Dados apenas dos períodos sazonais
    seasonal_data = df[df['seasonal_period'].isin(seasonal_periods)]
    
    # Estatísticas gerais por período
    stats = seasonal_data.groupby('seasonal_period')['freight_ratio'].agg(['count', 'mean', 'std']).round(4)
    print("\nEstatísticas gerais de razão do frete:")
    print(stats)
    
    # Comparações par a par
    print(f"\nComparações par a par ({len(list(combinations(seasonal_periods, 2)))} testes):")
    
    results = {}
    for period1, period2 in combinations(seasonal_periods, 2):
        group1 = seasonal_data[seasonal_data['seasonal_period'] == period1]['freight_ratio']
        group2 = seasonal_data[seasonal_data['seasonal_period'] == period2]['freight_ratio']
        
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        mean1, mean2 = group1.mean(), group2.mean()
        winner = period1 if mean1 > mean2 else period2
        significant = p_val < 0.05
        
        results[(period1, period2)] = {
            'winner': winner,
            'significant': significant,
            'p_value': p_val
        }
        
        sig_mark = "***" if significant else "ns"
        print(f"{period1} vs {period2}: {mean1:.4f} vs {mean2:.4f}, p={p_val:.5f} {sig_mark} → {winner}")
    
    # Calcular ranking
    scores = {period: 0 for period in seasonal_periods}
    for (p1, p2), result in results.items():
        if result['significant']:
            scores[result['winner']] += 1
        else:
            scores[p1] += 0.5
            scores[p2] += 0.5
    
    # Ranking final
    period_means = seasonal_data.groupby('seasonal_period')['freight_ratio'].mean()
    ranking = sorted(seasonal_periods, key=lambda x: (scores[x], period_means[x]), reverse=True)
    
    print(f"\nRANKING FINAL DE DISPOSIÇÃO PARA PAGAR FRETE:")
    for i, period in enumerate(ranking, 1):
        print(f"{i}. {period} (pontos: {scores[period]:.1f}, razão frete: {period_means[period]:.4f})")

def create_seasonal_visualizations(df):
    """Cria visualizações para análise sazonal"""
    print("\n" + "="*80)
    print("CRIANDO VISUALIZAÇÕES SAZONAIS")
    print("="*80)
    
    # Gráfico 1: Ticket médio por categoria e período sazonal
    top_categories = df['product_category'].value_counts().head(6).index.tolist()
    df_viz = df[df['product_category'].isin(top_categories)]
    
    plt.figure(figsize=(16, 10))
    
    # Preparar dados para visualização
    seasonal_periods = ['normal', 'dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal']
    
    pivot_data = df_viz.groupby(['product_category', 'seasonal_period'])['order_ticket'].mean().unstack(fill_value=0)
    
    # Reordenar colunas
    pivot_data = pivot_data.reindex(columns=seasonal_periods, fill_value=0)
    
    # Heatmap
    plt.subplot(2, 2, 1)
    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd', cbar_kws={'label': 'Ticket Médio (R$)'})
    plt.title('Ticket Médio por Categoria e Período Sazonal')
    plt.xlabel('Período Sazonal')
    plt.ylabel('Categoria')
    
    # Gráfico 2: Razão do frete por região e período
    plt.subplot(2, 2, 2)
    regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
    freight_pivot = df.groupby(['region', 'seasonal_period'])['freight_ratio'].mean().unstack(fill_value=0)
    freight_pivot = freight_pivot.reindex(columns=seasonal_periods, fill_value=0)
    
    sns.heatmap(freight_pivot, annot=True, fmt='.3f', cmap='Blues', cbar_kws={'label': 'Razão Frete'})
    plt.title('Razão do Frete por Região e Período Sazonal')
    plt.xlabel('Período Sazonal')
    plt.ylabel('Região')
    
    # Gráfico 3: Boxplot ticket médio por período
    plt.subplot(2, 2, 3)
    seasonal_data = df[df['seasonal_period'].isin(['dia_das_maes', 'dia_dos_pais', 'dia_das_criancas', 'natal'])]
    sns.boxplot(data=seasonal_data, x='seasonal_period', y='order_ticket')
    plt.title('Distribuição do Ticket Médio por Data Comemorativa')
    plt.xlabel('Data Comemorativa')
    plt.ylabel('Ticket Médio (R$)')
    plt.xticks(rotation=45)
    
    # Gráfico 4: Boxplot razão frete por período
    plt.subplot(2, 2, 4)
    sns.boxplot(data=seasonal_data, x='seasonal_period', y='freight_ratio')
    plt.title('Distribuição da Razão do Frete por Data Comemorativa')
    plt.xlabel('Data Comemorativa')
    plt.ylabel('Razão do Frete')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig('charts/seasonal_analysis_comprehensive.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Visualização salva: charts/seasonal_analysis_comprehensive.png")

def main():
    """Função principal"""
    print("="*80)
    print("ANÁLISE DE SAZONALIDADE POR DATAS COMEMORATIVAS")
    print("="*80)
    
    # Carregar dados
    df = load_data()
    
    # Definir períodos sazonais
    df_seasonal = define_seasonal_periods(df)
    
    # Análise 1: Ticket médio por categoria em datas comemorativas
    ticket_results = analyze_ticket_by_category_and_season(df_seasonal)
    
    # Análise 2: Ranking de datas comemorativas por categoria
    compare_seasonal_periods_by_category(df_seasonal)
    
    # Análise 3: Disposição para pagar frete por região
    analyze_freight_willingness_by_season(df_seasonal)
    
    # Análise 4: Ranking geral de disposição para pagar frete
    compare_seasonal_freight_willingness(df_seasonal)
    
    # Criar visualizações
    create_seasonal_visualizations(df_seasonal)
    
    print("\n" + "="*80)
    print("ANÁLISE DE SAZONALIDADE CONCLUÍDA!")
    print("="*80)

if __name__ == "__main__":
    main() 