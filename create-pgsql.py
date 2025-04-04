import psycopg2
import pandas as pd
import os
from psycopg2 import sql
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('olist_data_loading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment_variables():
    """Carrega credenciais do banco de dados de variáveis de ambiente"""
    load_dotenv()
    return {
        'dbname': os.getenv('DB_NAME', 'olist_db'),
        'user': os.getenv('DB_USER', 'olist_user'),
        'password': os.getenv('DB_PASSWORD', 'admin'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    }

def create_database_connection(db_params):
    """Cria e retorna uma conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(**db_params)
        conn.autocommit = False
        logger.info("Conexão com o banco de dados estabelecida com sucesso")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def drop_all_foreign_keys(conn):
    """Remove todas as constraints de chave estrangeira de forma agressiva"""
    try:
        with conn.cursor() as cur:
            # Obtém todas as constraints de chave estrangeira
            cur.execute("""
                SELECT conrelid::regclass AS table_name, 
                       conname AS constraint_name
                FROM pg_constraint
                WHERE contype = 'f'
                AND connamespace = 'public'::regnamespace;
            """)
            fk_constraints = cur.fetchall()
            
            # Remove cada constraint
            for table_name, constraint_name in fk_constraints:
                try:
                    cur.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")
                    logger.info(f"Removida constraint: {constraint_name} da tabela {table_name}")
                except psycopg2.Error as e:
                    conn.rollback()
                    logger.warning(f"Falha ao remover {constraint_name}: {e}")
            
            conn.commit()
        logger.info("Todas as constraints de chave estrangeira removidas")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Erro ao remover constraints: {e}")
        raise

def drop_and_recreate_tables(conn):
    """Remove e recria todas as tabelas sem constraints"""
    drop_tables_query = """
        DROP TABLE IF EXISTS 
        olist_order_payments_dataset,
        olist_order_reviews_dataset,
        olist_order_items_dataset,
        olist_orders_dataset,
        olist_order_customer_dataset,
        olist_products_dataset,
        olist_sellers_dataset,
        olist_geolocation_dataset CASCADE;
    """
    
    create_tables_queries = [
        """
        CREATE TABLE olist_geolocation_dataset (
            zip_code_prefix VARCHAR(10) PRIMARY KEY,
            lat FLOAT,
            lng FLOAT,
            city VARCHAR(100),
            state VARCHAR(100)
        );
        """,
        """
        CREATE TABLE olist_sellers_dataset (
            seller_id VARCHAR(50) PRIMARY KEY,
            seller_zip_code_prefix VARCHAR(10),
            seller_city VARCHAR(100),
            seller_state VARCHAR(100)
        );
        """,
        """
        CREATE TABLE olist_products_dataset (
            product_id VARCHAR(50) PRIMARY KEY,
            product_category_name VARCHAR(100),
            product_name_length INT,
            product_description_length INT,
            product_photos_qty INT,
            product_weight_g INT,
            product_length_cm INT,
            product_height_cm INT,
            product_width_cm INT
        );
        """,
        """
        CREATE TABLE olist_order_customer_dataset (
            customer_id VARCHAR(50) PRIMARY KEY,
            customer_unique_id VARCHAR(50),
            customer_zip_code_prefix VARCHAR(10),
            customer_city VARCHAR(100),
            customer_state VARCHAR(100)
        );
        """,
        """
        CREATE TABLE olist_orders_dataset (
            order_id VARCHAR(50) PRIMARY KEY,
            customer_id VARCHAR(50),
            order_status VARCHAR(50),
            order_purchase_timestamp TIMESTAMP,
            order_approved_at TIMESTAMP,
            order_delivered_carrier_date TIMESTAMP,
            order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP
        );
        """,
        """
        CREATE TABLE olist_order_items_dataset (
            order_id VARCHAR(50),
            order_item_id INT,
            product_id VARCHAR(50),
            seller_id VARCHAR(50),
            shipping_limit_date TIMESTAMP,
            price FLOAT,
            freight_value FLOAT,
            PRIMARY KEY (order_id, order_item_id)
        );
        """,
        """
        CREATE TABLE olist_order_reviews_dataset (
            review_id VARCHAR(50) PRIMARY KEY,
            order_id VARCHAR(50),
            review_score INT,
            review_comment_title TEXT,
            review_comment_message TEXT,
            review_creation_date TIMESTAMP,
            review_answer_timestamp TIMESTAMP
        );
        """,
        """
        CREATE TABLE olist_order_payments_dataset (
            order_id VARCHAR(50),
            payment_sequential INT,
            payment_type VARCHAR(50),
            payment_installments INT,
            payment_value FLOAT,
            PRIMARY KEY (order_id, payment_sequential)
        );
        """
    ]
    
    try:
        with conn.cursor() as cur:
            # Remove todas as tabelas
            cur.execute(drop_tables_query)
            logger.info("Todas as tabelas existentes removidas")
            
            # Recria as tabelas
            for query in create_tables_queries:
                cur.execute(query)
            
            conn.commit()
        logger.info("Todas as tabelas foram recriadas sem constraints")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Erro ao recriar tabelas: {e}")
        raise

def load_data_with_fallback(conn, csv_path, table_name, config):
    """Carrega dados com fallback para registros problemáticos"""
    try:
        start_time = datetime.now()
        logger.info(f"Carregando {config['file']} na tabela {table_name}...")
        
        # Lê o arquivo CSV
        file_path = os.path.join(csv_path, config['file'])
        df = pd.read_csv(file_path)
        
        # Renomeia colunas se necessário
        if 'rename_columns' in config:
            df = df.rename(columns=config['rename_columns'])
        
        # Seleciona apenas as colunas que queremos inserir
        df = df[config['columns']]
        
        # Substitui NaN por None para o PostgreSQL
        df = df.where(pd.notnull(df), None)
        
        # Prepara dados para inserção
        columns = config['columns']
        data_tuples = [tuple(x) for x in df.to_numpy()]
        
        # Cria a query INSERT
        insert_query = sql.SQL("""
            INSERT INTO {} ({})
            VALUES ({})
            ON CONFLICT DO NOTHING
        """).format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join([sql.Placeholder()] * len(columns))
        )
        
        # Tenta carregar todos os dados de uma vez
        with conn.cursor() as cur:
            try:
                execute_batch(cur, insert_query, data_tuples, page_size=100)
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                logger.warning(f"Erro no carregamento em lote, tentando registro por registro: {e}")
                
                # Fallback: insere registro por registro
                success_count = 0
                for record in data_tuples:
                    try:
                        cur.execute(insert_query, record)
                        success_count += 1
                    except psycopg2.Error:
                        conn.rollback()
                        continue
                conn.commit()
                logger.warning(f"Carregamento com fallback: {success_count}/{len(data_tuples)} registros inseridos")
        
        duration = datetime.now() - start_time
        logger.info(f"Concluído o carregamento de {config['file']} na tabela {table_name}. "
                  f"Linhas: {len(df)}. Duração: {duration}")
        
    except Exception as e:
        logger.error(f"Erro fatal ao carregar {config['file']}: {e}")
        raise

def add_foreign_keys_with_not_valid(conn):
    """Adiciona constraints com a opção NOT VALID"""
    foreign_key_queries = [
        """
        ALTER TABLE olist_sellers_dataset
        ADD CONSTRAINT fk_seller_zip_code
        FOREIGN KEY (seller_zip_code_prefix) 
        REFERENCES olist_geolocation_dataset(zip_code_prefix)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_customer_dataset
        ADD CONSTRAINT fk_customer_zip_code
        FOREIGN KEY (customer_zip_code_prefix) 
        REFERENCES olist_geolocation_dataset(zip_code_prefix)
        NOT VALID
        """,
        """
        ALTER TABLE olist_orders_dataset
        ADD CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id) 
        REFERENCES olist_order_customer_dataset(customer_id)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_items_dataset
        ADD CONSTRAINT fk_order_item_product
        FOREIGN KEY (product_id) 
        REFERENCES olist_products_dataset(product_id)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_items_dataset
        ADD CONSTRAINT fk_order_item_seller
        FOREIGN KEY (seller_id) 
        REFERENCES olist_sellers_dataset(seller_id)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_items_dataset
        ADD CONSTRAINT fk_order_item_order
        FOREIGN KEY (order_id) 
        REFERENCES olist_orders_dataset(order_id)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_reviews_dataset
        ADD CONSTRAINT fk_review_order
        FOREIGN KEY (order_id) 
        REFERENCES olist_orders_dataset(order_id)
        NOT VALID
        """,
        """
        ALTER TABLE olist_order_payments_dataset
        ADD CONSTRAINT fk_payment_order
        FOREIGN KEY (order_id) 
        REFERENCES olist_orders_dataset(order_id)
        NOT VALID
        """
    ]
    
    try:
        with conn.cursor() as cur:
            for query in foreign_key_queries:
                try:
                    cur.execute(query)
                    conn.commit()
                except psycopg2.Error as e:
                    conn.rollback()
                    logger.warning(f"Não foi possível adicionar constraint: {e}")
        logger.info("Constraints de chave estrangeira adicionadas com NOT VALID")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Erro ao adicionar constraints: {e}")
        raise

def main():
    try:
        # Carrega variáveis de ambiente
        db_params = load_environment_variables()
        
        # Obtém caminho do diretório CSV
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, 'olist-csv')
        
        # Verifica se o diretório CSV existe
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Diretório CSV não encontrado: {csv_path}")
        
        # Conecta ao banco de dados
        conn = create_database_connection(db_params)
        
        # Remove todas as constraints de forma agressiva
        drop_all_foreign_keys(conn)
        
        # Recria todas as tabelas sem constraints
        drop_and_recreate_tables(conn)
        
        # Configuração dos arquivos CSV
        csv_configs = {
            'olist_geolocation_dataset': {
                'file': 'olist_geolocation_dataset.csv',
                'columns': ['zip_code_prefix', 'lat', 'lng', 'city', 'state'],
                'rename_columns': {
                    'geolocation_zip_code_prefix': 'zip_code_prefix',
                    'geolocation_lat': 'lat',
                    'geolocation_lng': 'lng',
                    'geolocation_city': 'city',
                    'geolocation_state': 'state'
                }
            },
            'olist_sellers_dataset': {
                'file': 'olist_sellers_dataset.csv',
                'columns': ['seller_id', 'seller_zip_code_prefix', 'seller_city', 'seller_state']
            },
            'olist_products_dataset': {
                'file': 'olist_products_dataset.csv',
                'columns': [
                    'product_id', 'product_category_name', 'product_name_length', 
                    'product_description_length', 'product_photos_qty', 'product_weight_g',
                    'product_length_cm', 'product_height_cm', 'product_width_cm'
                ],
                'rename_columns': {
                    'product_name_lenght': 'product_name_length',
                    'product_description_lenght': 'product_description_length'
                }
            },
            'olist_order_customer_dataset': {
                'file': 'olist_customers_dataset.csv',
                'columns': ['customer_id', 'customer_unique_id', 'customer_zip_code_prefix', 'customer_city', 'customer_state'],
                'rename_columns': {
                    'customer_city': 'customer_city',
                    'customer_state': 'customer_state'
                }
            },
            'olist_orders_dataset': {
                'file': 'olist_orders_dataset.csv',
                'columns': [
                    'order_id', 'customer_id', 'order_status', 'order_purchase_timestamp',
                    'order_approved_at', 'order_delivered_carrier_date',
                    'order_delivered_customer_date', 'order_estimated_delivery_date'
                ]
            },
            'olist_order_items_dataset': {
                'file': 'olist_order_items_dataset.csv',
                'columns': [
                    'order_id', 'order_item_id', 'product_id', 'seller_id',
                    'shipping_limit_date', 'price', 'freight_value'
                ]
            },
            'olist_order_reviews_dataset': {
                'file': 'olist_order_reviews_dataset.csv',
                'columns': [
                    'review_id', 'order_id', 'review_score', 'review_comment_title',
                    'review_comment_message', 'review_creation_date', 'review_answer_timestamp'
                ]
            },
            'olist_order_payments_dataset': {
                'file': 'olist_order_payments_dataset.csv',
                'columns': [
                    'order_id', 'payment_sequential', 'payment_type',
                    'payment_installments', 'payment_value'
                ]
            }
        }
        
        # Carrega dados dos CSVs
        for table_name, config in csv_configs.items():
            load_data_with_fallback(conn, csv_path, table_name, config)
        
        # Adiciona constraints com NOT VALID
        add_foreign_keys_with_not_valid(conn)
        
        logger.info("Todos os dados foram carregados no banco PostgreSQL com sucesso!")
        
    except Exception as e:
        logger.error(f"Ocorreu um erro: {e}")
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
            logger.info("Conexão com o banco de dados fechada")

if __name__ == "__main__":
    main()