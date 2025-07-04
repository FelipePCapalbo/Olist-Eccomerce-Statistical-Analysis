import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import mannwhitneyu, kruskal, chi2_contingency, pearsonr, spearmanr
from scipy.stats import shapiro, normaltest, anderson, jarque_bera
import os
import warnings
warnings.filterwarnings('ignore')

# Configuração de visualização
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

def load_data():
    """Carrega e prepara os dados para análise"""
    print("Carregando dados...")
    
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
    
    # Merge final
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
    orders_summary['day_of_month'] = orders_summary['order_date'].dt.day
    orders_summary['day_of_week'] = orders_summary['order_date'].dt.dayofweek
    orders_summary['hour'] = orders_summary['order_date'].dt.hour
    orders_summary['month'] = orders_summary['order_date'].dt.month
    
    # Criar variável pós-salário (dias 5-9 do mês)
    orders_summary['post_salary'] = ((orders_summary['day_of_month'] >= 5) & 
                                    (orders_summary['day_of_month'] <= 9)).astype(int)
    
    # Criar faixas horárias
    orders_summary['time_slot'] = pd.cut(orders_summary['hour'], 
                                        bins=[-1, 5, 11, 17, 23], 
                                        labels=['Madrugada', 'Manhã', 'Tarde', 'Noite'])
    
    print(f"Dados carregados: {len(orders_summary)} pedidos")
    return orders_summary

def test_normality(data, variable_name):
    """Testa normalidade dos dados"""
    # Remover valores NaN
    clean_data = data.dropna()
    
    if len(clean_data) < 3:
        return "Amostra insuficiente", False
    
    # Usar amostra menor se dataset muito grande (para Shapiro-Wilk)
    if len(clean_data) > 5000:
        sample_data = clean_data.sample(5000, random_state=42)
    else:
        sample_data = clean_data
    
    # Teste de Shapiro-Wilk
    try:
        stat, p_value = shapiro(sample_data)
        is_normal = p_value > 0.05
        return f"Shapiro-Wilk: p-value = {p_value:.6f}", is_normal
    except:
        # Teste alternativo se Shapiro falhar
        stat, p_value = normaltest(sample_data)
        is_normal = p_value > 0.05
        return f"D'Agostino-Pearson: p-value = {p_value:.6f}", is_normal

def statistical_question_1(df):
    """
    PERGUNTA 1: Existe diferença significativa no ticket médio entre os estados?
    """
    print("\n" + "="*80)
    print("PERGUNTA 1: Existe diferença significativa no ticket médio entre os estados?")
    print("="*80)
    
    # Filtrar estados com amostra suficiente
    state_counts = df['customer_state'].value_counts()
    top_states = state_counts.head(8).index.tolist()
    df_states = df[df['customer_state'].isin(top_states)]
    
    # Estatísticas descritivas por estado
    print("\nESTATÍSTICAS DESCRITIVAS POR ESTADO:")
    state_stats = df_states.groupby('customer_state')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    print(state_stats)
    
    # Teste de normalidade
    print("\nTESTE DE NORMALIDADE:")
    norm_result, is_normal = test_normality(df_states['order_ticket'], 'order_ticket')
    print(f"Ticket médio: {norm_result}")
    
    # Escolher teste apropriado
    if is_normal:
        print("\nUSANDO ANOVA (dados normais):")
        groups = [group['order_ticket'].values for name, group in df_states.groupby('customer_state')]
        f_stat, p_value = stats.f_oneway(*groups)
        test_name = "ANOVA"
        stat_value = f_stat
    else:
        print("\nUSANDO KRUSKAL-WALLIS (dados não-normais):")
        groups = [group['order_ticket'].values for name, group in df_states.groupby('customer_state')]
        h_stat, p_value = kruskal(*groups)
        test_name = "Kruskal-Wallis"
        stat_value = h_stat
    
    print(f"Estatística do teste: {stat_value:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe diferença significativa no ticket médio entre estados"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa no ticket médio entre estados"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df_states, x='customer_state', y='order_ticket')
    plt.title('Distribuição do Ticket Médio por Estado')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('charts/question1_ticket_by_state.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'Existe diferença significativa no ticket médio entre os estados?',
        'test_used': test_name,
        'p_value': p_value,
        'conclusion': conclusion,
        'states_analyzed': len(top_states)
    }

def statistical_question_2(df):
    """
    PERGUNTA 2: Pedidos feitos após o dia de pagamento (5-9 do mês) têm ticket médio maior?
    """
    print("\n" + "="*80)
    print("PERGUNTA 2: Pedidos feitos após o dia de pagamento (5-9 do mês) têm ticket médio maior?")
    print("="*80)
    
    # Estatísticas descritivas
    print("\nESTATÍSTICAS DESCRITIVAS:")
    salary_stats = df.groupby('post_salary')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    salary_stats.index = ['Outros dias', 'Pós-salário (5-9)']
    print(salary_stats)
    
    # Teste de normalidade por grupo
    print("\nTESTE DE NORMALIDADE POR GRUPO:")
    group_0 = df[df['post_salary'] == 0]['order_ticket']
    group_1 = df[df['post_salary'] == 1]['order_ticket']
    
    norm_0, is_normal_0 = test_normality(group_0, 'outros_dias')
    norm_1, is_normal_1 = test_normality(group_1, 'pos_salario')
    
    print(f"Outros dias: {norm_0}")
    print(f"Pós-salário: {norm_1}")
    
    # Escolher teste apropriado
    if is_normal_0 and is_normal_1:
        print("\nUSANDO TESTE T (dados normais):")
        t_stat, p_value = stats.ttest_ind(group_1, group_0)
        test_name = "Teste t"
    else:
        print("\nUSANDO MANN-WHITNEY U (dados não-normais):")
        u_stat, p_value = mannwhitneyu(group_1, group_0, alternative='two-sided')
        test_name = "Mann-Whitney U"
    
    print(f"Estatística do teste: {u_stat if not (is_normal_0 and is_normal_1) else t_stat:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe diferença significativa no ticket médio entre períodos"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa no ticket médio entre períodos"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='post_salary', y='order_ticket')
    plt.xticks([0, 1], ['Outros dias', 'Pós-salário (5-9)'])
    plt.title('Ticket Médio: Outros dias vs Pós-salário')
    plt.tight_layout()
    plt.savefig('charts/question2_salary_effect.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'Pedidos feitos após o dia de pagamento têm ticket médio maior?',
        'test_used': test_name,
        'p_value': p_value,
        'conclusion': conclusion
    }

def statistical_question_3(df):
    """
    PERGUNTA 3: Existe correlação entre quantidade de itens e ticket médio?
    """
    print("\n" + "="*80)
    print("PERGUNTA 3: Existe correlação entre quantidade de itens e ticket médio?")
    print("="*80)
    
    # Remover outliers extremos para correlação
    df_clean = df[(df['n_items'] <= 10) & (df['order_ticket'] <= 1000)]
    
    # Estatísticas descritivas
    print(f"\nDados para análise: {len(df_clean)} pedidos")
    print(f"Quantidade de itens - Média: {df_clean['n_items'].mean():.2f}, Mediana: {df_clean['n_items'].median():.2f}")
    print(f"Ticket médio - Média: R$ {df_clean['order_ticket'].mean():.2f}, Mediana: R$ {df_clean['order_ticket'].median():.2f}")
    
    # Teste de normalidade
    print("\nTESTE DE NORMALIDADE:")
    norm_items, is_normal_items = test_normality(df_clean['n_items'], 'n_items')
    norm_ticket, is_normal_ticket = test_normality(df_clean['order_ticket'], 'order_ticket')
    
    print(f"Quantidade de itens: {norm_items}")
    print(f"Ticket médio: {norm_ticket}")
    
    # Escolher correlação apropriada
    if is_normal_items and is_normal_ticket:
        print("\nUSANDO CORRELAÇÃO DE PEARSON (dados normais):")
        corr_coef, p_value = pearsonr(df_clean['n_items'], df_clean['order_ticket'])
        corr_type = "Pearson"
    else:
        print("\nUSANDO CORRELAÇÃO DE SPEARMAN (dados não-normais):")
        corr_coef, p_value = spearmanr(df_clean['n_items'], df_clean['order_ticket'])
        corr_type = "Spearman"
    
    print(f"Coeficiente de correlação: {corr_coef:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação da força da correlação
    if abs(corr_coef) < 0.1:
        strength = "muito fraca"
    elif abs(corr_coef) < 0.3:
        strength = "fraca"
    elif abs(corr_coef) < 0.5:
        strength = "moderada"
    elif abs(corr_coef) < 0.7:
        strength = "forte"
    else:
        strength = "muito forte"
    
    direction = "positiva" if corr_coef > 0 else "negativa"
    
    if p_value < 0.05:
        conclusion = f"REJEITAR H₀: Existe correlação {strength} {direction} significativa (r={corr_coef:.4f})"
    else:
        conclusion = f"NÃO REJEITAR H₀: Não há correlação significativa"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    plt.scatter(df_clean['n_items'], df_clean['order_ticket'], alpha=0.1)
    plt.xlabel('Quantidade de Itens')
    plt.ylabel('Ticket Médio (R$)')
    plt.title(f'Correlação entre Quantidade de Itens e Ticket Médio\n{corr_type}: r={corr_coef:.4f}, p={p_value:.6f}')
    
    # Linha de tendência
    z = np.polyfit(df_clean['n_items'], df_clean['order_ticket'], 1)
    p = np.poly1d(z)
    plt.plot(df_clean['n_items'], p(df_clean['n_items']), "r--", alpha=0.8)
    
    plt.tight_layout()
    plt.savefig('charts/question3_items_correlation.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'Existe correlação entre quantidade de itens e ticket médio?',
        'test_used': f'Correlação de {corr_type}',
        'correlation': corr_coef,
        'p_value': p_value,
        'conclusion': conclusion
    }

def statistical_question_4(df):
    """
    PERGUNTA 4: O tipo de pagamento influencia o ticket médio?
    """
    print("\n" + "="*80)
    print("PERGUNTA 4: O tipo de pagamento influencia o ticket médio?")
    print("="*80)
    
    # Filtrar tipos de pagamento mais comuns
    payment_counts = df['payment_type'].value_counts()
    top_payments = payment_counts.head(4).index.tolist()
    df_payments = df[df['payment_type'].isin(top_payments)]
    
    # Estatísticas descritivas
    print("\nESTATÍSTICAS DESCRITIVAS POR TIPO DE PAGAMENTO:")
    payment_stats = df_payments.groupby('payment_type')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    print(payment_stats)
    
    # Teste de normalidade
    print("\nTESTE DE NORMALIDADE:")
    norm_result, is_normal = test_normality(df_payments['order_ticket'], 'order_ticket')
    print(f"Ticket médio: {norm_result}")
    
    # Escolher teste apropriado
    if is_normal:
        print("\nUSANDO ANOVA (dados normais):")
        groups = [group['order_ticket'].values for name, group in df_payments.groupby('payment_type')]
        f_stat, p_value = stats.f_oneway(*groups)
        test_name = "ANOVA"
    else:
        print("\nUSANDO KRUSKAL-WALLIS (dados não-normais):")
        groups = [group['order_ticket'].values for name, group in df_payments.groupby('payment_type')]
        h_stat, p_value = kruskal(*groups)
        test_name = "Kruskal-Wallis"
    
    print(f"Estatística do teste: {h_stat if not is_normal else f_stat:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: O tipo de pagamento influencia significativamente o ticket médio"
    else:
        conclusion = "NÃO REJEITAR H₀: O tipo de pagamento não influencia significativamente o ticket médio"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df_payments, x='payment_type', y='order_ticket')
    plt.title('Distribuição do Ticket Médio por Tipo de Pagamento')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('charts/question4_payment_type.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'O tipo de pagamento influencia o ticket médio?',
        'test_used': test_name,
        'p_value': p_value,
        'conclusion': conclusion
    }

def statistical_question_5(df):
    """
    PERGUNTA 5: Existe diferença no ticket médio entre faixas horárias?
    """
    print("\n" + "="*80)
    print("PERGUNTA 5: Existe diferença no ticket médio entre faixas horárias?")
    print("="*80)
    
    # Remover NaN em time_slot
    df_time = df.dropna(subset=['time_slot'])
    
    # Estatísticas descritivas
    print("\nESTATÍSTICAS DESCRITIVAS POR FAIXA HORÁRIA:")
    time_stats = df_time.groupby('time_slot')['order_ticket'].agg([
        'count', 'mean', 'std', 'median'
    ]).round(2)
    print(time_stats)
    
    # Teste de normalidade
    print("\nTESTE DE NORMALIDADE:")
    norm_result, is_normal = test_normality(df_time['order_ticket'], 'order_ticket')
    print(f"Ticket médio: {norm_result}")
    
    # Escolher teste apropriado
    if is_normal:
        print("\nUSANDO ANOVA (dados normais):")
        groups = [group['order_ticket'].values for name, group in df_time.groupby('time_slot')]
        f_stat, p_value = stats.f_oneway(*groups)
        test_name = "ANOVA"
    else:
        print("\nUSANDO KRUSKAL-WALLIS (dados não-normais):")
        groups = [group['order_ticket'].values for name, group in df_time.groupby('time_slot')]
        h_stat, p_value = kruskal(*groups)
        test_name = "Kruskal-Wallis"
    
    print(f"Estatística do teste: {h_stat if not is_normal else f_stat:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação
    if p_value < 0.05:
        conclusion = "REJEITAR H₀: Existe diferença significativa no ticket médio entre faixas horárias"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há diferença significativa no ticket médio entre faixas horárias"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_time, x='time_slot', y='order_ticket')
    plt.title('Distribuição do Ticket Médio por Faixa Horária')
    plt.tight_layout()
    plt.savefig('charts/question5_time_slots.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'Existe diferença no ticket médio entre faixas horárias?',
        'test_used': test_name,
        'p_value': p_value,
        'conclusion': conclusion
    }

def statistical_question_6(df):
    """
    PERGUNTA 6: Estados com maior razão de frete têm ticket médio menor?
    """
    print("\n" + "="*80)
    print("PERGUNTA 6: Estados com maior razão de frete têm ticket médio menor?")
    print("="*80)
    
    # Calcular médias por estado
    state_summary = df.groupby('customer_state').agg({
        'order_ticket': 'mean',
        'freight_ratio': 'mean',
        'order_id': 'count'
    }).round(4)
    state_summary.columns = ['ticket_medio', 'razao_frete_media', 'n_pedidos']
    
    # Filtrar estados com amostra suficiente
    state_summary = state_summary[state_summary['n_pedidos'] >= 100]
    
    print(f"\nDados para análise: {len(state_summary)} estados")
    print("\nMÉDIAS POR ESTADO:")
    print(state_summary.sort_values('razao_frete_media'))
    
    # Teste de normalidade
    print("\nTESTE DE NORMALIDADE:")
    norm_ticket, is_normal_ticket = test_normality(state_summary['ticket_medio'], 'ticket_medio')
    norm_freight, is_normal_freight = test_normality(state_summary['razao_frete_media'], 'razao_frete')
    
    print(f"Ticket médio: {norm_ticket}")
    print(f"Razão frete: {norm_freight}")
    
    # Escolher correlação apropriada
    if is_normal_ticket and is_normal_freight:
        print("\nUSANDO CORRELAÇÃO DE PEARSON (dados normais):")
        corr_coef, p_value = pearsonr(state_summary['razao_frete_media'], state_summary['ticket_medio'])
        corr_type = "Pearson"
    else:
        print("\nUSANDO CORRELAÇÃO DE SPEARMAN (dados não-normais):")
        corr_coef, p_value = spearmanr(state_summary['razao_frete_media'], state_summary['ticket_medio'])
        corr_type = "Spearman"
    
    print(f"Coeficiente de correlação: {corr_coef:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretação
    if p_value < 0.05:
        if corr_coef < 0:
            conclusion = "REJEITAR H₀: Estados com maior razão de frete TÊM ticket médio menor (correlação negativa significativa)"
        else:
            conclusion = "REJEITAR H₀: Estados com maior razão de frete TÊM ticket médio maior (correlação positiva significativa)"
    else:
        conclusion = "NÃO REJEITAR H₀: Não há correlação significativa entre razão de frete e ticket médio por estado"
    
    print(f"\nCONCLUSÃO: {conclusion}")
    
    # Visualização
    plt.figure(figsize=(10, 6))
    plt.scatter(state_summary['razao_frete_media'], state_summary['ticket_medio'])
    
    # Adicionar labels dos estados
    for idx, row in state_summary.iterrows():
        plt.annotate(idx, (row['razao_frete_media'], row['ticket_medio']), 
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    plt.xlabel('Razão Frete Média')
    plt.ylabel('Ticket Médio (R$)')
    plt.title(f'Correlação: Razão Frete vs Ticket Médio por Estado\n{corr_type}: r={corr_coef:.4f}, p={p_value:.6f}')
    
    # Linha de tendência
    z = np.polyfit(state_summary['razao_frete_media'], state_summary['ticket_medio'], 1)
    p = np.poly1d(z)
    plt.plot(state_summary['razao_frete_media'], p(state_summary['razao_frete_media']), "r--", alpha=0.8)
    
    plt.tight_layout()
    plt.savefig('charts/question6_freight_ticket_correlation.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'question': 'Estados com maior razão de frete têm ticket médio menor?',
        'test_used': f'Correlação de {corr_type}',
        'correlation': corr_coef,
        'p_value': p_value,
        'conclusion': conclusion
    }

def main():
    """Função principal que executa todas as análises"""
    print("ANÁLISE DE PERGUNTAS ESTATÍSTICAS PRAGMÁTICAS")
    print("=" * 80)
    
    # Carregar dados
    df = load_data()
    
    # Criar diretório para gráficos se não existir
    os.makedirs('charts', exist_ok=True)
    
    # Executar todas as perguntas
    results = []
    
    results.append(statistical_question_1(df))
    results.append(statistical_question_2(df))
    results.append(statistical_question_3(df))
    results.append(statistical_question_4(df))
    results.append(statistical_question_5(df))
    results.append(statistical_question_6(df))
    
    # Resumo final
    print("\n" + "="*80)
    print("RESUMO DAS ANÁLISES ESTATÍSTICAS")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['question']}")
        print(f"   Teste usado: {result['test_used']}")
        print(f"   P-value: {result['p_value']:.6f}")
        print(f"   Conclusão: {result['conclusion']}")
        
        if 'correlation' in result:
            print(f"   Correlação: {result['correlation']:.4f}")
    
    print(f"\nTotal de gráficos gerados: {len(results)}")
    print("Gráficos salvos em: charts/question*.png")

if __name__ == "__main__":
    main() 