"""
utils/whatsapp_utils.py

Purpose: WhatsApp message builders

- Constructs button, list, and text payloads
- Abstracts WhatsApp API formatting
- AiSensy-compatible message formats
"""

from typing import List, Dict, Optional, Any
import base64


def create_text_message(text: str, preview_url: bool = False) -> Dict[str, Any]:
    """
    Creates a simple text message response.
    
    Args:
        text: Message text (supports WhatsApp markdown)
        preview_url: Whether to show URL preview
    
    Returns:
        Message payload dict
    """
    return {
        "type": "text",
        "text": text,
        "preview_url": preview_url
    }


def create_button_message(
    text: str,
    buttons: List[Dict[str, str]],
    header: Optional[str] = None,
    footer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a message with interactive buttons (quick reply buttons).
    
    Args:
        text: Body text
        buttons: List of button dicts with 'id' and 'title' keys
                 Max 3 buttons, each title max 20 chars
        header: Optional header text
        footer: Optional footer text
    
    Returns:
        Button message payload
    
    Example:
        buttons = [
            {"id": "btn_1", "title": "Yes"},
            {"id": "btn_2", "title": "No"}
        ]
    """
    # Validate buttons
    if len(buttons) > 3:
        buttons = buttons[:3]  # WhatsApp allows max 3 quick reply buttons
    
    for button in buttons:
        if len(button.get("title", "")) > 20:
            button["title"] = button["title"][:20]
    
    payload = {
        "type": "button",
        "body": {
            "text": text
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": btn["id"],
                        "title": btn["title"]
                    }
                }
                for btn in buttons
            ]
        }
    }
    
    if header:
        payload["header"] = {"type": "text", "text": header}
    
    if footer:
        payload["footer"] = {"text": footer}
    
    return payload


def create_list_message(
    text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    header: Optional[str] = None,
    footer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a message with a list picker (interactive list).
    
    Args:
        text: Body text
        button_text: Button text to open the list (max 20 chars)
        sections: List sections with title and rows
        header: Optional header text
        footer: Optional footer text
    
    Returns:
        List message payload
    
    Example:
        sections = [
            {
                "title": "Select Option",
                "rows": [
                    {"id": "opt_1", "title": "Option 1", "description": "Description 1"},
                    {"id": "opt_2", "title": "Option 2"}
                ]
            }
        ]
    """
    # Validate button text length
    if len(button_text) > 20:
        button_text = button_text[:20]
    
    # Validate sections (max 10 sections, max 10 rows per section)
    if len(sections) > 10:
        sections = sections[:10]
    
    for section in sections:
        if "rows" in section and len(section["rows"]) > 10:
            section["rows"] = section["rows"][:10]
        
        # Validate row title length (max 24 chars)
        for row in section.get("rows", []):
            if len(row.get("title", "")) > 24:
                row["title"] = row["title"][:24]
    
    payload = {
        "type": "list",
        "body": {
            "text": text
        },
        "action": {
            "button": button_text,
            "sections": sections
        }
    }
    
    if header:
        payload["header"] = {"type": "text", "text": header}
    
    if footer:
        payload["footer"] = {"text": footer}
    
    return payload


def create_image_message(
    image_url: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates an image message.
    
    Args:
        image_url: URL of the image or base64 data
        caption: Optional image caption
    
    Returns:
        Image message payload
    """
    payload = {
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    
    if caption:
        payload["image"]["caption"] = caption
    
    return payload


def create_document_message(
    document_url: str,
    filename: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a document message (for PDFs, etc.).
    
    Args:
        document_url: URL of the document
        filename: Document filename
        caption: Optional caption
    
    Returns:
        Document message payload
    """
    payload = {
        "type": "document",
        "document": {
            "link": document_url,
            "filename": filename
        }
    }
    
    if caption:
        payload["document"]["caption"] = caption
    
    return payload


def create_template_message(
    template_name: str,
    language_code: str = "en",
    parameters: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Creates a template-based message (for approved WhatsApp templates).
    Used for sending messages outside 24-hour window.
    
    Args:
        template_name: Name of approved template
        language_code: Language code (default: "en")
        parameters: Template parameter values
    
    Returns:
        Template message payload
    """
    payload = {
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
    }
    
    if parameters:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": param}
                    for param in parameters
                ]
            }
        ]
    
    return payload


def format_whatsapp_markdown(text: str) -> str:
    """
    Ensures text uses proper WhatsApp markdown formatting.
    
    WhatsApp markdown:
    - *bold*
    - _italic_
    - ~strikethrough~
    - ```monospace```
    
    Args:
        text: Text to format
    
    Returns:
        Formatted text
    """
    # WhatsApp already supports these, just return as-is
    # Could add validation or conversion here if needed
    return text


def parse_button_response(message: Dict[str, Any]) -> Optional[str]:
    """
    Parses button click response from webhook.
    
    Args:
        message: Webhook message payload
    
    Returns:
        Button ID that was clicked, or None
    """
    if message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("id")
    
    return None


def parse_list_response(message: Dict[str, Any]) -> Optional[str]:
    """
    Parses list selection response from webhook.
    
    Args:
        message: Webhook message payload
    
    Returns:
        Selected list item ID, or None
    """
    if message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "list_reply":
            return interactive.get("list_reply", {}).get("id")
    
    return None


def get_message_text(message: Dict[str, Any]) -> Optional[str]:
    """
    Extracts text content from any message type.
    
    Args:
        message: Webhook message payload
    
    Returns:
        Message text content
    """
    msg_type = message.get("type")
    
    if msg_type == "text":
        return message.get("text", {}).get("body")
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        reply_type = interactive.get("type")
        
        if reply_type == "button_reply":
            return interactive.get("button_reply", {}).get("title")
        elif reply_type == "list_reply":
            return interactive.get("list_reply", {}).get("title")
    
    return None
