
def pytest_addoption(parser):
    parser.addoption("--module", action="store")
    parser.addoption("--cluster-name", action="store")
    parser.addoption("--aws-region", action="store")
    parser.addoption("--admin-username", action="store")
    parser.addoption("--admin-password", action="store")
