"""Photoshop application adapter."""

from typing import Optional

import photoshop.api as ps
from photoshop import Session


class PhotoshopApp:
    """Adapter for the Photoshop application.

    This class implements the Singleton pattern to ensure only one instance
    of the Photoshop application is created.
    """

    _instance: Optional["PhotoshopApp"] = None

    def __new__(cls):
        """Create a new instance or return the existing one."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Photoshop application."""
        if not getattr(self, "_initialized", False):
            try:
                # Create a session with new_document action
                self.session = Session(action="new_document", auto_close=False)
                self.app = self.session.app
            except Exception:
                # Fallback to direct Application if Session fails
                self.app = ps.Application()
            self._initialized = True

    def get_version(self):
        """Get the Photoshop version.

        Returns:
            str: The Photoshop version.

        """
        return self.app.version

    def get_active_document(self):
        """Get the active document.

        Returns:
            Document or None: The active document or None if no document is open.

        """
        try:
            if hasattr(self, "session"):
                return self.session.active_document
            return (
                self.app.activeDocument if hasattr(self.app, "activeDocument") else None
            )
        except Exception:
            return None

    def create_document(
        self, width=1000, height=1000, resolution=72, name="Untitled", mode="rgb"
    ):
        """Create a new document.

        Args:
            width (int, optional): Document width in pixels. Defaults to 1000.
            height (int, optional): Document height in pixels. Defaults to 1000.
            resolution (int, optional): Document resolution in PPI. Defaults to 72.
            name (str, optional): Document name. Defaults to "Untitled".
            mode (str, optional): Color mode (rgb, cmyk, etc.). Defaults to "rgb".

        Returns:
            Document: The created document.

        """
        print(
            f"PhotoshopApp.create_document called with: width={width}, height={height}, "
            f"resolution={resolution}, name={name}, mode={mode}"
        )

        # Ensure mode is lowercase for consistency
        mode = mode.lower() if isinstance(mode, str) else "rgb"
        print(f"Normalized mode: {mode}")

        # Get the NewDocumentMode enum value
        try:
            # Map mode string to correct enum name
            mode_map = {
                "rgb": "NewRGB",
                "cmyk": "NewCMYK",
                "grayscale": "NewGray",
                "gray": "NewGray",
                "bitmap": "NewBitmap",
                "lab": "NewLab",
            }

            # Get the correct enum name or default to NewRGB
            enum_name = mode_map.get(mode.lower(), "NewRGB")
            print(f"Getting NewDocumentMode enum for: {mode.lower()} -> {enum_name}")

            # Get the enum value
            mode_enum = getattr(ps.NewDocumentMode, enum_name)
            print(f"Mode enum: {mode_enum}")
        except (AttributeError, TypeError) as e:
            print(f"Error getting mode enum: {e}, defaulting to NewRGB")
            # Default to NewRGB if mode is invalid
            mode_enum = ps.NewDocumentMode.NewRGB

        
        doc = self.app.documents.add(width, height, resolution, name, mode_enum)
        self.app.activeDocument = doc  
        return doc
       

    def open_document(self, file_path):
        """Open an existing document.

        Args:
            file_path (str): Path to the document file.

        Returns:
            Document: The opened document.

        """
        try:
            return self.app.open(file_path)
        except Exception as e:
            import traceback

            traceback.print_exc()
            # Raise a more informative exception
            raise RuntimeError(f"Failed to open document at {file_path}") from e
        

    def execute_javascript(self, script):
        """Execute JavaScript code in Photoshop.

        Args:
            script (str): JavaScript code to execute.

        Returns:
            str: The result of the JavaScript execution.

        """
        # Ensure script returns a valid JSON string
        if not script.strip().endswith(";"):
            script = script.rstrip() + ";"

        # Make sure script returns a value
        if "return " not in script and "JSON.stringify" not in script:
            script = script + "\n'success';"  # Add a default return value

        try:
            # Try to execute with default parameters
            result = self.app.doJavaScript(script)
            if result:
                return result
            return '{"success": true}'  # Return a valid JSON if no result
        except Exception as e:
            print(f"Error executing JavaScript (attempt 1): {e}")

            # Check for specific COM error code -2147212704
            if "-2147212704" in str(e):
                print("Detected COM error -2147212704, trying alternative approach")
                # This is often a dialog-related error, try with a safer script
                safer_script = f"""
                try {{
                    // Disable dialogs
                    var originalDialogMode = app.displayDialogs;
                    app.displayDialogs = DialogModes.NO;

                    // Execute the original script
                    var result = (function() {{
                        {script}
                    }})();

                    // Restore dialog mode
                    app.displayDialogs = originalDialogMode;

                    return result;
                }} catch(e) {{
                    return JSON.stringify({{
                        "error": e.toString(),
                        "success": false
                    }});
                }}
                """
                try:
                    return self.app.doJavaScript(safer_script, None, 1)
                except Exception as e_safer:
                    print(f"Safer script approach failed: {e_safer}")
                    # Continue to other fallbacks

            try:
                # Try with explicit parameters
                # 1 = PsJavaScriptExecutionMode.psNormalMode
                result = self.app.doJavaScript(script, None, 1)
                if result:
                    return result
                return '{"success": true}'  # Return a valid JSON if no result
            except Exception as e2:
                print(f"Error executing JavaScript (attempt 2): {e2}")

                # Try with a different execution mode
                try:
                    # 2 = PsJavaScriptExecutionMode.psInteractiveMode
                    result = self.app.doJavaScript(script, None, 2)
                    if result:
                        return result
                    return '{"success": true}'  # Return a valid JSON if no result
                except Exception as e3:
                    print(f"Error executing JavaScript (attempt 3): {e3}")

                # Last resort: wrap script in a try-catch block if not already wrapped
                if "try {" not in script:
                    wrapped_script = f"""
                    try {{
                        // Disable dialogs
                        var originalDialogMode = app.displayDialogs;
                        app.displayDialogs = DialogModes.NO;

                        // Execute the original script
                        var result = (function() {{
                            {script}
                        }})();

                        // Restore dialog mode
                        app.displayDialogs = originalDialogMode;

                        return result;
                    }} catch(e) {{
                        return JSON.stringify({{
                            "error": e.toString(),
                            "success": false
                        }});
                    }}
                    """
                    try:
                        result = self.app.doJavaScript(wrapped_script, None, 1)
                        if result:
                            return result
                        return '{"success": true}'  # Return a valid JSON if no result
                    except Exception as e4:
                        print(f"Error executing JavaScript (final attempt): {e4}")
                        # Return a valid JSON with error information
                        error_msg = str(e4).replace('"', '\\"')
                        return '{"error": "' + error_msg + '", "success": false}'
                else:
                    # Script already has try-catch, just return the error
                    error_msg = str(e2).replace('"', '\\"')
                    return '{"error": "' + error_msg + '", "success": false}'
