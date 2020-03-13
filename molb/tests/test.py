from asynctest import CoroutineMock
from asynctest import MagicMock
from asynctest import Mock
from asynctest import patch
from asynctest import TestCase
from undecorated import undecorated

from molb.views.home import home


@patch("molb.views.home.authorized_userid")
class MolbTest(TestCase):
    def setUp(self):
        self.conn_mock = MagicMock(name="conn")

        dbpool_mock = MagicMock(name="db-pool")
        dbpool_mock.acquire = MagicMock(name="acquire")
        dbpool_mock.acquire.return_value.__aenter__.return_value = self.conn_mock

        app = MagicMock(name="app")
        d = {"db-pool": dbpool_mock}
        app.__getitem__.side_effect = d.__getitem__
        app.__iter__.side_effect = d.__iter__
        self.request = Mock(name="request")
        self.request.app = app

    async def test_home(self, mocked_auth):
        mocked_auth.return_value = "toto"

        self.conn_mock.fetchrow = CoroutineMock(
            name='fetchrow',
            return_value=(("login", "toto"),)
        )

        ret = await undecorated(home)(self.request)

        self.conn_mock.fetchrow.assert_called_once()
        self.assertEqual(
            self.conn_mock.fetchrow.call_args[0][0],
            "SELECT * FROM client WHERE login = $1"
        )
        self.assertEqual(self.conn_mock.fetchrow.call_args[0][1], "toto")

        self.assertEqual(
            ret["client"], {"login": "toto"}
        )
