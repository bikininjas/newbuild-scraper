"""
Price normalization and category/site helpers.
"""


def normalize_price(price, name=None):
    try:
        p = float(price)
    except Exception:
        return price
    if p > 2000:
        if name:
            name_l = name.lower()
            if not any(
                x in name_l
                for x in [
                    "gpu",
                    "graphics",
                    "carte graphique",
                    "cpu",
                    "ryzen",
                    "processeur",
                    "upgrade kit",
                    "kit",
                ]
            ):
                p = p / 100
        else:
            p = p / 100
    return f"{p:.2f}"


def get_category(name, url):
    name_l = name.lower()
    if any(x in name_l for x in ["cooler", "spirit", "air", "ventirad", "thermalright"]):
        return "Cooler"
    if any(
        x in name_l
        for x in [
            "cpu",
            "ryzen",
            "intel",
            "amd processor",
            "processeur",
            "9800x3d",
            "9800 x3d",
        ]
    ):
        return "CPU"
    if any(
        x in name_l
        for x in [
            "radeon",
            "geforce",
            "rtx",
            "gpu",
            "graphics",
            "carte graphique",
            "pulse radeon",
        ]
    ):
        return "GPU"
    if any(x in name_l for x in ["ram", "ddr", "memory", "mémoire"]):
        return "RAM"
    if any(x in name_l for x in ["ssd", "nvme", "m.2", "disque"]):
        return "SSD"
    if any(x in name_l for x in ["motherboard", "carte mère", "b850", "atx", "tuf gaming", "asus"]):
        return "Motherboard"
    if any(x in name_l for x in ["alimentation", "psu", "power supply", "a850gl"]):
        return "PSU"
    if any(x in name_l for x in ["keyboard", "clavier", "k70", "corsair"]):
        return "Keyboard"
    if any(x in name_l for x in ["mouse", "souris", "g502", "logitech"]):
        return "Mouse"
    if any(x in name_l for x in ["kit", "upgrade"]):
        return "Upgrade Kit"
    return "Other"


def get_site_label(url):
    if "amazon." in url:
        return "Amazon"
    if "ldlc." in url:
        return "LDLC"
    if "idealo." in url:
        return "Idealo"
    if "grosbill." in url:
        return "Grosbill"
    if "materiel.net" in url:
        return "Materiel.net"
    if "topachat." in url:
        return "TopAchat"
    if "alternate." in url:
        return "Alternate"
    if "bpm-power." in url:
        return "BPM Power"
    if "pccomponentes." in url:
        return "PCComponentes"
    if "caseking." in url:
        return "Caseking"
    return url.split("//")[-1].split("/")[0]
