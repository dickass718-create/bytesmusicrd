import unittest

import app


class PasswordHashingTests(unittest.TestCase):
    def test_hash_is_deterministic_for_same_salt(self):
        digest1, salt = app.hash_password("bytes-music", "fixed-salt")
        digest2, _ = app.hash_password("bytes-music", salt)
        self.assertEqual(digest1, digest2)

    def test_wrong_password_does_not_match(self):
        digest, salt = app.hash_password("correct", "fixed-salt")
        self.assertFalse(app.check_password("wrong", digest, salt))


class PayloadValidationTests(unittest.TestCase):
    def test_validate_username(self):
        self.assertTrue(app.validate_username("harshit"))
        self.assertTrue(app.validate_username("music_01"))
        self.assertFalse(app.validate_username("x"))
        self.assertFalse(app.validate_username("bad name"))

    def test_validate_password(self):
        self.assertTrue(app.validate_password("1234"))
        self.assertFalse(app.validate_password("123"))

    def test_validate_email(self):
        self.assertTrue(app.validate_email("user@example.com"))
        self.assertTrue(app.validate_email("technoproboizz@gmail.com"))
        self.assertFalse(app.validate_email("bad"))
        self.assertFalse(app.validate_email("no@domain"))
        self.assertFalse(app.validate_email(""))

    def test_is_admin_email(self):
        self.assertTrue(app.is_admin_email("technoproboizz@gmail.com"))
        self.assertTrue(app.is_admin_email("TECHNOPROBOIZZ@GMAIL.COM"))
        self.assertFalse(app.is_admin_email("someoneelse@gmail.com"))
        self.assertFalse(app.is_admin_email(""))


class AdminHelperTests(unittest.TestCase):
    def test_admin_from_token_returns_none_for_empty(self):
        self.assertIsNone(app.user_from_token(""))
        self.assertIsNone(app.user_from_token(None))


if __name__ == "__main__":
    unittest.main()
