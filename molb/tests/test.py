from asynctest import CoroutineMock
from asynctest import MagicMock
from asynctest import Mock
from asynctest import patch
from asynctest import TestCase
from undecorated import undecorated

from molb.views.home import home
from molb.views.language import language


class BaseTest(TestCase):
    def setUp(self):
        self.request = Mock()
        self.request.app = MagicMock()


class DatabaseTest(BaseTest):
    def setUp(self):
        super().setUp()

        self.conn_mock = MagicMock()

        dbpool_mock = MagicMock()
        dbpool_mock.acquire = MagicMock()
        dbpool_mock.acquire.return_value.__aenter__.return_value = self.conn_mock

        pool_dict = {"db-pool": dbpool_mock}
        self.request.app.__getitem__.side_effect = pool_dict.__getitem__
        self.request.app.__iter__.side_effect = pool_dict.__iter__


class HomeTest(DatabaseTest):
    """Test of home.py"""

    @patch("molb.views.home.authorized_userid")
    async def test_home(self, auth_userid_mock):

        auth_userid_mock.return_value = "toto"

        self.conn_mock.fetchrow = CoroutineMock(return_value=(("login", "toto"),))

        ret = await undecorated(home)(self.request)

        self.conn_mock.fetchrow.assert_called_once_with(
            "SELECT * FROM client WHERE login = $1", 'toto'
        )

        self.assertEqual(ret["client"], {"login": "toto"})


@patch("molb.views.language.HTTPFound")
class LanguageTest(BaseTest):
    """Test of language.py"""

    def setUp(self):
        super().setUp()

        home_route_dict = {"home": Mock()}
        self.request.app.router.__getitem__.side_effect = home_route_dict.__getitem__
        self.request.app.router.__iter__.side_effect = home_route_dict.__iter__

    async def test_language_header(self, http_found_mock):
        """url is taken from the header"""

        self.request.path.split.return_value = ["language", "en"]
        self.request.headers.get.return_value = "url_in_header"

        resp = await language(self.request)

        resp.set_cookie.assert_called_once_with("locale", "en")
        http_found_mock.assert_called_once_with("url_in_header")

    async def test_language_fr(self, http_found_mock):
        """selection of fr language"""

        self.request.path.split.return_value = ["language", "fr"]

        resp = await language(self.request)

        resp.set_cookie.assert_called_once_with("locale", "fr")

    async def test_language_home(self, http_found_mock):
        """url is the home url"""

        self.request.path.split.return_value = ["language", "en"]
        self.request.headers.get.return_value = None
        self.request.app.router["home"].url_for.return_value = "home_url"

        resp = await language(self.request)

        resp.set_cookie.assert_called_once_with("locale", "en")
        http_found_mock.assert_called_once_with("home_url")
