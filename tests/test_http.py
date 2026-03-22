import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from daemon.server.http import FrontendServer

def test_server_creation():
    srv = FrontendServer(port=8080, frontend_dir="frontend")
    assert srv.port == 8080
    assert srv.frontend_dir.endswith("frontend")
