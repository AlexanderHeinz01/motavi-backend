"""4-page PDF report generator using reportlab.

Page 1: Cover — workplace, date, REBA-Score (large, traffic-light colour)
Page 2: Movement breakdown table (%, min/shift, 8 h extrapolation)
Page 3: Body region REBA subscores (table + traffic-light indicator)
Page 4: Action fields — CRITICAL (red) then MEDIUM (yellow),
        each with region, measure text, reduction potential %
Footer (every page): "Erstellt durch Motavi · DSGVO-konform · EU-Server (europe-west3)"
"""
# TODO: implement in Step 2


def generate_report_pdf(result: dict) -> bytes:
    """Generate PDF report from analysis result dict. Returns PDF bytes."""
    # TODO: implement
    raise NotImplementedError
