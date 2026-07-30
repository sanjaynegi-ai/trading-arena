import unittest

from backend.mcp_servers import researcher_mcp_servers


class McpServerConfigurationTest(unittest.TestCase):
    def test_fetch_server_uses_compatible_uvx_args(self) -> None:
        servers = researcher_mcp_servers("Test", "User")

        self.assertTrue(servers, "expected at least one researcher MCP server")
        fetch_server = servers[0]
        self.assertEqual(
            fetch_server.params.args,
            ["--with", "mcp<1", "mcp-server-fetch"],
        )


if __name__ == "__main__":
    unittest.main()
