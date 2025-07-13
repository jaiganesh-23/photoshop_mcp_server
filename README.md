# Photoshop MCP Server
This a MCP Server built to automate all the actions that can be performed with photoshop.

## Contents
- [Example Usage](#example-usage)
- [Tools](#tools)
- [Resources](#resources)
- [Middleware](#middleware)
- [Configuration](#configuration)
- [Compatibility and Note](#compatibilty-and-note)
- [Updates](#updates)

### Example Usage

- 1. Perform edits on images with commands from a mcp client without using tools.


- 2. Generate an Instagram post with description and commands from a mcp client.


- 3. Add and edit pieces of images with commands from a mcp client.


### Tools

- `photoshop_create_document` :

Create a new document in Photoshop. Args: width: Document width in pixels. height: Document height in pixels. name: Document name. mode: Color mode (rgb, cmyk, etc.). Defaults to "rgb". Returns: dict: Result of the operation.

- `photoshop_open_document` :

Open an existing document. Args: file_path: Path to the document file. Returns: dict: Result of the operation.

- `photoshop_save_document` :

Save the active document. Args: file_path: Path where to save the document. format: File format (psd, jpg, png). Returns: dict: Result of the operation.

- `photoshop_describe_current_document` :

Saves the current Photoshop document as an image and uses BLIP to generate a description. Deletes the temporary image file after use. Returns: dict: Contains the generated description or error.

- `photoshop_list_open_documents` :

Lists the documents that are currently open in Photoshop. Returns: dict: Contains a list of open document names and their properties.

- `photoshop_select_document` :

Makes the given document the active document by selecting it from the open document tabs. Args: document_name (str): The name of the document to select. Returns: dict: Result of the operation.

- `photoshop_resize_document` :

Resizes the current active Photoshop document to the given width and height in pixels. Args: width (int): The new width in pixels. height (int): The new height in pixels. Returns: dict: Result of the operation.

- `photoshop_flatten_document` :

Flattens the current active Photoshop document. Returns: dict: Result of the operation.
photoshop_screenshot_current_document

Takes a screenshot of the current Photoshop document, resizes it to 300x300, and returns it as path.

- `photoshop_create_text_layer` :

Create a text layer. Args: text: Text content. x: X position. y: Y position. size: Font size. color_r: Red component (0-255). color_g: Green component (0-255). color_b: Blue component (0-255). Returns: dict: Result of the operation.

- `photoshop_create_solid_color_layer` :

Create a solid color fill layer. Args: color_r: Red component (0-255). color_g: Green component (0-255). color_b: Blue component (0-255). name: Layer name. Returns: dict: Result of the operation.

- `photoshop_select_polygon` :

Make a selection using the lasso tool with the given polygon points. Args: points (list): List of (x, y) tuples or lists representing polygon vertices. Returns: dict: Result of the operation.

- `photoshop_blur_polygon` :

Blur a polygonal region defined by points. Args: points (list): List of (x, y) tuples/lists for the polygon. radius (float): Blur radius (default 10.0). Returns: dict: Result of the operation.

- `photoshop_blur_polygon_edges` :

Blur only the edges of a polygonal region defined by points. Args: points (list): List of (x, y) tuples/lists for the polygon. edge_width (int): Width of the edge to blur (in pixels). radius (float): Blur radius. Returns: dict: Result of the operation.

- `photoshop_detect_polygons_with_owlvit_sam2` :

Detect regions in the current Photoshop document using OWLViT and a text prompt, segment with SAM2, and return JSON with label, box, box_score, and polygon points. All detected boxes above threshold are used for segmentation.

- `photoshop_region_generative_fill` :

Inpaint a region defined by a polygon mask using Stable Diffusion Inpainting. The region is filled according to the inpaint_prompt, which is augmented with a BLIP-generated description of the image. Args: polygon_mask (list): List of (x, y) tuples/lists for the polygon. inpaint_prompt (str): Text prompt describing the change to be made. Returns: dict: Result of the operation.

- `photoshop_generative_fill_without_region` :

Given a change prompt the change is applied with inpainting the region to be changed using flux inpainting model. Args: change_prompt (str): Text prompt describing the change to be made in the image. Returns: dict: Result of the operation.

- `photoshop_select_layer` :

Selects the layer with the given name and makes it the active layer. Args: layer_name (str): The name of the layer to select. Returns: dict: Result of the operation.

- `photoshop_delete_layer` :

Deletes the layer with the given name from the current Photoshop document. Args: layer_name (str): The name of the layer to delete. Returns: dict: Result of the operation.

- `photoshop_rotate_layer` :

Rotates the specified layer by the given angle (in degrees). Args: layer_name (str): The name of the layer to rotate. angle (float): The angle in degrees to rotate the layer (positive = clockwise). Returns: dict: Result of the operation.

- `photoshop_get_layers_info` :

Gets the layers in the current Photoshop document and their positions (coordinates and z-axis position). Returns: dict: List of layers with their name, coordinates (x, y), and z-axis (stack) position.

- `photoshop_reposition_layer` :

Changes a layer's position (coordinates and/or z-index) in the current Photoshop document. Args: layer_name (str): The name of the layer to reposition. x (float, optional): New x coordinate (for text or smart object layers). y (float, optional): New y coordinate (for text or smart object layers). z_index (int, optional): New z-index (stack order, 0 = bottom). Returns: dict: Result of the operation.

- `photoshop_apply_crop` :

Crops out a rectangular region from the current Photoshop document. Args: rectangular_points (list): List of four (x, y) tuples/lists representing the rectangle's corners in the order: top-left, top-right, bottom-right, bottom-left. Returns: dict: Result of the operation.

- `photoshop_copy_paste_region` :

Copies a polygonal region from the specified layer and pastes it as a new layer. Args: layer_name (str): The name of the layer to copy from. polygon_points (list): List of (x, y) tuples/lists representing polygon vertices. region_name (str, optional): Name for the new pasted region layer. Defaults to "Copied Region". Returns: dict: Result of the operation.

- `photoshop_set_all_locked` :

Sets the allLocked property of the given layer. Args: layer_name (str): The name of the layer to lock or unlock. value (bool): True to lock, False to unlock. Returns: dict: Result of the operation.

- `photoshop_set_background_layer` :

Sets the isBackgroundLayer property of the given layer. Args: layer_name (str): The name of the layer to set as (or unset from) background. value (bool): True to set as background, False to unset. Returns: dict: Result of the operation.

- `photoshop_apply_spot_heal` :

Spot heals the given polygonal region in the current Photoshop document. Args: polygon_points (list): List of (x, y) tuples/lists representing polygon vertices. Returns: dict: Result of the operation.

- `photoshop_apply_dodge` :

Dodges the interior of the given polygon by: • Copy-Merged into a new layer • Setting that layer's blend mode to Linear Dodge (Add) • Adjusting its Opacity Args: polygon_points (list): List of (x, y) tuples/lists representing polygon vertices. opacity (float): The opacity (0-100) of the dodge layer. Returns: dict: {"success": bool, "message"/"error": str}

- `photoshop_apply_burn` :

Burns the interior of the given polygon by: • Copy-Merged into a new layer • Setting that layer's blend mode to Linear Burn • Adjusting its Opacity Args: polygon_points (list): List of (x, y) tuples/lists representing polygon vertices. opacity (float): The opacity (0-100) of the burn layer. Returns: dict: {"success": bool, "message"/"error": str}

- `photoshop_apply_sponge` :

Simulates a sponge effect: - makes polygon selection - copy merged contents of that region - paste as new layer - apply destructive hue/saturation adjustment on it

- `photoshop_apply_sharpen` :

Sharpens the contents of a polygonal region by: • Selecting the polygon • Copy-merged contents into a new layer • Applying an Unsharp Mask filter (sharpen) Args: polygon_points (list): List of (x, y) tuples/lists defining the polygon. amount (float): Sharpen amount as a percentage (0-500). radius (float): Sharpen radius in pixels (0.1-250). threshold (int): Threshold for edge detection (0-255). Returns: dict: {"success": bool, "message"/"error": str}

- `photoshop_apply_smudge` :

Smudges a polygonal region by: 1. Selecting the polygon 2. Playing back your recorded SmudgeFill Action Args: polygon_points (list): List of (x,y) tuples defining your polygon. action_name (str): Name of the recorded action (e.g. "SmudgeFill"). action_set (str): Name of the action set (e.g. "MySmudgeSet"). Returns: dict: { success: bool, message or error }

- `photoshop_apply_eraser` :

Erases (clears) the pixels inside the given polygonal region on the active layer. Args: polygon_points (list): List of (x, y) tuples/lists defining the polygon vertices. Returns: dict: { "success": bool, "message": str on success or "error": str on failure }

- `photoshop_clip_mask` :

Creates a clipping mask: clips the second_layer inside the first_layer. Args: first_layer (str): The name of the base (mask) layer. second_layer (str): The name of the layer to be clipped (masked). Returns: dict: Result of the operation.

- `photoshop_empty_expand` :

Saves the current active Photoshop document and expands it to the new given size, adding extra white pixels on all sides. The expanded image is opened as a new document. Args: width (int): The new width in pixels. height (int): The new height in pixels. Returns: dict: Result of the operation.

- `photoshop_generative_expand` :

Expands the current Photoshop document to the new size with white pixels on all sides, then performs generative fill on the newly expanded white region using the given prompt. Args: width (int): The new width in pixels. height (int): The new height in pixels. inpaint_prompt (str): The prompt for generative fill on the expanded region. Returns: dict: Result of the operation.

- `photoshop_clear_created_files` :

Clears Files created in using previous tools. Returns: dict: Result of the operation.

- `photoshop_get_session_info` :

Get information about the current Photoshop session. Returns: dict: Information about the current Photoshop session.

- `photoshop_get_active_document_info` :

Get detailed information about the active document. Returns: dict: Detailed information about the active document or an error message.

- `photoshop_get_selection_info`:

Get information about the current selection in the active document. Returns: dict: Information about the current selection or an error message.

- `photoshop_get_selection_info_polygon_points` :

Get the current selection's polygon points in the active document by filling the selection with black on a temporary layer, copying the result to a new document, saving as a PNG, and analyzing it with OpenCV. Returns: dict: Information about the selection's polygon points or an error message.

### Resources

- `get_document_info` :

Get information about the active document. Returns: dict: Information about the active document or an error message.

- `get_layers` :

Get information about the layers in the active document. Returns: dict: Information about layers or an error message.

- `get_photoshop_info` :

Get information about the Photoshop application. Returns: dict: Information about Photoshop.

### Middleware

- `Instructions Middleware`:

Adds instructions to the context on firing list tools in starting the server.
Instructions to be followed in using this server: 
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

It must be explicitly stated to follow the instructions mentioned in context. For most use cases its
not mandatory to mention about following instructions.

### Configuration

Clone the repository and setup uv environment with uv.lock and pyproject.toml files.
After setting up uv run 'uv pip install -e .' from base directory to initialize the mcp server module.

If you dont use uv then install requirements from requirements.txt.

You need create an account on huggingface and groq for api keys to use this server.
Paste your keys in a .env folder on base directory.

VS Code MCP Config

```
{
    "servers": {
        "photoshop-mcp-server": {
            "command": "python", //If you are using global environment for packages or path to env
            "args": [
                "absolute/path/to/photoshop_mcp_server2/server.py"
            ],
            "env": {
				"PS_VERSION": "2024"
			},
			"type": "stdio"
        }
    }
}
```

### Compatibility and Note

This MCP Server only works on windows as it uses windows com modules for communication with photoshop.
The base template, basic tools were taken from the repo https://github.com/loonghao/photoshop-python-api-mcp-server and I have extended tools and capabilities. Do checkout the above repo for more info. 

### Updates
Server logs needs to be patched and more workflows to be added.
