def infer_palette_from_name(team_name: str) -> list[str]:
    presets = {
        "lakers": ["#552583", "#FDB927", "#111111"],
        "warriors": ["#1D428A", "#FFC72C", "#FFFFFF"],
        "celtics": ["#007A33", "#BA9653", "#FFFFFF"],
        "chennai super kings": ["#F9CD05", "#1D418C", "#F15C19"],
        "csk": ["#F9CD05", "#1D418C", "#F15C19"],
        "mumbai indians": ["#045093", "#D1AB3E", "#FFFFFF"],
        "royal challengers": ["#D71920", "#2B2A29", "#CBA92B"],
        "kolkata knight riders": ["#3A225D", "#B3A123", "#FFFFFF"],
        "sunrisers hyderabad": ["#F26522", "#000000", "#F7A721"],
        "rajasthan royals": ["#EA1A85", "#254AA5", "#FFFFFF"],
        "delhi capitals": ["#17479E", "#EF1B23", "#FFFFFF"],
        "punjab kings": ["#DD1F2D", "#A7A9AC", "#FFFFFF"],
        "gujarat titans": ["#1C1C1C", "#D4AF37", "#FFFFFF"],
        "lucknow super giants": ["#00A3E0", "#F28C28", "#E40046"],
    }
    lowered = team_name.lower()
    for key, colors in presets.items():
        if key in lowered:
            return colors
    return ["#1F2937", "#0EA5E9", "#F8FAFC"]
