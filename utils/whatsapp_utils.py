"""
utils/whatsapp_utils.py

Purpose: WhatsApp message builders

- Constructs button, list, and text payloads
- Abstracts WhatsApp API formatting
"""

from typing import List, Dict

def create_text_message(text: str) -> dict:
    """
    Creates a simple text message response.
    """
    return {
        "type": "text",
        "text": text
    }

def create_button_message(text: str, buttons: List[Dict]) -> dict:
    """
    Creates a message with interactive buttons.
    
    Args:
        text: Message text
        buttons: List of button dicts with 'id' and 'title' keys
    """
    return {
        "type": "button",
        "text": text,
        "buttons": buttons
    }

def create_list_message(text: str, button_text: str, sections: List[Dict]) -> dict:
    """
    Creates a message with a list picker.
    
    Args:
        text: Header text
        button_text: Button text to open the list
        sections: List sections with title and rows
    """
    return {
        "type": "list",
        "text": text,
        "button": button_text,
        "sections": sections
    }

def create_template_message(template_name: str, params: List[str]) -> dict:
    """
    Creates a template-based message (for approved WhatsApp templates).
    """
    return {
        "type": "template",
        "template_name": template_name,
        "parameters": params
    }
