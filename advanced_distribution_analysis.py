import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import minimize
import warnings
from matplotlib.gridspec import GridSpec
import os
from collections import OrderedDict
warnings.filterwarnings('ignore')

# Configuração do matplotlib
plt.rcParams['figure.figsize'] = (16, 12)
plt.rcParams['font.size'] = 9
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8

class AdvancedDistributionAnalyzer:
    """
    Classe para análise avançada de distribuições de probabilidade com múltiplos testes estatísticos.
    """
    
    def __init__(self):
        self.distributions = {
            'normal': stats.norm,
            'lognormal': stats.lognorm,
            'exponential': stats.expon,
            'gamma': stats.gamma,
            'weibull': stats.weibull_min,
            'beta': stats.beta,
            'pareto': stats.pareto,
            'chi2': stats.chi2,
            'uniform': stats.uniform
        }
        
        self.normality_tests = {
            'shapiro_wilk': self._shapiro_test,
            'anderson_darling': self._anderson_test,
            'kolmogorov_smirnov': self._ks_test,
            'jarque_bera': self._jarque_bera_test,
            'dagostino': self._dagostino_test
        }
    
    def _shapiro_test(self, data):
        """Teste de Shapiro-Wilk para normalidade."""
        if len(data) > 5000:
            # Shapiro-Wilk tem limitação de tamanho
            sample_data = np.random.choice(data, 5000, replace=False)
        else:
            sample_data = data
        
        statistic, p_value = stats.shapiro(sample_data)
        return {
            'test_name': 'Shapiro-Wilk',
            'statistic': statistic,
            'p_value': p_value,
            'null_hypothesis': 'Os dados seguem distribuição normal',
            'interpretation': 'Normal' if p_value > 0.05 else 'Não Normal'
        }
    
    def _anderson_test(self, data):
        """Teste de Anderson-Darling para normalidade."""
        result = stats.anderson(data, dist='norm')
        # Usar nível de significância de 5%
        critical_value = result.critical_values[2]  # 5%
        p_value = self._anderson_p_value(result.statistic, len(data))
        
        return {
            'test_name': 'Anderson-Darling',
            'statistic': result.statistic,
            'p_value': p_value,
            'critical_value': critical_value,
            'null_hypothesis': 'Os dados seguem distribuição normal',
            'interpretation': 'Normal' if result.statistic < critical_value else 'Não Normal'
        }
    
    def _anderson_p_value(self, statistic, n):
        """Aproximação do p-value para Anderson-Darling."""
        # Fórmula aproximada para p-value do Anderson-Darling
        if statistic < 0.2:
            return 1 - np.exp(-13.436 + 101.14 * statistic - 223.73 * statistic**2)
        elif statistic < 0.34:
            return 1 - np.exp(-8.318 + 42.796 * statistic - 59.938 * statistic**2)
        elif statistic < 0.6:
            return np.exp(0.9177 - 4.279 * statistic - 1.38 * statistic**2)
        else:
            return np.exp(1.2937 - 5.709 * statistic + 0.0186 * statistic**2)
    
    def _ks_test(self, data):
        """Teste de Kolmogorov-Smirnov para normalidade."""
        # Normalizar os dados
        normalized_data = (data - np.mean(data)) / np.std(data)
        statistic, p_value = stats.kstest(normalized_data, 'norm')
        
        return {
            'test_name': 'Kolmogorov-Smirnov',
            'statistic': statistic,
            'p_value': p_value,
            'null_hypothesis': 'Os dados seguem distribuição normal',
            'interpretation': 'Normal' if p_value > 0.05 else 'Não Normal'
        }
    
    def _jarque_bera_test(self, data):
        """Teste de Jarque-Bera para normalidade."""
        statistic, p_value = stats.jarque_bera(data)
        
        return {
            'test_name': 'Jarque-Bera',
            'statistic': statistic,
            'p_value': p_value,
            'null_hypothesis': 'Os dados seguem distribuição normal',
            'interpretation': 'Normal' if p_value > 0.05 else 'Não Normal'
        }
    
    def _dagostino_test(self, data):
        """Teste de D'Agostino para normalidade."""
        statistic, p_value = stats.normaltest(data)
        
        return {
            'test_name': "D'Agostino-Pearson",
            'statistic': statistic,
            'p_value': p_value,
            'null_hypothesis': 'Os dados seguem distribuição normal',
            'interpretation': 'Normal' if p_value > 0.05 else 'Não Normal'
        }
    
    def fit_distribution(self, data, distribution_name):
        """
        Ajusta uma distribuição específica aos dados.
        """
        dist = self.distributions[distribution_name]
        
        try:
            # Ajustar parâmetros
            if distribution_name == 'normal':
                params = dist.fit(data)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'lognormal':
                # Para lognormal, os dados devem ser positivos
                if np.any(data <= 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'exponential':
                if np.any(data <= 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'gamma':
                if np.any(data <= 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'weibull':
                if np.any(data <= 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'beta':
                # Beta requer dados entre 0 e 1
                if np.any(data <= 0) or np.any(data >= 1):
                    # Normalizar para [0,1]
                    data_norm = (data - data.min()) / (data.max() - data.min())
                    # Evitar 0 e 1 exatos
                    data_norm = np.clip(data_norm, 1e-6, 1-1e-6)
                    params = dist.fit(data_norm)
                    aic = self._calculate_aic(data_norm, dist, params)
                    bic = self._calculate_bic(data_norm, dist, params)
                else:
                    params = dist.fit(data)
                    aic = self._calculate_aic(data, dist, params)
                    bic = self._calculate_bic(data, dist, params)
                    
            elif distribution_name == 'pareto':
                if np.any(data <= 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'chi2':
                if np.any(data < 0):
                    return None
                params = dist.fit(data, floc=0)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            elif distribution_name == 'uniform':
                params = dist.fit(data)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
                
            else:
                params = dist.fit(data)
                aic = self._calculate_aic(data, dist, params)
                bic = self._calculate_bic(data, dist, params)
            
            # Teste de bondade de ajuste (Kolmogorov-Smirnov)
            ks_statistic, ks_p_value = stats.kstest(data, lambda x: dist.cdf(x, *params))
            
            return {
                'distribution': distribution_name,
                'parameters': params,
                'aic': aic,
                'bic': bic,
                'ks_statistic': ks_statistic,
                'ks_p_value': ks_p_value,
                'goodness_of_fit': 'Bom ajuste' if ks_p_value > 0.05 else 'Ajuste inadequado'
            }
            
        except Exception as e:
            print(f"Erro ao ajustar {distribution_name}: {e}")
            return None
    
    def _calculate_aic(self, data, dist, params):
        """Calcula o Critério de Informação de Akaike (AIC)."""
        log_likelihood = np.sum(dist.logpdf(data, *params))
        k = len(params)  # número de parâmetros
        return 2 * k - 2 * log_likelihood
    
    def _calculate_bic(self, data, dist, params):
        """Calcula o Critério de Informação Bayesiano (BIC)."""
        log_likelihood = np.sum(dist.logpdf(data, *params))
        k = len(params)  # número de parâmetros
        n = len(data)    # tamanho da amostra
        return k * np.log(n) - 2 * log_likelihood
    
    def comprehensive_analysis(self, data, variable_name, category=None, state=None):
        """
        Realiza análise abrangente de uma variável.
        """
        print(f"\n{'='*80}")
        print(f"ANÁLISE ABRANGENTE DE DISTRIBUIÇÕES: {variable_name.upper()}")
        if category:
            print(f"Categoria: {category}")
        if state:
            print(f"Estado: {state}")
        print(f"{'='*80}")
        
        # Estatísticas descritivas
        stats_desc = {
            'n': len(data),
            'mean': np.mean(data),
            'median': np.median(data),
            'std': np.std(data),
            'min': np.min(data),
            'max': np.max(data),
            'q25': np.percentile(data, 25),
            'q75': np.percentile(data, 75),
            'skewness': stats.skew(data),
            'kurtosis': stats.kurtosis(data)
        }
        
        print(f"\nESTATÍSTICAS DESCRITIVAS:")
        print(f"N: {stats_desc['n']:,}")
        print(f"Média: {stats_desc['mean']:.4f}")
        print(f"Mediana: {stats_desc['median']:.4f}")
        print(f"Desvio Padrão: {stats_desc['std']:.4f}")
        print(f"Assimetria: {stats_desc['skewness']:.4f}")
        print(f"Curtose: {stats_desc['kurtosis']:.4f}")
        
        # Testes de normalidade
        print(f"\nTESTES DE NORMALIDADE (H₀: dados são normais):")
        normality_results = {}
        for test_name, test_func in self.normality_tests.items():
            result = test_func(data)
            normality_results[test_name] = result
            print(f"{result['test_name']}: Estatística={result['statistic']:.4f}, "
                  f"P-Value={result['p_value']:.6f} → {result['interpretation']}")
        
        # Ajuste de distribuições
        print(f"\nAJUSTE DE DISTRIBUIÇÕES:")
        distribution_results = {}
        for dist_name in self.distributions.keys():
            result = self.fit_distribution(data, dist_name)
            if result:
                distribution_results[dist_name] = result
                print(f"{dist_name.title()}: AIC={result['aic']:.2f}, "
                      f"BIC={result['bic']:.2f}, KS P-Value={result['ks_p_value']:.6f} "
                      f"→ {result['goodness_of_fit']}")
        
        # Melhor distribuição baseada em AIC
        if distribution_results:
            best_dist = min(distribution_results.items(), key=lambda x: x[1]['aic'])
            print(f"\nMELHOR AJUSTE (menor AIC): {best_dist[0].title()}")
            print(f"AIC: {best_dist[1]['aic']:.2f}")
            print(f"P-Value KS: {best_dist[1]['ks_p_value']:.6f}")
        
        return {
            'descriptive_stats': stats_desc,
            'normality_tests': normality_results,
            'distribution_fits': distribution_results,
            'best_distribution': best_dist if distribution_results else None
        }
    
    def create_comprehensive_plot(self, data, analysis_results, variable_name, 
                                category=None, state=None):
        """
        Cria gráfico abrangente com múltiplas distribuições.
        """
        fig = plt.figure(figsize=(20, 16))
        
        # Título principal
        title = f'ANÁLISE DE DISTRIBUIÇÕES - {variable_name.upper()}'
        if state and category:
            title += f' - {state} - {category}'
        elif state:
            title += f' - {state}'
        elif category:
            title += f' - {category}'
        
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.95)
        
        # Grid de subplots
        gs = GridSpec(4, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Histograma com distribuições ajustadas
        ax1 = fig.add_subplot(gs[0, :])
        ax1.hist(data, bins=50, density=True, alpha=0.7, color='lightblue', 
                edgecolor='black', label='Dados Observados')
        
        # Plotar as 3 melhores distribuições
        dist_results = analysis_results['distribution_fits']
        if dist_results:
            sorted_dists = sorted(dist_results.items(), key=lambda x: x[1]['aic'])[:3]
            colors = ['red', 'green', 'orange']
            
            x_range = np.linspace(data.min(), data.max(), 1000)
            
            for i, (dist_name, result) in enumerate(sorted_dists):
                dist = self.distributions[dist_name]
                params = result['parameters']
                
                try:
                    pdf_values = dist.pdf(x_range, *params)
                    ax1.plot(x_range, pdf_values, colors[i], linewidth=2, 
                            label=f'{dist_name.title()} (AIC: {result["aic"]:.1f})')
                except:
                    continue
        
        ax1.set_xlabel(variable_name)
        ax1.set_ylabel('Densidade')
        ax1.set_title('Histograma com Distribuições Ajustadas')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Q-Q Plot para normalidade
        ax2 = fig.add_subplot(gs[1, 0])
        stats.probplot(data, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot (Normal)')
        ax2.grid(True, alpha=0.3)
        
        # 3. Boxplot
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.boxplot(data, vert=True)
        ax3.set_ylabel(variable_name)
        ax3.set_title('Boxplot')
        ax3.grid(True, alpha=0.3)
        
        # 4. Gráfico de densidade
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.hist(data, bins=30, density=True, alpha=0.7, color='lightgreen')
        ax4.set_xlabel(variable_name)
        ax4.set_ylabel('Densidade')
        ax4.set_title('Densidade Empírica')
        ax4.grid(True, alpha=0.3)
        
        # 5. Tabela de testes de normalidade
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        # Criar tabela de resultados
        normality_data = []
        for test_name, result in analysis_results['normality_tests'].items():
            normality_data.append([
                result['test_name'],
                f"{result['statistic']:.4f}",
                f"{result['p_value']:.6f}",
                result['interpretation']
            ])
        
        table = ax5.table(cellText=normality_data,
                         colLabels=['Teste', 'Estatística', 'P-Value', 'Interpretação'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0.1, 0.3, 0.8, 0.6])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        ax5.set_title('Testes de Normalidade (H₀: dados são normais)', 
                     fontsize=12, fontweight='bold', pad=20)
        
        # 6. Tabela de ajuste de distribuições
        ax6 = fig.add_subplot(gs[3, :])
        ax6.axis('off')
        
        if dist_results:
            dist_data = []
            sorted_dists = sorted(dist_results.items(), key=lambda x: x[1]['aic'])
            
            for dist_name, result in sorted_dists[:6]:  # Top 6 distribuições
                dist_data.append([
                    dist_name.title(),
                    f"{result['aic']:.2f}",
                    f"{result['bic']:.2f}",
                    f"{result['ks_p_value']:.6f}",
                    result['goodness_of_fit']
                ])
            
            table2 = ax6.table(cellText=dist_data,
                              colLabels=['Distribuição', 'AIC', 'BIC', 'KS P-Value', 'Ajuste'],
                              cellLoc='center',
                              loc='center',
                              bbox=[0.05, 0.2, 0.9, 0.7])
            table2.auto_set_font_size(False)
            table2.set_fontsize(9)
            table2.scale(1, 2)
            ax6.set_title('Ajuste de Distribuições (ordenado por AIC)', 
                         fontsize=12, fontweight='bold', pad=20)
        
        # Salvar gráfico
        filename_parts = ['advanced_dist', variable_name.lower().replace(' ', '_')]
        if state:
            filename_parts.append(state.lower())
        if category:
            filename_parts.append(category.lower().replace(' ', '_'))
        
        filename = f"charts/{'_'.join(filename_parts)}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"   → Gráfico salvo: {filename}")
        return filename

def load_data_for_advanced_analysis():
    """Carrega dados para análise avançada."""
    print("Carregando dados para análise avançada de distribuições...")
    
    # Usar o mesmo processo de carregamento do script anterior
    items_df = pd.read_csv('olist-csv/olist_order_items_dataset.csv')
    products_df = pd.read_csv('olist-csv/olist_products_dataset.csv')
    translation_df = pd.read_csv('olist-csv/product_category_name_translation.csv')
    orders_df = pd.read_csv('olist-csv/olist_orders_dataset.csv')
    customers_df = pd.read_csv('olist-csv/olist_customers_dataset.csv')
    
    # Merge progressivo
    items_products = items_df.merge(
        products_df[['product_id', 'product_category_name']], 
        on='product_id', 
        how='left'
    )
    
    items_products_trans = items_products.merge(
        translation_df, 
        on='product_category_name', 
        how='left'
    )
    
    orders_customers = orders_df.merge(
        customers_df[['customer_id', 'customer_state']], 
        on='customer_id', 
        how='left'
    )
    
    final_df = items_products_trans.merge(
        orders_customers[['order_id', 'customer_state', 'order_status']], 
        on='order_id', 
        how='left'
    )
    
    # Filtros de qualidade
    final_df = final_df[
        (final_df['order_status'] == 'delivered') &
        (final_df['price'] > 0) & 
        (final_df['freight_value'] >= 0) &
        (final_df['price'] <= 10000) &
        (final_df['product_category_name_english'].notna()) &
        (final_df['customer_state'].notna())
    ]
    
    # Agregação por pedido
    orders_summary = final_df.groupby(['order_id', 'customer_state']).agg({
        'price': 'sum',
        'freight_value': 'sum',
        'order_item_id': 'count',
        'product_category_name_english': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'mixed'
    }).reset_index()
    
    orders_summary.columns = ['order_id', 'customer_state', 'order_ticket', 'freight_value', 'n_items', 'product_category']
    orders_summary['freight_ratio'] = orders_summary['freight_value'] / orders_summary['order_ticket']
    orders_summary['freight_ratio'] = orders_summary['freight_ratio'].clip(0, 1)
    
    print(f"Dados carregados: {len(orders_summary)} pedidos")
    return orders_summary

def main():
    """Função principal para análise avançada de distribuições."""
    print("INICIANDO ANÁLISE AVANÇADA DE DISTRIBUIÇÕES")
    print("=" * 80)
    
    # Criar diretório para gráficos
    os.makedirs('charts', exist_ok=True)
    
    # Carregar dados
    df = load_data_for_advanced_analysis()
    
    # Inicializar analisador
    analyzer = AdvancedDistributionAnalyzer()
    
    # Selecionar top estados e categorias
    top_states = df['customer_state'].value_counts().head(5).index
    top_categories = df['product_category'].value_counts().head(4).index
    
    # Variáveis para análise
    variables = ['order_ticket', 'freight_ratio']
    
    # Análise geral por variável
    all_results = {}
    
    for variable in variables:
        print(f"\n{'='*60}")
        print(f"ANÁLISE GERAL: {variable.upper()}")
        print(f"{'='*60}")
        
        data = df[variable].values
        result = analyzer.comprehensive_analysis(data, variable)
        analyzer.create_comprehensive_plot(data, result, variable)
        all_results[f'{variable}_geral'] = result
    
    # Análise por estado
    for state in top_states:
        state_data = df[df['customer_state'] == state]
        
        for variable in variables:
            data = state_data[variable].values
            if len(data) > 100:  # Mínimo para análise robusta
                result = analyzer.comprehensive_analysis(data, variable, state=state)
                analyzer.create_comprehensive_plot(data, result, variable, state=state)
                all_results[f'{variable}_{state}'] = result
    
    # Análise por categoria
    for category in top_categories:
        cat_data = df[df['product_category'] == category]
        
        for variable in variables:
            data = cat_data[variable].values
            if len(data) > 100:
                result = analyzer.comprehensive_analysis(data, variable, category=category)
                analyzer.create_comprehensive_plot(data, result, variable, category=category)
                all_results[f'{variable}_{category}'] = result
    
    # Gerar relatório consolidado
    generate_advanced_report(all_results)
    
    print(f"\n{'='*80}")
    print("ANÁLISE AVANÇADA DE DISTRIBUIÇÕES CONCLUÍDA")
    print(f"Gráficos gerados: {len([f for f in os.listdir('charts') if 'advanced_dist' in f])}")
    print("Relatório: advanced_distribution_report.md")

def generate_advanced_report(results):
    """Gera relatório consolidado da análise avançada."""
    print("\nGerando relatório consolidado...")
    
    report_lines = [
        "# ANÁLISE AVANÇADA DE DISTRIBUIÇÕES DE PROBABILIDADE",
        "## E-commerce Brasileiro - Testes Estatísticos com P-Values",
        "",
        "### METODOLOGIA",
        "",
        "Esta análise implementa **testes rigorosos de múltiplas distribuições de probabilidade** utilizando:",
        "",
        "**Testes de Normalidade (todos baseados em P-Values):**",
        "- **Shapiro-Wilk**: Mais poderoso para amostras pequenas",
        "- **Anderson-Darling**: Sensível às caudas da distribuição", 
        "- **Kolmogorov-Smirnov**: Teste clássico de bondade de ajuste",
        "- **Jarque-Bera**: Baseado em assimetria e curtose",
        "- **D'Agostino-Pearson**: Combinação de testes de assimetria e curtose",
        "",
        "**Distribuições Testadas:**",
        "- Normal, Log-Normal, Exponencial, Gamma, Weibull, Beta, Pareto, Chi-quadrado, Uniforme",
        "",
        "**Critérios de Seleção:**",
        "- **AIC (Critério de Informação de Akaike)**: Menor valor indica melhor ajuste",
        "- **BIC (Critério de Informação Bayesiano)**: Penaliza complexidade do modelo",
        "- **Teste KS (P-Value)**: P > 0.05 indica ajuste adequado",
        "",
        "### INTERPRETAÇÃO DOS P-VALUES",
        "",
        "**Para todos os testes de hipótese:**",
        "- **P-Value > 0.05**: NÃO rejeitamos H₀ (evidência insuficiente contra a hipótese nula)",
        "- **P-Value ≤ 0.05**: REJEITAMOS H₀ (evidência significativa contra a hipótese nula)",
        "- **P-Value < 0.001**: Evidência muito forte contra H₀",
        "",
    ]
    
    # Análise por variável
    for result_key, result_data in results.items():
        if 'geral' in result_key:
            variable = result_key.replace('_geral', '')
            report_lines.extend([
                f"## ANÁLISE DETALHADA: {variable.upper().replace('_', ' ')}",
                "",
                f"### Estatísticas Descritivas",
                f"- **N**: {result_data['descriptive_stats']['n']:,}",
                f"- **Média**: {result_data['descriptive_stats']['mean']:.4f}",
                f"- **Mediana**: {result_data['descriptive_stats']['median']:.4f}",
                f"- **Desvio Padrão**: {result_data['descriptive_stats']['std']:.4f}",
                f"- **Assimetria**: {result_data['descriptive_stats']['skewness']:.4f}",
                f"- **Curtose**: {result_data['descriptive_stats']['kurtosis']:.4f}",
                "",
                "### Testes de Normalidade",
                "",
                "| Teste | Estatística | P-Value | Interpretação |",
                "|-------|-------------|---------|---------------|",
            ])
            
            for test_name, test_result in result_data['normality_tests'].items():
                report_lines.append(
                    f"| {test_result['test_name']} | {test_result['statistic']:.4f} | "
                    f"{test_result['p_value']:.6f} | {test_result['interpretation']} |"
                )
            
            report_lines.extend([
                "",
                "### Ajuste de Distribuições",
                "",
                "| Distribuição | AIC | BIC | KS P-Value | Qualidade do Ajuste |",
                "|--------------|-----|-----|------------|---------------------|",
            ])
            
            # Ordenar por AIC
            sorted_dists = sorted(result_data['distribution_fits'].items(), 
                                key=lambda x: x[1]['aic'])
            
            for dist_name, dist_result in sorted_dists:
                report_lines.append(
                    f"| {dist_name.title()} | {dist_result['aic']:.2f} | "
                    f"{dist_result['bic']:.2f} | {dist_result['ks_p_value']:.6f} | "
                    f"{dist_result['goodness_of_fit']} |"
                )
            
            # Melhor distribuição
            best_dist = result_data['best_distribution']
            if best_dist:
                report_lines.extend([
                    "",
                    f"**MELHOR AJUSTE**: {best_dist[0].title()}",
                    f"- AIC: {best_dist[1]['aic']:.2f}",
                    f"- P-Value KS: {best_dist[1]['ks_p_value']:.6f}",
                    f"- Qualidade: {best_dist[1]['goodness_of_fit']}",
                    "",
                    "---",
                    ""
                ])
    
    # Salvar relatório
    with open('advanced_distribution_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print("Relatório salvo: advanced_distribution_report.md")

if __name__ == "__main__":
    main()