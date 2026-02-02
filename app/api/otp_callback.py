"""
app/api/otp_callback.py

Purpose: Handles OTP link clicks from SMS short link service
Displays OTP to user and tracks link usage

When user clicks the short link from WhatsApp/SMS:
1. Shows them the OTP in a web page
2. Instructs them to return to WhatsApp
3. Tracks the click for analytics
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from app.services.session_service import get_session_data
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/otp-callback", response_class=HTMLResponse)
async def otp_callback(
    request: Request,
    p: str = Query(..., description="Phone number"),
    o: str = Query(..., description="OTP code"),
    g: str = Query(..., description="GSTIN"),
    t: str = Query(..., description="GST type"),
    pr: str = Query(..., description="Period")
):
    """
    Displays OTP to user when they click the short link
    
    Query params:
        p: Phone number (+919876543210)
        o: OTP code (123456)
        g: GSTIN
        t: GST type (GSTR1/GSTR3B)
        pr: Period (MMYYYY)
    
    Returns:
        HTML page with OTP displayed
    """
    logger.info(f"OTP callback accessed for phone: {p}, GSTIN: {g}")
    
    # Format period for display
    month = pr[:2]
    year = pr[2:]
    month_names = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December"
    }
    readable_period = f"{month_names.get(month, month)} {year}"
    
    # Create HTML response
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your GST Filing OTP</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                padding: 40px 30px;
                max-width: 500px;
                width: 100%;
                text-align: center;
            }}
            
            .logo {{
                font-size: 48px;
                margin-bottom: 20px;
            }}
            
            h1 {{
                color: #2d3748;
                font-size: 24px;
                margin-bottom: 10px;
            }}
            
            .subtitle {{
                color: #718096;
                font-size: 14px;
                margin-bottom: 30px;
            }}
            
            .otp-box {{
                background: #f7fafc;
                border: 3px dashed #667eea;
                border-radius: 15px;
                padding: 30px;
                margin: 30px 0;
            }}
            
            .otp-label {{
                color: #4a5568;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .otp-code {{
                font-size: 48px;
                font-weight: bold;
                color: #667eea;
                letter-spacing: 8px;
                font-family: 'Courier New', monospace;
                user-select: all;
                margin: 15px 0;
            }}
            
            .copy-btn {{
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-top: 15px;
                transition: all 0.3s ease;
            }}
            
            .copy-btn:hover {{
                background: #5a67d8;
                transform: scale(1.05);
            }}
            
            .copy-btn:active {{
                transform: scale(0.95);
            }}
            
            .details {{
                background: #edf2f7;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                text-align: left;
            }}
            
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #cbd5e0;
            }}
            
            .detail-row:last-child {{
                border-bottom: none;
            }}
            
            .detail-label {{
                color: #4a5568;
                font-weight: 600;
                font-size: 14px;
            }}
            
            .detail-value {{
                color: #2d3748;
                font-size: 14px;
            }}
            
            .instructions {{
                background: #fff5f5;
                border-left: 4px solid #f56565;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
                border-radius: 5px;
            }}
            
            .instructions-title {{
                color: #c53030;
                font-weight: 700;
                margin-bottom: 10px;
                font-size: 14px;
            }}
            
            .instructions ol {{
                margin-left: 20px;
                color: #2d3748;
            }}
            
            .instructions li {{
                margin: 8px 0;
                font-size: 14px;
            }}
            
            .whatsapp-btn {{
                background: #25D366;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-top: 20px;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
            }}
            
            .whatsapp-btn:hover {{
                background: #1fb855;
                transform: scale(1.05);
            }}
            
            .timer {{
                color: #f56565;
                font-size: 14px;
                margin-top: 15px;
                font-weight: 600;
            }}
            
            .success-message {{
                background: #c6f6d5;
                color: #2f855a;
                padding: 10px;
                border-radius: 8px;
                margin-top: 10px;
                display: none;
                font-weight: 600;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            .container {{
                animation: fadeIn 0.5s ease-out;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🔐</div>
            <h1>Your GST Filing OTP</h1>
            <p class="subtitle">NilEasy GST Filing Assistant</p>
            
            <div class="otp-box">
                <div class="otp-label">Your OTP Code</div>
                <div class="otp-code" id="otpCode">{o}</div>
                <button class="copy-btn" onclick="copyOTP()">📋 Copy OTP</button>
                <div class="success-message" id="successMsg">✅ Copied to clipboard!</div>
            </div>
            
            <div class="details">
                <div class="detail-row">
                    <span class="detail-label">Filing Type:</span>
                    <span class="detail-value">{t}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Period:</span>
                    <span class="detail-value">{readable_period}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">GSTIN:</span>
                    <span class="detail-value">{g}</span>
                </div>
            </div>
            
            <div class="instructions">
                <div class="instructions-title">⚠️ Next Steps:</div>
                <ol>
                    <li><strong>Copy the OTP above</strong> (click the button)</li>
                    <li><strong>Return to WhatsApp</strong></li>
                    <li><strong>Send the OTP</strong> to NilEasy bot</li>
                    <li>We'll complete your filing automatically</li>
                </ol>
            </div>
            
            <a href="https://wa.me/{p.replace('+', '')}" class="whatsapp-btn">
                💬 Return to WhatsApp
            </a>
            
            <div class="timer">⏱️ This OTP expires in 10 minutes</div>
        </div>
        
        <script>
            function copyOTP() {{
                const otpText = document.getElementById('otpCode').innerText;
                const successMsg = document.getElementById('successMsg');
                
                // Copy to clipboard
                navigator.clipboard.writeText(otpText).then(() => {{
                    // Show success message
                    successMsg.style.display = 'block';
                    
                    // Hide after 2 seconds
                    setTimeout(() => {{
                        successMsg.style.display = 'none';
                    }}, 2000);
                }}).catch(err => {{
                    alert('Failed to copy: ' + err);
                }});
            }}
            
            // Auto-select OTP on click
            document.getElementById('otpCode').addEventListener('click', function() {{
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(this);
                selection.removeAllRanges();
                selection.addRange(range);
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
