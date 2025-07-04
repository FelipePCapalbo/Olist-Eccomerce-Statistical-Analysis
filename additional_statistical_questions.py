import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import mannwhitneyu, kruskal, chi2_contingency, pearsonr, spearmanr
import os
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Carrega e prepara os dados para análise"""
    # Código similar ao anterior
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    orders_df = pd.read_csv('olist-csv/olist_orders_dataset.csv')
    customers_df = pd.read_csv('olist-csv/olist_customers_dataset.csv')
    payments_df = pd.read_csv('olist-csv/olist_order_payments_dataset.csv')
    
    # Merge e limpeza (código similar ao anterior)
    items_products = items_df.merge(products_df[['product_id', 'product_category_name']], on='product_id', how='left')
    items_products_trans = items_products.merge(translation_df, on='product_category_name', how='left')
    orders_customers = orders_df.merge(customers_df[['customer_id', 'customer_state']], on='customer_id', how='left')
    
    final_df = items_products_trans.merge(
        orders_customers[['order_id', 'customer_state', 'order_status', 'order_purchase_timestamp']], 
        on='order_id', how='left'
    )
    
    final_df = final_df[
        (final_df['order_status'] == 'delivered') &
        (final_df['price'] > 0) &
        (final_df['price'] <= 10000) &
        (final_df['freight_value'] >= 0) &
        (final_df['product_category_name_english'].notna()) &
        (final_df['customer_state'].notna())
    ]
    
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
    
    payments_summary = payments_df.groupby('order_id').agg({
        'payment_type': lambda x: x.mode().iloc[0],
        'payment_installments': 'mean',
        'payment_value': 'sum'
    }).reset_index()
    
    orders_summary = orders_summary.merge(payments_summary, on='order_id', how='left')
    
    # Variáveis temporais
    orders_summary['order_date'] = pd.to_datetime(orders_summary['order_date'])
    orders_summary['day_of_month'] = orders_summary['order_date'].dt.day
    orders_summary['day_of_week'] = orders_summary['order_date'].dt.dayofweek
    orders_summary['hour'] = orders_summary['order_date'].dt.hour
    orders_summary['month'] = orders_summary['order_date'].dt.month
    orders_summary['is_weekend'] = (orders_summary['day_of_week'] >= 5).astype(int)
    
    # Criar variáveis criativas
    orders_summary['high_ticket'] = (orders_summary['order_ticket'] > orders_summary['order_ticket'].quantile(0.75)).astype(int)
    orders_summary['high_freight'] = (orders_summary['freight_ratio'] > orders_summary['freight_ratio'].quantile(0.75)).astype(int)
    orders_summary['multiple_items'] = (orders_summary['n_items'] > 1).astype(int)
    
    # Classificar estados por região
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
    
    return orders_summary

def creative_question_1(df):
    """
    PERGUNTA CRIATIVA 1: Existe diferença no ticket médio entre regiões do Brasil?
    """
    print("\n" + "="*80)
    print("PERGUNTA CRIATIVA 1: Existe diferença no ticket médio entre regiões do Brasil?")
    print("="*80)
    
    # Estatísticas por região
    region_stats = df.groupby('region')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    
    print("\nESTATÍSTICAS POR REGIÃO:")
    print(region_stats)
    
    # Teste Kruskal-Wallis
    groups = [group['order_ticket'].values for name, group in df.groupby('region')]
    h_stat, p_value = kruskal(*groups)
    
    print(f"\nTESTE KRUSKAL-WALLIS:")
    print(f"Estatística: H = {h_stat:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe diferença significativa no ticket médio entre regiões"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa entre regiões"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='region', y='order_ticket')
    plt.title('Ticket Médio por Região do Brasil')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('charts/creative1_regions.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {'test': 'Kruskal-Wallis', 'p_value': p_value, 'conclusion': conclusion}

def creative_question_2(df):
    """
    PERGUNTA CRIATIVA 2: Pedidos com múltiplos itens têm maior ticket médio POR ITEM?
    """
    print("\n" + "="*80)
    print("PERGUNTA CRIATIVA 2: Pedidos com múltiplos itens têm maior ticket médio POR ITEM?")
    print("="*80)
    
    # Calcular ticket por item
    df['ticket_per_item'] = df['order_ticket'] / df['n_items']
    
    # Comparar single vs multiple items
    single_items = df[df['n_items'] == 1]['ticket_per_item']
    multiple_items = df[df['n_items'] > 1]['ticket_per_item']
    
    print(f"\nPedidos com 1 item: {len(single_items)} pedidos")
    print(f"Ticket médio por item: R$ {single_items.mean():.2f}")
    print(f"\nPedidos com múltiplos itens: {len(multiple_items)} pedidos")
    print(f"Ticket médio por item: R$ {multiple_items.mean():.2f}")
    
    # Teste Mann-Whitney U
    u_stat, p_value = mannwhitneyu(multiple_items, single_items, alternative='two-sided')
    
    print(f"\nTESTE MANN-WHITNEY U:")
    print(f"Estatística: U = {u_stat:.0f}")
    print(f"P-value: {p_value:.6f}")
    
    if p_value < 0.05:
        if multiple_items.mean() > single_items.mean():
            conclusion = "REJEITAR H₀: Pedidos múltiplos TÊM maior ticket por item (sem economia de escala)"
        else:
            conclusion = "REJEITAR H₀: Pedidos múltiplos TÊM menor ticket por item (há economia de escala)"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa no ticket por item"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    data_plot = pd.DataFrame({
        'Ticket_por_Item': list(single_items) + list(multiple_items),
        'Tipo': ['1 item'] * len(single_items) + ['Múltiplos'] * len(multiple_items)
    })
    sns.boxplot(data=data_plot, x='Tipo', y='Ticket_por_Item')
    plt.title('Ticket por Item: 1 item vs Múltiplos itens')
    plt.tight_layout()
    plt.savefig('charts/creative2_ticket_per_item.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {'test': 'Mann-Whitney U', 'p_value': p_value, 'conclusion': conclusion}

def creative_question_3(df):
    """
    PERGUNTA CRIATIVA 3: Pedidos de fim de semana têm ticket médio diferente?
    """
    print("\n" + "="*80)
    print("PERGUNTA CRIATIVA 3: Pedidos de fim de semana têm ticket médio diferente?")
    print("="*80)
    
    # Estatísticas por tipo de dia
    weekend_stats = df.groupby('is_weekend')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    weekend_stats.index = ['Semana', 'Fim de semana']
    
    print("\nESTATÍSTICAS POR TIPO DE DIA:")
    print(weekend_stats)
    
    # Teste Mann-Whitney U
    weekday = df[df['is_weekend'] == 0]['order_ticket']
    weekend = df[df['is_weekend'] == 1]['order_ticket']
    
    u_stat, p_value = mannwhitneyu(weekend, weekday, alternative='two-sided')
    
    print(f"\nTESTE MANN-WHITNEY U:")
    print(f"Estatística: U = {u_stat:.0f}")
    print(f"P-value: {p_value:.6f}")
    
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe diferença significativa entre semana e fim de semana"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa entre os períodos"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='is_weekend', y='order_ticket')
    plt.xticks([0, 1], ['Semana', 'Fim de semana'])
    plt.title('Ticket Médio: Semana vs Fim de semana')
    plt.tight_layout()
    plt.savefig('charts/creative3_weekend.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {'test': 'Mann-Whitney U', 'p_value': p_value, 'conclusion': conclusion}

def creative_question_4(df):
    """
    PERGUNTA CRIATIVA 4: Existe associação entre alto frete e múltiplos itens?
    """
    print("\n" + "="*80)
    print("PERGUNTA CRIATIVA 4: Existe associação entre alto frete e múltiplos itens?")
    print("="*80)
    
    # Tabela de contingência
    contingency_table = pd.crosstab(df['high_freight'], df['multiple_items'], 
                                   margins=True, margins_name="Total")
    contingency_table.index = ['Frete baixo', 'Frete alto', 'Total']
    contingency_table.columns = ['1 item', 'Múltiplos itens', 'Total']
    
    print("\nTABELA DE CONTINGÊNCIA:")
    print(contingency_table)
    
    # Teste Qui-quadrado
    chi2, p_value, dof, expected = chi2_contingency(contingency_table.iloc[:-1, :-1])
    
    print(f"\nTESTE QUI-QUADRADO:")
    print(f"Estatística: χ² = {chi2:.4f}")
    print(f"Graus de liberdade: {dof}")
    print(f"P-value: {p_value:.6f}")
    
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe associação significativa entre alto frete e múltiplos itens"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há associação significativa"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Calcular Cramér's V (medida de associação)
    n = contingency_table.iloc[:-1, :-1].sum().sum()
    cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 2)))
    print(f"Cramér's V: {cramers_v:.4f} (força da associação)")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    contingency_plot = contingency_table.iloc[:-1, :-1]
    sns.heatmap(contingency_plot, annot=True, fmt='d', cmap='Blues')
    plt.title('Associação: Alto Frete vs Múltiplos Itens')
    plt.tight_layout()
    plt.savefig('charts/creative4_freight_items_association.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {'test': 'Qui-quadrado', 'p_value': p_value, 'conclusion': conclusion, 'cramers_v': cramers_v}

def main():
    """Executa as perguntas criativas adicionais"""
    print("PERGUNTAS ESTATÍSTICAS CRIATIVAS ADICIONAIS")
    print("=" * 80)
    
    df = load_data()
    print(f"Dados carregados: {len(df)} pedidos")
    
    os.makedirs('charts', exist_ok=True)
    
    # Executar perguntas criativas
    results = []
    results.append(creative_question_1(df))
    results.append(creative_question_2(df))
    results.append(creative_question_3(df))
    results.append(creative_question_4(df))
    
    print("\n" + "="*80)
    print("RESUMO DAS PERGUNTAS CRIATIVAS")
    print("="*80)
    
    questions = [
        "Existe diferença no ticket médio entre regiões do Brasil?",
        "Pedidos com múltiplos itens têm maior ticket médio POR ITEM?",
        "Pedidos de fim de semana têm ticket médio diferente?",
        "Existe associação entre alto frete e múltiplos itens?"
    ]
    
    for i, (question, result) in enumerate(zip(questions, results), 1):
        print(f"\n{i}. {question}")
        print(f"   Teste: {result['test']}")
        print(f"   P-value: {result['p_value']:.6f}")
        print(f"   Conclusão: {result['conclusion']}")
        if 'cramers_v' in result:
            print(f"   Cramér's V: {result['cramers_v']:.4f}")

if __name__ == "__main__":
    main() 