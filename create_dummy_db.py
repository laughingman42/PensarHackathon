import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

DATABASE_NAME = 'banking.db'
NUM_CUSTOMERS = 50
NUM_ACCOUNTS_PER_CUSTOMER = (1, 3) # Range of accounts per customer
NUM_TRANSACTIONS_PER_ACCOUNT = (5, 25) # Range of transactions per account

fake = Faker()

def create_connection(db_file):
    """ create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite DB connection successful to {db_file}")
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def create_customer(conn, customer):
    """ Create a new customer into the customers table """
    sql = ''' INSERT INTO customers(name, email, phone, address, date_joined)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, customer)
    conn.commit()
    return cur.lastrowid

def create_account(conn, account):
    """ Create a new account into the accounts table """
    sql = ''' INSERT INTO accounts(customer_id, account_type, balance, date_opened)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, account)
    conn.commit()
    return cur.lastrowid

def create_transaction(conn, transaction):
    """ Create a new transaction into the transactions table """
    sql = ''' INSERT INTO transactions(account_id, amount, transaction_type, timestamp, description)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, transaction)
    conn.commit()
    return cur.lastrowid

def main():
    # Drop existing database if it exists to start fresh
    import os
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)
        print(f"Removed existing database: {DATABASE_NAME}")

    conn = create_connection(DATABASE_NAME)

    sql_create_customers_table = """
    CREATE TABLE IF NOT EXISTS customers (
        id integer PRIMARY KEY,
        name text NOT NULL,
        email text UNIQUE,
        phone text,
        address text,
        date_joined text NOT NULL
    );
    """

    sql_create_accounts_table = """
    CREATE TABLE IF NOT EXISTS accounts (
        id integer PRIMARY KEY,
        customer_id integer NOT NULL,
        account_type text NOT NULL, -- e.g., 'checking', 'savings'
        balance real NOT NULL,
        date_opened text NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    );
    """

    sql_create_transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        id integer PRIMARY KEY,
        account_id integer NOT NULL,
        amount real NOT NULL,
        transaction_type text NOT NULL, -- 'deposit', 'withdrawal', 'transfer_out', 'transfer_in'
        timestamp text NOT NULL,
        description text,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    );
    """

    if conn is not None:
        # Create tables
        create_table(conn, sql_create_customers_table)
        create_table(conn, sql_create_accounts_table)
        create_table(conn, sql_create_transactions_table)
        print("Tables created successfully.")

        # --- Generate Customers ---
        customer_ids = []
        print(f"Generating {NUM_CUSTOMERS} customers...")
        for _ in range(NUM_CUSTOMERS):
            join_date = fake.date_between(start_date='-5y', end_date='today').isoformat()
            customer = (
                fake.name(),
                fake.unique.email(),
                fake.phone_number(),
                fake.address().replace('\n', ', '),
                join_date
            )
            customer_id = create_customer(conn, customer)
            customer_ids.append(customer_id)
        print("Customers generated.")

        # --- Generate Accounts ---
        account_ids = []
        print("Generating accounts...")
        for cust_id in customer_ids:
            num_accounts = random.randint(NUM_ACCOUNTS_PER_CUSTOMER[0], NUM_ACCOUNTS_PER_CUSTOMER[1])
            for _ in range(num_accounts):
                account_type = random.choice(['Checking', 'Savings'])
                initial_balance = round(random.uniform(50.0, 10000.0), 2)
                open_date = fake.date_between(start_date='-4y', end_date='today').isoformat() # Ensure account opened after customer joined
                # Ideally, check against customer join date, but keeping it simple here
                account = (cust_id, account_type, initial_balance, open_date)
                account_id = create_account(conn, account)
                account_ids.append({'id': account_id, 'balance': initial_balance})
        print("Accounts generated.")

        # --- Generate Transactions ---
        print("Generating transactions...")
        for account_info in account_ids:
            acc_id = account_info['id']
            current_balance = account_info['balance']
            num_transactions = random.randint(NUM_TRANSACTIONS_PER_ACCOUNT[0], NUM_TRANSACTIONS_PER_ACCOUNT[1])

            # Get account opening date to generate transactions after that date
            cur = conn.cursor()
            cur.execute("SELECT date_opened FROM accounts WHERE id = ?", (acc_id,))
            open_date_str = cur.fetchone()[0]
            open_date = datetime.fromisoformat(open_date_str)

            for i in range(num_transactions):
                # Ensure transaction timestamp is after account opening
                transaction_ts = fake.date_time_between(start_date=open_date, end_date='now')

                if current_balance > 10 and random.random() > 0.3: # Higher chance of withdrawal if balance allows
                    transaction_type = 'Withdrawal'
                    # Ensure withdrawal doesn't exceed balance (simplified)
                    amount = round(random.uniform(5.0, min(current_balance * 0.5, 500.0)), 2)
                    current_balance -= amount
                    description = fake.catch_phrase()
                else:
                    transaction_type = 'Deposit'
                    amount = round(random.uniform(10.0, 2000.0), 2)
                    current_balance += amount
                    description = f"Deposit from {fake.company()}"

                transaction = (acc_id, amount, transaction_type, transaction_ts.isoformat(), description)
                create_transaction(conn, transaction)

            # Update final account balance after transactions
            update_sql = "UPDATE accounts SET balance = ? WHERE id = ?"
            cur.execute(update_sql, (round(current_balance, 2), acc_id))
            conn.commit()
        print("Transactions generated and account balances updated.")

        conn.close()
        print("Database connection closed.")
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    main()
