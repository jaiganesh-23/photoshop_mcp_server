"""Document-related MCP tools."""

import photoshop.api as ps

from photoshop_mcp_server2.ps_adapter.application import PhotoshopApp
from photoshop_mcp_server2.registry import register_tool


def register(mcp):
    """Register document-related tools.

    Args:
        mcp: The MCP server instance.

    Returns:
        list: List of registered tool names.

    """
    registered_tools = []

    def create_document(
        width: int = 1000, height: int = 1000, name: str = "Untitled", mode: str = "rgb"
    ) -> dict:
        """Create a new document in Photoshop.

        Args:
            width: Document width in pixels.
            height: Document height in pixels.
            name: Document name.
            mode: Color mode (rgb, cmyk, etc.). Defaults to "rgb".

        Returns:
            dict: Result of the operation.

        """
        print(
            f"Creating document: width={width}, height={height}, name={name}, mode={mode}"
        )
        ps_app = PhotoshopApp()
        try:
            # Validate mode parameter
            valid_modes = ["rgb", "cmyk", "grayscale", "gray", "bitmap", "lab"]
            if mode.lower() not in valid_modes:
                return {
                    "success": False,
                    "error": f"Invalid mode: {mode}. Valid modes are: {', '.join(valid_modes)}",
                    "detailed_error": (
                        f"Invalid color mode: {mode}\n\n"
                        f"Valid modes are: {', '.join(valid_modes)}\n\n"
                        f"The mode parameter specifies the color mode of the new document. "
                        f"It must be one of the valid modes listed above."
                    ),
                }

            # Create document
            print(
                f"Calling ps_app.create_document with width={width}, height={height}, name={name}, mode={mode}"
            )
            doc = ps_app.create_document(
                width=width, height=height, name=name, mode=mode
            )

            if not doc:
                return {
                    "success": False,
                    "error": "Failed to create document - returned None",
                }

            # Get document properties safely
            try:
                print("Document created, getting properties")
                doc_name = doc.name
                print(f"Document name: {doc_name}")

                # Get width safely
                doc_width = width  # Default fallback
                if hasattr(doc, "width"):
                    width_obj = doc.width
                    print(f"Width object type: {type(width_obj)}")
                    if hasattr(width_obj, "value"):
                        doc_width = width_obj.value
                    else:
                        try:
                            doc_width = float(width_obj)
                        except (TypeError, ValueError):
                            print(f"Could not convert width to float: {width_obj}")
                print(f"Document width: {doc_width}")

                # Get height safely
                doc_height = height  # Default fallback
                if hasattr(doc, "height"):
                    height_obj = doc.height
                    print(f"Height object type: {type(height_obj)}")
                    if hasattr(height_obj, "value"):
                        doc_height = height_obj.value
                    else:
                        try:
                            doc_height = float(height_obj)
                        except (TypeError, ValueError):
                            print(f"Could not convert height to float: {height_obj}")
                print(f"Document height: {doc_height}")

                return {
                    "success": True,
                    "document_name": doc_name,
                    "width": doc_width,
                    "height": doc_height,
                }
            except Exception as prop_error:
                print(f"Error getting document properties: {prop_error}")
                import traceback

                traceback.print_exc()
                # Document was created but we couldn't get properties
                return {
                    "success": True,
                    "document_name": name,
                    "width": width,
                    "height": height,
                    "warning": f"Created document but couldn't get properties: {prop_error!s}",
                }
        except Exception as e:
            print(f"Error creating document: {e}")
            import traceback

            tb_text = traceback.format_exc()
            traceback.print_exc()

            # Create a detailed error message
            detailed_error = (
                f"Error creating document with parameters:\n"
                f"  width: {width}\n"
                f"  height: {height}\n"
                f"  name: {name}\n"
                f"  mode: {mode}\n\n"
                f"Error: {e!s}\n\n"
                f"Traceback:\n{tb_text}"
            )

            return {
                "success": False,
                "error": str(e),
                "detailed_error": detailed_error,
                "parameters": {
                    "width": width,
                    "height": height,
                    "name": name,
                    "mode": mode,
                },
            }

    # Register the create_document function with a specific name
    tool_name = register_tool(mcp, create_document, "create_document")
    registered_tools.append(tool_name)

    def open_document(file_path: str) -> dict:
        """Open an existing document.

        Args:
            file_path: Path to the document file.

        Returns:
            dict: Result of the operation.

        """
        ps_app = PhotoshopApp()
        try:
            doc = ps_app.open_document(file_path)
            return {
                "success": True,
                "document_name": doc.name,
                "width": doc.width,
                "height": doc.height,
            }
            if hasattr(ps_app, "session"):
                ps_app.app.activeDocument = doc
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Register the open_document function with a specific name
    tool_name = register_tool(mcp, open_document, "open_document")
    registered_tools.append(tool_name)

    def save_document(file_path: str, format: str = "psd") -> dict:
        """Save the active document.

        Args:
            file_path: Path where to save the document.
            format: File format (psd, jpg, png).

        Returns:
            dict: Result of the operation.

        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            if format.lower() == "jpg" or format.lower() == "jpeg":
                options = ps.JPEGSaveOptions(quality=10)
                doc.saveAs(file_path, options, asCopy=True)
            elif format.lower() == "png":
                options = ps.PNGSaveOptions()
                doc.saveAs(file_path, options, asCopy=True)
            else:  # Default to PSD
                options = ps.PhotoshopSaveOptions()
                doc.saveAs(file_path, options, asCopy=True)

            return {"success": True, "file_path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Register the save_document function with a specific name
    tool_name = register_tool(mcp, save_document, "save_document")
    registered_tools.append(tool_name)

    def describe_current_document() -> dict:
        """
        Saves the current Photoshop document as an image and uses BLIP to generate a description.
        Deletes the temporary image file after use.

        Returns:
            dict: Contains the generated description or error.
        """
        import tempfile
        import os
        from PIL import Image
        import torch
        from transformers import BlipProcessor, BlipForConditionalGeneration

        temp_img_path = None

        # 1. Save current document as a temporary image (PNG)
        try:
            ps_app = PhotoshopApp()
            doc = ps_app.get_active_document()
            if not doc:
                return {"success": False, "error": "No active document"}

            temp_dir = tempfile.gettempdir()
            temp_img_path = os.path.join(temp_dir, "ps_doc_for_blip.png")

            # Save as PNG using Photoshop API
            import photoshop.api as ps
            options = ps.PNGSaveOptions()
            doc.saveAs(temp_img_path, options, asCopy=True)
        except Exception as e:
            return {"success": False, "error": f"Failed to save document as image: {e}"}

        # 2. Load image and run BLIP
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)

            raw_image = Image.open(temp_img_path).convert('RGB')
            inputs = processor(raw_image, return_tensors="pt").to(device)
            out = model.generate(**inputs)
            description = processor.decode(out[0], skip_special_tokens=True)
        except Exception as e:
            # Clean up temp file if it exists
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass
            return {"success": False, "error": f"BLIP description failed: {e}"}

        # 3. Delete the temporary image file
        if temp_img_path and os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception:
                pass

        return {
            "success": True,
            "description": description
        }

    # Register the describe_current_document function with a specific name
    tool_name = register_tool(mcp, describe_current_document, "describe_current_document")
    registered_tools.append(tool_name)

    def list_open_documents() -> dict:
        """
        Lists the documents that are currently open in Photoshop.

        Returns:
            dict: Contains a list of open document names and their properties.
        """
        try:
            ps_app = PhotoshopApp()
            app = ps_app.app
            docs = getattr(app, "documents", None)
            if docs is None or not hasattr(docs, "length") or docs.length == 0:
                return {"success": True, "documents": [], "message": "No documents are currently open."}

            open_docs = []
            for i,doc in enumerate(docs.app):
                try:
                    doc_info = {
                        "name": getattr(doc, "name", f"Document {i+1}"),
                        "width": float(getattr(doc, "width", 0)),
                        "height": float(getattr(doc, "height", 0)),
                        "index": i,
                    }
                    open_docs.append(doc_info)
                except Exception as e:
                    open_docs.append({"name": f"Document {i+1}", "error": str(e)})

            return {"success": True, "documents": open_docs}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
            }

    # Register the list_open_documents function
    tool_name = register_tool(mcp, list_open_documents, "list_open_documents")
    registered_tools.append(tool_name)

    def select_document(document_name: str) -> dict:
        """
        Makes the given document the active document by selecting it from the open document tabs.

        Args:
            document_name (str): The name of the document to select.

        Returns:
            dict: Result of the operation.
        """
        try:
            ps_app = PhotoshopApp()
            app = ps_app.app
            docs = getattr(app, "documents", None)
            if docs is None or not hasattr(docs, "length") or docs.length == 0:
                return {"success": False, "error": "No documents are currently open."}

            found = False
            for i,doc in enumerate(docs.app):
                try:
                    name = getattr(doc, "name", None)
                    if name == document_name:
                        app.activeDocument = doc
                        found = True
                        break
                except Exception:
                    continue

            if not found:
                return {"success": False, "error": f"Document '{document_name}' not found among open documents."}
            return {"success": True, "message": f"Document '{document_name}' is now the active document."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"document_name": document_name},
            }

    # Register the select_document function with a specific name
    tool_name = register_tool(mcp, select_document, "select_document")
    registered_tools.append(tool_name)

    def resize_document(width: int, height: int) -> dict:
        """
        Resizes the current active Photoshop document to the given width and height in pixels.

        Args:
            width (int): The new width in pixels.
            height (int): The new height in pixels.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            # Use Photoshop's resizeImage method
            doc.resizeImage(width, height)
            return {
                "success": True,
                "message": f"Document resized to {width}x{height} pixels.",
                "width": width,
                "height": height,
            }
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"width": width, "height": height},
            }

    # Register the resize_document function
    tool_name = register_tool(mcp, resize_document, "resize_document")
    registered_tools.append(tool_name)

    def flatten_document() -> dict:
        """
        Flattens the current active Photoshop document.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            doc.flatten()
            return {
                "success": True,
                "message": "Document has been flattened.",
            }
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
            }

    # Register the flatten_document function
    tool_name = register_tool(mcp, flatten_document, "flatten_document")
    registered_tools.append(tool_name)
    # Return the list of registered tools
    return registered_tools
