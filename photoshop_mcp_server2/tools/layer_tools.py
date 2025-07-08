"""Layer-related MCP tools."""

import photoshop.api as ps

from photoshop_mcp_server2.ps_adapter.application import PhotoshopApp
from photoshop_mcp_server2.registry import register_tool
import os
import tempfile
import numpy as np
from PIL import Image
import torch
import cv2
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grounded-SAM-2/sam2")))
from build_sam import build_sam2
from sam2_image_predictor import SAM2ImagePredictor
from transformers import OwlViTProcessor, OwlViTForObjectDetection
import tempfile
import os
from PIL import Image, ImageDraw
import numpy as np
import torch
from diffusers import StableDiffusionInpaintPipeline
from transformers import BlipProcessor, BlipForConditionalGeneration
import base64
from io import BytesIO
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from groq import Groq
from PIL import Image
from loguru import logger 
from dotenv import load_dotenv
from gradio_client import Client, file, handle_file
import pythoncom
import requests
import win32com.client
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")))
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
import huggingface_hub
huggingface_hub.login(token=os.getenv("HF_TOKEN"))

def register(mcp):
    """Register layer-related tools.

    Args:
        mcp: The MCP server instance.

    Returns:
        list: List of registered tool names.

    """
    registered_tools = []

    def create_text_layer(
        text: str,
        x: int = 100,
        y: int = 100,
        size: int = 24,
        color_r: int = 0,
        color_g: int = 0,
        color_b: int = 0,
        font: str = "Arial"  # Add a font parameter with a default
    ) -> dict:
        """Create a text layer.

        Args:
            text: Text content.
            x: X position.
            y: Y position.
            size: Font size.
            color_r: Red component (0-255).
            color_g: Green component (0-255).
            color_b: Blue component (0-255).

        Returns:
            dict: Result of the operation.

        """
        # Sanitize text input to ensure it's valid UTF-8
        try:
            # Ensure text is properly encoded/decoded
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="replace")
            else:
                # Force encode and decode to catch any encoding issues
                text = text.encode("utf-8", errors="replace").decode(
                    "utf-8", errors="replace"
                )
            print(f"Sanitized text: '{text}'")
        except Exception as e:
            print(f"Error sanitizing text: {e}")
            return {
                "success": False,
                "error": f"Invalid text encoding: {e!s}",
                "detailed_error": (
                    "The text provided contains invalid characters that cannot be properly encoded in UTF-8. "
                    "Please check the text and try again with valid characters."
                ),
            }

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            print(
                f"Creating text layer: text='{text}', position=({x}, {y}), "
                f"size={size}, color=({color_r}, {color_g}, {color_b})"
            )

            # Create text layer
            print("Adding art layer")
            text_layer = doc.artLayers.add()
            print("Setting layer kind to TextLayer")
            text_layer.kind = ps.LayerKind.TextLayer

            # Configure text
            print("Configuring text item")
            text_item = text_layer.textItem
            text_item.contents = text
            text_item.position = [x, y]
            text_item.size = size
            text_item.font = font  # Set the font here

            # Configure color
            print("Setting text color")
            text_color = ps.SolidColor()
            text_color.rgb.red = color_r
            text_color.rgb.green = color_g
            text_color.rgb.blue = color_b
            text_item.color = text_color

            print(f"Text layer created successfully: {text_layer.name}")
            return {"success": True, "layer_name": text_layer.name}
        except Exception as e:
            print(f"Error creating text layer: {e}")
            import traceback

            tb_text = traceback.format_exc()
            traceback.print_exc()

            # Create a detailed error message
            detailed_error = (
                f"Error creating text layer with parameters:\n"
                f"  text: {text}\n"
                f"  position: ({x}, {y})\n"
                f"  size: {size}\n"
                f"  color: ({color_r}, {color_g}, {color_b})\n\n"
                f"Error: {e!s}\n\n"
                f"Traceback:\n{tb_text}"
            )

            return {
                "success": False,
                "error": str(e),
                "detailed_error": detailed_error,
                "parameters": {
                    "text": text,
                    "x": x,
                    "y": y,
                    "size": size,
                    "color": [color_r, color_g, color_b],
                },
            }

    # Register the create_text_layer function with a specific name
    tool_name = register_tool(mcp, create_text_layer, "create_text_layer")
    registered_tools.append(tool_name)

    def create_solid_color_layer(
        color_r: int = 255, color_g: int = 0, color_b: int = 0, name: str = "Color Fill"
    ) -> dict:
        """Create a solid color fill layer.

        Args:
            color_r: Red component (0-255).
            color_g: Green component (0-255).
            color_b: Blue component (0-255).
            name: Layer name.

        Returns:
            dict: Result of the operation.

        """
        # Sanitize name input to ensure it's valid UTF-8
        try:
            # Ensure name is properly encoded/decoded
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            else:
                # Force encode and decode to catch any encoding issues
                name = name.encode("utf-8", errors="replace").decode(
                    "utf-8", errors="replace"
                )
            print(f"Sanitized layer name: '{name}'")
        except Exception as e:
            print(f"Error sanitizing layer name: {e}")
            return {
                "success": False,
                "error": f"Invalid name encoding: {e!s}",
                "detailed_error": (
                    "The layer name provided contains invalid characters that cannot be properly encoded in UTF-8. "
                    "Please check the name and try again with valid characters."
                ),
            }

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            print(
                f"Creating solid color layer: name='{name}', color=({color_r}, {color_g}, {color_b})"
            )

            # Escape special characters in the name for JavaScript
            escaped_name = (
                name.replace('"', '\\"')
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
            )

            # Create a solid color fill layer using JavaScript
            js_script = f"""
            try {{
                var doc = app.activeDocument;
                var newLayer = doc.artLayers.add();
                newLayer.name = "{escaped_name}";

                // Create a solid color fill
                var solidColor = new SolidColor();
                solidColor.rgb.red = {color_r};
                solidColor.rgb.green = {color_g};
                solidColor.rgb.blue = {color_b};

                // Fill the layer with the color
                doc.selection.selectAll();
                doc.selection.fill(solidColor);
                doc.selection.deselect();
                'success';
            }} catch(e) {{
                'Error: ' + e.toString();
            }}
            """

            print("Executing JavaScript to create solid color layer")
            result = ps_app.execute_javascript(js_script)
            print(f"JavaScript execution result: {result}")

            # Check if JavaScript returned an error
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while creating solid color layer: {result}",
                }

            print(f"Solid color layer created successfully: {name}")
            return {"success": True, "layer_name": name}
        except Exception as e:
            print(f"Error creating solid color layer: {e}")
            import traceback

            tb_text = traceback.format_exc()
            traceback.print_exc()

            # Create a detailed error message
            detailed_error = (
                f"Error creating solid color layer with parameters:\n"
                f"  name: {name}\n"
                f"  color: ({color_r}, {color_g}, {color_b})\n\n"
                f"Error: {e!s}\n\n"
                f"Traceback:\n{tb_text}"
            )

            return {
                "success": False,
                "error": str(e),
                "detailed_error": detailed_error,
                "parameters": {"name": name, "color": [color_r, color_g, color_b]},
            }

    # Register the create_solid_color_layer function with a specific name
    tool_name = register_tool(mcp, create_solid_color_layer, "create_solid_color_layer")
    registered_tools.append(tool_name)

    def select_polygon(points: list) -> dict:
        """
        Make a selection using the lasso tool with the given polygon points.

        Args:
            points (list): List of (x, y) tuples or lists representing polygon vertices.

        Returns:
            dict: Result of the operation.
        """
        if not points or not isinstance(points, list) or len(points) < 3:
            return {
                "success": False,
                "error": "At least 3 points are required to make a polygon selection.",
            }

        # Flatten the points for JavaScript: [[x1, y1], [x2, y2], ...] -> [x1, y1, x2, y2, ...]
        try:
            flat_points = []
            for pt in points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat_points.extend([float(pt[0]), float(pt[1])])
                else:
                    return {
                        "success": False,
                        "error": f"Invalid point format: {pt}. Each point must be a list or tuple of two numbers.",
                    }
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        # Prepare JavaScript array string
        js_points = ",".join(str(p) for p in flat_points)

        js_script = f"""
        try {{
            var doc = app.activeDocument;
            var pts = [{js_points}];
            var polygonArray = [];
            for (var i = 0; i < pts.length; i += 2) {{
                polygonArray.push([pts[i], pts[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(polygonArray);
            'success';
        }} catch(e) {{
            'Error: ' + e.toString();
        }}
        """

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while making polygon selection: {result}",
                }
            return {"success": True, "message": "Polygon selection made."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"points": points},
            }

    # Register the select_polygon function
    tool_name = register_tool(mcp, select_polygon, "select_polygon")
    registered_tools.append(tool_name)

    def blur_polygon(points: list, radius: float = 10.0) -> dict:
        """
        Blur a polygonal region defined by points.

        Args:
            points (list): List of (x, y) tuples/lists for the polygon.
            radius (float): Blur radius (default 10.0).

        Returns:
            dict: Result of the operation.
        """
        if not points or not isinstance(points, list) or len(points) < 3:
            return {
                "success": False,
                "error": "At least 3 points are required to define a polygon.",
            }

        # Flatten the points for JavaScript
        try:
            flat_points = []
            for pt in points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat_points.extend([float(pt[0]), float(pt[1])])
                else:
                    return {
                        "success": False,
                        "error": f"Invalid point format: {pt}. Each point must be a list or tuple of two numbers.",
                    }
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        js_points = ",".join(str(p) for p in flat_points)

        js_script = f"""
        try {{
            var doc = app.activeDocument;
            var pts = [{js_points}];
            var polygonArray = [];
            for (var i = 0; i < pts.length; i += 2) {{
                polygonArray.push([pts[i], pts[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(polygonArray);
            doc.activeLayer.applyGaussianBlur({radius});
            'success';
        }} catch(e) {{
            'Error: ' + e.toString();
        }}
        """

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while blurring polygon: {result}",
                }
            return {"success": True, "message": "Polygon blurred."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"points": points, "radius": radius},
            }

    # Register the blur_polygon function
    tool_name = register_tool(mcp, blur_polygon, "blur_polygon")
    registered_tools.append(tool_name)

    def blur_polygon_edges(points: list, edge_width: int = 10, radius: float = 10.0) -> dict:
        """
        Blur only the edges of a polygonal region defined by points.

        Args:
            points (list): List of (x, y) tuples/lists for the polygon.
            edge_width (int): Width of the edge to blur (in pixels).
            radius (float): Blur radius.

        Returns:
            dict: Result of the operation.
        """
        if not points or not isinstance(points, list) or len(points) < 3:
            return {
                "success": False,
                "error": "At least 3 points are required to define a polygon.",
            }

        # Flatten the points for JavaScript
        try:
            flat_points = []
            for pt in points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat_points.extend([float(pt[0]), float(pt[1])])
                else:
                    return {
                        "success": False,
                        "error": f"Invalid point format: {pt}. Each point must be a list or tuple of two numbers.",
                    }
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        js_points = ",".join(str(p) for p in flat_points)

        js_script = f"""
        try {{
            var doc = app.activeDocument;
            var pts = [{js_points}];
            var polygonArray = [];
            for (var i = 0; i < pts.length; i += 2) {{
                polygonArray.push([pts[i], pts[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(polygonArray);

            // Save the original selection
            doc.selection.store(doc.channels.add());

            // Contract selection to get the inner polygon
            doc.selection.contract({edge_width});
            // Save the inner selection
            doc.selection.store(doc.channels.add());

            // Reselect the original polygon
            doc.selection.load(doc.channels[doc.channels.length-2], ps.SelectionType.REPLACE);
            // Subtract the inner selection
            doc.selection.load(doc.channels[doc.channels.length-1], ps.SelectionType.SUBTRACT);

            // Apply blur to the edge selection
            doc.activeLayer.applyGaussianBlur({radius});

            // Deselect and remove temporary channels
            doc.selection.deselect();
            doc.channels[doc.channels.length-1].remove();
            doc.channels[doc.channels.length-1].remove();

            'success';
        }} catch(e) {{
            'Error: ' + e.toString();
        }}
        """

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while blurring polygon edges: {result}",
                }
            return {"success": True, "message": "Polygon edges blurred."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"points": points, "edge_width": edge_width, "radius": radius},
            }

    # Register the blur_polygon_edges function
    tool_name = register_tool(mcp, blur_polygon_edges, "blur_polygon_edges")
    registered_tools.append(tool_name)

    def mask_to_polygons(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []
        # Find the contour with the largest area
        max_contour = max(contours, key=cv2.contourArea)
        polygon = max_contour.squeeze().tolist()
        if isinstance(polygon[0], int):
            polygon = [polygon]
        return [polygon]

    def detect_polygons_with_owlvit_sam2(
        prompt: str,
        sam2_ckpt: str = str(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grounded-SAM-2/checkpoints/sam2.1_hiera_large.pt"))),
        sam2_cfg: str = "configs/sam2.1/sam2.1_hiera_l.yaml",
        box_threshold: float = 0.20
    ) -> dict:
        """
        Detect regions in the current Photoshop document using OWLViT and a text prompt,
        segment with SAM2, and return JSON with label, box, box_score, and polygon points.
        All detected boxes above threshold are used for segmentation.
        """
        try:
            # 1. Save current Photoshop document as PNG

            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "ps_active_doc_for_detection.png")

            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            doc.SaveAs(temp_path, options, True)

            # 2. Run OWLViT detection
            processor = OwlViTProcessor.from_pretrained("google/owlvit-large-patch14")
            model = OwlViTForObjectDetection.from_pretrained("google/owlvit-large-patch14")
            model.eval()

            image = Image.open(temp_path).convert("RGB")
            inputs = processor(text=[prompt], images=image, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs = model(**inputs)
            target_sizes = torch.tensor([image.size[::-1]])
            results = processor.post_process_object_detection(
                outputs, threshold=box_threshold, target_sizes=target_sizes
            )[0]
            boxes = results["boxes"].cpu().numpy()
            scores = results["scores"].cpu().numpy()

            if len(boxes) == 0:
                return {"success": True, "results": [], "message": "No bounding boxes found for the prompt."}

            # 3. Segment with SAM2 for all boxes
            device = "cuda" if torch.cuda.is_available() else "cpu"
            sam2_model = build_sam2(config_file=sam2_cfg, ckpt_path=sam2_ckpt, device=device)
            sam2_predictor = SAM2ImagePredictor(sam2_model)
            img_np = np.array(image)
            sam2_predictor.set_image(img_np)

            results_json = []
            for i, (box, score) in enumerate(zip(boxes, scores)):
                masks, mask_scores, logits = sam2_predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    box=np.expand_dims(box, axis=0),
                    multimask_output=False,
                )
                if masks.ndim == 4:
                    masks = masks.squeeze(1)
                x0, y0, x1, y1 = map(int, box)
                mask = masks[0].astype(np.uint8) * 255
                polygons = mask_to_polygons(mask)
                results_json.append({
                    "label": prompt,
                    "box": [x0, y0, x1, y1],
                    "box_score": float(score),
                    "polygon": polygons
                })

            # Clean up temp file
            try:
                os.remove(temp_path)
            except Exception:
                pass

            return {"success": True, "results": results_json}
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "detailed_error": traceback.format_exc(),
            }

    # Register the detect_polygons_with_owlvit_sam2 function
    tool_name = register_tool(mcp, detect_polygons_with_owlvit_sam2, "detect_polygons_with_owlvit_sam2")
    registered_tools.append(tool_name)

    def region_generative_fill(
        polygon_mask: list,
        inpaint_prompt: str
    ) -> dict:
        """
        Inpaint a region defined by a polygon mask using Stable Diffusion Inpainting.
        The region is filled according to the inpaint_prompt, which is augmented with a BLIP-generated description of the image.

        Args:
            polygon_mask (list): List of (x, y) tuples/lists for the polygon.
            inpaint_prompt (str): Text prompt describing the change to be made.
        Returns:
            dict: Result of the operation.
        """

        # 1. Download current PSD as image (PNG)
        try:

            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            temp_dir = tempfile.gettempdir()
            temp_img_path = os.path.join(temp_dir, "ps_active_doc_for_inpaint.png")

            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            doc.SaveAs(temp_img_path, options, True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to export PSD as image: {e}"
            }

        # 2. Load image and create mask
        try:
            image = Image.open(temp_img_path).convert("RGB")
            W, H = image.size

            # Create black-and-white mask
            mask = Image.new("L", (W, H), 0)
            draw = ImageDraw.Draw(mask)
            # Ensure polygon_mask is a list of tuples
            polygon = [(float(x), float(y)) for x, y in polygon_mask]
            draw.polygon(polygon, fill=255)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create mask: {e}"
            }

        # 3. Get image description using LangChain, ChatGroq, and Llama-4
        try:

            # Convert image and mask to base64
            def pil_to_base64(img):
                img = img.resize((300,300)) # Resize for faster processing
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode("utf-8")

            image_b64 = pil_to_base64(image)
            mask_b64 = pil_to_base64(mask)

            # Compose prompt template with examples
            prompt_template = f"""
            You are an expert Photoshop assistant. Given an image (base64 PNG), 
            a mask (base64 PNG, white region is the area to edit), and an inpaint prompt, 
            generate a detailed, context-aware prompt for a generative fill model. 
            The inpaint prompt describes the change to be made in the masked region.
            White region in the mask indicates the area to be edited,
            while the black region indicates the area to be left unchanged.
            The prompt should describe what should appear in the final generated image 
            with simple words. Give the complete description of the image without treating 
            the masked region separately, but rather as part of the whole image context.
            Compare where and what the white pixels in the mask represents in the image and process the
            information carefully along with the inpaint prompt to generate the full prompt. Do not
            misinterpret the mask, image and the inpaint prompt. Dont confuse the white pixels in the 
            image as the region to be edited, they are just part of the image. Do not add unnecessary details
            in the prompt, just describe the image as it is with the changes specified in the inpaint prompt(for ex:
            when a sun is told to be added, dont mention clouds,sky in the prompt if they are not present in the original image).

            Examples:
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a sun in the selected region"
            full_prompt: "A man with green shirt in the center. A sun in the top left corner."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "replace the cat with a dog"
            full_prompt: "A living room with a brown sofa. A dog sitting on the sofa."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the tree"
            full_prompt: "A mountain landscape with a clear sky and no tree in the foreground."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a red car"
            full_prompt: "A city street with buildings on both sides. A red car parked on the right side."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "change the sky to sunset"
            full_prompt: "A beach with palm trees. The sky is orange and pink with a sunset."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a person riding a bicycle"
            full_prompt: "A park with green grass and trees. A person riding a bicycle on the path."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "make the house blue"
            full_prompt: "A suburban street with a blue house and a white fence."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a flock of birds in the sky"
            full_prompt: "A lake surrounded by mountains. A flock of birds flying in the sky."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the person from the bench"
            full_prompt: "A park with a wooden bench under a tree. The bench is empty."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a rainbow over the waterfall"
            full_prompt: "A waterfall in a forest. A rainbow arches over the waterfall."
            ---

            Your turn:
            Write only the full prompt and nothing else like above examples. The above examples uses blank base64 images and masks, but give 
            your answer according to the image and mask provided below, dont add unnecessary details in the prompt.

            full_prompt:
            """

            # Call ChatGroq with Llama-4
            messages = [
                (
                    "user",
                    [
                        {"type": "text", "text": prompt_template},
                        {"type": "text", "text": "image:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"},
                        {"type": "text", "text": "mask:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{mask_b64}"},
                        {"type": "text", "text": f"inpaint_prompt: {inpaint_prompt}"}
                    ]
                )
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
            chat = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
            chain = prompt | chat
            response = chain.invoke(
                {
                    "image_b64": image_b64,
                    "mask_b64": mask_b64,
                    "inpaint_prompt": inpaint_prompt
                }
            )

            # Extract the full prompt from the response
            logger.info(f"LLM response: {response.content}")
            full_prompt = response.content.strip()
            if full_prompt.startswith('"') and full_prompt.endswith('"'):
                full_prompt = full_prompt[1:-1]
        except Exception as e:
            # If LLM fails, fallback to original prompt
            logger.error(f"LLM failed: {e}")
            full_prompt = inpaint_prompt

        # 4. Inpaint with Hugging Face API
        try:
            client = Client("ameerazam08/FLUX.1-dev-Inpainting-Model-Beta-GPU", hf_token=os.getenv("HF_TOKEN"))
            # Save mask as PNG in temp_dir
            mask_path = os.path.join(temp_dir, "ps_mask_for_inpaint.png")
            mask.save(mask_path)

            # Create a new image: copy of original, but white where mask is white
            combined = image.copy()
            mask_np = np.array(mask)
            combined_np = np.array(combined)
            white = np.ones_like(combined_np) * 255
            combined_np[mask_np == 255] = white[mask_np == 255]
            combined_img = Image.fromarray(combined_np)
            combined_path = os.path.join(temp_dir, "ps_combined_for_inpaint.png")
            combined_img.save(combined_path)

            response = client.predict(
                input_image_editor={"background":handle_file(str(temp_img_path).replace("\\","/")),"layers":[handle_file(str(mask_path).replace("\\","/"))],"composite":handle_file(str(combined_path).replace("\\","/"))},
                prompt=full_prompt,
                negative_prompt="",
                controlnet_conditioning_scale=0.9,
                guidance_scale=3.5,
                seed=124,
                num_inference_steps=24,
                true_guidance_scale=3.5,
                api_name="/process",
            )
            # The response from Gradio Client is a URL or path to the generated image
            if isinstance(response, str) and (response.startswith("http://") or response.startswith("https://")):
                # Download the image from the URL
                resp = requests.get(response)
                result = Image.open(BytesIO(resp.content)).convert("RGB")
            elif isinstance(response, str) and os.path.exists(response):
                result = Image.open(response).convert("RGB")
            elif isinstance(response, dict) and "output" in response:
                # Some Gradio APIs return a dict with 'output'
                output = response["output"]
                if isinstance(output, str) and (output.startswith("http://") or output.startswith("https://")):
                    resp = requests.get(output)
                    result = Image.open(BytesIO(resp.content)).convert("RGB")
                elif isinstance(output, str) and os.path.exists(output):
                    result = Image.open(output).convert("RGB")
                else:
                    raise RuntimeError("Unknown output format from Gradio response")
            else:
                raise RuntimeError("Unknown response format from Gradio client")
        except Exception as e:
            return {
                "success": False,
                "error": f"Inpainting failed: {e}"
            }

        # 5. Save result and open in Photoshop as new document
        try:
            result_path = os.path.join(temp_dir, "inpaint_result.png")
            result.save(result_path)

            # Open in Photoshop as new document
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            app.Open(result_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to open result in Photoshop: {e}"
            }

        return {
            "success": True,
            "message": "Region inpainted and result opened in Photoshop.",
            "result_path": result_path,
            "used_prompt": full_prompt
        }

    # Register the tool 
    tool_name = register_tool(mcp, region_generative_fill, "region_generative_fill")
    registered_tools.append(tool_name)

    def detect_region_generative_fill(
        detection_prompt: str,
        inpaint_prompt: str
    ) -> dict:
        """
        Detect a region in the current Photoshop document using OWLViT and a detection prompt,
        segment with SAM2, and inpaint the detected region using Flux.
        The inpainting prompt is constructed using an LLM chain as in region_generative_fill.

        Args:
            detection_prompt (str): Description of the region to detect.
            inpaint_prompt (str): Edit to be made in the detected region.

        Returns:
            dict: Result of the operation.
        """
        # 1. Download current PSD as image (PNG)
        try:
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            temp_dir = tempfile.gettempdir()
            temp_img_path = os.path.join(temp_dir, "ps_active_doc_for_detect_inpaint.png")

            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            doc.SaveAs(temp_img_path, options, True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to export PSD as image: {e}"
            }

        # 2. Run OWLViT detection
        try:
            processor = OwlViTProcessor.from_pretrained("google/owlvit-large-patch14")
            model = OwlViTForObjectDetection.from_pretrained("google/owlvit-large-patch14")
            model.eval()

            image = Image.open(temp_img_path).convert("RGB")
            W, H = image.size
            inputs = processor(text=[detection_prompt], images=image, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs = model(**inputs)
            target_sizes = torch.tensor([image.size[::-1]])
            results = processor.post_process_object_detection(
                outputs, threshold=0.20, target_sizes=target_sizes
            )[0]
            boxes = results["boxes"].cpu().numpy()
            scores = results["scores"].cpu().numpy()

            if len(boxes) == 0:
                return {"success": False, "error": "No region detected for the given prompt."}

            # Use the best box (highest score)
            best_idx = np.argmax(scores)
            best_box = boxes[best_idx]
        except Exception as e:
            return {
                "success": False,
                "error": f"OWLViT detection failed: {e}"
            }

        # 3. Segment with SAM2
        try:
            sam2_ckpt = str(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Grounded-SAM-2/checkpoints/sam2.1_hiera_large.pt")))
            sam2_cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"
            device = "cuda" if torch.cuda.is_available() else "cpu"
            sam2_model = build_sam2(config_file=sam2_cfg, ckpt_path=sam2_ckpt, device=device)
            sam2_predictor = SAM2ImagePredictor(sam2_model)
            img_np = np.array(image)
            sam2_predictor.set_image(img_np)

            masks, mask_scores, logits = sam2_predictor.predict(
                point_coords=None,
                point_labels=None,
                box=np.expand_dims(best_box, axis=0),
                multimask_output=False,
            )
            if masks.ndim == 4:
                masks = masks.squeeze(1)
            best_mask = masks[0].astype(np.uint8) * 255
        except Exception as e:
            return {
                "success": False,
                "error": f"SAM2 segmentation failed: {e}"
            }

        # 4. Prepare mask as polygon for prompt construction (optional, not needed for inpainting)
        # 5. Prepare base64 for image and mask
        def pil_to_base64(img):
            img = img.resize((300, 300))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

        mask_pil = Image.fromarray(best_mask).convert("L")
        image_b64 = pil_to_base64(image)
        mask_b64 = pil_to_base64(mask_pil)

        # 6. Construct full prompt using LLM chain (like region_generative_fill)
        try:
            prompt_template = f"""
            You are an expert Photoshop assistant. Given an image (base64 PNG), 
            a mask (base64 PNG, white region is the area to edit), and an inpaint prompt, 
            generate a detailed, context-aware prompt for a generative fill model. 
            The inpaint prompt describes the change to be made in the masked region.
            White region in the mask indicates the area to be edited,
            while the black region indicates the area to be left unchanged.
            The prompt should describe what should appear in the final generated image 
            with simple words. Give the complete description of the image without treating 
            the masked region separately, but rather as part of the whole image context.
            Compare where and what the white pixels in the mask represents in the image and process the
            information carefully along with the inpaint prompt to generate the full prompt. Do not
            misinterpret the mask, image and the inpaint prompt. Dont confuse the white pixels in the 
            image as the region to be edited, they are just part of the image. Do not add unnecessary details
            in the prompt, just describe the image as it is with the changes specified in the inpaint prompt(for ex:
            when a sun is told to be added, dont mention clouds,sky in the prompt if they are not present in the original image).

            Examples:
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a sun in the selected region"
            full_prompt: "A man with green shirt in the center. A sun in the top left corner."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "replace the cat with a dog"
            full_prompt: "A living room with a brown sofa. A dog sitting on the sofa."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the tree"
            full_prompt: "A mountain landscape with a clear sky and no tree in the foreground."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a red car"
            full_prompt: "A city street with buildings on both sides. A red car parked on the right side."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "change the sky to sunset"
            full_prompt: "A beach with palm trees. The sky is orange and pink with a sunset."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a person riding a bicycle"
            full_prompt: "A park with green grass and trees. A person riding a bicycle on the path."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "make the house blue"
            full_prompt: "A suburban street with a blue house and a white fence."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a flock of birds in the sky"
            full_prompt: "A lake surrounded by mountains. A flock of birds flying in the sky."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the person from the bench"
            full_prompt: "A park with a wooden bench under a tree. The bench is empty."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a rainbow over the waterfall"
            full_prompt: "A waterfall in a forest. A rainbow arches over the waterfall."
            ---

            Your turn:
            Write only the full prompt and nothing else like above examples. The above examples uses blank base64 images and masks, but give 
            your answer according to the image and mask provided below, dont add unnecessary details in the prompt.

            full_prompt:
            """

            messages = [
                (
                    "user",
                    [
                        {"type": "text", "text": prompt_template},
                        {"type": "text", "text": "image:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"},
                        {"type": "text", "text": "mask:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{mask_b64}"},
                        {"type": "text", "text": f"inpaint_prompt: {inpaint_prompt}"}
                    ]
                )
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
            chat = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
            chain = prompt | chat
            response = chain.invoke(
                {
                    "image_b64": image_b64,
                    "mask_b64": mask_b64,
                    "inpaint_prompt": inpaint_prompt
                }
            )

            # Extract the full prompt from the response
            logger.info(f"LLM response: {response.content}")
            full_prompt = response.content.strip()
            if full_prompt.startswith('"') and full_prompt.endswith('"'):
                full_prompt = full_prompt[1:-1]
        except Exception as e:
            # If LLM fails, fallback to original prompt
            logger.error(f"LLM failed: {e}")
            full_prompt = inpaint_prompt

        # 7. Inpaint with Hugging Face API
        try:
            client = Client("ameerazam08/FLUX.1-dev-Inpainting-Model-Beta-GPU")
            mask = Image.fromarray(best_mask).convert("L")
            # Save mask as PNG in temp_dir
            mask_path = os.path.join(temp_dir, "ps_mask_for_detect_inpaint.png")
            mask.save(mask_path)

            # Create a new image: copy of original, but white where mask is white
            combined = image.copy()
            mask_np = np.array(mask)
            combined_np = np.array(combined)
            white = np.ones_like(combined_np) * 255
            combined_np[mask_np == 255] = white[mask_np == 255]
            combined_img = Image.fromarray(combined_np)
            combined_path = os.path.join(temp_dir, "ps_combined_for_detect_inpaint.png")
            combined_img.save(combined_path)

            response = client.predict(
                input_image_editor={"background":handle_file(str(temp_img_path).replace("\\","/")),"layers":[handle_file(str(mask_path).replace("\\","/"))],"composite":handle_file(str(combined_path).replace("\\","/"))},
                prompt=full_prompt,
                negative_prompt="",
                controlnet_conditioning_scale=0.9,
                guidance_scale=3.5,
                seed=124,
                num_inference_steps=24,
                true_guidance_scale=3.5,
                api_name="/process"
            )
            # The response from Gradio Client is a URL or path to the generated image
            if isinstance(response, str) and (response.startswith("http://") or response.startswith("https://")):
                # Download the image from the URL
                resp = requests.get(response)
                result = Image.open(BytesIO(resp.content)).convert("RGB")
            elif isinstance(response, str) and os.path.exists(response):
                result = Image.open(response).convert("RGB")
            elif isinstance(response, dict) and "output" in response:
                # Some Gradio APIs return a dict with 'output'
                output = response["output"]
                if isinstance(output, str) and (output.startswith("http://") or output.startswith("https://")):
                    resp = requests.get(output)
                    result = Image.open(BytesIO(resp.content)).convert("RGB")
                elif isinstance(output, str) and os.path.exists(output):
                    result = Image.open(output).convert("RGB")
                else:
                    raise RuntimeError("Unknown output format from Gradio response")
            else:
                raise RuntimeError("Unknown response format from Gradio client")
        except Exception as e:
            return {
                "success": False,
                "error": f"Inpainting failed: {e}"
            }

        # 8. Save result and open in Photoshop as new document
        try:
            result_path = os.path.join(temp_dir, "detect_inpaint_result.png")
            result.save(result_path)

            # Open in Photoshop as new document
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            app.Open(result_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to open result in Photoshop: {e}"
            }

        return {
            "success": True,
            "message": "Region detected, inpainted, and result opened in Photoshop.",
            "result_path": result_path,
            "used_prompt": full_prompt
        }

    # Register the tool
    tool_name = register_tool(mcp, detect_region_generative_fill, "detect_region_generative_fill")
    registered_tools.append(tool_name)

    def select_layer(layer_name: str) -> dict:
        """
        Selects the layer with the given name and makes it the active layer.

        Args:
            layer_name (str): The name of the layer to select.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            found = False
            # Try top-level artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                try:
                    for layer in doc.artLayers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                doc.activeLayer = layer
                                found = True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            # Try searching in layerSets (groups)
            if not found:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                try:
                                    for layer in group.artLayers:
                                        try:
                                            if hasattr(layer, "name") and layer.name == layer_name:
                                                doc.activeLayer = layer
                                                found = True
                                                break
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                    except Exception:
                        pass

            if not found:
                return {"success": False, "error": f"Layer '{layer_name}' not found."}
            return {"success": True, "message": f"Layer '{layer_name}' selected."}
        except Exception as e:
            return {"success": False, "error": f"Failed to select layer: {e}"}

    # Register the select_layer function
    tool_name = register_tool(mcp, select_layer, "select_layer")
    registered_tools.append(tool_name)

    def delete_layer(layer_name: str) -> dict:
        """
        Deletes the layer with the given name from the current Photoshop document.

        Args:
            layer_name (str): The name of the layer to delete.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            found = False
            # Try deleting from artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                try:
                    for layer in doc.artLayers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                layer.delete()
                                found = True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            # Try searching and deleting in layer sets (groups)
            if not found:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                try:
                                    for layer in group.artLayers:
                                        try:
                                            if hasattr(layer, "name") and layer.name == layer_name:
                                                layer.delete()
                                                found = True
                                                break
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                    except Exception:
                        pass

            if not found:
                return {"success": False, "error": f"Layer '{layer_name}' not found."}
            return {"success": True, "message": f"Layer '{layer_name}' deleted."}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete layer: {e}"}

    # Register the delete_layer function
    tool_name = register_tool(mcp, delete_layer, "delete_layer")
    registered_tools.append(tool_name)

    def rotate_layer(layer_name: str, angle: float) -> dict:
        """
        Rotates the specified layer by the given angle (in degrees).

        Args:
            layer_name (str): The name of the layer to rotate.
            angle (float): The angle in degrees to rotate the layer (positive = clockwise).

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            found = False
            # Try rotating from artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                try:
                    for layer in doc.artLayers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                doc.activeLayer = layer
                                layer.rotate(angle)
                                found = True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            # Try searching and rotating in layer sets (groups)
            if not found:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                try:
                                    for layer in group.artLayers:
                                        try:
                                            if hasattr(layer, "name") and layer.name == layer_name:
                                                doc.activeLayer = layer
                                                layer.rotate(angle)
                                                found = True
                                                break
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                    except Exception:
                        pass

            if not found:
                return {"success": False, "error": f"Layer '{layer_name}' not found."}
            return {"success": True, "message": f"Layer '{layer_name}' rotated by {angle} degrees."}
        except Exception as e:
            return {"success": False, "error": f"Failed to rotate layer: {e}"}

    # Register the rotate_layer function
    tool_name = register_tool(mcp, rotate_layer, "rotate_layer")
    registered_tools.append(tool_name)

    def get_layers_info() -> dict:
        """
        Gets the layers in the current Photoshop document and their positions (coordinates and z-axis position).

        Returns:
            dict: List of layers with their name, coordinates (x, y), and z-axis (stack) position.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            layers_info = []

            def collect_layers(layers, z_offset=0):
                for idx in range(layers.length):
                    layer = layers.getByIndex(idx)
                    logger.info(f"Processing layer: {layer.name} (index: {idx}, z_offset: {z_offset})")
                    # Check for group/layerSet by trying to access artLayers and layerSets presence
                    is_group = False
                    try:
                        has_artlayers = False
                        try:
                            has_artlayers = hasattr(layer, "artLayers")
                        except Exception:
                            has_artlayers = False
                        if has_artlayers:
                            try:
                                has_length = hasattr(layer.artLayers, "length")
                            except Exception:
                                has_length = False
                            if has_length:
                                try:
                                    if layer.artLayers.length > 0:
                                        is_group = True
                                except Exception:
                                    is_group = False
                    except Exception:
                        is_group = False

                    if is_group:
                        logger.info("inside group/layerSet")
                        collect_layers(layer.artLayers, z_offset)
                        try:
                            has_layersets = False
                            try:
                                has_layersets = hasattr(layer, "layerSets")
                            except Exception:
                                has_layersets = False
                            if has_layersets:
                                try:
                                    has_length = hasattr(layer.layerSets, "length")
                                except Exception:
                                    has_length = False
                                if has_length and layer.layerSets.length > 0:
                                    for gidx in range(layer.layerSets.length):
                                        sublayer_set = layer.layerSets.getByIndex(gidx)
                                        try:
                                            has_sub_artlayers = False
                                            try:
                                                has_sub_artlayers = hasattr(sublayer_set, "artLayers")
                                            except Exception:
                                                has_sub_artlayers = False
                                            if has_sub_artlayers:
                                                try:
                                                    has_length = hasattr(sublayer_set.artLayers, "length")
                                                except Exception:
                                                    has_length = False
                                                if has_length and sublayer_set.artLayers.length > 0:
                                                    collect_layers(sublayer_set.artLayers, z_offset)
                                            # end if has_sub_artlayers
                                        except Exception:
                                            pass
                        except Exception:
                            pass
                    else:
                        # It's a normal layer
                        info = {
                            "name": layer.name,
                            "z_index": z_offset + idx,
                        }
                        # Try to get position if it's a text or smart object layer
                        try:
                            try:
                                has_kind = False
                                try:
                                    has_kind = hasattr(layer, "kind")
                                    info["kind"] = layer.kind
                                except Exception:
                                    info["kind"] = "unknown"
                                    has_kind = False
                                has_textitem = False
                                try:
                                    has_textitem = hasattr(layer, "textItem")
                                except Exception:
                                    has_textitem = False
                                if has_kind and has_textitem:
                                    try:
                                        if hasattr(layer.textItem, "width"):
                                            info["width"] = float(layer.textItem.width)
                                        if hasattr(layer.textItem, "height"):
                                            info["height"] = float(layer.textItem.height)
                                    except Exception:
                                        info["width"] = "unknown"
                                        info["height"] = "unknown"
                                    pos = layer.textItem.position
                                    info["x"] = float(pos[0])
                                    info["y"] = float(pos[1])
                            except Exception:
                                pass
                            try:
                                has_bounds = False
                                try:
                                    has_bounds = hasattr(layer, "bounds")
                                except Exception:
                                    has_bounds = False
                                if has_bounds:
                                    bounds = layer.bounds
                                    info["x"] = float(bounds[0])
                                    info["y"] = float(bounds[1])
                                    info["width"] = float(bounds[2]) - float(bounds[0])
                                    info["height"] = float(bounds[3]) - float(bounds[1])
                            except Exception:
                                pass
                            try:
                                if hasattr(layer, "isBackgroundLayer") and layer.isBackgroundLayer:
                                    info["is_background"] = True
                                else:
                                    info["is_background"] = False
                            except Exception:
                                info["is_background"] = False
                            try:
                                if hasattr(layer, "allLocked") and layer.allLocked:
                                    info["locked"] = True
                                else:
                                    info["locked"] = False
                            except Exception:
                                info["locked"] = False
                        except Exception:
                            pass
                        layers_info.append(info)

            # Top-level ArtLayers
            logger.info(f"{doc.artLayers.length} top-level art layers found.")
            try:
                has_artlayers = False
                try:
                    has_artlayers = hasattr(doc, "artLayers")
                except Exception:
                    has_artlayers = False
                if has_artlayers:
                    has_length = False
                    try:
                        has_length = hasattr(doc.artLayers, "length")
                    except Exception:
                        has_length = False
                    if has_length and doc.artLayers.length > 0:
                        collect_layers(doc.artLayers)
            except Exception:
                pass
            # Top-level LayerSets (groups)
            try:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    has_length = False
                    try:
                        has_length = hasattr(doc.layerSets, "length")
                    except Exception:
                        has_length = False
                    if has_length and doc.layerSets.length > 0:
                        for gidx in range(doc.layerSets.length):
                            layer_set = doc.layerSets.getByIndex(gidx)
                            try:
                                has_artlayers = False
                                try:
                                    has_artlayers = hasattr(layer_set, "artLayers")
                                except Exception:
                                    has_artlayers = False
                                if has_artlayers:
                                    has_length = False
                                    try:
                                        has_length = hasattr(layer_set.artLayers, "length")
                                    except Exception:
                                        has_length = False
                                    if has_length and layer_set.artLayers.length > 0:
                                        collect_layers(layer_set.artLayers)
                            except Exception:
                                pass
            except Exception:
                pass

            return {"success": True, "layers": layers_info}
        except Exception as e:
            return {"success": False, "error": f"Failed to get layer positions: {e}"}

        # Register the get_layer_positions function
    tool_name = register_tool(mcp, get_layers_info, "get_layers_info")
    registered_tools.append(tool_name)

    def reposition_layer(layer_name: str, x: float = None, y: float = None, z_index: int = None) -> dict:
        """
        Changes a layer's position (coordinates and/or z-index) in the current Photoshop document.

        Args:
            layer_name (str): The name of the layer to reposition.
            x (float, optional): New x coordinate (for text or smart object layers).
            y (float, optional): New y coordinate (for text or smart object layers).
            z_index (int, optional): New z-index (stack order, 0 = bottom).

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            # Find the layer and its parent collection
            found_layer = None
            parent_layers = None

            # Collect all artLayers and artLayers in layerSets, handling hasattr with try/except
            all_layers_collections = []
            try:
                has_artlayers = False
                try:
                    has_artlayers = hasattr(doc, "artLayers")
                except Exception:
                    has_artlayers = False
                if has_artlayers:
                    all_layers_collections.append(doc.artLayers)
            except Exception:
                pass

            try:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                all_layers_collections.append(group.artLayers)
                    except Exception:
                        pass
            except Exception:
                pass

            for layers in all_layers_collections:
                try:
                    for layer in layers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                found_layer = layer
                                parent_layers = layers
                                break
                        except Exception:
                            continue
                except Exception:
                    continue

            if not found_layer:
                return {"success": False, "error": f"Layer '{layer_name}' not found."}

            # Move (x, y) for text layers or smart objects
            if x is not None or y is not None:
                try:
                    has_kind = False
                    has_textitem = False
                    try:
                        has_kind = hasattr(found_layer, "kind")
                    except Exception:
                        has_kind = False
                    try:
                        has_textitem = hasattr(found_layer, "textItem")
                    except Exception:
                        has_textitem = False
                    if has_kind and has_textitem:
                        pos = list(found_layer.textItem.position)
                        if x is not None:
                            pos[0] = float(x)
                        if y is not None:
                            pos[1] = float(y)
                        found_layer.textItem.position = pos
                    else:
                        has_translate = False
                        try:
                            has_translate = hasattr(found_layer, "translate")
                        except Exception:
                            has_translate = False
                        if has_translate:
                            bounds = found_layer.bounds
                            cur_x, cur_y = float(bounds[0]), float(bounds[1])
                            dx = float(x) - cur_x if x is not None else 0
                            dy = float(y) - cur_y if y is not None else 0
                            found_layer.translate(dx, dy)
                except Exception as e:
                    return {"success": False, "error": f"Failed to move layer position: {e}"}

            # Move z-index (stack order)
            if z_index is not None and parent_layers is not None:
                try:
                    cur_index = None
                    for idx, layer in enumerate(parent_layers):
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                cur_index = idx
                                break
                        except Exception:
                            continue
                    if cur_index is not None and cur_index != z_index:
                        # Move the layer to the new index using Photoshop's move method
                        # Photoshop's move method: layer.move(relativeObject, ElementPlacement.PLACEBEFORE/PLACEAFTER)
                        # We'll move the layer before the target index layer
                        target_index = max(0, min(z_index, len(parent_layers) - 1))
                        target_layer = parent_layers.getByIndex(target_index)
                        # Import ElementPlacement from photoshop.api if not already imported
                        # If moving up, move before; if moving down, move after
                        if target_index < cur_index:
                            found_layer.move(target_layer, ps.ElementPlacement.PlaceBefore)
                        else:
                            found_layer.move(target_layer, ps.ElementPlacement.PlaceAfter)
                except Exception as e:
                    return {"success": False, "error": f"Failed to change z-index: {e}"}

            return {"success": True, "message": f"Layer '{layer_name}' repositioned."}
        except Exception as e:
            return {"success": False, "error": f"Failed to reposition layer: {e}"}

    # Register the reposition_layer function
    tool_name = register_tool(mcp, reposition_layer, "reposition_layer")
    registered_tools.append(tool_name)

    def apply_crop(rectangular_points: list) -> dict:
        """
        Crops out a rectangular region from the current Photoshop document.

        Args:
            rectangular_points (list): List of four (x, y) tuples/lists representing the rectangle's corners
                                    in the order: top-left, top-right, bottom-right, bottom-left.

        Returns:
            dict: Result of the operation.
        """
        if (
            not rectangular_points
            or not isinstance(rectangular_points, list)
            or len(rectangular_points) != 4
        ):
            return {
                "success": False,
                "error": "rectangular_points must be a list of four (x, y) tuples/lists representing the rectangle's corners.",
            }

        try:
            # Calculate the bounding box from the four points
            xs = [float(pt[0]) for pt in rectangular_points]
            ys = [float(pt[1]) for pt in rectangular_points]
            left, right = min(xs), max(xs)
            top, bottom = min(ys), max(ys)

            # Prepare JavaScript for cropping
            js_script = f"""
            try {{
                var doc = app.activeDocument;
                doc.crop([
                    UnitValue({left}, "px"),
                    UnitValue({top}, "px"),
                    UnitValue({right}, "px"),
                    UnitValue({bottom}, "px")
                ]);
                'success';
            }} catch(e) {{
                'Error: ' + e.toString();
            }}
            """

            ps_app = PhotoshopApp()
            doc = ps_app.get_active_document()
            if not doc:
                return {"success": False, "error": "No active document"}

            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while cropping: {result}",
                }
            return {"success": True, "message": "Document cropped to the specified rectangle."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"rectangular_points": rectangular_points},
            }

    # Register the apply_crop function
    tool_name = register_tool(mcp, apply_crop, "apply_crop")
    registered_tools.append(tool_name)

    def copy_paste_region(layer_name: str, polygon_points: list, region_name: str = "Copied Region") -> dict:
        """
        Copies a polygonal region from the specified layer and pastes it as a new layer.

        Args:
            layer_name (str): The name of the layer to copy from.
            polygon_points (list): List of (x, y) tuples/lists representing polygon vertices.
            region_name (str, optional): Name for the new pasted region layer. Defaults to "Copied Region".

        Returns:
            dict: Result of the operation.
        """
        if not polygon_points or not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {
                "success": False,
                "error": "At least 3 points are required to define a polygon region.",
            }

        # Flatten the points for JavaScript: [[x1, y1], [x2, y2], ...] -> [x1, y1, x2, y2, ...]
        try:
            flat_points = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat_points.extend([float(pt[0]), float(pt[1])])
                else:
                    return {
                        "success": False,
                        "error": f"Invalid point format: {pt}. Each point must be a list or tuple of two numbers.",
                    }
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        js_points = ",".join(str(p) for p in flat_points)
        js_layer_name = layer_name.replace("'", "\\'")
        js_region_name = region_name.replace("'", "\\'")

        js_script = f"""
        try {{
            var doc = app.activeDocument;
            var targetLayer = null;
            for (var i = 0; i < doc.layers.length; i++) {{
                if (doc.layers[i].name == '{js_layer_name}') {{
                    targetLayer = doc.layers[i];
                    break;
                }}
            }}
            if (!targetLayer) throw new Error('Layer not found: {js_layer_name}');
            doc.activeLayer = targetLayer;
            var pts = [{js_points}];
            var polygonArray = [];
            for (var i = 0; i < pts.length; i += 2) {{
                polygonArray.push([pts[i], pts[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(polygonArray);
            doc.selection.copy();
            var pastedLayer = doc.paste();
            pastedLayer.name = '{js_region_name}';
            doc.selection.deselect();
            'success';
        }} catch(e) {{
            'Error: ' + e.toString();
        }}
        """

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while copying and pasting region: {result}",
                }
            return {"success": True, "message": f"Region copied and pasted as new layer '{region_name}'."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"layer_name": layer_name, "polygon_points": polygon_points, "region_name": region_name},
            }

    # Register the copy_paste_region function
    tool_name = register_tool(mcp, copy_paste_region, "copy_paste_region")
    registered_tools.append(tool_name)

    def set_all_locked(layer_name: str, value: bool = True) -> dict:
        """
        Sets the allLocked property of the given layer.

        Args:
            layer_name (str): The name of the layer to lock or unlock.
            value (bool): True to lock, False to unlock.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            found = False
            # Try top-level artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                try:
                    for layer in doc.artLayers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                if hasattr(layer, "allLocked"):
                                    layer.allLocked = value
                                    found = True
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

            # Try searching in layerSets (groups)
            if not found:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                try:
                                    for layer in group.artLayers:
                                        try:
                                            if hasattr(layer, "name") and layer.name == layer_name:
                                                if hasattr(layer, "allLocked"):
                                                    layer.allLocked = value
                                                    found = True
                                                    break
                                        except Exception:
                                            continue
                                except Exception:
                                    continue
                            if found:
                                break
                    except Exception:
                        pass

            if not found:
                return {"success": False, "error": f"Layer '{layer_name}' not found or cannot set allLocked."}
            return {"success": True, "message": f"Layer '{layer_name}' allLocked set to {value}."}
        except Exception as e:
            return {"success": False, "error": f"Failed to set allLocked: {e}"}

    # Register the set_all_locked function
    tool_name = register_tool(mcp, set_all_locked, "set_all_locked")
    registered_tools.append(tool_name)

    def set_background_layer(layer_name: str, value: bool = True) -> dict:
        """
        Sets the isBackgroundLayer property of the given layer.

        Args:
            layer_name (str): The name of the layer to set as (or unset from) background.
            value (bool): True to set as background, False to unset.

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            found = False
            # Try top-level artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                try:
                    for layer in doc.artLayers:
                        try:
                            if hasattr(layer, "name") and layer.name == layer_name:
                                if hasattr(layer, "isBackgroundLayer"):
                                    layer.isBackgroundLayer = value
                                    found = True
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

            # Try searching in layerSets (groups)
            if not found:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    try:
                        for group in doc.layerSets:
                            has_group_artlayers = False
                            try:
                                has_group_artlayers = hasattr(group, "artLayers")
                            except Exception:
                                has_group_artlayers = False
                            if has_group_artlayers:
                                try:
                                    for layer in group.artLayers:
                                        try:
                                            if hasattr(layer, "name") and layer.name == layer_name:
                                                if hasattr(layer, "isBackgroundLayer"):
                                                    layer.isBackgroundLayer = value
                                                    found = True
                                                    break
                                        except Exception:
                                            continue
                                    if found:
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        pass

            if not found:
                return {"success": False, "error": f"Layer '{layer_name}' not found or cannot set isBackgroundLayer."}
            return {"success": True, "message": f"Layer '{layer_name}' isBackgroundLayer set to {value}."}
        except Exception as e:
            return {"success": False, "error": f"Failed to set background layer: {e}"}

    # Register the set_background_layer function
    tool_name = register_tool(mcp, set_background_layer, "set_background_layer")
    registered_tools.append(tool_name)

    def apply_spot_heal(polygon_points: list) -> dict:
        """
        Spot heals the given polygonal region in the current Photoshop document.

        Args:
            polygon_points (list): List of (x, y) tuples/lists representing polygon vertices.

        Returns:
            dict: Result of the operation.
        """
        if not polygon_points or not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {
                "success": False,
                "error": "At least 3 points are required to define a polygon region.",
            }

        # Flatten the points for JavaScript: [[x1, y1], [x2, y2], ...] -> [x1, y1, x2, y2, ...]
        try:
            flat_points = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat_points.extend([float(pt[0]), float(pt[1])])
                else:
                    return {
                        "success": False,
                        "error": f"Invalid point format: {pt}. Each point must be a list or tuple of two numbers.",
                    }
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        js_points = ",".join(str(p) for p in flat_points)
        logger.info(f"Spot healing polygon points: {js_points}")
        js_script = f"""
        try {{
            var doc = app.activeDocument;
            var pts = [{js_points}];
            var polygonArray = [];
            for (var i = 0; i < pts.length; i += 2) {{
                polygonArray.push([pts[i], pts[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(polygonArray);

            // Content-Aware Fill using ActionDescriptor
            var idfill = stringIDToTypeID("fill");
            var desc = new ActionDescriptor();
            var idusing = charIDToTypeID("Usng");
            var idcontentAware = stringIDToTypeID("contentAware");
            desc.putEnumerated(idusing, charIDToTypeID("FlCn"), idcontentAware);
            desc.putUnitDouble(charIDToTypeID("Opct"), charIDToTypeID("#Prc"), 100.0);
            desc.putEnumerated(charIDToTypeID("Md  "), charIDToTypeID("BlnM"), charIDToTypeID("Nrml"));
            executeAction(idfill, desc, DialogModes.NO);

            doc.selection.deselect();
            'success';
        }} catch(e) {{
            'Error: ' + e.toString();
        }}
        """

        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while spot healing: {result}",
                }
            return {"success": True, "message": "Spot healing applied to the polygon region."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"polygon_points": polygon_points},
            }

    # Register the apply_spot_heal function
    tool_name = register_tool(mcp, apply_spot_heal, "apply_spot_heal")
    registered_tools.append(tool_name)


    def apply_dodge(polygon_points: list, opacity: float = 25.0) -> dict:
        """
        Dodges the interior of the given polygon by:
        • Copy-Merged into a new layer
        • Setting that layer's blend mode to Linear Dodge (Add)
        • Adjusting its Opacity

        Args:
            polygon_points (list): List of (x, y) tuples/lists representing polygon vertices.
            opacity (float): The opacity (0-100) of the dodge layer.

        Returns:
            dict: {"success": bool, "message"/"error": str}
        """
        # Validate & flatten
        if not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {"success": False, "error": "Need at least 3 points to form a polygon."}
        try:
            flat = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat.extend([float(pt[0]), float(pt[1])])
                else:
                    raise ValueError(f"Bad point: {pt}")
        except Exception as e:
            return {"success": False, "error": f"Point processing failed: {e}"}

        # Clamp opacity
        opacity = max(0, min(100, opacity))

        js = f"""
        try {{
            var doc = app.activeDocument;

            // 1) Build & select the polygon
            var raw = [{', '.join(str(v) for v in flat)}];
            var poly = [];
            for (var i = 0; i < raw.length; i += 2) {{
                poly.push([raw[i], raw[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // 2) Copy Merged and Paste into new layer
            executeAction(stringIDToTypeID('copyMerged'), undefined, DialogModes.NO);
            var newLayer = doc.paste();

            // 3) Set blend mode to Linear Dodge (Add)
            newLayer.blendMode = BlendMode.LINEARDODGE;

            // 4) Set opacity
            newLayer.opacity = {opacity};

            // 5) Deselect
            doc.selection.deselect();

            'success';
        }} catch (e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        doc = ps.get_active_document()
        if not doc:
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {"success": True, "message": f"Polygon dodged with Linear Dodge layer at {opacity}% opacity."}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detailed_error": traceback.format_exc()}


    # Register the apply_dodge function
    tool_name = register_tool(mcp, apply_dodge, "apply_dodge")
    registered_tools.append(tool_name)


    def apply_burn(polygon_points: list, opacity: float = 25.0) -> dict:
        """
        Burns the interior of the given polygon by:
        • Copy-Merged into a new layer
        • Setting that layer's blend mode to Linear Burn
        • Adjusting its Opacity

        Args:
            polygon_points (list): List of (x, y) tuples/lists representing polygon vertices.
            opacity (float): The opacity (0-100) of the burn layer.

        Returns:
            dict: {"success": bool, "message"/"error": str}
        """
        # Validate & flatten
        if not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {"success": False, "error": "Need at least 3 points to form a polygon."}
        try:
            flat = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat.extend([float(pt[0]), float(pt[1])])
                else:
                    raise ValueError(f"Bad point: {pt}")
        except Exception as e:
            return {"success": False, "error": f"Point processing failed: {e}"}

        # Clamp opacity
        opacity = max(0, min(100, opacity))

        js = f"""
        try {{
            var doc = app.activeDocument;

            // 1) Build & select the polygon
            var raw = [{', '.join(str(v) for v in flat)}];
            var poly = [];
            for (var i = 0; i < raw.length; i += 2) {{
                poly.push([raw[i], raw[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // 2) Copy Merged and Paste into new layer
            executeAction(stringIDToTypeID('copyMerged'), undefined, DialogModes.NO);
            var newLayer = doc.paste();

            // 3) Set blend mode to Linear Burn
            newLayer.blendMode = BlendMode.LINEARBURN;

            // 4) Set opacity
            newLayer.opacity = {opacity};

            // 5) Deselect
            doc.selection.deselect();

            'success';
        }} catch (e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        doc = ps.get_active_document()
        if not doc:
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {"success": True, "message": f"Polygon burned with Linear Burn layer at {opacity}% opacity."}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detailed_error": traceback.format_exc()}
        
    # Register the apply_burn function
    tool_name = register_tool(mcp, apply_burn, "apply_burn")
    registered_tools.append(tool_name)

    def apply_sponge(polygon_points: list, saturation_delta: float = -50.0) -> dict:
        """
        Simulates a sponge effect:
        - makes polygon selection
        - copy merged contents of that region
        - paste as new layer
        - apply destructive hue/saturation adjustment on it
        """

        if not polygon_points or len(polygon_points) < 3:
            return {"success": False, "error": "At least 3 points are needed to define a polygon."}

        try:
            flat = []
            for pt in polygon_points:
                flat.extend([float(pt[0]), float(pt[1])])
        except Exception as e:
            return {"success": False, "error": f"Invalid polygon points: {e}"}

        sat = max(-100, min(100, saturation_delta))
        coords_js = ", ".join(str(x) for x in flat)

        js = f"""
        try {{
            var doc = app.activeDocument;
            // build polygon selection
            var coords = [{coords_js}];
            var poly = [];
            for (var i=0; i<coords.length; i+=2) {{
                poly.push([coords[i], coords[i+1]]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // copy merged
            doc.selection.copy(true);

            // paste as new layer
            var pasted = doc.paste();
            pasted.name = "SpongeEffect";

            // make sure it is active
            doc.activeLayer = pasted;

            // apply destructive hue/saturation to active layer
            var idHStr = charIDToTypeID( "HStr" );
            var desc337 = new ActionDescriptor();
            var idpresetKind = stringIDToTypeID( "presetKind" );
            var idpresetKindType = stringIDToTypeID( "presetKindType" );
            var idpresetKindCustom = stringIDToTypeID( "presetKindCustom" );
            desc337.putEnumerated( idpresetKind, idpresetKindType, idpresetKindCustom );
            var idClrz = charIDToTypeID( "Clrz" );
            desc337.putBoolean( idClrz, false );
            var idAdjs = charIDToTypeID( "Adjs" );
            var list10 = new ActionList();
            var desc338 = new ActionDescriptor();
            var idH = charIDToTypeID( "H   " );
            desc338.putInteger( idH, 0 );
            var idStrt = charIDToTypeID( "Strt" );
            desc338.putInteger( idStrt, {sat} );
            var idLght = charIDToTypeID( "Lght" );
            desc338.putInteger( idLght, 0 );
            var idHsttwo = charIDToTypeID( "Hst2" );
            list10.putObject( idHsttwo, desc338 );
            desc337.putList( idAdjs, list10 );
            executeAction( idHStr, desc337, DialogModes.NO );

            // deselect
            doc.selection.deselect();

            'success';
        }} catch(e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        doc = ps.get_active_document()
        if not doc:
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {
                "success": True,
                "message": f"Sponge-like effect applied destructively to new layer with saturation {sat}."
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "detailed_error": traceback.format_exc(),
            }

    # Register the apply_sponge function
    tool_name = register_tool(mcp, apply_sponge, "apply_sponge")
    registered_tools.append(tool_name)

    def apply_sharpen(polygon_points: list,
                  amount: float = 100.0,
                  radius: float = 1.0,
                  threshold: int = 0) -> dict:
        """
        Sharpens the contents of a polygonal region by:
        • Selecting the polygon
        • Copy-merged contents into a new layer
        • Applying an Unsharp Mask filter (sharpen)
        
        Args:
            polygon_points (list): List of (x, y) tuples/lists defining the polygon.
            amount (float): Sharpen amount as a percentage (0-500).
            radius (float): Sharpen radius in pixels (0.1-250).
            threshold (int): Threshold for edge detection (0-255).
        
        Returns:
            dict: {"success": bool, "message"/"error": str}
        """
        # Validate & flatten
        if not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {"success": False, "error": "Need at least 3 points to form a polygon."}
        try:
            flat = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat.extend([float(pt[0]), float(pt[1])])
                else:
                    raise ValueError(f"Bad point: {pt}")
        except Exception as e:
            return {"success": False, "error": f"Point processing failed: {e}"}

        # Clamp parameters
        amt = max(0.0, min(500.0, amount))
        rad = max(0.1, min(250.0, radius))
        thr = max(0, min(255, threshold))

        coords_js = ", ".join(str(v) for v in flat)

        js = f"""
        try {{
            var doc = app.activeDocument;

            // 1) Build & select the polygon
            var raw = [{coords_js}];
            var poly = [];
            for (var i = 0; i < raw.length; i += 2) {{
                poly.push([ raw[i], raw[i+1] ]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // 2) Copy merged & paste as new layer
            doc.selection.copy(true);  // copyMerged = true
            var pasted = doc.paste();
            pasted.name = "SharpenEffect";
            doc.activeLayer = pasted;

            // 3) Apply Unsharp Mask (sharpen)
            var idUnsM = charIDToTypeID("UnsM");
            var desc = new ActionDescriptor();
            desc.putUnitDouble(charIDToTypeID("Amnt"), charIDToTypeID("#Prc"), {amt});
            desc.putUnitDouble(charIDToTypeID("Rds "), charIDToTypeID("#Pxl"), {rad});
            desc.putInteger(charIDToTypeID("Thsh"), {thr});
            executeAction(idUnsM, desc, DialogModes.NO);

            // 4) Deselect
            doc.selection.deselect();

            'success';
        }} catch(e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        doc = ps.get_active_document()
        if not doc:
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {
                "success": True,
                "message": f"SharpenEffect layer created with Unsharp Mask (amount={amt}%, radius={rad}px, threshold={thr})."
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "detailed_error": traceback.format_exc()
            }

    # Register the apply_sharpen function
    tool_name = register_tool(mcp, apply_sharpen, "apply_sharpen")
    registered_tools.append(tool_name)

    import math

    def apply_smudge(polygon_points: list,
                            action_name: str = "SmudgeFill",
                            action_set: str = "MySmudgeSet"
                            ) -> dict:
        """
        Smudges a polygonal region by:
        1. Selecting the polygon
        2. Playing back your recorded SmudgeFill Action

        Args:
            polygon_points (list): List of (x,y) tuples defining your polygon.
            action_name (str): Name of the recorded action (e.g. "SmudgeFill").
            action_set (str): Name of the action set (e.g. "MySmudgeSet").

        Returns:
            dict: { success: bool, message or error }
        """
        # Validate & flatten
        if not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {"success": False, "error": "At least 3 points are required for a polygon."}
        try:
            flat = [float(c) for pt in polygon_points for c in pt]
        except Exception as e:
            return {"success": False, "error": f"Invalid polygon points: {e}"}

        coords_js = ", ".join(str(v) for v in flat)

        js = f"""
        try {{
            var doc = app.activeDocument;

            // 1) Build & select polygon
            var raw = [{coords_js}];
            var poly = [];
            for (var i = 0; i < raw.length; i += 2) {{
                poly.push([ raw[i], raw[i+1] ]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // 2) Play your recorded SmudgeFill action
            app.doAction("{action_name}", "{action_set}");

            'success';
        }} catch(e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        if not ps.get_active_document():
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {"success": True, "message": "SmudgeFill action applied along polygon."}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detailed_error": traceback.format_exc()}


    # Register the apply_smudge_filter function
    tool_name = register_tool(mcp, apply_smudge, "apply_smudge")
    registered_tools.append(tool_name)

    def apply_eraser(polygon_points: list) -> dict:
        """
        Erases (clears) the pixels inside the given polygonal region on the active layer.

        Args:
            polygon_points (list): List of (x, y) tuples/lists defining the polygon vertices.

        Returns:
            dict: {
                "success": bool,
                "message": str on success or "error": str on failure
            }
        """
        # Validate & flatten input
        if not isinstance(polygon_points, list) or len(polygon_points) < 3:
            return {"success": False, "error": "At least 3 points are required to define a polygon."}
        try:
            flat = []
            for pt in polygon_points:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    flat.extend([float(pt[0]), float(pt[1])])
                else:
                    raise ValueError(f"Invalid point: {pt}")
        except Exception as e:
            return {"success": False, "error": f"Error processing points: {e}"}

        coords_js = ", ".join(str(v) for v in flat)

        js = f"""
        try {{
            var doc = app.activeDocument;

            // 1) Build & select the polygon
            var raw = [{coords_js}];
            var poly = [];
            for (var i = 0; i < raw.length; i += 2) {{
                poly.push([ raw[i], raw[i+1] ]);
            }}
            doc.selection.deselect();
            doc.selection.select(poly);

            // 2) Clear the selection (erase to transparent)
            doc.selection.clear();

            // 3) Deselect
            doc.selection.deselect();

            'success';
        }} catch (e) {{
            'error: ' + e.toString();
        }}
        """

        ps = PhotoshopApp()
        doc = ps.get_active_document()
        if not doc:
            return {"success": False, "error": "No active Photoshop document."}

        try:
            result = ps.execute_javascript(js)
            if isinstance(result, str) and result.startswith("error:"):
                return {"success": False, "error": result}
            return {"success": True, "message": "Region erased successfully."}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detailed_error": traceback.format_exc()}

    # Register the apply_eraser function
    tool_name = register_tool(mcp, apply_eraser, "apply_eraser")
    registered_tools.append(tool_name)

    def clip_mask(first_layer: str, second_layer: str) -> dict:
        """
        Creates a clipping mask: clips the second_layer inside the first_layer.

        Args:
            first_layer (str): The name of the base (mask) layer.
            second_layer (str): The name of the layer to be clipped (masked).

        Returns:
            dict: Result of the operation.
        """
        ps_app = PhotoshopApp()
        doc = ps_app.get_active_document()
        if not doc:
            return {"success": False, "error": "No active document"}

        try:
            # Find both layers
            base_layer = None
            clip_layer = None

            # Search top-level artLayers
            has_artlayers = False
            try:
                has_artlayers = hasattr(doc, "artLayers")
            except Exception:
                has_artlayers = False
            if has_artlayers:
                for layer in doc.artLayers:
                    try:
                        if hasattr(layer, "name"):
                            if layer.name == first_layer:
                                base_layer = layer
                            if layer.name == second_layer:
                                clip_layer = layer
                    except Exception:
                        continue

            # Search in layerSets if not found
            if not base_layer or not clip_layer:
                has_layersets = False
                try:
                    has_layersets = hasattr(doc, "layerSets")
                except Exception:
                    has_layersets = False
                if has_layersets:
                    for group in doc.layerSets:
                        has_group_artlayers = False
                        try:
                            has_group_artlayers = hasattr(group, "artLayers")
                        except Exception:
                            has_group_artlayers = False
                        if has_group_artlayers:
                            for layer in group.artLayers:
                                try:
                                    if hasattr(layer, "name"):
                                        if layer.name == first_layer:
                                            base_layer = layer
                                        if layer.name == second_layer:
                                            clip_layer = layer
                                except Exception:
                                    continue

            if not base_layer or not clip_layer:
                return {"success": False, "error": "One or both layers not found."}

            # Use JavaScript to perform the clipping mask operation
            escaped_first_layer = first_layer.replace('"', '\\"')
            escaped_second_layer = second_layer.replace('"', '\\"')

            js_script = f"""
            try {{
                var doc = app.activeDocument;
                var base = null, clip = null;
                for (var i = 0; i < doc.layers.length; i++) {{
                    if (doc.layers[i].name == "{escaped_first_layer}") base = doc.layers[i];
                    if (doc.layers[i].name == "{escaped_second_layer}") clip = doc.layers[i];
                }}
                if (!base || !clip) throw new Error("Layer(s) not found");
                doc.activeLayer = clip;
                var clippingMask = charIDToTypeID ("GrpL");
                executeAction(clippingMask, undefined, DialogModes.NO);
                'success';
            }} catch(e) {{
                'Error: ' + e.toString();
            }}
            """

            result = ps_app.execute_javascript(js_script)
            if result and isinstance(result, str) and result.startswith("Error:"):
                return {
                    "success": False,
                    "error": result,
                    "detailed_error": f"JavaScript error while creating clipping mask: {result}",
                }
            return {"success": True, "message": f"Layer '{second_layer}' clipped inside '{first_layer}'."}
        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"first_layer": first_layer, "second_layer": second_layer},
            }

    # Register the clip_mask function
    tool_name = register_tool(mcp, clip_mask, "clip_mask")
    registered_tools.append(tool_name)

    def empty_expand(width: int, height: int) -> dict:
        """
        Saves the current active Photoshop document and expands it to the new given size,
        adding extra white pixels on all sides. The expanded image is opened as a new document.

        Args:
            width (int): The new width in pixels.
            height (int): The new height in pixels.

        Returns:
            dict: Result of the operation.
        """

        try:
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            # Save current document as PNG
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "ps_active_doc_for_expand.png")
            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            doc.SaveAs(temp_path, options, True)

            # Open with PIL and expand canvas
            image = Image.open(temp_path).convert("RGBA")
            orig_w, orig_h = image.size

            # Calculate padding
            pad_left = (width - orig_w) // 2
            pad_top = (height - orig_h) // 2
            pad_right = width - orig_w - pad_left
            pad_bottom = height - orig_h - pad_top

            if pad_left < 0 or pad_top < 0 or pad_right < 0 or pad_bottom < 0:
                return {
                    "success": False,
                    "error": "New size must be greater than or equal to the original size in both dimensions."
                }

            # Create new white background
            new_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            new_img.paste(image, (pad_left, pad_top))

            # Save expanded image
            expanded_path = os.path.join(temp_dir, "ps_expanded_doc.png")
            new_img.save(expanded_path)

            # Open in Photoshop as new document
            app.Open(expanded_path)

            return {
                "success": True,
                "message": f"Document expanded to {width}x{height} with white border and opened in Photoshop.",
                "expanded_path": expanded_path
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

    # Register the empty_expand function
    tool_name = register_tool(mcp, empty_expand, "empty_expand")
    registered_tools.append(tool_name)

    def generative_expand(width: int, height: int, inpaint_prompt: str) -> dict:
        """
        Expands the current Photoshop document to the new size with white pixels on all sides,
        then performs generative fill on the newly expanded white region using the given prompt.

        Args:
            width (int): The new width in pixels.
            height (int): The new height in pixels.
            inpaint_prompt (str): The prompt for generative fill on the expanded region.

        Returns:
            dict: Result of the operation.
        """

        try:
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            doc = app.ActiveDocument

            # Save current document as PNG
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "ps_active_doc_for_expand.png")
            options = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            doc.SaveAs(temp_path, options, True)

            # Open with PIL and expand canvas
            image = Image.open(temp_path).convert("RGBA")
            orig_w, orig_h = image.size

            # Calculate padding
            pad_left = (width - orig_w) // 2
            pad_top = (height - orig_h) // 2
            pad_right = width - orig_w - pad_left
            pad_bottom = height - orig_h - pad_top

            if pad_left < 0 or pad_top < 0 or pad_right < 0 or pad_bottom < 0:
                return {
                    "success": False,
                    "error": "New size must be greater than or equal to the original size in both dimensions."
                }

            # Create new white background
            new_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            new_img.paste(image, (pad_left, pad_top))

            # Save expanded image
            expanded_path = os.path.join(temp_dir, "ps_expanded_doc.png")
            new_img.save(expanded_path)

            # Open in Photoshop as new document and set as active
            app.Open(expanded_path)
            doc = app.ActiveDocument

            # Create mask for the expanded region (white border)
            mask = Image.new("L", (width, height), 0)
            draw = ImageDraw.Draw(mask)
            # Draw the full expanded region as white
            draw.rectangle([0, 0, width, height], fill=255)
            # Draw the original image region as black (not to be inpainted)
            draw.rectangle([pad_left, pad_top, pad_left + orig_w, pad_top + orig_h-10], fill=0)

            # 3. Get image description using LangChain, ChatGroq, and Llama-4
            def pil_to_base64(img):
                img = img.resize((300, 300))  # Resize for faster processing
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode("utf-8")

            image_b64 = pil_to_base64(new_img.convert("RGB"))
            mask_b64 = pil_to_base64(mask)
            # Show image_b64 and mask_b64 using cv2 for debugging

            def show_base64_image(b64_str, window_name="Image"):
                img_bytes = base64.b64decode(b64_str)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    cv2.imshow(window_name, img)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()

            show_base64_image(image_b64, "Expanded Image")
            show_base64_image(mask_b64, "Expanded Mask")
            # Compose prompt template with examples
            prompt_template = f"""
            You are an expert Photoshop assistant. Given an image (base64 PNG), 
            a mask (base64 PNG, white region is the area to edit), and an inpaint prompt, 
            generate a detailed, context-aware prompt for a generative fill model. 
            The inpaint prompt describes the change to be made in the masked region.
            White region in the mask indicates the area to be edited,
            while the black region indicates the area to be left unchanged.
            The prompt should describe what should appear in the final generated image 
            with simple words. Give the complete description of the image without treating 
            the masked region separately, but rather as part of the whole image context.
            Compare where and what the white pixels in the mask represents in the image and process the
            information carefully along with the inpaint prompt to generate the full prompt. Do not
            misinterpret the mask, image and the inpaint prompt. Dont confuse the white pixels in the 
            image as the region to be edited, they are just part of the image. Do not add unnecessary details
            in the prompt, just describe the image as it is with the changes specified in the inpaint prompt.

            Examples:
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a sun in the selected region"
            full_prompt: "A man with green shirt in the center. A sun in the top left corner."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "replace the cat with a dog"
            full_prompt: "A living room with a brown sofa. A dog sitting on the sofa."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the tree"
            full_prompt: "A mountain landscape with a clear sky and no tree in the foreground."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a red car"
            full_prompt: "A city street with buildings on both sides. A red car parked on the right side."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "change the sky to sunset"
            full_prompt: "A beach with palm trees. The sky is orange and pink with a sunset."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a person riding a bicycle"
            full_prompt: "A park with green grass and trees. A person riding a bicycle on the path."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "make the house blue"
            full_prompt: "A suburban street with a blue house and a white fence."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a flock of birds in the sky"
            full_prompt: "A lake surrounded by mountains. A flock of birds flying in the sky."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "remove the person from the bench"
            full_prompt: "A park with a wooden bench under a tree. The bench is empty."
            ---
            image: <base64:...>
            mask: <base64:...>
            inpaint_prompt: "add a rainbow over the waterfall"
            full_prompt: "A waterfall in a forest. A rainbow arches over the waterfall."
            ---

            Your turn:
            Write only the full prompt and nothing else like above examples. The above examples uses blank base64 images and masks, but give 
            your answer according to the image and mask provided below, dont add unnecessary details in the prompt.

            full_prompt:
            """

            # Call ChatGroq with Llama-4

            messages = [
                (
                    "user",
                    [
                        {"type": "text", "text": prompt_template},
                        {"type": "text", "text": "image:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"},
                        {"type": "text", "text": "mask:"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{mask_b64}"},
                        {"type": "text", "text": f"inpaint_prompt: {inpaint_prompt}"}
                    ]
                )
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
            chat = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
            chain = prompt | chat
            response = chain.invoke(
                {
                    "image_b64": image_b64,
                    "mask_b64": mask_b64,
                    "inpaint_prompt": inpaint_prompt
                }
            )

            # Extract the full prompt from the response
            logger.info(f"LLM response: {response.content}")
            full_prompt = response.content.strip()
            if full_prompt.startswith('"') and full_prompt.endswith('"'):
                full_prompt = full_prompt[1:-1]

            # 4. Inpaint with Hugging Face API
            from gradio_client import Client, handle_file
            client = Client("ameerazam08/FLUX.1-dev-Inpainting-Model-Beta-GPU", hf_token=os.getenv("HF_TOKEN"))
            # Save mask as PNG in temp_dir
            mask_path = os.path.join(temp_dir, "ps_mask_for_inpaint.png")
            mask.save(mask_path)

            # Create a new image: copy of original, but white where mask is white
            combined = new_img.convert("RGB").copy()
            mask_np = np.array(mask)
            combined_np = np.array(combined)
            white = np.ones_like(combined_np) * 255
            combined_np[mask_np == 255] = white[mask_np == 255]
            combined_img = Image.fromarray(combined_np)
            combined_path = os.path.join(temp_dir, "ps_combined_for_inpaint.png")
            combined_img.save(combined_path)

            response = client.predict(
                input_image_editor={"background":handle_file(str(expanded_path).replace("\\","/")),"layers":[handle_file(str(mask_path).replace("\\","/"))],"composite":handle_file(str(combined_path).replace("\\","/"))},
                prompt=full_prompt,
                negative_prompt="",
                controlnet_conditioning_scale=0.9,
                guidance_scale=3.5,
                seed=124,
                num_inference_steps=24,
                true_guidance_scale=3.5,
                api_name="/process",
            )
            # The response from Gradio Client is a URL or path to the generated image
            if isinstance(response, str) and (response.startswith("http://") or response.startswith("https://")):
                # Download the image from the URL
                resp = requests.get(response)
                result = Image.open(BytesIO(resp.content)).convert("RGB")
            elif isinstance(response, str) and os.path.exists(response):
                result = Image.open(response).convert("RGB")
            elif isinstance(response, dict) and "output" in response:
                # Some Gradio APIs return a dict with 'output'
                output = response["output"]
                if isinstance(output, str) and (output.startswith("http://") or output.startswith("https://")):
                    resp = requests.get(output)
                    result = Image.open(BytesIO(resp.content)).convert("RGB")
                elif isinstance(output, str) and os.path.exists(output):
                    result = Image.open(output).convert("RGB")
                else:
                    raise RuntimeError("Unknown output format from Gradio response")
            else:
                raise RuntimeError("Unknown response format from Gradio client")

            # 5. Save result and open in Photoshop as new document
            result_path = os.path.join(temp_dir, "inpaint_result.png")
            result.save(result_path)

            # Open in Photoshop as new document
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("Photoshop.Application")
            app.Open(result_path)

            return {
                "success": True,
                "message": "Document expanded and generative fill applied to new region.",
                "result_path": result_path,
                "used_prompt": full_prompt,
            }
        except Exception as e:
            import traceback

            tb_text = traceback.format_exc()
            return {
                "success": False,
                "error": str(e),
                "detailed_error": tb_text,
                "parameters": {"width": width, "height": height, "inpaint_prompt": inpaint_prompt},
            }

    # Register the generative_expand function
    tool_name = register_tool(mcp, generative_expand, "generative_expand")
    registered_tools.append(tool_name)
    # Return the list of registered tools
    return registered_tools
