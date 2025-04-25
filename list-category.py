import pandas as pd
import os

# Path to the directory containing the CSV files (same directory as the script)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'olist-csv') + '/'

# Nome do arquivo específico
file_name = 'olist_products_dataset.csv'

# Caminho completo
file_path = os.path.join(csv_path, file_name)

# Lê o CSV
df = pd.read_csv(file_path)

# Lista os valores distintos da coluna 'product_category_name'
distinct_values = df['product_category_name'].dropna().unique()

# Exibe os valores
print(f"Valores distintos da coluna 'product_category_name' ({len(distinct_values)} categorias):")
for category in sorted(distinct_values):
    print(category)
