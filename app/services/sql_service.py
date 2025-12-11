"""
SQL Service
Handles Text-to-SQL conversion using Vanna.ai with OpenAI and PostgreSQL.
"""

from typing import Dict, Any, List, Optional
import uuid
import pandas as pd
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore
import sqlalchemy
from app.config import settings


class VannaSQLService(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Custom Vanna class combining ChromaDB for vector storage and OpenAI for LLM.
    """

    def __init__(self, config: Dict[str, Any]):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


class TextToSQLService:
    """Service for converting natural language to SQL using Vanna.ai."""

    def __init__(self, database_url: str | None = None, openai_api_key: str | None = None):
        """
        Initialize the Text-to-SQL service.

        Args:
            database_url: PostgreSQL connection string
            openai_api_key: OpenAI API key
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY

        if not self.database_url:
            raise ValueError("DATABASE_URL is required for Text-to-SQL features")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for Text-to-SQL features")

        # Initialize Vanna with OpenAI and ChromaDB
        self.vn = VannaSQLService(config={
            'api_key': self.openai_api_key,
            'model': 'gpt-4-turbo-preview',
            'path': './data/vanna_chromadb'  # Local storage for Vanna's vector DB
        })

        # Connect to PostgreSQL database
        try:
            self.engine = sqlalchemy.create_engine(self.database_url)
            self.vn.connect_to_postgres(url=self.database_url)
            print("✓ Connected to PostgreSQL database")
        except Exception as e:
            raise Exception(f"Failed to connect to database: {str(e)}")

        # Store for pending SQL queries awaiting approval
        self.pending_queries: Dict[str, Dict[str, Any]] = {}

        # Track if training has been completed
        self.is_trained = False

    def train_on_schema(self):
        """
        Train Vanna on the database schema (DDL).
        This teaches Vanna about the table structures.
        """
        try:
            print("Training Vanna on database schema...")

            # Get all table names from the database
            ddl_statements = []

            # Train on the information schema
            df_tables = self.vn.run_sql("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)

            if not df_tables.empty:
                for table_name in df_tables['table_name']:
                    # Get CREATE TABLE statement for each table
                    ddl = self.vn.run_sql(f"""
                        SELECT
                            'CREATE TABLE ' || table_name || ' (' ||
                            string_agg(
                                column_name || ' ' || data_type ||
                                CASE WHEN character_maximum_length IS NOT NULL
                                THEN '(' || character_maximum_length || ')'
                                ELSE '' END,
                                ', '
                            ) || ');' as ddl
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        AND table_schema = 'public'
                        GROUP BY table_name
                    """)

                    if not ddl.empty:
                        ddl_statements.append(ddl['ddl'].iloc[0])

            # Train Vanna on each DDL statement
            for ddl in ddl_statements:
                self.vn.train(ddl=ddl)

            print(f"✓ Trained on {len(ddl_statements)} tables")

        except Exception as e:
            print(f"Warning: Failed to train on schema: {e}")

    def train_on_documentation(self, documentation: str):
        """
        Train Vanna on documentation about the database.

        Args:
            documentation: Natural language description of the database
        """
        try:
            self.vn.train(documentation=documentation)
            print("✓ Trained on documentation")
        except Exception as e:
            print(f"Warning: Failed to train on documentation: {e}")

    def train_on_examples(self, examples: List[Dict[str, str]]):
        """
        Train Vanna on question-SQL pairs (golden examples).

        Args:
            examples: List of dicts with 'question' and 'sql' keys
        """
        try:
            for example in examples:
                self.vn.train(
                    question=example['question'],
                    sql=example['sql']
                )
            print(f"✓ Trained on {len(examples)} example queries")
        except Exception as e:
            print(f"Warning: Failed to train on examples: {e}")

    def complete_training(self):
        """
        Complete training with schema and golden examples.
        """
        # Train on schema
        self.train_on_schema()

        # Train on database documentation
        documentation = """
        This is an e-commerce database with three main tables:
        - customers: Contains customer information including name, email, segment (SMB, Enterprise, Individual), and country
        - products: Product catalog with name, category, price, stock quantity, and description
        - orders: Customer orders with order date, total amount, status (Pending, Delivered, Cancelled, Processing), and shipping address

        The customers table has a one-to-many relationship with orders (one customer can have many orders).
        Use customer_order_summary view for aggregated customer statistics.
        """
        self.train_on_documentation(documentation)

        # Train on golden examples
        golden_examples = [
            {
                "question": "How many customers do we have?",
                "sql": "SELECT COUNT(*) as customer_count FROM customers;"
            },
            {
                "question": "What is the total revenue from all orders?",
                "sql": "SELECT SUM(total_amount) as total_revenue FROM orders;"
            },
            {
                "question": "List all delivered orders",
                "sql": "SELECT * FROM orders WHERE status = 'Delivered' ORDER BY order_date DESC;"
            },
            {
                "question": "How many orders per customer segment?",
                "sql": """SELECT c.segment, COUNT(o.id) as order_count
                         FROM customers c
                         LEFT JOIN orders o ON c.id = o.customer_id
                         GROUP BY c.segment;"""
            },
            {
                "question": "What is the average order value by customer segment?",
                "sql": """SELECT c.segment, AVG(o.total_amount) as avg_order_value
                         FROM customers c
                         JOIN orders o ON c.id = o.customer_id
                         GROUP BY c.segment;"""
            },
            {
                "question": "Top 10 customers by total spending",
                "sql": """SELECT c.name, c.email, SUM(o.total_amount) as total_spent
                         FROM customers c
                         JOIN orders o ON c.id = o.customer_id
                         GROUP BY c.id, c.name, c.email
                         ORDER BY total_spent DESC
                         LIMIT 10;"""
            },
            {
                "question": "How many products in each category?",
                "sql": "SELECT category, COUNT(*) as product_count FROM products GROUP BY category;"
            },
            {
                "question": "What are the top selling product categories?",
                "sql": """SELECT p.category, COUNT(DISTINCT o.id) as order_count
                         FROM products p
                         JOIN orders o ON o.created_at > p.created_at
                         GROUP BY p.category
                         ORDER BY order_count DESC;"""
            },
            {
                "question": "Show orders from the last 30 days",
                "sql": """SELECT * FROM orders
                         WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
                         ORDER BY order_date DESC;"""
            },
            {
                "question": "Which customers have never placed an order?",
                "sql": """SELECT c.* FROM customers c
                         LEFT JOIN orders o ON c.id = o.customer_id
                         WHERE o.id IS NULL;"""
            }
        ]

        self.train_on_examples(golden_examples)

        self.is_trained = True
        print("✓ Vanna training complete!")

    def generate_sql(self, question: str) -> Dict[str, Any]:
        """
        Generate SQL from a natural language question.

        Args:
            question: Natural language question

        Returns:
            Dictionary with generated SQL and metadata
        """
        if not self.is_trained:
            raise Exception("Vanna has not been trained yet. Call complete_training() first.")

        try:
            # Generate SQL using Vanna
            sql = self.vn.generate_sql(question=question)

            return {
                "question": question,
                "sql": sql,
                "status": "generated"
            }

        except Exception as e:
            raise Exception(f"Failed to generate SQL: {str(e)}")

    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query to execute

        Returns:
            List of result rows as dictionaries
        """
        try:
            # Run SQL using Vanna (which uses pandas DataFrame)
            df = self.vn.run_sql(sql)

            # Convert DataFrame to list of dictionaries
            if df.empty:
                return []

            return df.to_dict('records')

        except Exception as e:
            raise Exception(f"Failed to execute SQL: {str(e)}")

    def generate_sql_for_approval(self, question: str) -> Dict[str, Any]:
        """
        Generate SQL but don't execute yet - return for user approval.

        Args:
            question: Natural language question

        Returns:
            Dictionary with query_id, question, SQL, and status
        """
        # Generate SQL
        result = self.generate_sql(question)
        sql = result['sql']

        # Create unique query ID
        query_id = str(uuid.uuid4())

        # Store pending query
        self.pending_queries[query_id] = {
            'question': question,
            'sql': sql,
            'status': 'pending_approval',
            'generated_at': pd.Timestamp.now().isoformat()
        }

        return {
            'query_id': query_id,
            'question': question,
            'sql': sql,
            'explanation': "This SQL will retrieve data from your database. Please review before approving.",
            'status': 'pending_approval'
        }

    def execute_approved_query(self, query_id: str, approved: bool) -> Dict[str, Any]:
        """
        Execute a SQL query after user approval.

        Args:
            query_id: ID of the pending query
            approved: Whether the user approved execution

        Returns:
            Dictionary with results or rejection message
        """
        if query_id not in self.pending_queries:
            return {
                'error': 'Query ID not found',
                'status': 'error'
            }

        query_info = self.pending_queries[query_id]

        if not approved:
            # User rejected the query
            del self.pending_queries[query_id]
            return {
                'query_id': query_id,
                'status': 'rejected',
                'message': 'Query execution cancelled by user'
            }

        # Execute the SQL
        try:
            sql = query_info['sql']
            results = self.execute_sql(sql)

            # Clean up pending query
            del self.pending_queries[query_id]

            return {
                'query_id': query_id,
                'question': query_info['question'],
                'sql': sql,
                'results': results,
                'result_count': len(results),
                'status': 'executed'
            }

        except Exception as e:
            return {
                'query_id': query_id,
                'error': str(e),
                'status': 'error'
            }

    def get_pending_queries(self) -> List[Dict[str, Any]]:
        """
        Get list of all pending queries awaiting approval.

        Returns:
            List of pending query information
        """
        return [
            {
                'query_id': qid,
                **info
            }
            for qid, info in self.pending_queries.items()
        ]
