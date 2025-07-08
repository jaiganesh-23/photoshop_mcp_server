"""Session-related MCP tools for Photoshop."""

from typing import Any
import os
import tempfile
import cv2
import numpy as np
import pythoncom
import win32com.client

from photoshop_mcp_server2.ps_adapter.action_manager import ActionManager
from photoshop_mcp_server2.registry import register_tool
from photoshop_mcp_server2.ps_adapter.application import PhotoshopApp


def register(mcp):
    """Register session-related tools.

    Args:
        mcp: The MCP server instance.

    Returns:
        list: List of registered tool names.

    """
    registered_tools = []

    def get_session_info() -> dict[str, Any]:
        """Get information about the current Photoshop session.

        Returns:
            dict: Information about the current Photoshop session.

        """
        try:
            print("Getting Photoshop session information using Action Manager")

            # Use Action Manager to get session info
            session_info = ActionManager.get_session_info()
            print(
                f"Session info retrieved successfully: {session_info.get('success', False)}"
            )

            return session_info

        except Exception as e:
            print(f"Error getting Photoshop session info: {e}")
            import traceback

            tb_text = traceback.format_exc()
            traceback.print_exc()

            # Create a detailed error message
            detailed_error = f"Error getting Photoshop session information:\nError: {e!s}\n\nTraceback:\n{tb_text}"

            return {
                "success": False,
                "is_running": False,
                "error": str(e),
                "detailed_error": detailed_error,
            }

    # Register the get_session_info function with a specific name
    tool_name = register_tool(mcp, get_session_info, "get_session_info")
    registered_tools.append(tool_name)

    def get_active_document_info() -> dict[str, Any]:
        """Get detailed information about the active document.

        Returns:
            dict: Detailed information about the active document or an error message.

        """
        try:
            print("Getting active document information using Action Manager")

            # Use Action Manager to get document info
            doc_info = ActionManager.get_active_document_info()
            print(
                f"Document info retrieved successfully: {doc_info.get('success', False)}"
            )

            return doc_info

        except Exception as e:
            print(f"Error getting active document info: {e}")
            import traceback

            tb_text = traceback.format_exc()
            traceback.print_exc()

            # Create a detailed error message
            detailed_error = f"Error getting active document information:\nError: {e!s}\n\nTraceback:\n{tb_text}"

            return {"success": False, "error": str(e), "detailed_error": detailed_error}

    # Register the get_active_document_info function with a specific name
    tool_name = register_tool(mcp, get_active_document_info, "get_active_document_info")
    registered_tools.append(tool_name)

    def get_selection_info() -> dict[str, Any]:
        """Get information about the current selection in the active document.

        Returns:
            dict: Information about the current selection or an error message.

        """
        try:
            ps_app = PhotoshopApp()
            app = ps_app.app

            # Check if there's an active document
            if not hasattr(app, "documents") or not app.documents.length:
                return {
                    "success": True,
                    "has_selection": False,
                    "error": "No active document",
                }

            try:
                selection = app.activeDocument.selection
                if selection is None or not selection.bounds:
                    return {
                        "success": True,
                        "has_selection": False,
                        "error": "No selection",
                    }
                bounds = selection.bounds
                return {
                    "success": True,
                    "has_selection": True,
                    "bounds": {
                        "left": bounds[0],
                        "top": bounds[1],
                        "right": bounds[2],
                        "bottom": bounds[3],
                    }
                }
            except Exception as e:
                print(f"Error getting selection info: {e}")
                return {
                    "success": True,
                    "has_selection": False,
                    "error": str(e),
                }
        except Exception as e:
            import traceback

            tb_text = traceback.format_exc()
            print(f"Error in get_selection_info: {e}")
            print(tb_text)
            return {
                "success": False,
                "has_selection": False,
                "error": str(e),
                "detailed_error": tb_text,
            }

    # Register the get_selection_info function with a specific name
    tool_name = register_tool(mcp, get_selection_info, "get_selection_info")
    registered_tools.append(tool_name)

    def get_selection_info_polygon_points() -> dict:
        """
        Get the current selection's polygon points in the active document by filling the selection with black
        on a temporary layer, copying the result to a new document, saving as a PNG, and analyzing it with OpenCV.

        Returns:
            dict: Information about the selection's polygon points or an error message.
        """
        try:
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            # Check for selection
            try:
                bounds = doc.Selection.Bounds
            except Exception:
                return {
                    "success": True,
                    "has_selection": False,
                    "error": "No selection",
                }

            doc_width = int(doc.Width)
            doc_height = int(doc.Height)
            temp_dir = tempfile.gettempdir()
            mask_path = os.path.join(temp_dir, "ps_selection_mask.png")

            # 1. Add a new layer and fill the selection with black in the main document
            black_layer = doc.ArtLayers.Add()
            black_layer.Name = "TempBlackFill"
            black = win32com.client.Dispatch("Photoshop.SolidColor")
            black.RGB.Red = 0
            black.RGB.Green = 0
            black.RGB.Blue = 0
            doc.Selection.Fill(black, 2, 100, False)  # 2 = Normal blend mode

            # 2. Copy the whole document (merged copy)
            doc.ActiveLayer = black_layer
            black_layer.Copy()

            # 3. In the temp document, paste, translate, flatten, save as PNG
            mask_doc = app.Documents.Add(doc_width, doc_height, doc.Resolution, "TempMask", 1, 2)  # 1=RGB, 2=White background
            mask_doc.Paste()
            # Translate the pasted layer to the original selection position
            pasted_layer = mask_doc.ArtLayers[0]
            # bounds from original doc.Selection.Bounds
            left = int(bounds[0])
            top = int(bounds[1])
            # Move relative to current position
            pasted_layer.Translate(left - pasted_layer.Bounds[0], top - pasted_layer.Bounds[1])
            mask_doc.Flatten()
            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            mask_doc.SaveAs(mask_path, options, True)
            mask_doc.Close(2)  # 2 = don't save

            # 4. Back in the main document, delete the black fill layer
            black_layer.Delete()

            # 5. Use OpenCV to extract polygon points from the mask
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                return {
                    "success": False,
                    "error": "Failed to read mask PNG.",
                }
            # The selection region is black (0), background is white (255)
            _, thresh = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not contours:
                return {
                    "success": True,
                    "has_selection": True,
                    "polygon_points": [],
                    "error": "No contours found in mask.",
                }

            # Filter out contours that are too large (likely the background)
            image_area = doc_width * doc_height
            filtered_contours = [
                c for c in contours if cv2.contourArea(c) < 0.95 * image_area
            ]
            if not filtered_contours:
                return {
                    "success": True,
                    "has_selection": True,
                    "polygon_points": [],
                    "error": "No valid selection contour found.",
                }

            # Take the largest remaining contour and approximate it with approxPolyDP
            contour = max(filtered_contours, key=cv2.contourArea)
            epsilon = 0.001  # You can adjust this value for more/less detail
            approx = cv2.approxPolyDP(contour, epsilon, True)
            points = [[int(pt[0][0]), int(pt[0][1])] for pt in approx]

            # Draw all filtered contours on the mask and show it
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            try:
                os.remove(mask_path)
            except Exception:
                pass

            return {
                "success": True,
                "has_selection": True,
                "polygon_points": points,
            }
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
            }

    # Register the get_selection_info_polygon_points tool
    tool_name = register_tool(mcp, get_selection_info_polygon_points, "get_selection_info_polygon_points")
    registered_tools.append(tool_name)

    return registered_tools
