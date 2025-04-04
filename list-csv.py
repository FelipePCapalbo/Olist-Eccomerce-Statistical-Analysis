import pandas as pd
import os

# Path to the directory containing the CSV files (same directory as the script)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'olist-csv') + '/'

# List of CSV files
csv_files = [
    'olist_geolocation_dataset.csv',
    'olist_sellers_dataset.csv',
    'olist_products_dataset.csv',
    'olist_customers_dataset.csv',
    'olist_orders_dataset.csv',
    'olist_order_items_dataset.csv',
    'olist_order_reviews_dataset.csv',
    'olist_order_payments_dataset.csv'
]

# Display the first 5 rows of each CSV file
for csv_file in csv_files:
    print(f"Preview of {csv_file}:")
    # Read the CSV file
    df = pd.read_csv(f"{csv_path}{csv_file}")
    
    # Display the first 5 rows
    print(df.head(), "\n")
