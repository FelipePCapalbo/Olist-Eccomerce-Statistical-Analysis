import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu
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
    
    # Adicionar dados de pagamento
    payments_summary = payments_df.groupby('order_id').agg({
        'payment_type': lambda x: x.mode().iloc[0]
    }).reset_index()
    
    orders_summary = orders_summary.merge(payments_summary, on='order_id', how='left')
    
    # Criar variáveis temporais
    orders_summary['order_date'] = pd.to_datetime(orders_summary['order_date'])
    orders_summary['hour'] = orders_summary['order_date'].dt.hour
    
    # Criar faixas horárias
    orders_summary['time_slot'] = pd.cut(orders_summary['hour'], 
                                        bins=[-1, 5, 11, 17, 23], 
                                        labels=['Madrugada', 'Manhã', 'Tarde', 'Noite'])
    
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
    
    return orders_summary

def pairwise_states(df):
    """Análise combinatória para estados"""
    print("ANÁLISE COMBINATÓRIA: ESTADOS")
    print("="*50)
    
    # Top 8 estados
    top_states = df['customer_state'].value_counts().head(8).index.tolist()
    df_states = df[df['customer_state'].isin(top_states)]
    
    # Estatísticas
    stats = df_states.groupby('customer_state')['order_ticket'].agg(['count', 'mean']).round(2)
    print("\nEstatísticas por estado:")
    for state in top_states:
        mean_val = stats.loc[state, 'mean']
        count_val = stats.loc[state, 'count']
        print(f"{state}: {mean_val:.2f} (n={count_val})")
    
    # Comparações par a par
    print(f"\nComparações par a par ({len(list(combinations(top_states, 2)))} testes):")
    
    results = {}
    for state1, state2 in combinations(top_states, 2):
        group1 = df_states[df_states['customer_state'] == state1]['order_ticket']
        group2 = df_states[df_states['customer_state'] == state2]['order_ticket']
        
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        mean1, mean2 = group1.mean(), group2.mean()
        winner = state1 if mean1 > mean2 else state2
        significant = p_val < 0.05
        
        results[(state1, state2)] = {
            'winner': winner,
            'significant': significant,
            'p_value': p_val,
            'mean1': mean1,
            'mean2': mean2
        }
        
        sig_mark = "***" if significant else "ns"
        print(f"{state1} vs {state2}: {mean1:.2f} vs {mean2:.2f}, p={p_val:.5f} {sig_mark} → {winner}")
    
    # Calcular ranking
    scores = {state: 0 for state in top_states}
    for (s1, s2), result in results.items():
        if result['significant']:
            scores[result['winner']] += 1
        else:
            scores[s1] += 0.5
            scores[s2] += 0.5
    
    # Ranking final
    state_means = df_states.groupby('customer_state')['order_ticket'].mean()
    ranking = sorted(top_states, key=lambda x: (scores[x], state_means[x]), reverse=True)
    
    print(f"\nRANKING FINAL:")
    for i, state in enumerate(ranking, 1):
        print(f"{i}. {state} (pontos: {scores[state]:.1f}, média: {state_means[state]:.2f})")
    
    return ranking

def pairwise_payments(df):
    """Análise combinatória para tipos de pagamento"""
    print("\n" + "="*50)
    print("ANÁLISE COMBINATÓRIA: TIPOS DE PAGAMENTO")
    print("="*50)
    
    # Top 4 tipos de pagamento
    top_payments = df['payment_type'].value_counts().head(4).index.tolist()
    df_payments = df[df['payment_type'].isin(top_payments)]
    
    # Estatísticas
    stats = df_payments.groupby('payment_type')['order_ticket'].agg(['count', 'mean']).round(2)
    print("\nEstatísticas por tipo de pagamento:")
    for payment in top_payments:
        mean_val = stats.loc[payment, 'mean']
        count_val = stats.loc[payment, 'count']
        print(f"{payment}: {mean_val:.2f} (n={count_val})")
    
    # Comparações par a par
    print(f"\nComparações par a par ({len(list(combinations(top_payments, 2)))} testes):")
    
    results = {}
    for pay1, pay2 in combinations(top_payments, 2):
        group1 = df_payments[df_payments['payment_type'] == pay1]['order_ticket']
        group2 = df_payments[df_payments['payment_type'] == pay2]['order_ticket']
        
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        mean1, mean2 = group1.mean(), group2.mean()
        winner = pay1 if mean1 > mean2 else pay2
        significant = p_val < 0.05
        
        results[(pay1, pay2)] = {
            'winner': winner,
            'significant': significant,
            'p_value': p_val
        }
        
        sig_mark = "***" if significant else "ns"
        print(f"{pay1} vs {pay2}: {mean1:.2f} vs {mean2:.2f}, p={p_val:.5f} {sig_mark} → {winner}")
    
    # Calcular ranking
    scores = {pay: 0 for pay in top_payments}
    for (p1, p2), result in results.items():
        if result['significant']:
            scores[result['winner']] += 1
        else:
            scores[p1] += 0.5
            scores[p2] += 0.5
    
    # Ranking final
    payment_means = df_payments.groupby('payment_type')['order_ticket'].mean()
    ranking = sorted(top_payments, key=lambda x: (scores[x], payment_means[x]), reverse=True)
    
    print(f"\nRANKING FINAL:")
    for i, payment in enumerate(ranking, 1):
        print(f"{i}. {payment} (pontos: {scores[payment]:.1f}, média: {payment_means[payment]:.2f})")
    
    return ranking

def pairwise_time_slots(df):
    """Análise combinatória para faixas horárias"""
    print("\n" + "="*50)
    print("ANÁLISE COMBINATÓRIA: FAIXAS HORÁRIAS")
    print("="*50)
    
    df_time = df.dropna(subset=['time_slot'])
    time_slots = ['Madrugada', 'Manhã', 'Tarde', 'Noite']
    
    # Estatísticas
    stats = df_time.groupby('time_slot')['order_ticket'].agg(['count', 'mean']).round(2)
    print("\nEstatísticas por faixa horária:")
    for slot in time_slots:
        mean_val = stats.loc[slot, 'mean']
        count_val = stats.loc[slot, 'count']
        print(f"{slot}: {mean_val:.2f} (n={count_val})")
    
    # Comparações par a par
    print(f"\nComparações par a par ({len(list(combinations(time_slots, 2)))} testes):")
    
    results = {}
    for slot1, slot2 in combinations(time_slots, 2):
        group1 = df_time[df_time['time_slot'] == slot1]['order_ticket']
        group2 = df_time[df_time['time_slot'] == slot2]['order_ticket']
        
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        mean1, mean2 = group1.mean(), group2.mean()
        winner = slot1 if mean1 > mean2 else slot2
        significant = p_val < 0.05
        
        results[(slot1, slot2)] = {
            'winner': winner,
            'significant': significant,
            'p_value': p_val
        }
        
        sig_mark = "***" if significant else "ns"
        print(f"{slot1} vs {slot2}: {mean1:.2f} vs {mean2:.2f}, p={p_val:.5f} {sig_mark} → {winner}")
    
    # Calcular ranking
    scores = {slot: 0 for slot in time_slots}
    for (s1, s2), result in results.items():
        if result['significant']:
            scores[result['winner']] += 1
        else:
            scores[s1] += 0.5
            scores[s2] += 0.5
    
    # Ranking final
    slot_means = df_time.groupby('time_slot')['order_ticket'].mean()
    ranking = sorted(time_slots, key=lambda x: (scores[x], slot_means[x]), reverse=True)
    
    print(f"\nRANKING FINAL:")
    for i, slot in enumerate(ranking, 1):
        print(f"{i}. {slot} (pontos: {scores[slot]:.1f}, média: {slot_means[slot]:.2f})")
    
    return ranking

def pairwise_regions(df):
    """Análise combinatória para regiões"""
    print("\n" + "="*50)
    print("ANÁLISE COMBINATÓRIA: REGIÕES")
    print("="*50)
    
    regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
    
    # Estatísticas
    stats = df.groupby('region')['order_ticket'].agg(['count', 'mean']).round(2)
    print("\nEstatísticas por região:")
    for region in regions:
        mean_val = stats.loc[region, 'mean']
        count_val = stats.loc[region, 'count']
        print(f"{region}: {mean_val:.2f} (n={count_val})")
    
    # Comparações par a par
    print(f"\nComparações par a par ({len(list(combinations(regions, 2)))} testes):")
    
    results = {}
    for reg1, reg2 in combinations(regions, 2):
        group1 = df[df['region'] == reg1]['order_ticket']
        group2 = df[df['region'] == reg2]['order_ticket']
        
        u_stat, p_val = mannwhitneyu(group1, group2, alternative='two-sided')
        
        mean1, mean2 = group1.mean(), group2.mean()
        winner = reg1 if mean1 > mean2 else reg2
        significant = p_val < 0.05
        
        results[(reg1, reg2)] = {
            'winner': winner,
            'significant': significant,
            'p_value': p_val
        }
        
        sig_mark = "***" if significant else "ns"
        print(f"{reg1} vs {reg2}: {mean1:.2f} vs {mean2:.2f}, p={p_val:.5f} {sig_mark} → {winner}")
    
    # Calcular ranking
    scores = {reg: 0 for reg in regions}
    for (r1, r2), result in results.items():
        if result['significant']:
            scores[result['winner']] += 1
        else:
            scores[r1] += 0.5
            scores[r2] += 0.5
    
    # Ranking final
    region_means = df.groupby('region')['order_ticket'].mean()
    ranking = sorted(regions, key=lambda x: (scores[x], region_means[x]), reverse=True)
    
    print(f"\nRANKING FINAL:")
    for i, region in enumerate(ranking, 1):
        print(f"{i}. {region} (pontos: {scores[region]:.1f}, média: {region_means[region]:.2f})")
    
    return ranking

def main():
    print("Carregando dados...")
    df = load_data()
    print(f"Dados carregados: {len(df)} pedidos\n")
    
    # Realizar análises combinatórias
    state_ranking = pairwise_states(df)
    payment_ranking = pairwise_payments(df)
    time_ranking = pairwise_time_slots(df)
    region_ranking = pairwise_regions(df)
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DOS RANKINGS FINAIS")
    print("="*60)
    
    print("\nESTADOS:")
    for i, state in enumerate(state_ranking, 1):
        print(f"{i}. {state}")
    
    print("\nTIPOS DE PAGAMENTO:")
    for i, payment in enumerate(payment_ranking, 1):
        print(f"{i}. {payment}")
    
    print("\nFAIXAS HORÁRIAS:")
    for i, slot in enumerate(time_ranking, 1):
        print(f"{i}. {slot}")
    
    print("\nREGIÕES:")
    for i, region in enumerate(region_ranking, 1):
        print(f"{i}. {region}")

if __name__ == "__main__":
    main() 