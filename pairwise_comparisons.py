import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu, chi2_contingency
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Carrega e prepara os dados"""
    # Carregar datasets
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    orders_df = pd.read_csv('olist-csv/olist_orders_dataset.csv')
    customers_df = pd.read_csv('olist-csv/olist_customers_dataset.csv')
    payments_df = pd.read_csv('olist-csv/olist_order_payments_dataset.csv')
    
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
    
    # Adicionar dados de pagamento
    payments_summary = payments_df.groupby('order_id').agg({
        'payment_type': lambda x: x.mode().iloc[0],
        'payment_installments': 'mean',
        'payment_value': 'sum'
    }).reset_index()
    
    orders_summary = orders_summary.merge(payments_summary, on='order_id', how='left')
    
    # Criar variáveis temporais
    orders_summary['order_date'] = pd.to_datetime(orders_summary['order_date'])
    orders_summary['hour'] = orders_summary['order_date'].dt.hour
    
    # Criar faixas horárias
    orders_summary['time_slot'] = pd.cut(orders_summary['hour'], 
                                        bins=[-1, 5, 11, 17, 23], 
                                        labels=['Madrugada', 'Manhã', 'Tarde', 'Noite'])
    
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

def pairwise_comparison_states(df):
    """Comparação par a par entre estados"""
    print("="*80)
    print("ANÁLISE COMBINATÓRIA: COMPARAÇÃO PAR A PAR - ESTADOS")
    print("="*80)
    
    # Filtrar estados com amostra suficiente
    state_counts = df['customer_state'].value_counts()
    top_states = state_counts.head(8).index.tolist()
    df_states = df[df['customer_state'].isin(top_states)]
    
    # Calcular estatísticas descritivas
    stats = df_states.groupby('customer_state')['order_ticket'].agg(['count', 'mean', 'median', 'std']).round(2)
    print("\nEstatísticas descritivas por estado:")
    print(stats)
    
    # Matriz de comparações par a par
    results = {}
    p_values = {}
    
    print(f"\nRealizando {len(list(combinations(top_states, 2)))} comparações par a par...")
    
    for state1, state2 in combinations(top_states, 2):
        group1 = df_states[df_states['customer_state'] == state1]['order_ticket']
        group2 = df_states[df_states['customer_state'] == state2]['order_ticket']
        
        # Teste Mann-Whitney U
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        results[(state1, state2)] = {
            'mean1': group1.mean(),
            'mean2': group2.mean(),
            'p_value': p_val,
            'significant': p_val < 0.05,
            'winner': state1 if group1.mean() > group2.mean() else state2
        }
        
        p_values[(state1, state2)] = p_val
    
    # Criar ranking baseado nas comparações
    print("\nResultados das comparações par a par (α = 0,05):")
    print("Estado1 vs Estado2 | Média1 | Média2 | P-value | Significativo | Maior")
    print("-" * 75)
    
    for (state1, state2), result in results.items():
        sig_mark = "***" if result['significant'] else "ns"
        print(f"{state1:2} vs {state2:2} | {result['mean1']:6.2f} | {result['mean2']:6.2f} | {result['p_value']:7.5f} | {sig_mark:11} | {result['winner']}")
    
    # Construir ranking
    state_scores = {state: 0 for state in top_states}
    
    for (state1, state2), result in results.items():
        if result['significant']:
            if result['winner'] == state1:
                state_scores[state1] += 1
            else:
                state_scores[state2] += 1
        else:
            # Se não é significativo, ambos recebem 0.5 ponto
            state_scores[state1] += 0.5
            state_scores[state2] += 0.5
    
    # Ordenar por pontuação e média
    state_stats = df_states.groupby('customer_state')['order_ticket'].mean()
    ranking = sorted(top_states, key=lambda x: (state_scores[x], state_stats[x]), reverse=True)
    
    print(f"\nRANKING FINAL DOS ESTADOS (baseado em {len(list(combinations(top_states, 2)))} comparações):")
    print("Posição | Estado | Pontuação | Média (R$) | Interpretação")
    print("-" * 60)
    
    for i, state in enumerate(ranking, 1):
        interpretation = "Maior ticket" if i <= 2 else "Intermediário" if i <= 6 else "Menor ticket"
        print(f"{i:7} | {state:6} | {state_scores[state]:9.1f} | {state_stats[state]:10.2f} | {interpretation}")
    
    return ranking, results

def pairwise_comparison_payment_types(df):
    """Comparação par a par entre tipos de pagamento"""
    print("\n" + "="*80)
    print("ANÁLISE COMBINATÓRIA: COMPARAÇÃO PAR A PAR - TIPOS DE PAGAMENTO")
    print("="*80)
    
    # Filtrar tipos de pagamento principais
    payment_counts = df['payment_type'].value_counts()
    top_payments = payment_counts.head(4).index.tolist()
    df_payments = df[df['payment_type'].isin(top_payments)]
    
    # Calcular estatísticas descritivas
    stats = df_payments.groupby('payment_type')['order_ticket'].agg(['count', 'mean', 'median', 'std']).round(2)
    print("\nEstatísticas descritivas por tipo de pagamento:")
    print(stats)
    
    # Matriz de comparações par a par
    results = {}
    
    print(f"\nRealizando {len(list(combinations(top_payments, 2)))} comparações par a par...")
    
    for pay1, pay2 in combinations(top_payments, 2):
        group1 = df_payments[df_payments['payment_type'] == pay1]['order_ticket']
        group2 = df_payments[df_payments['payment_type'] == pay2]['order_ticket']
        
        # Teste Mann-Whitney U
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        results[(pay1, pay2)] = {
            'mean1': group1.mean(),
            'mean2': group2.mean(),
            'p_value': p_val,
            'significant': p_val < 0.05,
            'winner': pay1 if group1.mean() > group2.mean() else pay2
        }
    
    # Mostrar resultados
    print("\nResultados das comparações par a par (α = 0,05):")
    print("Pagamento1 vs Pagamento2 | Média1 | Média2 | P-value | Significativo | Maior")
    print("-" * 85)
    
    for (pay1, pay2), result in results.items():
        sig_mark = "***" if result['significant'] else "ns"
        print(f"{pay1:11} vs {pay2:11} | {result['mean1']:6.2f} | {result['mean2']:6.2f} | {result['p_value']:7.5f} | {sig_mark:11} | {result['winner']}")
    
    # Construir ranking
    payment_scores = {pay: 0 for pay in top_payments}
    
    for (pay1, pay2), result in results.items():
        if result['significant']:
            if result['winner'] == pay1:
                payment_scores[pay1] += 1
            else:
                payment_scores[pay2] += 1
        else:
            payment_scores[pay1] += 0.5
            payment_scores[pay2] += 0.5
    
    # Ordenar por pontuação e média
    payment_stats = df_payments.groupby('payment_type')['order_ticket'].mean()
    ranking = sorted(top_payments, key=lambda x: (payment_scores[x], payment_stats[x]), reverse=True)
    
    print(f"\nRANKING FINAL DOS TIPOS DE PAGAMENTO:")
    print("Posição | Tipo Pagamento | Pontuação | Média (R$) | Interpretação")
    print("-" * 70)
    
    for i, pay in enumerate(ranking, 1):
        interpretation = "Maior ticket" if i == 1 else "Intermediário" if i <= 3 else "Menor ticket"
        print(f"{i:7} | {pay:14} | {payment_scores[pay]:9.1f} | {payment_stats[pay]:10.2f} | {interpretation}")
    
    return ranking, results

def pairwise_comparison_time_slots(df):
    """Comparação par a par entre faixas horárias"""
    print("\n" + "="*80)
    print("ANÁLISE COMBINATÓRIA: COMPARAÇÃO PAR A PAR - FAIXAS HORÁRIAS")
    print("="*80)
    
    # Remover valores nulos
    df_time = df.dropna(subset=['time_slot'])
    
    # Calcular estatísticas descritivas
    stats = df_time.groupby('time_slot')['order_ticket'].agg(['count', 'mean', 'median', 'std']).round(2)
    print("\nEstatísticas descritivas por faixa horária:")
    print(stats)
    
    # Lista das faixas horárias
    time_slots = ['Madrugada', 'Manhã', 'Tarde', 'Noite']
    
    # Matriz de comparações par a par
    results = {}
    
    print(f"\nRealizando {len(list(combinations(time_slots, 2)))} comparações par a par...")
    
    for slot1, slot2 in combinations(time_slots, 2):
        group1 = df_time[df_time['time_slot'] == slot1]['order_ticket']
        group2 = df_time[df_time['time_slot'] == slot2]['order_ticket']
        
        # Teste Mann-Whitney U
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        results[(slot1, slot2)] = {
            'mean1': group1.mean(),
            'mean2': group2.mean(),
            'p_value': p_val,
            'significant': p_val < 0.05,
            'winner': slot1 if group1.mean() > group2.mean() else slot2
        }
    
    # Mostrar resultados
    print("\nResultados das comparações par a par (α = 0,05):")
    print("Faixa1 vs Faixa2 | Média1 | Média2 | P-value | Significativo | Maior")
    print("-" * 75)
    
    for (slot1, slot2), result in results.items():
        sig_mark = "***" if result['significant'] else "ns"
        print(f"{slot1:9} vs {slot2:9} | {result['mean1']:6.2f} | {result['mean2']:6.2f} | {result['p_value']:7.5f} | {sig_mark:11} | {result['winner']}")
    
    # Construir ranking
    slot_scores = {slot: 0 for slot in time_slots}
    
    for (slot1, slot2), result in results.items():
        if result['significant']:
            if result['winner'] == slot1:
                slot_scores[slot1] += 1
            else:
                slot_scores[slot2] += 1
        else:
            slot_scores[slot1] += 0.5
            slot_scores[slot2] += 0.5
    
    # Ordenar por pontuação e média
    slot_stats = df_time.groupby('time_slot')['order_ticket'].mean()
    ranking = sorted(time_slots, key=lambda x: (slot_scores[x], slot_stats[x]), reverse=True)
    
    print(f"\nRANKING FINAL DAS FAIXAS HORÁRIAS:")
    print("Posição | Faixa Horária | Pontuação | Média (R$) | Interpretação")
    print("-" * 70)
    
    for i, slot in enumerate(ranking, 1):
        interpretation = "Maior ticket" if i == 1 else "Intermediário" if i <= 3 else "Menor ticket"
        print(f"{i:7} | {slot:13} | {slot_scores[slot]:9.1f} | {slot_stats[slot]:10.2f} | {interpretation}")
    
    return ranking, results

def pairwise_comparison_regions(df):
    """Comparação par a par entre regiões"""
    print("\n" + "="*80)
    print("ANÁLISE COMBINATÓRIA: COMPARAÇÃO PAR A PAR - REGIÕES")
    print("="*80)
    
    # Calcular estatísticas descritivas
    stats = df.groupby('region')['order_ticket'].agg(['count', 'mean', 'median', 'std']).round(2)
    print("\nEstatísticas descritivas por região:")
    print(stats)
    
    # Lista das regiões
    regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
    
    # Matriz de comparações par a par
    results = {}
    
    print(f"\nRealizando {len(list(combinations(regions, 2)))} comparações par a par...")
    
    for reg1, reg2 in combinations(regions, 2):
        group1 = df[df['region'] == reg1]['order_ticket']
        group2 = df[df['region'] == reg2]['order_ticket']
        
        # Teste Mann-Whitney U
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        results[(reg1, reg2)] = {
            'mean1': group1.mean(),
            'mean2': group2.mean(),
            'p_value': p_val,
            'significant': p_val < 0.05,
            'winner': reg1 if group1.mean() > group2.mean() else reg2
        }
    
    # Mostrar resultados
    print("\nResultados das comparações par a par (α = 0,05):")
    print("Região1 vs Região2 | Média1 | Média2 | P-value | Significativo | Maior")
    print("-" * 80)
    
    for (reg1, reg2), result in results.items():
        sig_mark = "***" if result['significant'] else "ns"
        print(f"{reg1:12} vs {reg2:12} | {result['mean1']:6.2f} | {result['mean2']:6.2f} | {result['p_value']:7.5f} | {sig_mark:11} | {result['winner']}")
    
    # Construir ranking
    region_scores = {reg: 0 for reg in regions}
    
    for (reg1, reg2), result in results.items():
        if result['significant']:
            if result['winner'] == reg1:
                region_scores[reg1] += 1
            else:
                region_scores[reg2] += 1
        else:
            region_scores[reg1] += 0.5
            region_scores[reg2] += 0.5
    
    # Ordenar por pontuação e média
    region_stats = df.groupby('region')['order_ticket'].mean()
    ranking = sorted(regions, key=lambda x: (region_scores[x], region_stats[x]), reverse=True)
    
    print(f"\nRANKING FINAL DAS REGIÕES:")
    print("Posição | Região       | Pontuação | Média (R$) | Interpretação")
    print("-" * 70)
    
    for i, reg in enumerate(ranking, 1):
        interpretation = "Maior ticket" if i == 1 else "Intermediário" if i <= 3 else "Menor ticket"
        print(f"{i:7} | {reg:12} | {region_scores[reg]:9.1f} | {region_stats[reg]:10.2f} | {interpretation}")
    
    return ranking, results

def main():
    """Função principal"""
    print("Carregando dados...")
    df = load_data()
    print(f"Dados carregados: {len(df)} pedidos")
    
    # Realizar todas as análises combinatórias
    state_ranking, state_results = pairwise_comparison_states(df)
    payment_ranking, payment_results = pairwise_comparison_payment_types(df)
    time_ranking, time_results = pairwise_comparison_time_slots(df)
    region_ranking, region_results = pairwise_comparison_regions(df)
    
    # Salvar resultados em arquivo
    with open('pairwise_analysis_results.txt', 'w') as f:
        f.write("RESULTADOS DA ANÁLISE COMBINATÓRIA - COMPARAÇÕES PAR A PAR\n")
        f.write("="*80 + "\n\n")
        
        f.write("RANKING ESTADOS:\n")
        for i, state in enumerate(state_ranking, 1):
            f.write(f"{i}. {state}\n")
        
        f.write("\nRANKING TIPOS DE PAGAMENTO:\n")
        for i, pay in enumerate(payment_ranking, 1):
            f.write(f"{i}. {pay}\n")
        
        f.write("\nRANKING FAIXAS HORÁRIAS:\n")
        for i, slot in enumerate(time_ranking, 1):
            f.write(f"{i}. {slot}\n")
        
        f.write("\nRANKING REGIÕES:\n")
        for i, reg in enumerate(region_ranking, 1):
            f.write(f"{i}. {reg}\n")
    
    print("\n" + "="*80)
    print("ANÁLISE COMBINATÓRIA CONCLUÍDA!")
    print("Resultados salvos em: pairwise_analysis_results.txt")
    print("="*80)

if __name__ == "__main__":
    main() 