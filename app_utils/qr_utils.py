import base64
import io

import qrcode


def generate_qr_data_url(text):
    """Returns a base64 data: URL of a QR code PNG encoding `text`."""
    img = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
