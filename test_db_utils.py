import unittest
import sqlite3
import os
from db_utils import (
    create_connection,
    get_customer_by_id,
    get_customer_by_name,
    get_accounts_for_customer,
    get_account_by_id,
    get_transactions_for_account,
    DATABASE_NAME
)

# Ensure the database exists before running tests
if not os.path.exists(DATABASE_NAME):
    print(f"Error: Database file '{DATABASE_NAME}' not found. Run create_dummy_db.py first.")
    exit(1)

class TestDbUtils(unittest.TestCase):

    def test_connection(self):
        """ Test if the database connection can be established. """
        print("\nTesting Connection...")
        conn = create_connection()
        self.assertIsNotNone(conn, "Database connection should be established")
        if conn:
            conn.close()
        print("Connection test passed.")

    def test_get_customer_by_id_exists(self):
        """ Test retrieving an existing customer by ID (assuming ID 1 exists). """
        print("\nTesting get_customer_by_id (ID: 1)...")
        customer = get_customer_by_id(1)
        print("Retrieved Customer:", customer) # Print the data
        self.assertIsNotNone(customer, "Customer with ID 1 should be found")
        self.assertIsInstance(customer, dict, "Customer should be returned as a dictionary")
        self.assertEqual(customer['id'], 1, "Customer ID should match the query")
        print("Customer by ID test passed.")


    def test_get_customer_by_id_not_exists(self):
        """ Test retrieving a non-existent customer by ID. """
        print("\nTesting get_customer_by_id (ID: 99999)...")
        customer = get_customer_by_id(99999) # Assuming this ID doesn't exist
        print("Retrieved Customer:", customer) # Print the data (should be None)
        self.assertIsNone(customer, "Non-existent customer should return None")
        print("Non-existent customer by ID test passed.")

    def test_get_customer_by_name_exists(self):
        """ Test retrieving a customer by a likely existing partial name. """
        print("\nTesting get_customer_by_name...")
        # We need a name that's likely in the DB. Let's query one first.
        conn = create_connection()
        name_to_find = ""
        sample_name = ""
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT name FROM customers LIMIT 1")
                row = cur.fetchone()
                if row:
                    sample_name = row['name']
                    name_to_find = sample_name.split()[0] # Use the first name part for partial search
                    print(f"(Searching for name like: '{name_to_find}' based on sample: '{sample_name}')")
            finally:
                conn.close()

        if not name_to_find:
            self.skipTest("Could not retrieve a sample name from the database to test search.")

        customer = get_customer_by_name(name_to_find)
        print("Retrieved Customer:", customer) # Print the data
        self.assertIsNotNone(customer, f"Customer with name like '{name_to_find}' should be found")
        self.assertIsInstance(customer, dict, "Customer should be returned as a dictionary")
        print("Customer by Name test passed.")

    def test_get_customer_by_name_not_exists(self):
        """ Test retrieving a customer by a non-existent name. """
        print("\nTesting get_customer_by_name (NonExistentXYZ)...")
        customer = get_customer_by_name("NonExistentXYZ")
        print("Retrieved Customer:", customer) # Print the data (should be None)
        self.assertIsNone(customer, "Customer with a non-existent name should return None")
        print("Non-existent customer by name test passed.")


    def test_get_accounts_for_customer(self):
        """ Test retrieving accounts for an existing customer (assuming ID 1 exists). """
        print("\nTesting get_accounts_for_customer (CustomerID: 1)...")
        accounts = get_accounts_for_customer(1)
        print("Retrieved Accounts:", accounts) # Print the data
        self.assertIsInstance(accounts, list, "Accounts should be returned as a list")
        # We can't guarantee customer 1 has accounts, but if they do, they should be dicts
        if accounts:
            self.assertIsInstance(accounts[0], dict, "Each account in the list should be a dictionary")
            self.assertEqual(accounts[0]['customer_id'], 1, "Account's customer_id should match")
        print("Get Accounts test passed.")

    def test_get_account_by_id_exists(self):
        """ Test retrieving an existing account by ID (assuming ID 1 exists). """
        print("\nTesting get_account_by_id (ID: 1)...")
        account = get_account_by_id(1)
        print("Retrieved Account:", account) # Print the data
        self.assertIsNotNone(account, "Account with ID 1 should be found")
        self.assertIsInstance(account, dict, "Account should be returned as a dictionary")
        self.assertEqual(account['id'], 1, "Account ID should match the query")
        print("Account by ID test passed.")

    def test_get_account_by_id_not_exists(self):
        """ Test retrieving a non-existent account by ID. """
        print("\nTesting get_account_by_id (ID: 99999)...")
        account = get_account_by_id(99999) # Assuming this ID doesn't exist
        print("Retrieved Account:", account) # Print the data (should be None)
        self.assertIsNone(account, "Non-existent account should return None")
        print("Non-existent account by ID test passed.")

    def test_get_transactions_for_account(self):
        """ Test retrieving transactions for an existing account (assuming ID 1 exists). """
        print("\nTesting get_transactions_for_account (AccountID: 1)...")
        transactions = get_transactions_for_account(1)
        print("Retrieved Transactions:", transactions) # Print the data
        self.assertIsInstance(transactions, list, "Transactions should be returned as a list")
        # We can't guarantee account 1 has transactions, but if they do, they should be dicts
        if transactions:
            self.assertIsInstance(transactions[0], dict, "Each transaction should be a dictionary")
            self.assertEqual(transactions[0]['account_id'], 1, "Transaction's account_id should match")
            # Check if ordered by timestamp descending (difficult to assert exact order without knowing data)
            if len(transactions) > 1:
                 # Assuming ISO format strings are comparable
                 self.assertGreaterEqual(transactions[0]['timestamp'], transactions[-1]['timestamp'])
        print("Get Transactions test passed.")

if __name__ == '__main__':
    # Add verbosity to see the print statements clearly along with test results
    unittest.main(verbosity=2)
