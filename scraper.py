from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re

BASE_URL = "https://www.aldi-sued.de"

# Full category tree: { parent: { subcategory: url } }
# Top-level-only categories use None as the subcategory key.
CATEGORIES = {
    "Wochenangebote": {
        None:                           "/produkte/wochenangebote/k/1588161426582123",
        "Frischeprodukte im Angebot":   "/produkte/wochenangebote/frischeprodukte-im-angebot/k/1588161427299187",
        "Eigenmarken im Angebot":       "/produkte/wochenangebote/eigenmarken-im-angebot/k/1588161427299188",
        "Markenprodukte im Angebot":    "/produkte/wochenangebote/markenprodukte-im-angebot/k/1588161427299189",
    },
    "Dauerhaft günstig": {
        None: "/produkte/dauerhaft-guenstig/k/1588161425467260",
    },
    "Neuheiten": {
        None: "/produkte/neuheiten/k/1588161425467262",
    },
    "Alkoholische Getränke": {
        None:                                           "/produkte/alkoholische-getraenke/k/1588161425467197",
        "Bier":                                         "/produkte/alkoholische-getraenke/bier/k/1588161425467198",
        "Spirituosen":                                  "/produkte/alkoholische-getraenke/spirituosen/k/1588161425467199",
        "Wein":                                         "/produkte/alkoholische-getraenke/wein/k/1588161425467200",
        "Roséwein":                                     "/produkte/alkoholische-getraenke/rosewein/k/1588161425467201",
        "Rotwein":                                      "/produkte/alkoholische-getraenke/rotwein/k/1588161425467202",
        "Sekt & Schaumwein":                            "/produkte/alkoholische-getraenke/sekt-schaumwein/k/1588161425467203",
        "Weißwein":                                     "/produkte/alkoholische-getraenke/weisswein/k/1588161425467204",
        "Alkoholfreie Weine, Biere & Spirituosen":      "/produkte/alkoholische-getraenke/alkoholfreie-weine-biere-spirituosen/k/1588161425467205",
    },
    "Backwaren, Aufstriche & Cerealien": {
        None:                               "/produkte/backwaren-aufstriche-cerealien/k/1588161425467101",
        "Brot":                             "/produkte/backwaren-aufstriche-cerealien/brot/k/1588161425467102",
        "Toastbrot":                        "/produkte/backwaren-aufstriche-cerealien/toastbrot/k/1588161425467103",
        "Brötchen & Baguette":              "/produkte/backwaren-aufstriche-cerealien/broetchen-baguette/k/1588161425467104",
        "Knäckebrot, Zwieback & Reiswaffeln": "/produkte/backwaren-aufstriche-cerealien/knaeckebrot-zwieback-reiswaffeln/k/1588161425467105",
        "Hotdogs, Burger Buns & Wraps":     "/produkte/backwaren-aufstriche-cerealien/hotdogs-burger-buns-wraps/k/1588161425467106",
        "Herzhaftes Gebäck":                "/produkte/backwaren-aufstriche-cerealien/herzhaftes-gebaeck/k/1588161425467107",
        "Fertigkuchen & Süßgebäck":         "/produkte/backwaren-aufstriche-cerealien/fertigkuchen-suessgebaeck/k/1588161425467108",
        "Müsli & Cornflakes":               "/produkte/backwaren-aufstriche-cerealien/muesli-cornflakes/k/1588161425467109",
        "Herzhafter Brotaufstrich":         "/produkte/backwaren-aufstriche-cerealien/herzhafter-brotaufstrich/k/1588161425467110",
        "Honig":                            "/produkte/backwaren-aufstriche-cerealien/honig/k/1588161425467111",
        "Fruchtaufstriche & Marmelade":     "/produkte/backwaren-aufstriche-cerealien/fruchtaufstriche-marmelade/k/1588161425467112",
        "Nuss- & Schokocreme":              "/produkte/backwaren-aufstriche-cerealien/nuss-schokocreme/k/1588161425467113",
    },
    "Backzutaten, Mehl & Zucker": {
        None:                               "/produkte/backzutaten-mehl-zucker/k/1588161425467155",
        "Backmischungen":                   "/produkte/backzutaten-mehl-zucker/backmischungen/k/1588161425467157",
        "Backaromen & Backhelfer":          "/produkte/backzutaten-mehl-zucker/backaromen-backhelfer/k/1588161425467158",
        "Mehl":                             "/produkte/backzutaten-mehl-zucker/mehl/k/1588161425467159",
        "Zucker & Süßungsmittel":           "/produkte/backzutaten-mehl-zucker/zucker-suessungsmittel/k/1588161425467160",
        "Dessert- & Puddingpulver":         "/produkte/backzutaten-mehl-zucker/dessert-puddingpulver/k/1588161425467161",
    },
    "Bio-Produkte": {
        None: "/produkte/bio-produkte/k/1588161425467036",
    },
    "Fairtrade-Produkte": {
        None: "/produkte/fairtrade-produkte/k/1588161425467037",
    },
    "Fleisch & Fisch": {
        None:                       "/produkte/fleisch-fisch/k/1588161425467052",
        "Bratwurst & Würstchen":    "/produkte/fleisch-fisch/bratwurst-wuerstchen/k/1588161425467053",
        "Fisch- & Fleischsalate":   "/produkte/fleisch-fisch/fisch-fleischsalate/k/1588161425467054",
        "Fisch & Meeresfrüchte":    "/produkte/fleisch-fisch/fisch-meeresfruechte/k/1588161425467055",
        "Geflügel":                 "/produkte/fleisch-fisch/gefluegel/k/1588161425467059",
        "Hackfleisch":              "/produkte/fleisch-fisch/hackfleisch/k/1588161425467061",
        "Rindfleisch":              "/produkte/fleisch-fisch/rindfleisch/k/1588161425467064",
        "Schweinefleisch":          "/produkte/fleisch-fisch/schweinefleisch/k/1588161425467066",
    },
    "Getränke": {
        None:                               "/produkte/getraenke/k/1588161425467173",
        "Cola":                             "/produkte/getraenke/cola/k/1588161425467175",
        "Eistee":                           "/produkte/getraenke/eistee/k/1588161425467176",
        "Limonade":                         "/produkte/getraenke/limonade/k/1588161425467177",
        "Energydrinks":                     "/produkte/getraenke/energydrinks/k/1588161425467190",
        "Tee":                              "/produkte/getraenke/tee/k/1588161425467191",
        "Mineralwasser":                    "/produkte/getraenke/mineralwasser/k/1588161425467192",
        "Kaffee":                           "/produkte/getraenke/kaffee/k/1588161425467193",
        "Kakao-, Milch- & Kaffeegetränke":  "/produkte/getraenke/kakao-milch-kaffeegetraenke/k/1588161425467194",
        "Saft, Nektar & Smoothies":         "/produkte/getraenke/saft-nektar-smoothies/k/1588161425467196",
    },
    "Grillen": {
        None:                               "/produkte/grillen/k/1588161425467254",
        "Vegetarisches & veganes Grillgut": "/produkte/grillen/vegetarisches-veganes-grillgut/k/1588161425467255",
        "Grillkäse":                        "/produkte/grillen/grillkaese/k/1588161425467256",
        "Grillsaucen":                      "/produkte/grillen/grillsaucen/k/1588161425467257",
    },
    "Käse": {
        None:                       "/produkte/kaese/k/1588161425467083",
        "Schnittkäse":              "/produkte/kaese/schnittkaese/k/1588161425467084",
        "Weichkäse":                "/produkte/kaese/weichkaese/k/1588161425467085",
        "Frischkäse":               "/produkte/kaese/frischkaese/k/1588161425467086",
        "Feta & Hirtenkäse":        "/produkte/kaese/feta-hirtenkaese/k/1588161425467087",
        "Hartkäse & Stückkäse":     "/produkte/kaese/hartkaese-stueckkaese/k/1588161425467088",
        "Mozzarella":               "/produkte/kaese/mozzarella/k/1588161425467089",
        "Ofenkäse":                 "/produkte/kaese/ofenkaese/k/1588161425467090",
        "Reibekäse":                "/produkte/kaese/reibekaese/k/1588161425467091",
        "Schmelzkäse":              "/produkte/kaese/schmelzkaese/k/1588161425467092",
    },
    "Konserven & Fertiggerichte": {
        None:                               "/produkte/konserven-fertiggerichte/k/1588161425467133",
        "Eintöpfe & Suppen":                "/produkte/konserven-fertiggerichte/eintoepfe-suppen/k/1588161425467134",
        "Fertiggerichte & Ravioli":         "/produkte/konserven-fertiggerichte/fertiggerichte-ravioli/k/1588161425467135",
        "Fischkonserven":                   "/produkte/konserven-fertiggerichte/fischkonserven/k/1588161425467136",
        "Gemüsekonserven":                  "/produkte/konserven-fertiggerichte/gemuesekonserven/k/1588161425467137",
        "Obstkonserven":                    "/produkte/konserven-fertiggerichte/obstkonserven/k/1588161425467138",
        "Wurst- & Fleischkonserven":        "/produkte/konserven-fertiggerichte/wurst-fleischkonserven/k/1588161425467139",
        "Antipasti-Feinkost & Salate":      "/produkte/konserven-fertiggerichte/antipasti-feinkost-salate/k/1588161425467140",
    },
    "Milchprodukte & Eier": {
        None:                           "/produkte/milchprodukte-eier/k/1588161425467093",
        "Milch":                        "/produkte/milchprodukte-eier/milch/k/1588161425467094",
        "Speisequark":                  "/produkte/milchprodukte-eier/speisequark/k/1588161425467095",
        "Fruchtjoghurt & Desserts":     "/produkte/milchprodukte-eier/fruchtjoghurt-desserts/k/1588161425467096",
        "Naturjoghurt & Skyr":          "/produkte/milchprodukte-eier/naturjoghurt-skyr/k/1588161425467097",
        "Sahne, Schmand & Crème fraîche": "/produkte/milchprodukte-eier/sahne-schmand-creme-fraiche/k/1588161425467098",
        "Butter & Margarine":           "/produkte/milchprodukte-eier/butter-margarine/k/1588161425467099",
        "Eier":                         "/produkte/milchprodukte-eier/eier/k/1588161425467100",
    },
    "Nudeln, Reis & Hülsenfrüchte": {
        None:                           "/produkte/nudeln-reis-huelsenfruechte/k/1588161425467115",
        "Nudeln & Pasta":               "/produkte/nudeln-reis-huelsenfruechte/nudeln-pasta/k/1588161425467116",
        "Reis":                         "/produkte/nudeln-reis-huelsenfruechte/reis/k/1588161425467117",
        "Kartoffelprodukte":            "/produkte/nudeln-reis-huelsenfruechte/kartoffelprodukte/k/1588161425467118",
        "Hülsenfrüchte & Getreide":     "/produkte/nudeln-reis-huelsenfruechte/huelsenfruechte-getreide/k/1588161425467120",
    },
    "Saucen, Öle & Gewürze": {
        None:                               "/produkte/saucen-oele-gewuerze/k/1588161425467121",
        "Saucen & Fertigsaucen":            "/produkte/saucen-oele-gewuerze/saucen-fertigsaucen/k/1588161425467122",
        "Brühe, Bouillons & Fonds":         "/produkte/saucen-oele-gewuerze/bruehe-bouillons-fonds/k/1588161425467123",
        "Dressings":                        "/produkte/saucen-oele-gewuerze/dressings/k/1588161425467128",
        "Essig & Öl":                       "/produkte/saucen-oele-gewuerze/essig-oel/k/1588161425467129",
        "Mayonnaise, Ketchup & Remoulade":  "/produkte/saucen-oele-gewuerze/mayonnaise-ketchup-remoulade/k/1588161425467130",
        "Senf & Meerrettich":               "/produkte/saucen-oele-gewuerze/senf-meerrettich/k/1588161425467131",
        "Gewürze & frische Kräuter":        "/produkte/saucen-oele-gewuerze/gewuerze-frische-kraeuter/k/1588161425467132",
    },
    "Süßigkeiten & salzige Snacks": {
        None:                       "/produkte/suessigkeiten-salzige-snacks/k/1588161425467162",
        "Bonbons":                  "/produkte/suessigkeiten-salzige-snacks/bonbons/k/1588161425467163",
        "Lakritz & Fruchtgummi":    "/produkte/suessigkeiten-salzige-snacks/lakritz-fruchtgummi/k/1588161425467164",
        "Kaugummis":                "/produkte/suessigkeiten-salzige-snacks/kaugummis/k/1588161425467165",
        "Kekse":                    "/produkte/suessigkeiten-salzige-snacks/kekse/k/1588161425467166",
        "Nougat & Konfekt":         "/produkte/suessigkeiten-salzige-snacks/nougat-konfekt/k/1588161425467167",
        "Nüsse & Trockenfrüchte":   "/produkte/suessigkeiten-salzige-snacks/nuesse-trockenfruechte/k/1588161425467168",
        "Frucht- & Müsliriegel":    "/produkte/suessigkeiten-salzige-snacks/frucht-muesliriegel/k/1588161425467170",
        "Schokolade":               "/produkte/suessigkeiten-salzige-snacks/schokolade/k/1588161425467171",
        "Chips & Knabbereien":      "/produkte/suessigkeiten-salzige-snacks/chips-knabbereien/k/1588161425467172",
    },
    "Tiefkühlung": {
        None:                           "/produkte/tiefkuehlung/k/1588161425467141",
        "TK Fleisch":                   "/produkte/tiefkuehlung/tk-fleisch/k/1588161425467142",
        "TK Fisch & Meeresfrüchte":     "/produkte/tiefkuehlung/tk-fisch-meeresfruechte/k/1588161425467143",
        "TK Garnelen":                  "/produkte/tiefkuehlung/tk-garnelen/k/1588161425467144",
        "TK Lachs":                     "/produkte/tiefkuehlung/tk-lachs/k/1588161425467145",
        "TK Pizza & Baguettes":         "/produkte/tiefkuehlung/tk-pizza-baguettes/k/1588161425467146",
        "TK Pfannen- & Fertiggerichte": "/produkte/tiefkuehlung/tk-pfannen-fertiggerichte/k/1588161425467147",
        "Pommes, Wedges & Kroketten":   "/produkte/tiefkuehlung/pommes-wedges-kroketten/k/1588161425467148",
        "TK Gemüse":                    "/produkte/tiefkuehlung/tk-gemuese/k/1588161425467150",
        "TK Obst":                      "/produkte/tiefkuehlung/tk-obst/k/1588161425467151",
        "TK Desserts & Backwaren":      "/produkte/tiefkuehlung/tk-desserts-backwaren/k/1588161425467152",
        "Eis":                          "/produkte/tiefkuehlung/eis/k/1588161425467153",
    },
    "Wurst & Aufschnitt": {
        None:                           "/produkte/wurst-aufschnitt/k/1588161425467075",
        "Fleischwurst":                 "/produkte/wurst-aufschnitt/fleischwurst/k/1588161425467078",
        "Geflügelwurst":                "/produkte/wurst-aufschnitt/gefluegelwurst/k/1588161425467079",
        "Salami":                       "/produkte/wurst-aufschnitt/salami/k/1588161425467080",
        "Schinken":                     "/produkte/wurst-aufschnitt/schinken/k/1588161425467081",
        "Streichwurst & Pasteten":      "/produkte/wurst-aufschnitt/streichwurst-pasteten/k/1588161425467082",
    },
    "Vegetarisch & Vegan": {
        None:                               "/produkte/vegetarisch-vegan/k/1588161425467039",
        "Fisch- & Fleischersatz":           "/produkte/vegetarisch-vegan/fisch-fleischersatz/k/1588161425467040",
        "Milchalternativen":                "/produkte/vegetarisch-vegan/milchalternativen/k/1588161425467041",
        "Joghurt- & Dessertalternativen":   "/produkte/vegetarisch-vegan/joghurt-dessertalternativen/k/1588161425467042",
        "Käse- & Wurstalternativen":        "/produkte/vegetarisch-vegan/kaese-wurstalternativen/k/1588161425467043",
        "Aufstriche":                       "/produkte/vegetarisch-vegan/aufstriche/k/1588161425467044",
        "Fertiggerichte":                   "/produkte/vegetarisch-vegan/fertiggerichte/k/1588161425467045",
        "Tofu, Falafel & Gemüsebällchen":   "/produkte/vegetarisch-vegan/tofu-falafel-gemuesebaellchen/k/1588161425467046",
        "Vegane Süßigkeiten & Snacks":      "/produkte/vegetarisch-vegan/vegane-suessigkeiten-snacks/k/1588161425467047",
        "Tiefkühlprodukte":                 "/produkte/vegetarisch-vegan/tiefkuehlprodukte/k/1588161425467048",
    },
    "Babyartikel": {
        None:                       "/produkte/babyartikel/k/1588161425467246",
        "Babynahrung":              "/produkte/babyartikel/babynahrung/k/1588161425467247",
        "Babypflege & Windeln":     "/produkte/babyartikel/babypflege-windeln/k/1588161425467248",
    },
    "Drogerie & Kosmetik": {
        None:                           "/produkte/drogerie-kosmetik/k/1588161425467233",
        "Nahrungsergänzungsmittel":     "/produkte/drogerie-kosmetik/nahrungsergaenzungsmittel/k/1588161425467234",
        "Hygieneartikel":               "/produkte/drogerie-kosmetik/hygieneartikel/k/1588161425467235",
        "Deodorant":                    "/produkte/drogerie-kosmetik/deodorant/k/1588161425467236",
        "Duschgel":                     "/produkte/drogerie-kosmetik/duschgel/k/1588161425467237",
        "Körper- & Gesichtspflege":     "/produkte/drogerie-kosmetik/koerper-gesichtspflege/k/1588161425467238",
        "Shampoo & Haarpflege":         "/produkte/drogerie-kosmetik/shampoo-haarpflege/k/1588161425467239",
        "Rasur & Haarentfernung":       "/produkte/drogerie-kosmetik/rasur-haarentfernung/k/1588161425467240",
        "Seife":                        "/produkte/drogerie-kosmetik/seife/k/1588161425467241",
        "Hand-, Fuß- & Nagelpflege":    "/produkte/drogerie-kosmetik/hand-fuss-nagelpflege/k/1588161425467242",
        "Zahnpflegeprodukte":           "/produkte/drogerie-kosmetik/zahnpflegeprodukte/k/1588161425467243",
        "Make-up":                      "/produkte/drogerie-kosmetik/make-up/k/1588161425467245",
    },
    "Haushaltsartikel": {
        None:                       "/produkte/haushaltsartikel/k/1588161425467211",
        "Müllbeutel & Folien":      "/produkte/haushaltsartikel/muellbeutel-folien/k/1588161425467212",
        "Papier & Tücher":          "/produkte/haushaltsartikel/papier-tuecher/k/1588161425467213",
        "Putzmittel":               "/produkte/haushaltsartikel/putzmittel/k/1588161425467214",
        "Spülmittel & Schwämme":    "/produkte/haushaltsartikel/spuelmittel-schwaemme/k/1588161425467229",
        "Waschmittel":              "/produkte/haushaltsartikel/waschmittel/k/1588161425467231",
        "Batterien":                "/produkte/haushaltsartikel/batterien/k/1588161425467232",
    },
    "Tierbedarf": {
        None:                           "/produkte/tierbedarf/k/1588161425467249",
        "Hundefutter":                  "/produkte/tierbedarf/hundefutter/k/1588161425467250",
        "Katzenfutter & Katzenstreu":   "/produkte/tierbedarf/katzenfutter-katzenstreu/k/1588161425467251",
    },
    # Non-food / seasonal — scrape top level only (no stable subcategories)
    "Blumen & Blumensträuße":       {None: "/produkte/blumen-blumenstraeusse/k/1588161425467259"},
    "Garten":                       {None: "/produkte/garten/k/1588161426582150"},
    "Camping":                      {None: "/produkte/camping/k/1588161426582146"},
    "Einrichtung & Wohnen":         {None: "/produkte/einrichtung-wohnen/k/1588161426582147"},
    "Heimwerken":                   {None: "/produkte/heimwerken/k/1588161426582152"},
    "Fahrrad & Zubehör":            {None: "/produkte/fahrrad-zubehoer/k/1588161426582148"},
    "Kleidung":                     {None: "/produkte/kleidung/k/1588161426582153"},
    "Küche & Backen":               {None: "/produkte/kueche-backen/k/1588161426583075"},
    "Bettwäsche & Heimtextilien":   {None: "/produkte/bettwaesche-heimtextilien/k/1588161426582155"},
    "Outdoor & Freizeit":           {None: "/produkte/outdoor-freizeit/k/1588161426582154"},
    "Technik & Elektronik":         {None: "/produkte/technik-elektronik/k/1588161426582160"},
    "Schreibwaren":                 {None: "/produkte/schreibwaren/k/1588161426582156"},
    "Sport & Fitness":              {None: "/produkte/sport-fitness/k/1588161426582158"},
    "Spielzeug":                    {None: "/produkte/spielzeug/k/1588161426582157"},
    "Urlaub & Strand":              {None: "/produkte/urlaub-strand/k/1588161426582159"},
}


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_price(raw: str) -> float:
    """'2,49\xa0€' or '2.49 €'  ->  2.49"""
    # Strip all non-numeric characters except comma and dot, then normalise decimal separator
    cleaned = re.sub(r"[^\d,\.]", "", raw).strip()
    # If both comma and dot present, comma is thousands sep → remove it; otherwise comma is decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def parse_weight(raw: str) -> float:
    """Convert any Aldi weight/volume string to kilograms.

    Examples:
      '0,36 kg'  -> 0.36
      '400 g'    -> 0.4
      '500 ml'   -> 0.5   (1 ml ≈ 1 g, good enough for cost-per-kg)
      '1,5 l'    -> 1.5
      '1 l'      -> 1.0
    """
    raw = raw.strip()
    # Normalise decimal separator
    normalised = raw.replace(",", ".")
    m = re.match(r"([\d.]+)\s*(kg|g|l|ml|liter|litre)", normalised, re.IGNORECASE)
    if not m:
        raise ValueError(f"Unrecognised weight format: {raw!r}")
    value, unit = float(m.group(1)), m.group(2).lower()
    if unit == "kg":
        return value
    elif unit == "g":
        return value / 1000
    elif unit in ("l", "liter", "litre"):
        return value          # 1 L water ≈ 1 kg
    elif unit == "ml":
        return value / 1000   # 1 ml ≈ 1 g
    raise ValueError(f"Unknown unit {unit!r} in {raw!r}")


# ── core scraper ─────────────────────────────────────────────────────────────

def scrape_page(page, url: str, parent_category: str, subcategory: str | None) -> list[dict]:
    """Fetches one category URL and returns a list of product dicts."""
    label = f"{parent_category} > {subcategory}" if subcategory else parent_category
    print(f"  🔍 {label}")

    try:
        page.goto(BASE_URL + url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("div.product-tile", timeout=15000)
    except Exception as e:
        print(f"    ⚠️  Could not load page: {e}")
        return []

    soup = BeautifulSoup(page.content(), "html.parser")
    cards = soup.find_all("div", class_="product-tile")

    products = []
    for card in cards:
        try:
            brand_tag = card.find("div", class_="product-tile__brandname")
            brand = brand_tag.find("p").text.strip() if brand_tag else ""

            name_tag = card.find("div", class_="product-tile__name")
            name = name_tag.find("p").text.strip() if name_tag else ""
            if not name:
                continue

            price_tag = card.find("span", class_="base-price__regular")
            price_raw = price_tag.find("span").text.strip() if price_tag else ""
            try:
                price_eur = parse_price(price_raw) if price_raw else None
            except ValueError:
                price_eur = None

            unit_tag = card.find("div", class_="product-tile__unit-of-measurement")
            unit_raw = unit_tag.find("p").text.strip() if unit_tag else ""
            try:
                weight_kg = parse_weight(unit_raw) if unit_raw else None
            except ValueError:
                weight_kg = None

            link_tag = card.find("a", class_="product-tile__link")
            link = (BASE_URL + link_tag["href"]) if link_tag else ""

            products.append({
                "brand":            brand,
                "title":            name,
                "price_eur":        price_eur,
                "weight_kg":        weight_kg,
                "url":              link,
                "category":         parent_category,
                "subcategory":      subcategory,
            })
        except AttributeError:
            continue

    print(f"    ✅ {len(products)} products")
    return products


def deduplicate(products: list[dict]) -> list[dict]:
    """Remove duplicate products by URL, keeping the most specific entry
    (subcategory wins over None)."""
    seen: dict[str, dict] = {}
    for p in products:
        key = p["url"]
        if key not in seen or (p["subcategory"] is not None and seen[key]["subcategory"] is None):
            seen[key] = p
    return list(seen.values())


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    all_products: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Accept cookie banner once on the home page
        print("🌐 Opening Aldi website...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        try:
            page.click("#onetrust-accept-btn-handler", timeout=5000)
            print("✅ Cookie banner accepted.")
        except Exception:
            print("ℹ️  No cookie banner found.")

        total_categories = sum(len(subs) for subs in CATEGORIES.values())
        scraped = 0

        for parent, subcategories in CATEGORIES.items():
            print(f"\n📂 {parent}")
            for subcat, path in subcategories.items():
                items = scrape_page(page, path, parent, subcat)
                all_products.extend(items)
                scraped += 1
                print(f"    [{scraped}/{total_categories}]")

        browser.close()

    # Remove duplicates that appear in both a parent roll-up and a subcategory
    before = len(all_products)
    all_products = deduplicate(all_products)
    print(f"\n🔁 Deduplication: {before} → {len(all_products)} unique products")

    with open("aldi_catalog.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=4)

    print(f"✅ Done! Saved {len(all_products)} products to aldi_catalog.json.")


if __name__ == "__main__":
    main()
