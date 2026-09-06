#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOCAL SERVICE SITE GENERATOR  —  self-contained, one file, no dependencies.

    python3 build_site.py --core     # <-- START HERE. Writes ONE example of
                                     #     each page type (10 files) into ./out
    python3 build_site.py            # writes the FULL site into ./out
    python3 build_site.py --here     # write into the current directory instead
    python3 build_site.py --report    # + duplicate-content check

Everything you edit lives in the CONFIG block below. Everything under
"THEME" and "BUILDERS" is the reusable machinery and does not change
between cities.

WHAT --core PRODUCES  (the structural template — 10 pages)
    /                                     1. home
    /<cluster>/                           2. service cluster / category hub
    /<cluster>/<child>/                   3. service sub-cluster page
    /<cluster>-<city>/                    4. service x city page
    /areas/                               5. service-areas index
    /<brandslug>-<city>/                  6. single service-area page
    /faq/                                 7. FAQ
    /about/                               8. About Us
    /contact/                             9. Contact
    /404.html                            10. 404
    Nav links on these point at the full site, so they 404 until you do a
    full build. That is expected — the markup is what you are copying.

WHAT A FULL RUN PRODUCES
    /                                     home
    /<cluster>/                           5 service cluster (hub) pages
    /<cluster>/<child>/                   sub-cluster pages
    /<cluster>-<city>/                    cluster x service-area pages
    /<brandslug>-<city>/                  service area pages
    /areas/  /faq/  /about/  /contact/    plus 404
    sitemap.xml robots.txt _headers _redirects wrangler.jsonc .assetsignore

HOW TO USE IT FOR A NEW CITY
    1. Edit SITE, AREAS and SILOS.
    2. Edit COPY — the per-page words. This is the part that must be
       genuinely local; everything else is structure.
    3. Run it, drop your images into img/, push to a NEW repo.

Duplicate-content note: run --report after building. It prints sentence
and 5-word-phrase similarity across every pair of generated pages. Keep
average sentence overlap under about 10%.
"""
import io, os, re, json, sys, html

# ==========================================================================
# 1. CONFIG  —  EDIT THIS BLOCK
# ==========================================================================

SITE = dict(
    city        = "Austin",
    state       = "TX",
    state_long  = "Texas",
    region      = "Central Texas",
    county      = "Travis County",
    brand       = "Retaining Wall Contractors Austin",
    brand_short = "Retaining Wall<br>Contractors",
    brand_sub   = "AUSTIN, TX",
    domain      = "https://retainingwallcontractoraustin.com",
    phone       = "(512) 555-0142",
    phone_href  = "tel:15125550142",
    phone_e164  = "+1-512-555-0142",
    email       = "hello@retainingwallcontractoraustin.com",
    hours       = [("Monday – Friday","7:00am – 6:00pm"),
                   ("Saturday","8:00am – 2:00pm"),
                   ("Sunday","Closed")],
    founded     = "2007",
    # the URL prefix for the plain service-area pages
    area_prefix = "retaining-wall-contractor",
)

# Service areas. `blurb` is the one-line local hook; `nearby` drives
# interlinking; `auth` is the actual permitting authority, which is the
# single most useful differentiator between otherwise similar pages.
AREAS = [
 dict(name="West Lake Hills",  slug="west-lake-hills",  auth="the City of West Lake Hills",
      blurb="Steep limestone lots above Bee Creek, where the rock is close to the surface and the walls are structural."),
 dict(name="Rollingwood",      slug="rollingwood",      auth="the City of Rollingwood",
      blurb="Small, established lots falling toward Zilker and the river, with its own building department."),
 dict(name="Barton Creek",     slug="barton-creek",     auth="the City of Austin",
      blurb="Greenbelt-adjacent slopes inside the Barton Springs Zone, where water quality rules shape the design."),
 dict(name="Bee Cave",         slug="bee-cave",         auth="the City of Bee Cave",
      blurb="Hill Country terrain west of the escarpment, thin soil over hard limestone."),
 dict(name="Lakeway",          slug="lakeway",          auth="the City of Lakeway",
      blurb="Lots stepping down toward Lake Travis, where grade change and lake-level drawdown both matter."),
 dict(name="Steiner Ranch",    slug="steiner-ranch",    auth="Travis County",
      blurb="Canyon rim lots between the Colorado River arms, with wildland interface on the boundary."),
 dict(name="Lost Creek",       slug="lost-creek",       auth="the City of Austin",
      blurb="Wooded slopes off Loop 360 where mature heritage trees constrain where a footing can go."),
 dict(name="Tarrytown",        slug="tarrytown",        auth="the City of Austin",
      blurb="Older central lots falling toward Lake Austin, with walls that predate current standards."),
 dict(name="Zilker",           slug="zilker",           auth="the City of Austin",
      blurb="Close-in lots above Barton Creek, tight sites and heritage tree protection."),
 dict(name="Travis Heights",   slug="travis-heights",   auth="the City of Austin",
      blurb="Steep south-central streets on Blunn Creek, dense lots and real gradient."),
 dict(name="Spicewood",        slug="spicewood",        auth="Travis County",
      blurb="Large acreage lots west of the city where walls run long and access is the constraint."),
 dict(name="Dripping Springs", slug="dripping-springs", auth="the City of Dripping Springs",
      blurb="Hays County hill country, shallow soil over limestone and its own review process."),
 dict(name="Cedar Park",       slug="cedar-park",       auth="the City of Cedar Park",
      blurb="Williamson County ground where the escarpment meets flatter prairie."),
 dict(name="Leander",          slug="leander",          auth="the City of Leander",
      blurb="Fast-growing lots on mixed limestone and clay, much of it recent fill."),
 dict(name="Round Rock",       slug="round-rock",       auth="the City of Round Rock",
      blurb="Blackland prairie clay that swells and shrinks hard through the season."),
 dict(name="Georgetown",       slug="georgetown",       auth="the City of Georgetown",
      blurb="North Williamson County, San Gabriel River terraces and karst limestone."),
 dict(name="Pflugerville",     slug="pflugerville",     auth="the City of Pflugerville",
      blurb="Flat expansive-clay ground east of the escarpment, where walls create level yard."),
 dict(name="Hudson Bend",      slug="hudson-bend",      auth="Travis County",
      blurb="Lake Travis peninsula lots with steep drops and long approach drives."),
]
for i,a in enumerate(AREAS):
    a["nearby"] = [AREAS[(i+k) % len(AREAS)]["name"] for k in (1,2,3,4)]

# The silo. Order here is the order in the mega menu and the footer.
SILOS = [
 dict(label="Retaining Wall Repair", slug="retaining-wall-repair", nav="Repair",
      blurb="Leaning, cracking, bulging and weeping walls diagnosed properly — including when a repair holds and when it does not.",
      children=[("Leaning Retaining Wall","leaning-retaining-wall"),
                ("Bulging Wall Repair","bulging-wall-repair"),
                ("Wall Crack Repair","wall-crack-repair"),
                ("Failing Wall Replacement","failing-wall-replacement"),
                ("Wall Anchors &amp; Tiebacks","wall-anchors-tiebacks"),
                ("Drainage Retrofit","drainage-retrofit")]),
 dict(label="Retaining Wall Installation", slug="retaining-wall-installation", nav="Installation",
      blurb="New walls engineered for the ground they are actually holding — drainage, reinforcement and permits handled.",
      children=[("Wall Drainage","wall-drainage"),
                ("Base Preparation","base-preparation"),
                ("Geogrid Reinforcement","geogrid-reinforcement"),
                ("Tiered &amp; Terraced Walls","tiered-terraced-walls"),
                ("Curved Retaining Walls","curved-retaining-walls")]),
 dict(label="Retaining Wall Types", slug="retaining-walls", nav="Wall Types",
      blurb="Every common wall system, side by side, with the trade-offs that decide which one your ground needs.",
      children=[("Limestone Block Walls","limestone-block-walls"),
                ("Concrete Retaining Walls","concrete-retaining-walls"),
                ("CMU Block Walls","cmu-block-walls"),
                ("Wood Retaining Walls","wood-retaining-walls"),
                ("Stone &amp; Boulder Walls","stone-boulder-walls"),
                ("Shotcrete Walls","shotcrete-walls"),
                ("Gabion Walls","gabion-walls")]),
 dict(label="Hill Country Retaining Walls", slug="hill-country-retaining-walls", nav="Hill Country",
      blurb="Escarpment lots, limestone benches and canyon rims — the walls that need engineering rather than landscaping.",
      children=[("Slope Stabilization","slope-stabilization"),
                ("Pier &amp; Beam Walls","pier-and-beam-walls"),
                ("Tieback &amp; Anchored Walls","tieback-anchored-walls"),
                ("Hillside Grading","hillside-grading"),
                ("Erosion Control","erosion-control"),
                ("Downslope &amp; Upslope Lots","downslope-upslope-lots")]),
 dict(label="Commercial Retaining Walls", slug="commercial-retaining-walls", nav="Commercial",
      blurb="Parking, multifamily and site development walls with stamped engineering and inspection coordination.",
      children=[("Parking Lot Retaining Walls","parking-lot-retaining-walls"),
                ("Multi-Unit &amp; HOA Walls","multi-unit-hoa-walls")]),
]
SHOWN = 5   # links per mega-menu column before "View all"

# Which clusters get a page per service area (cluster x city).
CITY_CLUSTERS = ["retaining-wall-repair","retaining-wall-installation"]

# ==========================================================================
# 2. COPY  —  the words. This is the part that has to be genuinely local.
#    Anything in {braces} is filled from SITE / the current area.
# ==========================================================================

COPY = dict(
 # ---- home -------------------------------------------------------------
 home_title   = "Retaining Wall Contractor in {city}, {state} | Free On-Site Estimates",
 home_desc    = "Retaining wall contractor in {city}, {state} — installation, repair and Hill Country "
                "terracing in limestone, concrete, block and timber. Free on-site estimate.",
 home_h1      = "Retaining Wall Contractor",
 home_h1_sub  = "in {city}, {state}",
 home_lede    = "{brand} builds and repairs retaining walls across {region} — from the limestone "
                "benches west of the Balcones Escarpment to the expansive clay east of it. Two very "
                "different grounds, and they do not take the same wall.",
 # the local conditions that make this city a specialist job
 conditions = [
   ("The Balcones Escarpment splits the city in two.",
    "West of it you are on thin soil over hard limestone; east of it you are on Blackland Prairie clay. "
    "A wall designed for one is the wrong wall on the other, and the line runs straight through town."),
   ("Blackland clay moves more than almost any soil in the country.",
    "It swells when it takes on water and shrinks hard in a {city} summer. Footings are sized for that "
    "annual cycle, not for the weight of the wall."),
   ("Limestone is excellent to found on and difficult to dig.",
    "Where rock is shallow it gives superb bearing and changes excavation cost and method entirely."),
   ("Rain arrives as a flood, not a season.",
    "{region} takes much of its rain in a handful of intense storms. Drainage is sized for the peak "
    "event rather than the annual figure."),
   ("Heritage trees are protected and they are everywhere.",
    "{city}'s tree ordinance affects where a footing can go, and it is resolved at design stage rather "
    "than discovered by an inspector."),
   ("Water quality rules apply over the aquifer.",
    "Work in the Barton Springs Zone and the Edwards Aquifer recharge area carries requirements that "
    "ordinary lots do not."),
 ],
 # ---- service area page ------------------------------------------------
 area_title   = "Retaining Wall Contractor in {area}, {state} | Free On-Site Estimates",
 area_desc    = "Retaining wall installation and repair in {area}, {state}. Free on-site estimate and an "
                "itemised written scope. {blurb}",
 area_h1      = "Retaining Wall Contractor",
 area_h1_sub  = "in {area}, {state}",
 area_lede    = "{brand} works throughout {area}. {blurb}",
 area_intro   = "What a wall has to do in {area} is decided before anyone picks a block. {blurb} That "
                "sets the footing, the drainage and frequently the wall system itself, and it is why we "
                "walk the ground before quoting rather than after.",
 area_permit  = "Permits and plan check for {area} go through {auth}. Getting the jurisdiction right "
                "matters here — {region} has a lot of small cities with their own building departments "
                "sitting inside county territory, and sending drawings to the wrong desk costs weeks.",
 # ---- cluster (hub) page -----------------------------------------------
 hub_title    = "{label} in {city}, {state} | Free On-Site Estimates",
 hub_desc     = "{blurb} Serving {city} and {region}. Free on-site estimate and an itemised written scope.",
 hub_lede     = "{brand} — {blurb}",
 # ---- sub-cluster page --------------------------------------------------
 child_title  = "{child} in {city}, {state}",
 child_desc   = "{child} in {city}, {state} — what it is, when it is needed and what the work involves. "
                "Free on-site estimate.",
 # ---- cluster x area page ----------------------------------------------
 cx_title     = "{label} in {area}, {state} | Free On-Site Estimates",
 cx_desc      = "{label} in {area}, {state}. {blurb} Free on-site assessment and an itemised written scope.",
 cx_lede      = "{brand} — {label_lower} throughout {area}.",
 # ---- shared blocks ----------------------------------------------------
 process = [("Site visit","We walk the ground, check drainage, measure, and look at what the grade is doing."),
            ("Written estimate","Line-item scope covering materials, drainage, footing, engineering and timeline."),
            ("Engineering &amp; permits","Soils report, structural plans and plan check tracked before we mobilise."),
            ("Excavation &amp; base","We cut the bench, compact the subgrade and set the footing the wall stands on."),
            ("Build, drain &amp; backfill","Wall, gravel chimney, drain line and compacted backfill — photographed before it is covered.")],
 standards = [("Drainage is never optional.","Gravel chimney, filter fabric, perforated pipe and a legal outlet on every wall that needs one."),
              ("Compaction in lifts, tested where specified.","Fill placed in depths that can actually be compacted."),
              ("Engineering when the job needs it.","Tall walls, walls protecting structures and moving slopes need engineered design and a soils report."),
              ("Permits treated as design work.","Settled at design stage rather than discovered at inspection."),
              ("Progress photos before backfill.","The base, gravel, fabric, pipe and every reinforcement layer."),
              ("A written workmanship warranty.","At sign-off, in plain language.")],
 faq_groups = [
   ("Cost and quoting","What a wall costs, and why nobody can tell you over the phone.", [
     ("How much does a retaining wall cost in {city}?",
      "Height, ground conditions and access drive it far more than the wall type, which is why we do not "
      "publish a price per foot. Whether you are on limestone or Blackland clay can change the footing "
      "entirely on two lots the same height apart."),
     ("Why won't you quote over the phone?",
      "Because a firm number without a site visit is a guess that gets corrected upwards once digging "
      "starts. In {region} what is under the grass is frequently rock at one end and clay at the other."),
     ("What makes one quote cheaper than another?",
      "Usually the lines, not the labour. Drainage is the easiest thing to leave out of a bid and the "
      "hardest thing to notice missing."),
     ("Do you charge for the estimate?",
      "No. On-site estimates are free, carry no obligation, and you keep the written scope either way."),
   ]),
   ("Permits and engineering","When a wall stops being landscaping and becomes a structure.", [
     ("Do I need a permit for a retaining wall in {city}?",
      "Commonly once you pass a height threshold, and sooner with a surcharge above the wall. Which "
      "department reviews it depends on your address — {city}, one of the small incorporated cities, or "
      "the county."),
     ("Does the heritage tree ordinance affect my wall?",
      "It can decide where the footing goes. Protected trees are resolved on paper at design stage, "
      "because moving a wall is cheaper than the alternative."),
     ("What if I'm over the aquifer recharge zone?",
      "Work in the Barton Springs Zone and the Edwards Aquifer recharge area carries water quality "
      "requirements ordinary lots do not. It is a design-stage question."),
     ("Do I need an engineer?",
      "Tall walls, walls protecting a structure and slopes already moving do. We will say so even when "
      "it makes the project larger."),
   ]),
   ("Choosing a wall","Which system belongs on your ground.", [
     ("What type of retaining wall is best here?",
      "There is no universal answer — there is a right one for your height, soil, surcharge, access and "
      "budget. West of the escarpment and east of it usually point at different systems."),
     ("Is limestone block a good choice?",
      "It suits {region} well and matches what is already on most properties. Whether it works "
      "structurally depends on height and what sits above the wall."),
     ("How tall can a wall be without engineering?",
      "There is a height threshold, and it effectively drops to zero the moment something loads the "
      "ground above the wall — a driveway, a pool, a structure."),
     ("Do all retaining walls need drainage?",
      "Every one that retains more than a token amount of soil. On Blackland clay it is the difference "
      "between a wall and a future repair."),
   ]),
   ("Problems with an existing wall","How to read what your wall is telling you.", [
     ("My wall is leaning. Is it dangerous?",
      "It depends how far and whether it is still moving. Get it looked at before the wet season — the "
      "options are far wider while it is standing."),
     ("Are cracks serious?",
      "The pattern matters more than the width. Stepped diagonal cracking usually means settlement; a "
      "horizontal crack across a rigid wall is a pressure signature and worth acting on."),
     ("Can a failing wall be repaired or does it need replacing?",
      "Both happen. Walls that are moving but intact can often be held with anchors and a drainage fix; "
      "walls whose footing has gone are usually cheaper to replace over ten years."),
     ("My wall has no drainage. Can it be added?",
      "Yes, and it is one of the most common jobs we do. On an otherwise sound wall it removes the "
      "cause rather than treating the symptom."),
   ]),
 ],
 # ---- about / contact ---------------------------------------------------
 about_story = "We have been building retaining walls across {region} since {founded}. The work narrowed "
               "to walls on purpose: on ground that changes from limestone to Blackland clay within a few "
               "miles, a retaining wall is a structural problem wearing a landscaping costume, and doing "
               "it alongside patios and planting means doing it second-best.",
 glance = [("{years} years.","Building retaining walls across {region} since {founded}."),
           ("Retaining walls only.","Not a landscaping company with a wall crew — it is the whole of what we do."),
           ("A written itemised scope.","Before you commit, with drainage, footing and engineering as separate lines."),
           ("Drainage on every quote.","The first thing cut from a cheap bid, and the first thing we detail on ours."),
           ("Progress photos before backfill.","The base, gravel, fabric, pipe and every reinforcement layer."),
           ("{n_areas} communities.","Across {region}, concentrated where the ground actually moves.")],
 wont_do = [("Skip the drainage to win a bid","The cheapest way to make a quote look competitive and the most reliable way to guarantee a repair in a few years."),
            ("Quote a wall we have not seen","A number without a site visit is a guess dressed up as a price."),
            ("Say a repair will hold when it will not","Some walls are past repair and replacement is cheaper over ten years."),
            ("Sell a wall against the wrong problem","Where the slope is moving rather than the wall failing, a new wall buys a few years at real expense.")],
)

# ---- inlined theme assets (generated from a working site; do not hand-edit)
FONTFACE = r"""@font-face{font-family:'Barlow';font-style:normal;font-weight:400;font-display:swap;src:url(/fonts/barlow-400.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow';font-style:normal;font-weight:500;font-display:swap;src:url(/fonts/barlow-500.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow';font-style:normal;font-weight:600;font-display:swap;src:url(/fonts/barlow-600.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow';font-style:normal;font-weight:700;font-display:swap;src:url(/fonts/barlow-700.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow Semi Condensed';font-style:normal;font-weight:600;font-display:swap;src:url(/fonts/barlow-sc-600.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow Semi Condensed';font-style:normal;font-weight:700;font-display:swap;src:url(/fonts/barlow-sc-700.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}@font-face{font-family:'Barlow Semi Condensed';font-style:normal;font-weight:800;font-display:swap;src:url(/fonts/barlow-sc-800.woff2) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD}"""

CSS = r"""

:root{
  --navy-900:#0B1721; --navy-800:#12232F; --navy-700:#1B3040; --navy-600:#26404F;
  --green:#2E6B4F; --green-lt:#4A8F6B; --sage:#8FB39B; --sage-pale:#E4EDE6;
  --gold:#D4A62A; --gold-lt:#EFC44B; --gold-dk:#A87F17;
  --cream:#F7F4EC; --paper:#FBFAF8; --stone:#E8E3D7; --line:#DCD6C7;
  --text:#14202A; --muted:#5A6B78;
  --serif:'Barlow Semi Condensed','Barlow',system-ui,sans-serif;
  --sans:'Barlow',system-ui,-apple-system,sans-serif;
  --maxw:1200px;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--text);background:#fff;line-height:1.65;-webkit-font-smoothing:antialiased;overflow-x:hidden}
img,svg{max-width:100%}
a{color:inherit;text-decoration:none}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 26px}
:focus-visible{outline:3px solid var(--gold);outline-offset:3px}

.eyebrow{font-weight:600;font-size:12.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--green);display:flex;align-items:center;gap:12px;margin-bottom:16px}
.eyebrow::before{content:"";width:28px;height:2px;background:var(--gold);flex:none}
.eyebrow.center{justify-content:center}
.eyebrow.light{color:var(--gold-lt)}
h2.sec{font-family:var(--serif);font-weight:800;font-size:clamp(30px,4.2vw,50px);line-height:1.02;letter-spacing:-.015em;text-transform:uppercase;color:var(--navy-900)}
h3{font-family:var(--serif);font-weight:700;letter-spacing:-.008em}
.lede{font-size:17px;color:var(--muted);max-width:62ch;margin-top:18px}

.btn{display:inline-flex;align-items:center;justify-content:center;gap:9px;font-weight:700;font-size:15.5px;padding:15px 28px;border:0;cursor:pointer;border-radius:2px;
  background:linear-gradient(180deg,var(--gold-lt),var(--gold));color:var(--navy-900);
  box-shadow:0 6px 18px rgba(168,127,23,.28);transition:transform .16s,box-shadow .16s,filter .16s}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 26px rgba(168,127,23,.36);filter:brightness(1.04)}
.btn-outline{background:transparent;color:var(--navy-900);border:1.5px solid var(--navy-700);box-shadow:none}
.btn-outline:hover{background:var(--navy-900);color:#fff;box-shadow:none}
.btn-outline-lt{background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.42);box-shadow:none}
.btn-outline-lt:hover{background:rgba(255,255,255,.08);border-color:#fff;box-shadow:none}
.btn-green{background:linear-gradient(180deg,var(--green-lt),var(--green));color:#fff;box-shadow:0 6px 18px rgba(46,107,79,.28)}

/* header */
.topbar{background:var(--navy-900);color:#9FB0BC;font-size:13px}
.topbar .wrap{display:flex;justify-content:space-between;align-items:center;gap:16px;min-height:38px;flex-wrap:wrap}
.topbar a{color:#EAEFF3;font-weight:600}
.topbar .lic{color:var(--gold-lt);font-weight:600}
header.site{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:80}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:22px;padding:14px 26px}
.brand{display:flex;align-items:center;gap:13px}
.brand .mark{width:46px;height:46px;flex:none}
.brand .name{font-family:var(--serif);font-weight:800;font-size:20px;line-height:1.02;white-space:nowrap;letter-spacing:-.012em;text-transform:uppercase;color:var(--navy-900)}
.brand .name small{display:block;font-family:var(--sans);font-weight:600;font-size:10.5px;letter-spacing:.22em;color:var(--green);margin-top:4px}
nav.main{display:flex;gap:26px}
nav.main a{font-weight:600;font-size:15px;color:var(--navy-800);white-space:nowrap}
nav.main a:hover{color:var(--green)}
.nav-tel{font-family:var(--serif);font-weight:700;font-size:19px;color:var(--navy-900)}
.burger{display:none;background:none;border:1px solid var(--line);padding:8px 12px;font-size:18px;cursor:pointer;border-radius:2px}

/* ===== PAGE HERO (photo, compact) ===== */
.phero{position:relative;isolation:isolate;display:flex;align-items:center;min-height:clamp(220px,26vh,310px);background:var(--navy-900);color:#fff;overflow:hidden}
.phero-media{position:absolute;inset:0;z-index:0}
.phero-media img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 58%;display:block}
.phero-media picture{position:absolute;inset:0;z-index:1}

/* centred copy needs an even scrim, not a left-weighted one */
.phero-scrim{position:absolute;inset:0;z-index:2;pointer-events:none;
  background:
    radial-gradient(120% 88% at 50% 50%,rgba(11,23,33,.72) 0%,rgba(11,23,33,.86) 62%,rgba(11,23,33,.94) 100%),
    linear-gradient(180deg,rgba(11,23,33,.6),transparent 30%,transparent 68%,rgba(11,23,33,.72))}
.phero .wrap{position:relative;z-index:4;width:100%;padding-top:22px;padding-bottom:26px}
.phero-copy{max-width:900px;margin-inline:auto;text-align:center}
.crumbs{font-weight:600;letter-spacing:.02em;font-size:13px;color:#A6B4C0;margin-bottom:10px}
.crumbs a:hover{color:var(--gold-lt)}
.crumbs span{color:#6E7E8B;margin:0 9px}
.phero-pill{display:inline-flex;align-items:center;gap:9px;border:1px solid rgba(255,255,255,.28);background:rgba(11,23,33,.5);
  border-radius:999px;padding:6px 15px;margin-bottom:11px;font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#E7EDF2;backdrop-filter:blur(4px)}
.phero-pill svg{width:15px;height:15px;color:var(--gold-lt);flex:none}
.phero h1{font-family:var(--serif);font-weight:800;font-size:clamp(38px,3.5vw,46px);line-height:.98;letter-spacing:-.016em;text-transform:uppercase;color:#fff;text-shadow:0 2px 18px rgba(0,0,0,.5)}
.phero h1 em{font-style:normal;color:var(--gold-lt)}
.phero p{color:#C6D2DA;font-size:15.5px;line-height:1.5;margin:10px auto 0;max-width:66ch;text-shadow:0 1px 10px rgba(0,0,0,.45)}

/* centred call button */
.callbtn{display:inline-flex;align-items:center;gap:12px;margin-top:18px;background:linear-gradient(180deg,var(--gold-lt),var(--gold));
  color:var(--navy-900);padding:9px 26px 9px 9px;border-radius:3px;box-shadow:0 10px 30px rgba(168,127,23,.38);
  font-family:var(--serif);font-weight:800;font-size:clamp(20px,2.1vw,25px);letter-spacing:-.01em;
  transition:transform .16s,box-shadow .16s,filter .16s}
.callbtn:hover{transform:translateY(-2px);box-shadow:0 14px 38px rgba(168,127,23,.48);filter:brightness(1.05)}
.callbtn .cb-ico{width:40px;height:40px;flex:none;background:var(--navy-900);border-radius:3px;display:grid;place-items:center}
.callbtn .cb-ico svg{width:19px;height:19px;color:var(--gold-lt)}
.phero .orlink{display:inline-flex;align-items:center;gap:8px;margin-top:11px;font-weight:700;font-size:14.5px;color:#fff;
  border-bottom:2px solid rgba(255,255,255,.5);padding-bottom:2px;transition:border-color .16s,color .16s}
.phero .orlink:hover{color:var(--gold-lt);border-color:var(--gold-lt)}
.phero .micro{display:block;margin-top:12px;font-size:12.5px;color:#93A5B2;text-shadow:0 1px 8px rgba(0,0,0,.4)}

/* trust strip */
.strip{background:var(--cream);border-bottom:1px solid var(--line)}
.strip .wrap{display:flex;justify-content:space-between;gap:26px;flex-wrap:wrap;padding:14px 26px}
.strip div{display:flex;align-items:center;gap:11px;font-weight:600;font-size:14.5px;color:var(--navy-800)}
.strip svg{width:21px;height:21px;color:var(--green);flex:none}

/* ===== BODY + SIDEBAR ===== */
.pagebody{padding:46px 0 80px}
.cols{display:grid;grid-template-columns:1fr 340px;gap:58px;align-items:start}
article h2{font-family:var(--serif);font-weight:800;font-size:clamp(27px,3.4vw,38px);line-height:1.04;letter-spacing:-.014em;text-transform:uppercase;margin:46px 0 14px;color:var(--navy-900)}
article h2:first-child{margin-top:0}
article h3.sub{font-family:var(--serif);font-weight:700;font-size:21px;margin:28px 0 9px}
article p{margin-bottom:14px;font-size:16.5px;color:#2B333D}
article p a{color:var(--gold-dk);border-bottom:1px solid rgba(168,127,23,.4)}
article strong{font-weight:700;color:var(--text)}

.checklist{list-style:none;margin:18px 0 8px}
.checklist li{position:relative;padding-left:32px;margin-bottom:11px;font-size:16px;color:#2B333D}
.checklist li::before{content:"";position:absolute;left:0;top:7px;width:17px;height:17px;background:var(--gold);
  clip-path:polygon(14% 44%,0 58%,42% 100%,100% 22%,86% 8%,42% 72%)}

/* build layers diagram */
.layers{border:1px solid var(--line);background:var(--paper);padding:24px;margin:24px 0}
.layers svg{width:100%;height:auto;display:block}
.layers .cap{font-size:13px;color:var(--muted);margin-top:14px;text-align:center}

.callouts{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:22px 0 8px}
.callout{border:1px solid var(--line);border-top:4px solid var(--green);padding:20px;background:#fff}
.callout.gold{border-top-color:var(--gold)}
.callout h4{font-family:var(--serif);font-weight:600;font-size:18px;margin-bottom:7px}
.callout p{font-size:14.5px;color:var(--muted);margin:0}

.spec{border:1px solid var(--line);background:#fff;margin:24px 0}
.spec table{width:100%;border-collapse:collapse;font-size:15px}
.spec th{text-align:left;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);padding:16px 20px 12px;border-bottom:2px solid var(--line);font-weight:600}
.spec td{padding:14px 20px;border-bottom:1px solid var(--line);color:#2B333D;vertical-align:top}
.spec tr:last-child td{border-bottom:0}
.spec td:first-child{font-weight:600;color:var(--navy-900);white-space:nowrap}

details.q{background:#fff;border:1px solid var(--line);margin-bottom:11px;padding:20px 24px}
details.q[open]{border-color:var(--gold)}
details.q summary{font-family:var(--serif);font-weight:700;font-size:19px;letter-spacing:-.012em;cursor:pointer;list-style:none;display:flex;justify-content:space-between;gap:18px;align-items:center;color:var(--navy-900)}
details.q summary::-webkit-details-marker{display:none}
details.q summary::after{content:"+";color:var(--gold-dk);font-size:23px;line-height:1;font-family:var(--sans)}
details.q[open] summary::after{content:"–"}
details.q p{margin:11px 0 0;font-size:15.5px;color:var(--muted)}

/* sidebar */
aside{position:sticky;top:100px}
.side-cta{background:var(--navy-900);color:#fff;border-top:5px solid var(--gold);padding:28px 26px}
.side-cta p.sc-h{letter-spacing:-.008em;font-family:var(--serif);font-weight:700;font-size:25px;line-height:1.1;margin-bottom:10px;color:#fff}
.side-cta p{font-size:14.5px;color:#9FB0BC;margin-bottom:20px}
.side-cta .btn{width:100%}
.side-cta .micro{font-size:12.5px;color:#6C7E8B;text-align:center;margin-top:12px}
.side-list{border:1px solid var(--line);border-top:0;background:var(--paper);padding:22px 26px}
.side-list p.sl-h{font-size:11.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);font-weight:600;margin-bottom:14px}
.side-list li{list-style:none;position:relative;padding-left:26px;font-size:14.5px;color:#2B333D;margin-bottom:10px}
.side-list li:last-child{margin-bottom:0}
.side-list li::before{content:"";position:absolute;left:0;top:6px;width:15px;height:15px;background:var(--green);
  clip-path:polygon(14% 44%,0 58%,42% 100%,100% 22%,86% 8%,42% 72%)}

/* sections */
section{padding:82px 0}
.alt{background:var(--paper)}
.dark{background:var(--navy-900);color:#fff}
.dark h2.sec{color:#fff}
.dark .lede{color:#9FB0BC}
.sec-head{max-width:760px}
.sec-head.center{margin:0 auto;text-align:center}
.sec-head.center .lede{margin-inline:auto}

/* included grid */
.inc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:44px}
.inc{background:#fff;border:1px solid var(--line);border-top:4px solid var(--navy-900);padding:26px 24px;transition:transform .16s,box-shadow .16s,border-top-color .16s}
.inc:hover{transform:translateY(-4px);box-shadow:0 16px 36px rgba(11,23,33,.1);border-top-color:var(--gold)}
.inc .ico{width:38px;height:38px;color:var(--green);margin-bottom:15px}
.inc h3{font-size:20px;margin-bottom:7px}
.inc p{font-size:14.5px;color:var(--muted)}

/* steps */
.steps{display:grid;grid-template-columns:repeat(5,1fr);margin-top:48px;position:relative}
.steps::before{content:"";position:absolute;top:28px;left:9%;right:9%;height:1px;background:var(--navy-700)}
.step{text-align:center;padding:0 16px;position:relative}
.step .n{width:56px;height:56px;margin:0 auto 20px;border-radius:50%;background:var(--navy-800);color:var(--gold-lt);
  font-family:var(--serif);font-weight:700;font-size:22px;display:grid;place-items:center;position:relative;z-index:2;border:5px solid var(--navy-900)}
.step:first-child .n{background:var(--gold);color:var(--navy-900)}
.step h3{font-size:18px;margin-bottom:7px;color:#fff}
.step p{font-size:14px;color:#9FB0BC}

/* reviews */
.rev-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:42px}
.rev{background:#fff;border:1px solid var(--line);padding:26px}
.rev .stars{color:var(--gold);letter-spacing:2px;font-size:14px}
.rev p{font-size:15px;color:#2B333D;margin:11px 0 15px}
.rev b{font-family:var(--serif);font-weight:600;font-size:17px;color:var(--navy-900)}
.rev b span{display:block;font-family:var(--sans);font-weight:500;font-size:12.5px;color:var(--muted);margin-top:2px}

/* services in this category */
.cat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:22px 0 8px}
.cat{background:#fff;border:1px solid var(--line);border-radius:3px;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;gap:14px;
  font-weight:600;font-size:15.5px;color:var(--navy-900);transition:border-color .16s,box-shadow .16s,transform .16s}
.cat:hover{border-color:var(--gold);box-shadow:0 8px 22px rgba(11,23,33,.08);transform:translateY(-2px)}
.cat .arw{color:var(--gold-dk);font-weight:700;font-size:17px;flex:none;transition:transform .16s}
.cat:hover .arw{transform:translateX(4px)}

/* areas — visual cards */
.areas-intro{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center;margin-bottom:52px}
.areas-art{border:1px solid var(--line);border-radius:4px;overflow:hidden;aspect-ratio:16/10;background:var(--stone);position:relative}
.areas-art .ph{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;padding:22px;text-align:center;color:#8A8371;background:repeating-linear-gradient(45deg,#EFEADE 0 14px,#E8E3D7 14px 28px);z-index:1}
.areas-art img{z-index:2}
.areas-art img,.areas-art .ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.acard-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
.acard{position:relative;display:block;aspect-ratio:5/4;overflow:hidden;border:1px solid var(--line);border-radius:4px;background:var(--navy-800);
  transition:transform .2s,box-shadow .2s,border-color .2s}
.acard:hover{transform:translateY(-5px);box-shadow:0 20px 44px rgba(11,23,33,.22);border-color:var(--gold)}
.acard-media{position:absolute;inset:0;overflow:hidden;isolation:isolate}
.acard-media img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;z-index:1;transition:transform .5s ease}
.acard:hover .acard-media img{transform:scale(1.06)}
/* illustrated fallback: layered terrace courses, tint varies per card */
.acard-media::before{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(45deg,#1D2E3B 0 14px,#182734 14px 28px)}

.acard-scrim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,23,33,.15) 0%,rgba(11,23,33,.35) 45%,rgba(11,23,33,.9) 100%)}
.acard-body{position:absolute;left:0;right:0;bottom:0;padding:20px 20px 22px;z-index:2}
.acard-eyebrow{display:block;font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--gold-lt);margin-bottom:7px}
.acard-title{display:block;font-family:var(--serif);font-weight:800;font-size:21px;line-height:1.12;letter-spacing:-.008em;text-transform:uppercase;color:#fff}
.acard:hover .acard-title{color:var(--gold-lt)}
.acard-all{display:grid;place-items:center;background:var(--navy-900);border:1px solid var(--navy-700);text-align:center;padding:24px}
.acard-all:hover{border-color:var(--gold);background:var(--navy-800)}
.acard-all span{font-family:var(--serif);font-weight:800;font-size:21px;text-transform:uppercase;color:#fff;line-height:1.15}
.acard-all em{display:block;font-family:var(--sans);font-style:normal;font-weight:700;font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--gold-lt);margin-top:9px}

/* related */
.rel-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:42px}
.rel{background:#fff;border:1px solid var(--line);border-top:4px solid var(--navy-900);padding:26px 24px;transition:transform .16s,box-shadow .16s,border-top-color .16s}
.rel:hover{transform:translateY(-4px);box-shadow:0 16px 36px rgba(11,23,33,.1);border-top-color:var(--gold)}
.rel h3{font-size:20px;margin-bottom:7px}
.rel p{font-size:14.5px;color:var(--muted)}
.rel .go{display:inline-block;margin-top:12px;font-weight:700;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--gold-dk)}

/* GBP / NAP */

/* final */
.final{background:linear-gradient(150deg,var(--green) 0%,#20503B 100%);color:#fff;text-align:center;position:relative;overflow:hidden}
.final::before{content:"";position:absolute;inset:0;opacity:.09;background-image:linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px);background-size:48px 48px}
.final .wrap{position:relative;z-index:2}
.final p.final-h{margin:0;max-width:none;color:#fff;font-family:var(--serif);font-weight:800;font-size:clamp(30px,4.6vw,52px);line-height:1.02;letter-spacing:-.016em;text-transform:uppercase}
.final p{margin:16px auto 28px;max-width:58ch;color:rgba(255,255,255,.88);font-size:17px}
.final .cta-row{display:flex;gap:13px;justify-content:center;flex-wrap:wrap}
.final .tapcall.center{margin-top:6px}

/* footer */
footer{background:var(--navy-900);color:#8FA1AE;padding:58px 0 24px;font-size:14.5px}
.f-grid{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:38px}
footer p.f-h{font-weight:700;text-transform:uppercase;color:#fff;font-size:12.5px;letter-spacing:.16em;margin-bottom:16px}
footer ul{list-style:none}
footer li{margin-bottom:9px}
footer a:hover{color:var(--gold-lt)}
footer .brand{margin-bottom:16px}
footer .brand .name{color:#fff}
.legal{border-top:1px solid var(--navy-700);margin-top:42px;padding-top:22px;font-size:12.5px;color:#677885;line-height:1.65}


/* ---- header call button: shiny gold ---- */
.nav-tel{display:inline-flex;align-items:center;gap:11px;font-family:var(--serif);font-weight:800;font-size:clamp(19px,1.6vw,24px);
  letter-spacing:-.01em;color:var(--navy-900);padding:8px 20px 8px 8px;border-radius:4px;
  background:linear-gradient(180deg,#FBE49C 0%,#EFC44B 42%,#D4A62A 56%,#B0891B 100%);
  box-shadow:0 6px 18px rgba(168,127,23,.34),inset 0 1px 0 rgba(255,255,255,.6);
  transition:transform .16s,box-shadow .16s,filter .16s}
.nav-tel:hover{transform:translateY(-1px);filter:brightness(1.05);box-shadow:0 10px 24px rgba(168,127,23,.44),inset 0 1px 0 rgba(255,255,255,.6)}
.nav-tel .nt-ico{width:36px;height:36px;flex:none;background:var(--navy-900);border-radius:3px;display:grid;place-items:center}
.nav-tel .nt-ico svg{width:17px;height:17px;color:var(--gold-lt)}

/* ---- underlined secondary link (replaces the outlined button) ---- */
.textlink{display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:15px;color:#fff;
  border-bottom:2px solid rgba(255,255,255,.5);padding-bottom:3px;transition:color .16s,border-color .16s}
.textlink:hover{color:var(--gold-lt);border-color:var(--gold-lt)}
.textlink.dark{color:var(--navy-900);border-bottom-color:rgba(11,23,33,.35)}
.textlink.dark:hover{color:var(--gold-dk);border-bottom-color:var(--gold-dk)}

/* ---- footer service-area index ---- */
.f-areas{border-top:1px solid var(--navy-700);margin-top:40px;padding-top:32px}
.f-areas-head{display:flex;justify-content:space-between;align-items:baseline;gap:20px;flex-wrap:wrap;margin-bottom:8px}
.f-areas-head p.f-h{margin-bottom:0}
.f-areas-head span{font-size:13.5px;color:#7E909C}
.f-areas p.f-sub{font-weight:700;text-transform:uppercase;color:#B7C4CE;font-size:12.5px;letter-spacing:.16em;margin:22px 0 18px}
.f-area-list{display:grid;grid-template-columns:repeat(4,1fr);gap:14px 28px;list-style:none}
.f-area-list li{margin:0}
.f-area-list a{display:inline-flex;align-items:flex-start;gap:8px;font-size:14.5px;color:#8FA1AE;line-height:1.4}
.f-area-list a svg{width:14px;height:14px;flex:none;margin-top:3px;color:var(--green-lt);transition:color .15s}
.f-area-list a:hover{color:#fff}
.f-area-list a:hover svg{color:var(--gold-lt)}
.f-contact li{display:flex;gap:11px;align-items:flex-start;margin-bottom:13px}
.f-contact svg{width:17px;height:17px;flex:none;margin-top:3px;color:var(--gold)}

/* ---- mobile sticky call bar ---- */
.mobilebar{position:fixed;left:0;right:0;bottom:0;z-index:140;display:none;
  box-shadow:0 -6px 26px rgba(0,0,0,.32);transform:translateY(115%);transition:transform .3s cubic-bezier(.22,.61,.36,1);
  padding-bottom:env(safe-area-inset-bottom,0px)}
.mobilebar.show{transform:none}
.mb-row{display:grid;grid-template-columns:1fr 1fr}
.mb-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;
  min-height:62px;padding:10px 12px;text-align:center;transition:filter .16s}
.mb-btn:active{filter:brightness(.94)}
.mb-label{display:block;font-size:10.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
.mb-main{display:block;font-family:var(--serif);font-weight:800;font-size:22px;line-height:1.06;letter-spacing:-.012em;white-space:nowrap}
.mb-call{background:linear-gradient(180deg,#FBE49C 0%,#EFC44B 40%,#D4A62A 58%,#B0891B 100%);color:var(--navy-900)}
.mb-call .mb-label{color:rgba(11,23,33,.72)}
.mb-quote{background:linear-gradient(180deg,#22394A 0%,#162937 55%,#0B1721 100%);color:#fff;
  box-shadow:inset 2px 0 0 rgba(239,196,75,.6)}
.mb-quote .mb-label{color:var(--gold-lt)}
@media(max-width:360px){.mb-main{font-size:19px}}
@media(max-width:900px){
  .mobilebar{display:block}
  body{padding-bottom:78px}
}


/* gold hyperlink CTA (not a button) */
.goldlink{display:inline-block;margin-top:15px;font-weight:700;font-size:15px;color:var(--gold-dk);
  border-bottom:2px solid rgba(168,127,23,.45);padding-bottom:3px;transition:color .16s,border-color .16s}
.goldlink:hover{color:var(--gold);border-color:var(--gold)}
.tapcall.center{margin-inline:auto}
.type .blurb{font-size:15px;color:var(--muted);margin-bottom:0}
.type .viewlink{display:inline-flex;align-items:center;gap:8px;margin-top:16px;font-weight:700;font-size:14.5px;
  color:var(--gold-dk);border-bottom:2px solid rgba(168,127,23,.4);padding-bottom:3px;transition:color .16s,border-color .16s}
.type .viewlink:hover{color:var(--gold);border-color:var(--gold)}

/* real-photo slots with a visible placeholder until the file exists */
.shot{margin:26px 0 4px;border:1px solid var(--line);background:#fff}
.shot-box{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;background:var(--stone)}
.shot-box img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:2;display:block}
.shot .ph{position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:7px;padding:22px;text-align:center;color:#8A8371;
  background:repeating-linear-gradient(45deg,#EFEADE 0 14px,#E8E3D7 14px 28px)}
.shot .ph svg{width:32px;height:32px;opacity:.6}
.shot .ph b{font-size:11.5px;font-weight:700;letter-spacing:.17em;text-transform:uppercase}
.shot .ph code{font-size:11.5px;color:#6E6858;word-break:break-all}
.shot .ph small{font-size:12.5px;max-width:48ch;line-height:1.5}
.shot.wide{margin:30px 0 6px}
.mini-why{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:22px 0 6px}
.mini-why div{border:1px solid var(--line);border-left:3px solid var(--green);padding:18px 20px;background:#fff}
.mini-why h3{font-size:18px;margin-bottom:6px}
.mini-why p{font-size:14.5px;color:var(--muted);margin:0}
@media(max-width:640px){.mini-why{grid-template-columns:1fr}}

@media(max-width:1150px){
  nav.main{display:none}
  .burger{display:flex}
  .cols{grid-template-columns:1fr;gap:46px}
  aside{position:static}
  .inc-grid,.rev-grid,.rel-grid{grid-template-columns:repeat(2,1fr)}
  .steps{grid-template-columns:repeat(2,1fr);gap:34px 0}
  .steps::before{display:none}
  .acard-grid{grid-template-columns:repeat(2,1fr)}
  .areas-intro{grid-template-columns:1fr;gap:36px}
  .f-grid{grid-template-columns:repeat(2,1fr)}
  .f-area-list{grid-template-columns:repeat(2,1fr)}
  .f-areas-head{gap:8px}
  .phero-media img{object-position:center 58%}
  .phero-scrim{background:radial-gradient(140% 90% at 50% 50%,rgba(11,23,33,.76),rgba(11,23,33,.92) 70%),linear-gradient(180deg,rgba(11,23,33,.6),transparent 32%,rgba(11,23,33,.74))}
}
@media(max-width:640px){
  .f-area-list{grid-template-columns:1fr}
  section{padding:60px 0}
  .callbtn{width:100%;justify-content:center;padding:10px 20px 10px 10px;font-size:22px;gap:11px}
  .callbtn .cb-ico{width:42px;height:42px}
  .crumbs{font-size:12.5px}
  .inc-grid,.rev-grid,.rel-grid,.steps,.f-grid,.callouts,.cat-grid{grid-template-columns:1fr}
  .acard-grid{grid-template-columns:repeat(2,1fr);gap:12px}
  .acard-title{font-size:16px}
  .nav-tel{display:none}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}html{scroll-behavior:auto}}

/* ===== near-me + service-area map ===== */
.nearme{background:#fff}
.nearme .cols{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center}
.nearme p{color:var(--muted);font-size:16.5px;margin-bottom:15px}
.nearme p a{color:var(--gold-dk);font-weight:600;border-bottom:1px solid rgba(168,127,23,.4)}
.nearme p a:hover{border-color:var(--gold-dk)}
.mapframe{position:relative;border:1px solid var(--line);border-radius:4px;overflow:hidden;background:var(--stone);aspect-ratio:4/3;box-shadow:0 14px 36px rgba(11,23,33,.09)}
.mapframe iframe{position:absolute;inset:0;width:100%;height:100%;border:0;display:block;filter:saturate(.92)}
.mapcap{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-top:14px;font-size:13.5px;color:var(--muted)}
.mapcap b{color:var(--navy-900);font-weight:700}
@media(max-width:1050px){.nearme .cols{grid-template-columns:1fr;gap:40px}}

/* ===== mobile menu: visible trigger + slide-in drawer ===== */
.burger{flex:none;width:46px;height:44px;align-items:center;justify-content:center;
  background:var(--navy-900);border:0;border-radius:3px;cursor:pointer;padding:0}
.burger:hover{background:var(--navy-700)}
.burger .bars,.burger .bars::before,.burger .bars::after{display:block;width:20px;height:2px;
  background:#fff;border-radius:2px}
.burger .bars{position:relative}
.burger .bars::before,.burger .bars::after{content:"";position:absolute;left:0}
.burger .bars::before{top:-6px}
.burger .bars::after{top:6px}

.navdrawer{position:fixed;inset:0;z-index:200}
.navdrawer[hidden]{display:none}
.nd-backdrop{position:absolute;inset:0;background:rgba(6,13,19,.62);opacity:0;transition:opacity .28s ease}
.nd-panel{position:absolute;top:0;right:0;height:100%;width:min(320px,86vw);background:var(--navy-900);
  color:#fff;display:flex;flex-direction:column;transform:translateX(100%);
  transition:transform .3s cubic-bezier(.22,.61,.36,1);box-shadow:-18px 0 46px rgba(0,0,0,.42)}
.navdrawer.open .nd-backdrop{opacity:1}
.navdrawer.open .nd-panel{transform:none}
.nd-head{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:calc(16px + env(safe-area-inset-top,0px)) 20px 16px;border-bottom:1px solid rgba(255,255,255,.13)}
.nd-title{font-family:var(--sans);font-weight:700;font-size:11.5px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--gold-lt)}
.nd-close{background:none;border:0;color:#fff;font-size:26px;line-height:1;cursor:pointer;
  width:40px;height:40px;display:grid;place-items:center;border-radius:3px}
.nd-close:hover{background:rgba(255,255,255,.09)}
.nd-nav{display:flex;flex-direction:column;flex:1;overflow-y:auto;padding:4px 0}
.nd-nav a{font-family:var(--serif);font-weight:700;font-size:21px;letter-spacing:-.01em;color:#fff;
  padding:15px 20px;border-bottom:1px solid rgba(255,255,255,.08)}
.nd-nav a:hover,.nd-nav a:focus-visible{background:rgba(255,255,255,.07);color:var(--gold-lt)}
.nd-cta{display:grid;gap:10px;padding:18px 20px calc(20px + env(safe-area-inset-bottom,0px));
  border-top:1px solid rgba(255,255,255,.13)}
.nd-call{display:block;text-align:center;border-radius:3px;padding:11px 16px;color:var(--navy-900);
  background:linear-gradient(180deg,var(--gold-lt),var(--gold))}
.nd-call small{display:block;font-size:10.5px;font-weight:700;letter-spacing:.16em;
  text-transform:uppercase;color:rgba(11,23,33,.72)}
.nd-call b{display:block;font-family:var(--serif);font-weight:800;font-size:22px;line-height:1.15}
.nd-est{display:block;text-align:center;border:1.5px solid rgba(255,255,255,.45);border-radius:3px;
  padding:12px 16px;font-weight:700;font-size:14.5px;color:#fff}
.nd-est:hover{background:rgba(255,255,255,.09);border-color:#fff}
body.nav-open{overflow:hidden}
@media(prefers-reduced-motion:reduce){.nd-panel,.nd-backdrop{transition:none}}

/* ===== desktop mega menu ===== */
.nav-mega{position:relative}
.megatrig{white-space:nowrap;display:inline-flex;align-items:center;gap:6px;background:none;border:0;padding:0;cursor:pointer;
  font-family:var(--sans);font-weight:600;font-size:15px;color:var(--navy-800)}
.megatrig .chev{width:15px;height:15px;transition:transform .2s}
.megatrig:hover,.megatrig[aria-expanded="true"]{color:var(--green)}
.megatrig[aria-expanded="true"] .chev{transform:rotate(180deg)}
.mega{position:absolute;left:0;right:0;top:100%;background:#fff;border-top:3px solid var(--gold);
  border-bottom:1px solid var(--line);box-shadow:0 22px 44px rgba(11,23,33,.16);z-index:90}
.mega[hidden]{display:none}
.mega-cols{display:grid;grid-template-columns:repeat(5,1fr);gap:32px;padding:34px 0 30px}
.mega-col .mega-h{font-family:var(--sans);font-weight:700;font-size:12.5px;letter-spacing:.15em;
  text-transform:uppercase;color:var(--navy-900);padding-bottom:12px;margin-bottom:14px;
  border-bottom:1px solid var(--line)}
.mega-col .mega-h a{color:inherit}
.mega-col .mega-h a:hover{color:var(--green)}
.mega-col a{display:block;font-size:14.5px;color:#41505C;padding:7px 0}
.mega-col a:hover{color:var(--green)}
.mega-all{margin-top:12px;font-weight:700;font-size:13px;letter-spacing:.04em;color:var(--gold-dk)!important}
.mega-all:hover{color:var(--gold)!important}

/* ===== drawer accordions ===== */
.nd-acc,.nd-acc2{display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;
  background:none;border:0;cursor:pointer;text-align:left;color:#fff;font-family:var(--serif)}
.nd-acc{font-weight:700;font-size:21px;letter-spacing:-.01em;padding:15px 20px;
  border-bottom:1px solid rgba(255,255,255,.08)}
.nd-acc2{font-family:var(--sans);font-weight:600;font-size:15px;padding:13px 20px 13px 32px;
  border-bottom:1px solid rgba(255,255,255,.07);color:#DCE5EB}
.nd-acc .chev,.nd-acc2 .chev{width:17px;height:17px;flex:none;transition:transform .2s;color:var(--gold-lt)}
.nd-acc[aria-expanded="true"] .chev,.nd-acc2[aria-expanded="true"] .chev{transform:rotate(180deg)}
.nd-acc:hover,.nd-acc2:hover{background:rgba(255,255,255,.07)}
.nd-sub{background:rgba(0,0,0,.22)}
.nd-sub[hidden],.nd-sub2[hidden]{display:none}
.nd-sub2{background:rgba(0,0,0,.28);padding:4px 0 10px}
.nd-sub2 a{display:block;font-family:var(--sans);font-weight:500;font-size:14.5px;color:#B9C6D0;
  padding:10px 20px 10px 44px;border-bottom:0}
.nd-sub2 a:hover{color:var(--gold-lt);background:rgba(255,255,255,.05)}
.nd-all{font-weight:700!important;color:var(--gold-lt)!important;letter-spacing:.03em}

/* brand mention in the hero sub-headline, linked back to the homepage */
.phero-copy p .brandlink{color:var(--gold-lt);font-weight:700;border-bottom:1px solid rgba(239,196,75,.45);transition:border-color .16s}
.phero-copy p .brandlink:hover{border-color:var(--gold-lt)}

/* ===== service areas dropdown ===== */
.nav-areas{position:relative}
.areatrig{display:inline-flex;align-items:center;gap:6px;background:none;border:0;padding:0;cursor:pointer;
  white-space:nowrap;font-family:var(--sans);font-weight:600;font-size:15px;color:var(--navy-800)}
.areatrig .chev{width:15px;height:15px;transition:transform .2s}
.areatrig:hover,.areatrig[aria-expanded="true"]{color:var(--green)}
.areatrig[aria-expanded="true"] .chev{transform:rotate(180deg)}
.areadrop{position:absolute;left:50%;transform:translateX(-50%);top:calc(100% + 14px);width:300px;
  background:#fff;border-top:3px solid var(--gold);border-bottom:1px solid var(--line);
  box-shadow:0 22px 44px rgba(11,23,33,.18);z-index:95;border-radius:0 0 4px 4px}
.areadrop[hidden]{display:none}
.areadrop .ad-h{font-family:var(--sans);font-weight:700;font-size:12.5px;letter-spacing:.15em;text-transform:uppercase;
  color:var(--navy-900);padding:22px 24px 12px;margin:0 0 2px;border-bottom:1px solid var(--line)}
.arealist{max-height:396px;overflow-y:auto;padding:6px 0;scrollbar-width:thin}
.arealist::-webkit-scrollbar{width:8px}
.arealist::-webkit-scrollbar-thumb{background:#D6D0C2;border-radius:4px}
.arealist::-webkit-scrollbar-track{background:#F3F0E8}
.arealist a{display:block;font-size:14.5px;color:#41505C;padding:9px 24px}
.arealist a:hover{color:var(--green);background:var(--paper)}
.areadrop .areadrop-all{display:block;padding:13px 24px;border-top:1px solid var(--line);
  font-weight:700;font-size:13px;letter-spacing:.04em;color:var(--gold-dk)}
.areadrop .areadrop-all:hover{color:var(--gold)}

.nd-arealist{max-height:none}
.nd-arealist a{padding-left:32px}


.nav-actions{display:flex;align-items:center;gap:10px;flex:none}
.nav-est{display:inline-flex;align-items:center;font-weight:700;font-size:14.5px;letter-spacing:.01em;
  color:var(--navy-900);border:1.5px solid #C9D0D6;background:#fff;padding:13px 18px;border-radius:4px;
  transition:border-color .16s,background .16s,color .16s}
.nav-est:hover{border-color:var(--navy-900);background:var(--navy-900);color:#fff}
@media(max-width:1240px){.nav-est{padding:11px 14px;font-size:13.5px}}
@media(max-width:1150px){.nav-est{display:none}}


/* The top bar duplicates the phone number, and below 900px the sticky
   call bar takes over that job, so it is hidden rather than wrapped. */
@media(max-width:900px){.topbar{display:none}}
"""

ABOUT_CSS = r"""<style>
/* About: text column beside a sticky photo + at-a-glance rail */
.abx{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:clamp(28px,3.4vw,54px);align-items:start}
.abx-main>h2:first-child{margin-top:0}
.abx-main h2{font-family:var(--serif);font-weight:800;font-size:clamp(25px,2.5vw,32px);line-height:1.06;
  letter-spacing:-.015em;color:var(--navy-900);margin:38px 0 14px}
.abx-main h2:first-of-type{margin-top:0}
.abx-main p{margin-bottom:15px}
.abx-rail{position:sticky;top:24px;display:grid;gap:18px}
.abx-photo{display:block;width:100%;aspect-ratio:3/4;overflow:hidden;background:var(--navy-900)}
.abx-photo img{width:100%;height:100%;object-fit:cover;display:block}
.glance{border:1px solid var(--line);border-top:4px solid var(--gold);background:#fff;padding:24px 24px 22px}
.glance p.gl-h{font-family:var(--serif);font-weight:700;font-size:20px;letter-spacing:-.01em;color:var(--navy-900);margin-bottom:16px}
.glance ul{list-style:none;display:grid;gap:14px;margin-bottom:20px}
.glance li{display:grid;grid-template-columns:20px 1fr;gap:13px;align-items:start;font-size:14.5px;line-height:1.5;color:var(--muted)}
.glance li svg{width:18px;height:18px;color:var(--gold);margin-top:2px;flex:none}
.glance li strong{color:var(--navy-900);font-weight:700}
.glance .btn{width:100%}
.glance .micro{font-size:12.5px;color:var(--muted);text-align:center;margin-top:11px;line-height:1.5}

/* Contact: info cards beside the form */
.cx{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(20px,2.4vw,34px);align-items:start}
.cx-cards{display:grid;gap:14px;align-content:start}
.ccard{border:1px solid var(--line);background:#fff;padding:20px 22px;display:grid;grid-template-columns:42px 1fr;gap:15px;align-items:start}
.ccard .ci{width:42px;height:42px;display:grid;place-items:center;border-radius:50%;background:var(--navy-900);color:var(--gold-lt)}
.ccard .ci svg{width:18px;height:18px}
.ccard p.cc-h{margin-top:0;line-height:1.65;font-family:var(--sans);font-weight:700;font-size:11.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--green);margin-bottom:6px}
.ccard .big{display:block;font-family:var(--serif);font-weight:800;font-size:22px;line-height:1.15;letter-spacing:-.015em;color:var(--navy-900);word-break:break-word}
.ccard .big a{color:inherit}
.ccard p{font-size:14px;color:var(--muted);margin:6px 0 0;line-height:1.55}
.ccard dl{display:grid;grid-template-columns:1fr auto;gap:5px 16px;font-size:14.5px;margin-top:2px}
.ccard dt{color:var(--muted)}
.ccard dd{font-weight:700;color:var(--navy-900);text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:960px){.abx,.cx{grid-template-columns:1fr}.abx-rail{position:static}
  .abx-photo{aspect-ratio:16/10;max-height:420px}}
</style>"""

CONTACT_CSS = r"""<style>
/* About: text column beside a sticky photo + at-a-glance rail */
.abx{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:clamp(28px,3.4vw,54px);align-items:start}
.abx-main>h2:first-child{margin-top:0}
.abx-main h2{font-family:var(--serif);font-weight:800;font-size:clamp(25px,2.5vw,32px);line-height:1.06;
  letter-spacing:-.015em;color:var(--navy-900);margin:38px 0 14px}
.abx-main h2:first-of-type{margin-top:0}
.abx-main p{margin-bottom:15px}
.abx-rail{position:sticky;top:24px;display:grid;gap:18px}
.abx-photo{display:block;width:100%;aspect-ratio:3/4;overflow:hidden;background:var(--navy-900)}
.abx-photo img{width:100%;height:100%;object-fit:cover;display:block}
.glance{border:1px solid var(--line);border-top:4px solid var(--gold);background:#fff;padding:24px 24px 22px}
.glance p.gl-h{font-family:var(--serif);font-weight:700;font-size:20px;letter-spacing:-.01em;color:var(--navy-900);margin-bottom:16px}
.glance ul{list-style:none;display:grid;gap:14px;margin-bottom:20px}
.glance li{display:grid;grid-template-columns:20px 1fr;gap:13px;align-items:start;font-size:14.5px;line-height:1.5;color:var(--muted)}
.glance li svg{width:18px;height:18px;color:var(--gold);margin-top:2px;flex:none}
.glance li strong{color:var(--navy-900);font-weight:700}
.glance .btn{width:100%}
.glance .micro{font-size:12.5px;color:var(--muted);text-align:center;margin-top:11px;line-height:1.5}

/* Contact: info cards beside the form */
.cx{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(20px,2.4vw,34px);align-items:start}
.cx-cards{display:grid;gap:14px;align-content:start}
.ccard{border:1px solid var(--line);background:#fff;padding:20px 22px;display:grid;grid-template-columns:42px 1fr;gap:15px;align-items:start}
.ccard .ci{width:42px;height:42px;display:grid;place-items:center;border-radius:50%;background:var(--navy-900);color:var(--gold-lt)}
.ccard .ci svg{width:18px;height:18px}
.ccard p.cc-h{margin-top:0;line-height:1.65;font-family:var(--sans);font-weight:700;font-size:11.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--green);margin-bottom:6px}
.ccard .big{display:block;font-family:var(--serif);font-weight:800;font-size:22px;line-height:1.15;letter-spacing:-.015em;color:var(--navy-900);word-break:break-word}
.ccard .big a{color:inherit}
.ccard p{font-size:14px;color:var(--muted);margin:6px 0 0;line-height:1.55}
.ccard dl{display:grid;grid-template-columns:1fr auto;gap:5px 16px;font-size:14.5px;margin-top:2px}
.ccard dt{color:var(--muted)}
.ccard dd{font-weight:700;color:var(--navy-900);text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:960px){.abx,.cx{grid-template-columns:1fr}.abx-rail{position:static}
  .abx-photo{aspect-ratio:16/10;max-height:420px}}
</style>"""

FORM = r"""<div class="cform">
        <p class="cf-h">Request a free on-site estimate</p>
        <p class="hint">Tell us what the slope is doing. We read every message and reply during working hours &mdash; usually the same day.</p>
        <form id="estimate-form" novalidate>
          <div class="frow">
            <div class="fld"><label for="f-name">Name <span class="req">*</span></label>
              <input id="f-name" name="name" type="text" autocomplete="name" required></div>
            <div class="fld"><label for="f-phone">Phone <span class="req">*</span></label>
              <input id="f-phone" name="phone" type="tel" autocomplete="tel" required></div>
          </div>
          <div class="frow">
            <div class="fld"><label for="f-email">Email</label>
              <input id="f-email" name="email" type="email" autocomplete="email"></div>
            <div class="fld"><label for="f-city">Property city or neighbourhood</label>
              <input id="f-city" name="city" type="text" autocomplete="address-level2"></div>
          </div>
          <div class="fld"><label for="f-type">What do you need?</label>
            <select id="f-type" name="type">
              <option>A new retaining wall</option>
              <option>An existing wall repaired</option>
              <option>An existing wall assessed &mdash; not sure yet</option>
              <option>Drainage work on an existing wall</option>
              <option>Hillside or slope work</option>
              <option>Commercial, multi-unit or HOA property</option>
              <option>Something else</option>
            </select></div>
          <div class="fld"><label for="f-msg">Tell us about the slope <span class="req">*</span></label>
            <textarea id="f-msg" name="message" required placeholder="Roughly how tall and how long is the wall? Is it new work or an existing wall? If it is existing, what is it doing &mdash; leaning, cracking, bulging, weeping after rain?"></textarea></div>
          <button type="submit">Send my request</button>
          <p class="fnote">No obligation, and no pressure to sign anything on the spot. We will not pass your details to anyone else.</p>
          <div class="fmsg" id="f-msg-out" role="status" aria-live="polite"></div>
        </form>
      </div>"""

_SCRIPTS = r"""<script>
(function(){
  var bar=document.getElementById('mobilebar');
  var hero=document.querySelector('.hero')||document.querySelector('.phero');
  if(!bar) return;
  function trigger(){ return hero ? hero.offsetHeight*0.75 : 380; }
  function onScroll(){
    if(window.scrollY > trigger()) bar.classList.add('show');
    else bar.classList.remove('show');
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',onScroll,{passive:true});
  onScroll();
})();
</script>
<script>
(function(){
  var d = document.getElementById('navdrawer');
  var b = document.querySelector('.burger');
  if (!d || !b) return;
  var panel = d.querySelector('.nd-panel'), lastFocus = null, hideTimer = null;

  function open(){
    lastFocus = document.activeElement;
    clearTimeout(hideTimer);
    d.hidden = false;
    void d.offsetWidth;                    // flush layout so the slide-in animates
    d.classList.add('open');
    b.setAttribute('aria-expanded','true');
    document.body.classList.add('nav-open');
    var c = d.querySelector('.nd-close'); if (c) c.focus();
  }
  function close(){
    d.classList.remove('open');
    b.setAttribute('aria-expanded','false');
    document.body.classList.remove('nav-open');
    hideTimer = setTimeout(function(){ d.hidden = true; }, 320);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  b.addEventListener('click', open);
  d.addEventListener('click', function(e){
    var t = e.target;
    if (t && t.closest && (t.closest('[data-close]') || t.closest('.nd-nav a'))) close();
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && d.classList.contains('open')) close();
  });
  d.addEventListener('keydown', function(e){          // keep tabbing inside the panel
    if (e.key !== 'Tab' || !d.classList.contains('open')) return;
    var f = panel.querySelectorAll('a[href],button');
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
  });
})();
</script>
<script>
/* Only one desktop dropdown may be open at a time. */
function shut(id,trig){var p=document.getElementById(id);if(!p||p.hidden)return;p.hidden=true;var b=document.querySelector(trig);if(b)b.setAttribute('aria-expanded','false');}
</script>
<script>
(function(){                                   /* desktop mega menu */
  var t = document.querySelector('.megatrig'), m = document.getElementById('mega-services');
  if (!t || !m) return;
  var head = t.closest('header'), timer = null;
  function show(){ clearTimeout(timer); shut('area-drop','.areatrig'); m.hidden = false; t.setAttribute('aria-expanded','true'); }
  function hide(){ m.hidden = true; t.setAttribute('aria-expanded','false'); }
  function lazyHide(){ clearTimeout(timer); timer = setTimeout(hide, 160); }
  t.closest('.nav-mega').addEventListener('mouseenter', show);
  m.addEventListener('mouseenter', function(){ clearTimeout(timer); });
  head.addEventListener('mouseleave', lazyHide);
  t.addEventListener('click', function(e){ e.preventDefault(); m.hidden ? show() : hide(); });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') hide(); });
  document.addEventListener('click', function(e){
    if (!m.hidden && !m.contains(e.target) && !t.contains(e.target)) hide();
  });
})();
(function(){                                   /* drawer accordions, both levels */
  var nav = document.querySelector('.nd-nav');
  if (!nav) return;
  nav.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('.nd-acc, .nd-acc2');
    if (!b) return;
    var panel = b.nextElementSibling;
    if (!panel) return;
    var open = b.getAttribute('aria-expanded') === 'true';
    b.setAttribute('aria-expanded', open ? 'false' : 'true');
    panel.hidden = open;
  });
})();
</script>
<script>
(function(){                                  /* service areas dropdown */
  var t=document.querySelector('.areatrig'), d=document.getElementById('area-drop');
  if(!t||!d) return;
  var head=t.closest('header'), timer=null;
  function show(){ clearTimeout(timer); shut('mega-services','.megatrig'); d.hidden=false; t.setAttribute('aria-expanded','true'); }
  function hide(){ d.hidden=true; t.setAttribute('aria-expanded','false'); }
  function lazyHide(){ clearTimeout(timer); timer=setTimeout(hide,160); }
  t.closest('.nav-areas').addEventListener('mouseenter',show);
  d.addEventListener('mouseenter',function(){ clearTimeout(timer); });
  head.addEventListener('mouseleave',lazyHide);
  t.addEventListener('click',function(e){ e.preventDefault(); d.hidden?show():hide(); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') hide(); });
  document.addEventListener('click',function(e){
    if(!d.hidden && !d.contains(e.target) && !t.contains(e.target)) hide();
  });
})();
</script>"""
_FORM_JS = r"""<script>
/* Contact form. Set FORM_ENDPOINT to a form-handling URL (Web3Forms,
   Formspree, etc). Until it is set the form does not pretend to send. */
(function(){var FORM_ENDPOINT="";var f=document.getElementById("estimate-form");if(!f)return;
var out=document.getElementById("f-msg-out"),btn=f.querySelector("button[type=submit]");
function say(h,ok){out.innerHTML=h;out.className="fmsg on"+(ok?" ok":"");}
f.addEventListener("submit",function(e){e.preventDefault();
var miss=[].slice.call(f.querySelectorAll("[required]")).filter(function(el){return !el.value.trim();});
if(miss.length){say("Please fill in your name, phone number and a short description.",false);miss[0].focus();return;}
if(!FORM_ENDPOINT){say('This form is not connected yet. Please call <a href="__TEL__">__PHONE__</a> '+
  'or email <a href="mailto:__EMAIL__">__EMAIL__</a>.',false);return;}
btn.disabled=true;say("Sending\u2026",false);
fetch(FORM_ENDPOINT,{method:"POST",headers:{Accept:"application/json"},body:new FormData(f)})
.then(function(r){if(!r.ok)throw 0;f.reset();say("Thanks \u2014 your request is in. We will call you back.",true);})
.catch(function(){say('Something went wrong. Please call <a href="__TEL__">__PHONE__</a>.',false);})
.then(function(){btn.disabled=false;});});})();
</script>
"""
SCRIPTS = _SCRIPTS + _FORM_JS.replace('__TEL__',SITE['phone_href']).replace(
          '__PHONE__',SITE['phone']).replace('__EMAIL__',SITE['email'])

# ==========================================================================
# 3. THEME  —  markup helpers. Do not edit per city.
# ==========================================================================

ICO = dict(
 phone='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 16.9v3a2 2 0 01-2.2 2 19.8 19.8 0 01-8.6-3.1 19.5 19.5 0 01-6-6A19.8 19.8 0 012.1 4.2 2 2 0 014.1 2h3a2 2 0 012 1.7c.1 1 .4 1.9.7 2.8a2 2 0 01-.4 2.1L8.1 9.9a16 16 0 006 6l1.3-1.3a2 2 0 012.1-.4c.9.3 1.8.6 2.8.7a2 2 0 011.7 2z"/></svg>',
 mail ='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
 clock='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>',
 pin  ='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s7-5.5 7-11a7 7 0 10-14 0c0 5.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.4"/></svg>',
 chev ='<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M6 9l6 6 6-6"/></svg>',
 tick ='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>',
 shield='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 3.5v5c0 5-3.4 8.6-8 9.5-4.6-.9-8-4.5-8-9.5v-5z"/><path d="M9 12l2.2 2.2L15.5 10"/></svg>',
)

MARK = ('<svg class="mark" viewBox="0 0 84 84" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
 '<defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#EFC44B"/>'
 '<stop offset="100%" stop-color="#C79A22"/></linearGradient>'
 '<linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#4A8F6B"/>'
 '<stop offset="100%" stop-color="#2E6B4F"/></linearGradient></defs>'
 '<path d="M8 68C8 40 26 16 46 12c16-3 28 6 34 20" fill="none" stroke="url(#g2)" stroke-width="7" stroke-linecap="round"/>'
 '<g fill="url(#g1)"><rect x="6" y="54" width="72" height="13" rx="2"/><rect x="18" y="38" width="60" height="13" rx="2"/>'
 '<rect x="32" y="22" width="46" height="13" rx="2"/></g>'
 '<g stroke="#0B1721" stroke-width="2" opacity=".4"><path d="M30 54v13M54 54v13M40 38v13M62 38v13M50 22v13"/></g></svg>')

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 84 84" role="img" aria-label="{brand}">\n'
 '  <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#EFC44B"/>'
 '<stop offset="100%" stop-color="#C79A22"/></linearGradient>'
 '<linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#4A8F6B"/>'
 '<stop offset="100%" stop-color="#2E6B4F"/></linearGradient></defs>\n'
 '  <rect width="84" height="84" rx="14" fill="#0B1721"/>\n'
 '  <path d="M8 68C8 40 26 16 46 12c16-3 28 6 34 20" fill="none" stroke="url(#g2)" stroke-width="7" stroke-linecap="round"/>\n'
 '  <g fill="url(#g1)"><rect x="6" y="54" width="72" height="13" rx="2"/><rect x="18" y="38" width="60" height="13" rx="2"/>'
 '<rect x="32" y="22" width="46" height="13" rx="2"/></g>\n'
 '  <g stroke="#0B1721" stroke-width="2" opacity=".4"><path d="M30 54v13M54 54v13M40 38v13M62 38v13M50 22v13"/></g>\n</svg>\n')

def T(s, **kw):
    """Fill {placeholders} from SITE plus anything passed in."""
    d = dict(SITE); d.update(kw)
    d.setdefault('years', str(2026 - int(SITE['founded'])))
    d.setdefault('n_areas', str(len(AREAS)))
    out = s
    for k, v in d.items():
        out = out.replace('{%s}' % k, str(v))
    return out

def area_url(a):   return '/%s-%s/' % (SITE['area_prefix'], a['slug'])
def hub_url(s):    return '/%s/' % s['slug']
def child_url(s,c):return '/%s/%s/' % (s['slug'], c)
def cx_url(s,a):   return '/%s-%s/' % (s['slug'], a['slug'])

# ---- chrome ---------------------------------------------------------------

def topbar():
    return ('<div class="topbar">\n  <div class="wrap">\n    <div>Serving {region}</div>\n'
      '    <div>Free on-site estimate: <a href="{phone_href}">{phone}</a></div>\n  </div>\n</div>\n')

def mega():
    cols=''
    for s in SILOS:
        links=''.join('          <a href="%s">%s</a>\n'%(child_url(s,c[1]),c[0]) for c in s['children'][:SHOWN])
        more='View all %d &rarr;'%len(s['children']) if len(s['children'])>SHOWN else 'View all &rarr;'
        cols+=('        <div class="mega-col">\n          <p class="mega-h"><a href="%s">%s</a></p>\n%s'
               '          <a class="mega-all" href="%s">%s</a>\n        </div>\n'
               %(hub_url(s),s['label'],links,hub_url(s),more))
    return ('  <div class="mega" id="mega-services" hidden>\n    <div class="wrap">\n'
            '      <div class="mega-cols">\n%s      </div>\n    </div>\n  </div>\n'%cols)

def areadrop():
    links=''.join('          <a href="%s">%s</a>\n'%(area_url(a),a['name'])
                  for a in sorted(AREAS,key=lambda x:x['name']))
    return ('      <div class="areadrop" id="area-drop" hidden>\n        <p class="ad-h">Where We Serve</p>\n'
            '        <div class="arealist">\n%s        </div>\n'
            '        <a class="areadrop-all" href="/areas/">View all service areas &rarr;</a>\n      </div>'%links)

def header():
    return T('<header class="site">\n  <div class="wrap">\n'
      '    <a class="brand" href="/">\n      %s\n'
      '      <span class="name">{brand_short}<small>{brand_sub}</small></span>\n    </a>\n'
      '    <nav class="main">\n      <a href="/">Home</a>\n'
      '      <span class="nav-mega"><button class="megatrig" type="button" aria-expanded="false" '
      'aria-controls="mega-services">Services%s</button></span>\n'
      '      <span class="nav-areas"><button class="areatrig" type="button" aria-expanded="false" '
      'aria-controls="area-drop">Service Areas%s</button>\n%s</span>\n'
      '      <a href="/about/">About Us</a>\n      <a href="/faq/">FAQ</a>\n      <a href="/contact/">Contact</a>\n'
      '    </nav>\n    <div class="nav-actions">\n'
      '      <a class="nav-tel" href="{phone_href}"><span class="nt-ico">%s</span>{phone}</a>\n'
      '      <a class="nav-est" href="#estimate">Get Estimate</a>\n    </div>\n'
      '    <button class="burger" type="button" aria-label="Open menu" aria-expanded="false" '
      'aria-controls="navdrawer"><span class="bars"></span></button>\n  </div>\n%s</header>\n'
      %(MARK,ICO['chev'],ICO['chev'],areadrop(),ICO['phone'],mega()))

def drawer():
    groups=''
    for s in SILOS:
        links=''.join('            <a href="%s">%s</a>\n'%(child_url(s,c[1]),c[0]) for c in s['children'][:SHOWN])
        groups+=('        <div class="nd-group2">\n          <button class="nd-acc2" type="button" '
                 'aria-expanded="false">%s%s</button>\n          <div class="nd-sub2" hidden>\n%s'
                 '            <a class="nd-all" href="%s">View all &rarr;</a>\n          </div>\n        </div>\n'
                 %(s['label'],ICO['chev'],links,hub_url(s)))
    areas=''.join('            <a href="%s">%s</a>\n'%(area_url(a),a['name'])
                  for a in sorted(AREAS,key=lambda x:x['name']))
    return T('<div class="navdrawer" id="navdrawer" hidden>\n  <div class="nd-backdrop" data-close></div>\n'
      '  <aside class="nd-panel" role="dialog" aria-modal="true" aria-label="Site menu">\n'
      '    <div class="nd-head"><span class="nd-title">Menu</span>'
      '<button class="nd-close" type="button" aria-label="Close menu" data-close>&times;</button></div>\n'
      '    <nav class="nd-nav">\n      <a href="/">Home</a>\n      <div class="nd-group">\n'
      '        <button class="nd-acc" type="button" aria-expanded="false">Services%s</button>\n'
      '        <div class="nd-sub" hidden>\n%s        </div>\n      </div>\n'
      '      <div class="nd-group">\n        <button class="nd-acc" type="button" aria-expanded="false">'
      'Service Areas%s</button>\n        <div class="nd-sub" hidden>\n'
      '          <div class="nd-sub2 nd-arealist">\n%s'
      '            <a class="nd-all" href="/areas/">View all service areas &rarr;</a>\n'
      '          </div>\n        </div>\n      </div>\n'
      '      <a href="/about/">About Us</a>\n      <a href="/faq/">FAQ</a>\n      <a href="/contact/">Contact</a>\n'
      '    </nav>\n    <div class="nd-cta">\n'
      '      <a class="nd-call" href="{phone_href}"><small>Tap to call</small><b>{phone}</b></a>\n'
      '      <a class="nd-est" href="#estimate" data-close>Get a free estimate</a>\n'
      '    </div>\n  </aside>\n</div>\n'%(ICO['chev'],groups,ICO['chev'],areas))

def footer():
    cols=''
    for s in SILOS[:2]:
        items=''.join('          <li><a href="%s">%s</a></li>\n'%(child_url(s,c[1]),c[0]) for c in s['children'][:4])
        cols+=('      <div>\n        <p class="f-h">%s</p>\n        <ul>\n%s        </ul>\n      </div>\n'
               %(s['label'],items))
    areas=''.join('        <li><a href="%s">%sRetaining Walls in %s</a></li>\n'%(area_url(a),ICO['pin'],a['name'])
                  for a in AREAS)
    return T('<footer>\n  <div class="wrap">\n    <div class="f-grid">\n'
      '      <div>\n        <div class="brand">%s<span class="name">{brand_short}<small>{brand_sub}</small></span></div>\n'
      '        <p class="f-about">Engineered retaining walls for {region}. Limestone, concrete, block and '
      'timber — with drainage, engineering and permits handled as part of the job.</p>\n      </div>\n%s'
      '      <div>\n        <p class="f-h">Contact Us</p>\n        <ul class="f-contact">\n'
      '          <li>%s<span>Serving all of<br>{region}</span></li>\n'
      '          <li>%s<a href="{phone_href}">{phone}</a></li>\n'
      '          <li>%s<a href="mailto:{email}">{email}</a></li>\n'
      '          <li>%s<span>Mon–Fri 7:00am – 6:00pm<br>Sat 8:00am – 2:00pm</span></li>\n'
      '        </ul>\n      </div>\n    </div>\n'
      '    <div class="f-areas">\n      <div class="f-areas-head"><p class="f-h">Service Areas</p>'
      '<span>Based in {city} — serving {n_areas} communities across {region}.</span></div>\n'
      '      <p class="f-sub">Retaining Wall Contractor — Cities We Serve</p>\n'
      '      <ul class="f-area-list">\n%s      </ul>\n    </div>\n'
      '    <div class="legal">\n      Cost ranges shown are planning estimates only and do not constitute '
      'a quote. Permit thresholds and requirements vary by jurisdiction across {region} — confirm '
      'requirements for your property with the relevant building department.<br><br>\n'
      '      © 2026 {brand}. All rights reserved. · <a href="/privacy/">Privacy</a> · '
      '<a href="/terms/">Terms</a>\n    </div>\n  </div>\n</footer>\n'
      %(MARK,cols,ICO['pin'],ICO['phone'],ICO['mail'],ICO['clock'],areas))

def mobilebar():
    return T('<div class="mobilebar" id="mobilebar">\n  <div class="mb-row">\n'
      '    <a class="mb-btn mb-call" href="{phone_href}"><b>Call Now</b><small>{phone}</small></a>\n'
      '    <a class="mb-btn mb-est" href="/contact/"><b>Free Estimate</b><small>No obligation</small></a>\n'
      '  </div>\n</div>\n')

# ==========================================================================
# 4. PAGE BUILDERS
# ==========================================================================

def strip(t): return re.sub(r'<[^>]+>','',t).replace('&amp;','&').replace('&mdash;','—')

_SC=re.compile(r'((?:[.!?]\s+|<p>|<strong>|<summary>)<a href="[^"]+">)([a-z])')
def scase(h): return _SC.sub(lambda m:m.group(1)+m.group(2).upper(),h)

def checklist(items):
    return ('      <ul class="checklist">\n'
            + ''.join('        <li><strong>%s</strong> %s</li>\n'%(a,b) for a,b in items)
            + '      </ul>\n')

def subs(items):
    return ''.join('      <h3 class="sub">%s</h3>\n      <p>%s</p>\n'%(a,b) for a,b in items)

def faqblock(items, indent='      '):
    o=''
    for i,(q,a) in enumerate(items):
        o+=('%s<details class="q"%s>\n%s  <summary>%s</summary>\n%s  <p>%s</p>\n%s</details>\n'
            %(indent,' open' if i==0 else '',indent,q,indent,a,indent))
    return o

def steps(eyebrow,h2,lede,items):
    o=('<section class="dark">\n  <div class="wrap">\n    <div class="sec-head center">\n'
       '      <div class="eyebrow center light">%s</div>\n      <h2 class="sec">%s</h2>\n'
       '      <p class="lede" style="margin-inline:auto">%s</p>\n    </div>\n    <div class="steps">\n'
       %(eyebrow,h2,lede))
    for i,(t,d) in enumerate(items,1):
        o+='      <div class="step"><div class="n">%d</div><h3>%s</h3><p>%s</p></div>\n'%(i,t,d)
    return o+'    </div>\n  </div>\n</section>\n'

def area_grid(h2,lede,link=area_url):
    cards=''.join('      <a class="area" href="%s"><span class="pin">%s%s</span> '
                  '<span class="arw">&rarr;</span></a>\n'%(link(a),ICO['pin'],a['name']) for a in AREAS)
    cards+=('      <a class="area" href="/areas/"><span class="pin">%sView all areas</span> '
            '<span class="arw">&rarr;</span></a>\n'%ICO['pin'])
    return ('<section id="areas">\n  <div class="wrap">\n    <div class="sec-head center">\n'
            '      <div class="eyebrow center">Coverage</div>\n      <h2 class="sec">%s</h2>\n'
            '      <p class="lede" style="margin-inline:auto">%s</p>\n    </div>\n'
            '    <div class="area-grid">\n%s    </div>\n  </div>\n</section>\n'%(h2,lede,cards))

def cat_grid(items):
    return ('      <div class="cat-grid">\n'
            + ''.join('        <a class="cat" href="%s">%s <span class="arw">&rarr;</span></a>\n'%(u,l)
                      for l,u in items) + '      </div>\n')

def final_cta(h2,p):
    return T('<section class="final" id="estimate">\n  <div class="wrap">\n    <p class="final-h">%s</p>\n'
      '    <p>%s</p>\n    <div><a class="btn" href="{phone_href}">Call {phone}</a></div>\n'
      '    <div><a class="textlink" href="/contact/" style="margin-top:15px">Get a free estimate &rarr;</a></div>\n'
      '  </div>\n</section>\n'%(h2,p))

def hero(pill,h1,h1sub,lede,crumbs,img):
    cr=''.join('<a href="%s">%s</a><span>&rsaquo;</span>'%(u,l) if u else l for l,u in crumbs)
    return T('<section class="phero">\n  <div class="phero-media">\n    <picture>\n'
      '      <source srcset="/img/%s.avif" type="image/avif">\n'
      '      <source srcset="/img/%s.webp" type="image/webp">\n'
      '      <img src="/img/%s.jpg" alt="%s" title="%s" fetchpriority="high" decoding="async" '
      'width="1376" height="602" onerror="this.closest(\'picture\').remove()">\n    </picture>\n  </div>\n'
      '  <div class="phero-scrim" aria-hidden="true"></div>\n  <div class="wrap">\n'
      '    <div class="phero-copy">\n      <nav class="crumbs" aria-label="Breadcrumb">%s</nav>\n'
      '      <span class="phero-pill">%s %s</span>\n'
      '      <h1>%s%s</h1>\n      <p><a class="brandlink" href="/">{brand}</a> %s</p>\n'
      '      <div><a class="callbtn" href="{phone_href}"><span class="cb-ico">%s</span>Call {phone}</a></div>\n'
      '      <div><a class="textlink" href="#estimate" style="margin-top:11px">Or get a free estimate &rarr;</a></div>\n'
      '      <span class="micro">Free on-site estimate · No obligation · Written scope before you commit</span>\n'
      '    </div>\n  </div>\n</section>\n'
      %(img,img,img,img.replace('-',' ').title(),img.replace('-',' ').title(),cr,ICO['shield'],pill,
        h1,'<span class="h1-sub">%s</span>'%h1sub if h1sub else '',lede,ICO['phone']))

def schema(nodes):
    return ('<script type="application/ld+json">\n%s\n</script>'
            % json.dumps({"@context":"https://schema.org","@graph":nodes},indent=2,ensure_ascii=False))

def business_node():
    return {"@type":"GeneralContractor","@id":SITE['domain']+"/#business","name":SITE['brand'],
      "url":SITE['domain']+"/","telephone":SITE['phone_e164'],"email":SITE['email'],
      "foundingDate":SITE['founded'],
      "areaServed":[{"@type":"City","name":a['name']} for a in AREAS],
      "openingHoursSpecification":[
        {"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday"],
         "opens":"07:00","closes":"18:00"},
        {"@type":"OpeningHoursSpecification","dayOfWeek":["Saturday"],"opens":"08:00","closes":"14:00"}]}

def crumb_node(trail):
    return {"@type":"BreadcrumbList","itemListElement":[
      {"@type":"ListItem","position":i+1,"name":n,"item":SITE['domain']+u} for i,(n,u) in enumerate(trail)]}

def faq_node(pairs):
    return {"@type":"FAQPage","mainEntity":[{"@type":"Question","name":strip(T(q)),
      "acceptedAnswer":{"@type":"Answer","text":strip(T(a))}} for q,a in pairs]}

def page(path,title,desc,body,nodes,extra_css=''):
    """Assemble one complete HTML document."""
    url=SITE['domain']+path
    return T('<title>%s</title>\n'
      '<meta name="description" content="%s">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      '<link rel="canonical" href="%s">\n'
      '<meta property="og:type" content="website">\n<meta property="og:url" content="%s">\n'
      '<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n'
      '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
      '<link rel="preload" as="font" type="font/woff2" href="/fonts/barlow-sc-800.woff2" crossorigin>\n'
      '<link rel="preload" as="font" type="font/woff2" href="/fonts/barlow-400.woff2" crossorigin>\n'
      '<style>%s</style>\n<style>%s</style>\n%s\n'
      '%s%s%s%s%s%s\n'
      %(title,desc,url,url,title,desc,FONTFACE,CSS,extra_css,schema(nodes),
        topbar(),header(),body,footer(),mobilebar()+drawer()+SCRIPTS))

# ==========================================================================
# 5. THE PAGES
# ==========================================================================

def p_home():
    body = hero("Serving {region} since {founded}","Retaining Wall Contractor",T(COPY['home_h1_sub']),
                T(COPY['home_lede']),[("Home",None)],"hero-home")
    art  = '      <h2>Why Retaining Walls in {city} Are a Specialist Job</h2>\n'
    art += '      <p>%s</p>\n'%T(COPY['home_lede'])
    art += checklist([(T(a),T(b)) for a,b in COPY['conditions']])
    art += '      <h2>What We Do</h2>\n'
    art += cat_grid([(s['label'],hub_url(s)) for s in SILOS])
    art += ('      <p>Not sure which of those your project is &mdash; and plenty are more than one? '
            'That is exactly what the first conversation is for. <a href="/contact/">Get in touch</a>.</p>\n')
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += steps("Process",T("How a {city} Project Runs"),
        "Five phases from first call to sign-off. You will know which one you are in at any point.",
        COPY['process'])
    body += area_grid(T("Areas We Serve Around {city}"),
        T("We work across {n_areas} communities in {region}, and the ground changes more across that "
          "distance than people expect."))
    body += ('<section>\n  <div class="wrap narrow">\n    <div class="sec-head center">\n'
             '      <div class="eyebrow center">Questions</div>\n      <h2 class="sec">Retaining Wall FAQs</h2>\n'
             '    </div>\n%s  </div>\n</section>\n'
             % faqblock([(T(q),T(a)) for q,a in COPY['faq_groups'][0][2]],'    '))
    body += final_cta(T("Get your wall priced properly"),
        "We'll walk the ground, tell you what the wall actually needs, and leave you with an itemised "
        "written scope. No obligation.")
    nodes=[{"@type":"WebPage","@id":SITE['domain']+"/#page","url":SITE['domain']+"/",
            "name":strip(T(COPY['home_title'])),"description":strip(T(COPY['home_desc']))},
           crumb_node([("Home","/")]),
           faq_node(COPY['faq_groups'][0][2]), business_node()]
    return page("/",T(COPY['home_title']),T(COPY['home_desc']),body,nodes)

def p_hub(s):
    fmt=dict(label=s['label'],blurb=s['blurb'],slug=s['slug'])
    body = hero(T("{city} and {region}"),s['label'],T(" in {city}, {state}"),
                T(COPY['hub_lede'],**fmt),[("Home","/"),(s['label'],None)],"hero-%s"%s['slug'])
    art  = '      <h2>%s in %s, %s</h2>\n'%(s['label'],SITE['city'],SITE['state'])
    art += '      <p>%s</p>\n'%T(s['blurb'])
    art += ('      <p>What that means on the ground changes across {region}. The Balcones Escarpment puts '
            'thin soil over hard limestone on one side of the city and deep expansive clay on the other, '
            'so the same job description produces two different walls depending on your address.</p>\n')
    art += '      <h2>What We Cover</h2>\n'
    art += cat_grid([(c[0],child_url(s,c[1])) for c in s['children']])
    art += '      <h2>How We Work</h2>\n'+checklist([(T(a),T(b)) for a,b in COPY['standards']])
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += steps("Process",T("How a {city} Project Runs"),
        "Five phases from first call to sign-off.",COPY['process'])
    link=(lambda a: cx_url(s,a)) if s['slug'] in CITY_CLUSTERS else area_url
    title=("%s in Every Area We Serve"%s['label']) if s['slug'] in CITY_CLUSTERS else T("Areas We Serve Around {city}")
    body += area_grid(title,T("Pick your area for how the ground, the drainage and the permit path "
                              "actually differ there."),link)
    body += final_cta(T("Get your wall priced properly"),
        "Free on-site visit, itemised written scope, nothing to sign on the day.")
    nodes=[{"@type":"Service","name":s['label'],"serviceType":s['label'],
            "description":strip(T(s['blurb'])),"url":SITE['domain']+hub_url(s),
            "provider":{"@id":SITE['domain']+"/#business"},
            "areaServed":{"@type":"City","name":SITE['city']}},
           crumb_node([("Home","/"),(s['label'],hub_url(s))]), business_node()]
    return page(hub_url(s),T(COPY['hub_title'],**fmt),T(COPY['hub_desc'],**fmt),body,nodes)

def p_child(s,label,slug):
    fmt=dict(child=strip(label),label=s['label'])
    body = hero(s['label'],strip(label),T(" in {city}, {state}"),
                T("handles {child_l} across {region} — here is what the work actually involves.",
                  child_l=strip(label).lower()),
                [("Home","/"),(s['label'],hub_url(s)),(strip(label),None)],"hero-%s"%s['slug'])
    art  = '      <h2>What Is %s?</h2>\n'%strip(label)
    art += ('      <p>[Write 2–3 paragraphs defining %s for a {city} reader. Lead with what it is, then '
            'why {region} ground makes it matter. This is the section that has to be genuinely yours.]</p>\n'
            %strip(label).lower())
    art += '      <h2>When It Is Needed</h2>\n'+checklist([("Point one.","[detail]"),("Point two.","[detail]")])
    art += '      <h2>How We Do It</h2>\n'+checklist([(T(a),T(b)) for a,b in COPY['standards'][:4]])
    art += '      <h2>%s FAQ\'s</h2>\n'%strip(label)
    art += faqblock([(T(q),T(a)) for q,a in COPY['faq_groups'][2][2][:3]])
    art += '\n      <h2>Related %s Work</h2>\n'%s['label']
    art += cat_grid([(c[0],child_url(s,c[1])) for c in s['children'] if c[1]!=slug])
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += final_cta(T("Get your wall priced properly"),"Free on-site visit and an itemised written scope.")
    nodes=[{"@type":"Service","name":strip(label),"serviceType":strip(label),
            "url":SITE['domain']+child_url(s,slug),"provider":{"@id":SITE['domain']+"/#business"},
            "areaServed":{"@type":"City","name":SITE['city']}},
           crumb_node([("Home","/"),(s['label'],hub_url(s)),(strip(label),child_url(s,slug))]),
           faq_node(COPY['faq_groups'][2][2][:3]), business_node()]
    return page(child_url(s,slug),T(COPY['child_title'],**fmt),T(COPY['child_desc'],**fmt),body,nodes)

def p_area(a):
    fmt=dict(area=a['name'],blurb=a['blurb'],auth=a['auth'])
    body = hero(T("Serving {area} and nearby",**fmt),"Retaining Wall Contractor",
                T(" in {area}, {state}",**fmt),T(COPY['area_lede'],**fmt),
                [("Home","/"),("Service Areas","/areas/"),(a['name'],None)],"hero-home")
    art  = '      <h2>Retaining Walls in %s</h2>\n'%a['name']
    art += '      <p>%s</p>\n'%T(COPY['area_intro'],**fmt)
    art += '      <p>%s</p>\n'%T(COPY['area_permit'],**fmt)
    art += '      <h2>What We Do in %s</h2>\n'%a['name']
    art += cat_grid([(s['label'], cx_url(s,a) if s['slug'] in CITY_CLUSTERS else hub_url(s)) for s in SILOS])
    art += '      <h2>What Shapes a Wall Here</h2>\n'+checklist([(T(x),T(y)) for x,y in COPY['conditions'][:4]])
    art += '      <h2>Nearby</h2>\n      <p>We also work in %s.</p>\n'%(
        ', '.join('<a href="%s">%s</a>'%(area_url(n),n['name'])
                  for n in AREAS if n['name'] in a['nearby']))
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += steps("Process",T("How a {area} Project Runs",**fmt),
        "Five phases from first call to sign-off.",COPY['process'])
    body += final_cta(T("Get a free on-site estimate in %s"%a['name']),
        "We walk the ground, price it properly, and leave you a written scope.")
    nodes=[{"@type":"Service","name":"Retaining Wall Contractor","url":SITE['domain']+area_url(a),
            "provider":{"@id":SITE['domain']+"/#business"},
            "areaServed":[{"@type":"City","name":a['name']}]+[{"@type":"City","name":n} for n in a['nearby']]},
           crumb_node([("Home","/"),("Service Areas","/areas/"),(a['name'],area_url(a))]), business_node()]
    return page(area_url(a),T(COPY['area_title'],**fmt),T(COPY['area_desc'],**fmt),body,nodes)

def p_cx(s,a):
    fmt=dict(label=s['label'],label_lower=s['label'].lower(),area=a['name'],blurb=a['blurb'],auth=a['auth'])
    body = hero(T("Serving {area}",**fmt),s['label'],T(" in {area}, {state}",**fmt),
                T(COPY['cx_lede'],**fmt),
                [("Home","/"),(s['label'],hub_url(s)),(a['name'],None)],"hero-%s"%s['slug'])
    art  = '      <h2>%s in %s: %s</h2>\n'%(s['label'],a['name'],a['blurb'].split(',')[0])
    art += ('      <p>[LANDMARK-LED OPENER. Name the actual streets, creeks, parks or ridges in %s and '
            'say what they mean for %s. This paragraph is the one that must not read like any other '
            'page.]</p>\n'%(a['name'],s['label'].lower()))
    art += '      <p>%s</p>\n'%T(COPY['area_intro'],**fmt)
    art += '      <h2>What Shapes %s Here</h2>\n'%s['label']
    art += checklist([(T(x),T(y)) for x,y in COPY['conditions'][:4]])
    art += '      <h2>Permits in %s</h2>\n      <p>%s</p>\n'%(a['name'],T(COPY['area_permit'],**fmt))
    art += '      <h2>%s FAQ\'s for %s</h2>\n'%(s['label'],a['name'])
    art += faqblock([(T(q,**fmt),T(x,**fmt)) for q,x in COPY['faq_groups'][3][2]])
    art += '\n      <h2>What This Involves</h2>\n'
    art += cat_grid([(c[0],child_url(s,c[1])) for c in s['children']])
    art += ('      <p>Or see everything we do in <a href="%s">%s</a>.</p>\n'%(area_url(a),a['name']))
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += final_cta(T("%s in %s"%(s['label'],a['name'])),
        "Free on-site assessment and an itemised written scope.")
    nodes=[{"@type":"Service","name":s['label'],"serviceType":s['label'],"url":SITE['domain']+cx_url(s,a),
            "provider":{"@id":SITE['domain']+"/#business"},"areaServed":{"@type":"City","name":a['name']}},
           crumb_node([("Home","/"),(s['label'],hub_url(s)),(a['name'],cx_url(s,a))]),
           faq_node(COPY['faq_groups'][3][2]), business_node()]
    return page(cx_url(s,a),T(COPY['cx_title'],**fmt),T(COPY['cx_desc'],**fmt),body,nodes)

def p_faq():
    body = hero("Straight answers","Retaining Wall <em>FAQs</em>",T(" in {city}, {state}"),
                "answers the questions people actually ask before handing a wall to anyone.",
                [("Home","/"),("FAQ",None)],"hero-home")
    secs=''; allq=[]
    for i,(title,lede,qas) in enumerate(COPY['faq_groups']):
        qas=[(T(q),T(a)) for q,a in qas]; allq+=qas
        secs+=('<section%s>\n  <div class="wrap narrow">\n    <div class="sec-head center">\n'
               '      <div class="eyebrow center">0%d</div>\n      <h2 class="sec">%s</h2>\n'
               '      <p class="lede" style="margin-inline:auto">%s</p>\n    </div>\n%s  </div>\n</section>\n'
               %(' class="tint"' if i%2 else '',i+1,title,T(lede),faqblock(qas,'    ')))
    body += secs + final_cta("Still have a question?","Call and ask. No obligation, no pressure.")
    nodes=[faq_node(allq), crumb_node([("Home","/"),("FAQ","/faq/")]), business_node()]
    return page("/faq/",T("Retaining Wall FAQs | {city}, {state}"),
                T("Answers on cost, permits, choosing a wall and diagnosing a failing one in {city}, {state}."),
                body,nodes,extra_css='<style>.tint{background:var(--cream,#F7F4EC)}</style>')

def p_areas():
    body = hero(T("{n_areas} communities"),"Retaining Wall","<em>Service Areas</em>",
                T("builds across {region}. Here is where, and what is different about each."),
                [("Home","/"),("Service Areas",None)],"hero-home")
    art=('      <h2>Where We Build Across {region}</h2>\n'
         '      <p>The ground changes more across {region} than most people expect. West of the Balcones '
         'Escarpment you are on thin soil over hard limestone; east of it, deep Blackland Prairie clay '
         'that swells and shrinks through the season. Each area page below covers what is specific to '
         'that place rather than repeating the same copy with the name swapped.</p>\n')
    body += ('<section class="pagebody">\n  <div class="wrap narrow"><article>\n%s  </article></div>\n</section>\n'
             % T(scase(art)))
    body += area_grid("The Communities We Serve",
        "Every one has its own page covering the ground, the drainage and the permit path there.")
    body += final_cta("Not sure if you're in range?","Call and we will tell you honestly.")
    nodes=[{"@type":"CollectionPage","url":SITE['domain']+"/areas/","name":T("Retaining Wall Service Areas in {region}"),
            "hasPart":[{"@type":"WebPage","name":"Retaining Walls in %s"%a['name'],
                        "url":SITE['domain']+area_url(a)} for a in AREAS]},
           crumb_node([("Home","/"),("Service Areas","/areas/")]), business_node()]
    return page("/areas/",T("Retaining Wall Service Areas in {region}"),
                T("The {n_areas} communities we build retaining walls in across {region}."),body,nodes)

def p_about():
    body = hero("Retaining walls are all we do","<em>About</em> "+SITE['brand'],"",
                T("has built retaining walls across {region} since {founded} — and nothing else, which is the point."),
                [("Home","/"),("About Us",None)],"hero-home")
    glance=''.join('        <li>%s<span><strong>%s</strong> %s</span></li>\n'%(ICO['tick'],T(a),T(b))
                   for a,b in COPY['glance'])
    rail=('      <div class="glance">\n        <p class="gl-h">At a glance</p>\n        <ul>\n%s        </ul>\n'
          '        <a class="btn" href="{phone_href}">Call {phone}</a>\n'
          '        <p class="micro">Free on-site estimate &middot; No obligation</p>\n      </div>\n'%glance)
    main =('      <h2>Our story</h2>\n      <p>%s</p>\n'%T(COPY['about_story'])
          +'      <h2>How we work</h2>\n'+checklist([(T(a),T(b)) for a,b in COPY['standards']])
          +'      <h2>What we will not do</h2>\n'+subs([(T(a),T(b)) for a,b in COPY['wont_do']])
          +'      <h2>What we build</h2>\n'+cat_grid([(s['label'],hub_url(s)) for s in SILOS]))
    body += T('<section class="pagebody">\n  <div class="wrap">\n    <div class="abx">\n'
              '      <div class="abx-main">\n%s      </div>\n      <div class="abx-rail">\n%s      </div>\n'
              '    </div>\n  </div>\n</section>\n'%(scase(main),rail))
    body += area_grid(T("Areas We Serve Around {city}"),T("Concentrated where the ground actually moves."))
    body += final_cta("Get your wall priced properly","Free on-site visit and an itemised written scope.")
    nodes=[{"@type":"AboutPage","url":SITE['domain']+"/about/","name":T("About {brand}")},
           crumb_node([("Home","/"),("About Us","/about/")]), business_node()]
    return page("/about/",T("About {brand} | Retaining Wall Specialists"),
                T("About {brand} — building retaining walls across {region} since {founded}."),body,nodes,
                extra_css=ABOUT_CSS)

def p_contact():
    body = hero("Free on-site estimates","<em>Contact</em> Us",T(" in {city}, {state}"),
                "walks the ground, prices the wall properly and leaves you an itemised written scope.",
                [("Home","/"),("Contact",None)],"hero-home")
    hrs=''.join('            <dt>%s</dt><dd>%s</dd>\n'%(a,b) for a,b in SITE['hours'])
    cards=T('      <div class="ccard"><span class="ci">%s</span><div>\n'
      '          <p class="cc-h">Call or text</p>\n          <span class="big"><a href="{phone_href}">{phone}</a></span>\n'
      '          <p>The fastest way to reach us. Leave a message if we are on a site and we call back the '
      'same working day.</p>\n        </div></div>\n'
      '      <div class="ccard"><span class="ci">%s</span><div>\n'
      '          <p class="cc-h">Email</p>\n          <span class="big" style="font-size:16.5px">'
      '<a href="mailto:{email}">{email}</a></span>\n'
      '          <p>Best if you have photos. Pictures of the wall and the ground above it tell us more '
      'than a long description.</p>\n        </div></div>\n'
      '      <div class="ccard"><span class="ci">%s</span><div>\n'
      '          <p class="cc-h">Hours</p>\n          <dl>\n%s          </dl>\n'
      '        </div></div>\n'
      '      <div class="ccard"><span class="ci">%s</span><div>\n'
      '          <p class="cc-h">Where we work</p>\n          <span class="big" style="font-size:19px">'
      '{n_areas} communities across {region}</span>\n'
      '          <p>Just outside? Call anyway and we will tell you honestly whether we are the right '
      'people for it.</p>\n        </div></div>\n'
      %(ICO['phone'],ICO['mail'],ICO['clock'],hrs,ICO['pin']))
    body += T('<section class="pagebody">\n  <div class="wrap">\n    <div class="cx">\n'
              '      <div class="cx-cards">\n%s      </div>\n      <div>\n%s      </div>\n    </div>\n'
              '  </div>\n</section>\n'%(cards,FORM))
    body += final_cta("Prefer to talk it through?","Call and we will work out what you actually need.")
    nodes=[{"@type":"ContactPage","url":SITE['domain']+"/contact/","name":T("Contact {brand}")},
           crumb_node([("Home","/"),("Contact","/contact/")]), business_node()]
    return page("/contact/",T("Contact {brand} | Free Estimates in {city}, {state}"),
                T("Contact {brand} for a free on-site estimate. Call {phone} or send photos of the wall."),
                body,nodes,extra_css=CONTACT_CSS)

def p_404():
    body=('<section class="pagebody"><div class="wrap narrow"><article>\n'
          '  <h1>404</h1>\n  <h2>This page didn\'t hold</h2>\n'
          '  <p>The page you are after has moved or never existed. Try the '
          '<a href="/">home page</a>, the <a href="/areas/">service areas</a>, or '
          '<a href="/contact/">get in touch</a>.</p>\n</article></div></section>\n')
    return page("/404.html","Page not found | "+SITE['brand'],"Page not found.",body,
                [crumb_node([("Home","/")])])

# ==========================================================================
# 6. SITE FILES + MAIN
# ==========================================================================

def all_pages():
    P=[("/",p_home()),("/areas/",p_areas()),("/faq/",p_faq()),("/about/",p_about()),("/contact/",p_contact())]
    for s in SILOS:
        P.append((hub_url(s),p_hub(s)))
        for label,slug in s['children']:
            P.append((child_url(s,slug),p_child(s,label,slug)))
    for a in AREAS:
        P.append((area_url(a),p_area(a)))
        for s in SILOS:
            if s['slug'] in CITY_CLUSTERS:
                P.append((cx_url(s,a),p_cx(s,a)))
    return P

def core_pages():
    """--core : ONE example of each page type. This is the structural template."""
    s   = SILOS[0]                      # example service cluster (hub)
    lbl,slug = s['children'][0]         # example sub-cluster (child)
    a   = AREAS[0]                      # example service area
    cs  = next(x for x in SILOS if x['slug'] in CITY_CLUSTERS)
    return [
      ("/",                 p_home()),                 # 1. home
      (hub_url(s),          p_hub(s)),                  # 3. service cluster / category hub
      (child_url(s,slug),   p_child(s,lbl,slug)),       # 4. service sub-cluster page
      ("/areas/",           p_areas()),                 # 5. service-areas index
      (area_url(a),         p_area(a)),                 # 6. single service-area page
      (cx_url(cs,a),        p_cx(cs,a)),                # 7. cluster x city page
      ("/faq/",             p_faq()),                   # 8. FAQ
      ("/about/",           p_about()),                 # 9. About Us
      ("/contact/",         p_contact()),               # 10. Contact
      ("/404.html",         p_404()),                   # 11. 404
    ]

def sitemap(paths):
    pri=lambda p:'1.0' if p=='/' else ('0.9' if p.count('/')==2 else '0.7')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + ''.join('  <url><loc>%s%s</loc><priority>%s</priority></url>\n'%(SITE['domain'],p,pri(p)) for p in paths)
      + '</urlset>\n')

def robots():
    return "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n"%SITE['domain']

def headers():
    return ("/*\n  X-Content-Type-Options: nosniff\n  X-Frame-Options: SAMEORIGIN\n"
      "  Referrer-Policy: strict-origin-when-cross-origin\n"
      "  Permissions-Policy: geolocation=(), microphone=(), camera=()\n"
      "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n\n"
      "/*.svg\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/*.png\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/*.ico\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/*.jpg\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/*.webp\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/*.avif\n  Cache-Control: public, max-age=31536000, immutable\n"
      "/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n  Access-Control-Allow-Origin: *\n\n"
      "/*.html\n  Cache-Control: public, max-age=0, must-revalidate\n"
      "/\n  Cache-Control: public, max-age=0, must-revalidate\n")

def redirects():
    host=SITE['domain'].replace('https://','')
    r=["# Force apex","https://www.%s/*  %s/:splat  301"%(host,SITE['domain']),"",
       "/home            /            301","/estimate        /#estimate   301",
       "/free-estimate   /#estimate   301","/quote           /#estimate   301",
       "/contact-us      /contact/    301","/about-us        /about/      301",
       "/faqs            /faq/        301","/service-areas   /areas/      301",""]
    for s in SILOS: r.append("/%-16s %-34s 301"%(s['nav'].lower(),hub_url(s)))
    return '\n'.join(r)+'\n'

def wrangler():
    name=SITE['domain'].replace('https://','').split('.')[0]
    return ('{\n  // Static-site Worker. No Worker script — assets served from the repo root.\n'
      '  "name": "%s",\n  "compatibility_date": "2025-09-01",\n'
      '  "assets": {\n    "directory": "./",\n    "html_handling": "auto-trailing-slash",\n'
      '    "not_found_handling": "404-page"\n  }\n}\n'%name)

def report(pages):
    """Duplicate-content check across every generated page pair."""
    import itertools
    def bodyof(h):
        m=re.search(r'<article>(.*?)</article>',h,re.S)
        t=m.group(1) if m else h
        return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',t)).strip()
    def sents(t): return {x.strip() for x in re.split(r'(?<=[.!?]) ',t) if len(x.strip())>40}
    def sh(t,n=5):
        w=re.findall(r"[a-z']+",t.lower()); return {tuple(w[i:i+n]) for i in range(len(w)-n+1)}
    def bucket(p):
        seg=[x for x in p.strip('/').split('/') if x]
        if not seg or p=='/404.html': return None
        if len(seg)==2:
            for h in SILOS:
                if seg[0]==h['slug']: return 'sub-cluster: '+h['slug']
            return None
        if len(seg)!=1: return None
        u=seg[0]
        if u in {h['slug'] for h in SILOS}: return None
        for h in SILOS:
            if h['slug'] in CITY_CLUSTERS and u.startswith(h['slug']+'-'):
                return 'city pages: '+h['slug']
        if u.startswith(SITE['area_prefix']+'-'): return 'service-area pages'
        return None
    groups={}
    for p,h in pages:
        k=bucket(p)
        if k: groups.setdefault(k,[]).append((p,bodyof(h)))
    print('\nDUPLICATE CONTENT REPORT (article body only)')
    print('='*62)
    for k,v in sorted(groups.items()):
        if len(v)<2: continue
        S={p:sents(t) for p,t in v}; G={p:sh(t) for p,t in v}
        sp=[100*len(S[a]&S[b])/max(1,min(len(S[a]),len(S[b]))) for a,b in itertools.combinations(S,2)]
        gp=[100*len(G[a]&G[b])/max(1,len(G[a]|G[b])) for a,b in itertools.combinations(G,2)]
        flag='' if sum(sp)/len(sp)<10 else '   <-- TOO SIMILAR, rewrite the openers'
        print('  %-34s %2d pages  sentence %5.1f%%  phrase %5.1f%%%s'
              %(k,len(v),sum(sp)/len(sp),sum(gp)/len(gp),flag))

def main():
    out='.' if '--here' in sys.argv else 'out'
    pages=core_pages() if '--core' in sys.argv else all_pages()
    for path,htmlsrc in pages:
        rel='404.html' if path=='/404.html' else (path.strip('/')+'/index.html' if path!='/' else 'index.html')
        dest=os.path.join(out,rel)
        os.makedirs(os.path.dirname(dest) or '.',exist_ok=True)
        io.open(dest,'w',encoding='utf-8').write(htmlsrc)
    paths=[p for p,_ in pages if p!='/404.html']
    for name,content in (('sitemap.xml',sitemap(paths)),('robots.txt',robots()),('_headers',headers()),
                         ('_redirects',redirects()),('wrangler.jsonc',wrangler()),
                         ('favicon.svg',T(FAVICON)),
                         ('.assetsignore','.git\n.gitignore\n.assetsignore\nwrangler.jsonc\nREADME.md\nbuild_site.py\n')):
        io.open(os.path.join(out,name),'w',encoding='utf-8').write(content)
    for d in ('img','fonts'): os.makedirs(os.path.join(out,d),exist_ok=True)
    print('%d pages written to %s/'%(len(pages),out))
    print('  %d service areas x %d city clusters, %d hubs, %d sub-pages'
          %(len(AREAS),len(CITY_CLUSTERS),len(SILOS),sum(len(s['children']) for s in SILOS)))
    if '--core' in sys.argv:
        print('  (template mode: one example of each page type — nav links to the'
              ' rest of the site will 404 until you run a full build)')
    print('\nNEXT: drop hero images into %s/img/ named hero-home, %s'
          %(out,', '.join('hero-'+s['slug'] for s in SILOS)))
    print('      copy your woff2 files into %s/fonts/, then push to a NEW repo.'%out)
    if '--report' in sys.argv: report(pages)

if __name__=='__main__':
    main()
