"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_read_an_account(self):
        """It should Read a single Account"""
        account = AccountFactory()
        post_resp = self.client.post(BASE_URL, json=account.serialize())
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)

        created_account = post_resp.get_json()
        account_id = created_account["id"]

        # Read the account
        get_resp = self.client.get(f"{BASE_URL}/{account_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)

        data = get_resp.get_json()
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)

    def test_account_not_found(self):
        """It should return 404 if Account is not found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_account(self):
        """It should Update an existing Account"""
        # Erstellt einen Account
        account = AccountFactory()
        post_resp = self.client.post(BASE_URL, json=account.serialize())
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)
        created_account = post_resp.get_json()

        # Daten ändern
        created_account["name"] = "Updated Name"
        created_account["email"] = "updated@example.com"

        # PUT auf /accounts/{id}
        put_resp = self.client.put(f"{BASE_URL}/{created_account['id']}", json=created_account)
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)
        updated_account = put_resp.get_json()

        self.assertEqual(updated_account["name"], "Updated Name")
        self.assertEqual(updated_account["email"], "updated@example.com")

    def test_update_account_not_found(self):
        """It should return 404 when updating non-existing Account"""
        fake_account = AccountFactory()
        fake_account.id = 999
        response = self.client.put(f"{BASE_URL}/999", json=fake_account.serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """It should Delete an Account"""
        account = AccountFactory()
        post_resp = self.client.post(BASE_URL, json=account.serialize())
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)
        account_id = post_resp.get_json()["id"]

        # Delete the account
        delete_resp = self.client.delete(f"{BASE_URL}/{account_id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Try to read it again → 404
        get_resp = self.client.get(f"{BASE_URL}/{account_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_account(self):
        """It should return 204 when deleting a non-existent Account"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_all_accounts(self):
        """It should List all Accounts"""
        accounts = self._create_accounts(3)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(len(data), 3)

        names = [acc.name for acc in accounts]
        for item in data:
            self.assertIn(item["name"], names)

    def test_list_no_accounts(self):
        """It should return an empty list when no Accounts exist"""
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ######################################################################
    #  S E C U R I T Y   T E S T   C A S E S
    ######################################################################

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return a CORS header"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check for the CORS header
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
