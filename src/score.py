def compute_composite(sector_fit, relationship_depth, halo_value, emerging_fit):
    return (
        (sector_fit * 0.35) +
        (relationship_depth * 0.30) +
        (halo_value * 0.20) +
        (emerging_fit * 0.15)
    )

def classify_tier(composite):
    if composite >= 8.0:
        return "PRIORITY CLOSE"
    elif composite >= 6.5:
        return "STRONG FIT"
    elif composite >= 5.0:
        return "MODERATE FIT"
    else:
        return "WEAK FIT"

# allocation % ranges by org type
ALLOCATION_RANGES = {
    "Pension":              (0.005, 0.02),
    "Insurance":            (0.005, 0.02),
    "Endowment":            (0.01,  0.03),
    "Foundation":           (0.01,  0.03),
    "Fund of Funds":        (0.02,  0.05),
    "Multi-Family Office":  (0.02,  0.05),
    "Single Family Office": (0.03,  0.10),
    "HNWI":                 (0.03,  0.10),
    "Asset Manager":        (0.005, 0.03),
    "RIA/FIA":              (0.005, 0.03),
    "Private Capital Firm": (0.005, 0.03),
}

def estimate_check_size(aum_str, org_type):
    if not aum_str:
        return None
    # parse AUM string like "$6.4B", "$500M", "$2B"
    try:
        s = aum_str.replace("$", "").replace(",", "").strip()
        if s.upper().endswith("B"):
            aum = float(s[:-1]) * 1_000_000_000
        elif s.upper().endswith("M"):
            aum = float(s[:-1]) * 1_000_000
        else:
            aum = float(s)
    except (ValueError, AttributeError):
        return None

    low_pct, high_pct = ALLOCATION_RANGES.get(org_type, (0.01, 0.03))
    low = aum * low_pct
    high = aum * high_pct

    def fmt(n):
        if n >= 1_000_000:
            return f"${n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"${n/1_000:.0f}K"
        else:
            return f"${n:.0f}"

    return f"{fmt(low)} – {fmt(high)}"


if __name__ == "__main__":
    # quick sanity check against calibration anchors
    tests = [
        ("Rockefeller Foundation", 9, 7, 9, 8),
        ("PBUCC", 8, 7, 6, 8),
        ("Inherent Group", 8, 5, 3, 5),
        ("Meridian Capital", 1, 3, 3, 1),
    ]
    for name, sf, rd, halo, em in tests:
        c = compute_composite(sf, rd, halo, em)
        print(f"{name}: composite={c:.2f} tier={classify_tier(c)}")

    print()
    print(estimate_check_size("$6.4B", "Foundation"))
    print(estimate_check_size("$2B", "Pension"))
    print(estimate_check_size("$500M", "Single Family Office"))