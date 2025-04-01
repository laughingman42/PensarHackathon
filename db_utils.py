import sqlite3

DATABASE_NAME = 'banking.db'

def create_connection(db_file=DATABASE_NAME):
    """ Create a database connection to the SQLite database. """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_file}: {e}")
    return conn

def get_customer_by_name(name):
    """ Query customer by name (case-insensitive partial match). """
    conn = create_connection()
    if not conn:
        return None

    customer = None
    try:
        cur = conn.cursor()
        # Use LIKE for partial matching, adjust if exact match is needed
        cur.execute("SELECT * FROM customers WHERE lower(name) LIKE lower(?) LIMIT 1", (f'%{name}%',))
        row = cur.fetchone()
        if row:
            customer = dict(row)
    except sqlite3.Error as e:
        print(f"Error querying customer by name: {e}")
    finally:
        if conn:
            conn.close()
    return customer

def get_customer_by_id(customer_id):
    """ Query customer by ID. """
    conn = create_connection()
    if not conn:
        return None

    customer = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        if row:
            customer = dict(row)
    except sqlite3.Error as e:
        print(f"Error querying customer by id: {e}")
    finally:
        if conn:
            conn.close()
    return customer

def get_accounts_for_customer(customer_id):
    """ Query all accounts for a given customer ID. """
    conn = create_connection()
    if not conn:
        return []

    accounts = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE customer_id = ? ORDER BY account_type", (customer_id,))
        rows = cur.fetchall()
        accounts = [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error querying accounts for customer: {e}")
    finally:
        if conn:
            conn.close()
    return accounts

def get_account_by_id(account_id):
    """ Query account by account ID. """
    conn = create_connection()
    if not conn:
        return None

    account = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = cur.fetchone()
        if row:
            account = dict(row)
    except sqlite3.Error as e:
        print(f"Error querying account by id: {e}")
    finally:
        if conn:
            conn.close()
    return account

def get_transactions_for_account(account_id, limit=20):
    """ Query transactions for a given account ID, ordered by timestamp descending. """
    conn = create_connection()
    if not conn:
        return []

    transactions = []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM transactions
            WHERE account_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """, (account_id, limit))
        rows = cur.fetchall()
        transactions = [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error querying transactions for account: {e}")
    finally:
        if conn:
            conn.close()
    return transactions

# --- Example Usage (can be commented out or removed) ---
if __name__ == '__main__':
    print("--- Database Utility Functions Example ---")

    # Example 1: Find a customer by name and get their accounts
    customer_name_to_find = "Smith" # Example partial name
    print(f"\nSearching for customer like '{customer_name_to_find}'...")
    customer = get_customer_by_name(customer_name_to_find)
    if customer:
        print(f"Found customer: ID={customer['id']}, Name={customer['name']}, Email={customer['email']}")
        customer_id = customer['id']
        print(f"\nFetching accounts for customer ID {customer_id}...")
        accounts = get_accounts_for_customer(customer_id)
        if accounts:
            for acc in accounts:
                print(f"  Account ID: {acc['id']}, Type: {acc['account_type']}, Balance: ${acc['balance']:.2f}")

                # Example 2: Get transactions for the first account found
                account_id_to_query = acc['id']
                print(f"\nFetching transactions for account ID {account_id_to_query}...")
                transactions = get_transactions_for_account(account_id_to_query, limit=5)
                if transactions:
                    for tx in transactions:
                        print(f"    TX ID: {tx['id']}, Type: {tx['transaction_type']}, Amount: ${tx['amount']:.2f}, Time: {tx['timestamp']}, Desc: {tx['description']}")
                else:
                    print(f"    No transactions found for account ID {account_id_to_query}.")
                break # Only show transactions for the first account in this example
        else:
            print(f"No accounts found for customer ID {customer_id}.")
    else:
        print(f"Customer like '{customer_name_to_find}' not found.")

    # Example 3: Get account by specific ID (replace with a valid ID from your db)
    # specific_account_id = 10
    # print(f"\nFetching account details for ID {specific_account_id}...")
    # specific_account = get_account_by_id(specific_account_id)
    # if specific_account:
    #     print(f"Found account: {specific_account}")
    # else:
    #     print(f"Account ID {specific_account_id} not found.")
