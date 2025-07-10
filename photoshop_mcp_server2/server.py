"""Photoshop MCP Server main module."""

import logging
import os
import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.client import Client
import asyncio

# Import registry
from photoshop_mcp_server2.registry import register_all_resources, register_all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("photoshop-mcp-server2")


def create_server(
    name: str = "Photoshop",
    description: str = "Control Adobe Photoshop using MCP",
    config: dict[str, Any] | None = None,
) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        name: The name of the MCP server.
        description: A description of the server's functionality.
        config: Additional configuration options.

    Returns:
        FastMCP: The configured MCP server.

    """
    # Create a new MCP server with the provided configuration
    instructions = """
        1. Whenever a new document is set as active document, always check if the document
        contains any background layers. If it does, convert them to a normal layer.
        2. Before running any tool check if there is a background layer in the active document.
        If there are background layers, convert them to a normal layer before running tools.
        3. Whenever a background layer is converted to a normal layer, its name changes to a new name.
        Check it up using get_layers_info tool and apply correct name on further operations.
        4. When using generative fill use generative_fill_without_region tool if no selection is made / 
        region is unknown and If a selection is made, use region_generative_fill tool.
        5. When tools like region_generative_fill are used, a new document is created and 
        added in the documents list. Always set the newly created document as the active document before
        proceding with any further operations. Whenever a opertion creates a new document, it should
        set that new document as the active document.
        6. Always clarify what and how to use the tools and resources provided by the MCP server.
        7. Run photoshop_generative_expand only once. Dont run it twice unnecessarily.
        8. Check your work with screenshot_current_document tool while perform operations on layers.
        Adjust positions, sizes, and other properties of layers as needed to achieve the desired result.
        9. Always flatten the document before saving it / after completing the work to ensure all layers are merged.
    """
    server_mcp = FastMCP(name=name, instructions=instructions)

    class SessionMiddleware(Middleware):
        async def on_list_tools(self, context: MiddlewareContext, call_next: Any) -> Any:
            logger.info("Adding instructions to context")
            await context.fastmcp_context.info('Instructions to be followed in using this server: '+instructions)
            return await super().on_list_tools(context, call_next)
    server_mcp.add_middleware(SessionMiddleware())

    # Register all resources dynamically
    logger.info("Registering resources...")
    registered_resources = register_all_resources(server_mcp)
    logger.info(
        f"Registered resources from modules: {list(registered_resources.keys())}"
    )

    # Register all tools dynamically
    logger.info("Registering tools...")
    registered_tools = register_all_tools(server_mcp)
    logger.info(f"Registered tools from modules: {list(registered_tools.keys())}")

    # Apply additional configuration if provided
    if config:
        logger.info(f"Applying additional configuration: {config}")
        # Example: Set environment variables
        if "env_vars" in config:
            for key, value in config["env_vars"].items():
                os.environ[key] = str(value)

    logger.info(f"Server '{name}' configured successfully")
    return server_mcp


def main():
    """Run the main entry point for the server.

    This function parses command-line arguments and starts the MCP server.
    It can be invoked directly or through the 'ps-mcp' entry point.

    Command-line arguments:
        --name: Server name (default: "Photoshop")
        --description: Server description
        --debug: Enable debug logging
    """
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Photoshop MCP Server")
    parser.add_argument("--name", default="Photoshop", help="Server name")
    parser.add_argument(
        "--description",
        default="Control Adobe Photoshop using MCP",
        help="Server description",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging level
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
            handler.stream.reconfigure(encoding='utf-8')
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    logger.info(f"Starting Photoshop MCP Server...")

    try:
        # Configure and run the server with command-line arguments
        server_mcp = create_server(
            name=args.name, description=args.description
        )
        server_mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
